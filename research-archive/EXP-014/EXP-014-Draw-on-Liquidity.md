# EXP-014 — Draw on Liquidity

Diagnostic only.

## Coverage

- Feature matched: 1218 / 1218

## Trade alignment with DOL

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts |
|---|---:|---:|---:|---:|---:|---:|
| aligned | 1189 | 27.9% | 1.83 | 0.073 | 1.10 | 2173.75 |
| neutral/unknown | 28 | 21.4% | 0.86 | 0.049 | 1.04 | 24.00 |
| opposed | 1 | 0.0% | -25.25 | -1.010 | 0.00 | -25.25 |

## DOL target type

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts |
|---|---:|---:|---:|---:|---:|---:|
| <missing> | 28 | 21.4% | 0.86 | 0.049 | 1.04 | 24.00 |
| ash | 2 | 0.0% | -25.25 | -1.010 | 0.00 | -50.50 |
| asl | 1 | 0.0% | -25.25 | -1.010 | 0.00 | -25.25 |
| external_equal_high | 17 | 41.2% | 12.37 | 0.495 | 1.83 | 210.25 |
| external_equal_low | 19 | 26.3% | -4.97 | -0.199 | 0.73 | -94.50 |
| external_swing_high | 308 | 26.6% | 1.24 | 0.051 | 1.07 | 383.00 |
| external_swing_low | 244 | 23.4% | -1.22 | -0.047 | 0.94 | -297.00 |
| internal_equal_high | 47 | 27.7% | -1.42 | -0.061 | 0.92 | -66.75 |
| internal_equal_low | 54 | 37.0% | 14.22 | 0.567 | 1.91 | 767.75 |
| loh | 2 | 100.0% | 67.00 | 2.763 | ∞ | 134.00 |
| lol | 2 | 50.0% | 37.25 | 1.490 | 3.95 | 74.50 |
| onh | 32 | 31.2% | 5.05 | 0.201 | 1.29 | 161.75 |
| onl | 47 | 31.9% | 5.91 | 0.232 | 1.36 | 278.00 |
| pdh | 59 | 42.4% | 7.45 | 0.295 | 1.52 | 439.75 |
| pdl | 67 | 20.9% | -6.12 | -0.251 | 0.69 | -409.75 |
| pmh | 18 | 44.4% | 24.10 | 0.954 | 2.95 | 433.75 |
| pml | 22 | 9.1% | -16.76 | -0.670 | 0.27 | -368.75 |
| week_high | 146 | 30.1% | 2.38 | 0.094 | 1.14 | 347.50 |
| week_low | 103 | 26.2% | 2.24 | 0.090 | 1.12 | 230.75 |

## DOL target category

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts |
|---|---:|---:|---:|---:|---:|---:|
| <missing> | 28 | 21.4% | 0.86 | 0.049 | 1.04 | 24.00 |
| asia_high_low | 3 | 0.0% | -25.25 | -1.010 | 0.00 | -75.75 |
| equal_highs_lows | 137 | 32.8% | 5.96 | 0.237 | 1.36 | 816.75 |
| external_swings | 552 | 25.2% | 0.16 | 0.008 | 1.01 | 86.00 |
| loh_lol | 4 | 75.0% | 52.12 | 2.126 | 9.26 | 208.50 |
| onh_onl | 79 | 31.6% | 5.57 | 0.219 | 1.33 | 439.75 |
| pdh_pdl | 126 | 31.0% | 0.24 | 0.005 | 1.01 | 30.00 |
| pmh_pml | 40 | 25.0% | 1.62 | 0.061 | 1.09 | 65.00 |
| weekly_high_low | 249 | 28.5% | 2.32 | 0.092 | 1.13 | 578.25 |

## DOL confidence quartiles

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts |
|---|---:|---:|---:|---:|---:|---:|
| (-0.001, 0.469] | 378 | 25.9% | 1.35 | 0.052 | 1.07 | 508.50 |
| (0.469, 0.531] | 263 | 25.5% | -1.91 | -0.078 | 0.90 | -503.25 |
| (0.531, 0.625] | 302 | 30.1% | 4.64 | 0.190 | 1.27 | 1402.75 |
| (0.625, 0.969] | 275 | 29.8% | 2.78 | 0.110 | 1.16 | 764.50 |

