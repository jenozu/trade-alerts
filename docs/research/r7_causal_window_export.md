# R7 next read-only VPS evidence

Run this from `/root/trade-alerts-verify-YwIqEc/repo`. It uses the separate
verification venv, reads the existing chronology files and prints two small
causal windows. It does not rebuild data, run an experiment, write files, change
configuration or restart services. Paste the text between the markers back into
the conversation. If it fails, paste the error; do not launch a yearly rerun.

```bash
cd /root/trade-alerts-verify-YwIqEc/repo
../venv/bin/python - <<'PY'
import base64, gzip, json
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq

manifest = Path('/root/trade-alerts-verify-YwIqEc/replays/isolated-2023-xgi4yfiw/chronology/LINKED_SEQUENCE_SUMMARY.json')
summary = json.loads(manifest.read_text())
ends = [pd.Timestamp('2023-01-03T14:34:00Z'), pd.Timestamp('2023-08-24T13:45:00Z')]
windows = [(end - pd.Timedelta(minutes=30), end) for end in ends]
base = {'timestamp', 'contract', 'open', 'high', 'low', 'close', 'volume',
        'bar_complete', 'is_complete', 'available_at', 'new_entry_allowed',
        'is_strategy_window', 'long_candidate', 'short_candidate',
        'long_raw_score', 'short_raw_score', 'linked_sequence_contract',
        'active_internal_swing_high', 'active_internal_swing_low'}
parts = []
for segment in summary['segments']:
    path = Path(segment['features_path'])
    if not path.is_absolute():
        path = manifest.parent / path
    names = pq.read_schema(path).names
    columns = [name for name in names if name in base or any(
        word in name for word in ('linked_', 'core_sequence', 'liquidity_sweep',
                                 'sweep_event', 'sweep_source', 'recent_buy_side_sweep',
                                 'recent_sell_side_sweep', 'displacement', 'mss',
                                 'structure_close_break', 'structure_break_event',
                                 'fvg_created', 'fvg_retest', 'fvg_first_touch',
                                 'nearest_active_bullish_fvg', 'nearest_active_bearish_fvg'))]
    filters = [[('timestamp', '>=', start.to_pydatetime()),
                ('timestamp', '<=', end.to_pydatetime())] for start, end in windows]
    frame = pd.read_parquet(path, columns=columns, filters=filters)
    if not frame.empty:
        frame['timestamp'] = pd.to_datetime(frame['timestamp'], utc=True)
        parts.append(frame)
assert parts, 'No rows found in the existing feature files'
frame = pd.concat(parts, ignore_index=True).sort_values(['timestamp', 'contract'])
assert not frame.duplicated(['timestamp', 'contract']).any(), 'Duplicate window rows'
for end in ends:
    assert (frame['timestamp'] == end).sum() == 1, f'Missing candidate at {end}'
assert 2 <= len(frame) <= 62, f'Unexpected window size: {len(frame)}'
payload = frame.to_json(orient='records', date_format='iso').encode()
print('Window rows:', len(frame))
print('BEGIN_R7_CAUSAL_WINDOWS')
print(base64.b64encode(gzip.compress(payload, mtime=0)).decode())
print('END_R7_CAUSAL_WINDOWS')
PY
```

The windows include noncandidate bars. Gaps are retained, not filled. Thirty
preceding minutes allow inspection of the ten-bar sequence windows; they do not
guarantee that every older active FVG's complete lifecycle is included. Further
evidence is requested only if the sampled event history requires it.
