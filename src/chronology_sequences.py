"""Opt-in completed-bar chronology layered on preserved FVG object evidence."""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

from linked_sequences import CHRONOLOGY, _times, add_linked_sequences


def add_chronology_sequences(frame, objects, *, lookback_bars=10, break_buffer_points=.25):
    """Earlier sweep -> displacement/MSS -> own FVG retest; or
    break -> later hold -> own retest -> later close through a frozen swing.

    These are explicit conservative choices, not inferred intraminute ordering.
    All original columns and the older contracts remain unchanged.
    """
    if isinstance(break_buffer_points, bool) or not math.isfinite(break_buffer_points) or break_buffer_points < 0:
        raise ValueError('Break buffer must be finite and non-negative')
    required = {'close', 'available_at', 'bar_complete', 'sell_side_liquidity_sweep',
                'buy_side_liquidity_sweep', 'active_internal_swing_high', 'active_internal_swing_low'}
    required |= {f'{side}_{name}' for side in ('bullish', 'bearish') for name in ('displacement', 'mss')}
    if required - set(frame):
        raise ValueError(f'Missing chronology inputs: {sorted(required - set(frame))}')
    bools = required - {'close', 'available_at', 'active_internal_swing_high', 'active_internal_swing_low'}
    if any(not pd.api.types.is_bool_dtype(frame[c]) or frame[c].isna().any() for c in bools):
        raise ValueError('Chronology events must be non-null booleans')
    times = _times(frame.timestamp)
    availability = _times(frame.available_at)
    nanoseconds = times.as_unit('ns').asi8
    if not np.array_equal(availability.as_unit('ns').asi8, nanoseconds + 60_000_000_000):
        raise ValueError('Chronology requires start-labelled one-minute availability')
    if not np.isfinite(frame.close.to_numpy(dtype=float)).all():
        raise ValueError('Chronology close prices must be finite')
    modified = frame.copy()
    complete = frame.bar_complete.to_numpy()
    for side, sweep_side in (('bullish', 'sell'), ('bearish', 'buy')):
        sweep = displacement = None
        active = np.zeros(len(frame), dtype=bool)
        events = np.zeros(len(frame), dtype=bool)
        done = False
        for i in range(len(frame)):
            if i and nanoseconds[i] - nanoseconds[i-1] != 60_000_000_000:
                sweep = displacement = None
                done = False
            if not complete[i]:
                sweep = displacement = None
                done = False
                continue
            if bool(frame[f'{sweep_side}_side_liquidity_sweep'].iloc[i]):
                sweep, displacement, done = i, None, False
            if sweep is not None and i - sweep >= lookback_bars:
                sweep = displacement = None
                done = False
            if (sweep is not None and i > sweep and displacement is None
                    and bool(frame[f'{side}_displacement'].iloc[i])):
                displacement = i
            if displacement is not None and not done and bool(frame[f'{side}_mss'].iloc[i]):
                done = True
                events[i] = True
            active[i] = done
        modified[f'{side}_core_sequence'] = active
        modified[f'{side}_core_sequence_completed'] = events
        # An incomplete break never starts a continuation.
        modified[f'{side}_displacement_structure_break_event'] &= complete
    result = add_linked_sequences(modified, objects, lookback_bars=lookback_bars)
    # Restore even the inherited core columns byte-for-byte.
    for name in frame:
        result[name] = frame[name]
    result['linked_sequence_contract'] = CHRONOLOGY
    invalidations = {}
    for gap in objects.to_dict('records') if not objects.empty else []:
        created = pd.Timestamp(gap['creation_time']).tz_convert('UTC')
        identity = f"{gap['direction']}:{created.isoformat()}:{gap['fvg_id']}"
        value = gap.get('invalidation_time', pd.NaT)
        invalidations[identity] = pd.NaT if pd.isna(value) else pd.Timestamp(value)
    for side, sign, level_column in (('bullish', 1, 'active_internal_swing_high'),
                                     ('bearish', -1, 'active_internal_swing_low')):
        prefix = f'{side}_linked_continuation'
        linked_events = result[f'{prefix}_entry_valid_event'].to_numpy().copy()
        linked_ids = result[f'{prefix}_fvg_id'].tolist()
        active = np.zeros(len(frame), dtype=bool)
        events = np.zeros(len(frame), dtype=bool)
        identities = [None] * len(frame)
        hold_times, retest_times, micro_levels = [None]*len(frame), [None]*len(frame), [np.nan]*len(frame)
        trigger = hold = retest = None
        broken = micro = np.nan
        identity = None
        done = False
        for i, timestamp in enumerate(times):
            close = float(frame.close.iloc[i])
            if i and nanoseconds[i] - nanoseconds[i-1] != 60_000_000_000:
                trigger, hold, retest, identity, done = None, None, None, None, False
            if bool(modified[f'{side}_displacement_structure_break_event'].iloc[i]):
                trigger, hold, retest, identity, done = i, None, None, None, False
                broken = float(frame[level_column].iloc[i])
                micro = np.nan
                if not np.isfinite(broken) or sign * (close - broken) <= break_buffer_points:
                    trigger = None
            if trigger is None:
                continue
            invalidation = invalidations.get(identity, pd.NaT)
            if (not complete[i] or i - trigger >= lookback_bars or
                    sign * (close - broken) <= 0 or
                    (pd.notna(invalidation) and invalidation <= timestamp)):
                trigger, hold, retest, identity, done = None, None, None, None, False
                continue
            # Acceptance is a distinct completed close beyond the original
            # broken swing, before the retest; no tuned dwell-time threshold.
            if hold is None and trigger < i and sign * (close - broken) > break_buffer_points:
                hold = i
            if linked_events[i] and hold is not None and hold < i:
                candidate_level = float(frame[level_column].iloc[i])
                # Already beyond that swing on the retest bar is unproven
                # post-retest ordering, so it cannot count as a later BOS.
                if np.isfinite(candidate_level) and sign * (close - candidate_level) <= break_buffer_points:
                    retest, micro, identity = i, candidate_level, linked_ids[i]
            if (retest is not None and i > retest and not done
                    and sign * (close - micro) > break_buffer_points):
                done = True
                events[i] = True
            if done:
                active[i], identities[i] = True, identity
                hold_times[i], retest_times[i], micro_levels[i] = times[hold].isoformat(), times[retest].isoformat(), micro
        result[f'{prefix}_sequence'] = active
        result[f'{prefix}_entry_valid_event'] = events
        result[f'{prefix}_fvg_id'] = identities
        result[f'{prefix}_acceptance_time'] = hold_times
        result[f'{prefix}_retest_time'] = retest_times
        result[f'{prefix}_micro_bos_level'] = micro_levels
    # Incomplete retests do not confirm reversal either.
    for side in ('bullish', 'bearish'):
        prefix = f'{side}_linked_reversal'
        result[f'{prefix}_entry_valid_event'] &= complete
        result[f'{prefix}_sequence'] &= complete
        for i, identity in enumerate(result[f'{prefix}_fvg_id']):
            invalidation = invalidations.get(identity, pd.NaT)
            if pd.notna(invalidation) and invalidation <= times[i]:
                result.loc[result.index[i], f'{prefix}_sequence'] = False
                result.loc[result.index[i], f'{prefix}_entry_valid_event'] = False
                result.loc[result.index[i], f'{prefix}_fvg_id'] = None
    return result