## Distance to primary DOL target quartiles

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts |
|---|---:|---:|---:|---:|---:|---:|
| (24.999, 37.75] | 302 | 30.1% | 2.47 | 0.099 | 1.14 | 747.00 |
| (37.75, 57.25] | 294 | 27.9% | 1.28 | 0.053 | 1.07 | 377.25 |
| (57.25, 93.5] | 298 | 25.8% | -0.16 | -0.008 | 0.99 | -49.00 |
| (93.5, 1124.0] | 296 | 27.7% | 3.63 | 0.143 | 1.20 | 1073.25 |

## Setup-family diagnostics

### reversal

#### alignment

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts |
|---|---:|---:|---:|---:|---:|---:|
| aligned | 1009 | 27.3% | 0.94 | 0.038 | 1.05 | 951.25 |
| neutral/unknown | 24 | 25.0% | 5.21 | 0.226 | 1.28 | 125.00 |

#### target_category

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts |
|---|---:|---:|---:|---:|---:|---:|
| <missing> | 24 | 25.0% | 5.21 | 0.226 | 1.28 | 125.00 |
| asia_high_low | 1 | 0.0% | -25.25 | -1.010 | 0.00 | -25.25 |
| equal_highs_lows | 103 | 31.1% | 5.50 | 0.219 | 1.32 | 567.00 |
| external_swings | 521 | 24.6% | -0.55 | -0.021 | 0.97 | -287.25 |
| loh_lol | 3 | 66.7% | 36.25 | 1.505 | 5.31 | 108.75 |
| onh_onl | 73 | 31.5% | 5.46 | 0.215 | 1.33 | 398.50 |
| pdh_pdl | 75 | 34.7% | -0.78 | -0.036 | 0.95 | -58.50 |
| pmh_pml | 37 | 27.0% | 3.80 | 0.148 | 1.22 | 140.75 |
| weekly_high_low | 196 | 27.6% | 0.55 | 0.022 | 1.03 | 107.25 |

### continuation

#### alignment

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts |
|---|---:|---:|---:|---:|---:|---:|
| aligned | 180 | 31.7% | 6.79 | 0.269 | 1.40 | 1222.50 |
| neutral/unknown | 4 | 0.0% | -25.25 | -1.010 | 0.00 | -101.00 |
| opposed | 1 | 0.0% | -25.25 | -1.010 | 0.00 | -25.25 |

#### target_category

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts |
|---|---:|---:|---:|---:|---:|---:|
| <missing> | 4 | 0.0% | -25.25 | -1.010 | 0.00 | -101.00 |
| asia_high_low | 2 | 0.0% | -25.25 | -1.010 | 0.00 | -50.50 |
| equal_highs_lows | 34 | 38.2% | 7.35 | 0.289 | 1.48 | 249.75 |
| external_swings | 31 | 35.5% | 12.04 | 0.482 | 1.74 | 373.25 |
| loh_lol | 1 | 100.0% | 99.75 | 3.990 | ∞ | 99.75 |
| onh_onl | 6 | 33.3% | 6.88 | 0.275 | 1.41 | 41.25 |
| pdh_pdl | 51 | 25.5% | 1.74 | 0.065 | 1.09 | 88.50 |
| pmh_pml | 3 | 0.0% | -25.25 | -1.010 | 0.00 | -75.75 |
| weekly_high_low | 53 | 32.1% | 8.89 | 0.353 | 1.52 | 471.00 |

## Year diagnostics

### 2023

#### alignment

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts |
|---|---:|---:|---:|---:|---:|---:|
| aligned | 335 | 32.2% | 2.55 | 0.101 | 1.15 | 854.50 |
| neutral/unknown | 8 | 37.5% | 21.72 | 0.920 | 2.38 | 173.75 |
| opposed | 1 | 0.0% | -25.25 | -1.010 | 0.00 | -25.25 |

