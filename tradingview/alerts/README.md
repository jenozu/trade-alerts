# Research telemetry, not trade execution

The indicator file tradingview/indicators/nq_market_intelligence_v1.pine has a **JSON snapshot cadence** input (Off / 1m / 5m). It defaults to Off.

The indicator must be added to a 1-minute futures chart, the cadence changed, and a TradingView alert created with **Any alert() function call**. The alert webhook URL should point to an authenticated HTTPS endpoint on the VPS *when that receiver is actually deployed*. Pine cannot create a running alert by itself.

Payload identifier: nq.mi.snapshot.v1.
- time_close_ms is the completed candle's UNIX epoch timestamp in milliseconds.
- OHLCV, PDH/PDL, PMH/PML, London H/L, VWAP, 1m SNR quality and rolling RVOL are numerical or null.
- buy_side_sweep / sell_side_sweep, swing break, FVG creation / hold / invalidation and in_entry_window are booleans.
- mode is always research_only and is not an execution authorization.
- Nulls mean insufficient candles or unavailable data; do not interpret as zero.
- The endpoint must validate schema, deduplicate on symbol + timeframe + time_close_ms, reject stale/malformed data, track gaps and store both payload and ingestion time.
- Do NOT insert secrets or broker credentials in Pine messages. TradingView webhook endpoint security, deployment, rate handling and failure recovery are separate milestones.
- A 1m/5m webhook stream is not historical data backfill; retain the existing Python historical pipeline and cross-check feeds/contract roll adjustments.

No webhook receiver or TradingView alert has been deployed or activated yet. Never interpret these event flags as a validated entry, stop, TP or trade instruction.
