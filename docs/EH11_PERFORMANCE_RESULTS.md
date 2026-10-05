# EH-11 Performance Evaluation

Commit: `87f4e6f11f9d4fedab00f8741fb0db11fd77d73d`  
Captured: `2026-10-05T19:44:35.958538+00:00`

## Environment

- CPU: `AMD EPYC 7763 64-Core Processor`
- Logical CPUs: `4`
- Platform: `Linux-6.17.0-1022-azure-x86_64-with-glibc2.39`
- Python: `3.12.14 (main, Aug 13 2026, 02:47:42) [GCC 13.3.0]`
- OR-Tools: `9.15.6755`

## Yield

- Attempted: **540**; excluded: **40**; runnable: **500**
- Generated: **126** (25.2%)
- Strict accepted: **126** (25.2%)
- Released: **126** (25.2%)
- Outcomes: `{'success': 126, 'no_solution': 374, 'excluded': 40}`
- Solver statuses: `{'OPTIMAL': 75, 'FEASIBLE': 51, 'UNKNOWN': 364, 'NOT_RUN': 40, 'INFEASIBLE': 10}`

## Multi-output throughput

- Cases: **18**
- Requested solutions: **54**
- Generated solutions: **9**

## Scaling and variance

| Profile | Bars | Mode | n run | n success | Attempt median s | Attempt p90 s | Attempt CV | Success median s | RSS median MiB | Cert median s | Cert/gen |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| applied_harmony | 1 | single | 5 | 5 | 0.2558 | 0.2569 | 0.015 | 0.2138 | 110.7 | 0.0227 | 0.106 |
| applied_harmony | 1 | throughput | 5 | 5 | 0.2492 | 0.2531 | 0.015 | 0.2068 | 114.3 | 0.0226 | 0.110 |
| applied_harmony | 2 | single | 5 | 1 | 2.1682 | 2.2006 | 0.011 | 2.1731 | 142.8 | 0.0261 | 0.012 |
| applied_harmony | 2 | throughput | 5 | 5 | 2.2283 | 2.2301 | 0.001 | 2.1797 | 185.7 | 0.0259 | 0.012 |
| applied_harmony | 4 | single | 5 | 0 | 2.1468 | 2.1575 | 0.003 | n/a | 187.3 | n/a | n/a |
| applied_harmony | 4 | throughput | 5 | 0 | 2.1513 | 2.1576 | 0.002 | n/a | 188.3 | n/a | n/a |
| applied_harmony | 8 | single | 5 | 0 | 2.0108 | 2.3333 | 0.113 | n/a | 263.8 | n/a | n/a |
| applied_harmony | 8 | throughput | 5 | 0 | 2.0050 | 2.0091 | 0.002 | n/a | 262.7 | n/a | n/a |
| applied_harmony | 16 | single | 5 | 0 | 3.1721 | 3.1773 | 0.001 | n/a | 445.7 | n/a | n/a |
| applied_harmony | 16 | throughput | 5 | 0 | 3.1810 | 3.1919 | 0.003 | n/a | 445.3 | n/a | n/a |
| applied_harmony | 32 | single | 5 | 0 | 4.4191 | 4.4250 | 0.003 | n/a | 545.9 | n/a | n/a |
| applied_harmony | 32 | throughput | 5 | 0 | 4.4048 | 4.4092 | 0.001 | n/a | 544.1 | n/a | n/a |
| base_satb | 1 | single | 5 | 5 | 0.2519 | 0.2659 | 0.120 | 0.2138 | 105.4 | 0.0206 | 0.096 |
| base_satb | 1 | throughput | 5 | 5 | 0.1936 | 0.2868 | 0.222 | 0.1554 | 111.1 | 0.0205 | 0.132 |
| base_satb | 2 | single | 5 | 5 | 1.9981 | 2.0391 | 0.020 | 1.9526 | 121.6 | 0.0236 | 0.012 |
| base_satb | 2 | throughput | 5 | 5 | 2.1274 | 2.1381 | 0.004 | 2.0824 | 156.3 | 0.0236 | 0.011 |
| base_satb | 4 | single | 5 | 1 | 2.1302 | 2.1690 | 0.013 | 2.1367 | 150.5 | 0.0304 | 0.014 |
| base_satb | 4 | throughput | 5 | 5 | 2.2036 | 2.2045 | 0.001 | 2.1457 | 210.5 | 0.0304 | 0.014 |
| base_satb | 8 | single | 5 | 0 | 1.9352 | 1.9434 | 0.003 | n/a | 184.9 | n/a | n/a |
| base_satb | 8 | throughput | 5 | 0 | 1.9367 | 1.9404 | 0.003 | n/a | 185.7 | n/a | n/a |
| base_satb | 16 | single | 5 | 0 | 2.4315 | 2.4362 | 0.006 | n/a | 272.0 | n/a | n/a |
| base_satb | 16 | throughput | 5 | 0 | 2.4253 | 2.4477 | 0.007 | n/a | 271.7 | n/a | n/a |
| base_satb | 32 | single | 5 | 0 | 2.8481 | 2.8836 | 0.007 | n/a | 394.4 | n/a | n/a |
| base_satb | 32 | throughput | 5 | 0 | 2.8648 | 2.8806 | 0.005 | n/a | 397.3 | n/a | n/a |
| borrowed_harmony | 1 | single | 5 | 5 | 0.3043 | 0.3224 | 0.096 | 0.2640 | 106.8 | 0.0212 | 0.081 |
| borrowed_harmony | 1 | throughput | 5 | 5 | 0.2395 | 0.2437 | 0.015 | 0.1991 | 112.8 | 0.0213 | 0.106 |
| borrowed_harmony | 2 | single | 5 | 5 | 2.1409 | 2.1427 | 0.001 | 2.0939 | 124.6 | 0.0245 | 0.012 |
| borrowed_harmony | 2 | throughput | 5 | 5 | 2.1465 | 2.1486 | 0.001 | 2.0980 | 160.6 | 0.0258 | 0.012 |
| borrowed_harmony | 4 | single | 5 | 0 | 2.1445 | 2.1612 | 0.006 | n/a | 158.1 | n/a | n/a |
| borrowed_harmony | 4 | throughput | 5 | 0 | 2.1533 | 2.1548 | 0.001 | n/a | 208.5 | n/a | n/a |
| borrowed_harmony | 8 | single | 5 | 0 | 2.2211 | 2.2271 | 0.002 | n/a | 203.6 | n/a | n/a |
| borrowed_harmony | 8 | throughput | 5 | 0 | 2.2186 | 2.2366 | 0.006 | n/a | 203.5 | n/a | n/a |
| borrowed_harmony | 16 | single | 5 | 0 | 1.8897 | 1.8949 | 0.005 | n/a | 275.2 | n/a | n/a |
| borrowed_harmony | 16 | throughput | 5 | 0 | 1.8845 | 1.8938 | 0.004 | n/a | 274.9 | n/a | n/a |
| borrowed_harmony | 32 | single | 5 | 0 | 3.0507 | 3.0587 | 0.002 | n/a | 445.8 | n/a | n/a |
| borrowed_harmony | 32 | throughput | 5 | 0 | 3.0477 | 3.0651 | 0.003 | n/a | 446.5 | n/a | n/a |
| combined_borrowed_modulation | 1 | single | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| combined_borrowed_modulation | 1 | throughput | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| combined_borrowed_modulation | 2 | single | 5 | 5 | 1.6132 | 1.6514 | 0.021 | 1.5624 | 122.4 | 0.0269 | 0.017 |
| combined_borrowed_modulation | 2 | throughput | 5 | 5 | 1.6289 | 1.6984 | 0.093 | 1.5762 | 149.5 | 0.0269 | 0.017 |
| combined_borrowed_modulation | 4 | single | 5 | 0 | 2.3144 | 2.3161 | 0.002 | n/a | 144.2 | n/a | n/a |
| combined_borrowed_modulation | 4 | throughput | 5 | 0 | 2.3075 | 2.3112 | 0.002 | n/a | 144.5 | n/a | n/a |
| combined_borrowed_modulation | 8 | single | 5 | 0 | 2.3557 | 2.3998 | 0.014 | n/a | 194.9 | n/a | n/a |
| combined_borrowed_modulation | 8 | throughput | 5 | 0 | 2.3542 | 2.3646 | 0.003 | n/a | 195.6 | n/a | n/a |
| combined_borrowed_modulation | 16 | single | 5 | 0 | 3.3393 | 3.3553 | 0.003 | n/a | 297.5 | n/a | n/a |
| combined_borrowed_modulation | 16 | throughput | 5 | 0 | 3.3309 | 3.3366 | 0.001 | n/a | 295.7 | n/a | n/a |
| combined_borrowed_modulation | 32 | single | 5 | 0 | 4.5548 | 4.5732 | 0.003 | n/a | 465.1 | n/a | n/a |
| combined_borrowed_modulation | 32 | throughput | 5 | 0 | 4.5685 | 4.5940 | 0.008 | n/a | 465.4 | n/a | n/a |
| declared_modulation | 1 | single | 5 | 5 | 0.1389 | 0.1419 | 0.027 | 0.1008 | 102.6 | 0.0200 | 0.199 |
| declared_modulation | 1 | throughput | 5 | 5 | 0.1340 | 0.1370 | 0.021 | 0.0961 | 106.4 | 0.0200 | 0.209 |
| declared_modulation | 2 | single | 5 | 5 | 0.8012 | 0.8217 | 0.018 | 0.7568 | 108.8 | 0.0238 | 0.031 |
| declared_modulation | 2 | throughput | 5 | 5 | 0.8817 | 0.8929 | 0.021 | 0.8369 | 126.6 | 0.0237 | 0.028 |
| declared_modulation | 4 | single | 5 | 5 | 2.1991 | 2.1991 | 0.000 | 2.1397 | 123.4 | 0.0315 | 0.015 |
| declared_modulation | 4 | throughput | 5 | 5 | 2.2083 | 2.2169 | 0.002 | 2.1494 | 173.0 | 0.0315 | 0.015 |
| declared_modulation | 8 | single | 5 | 0 | 2.0442 | 2.0503 | 0.004 | n/a | 135.2 | n/a | n/a |
| declared_modulation | 8 | throughput | 5 | 0 | 2.0430 | 2.0476 | 0.002 | n/a | 135.1 | n/a | n/a |
| declared_modulation | 16 | single | 5 | 0 | 2.2383 | 2.2546 | 0.005 | n/a | 167.6 | n/a | n/a |
| declared_modulation | 16 | throughput | 5 | 0 | 2.2427 | 2.2643 | 0.007 | n/a | 168.4 | n/a | n/a |
| declared_modulation | 32 | single | 5 | 0 | 2.9934 | 3.0017 | 0.002 | n/a | 237.6 | n/a | n/a |
| declared_modulation | 32 | throughput | 5 | 0 | 2.9917 | 2.9952 | 0.001 | n/a | 237.4 | n/a | n/a |
| expanded_sevenths | 1 | single | 5 | 5 | 0.3231 | 0.3603 | 0.079 | 0.2852 | 110.0 | 0.0200 | 0.070 |
| expanded_sevenths | 1 | throughput | 5 | 5 | 0.3166 | 0.3451 | 0.070 | 0.2785 | 123.8 | 0.0200 | 0.072 |
| expanded_sevenths | 2 | single | 5 | 1 | 2.1427 | 2.1708 | 0.010 | 2.1455 | 131.8 | 0.0233 | 0.011 |
| expanded_sevenths | 2 | throughput | 5 | 5 | 2.1946 | 2.1949 | 0.000 | 2.1506 | 168.9 | 0.0233 | 0.011 |
| expanded_sevenths | 4 | single | 5 | 0 | 2.2730 | 2.2735 | 0.001 | n/a | 167.5 | n/a | n/a |
| expanded_sevenths | 4 | throughput | 5 | 0 | 2.2720 | 2.2737 | 0.001 | n/a | 167.5 | n/a | n/a |
| expanded_sevenths | 8 | single | 5 | 0 | 2.5140 | 2.5159 | 0.002 | n/a | 235.4 | n/a | n/a |
| expanded_sevenths | 8 | throughput | 5 | 0 | 2.5171 | 2.5388 | 0.006 | n/a | 234.8 | n/a | n/a |
| expanded_sevenths | 16 | single | 5 | 0 | 2.5516 | 2.5563 | 0.003 | n/a | 344.7 | n/a | n/a |
| expanded_sevenths | 16 | throughput | 5 | 0 | 2.5563 | 2.5608 | 0.004 | n/a | 345.3 | n/a | n/a |
| expanded_sevenths | 32 | single | 5 | 0 | 3.9915 | 4.0120 | 0.004 | n/a | 589.7 | n/a | n/a |
| expanded_sevenths | 32 | throughput | 5 | 0 | 3.9918 | 4.0024 | 0.002 | n/a | 589.6 | n/a | n/a |
| phrase_grammar | 1 | single | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| phrase_grammar | 1 | throughput | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| phrase_grammar | 2 | single | 5 | 0 | 0.0793 | 0.0796 | 0.004 | n/a | 99.0 | n/a | n/a |
| phrase_grammar | 2 | throughput | 5 | 0 | 0.0790 | 0.0794 | 0.003 | n/a | 99.0 | n/a | n/a |
| phrase_grammar | 4 | single | 5 | 2 | 2.1199 | 2.1839 | 0.016 | 2.1250 | 140.6 | 0.0312 | 0.015 |
| phrase_grammar | 4 | throughput | 5 | 5 | 2.1947 | 2.1950 | 0.000 | 2.1351 | 193.0 | 0.0314 | 0.015 |
| phrase_grammar | 8 | single | 5 | 0 | 1.8398 | 1.8461 | 0.002 | n/a | 176.6 | n/a | n/a |
| phrase_grammar | 8 | throughput | 5 | 0 | 1.8398 | 1.8446 | 0.002 | n/a | 176.7 | n/a | n/a |
| phrase_grammar | 16 | single | 5 | 0 | 2.4550 | 2.4574 | 0.003 | n/a | 270.0 | n/a | n/a |
| phrase_grammar | 16 | throughput | 5 | 0 | 2.4488 | 2.4528 | 0.001 | n/a | 271.7 | n/a | n/a |
| phrase_grammar | 32 | single | 5 | 0 | 2.8727 | 2.8777 | 0.001 | n/a | 393.8 | n/a | n/a |
| phrase_grammar | 32 | throughput | 5 | 0 | 2.8731 | 2.8792 | 0.002 | n/a | 392.8 | n/a | n/a |
| rhythm_motifs | 1 | single | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| rhythm_motifs | 1 | throughput | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| rhythm_motifs | 2 | single | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| rhythm_motifs | 2 | throughput | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| rhythm_motifs | 4 | single | 5 | 0 | 2.1429 | 2.1436 | 0.000 | n/a | 153.5 | n/a | n/a |
| rhythm_motifs | 4 | throughput | 5 | 1 | 2.1514 | 2.2068 | 0.018 | 2.1800 | 209.1 | 0.0322 | 0.015 |
| rhythm_motifs | 8 | single | 5 | 0 | 2.3089 | 2.3094 | 0.000 | n/a | 199.6 | n/a | n/a |
| rhythm_motifs | 8 | throughput | 5 | 0 | 2.3103 | 2.3131 | 0.001 | n/a | 199.9 | n/a | n/a |
| rhythm_motifs | 16 | single | 5 | 0 | 1.9933 | 2.0146 | 0.007 | n/a | 288.1 | n/a | n/a |
| rhythm_motifs | 16 | throughput | 5 | 0 | 1.9952 | 2.0013 | 0.002 | n/a | 286.7 | n/a | n/a |
| rhythm_motifs | 32 | single | 5 | 0 | 3.2118 | 3.2131 | 0.004 | n/a | 465.0 | n/a | n/a |
| rhythm_motifs | 32 | throughput | 5 | 0 | 3.2001 | 3.2178 | 0.003 | n/a | 465.2 | n/a | n/a |
| secondary_harmony | 1 | single | 5 | 0 | 2.9391 | 2.9426 | 0.003 | n/a | 126.1 | n/a | n/a |
| secondary_harmony | 1 | throughput | 5 | 0 | 2.9317 | 2.9409 | 0.003 | n/a | 126.5 | n/a | n/a |
| secondary_harmony | 2 | single | 5 | 0 | 4.0557 | 4.0749 | 0.005 | n/a | 157.8 | n/a | n/a |
| secondary_harmony | 2 | throughput | 5 | 0 | 4.0559 | 4.0808 | 0.006 | n/a | 157.8 | n/a | n/a |
| secondary_harmony | 4 | single | 5 | 0 | 6.6346 | 6.6581 | 0.003 | n/a | 229.4 | n/a | n/a |
| secondary_harmony | 4 | throughput | 5 | 0 | 6.6318 | 6.6653 | 0.004 | n/a | 228.8 | n/a | n/a |
| secondary_harmony | 8 | single | 5 | 0 | 11.1610 | 11.1663 | 0.003 | n/a | 345.2 | n/a | n/a |
| secondary_harmony | 8 | throughput | 5 | 0 | 11.1213 | 11.1501 | 0.004 | n/a | 345.6 | n/a | n/a |
| secondary_harmony | 16 | single | 5 | 0 | 20.2376 | 20.2513 | 0.001 | n/a | 427.6 | n/a | n/a |
| secondary_harmony | 16 | throughput | 5 | 0 | 20.2595 | 20.3099 | 0.003 | n/a | 424.7 | n/a | n/a |
| secondary_harmony | 32 | single | 5 | 0 | 40.9943 | 41.2315 | 0.004 | n/a | 760.4 | n/a | n/a |
| secondary_harmony | 32 | throughput | 5 | 0 | 41.0871 | 41.2210 | 0.003 | n/a | 759.0 | n/a | n/a |

Raw rows preserve exclusions, UNKNOWN/no-solution outcomes, and crashes. 
These measurements apply only to the recorded commit/runner; optimization is outside EH-11.