#### target_category

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts |
|---|---:|---:|---:|---:|---:|---:|
| <missing> | 8 | 37.5% | 21.72 | 0.920 | 2.38 | 173.75 |
| equal_highs_lows | 48 | 35.4% | 7.01 | 0.278 | 1.44 | 336.50 |
| external_swings | 163 | 30.1% | 1.43 | 0.060 | 1.08 | 233.00 |
| loh_lol | 1 | 100.0% | 67.00 | 2.763 | ∞ | 67.00 |
| onh_onl | 19 | 36.8% | 7.74 | 0.308 | 1.49 | 147.00 |
| pdh_pdl | 39 | 35.9% | -1.22 | -0.055 | 0.92 | -47.50 |
| pmh_pml | 7 | 14.3% | -16.43 | -0.657 | 0.24 | -115.00 |
| weekly_high_low | 59 | 32.2% | 3.53 | 0.136 | 1.21 | 208.25 |

### 2024

#### alignment

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts |
|---|---:|---:|---:|---:|---:|---:|
| aligned | 378 | 28.0% | 0.84 | 0.034 | 1.05 | 318.75 |
| neutral/unknown | 10 | 0.0% | -25.25 | -1.010 | 0.00 | -252.50 |

#### target_category

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts |
|---|---:|---:|---:|---:|---:|---:|
| <missing> | 10 | 0.0% | -25.25 | -1.010 | 0.00 | -252.50 |
| asia_high_low | 1 | 0.0% | -25.25 | -1.010 | 0.00 | -25.25 |
| equal_highs_lows | 44 | 31.8% | 2.61 | 0.102 | 1.16 | 115.00 |
| external_swings | 173 | 21.4% | -3.53 | -0.139 | 0.82 | -610.75 |
| loh_lol | 1 | 100.0% | 67.00 | 2.763 | ∞ | 67.00 |
| onh_onl | 25 | 36.0% | 3.18 | 0.121 | 1.21 | 79.50 |
| pdh_pdl | 46 | 30.4% | -2.08 | -0.088 | 0.88 | -95.75 |
| pmh_pml | 11 | 27.3% | 2.43 | 0.097 | 1.13 | 26.75 |
| weekly_high_low | 77 | 36.4% | 9.90 | 0.399 | 1.62 | 762.25 |

### 2025

#### alignment

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts |
|---|---:|---:|---:|---:|---:|---:|
| aligned | 476 | 24.8% | 2.10 | 0.083 | 1.11 | 1000.50 |
| neutral/unknown | 10 | 30.0% | 10.28 | 0.411 | 1.58 | 102.75 |

#### target_category

| Segment | Trades | Win | Exp pts | Exp R | PF | Net pts |
|---|---:|---:|---:|---:|---:|---:|
| <missing> | 10 | 30.0% | 10.28 | 0.411 | 1.58 | 102.75 |
| asia_high_low | 2 | 0.0% | -25.25 | -1.010 | 0.00 | -50.50 |
| equal_highs_lows | 45 | 31.1% | 8.12 | 0.325 | 1.47 | 365.25 |
| external_swings | 216 | 24.5% | 2.15 | 0.086 | 1.11 | 463.75 |
| loh_lol | 2 | 50.0% | 37.25 | 1.490 | 3.95 | 74.50 |
| onh_onl | 35 | 25.7% | 6.09 | 0.242 | 1.33 | 213.25 |
| pdh_pdl | 41 | 26.8% | 4.23 | 0.165 | 1.23 | 173.25 |
| pmh_pml | 22 | 27.3% | 6.97 | 0.271 | 1.41 | 153.25 |
| weekly_high_low | 113 | 21.2% | -3.47 | -0.140 | 0.82 | -392.25 |

## Limitations

- Existing baseline trades only.
- Opposed-DOL baseline sample may be extremely small because DOL already participates in scoring/selection.
- Target cleanliness/untouched status is reported only if encoded by target type/category; no new classification is invented.
- No strategy change is authorized.

## Decision discipline

**Diagnostic only — no strategy change.**