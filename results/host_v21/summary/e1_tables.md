**E1: lower-edge sweep, v2.1 vs v2 (N = 20 per point, µ ×1).** v2 = host_v2 C6/C6b runs (imported).

| \|V_th\| (V) | V̂ (err mV) | mode | **v2.1** correct / valid (failures) | v2 correct / valid (failures) | both / v2.1 only / v2 only / neither (McNemar p) | v2.1 median race (µs) | pre-trip timer count (µs) |
|---|---|---|---|---|---|---|---|
| 0.49 | 0.4936 (+3.6) FLAG | W | **0 / 0** (none_latched 4, timeout 16) | 0 / 0 (stuck_latched 20) | 0 / 0 / 0 / 20 (1) | 1544.867 | [0.0, 0.0] |
| 0.51 | 0.5131 (+3.0) | W | **15 / 20** | 0 / 0 (stuck_latched 20) | 0 / 15 / 0 / 5 (0.0001) | 1329.717 | [0.0, 0.0] |
| 0.53 | 0.5325 (+2.5) | W | **15 / 20** | 0 / 0 (stuck_latched 20) | 0 / 15 / 0 / 5 (0.0001) | 1294.847 | [0.0, 0.0] |
| 0.55 | 0.5518 (+1.8) | W | **15 / 20** | 0 / 0 (stuck_latched 20) | 0 / 15 / 0 / 5 (0.0001) | 1269.428 | [0.0, 0.0] |
| 0.57 | 0.5719 (+1.9) | W | **15 / 20** | 0 / 0 (none_latched 20) | 0 / 15 / 0 / 5 (0.0001) | 1231.102 | [0.0, 0.0] |
| 0.59 | 0.5940 (+4.0) | W | **15 / 20** | 15 / 20 | 15 / 0 / 0 / 5 (1) | 1170.556 | [0.0, 0.0] |
| 0.61 | 0.6064 (-3.6) | G | **15 / 20** | 15 / 20 | 15 / 0 / 0 / 5 (1) | 1753.993 | [2.028, 2.143] |

Pooled over the 7 points: v2.1 90/140, v2 30/140; paired both / v2.1 only / v2 only / neither 30 / 60 / 0 / 50 (exact McNemar p = 1.7e-18).

**Energy and standby per point** (medians over the runs; standby = mean power over the 1 s idle after each run).

| \|V_th\| (V) | mode | E per classification (nJ) | standby mean (µW), range | standby at 1 ms / 1 s (µW, ranges) | idle energy per 1 s (nJ) | per classification at 1 /s (nJ) |
|---|---|---|---|---|---|---|
| 0.49 | W | 1069.726 ([496.886, 1069.859]) | 209.2 ([209.152, 209.236]) | [210.862, 210.967] / [207.43, 207.506] | 209200.095 | 210266.38 |
| 0.51 | W | 467.594 ([385.783, 523.965]) | 192.116 ([192.081, 192.155]) | [193.117, 193.192] / [191.003, 191.077] | 192116.326 | 192577.528 |
| 0.53 | W | 449.928 ([370.027, 505.018]) | 187.669 ([187.637, 187.71]) | [188.246, 188.319] / [186.983, 187.055] | 187668.587 | 188113.751 |
| 0.55 | W | 434.434 ([356.085, 488.509]) | 183.082 ([183.056, 183.124]) | [183.391, 183.458] / [182.672, 182.739] | 183082.453 | 183510.867 |
| 0.57 | W | 416.786 ([340.326, 469.617]) | 178.408 ([178.382, 178.447]) | [178.547, 178.612] / [178.164, 178.23] | 178407.715 | 178816.902 |
| 0.59 | W | 395.447 ([321.52, 446.612]) | 173.668 ([173.643, 173.709]) | [173.711, 173.776] / [173.52, 173.586] | 173668.422 | 174055.275 |
| 0.61 | G | 646.302 ([548.092, 713.687]) | -0.001 ([-0.001, -0.001]) | [0.0, 0.0] / [0.0, 0.0] | -0.707 | 646.302 |

**Forced mode W at 0.61 V** (P3.2): V̂ 0.6064 V, flag False; **15 / 20** (); vs the v2.1 (mode G) runs at the same point: both / W only / G only / neither 15 / 0 / 0 / 5 (p = 1), same outcome 20/20; median race 1217.06 µs; standby mean 169.06 µW ([169.034, 169.101]).

**Mode-W chain at 0.51 V** (P3.3, 20 steps, 1 s VDD-on idle between): 14 / 19 (multi_latched 1); same outcome as the independent runs 19/20; race shift [0.0, 19.0] µs; changed: [{'step': 6, 'idx': 31, 'chain': 'multi_latched', 'independent': 2}].
