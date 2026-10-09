# Backtest accounting contract

`gross_result_points` is the signed price difference between executed entry and
exit, per contract, **after entry and exit slippage**. `commission_cost` is
round-trip commission expressed in price points per contract. Net points equal
gross points minus commission; net R divides that value by initial stop distance.

`backtest.commission.per_contract_round_trip` covers one complete entry and exit
for one contract. `unit: points` is the legacy numeric interpretation, now
explicit in strategy.yaml. `unit: dollars` requires `market.point_value` (dollars
per price point per contract); cost points equal dollars / point value. The
symbol alone never determines currency conversion. A price point is the same
index move for NQ/MNQ; their dollar values differ. No commissions were enabled in
the frozen default EXP-001 run; its results remain valid under this correction.

`backtest.quantity` defaults to 1. Price-point results and R remain per contract;
quantity does not change R because position risk scales by the same quantity.
For quantities above 1 the ledger additionally records position gross, commission,
and net contract-points (per-contract values multiplied by quantity). Multiply
these totals by point value for dollars. Slippage is a price adjustment, never a
second commission deduction.

The baseline has one full exit; TP1–TP3 are touch observations, not partial fills.
It charges one round trip regardless of observations. Future partial exits need
separate entry and exit-side per-contract fees on actual filled quantities and
must avoid charging a full round trip for each partial exit. That execution
model is not implemented by this accounting fix. No existing enabled-cost
archive is regenerated without its original inputs and declared units.
