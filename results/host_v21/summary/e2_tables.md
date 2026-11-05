**E2: ramp-rate stress (5 runs per rate, 134 TFTs, nominal die, mode G).** Stress = max(|V_GS|, |V_GD|), limit 3.5 V.

| Rate (× C2) | Ramp (µs) / slope (V/µs) | Segment | TFTs > 3.5 V | Worst TFT: max \|V_GS\| / \|V_GD\| (V), at (µs) | Margin (V) | Crossbar peak (V) | Most negative internal node (V) | Outcomes vs 1× |
|---|---|---|---|---|---|---|---|---|
| 0.1× | 100 / 0.033 | power-up + classification | 0 | XWR: 3.300 / 3.118, 100.00 | 0.200 | 3.009 (X1, 100.00 µs) | -2.062 (nb1, 0.00 µs) | 5/5 same, race shift ≤ 0.40 µs |
| 0.1× | 100 / 0.033 | power-down + 1 s off | 0 | X69: 2.119 / 3.300, 0.00 | 0.200 | 1.653 (X1, 0.51 µs) | -2.214 (nb1, 102.19 µs) |  |
| 0.3× | 33.3 / 0.099 | power-up + classification | 0 | X84: 3.330 / 0.000, 50.90 | 0.170 | 3.021 (X1, 33.33 µs) | -2.048 (nb1, 0.00 µs) | 5/5 same, race shift ≤ 0.39 µs |
| 0.3× | 33.3 / 0.099 | power-down + 1 s off | 0 | X69: 2.119 / 3.300, 0.00 | 0.200 | 1.891 (X8, 34.33 µs) | -2.201 (nb1, 35.06 µs) |  |
| 1× | 10 / 0.33 | power-up + classification | 0 | XNP1: 3.300 / 3.286, 10.00 | 0.200 | 3.033 (X1, 10.00 µs) | -2.042 (nb1, 0.00 µs) | 5/5 same, race shift ≤ 0.00 µs |
| 1× | 10 / 0.33 | power-down + 1 s off | 0 | X69: 2.119 / 3.300, 0.00 | 0.200 | 2.021 (X8, 11.00 µs) | -2.197 (nb1, 14.97 µs) |  |
| 3× | 3.33 / 0.99 | power-up + classification | 0 | XWR: 3.300 / 3.374, 3.68 | 0.126 | 3.041 (X13, 3.33 µs) | -2.040 (nb1, 0.00 µs) | 5/5 same, race shift ≤ 0.14 µs |
| 3× | 3.33 / 0.99 | power-down + 1 s off | 0 | X69: 2.120 / 3.300, 0.00 | 0.200 | 2.078 (X8, 4.33 µs) | -2.196 (nb1, 7.28 µs) |  |
| 10× | 1 / 3.3 | power-up + classification | 0 | XWR: 3.300 / 3.436, 1.29 | 0.064 | 3.048 (X8, 1.00 µs) | -2.039 (nb1, 0.00 µs) | 5/5 same, race shift ≤ 0.17 µs |
| 10× | 1 / 3.3 | power-down + 1 s off | 0 | X69: 2.120 / 3.300, 0.00 | 0.200 | 2.111 (X8, 2.00 µs) | -2.195 (nb1, 5.93 µs) |  |
