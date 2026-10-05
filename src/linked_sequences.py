"""Opt-in FVG-object confirmation; legacy sequence columns are preserved."""
from __future__ import annotations

import numpy as np
import pandas as pd

CONTRACT = 'fvg_object_linked_v1'
LEGACY = 'production_boolean_v1'


def selected_contract(config):
    value = config.get('backtest', {}).get('sequence_contract', LEGACY)
    if value not in (LEGACY, CONTRACT):
        raise ValueError(f'Unknown sequence_contract: {value}')
    return value


def _times(values, *, nullable=False):
    # Reject naive values rather than silently interpreting local time as UTC.
    parsed = [pd.NaT if pd.isna(v) else pd.Timestamp(v) for v in values]
    if any(pd.notna(v) and v.tzinfo is None for v in parsed):
        raise ValueError('Sequence timestamps must be timezone-aware')
    if not nullable and any(pd.isna(v) for v in parsed):
        raise ValueError('Sequence timestamps must be non-null')
    return pd.DatetimeIndex(pd.to_datetime(parsed, utc=True))


def add_linked_sequences(frame, tracked_fvgs, *, lookback_bars=10):
    """Bind post-trigger FVG creation and its own later retest to a setup.

    Core reversal and displacement-break definitions stay unchanged. This
    contract fixes object identity, not the independent same-row core ambiguity
    or a separately defined post-retest micro-BOS. It never reads future prices.
    Lifecycle times are consulted only when their event has become visible.
    """
    if isinstance(lookback_bars, bool) or not isinstance(lookback_bars, int) or lookback_bars <= 0:
        raise ValueError('lookback_bars must be a positive integer')
    times = _times(frame.timestamp)
    if times.has_duplicates or not times.is_monotonic_increasing:
        raise ValueError('Sequence bars must be unique and ordered')
    if 'contract' in frame and (frame.contract.isna().any() or frame.contract.nunique() != 1):
        raise ValueError('Object-linked sequences require one known contract')
    required = {f'{side}_{name}' for side in ('bullish', 'bearish')
                for name in ('core_sequence', 'core_sequence_completed',
                             'displacement_structure_break_event', 'fvg_created')}
    if required - set(frame):
        raise ValueError(f'Missing sequence inputs: {sorted(required - set(frame))}')
    if any(not pd.api.types.is_bool_dtype(frame[c]) or frame[c].isna().any() for c in required):
        raise ValueError('Sequence inputs must be non-null booleans')
    objects = tracked_fvgs.copy()
    if not objects.empty:
        cols = {'fvg_id', 'direction', 'creation_time', 'retest_hold_time'}
        if cols - set(objects):
            raise ValueError('Tracked FVG identity and event times are required')
        if objects.fvg_id.isna().any() or objects.fvg_id.duplicated().any():
            raise ValueError('Tracked FVG IDs must be unique and non-null')
        objects['fvg_id'] = objects.fvg_id.astype(str)
        if objects.fvg_id.duplicated().any():
            raise ValueError('Tracked FVG IDs must have unique canonical identities')
        if not objects.direction.isin(['bullish', 'bearish']).all():
            raise ValueError('Invalid FVG direction')
        objects['creation_time'] = _times(objects.creation_time)
        objects['retest_hold_time'] = _times(objects.retest_hold_time, nullable=True)
        if (objects.retest_hold_time < objects.creation_time).any():
            raise ValueError('Retest cannot precede creation')
        if not objects.creation_time.isin(times).all():
            raise ValueError('Full creation history is required')
        if 'invalidation_time' in objects:
            objects['invalidation_time'] = _times(objects.invalidation_time, nullable=True)
        for side in ('bullish', 'bearish'):
            actual = set(objects.loc[objects.direction.eq(side), 'creation_time'])
            expected = set(times[frame[f'{side}_fvg_created'].to_numpy()])
            if actual != expected:
                raise ValueError('FVG objects must match bar creation events')
    elif any(frame[f'{side}_fvg_created'].any() for side in ('bullish', 'bearish')):
        raise ValueError('Missing tracked objects for created FVGs')

    result = frame.copy()
    result['linked_sequence_contract'] = CONTRACT
    for side in ('bullish', 'bearish'):
        creation = {}
        retests = {}
        for gap in objects.loc[objects.direction.eq(side)].to_dict('records') if not objects.empty else []:
            creation.setdefault(gap['creation_time'], []).append(gap)
            if pd.notna(gap['retest_hold_time']):
                retests.setdefault(gap['retest_hold_time'], []).append(gap)
        for family in ('reversal', 'continuation'):
            active = np.zeros(len(frame), dtype=bool)
            events = np.zeros(len(frame), dtype=bool)
            identities = [None] * len(frame)
            trigger = None
            eligible = {}
            confirmed = None
            trigger_column = (f'{side}_core_sequence_completed' if family == 'reversal'
                              else f'{side}_displacement_structure_break_event')
            for i, timestamp in enumerate(times):
                if bool(frame[trigger_column].iloc[i]):
                    trigger, eligible, confirmed = i, {}, None
                if trigger is not None and (i - trigger >= lookback_bars or
                        (family == 'reversal' and not bool(frame[f'{side}_core_sequence'].iloc[i]))):
                    trigger, eligible, confirmed = None, {}, None
                if trigger is None:
                    continue
                for gap in creation.get(timestamp, []):
                    eligible[str(gap['fvg_id'])] = gap
                if confirmed is None:
                    # Latest eligible creation wins simultaneous retest ties;
                    # identity is retained rather than an aggregate boolean.
                    matches = sorted(retests.get(timestamp, []),
                                     key=lambda g: (g['creation_time'], str(g['fvg_id'])), reverse=True)
                    for gap in matches:
                        key = str(gap['fvg_id'])
                        invalidation = gap.get('invalidation_time', pd.NaT)
                        if (key in eligible and gap['creation_time'] < timestamp and
                                (pd.isna(invalidation) or invalidation > timestamp)):
                            confirmed = f"{side}:{gap['creation_time'].isoformat()}:{key}"
                            events[i] = True
                            break
                if confirmed is not None:
                    active[i] = True
                    identities[i] = confirmed
            prefix = f'{side}_linked_{family}'
            result[f'{prefix}_sequence'] = active
            result[f'{prefix}_entry_valid_event'] = events
            result[f'{prefix}_fvg_id'] = identities
    return result


def apply_sequence_contract(frame, config):
    """Activate linked flags only for an explicitly selected execution contract."""
    if selected_contract(config) == LEGACY:
        return frame
    if ('linked_sequence_contract' not in frame or
            not frame.linked_sequence_contract.eq(CONTRACT).all()):
        raise ValueError('Object-linked execution requires versioned feature evidence')
    result = frame.copy()
    for side in ('bullish', 'bearish'):
        for family in ('reversal', 'continuation'):
            prefix = f'{side}_linked_{family}'
            for suffix in ('sequence', 'entry_valid_event'):
                name = f'{prefix}_{suffix}'
                if name not in frame or not pd.api.types.is_bool_dtype(frame[name]) or frame[name].isna().any():
                    raise ValueError(f'Object-linked execution requires boolean {name}')
                result[f'{side}_{family}_{suffix}'] = frame[name]
            identity = f'{prefix}_fvg_id'
            if identity not in frame or (frame[f'{prefix}_sequence'] & frame[identity].isna()).any():
                raise ValueError('Active linked confirmation requires FVG identity')
            if (frame[f'{prefix}_entry_valid_event'] & ~frame[f'{prefix}_sequence']).any():
                raise ValueError('Linked event requires an active sequence')
    return result
