# EH-11 Performance Evaluation

Commit: `4164c86dd69d5de851b9c5ebcf3745f2529c242b`  
Captured: `2026-10-05T18:30:13.660669+00:00`

## Environment

- CPU: `AMD EPYC 9V45 96-Core Processor`
- Logical CPUs: `4`
- Platform: `Linux-6.17.0-1022-azure-x86_64-with-glibc2.39`
- Python: `3.12.14 (main, Aug 13 2026, 02:47:42) [GCC 13.3.0]`
- OR-Tools: `9.15.6755`

## Yield

- Attempted: **540**; excluded: **30**; runnable: **510**
- Generated: **179** (35.1%)
- Strict accepted: **179** (35.1%)
- Released: **179** (35.1%)
- Outcomes: `{'success': 179, 'no_solution': 316, 'excluded': 30, 'internal_error': 15}`
- Solver statuses: `{'OPTIMAL': 114, 'FEASIBLE': 65, 'UNKNOWN': 306, 'NOT_RUN': 30, 'INFEASIBLE': 10, 'ERROR': 15}`

## Multi-output throughput

- Cases: **18**
- Requested solutions: **54**
- Generated solutions: **18**

## Scaling and variance

| Profile | Bars | Mode | n run | n success | Attempt median s | Attempt p90 s | Attempt CV | Success median s | RSS median MiB | Cert median s | Cert/gen |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| applied_harmony | 1 | single | 5 | 5 | 0.1438 | 0.1450 | 0.015 | 0.1221 | 111.0 | 0.0113 | 0.093 |
| applied_harmony | 1 | throughput | 5 | 5 | 0.1400 | 0.1441 | 0.021 | 0.1186 | 114.7 | 0.0113 | 0.095 |
| applied_harmony | 2 | single | 5 | 5 | 2.0217 | 2.1053 | 0.025 | 1.9970 | 143.0 | 0.0130 | 0.006 |
| applied_harmony | 2 | throughput | 5 | 5 | 2.1169 | 2.1180 | 0.001 | 2.0918 | 192.3 | 0.0131 | 0.006 |
| applied_harmony | 4 | single | 5 | 0 | 1.8473 | 1.8680 | 0.007 | n/a | 196.2 | n/a | n/a |
| applied_harmony | 4 | throughput | 5 | 0 | 1.8506 | 1.8563 | 0.003 | n/a | 197.5 | n/a | n/a |
| applied_harmony | 8 | single | 5 | 0 | 2.0298 | 2.0352 | 0.004 | n/a | 292.0 | n/a | n/a |
| applied_harmony | 8 | throughput | 5 | 0 | 2.0276 | 2.0343 | 0.002 | n/a | 291.9 | n/a | n/a |
| applied_harmony | 16 | single | 5 | 0 | 2.5581 | 2.5750 | 0.068 | n/a | 443.3 | n/a | n/a |
| applied_harmony | 16 | throughput | 5 | 0 | 2.5396 | 2.5752 | 0.010 | n/a | 444.4 | n/a | n/a |
| applied_harmony | 32 | single | 5 | 0 | 3.0843 | 3.1015 | 0.005 | n/a | 700.2 | n/a | n/a |
| applied_harmony | 32 | throughput | 5 | 0 | 3.0909 | 3.1706 | 0.017 | n/a | 700.0 | n/a | n/a |
| base_satb | 1 | single | 5 | 5 | 0.1420 | 0.1529 | 0.106 | 0.1228 | 105.5 | 0.0103 | 0.083 |
| base_satb | 1 | throughput | 5 | 5 | 0.1121 | 0.1695 | 0.233 | 0.0927 | 111.1 | 0.0102 | 0.110 |
| base_satb | 2 | single | 5 | 5 | 1.1811 | 1.2203 | 0.025 | 1.1555 | 121.7 | 0.0118 | 0.010 |
| base_satb | 2 | throughput | 5 | 5 | 1.3418 | 1.3615 | 0.011 | 1.3178 | 156.3 | 0.0116 | 0.009 |
| base_satb | 4 | single | 5 | 5 | 2.0917 | 2.0927 | 0.000 | 2.0624 | 150.7 | 0.0151 | 0.007 |
| base_satb | 4 | throughput | 5 | 5 | 2.1033 | 2.1044 | 0.000 | 2.0738 | 232.9 | 0.0149 | 0.007 |
| base_satb | 8 | single | 5 | 0 | 2.1247 | 2.1284 | 0.002 | n/a | 208.7 | n/a | n/a |
| base_satb | 8 | throughput | 5 | 0 | 2.1223 | 2.1264 | 0.002 | n/a | 278.9 | n/a | n/a |
| base_satb | 16 | single | 5 | 0 | 2.0228 | 2.0568 | 0.018 | n/a | 279.9 | n/a | n/a |
| base_satb | 16 | throughput | 5 | 0 | 1.9948 | 2.0689 | 0.029 | n/a | 280.1 | n/a | n/a |
| base_satb | 32 | single | 5 | 0 | 2.4172 | 2.4238 | 0.006 | n/a | 407.8 | n/a | n/a |
| base_satb | 32 | throughput | 5 | 0 | 2.4193 | 2.4270 | 0.006 | n/a | 406.5 | n/a | n/a |
| borrowed_harmony | 1 | single | 5 | 5 | 0.1778 | 0.1902 | 0.105 | 0.1579 | 106.7 | 0.0106 | 0.065 |
| borrowed_harmony | 1 | throughput | 5 | 5 | 0.1351 | 0.1358 | 0.006 | 0.1150 | 113.1 | 0.0104 | 0.091 |
| borrowed_harmony | 2 | single | 5 | 5 | 1.4193 | 1.4590 | 0.042 | 1.3958 | 124.8 | 0.0131 | 0.009 |
| borrowed_harmony | 2 | throughput | 5 | 5 | 1.4169 | 1.5102 | 0.093 | 1.3911 | 161.1 | 0.0132 | 0.010 |
| borrowed_harmony | 4 | single | 5 | 0 | 2.0758 | 2.0811 | 0.002 | n/a | 158.3 | n/a | n/a |
| borrowed_harmony | 4 | throughput | 5 | 5 | 2.1324 | 2.1388 | 0.003 | 2.0975 | 238.2 | 0.0182 | 0.009 |
| borrowed_harmony | 8 | single | 5 | 0 | 1.9767 | 2.0103 | 0.016 | n/a | 220.4 | n/a | n/a |
| borrowed_harmony | 8 | throughput | 5 | 0 | 1.9995 | 2.0321 | 0.017 | n/a | 220.5 | n/a | n/a |
| borrowed_harmony | 16 | single | 5 | 0 | 2.1888 | 2.1948 | 0.002 | n/a | 311.8 | n/a | n/a |
| borrowed_harmony | 16 | throughput | 5 | 0 | 2.1899 | 2.2641 | 0.028 | n/a | 313.3 | n/a | n/a |
| borrowed_harmony | 32 | single | 5 | 0 | 2.0933 | 2.1589 | 0.021 | n/a | 455.2 | n/a | n/a |
| borrowed_harmony | 32 | throughput | 5 | 0 | 2.0790 | 2.0903 | 0.005 | n/a | 455.4 | n/a | n/a |
| combined_borrowed_modulation | 1 | single | 5 | 0 | 0.0003 | 0.0003 | 0.039 | n/a | 92.4 | n/a | n/a |
| combined_borrowed_modulation | 1 | throughput | 5 | 0 | 0.0003 | 0.0003 | 0.033 | n/a | 92.4 | n/a | n/a |
| combined_borrowed_modulation | 2 | single | 5 | 5 | 0.9578 | 0.9763 | 0.020 | 0.9322 | 122.5 | 0.0133 | 0.014 |
| combined_borrowed_modulation | 2 | throughput | 5 | 5 | 0.9246 | 0.9638 | 0.128 | 0.8998 | 149.3 | 0.0134 | 0.015 |
| combined_borrowed_modulation | 4 | single | 5 | 3 | 2.2334 | 2.2382 | 0.011 | 2.1986 | 158.6 | 0.0209 | 0.009 |
| combined_borrowed_modulation | 4 | throughput | 5 | 5 | 2.2356 | 2.2383 | 0.001 | 2.2017 | 241.8 | 0.0185 | 0.008 |
| combined_borrowed_modulation | 8 | single | 5 | 0 | 2.3402 | 2.3439 | 0.002 | n/a | 218.2 | n/a | n/a |
| combined_borrowed_modulation | 8 | throughput | 5 | 0 | 2.3678 | 2.3705 | 0.001 | n/a | 314.4 | n/a | n/a |
| combined_borrowed_modulation | 16 | single | 5 | 0 | 2.7158 | 2.7196 | 0.001 | n/a | 308.0 | n/a | n/a |
| combined_borrowed_modulation | 16 | throughput | 5 | 0 | 2.7134 | 2.7204 | 0.002 | n/a | 309.3 | n/a | n/a |
| combined_borrowed_modulation | 32 | single | 5 | 0 | 3.4032 | 3.4411 | 0.008 | n/a | 507.4 | n/a | n/a |
| combined_borrowed_modulation | 32 | throughput | 5 | 0 | 3.4281 | 3.4430 | 0.004 | n/a | 506.2 | n/a | n/a |
| declared_modulation | 1 | single | 5 | 5 | 0.0773 | 0.0784 | 0.029 | 0.0585 | 102.7 | 0.0098 | 0.166 |
| declared_modulation | 1 | throughput | 5 | 5 | 0.0735 | 0.0758 | 0.024 | 0.0545 | 106.5 | 0.0098 | 0.180 |
| declared_modulation | 2 | single | 5 | 5 | 0.4784 | 0.4859 | 0.018 | 0.4562 | 109.0 | 0.0117 | 0.025 |
| declared_modulation | 2 | throughput | 5 | 5 | 0.5085 | 0.5128 | 0.019 | 0.4858 | 126.7 | 0.0117 | 0.024 |
| declared_modulation | 4 | single | 5 | 5 | 2.0982 | 2.0988 | 0.000 | 2.0685 | 125.3 | 0.0157 | 0.008 |
| declared_modulation | 4 | throughput | 5 | 5 | 1.7600 | 1.8523 | 0.036 | 1.7301 | 174.2 | 0.0159 | 0.009 |
| declared_modulation | 8 | single | 5 | 5 | 2.1845 | 2.2135 | 0.009 | 2.1415 | 152.4 | 0.0224 | 0.010 |
| declared_modulation | 8 | throughput | 5 | 5 | 2.1943 | 2.1954 | 0.001 | 2.1508 | 244.8 | 0.0226 | 0.011 |
| declared_modulation | 16 | single | 5 | 0 | 2.2644 | 2.2670 | 0.001 | n/a | 187.9 | n/a | n/a |
| declared_modulation | 16 | throughput | 5 | 0 | 2.2645 | 2.2668 | 0.029 | n/a | 306.9 | n/a | n/a |
| declared_modulation | 32 | single | 5 | 0 | 2.5251 | 2.5301 | 0.001 | n/a | 250.8 | n/a | n/a |
| declared_modulation | 32 | throughput | 5 | 0 | 2.5235 | 2.5276 | 0.001 | n/a | 251.1 | n/a | n/a |
| expanded_sevenths | 1 | single | 5 | 5 | 0.2001 | 0.2158 | 0.072 | 0.1800 | 110.1 | 0.0099 | 0.057 |
| expanded_sevenths | 1 | throughput | 5 | 5 | 0.1969 | 0.2093 | 0.061 | 0.1767 | 123.4 | 0.0099 | 0.058 |
| expanded_sevenths | 2 | single | 5 | 5 | 1.6956 | 1.7092 | 0.012 | 1.6728 | 132.2 | 0.0114 | 0.007 |
| expanded_sevenths | 2 | throughput | 5 | 5 | 1.7480 | 1.7585 | 0.166 | 1.7257 | 170.4 | 0.0115 | 0.007 |
| expanded_sevenths | 4 | single | 5 | 0 | 2.1473 | 2.1505 | 0.003 | n/a | 180.9 | n/a | n/a |
| expanded_sevenths | 4 | throughput | 5 | 3 | 2.1647 | 2.1901 | 0.011 | 2.1545 | 253.8 | 0.0152 | 0.007 |
| expanded_sevenths | 8 | single | 5 | 0 | 2.2033 | 2.2328 | 0.009 | n/a | 254.2 | n/a | n/a |
| expanded_sevenths | 8 | throughput | 5 | 0 | 2.1960 | 2.2060 | 0.003 | n/a | 253.8 | n/a | n/a |
| expanded_sevenths | 16 | single | 5 | 0 | 2.5532 | 2.5626 | 0.005 | n/a | 381.0 | n/a | n/a |
| expanded_sevenths | 16 | throughput | 5 | 0 | 2.5517 | 2.5714 | 0.005 | n/a | 380.7 | n/a | n/a |
| expanded_sevenths | 32 | single | 5 | 0 | 2.8713 | 3.0129 | 0.038 | n/a | 596.9 | n/a | n/a |
| expanded_sevenths | 32 | throughput | 5 | 0 | 2.8502 | 2.8613 | 0.004 | n/a | 596.7 | n/a | n/a |
| phrase_grammar | 1 | single | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| phrase_grammar | 1 | throughput | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| phrase_grammar | 2 | single | 5 | 0 | 0.0446 | 0.0449 | 0.028 | n/a | 99.1 | n/a | n/a |
| phrase_grammar | 2 | throughput | 5 | 0 | 0.0432 | 0.0446 | 0.022 | n/a | 99.1 | n/a | n/a |
| phrase_grammar | 4 | single | 5 | 5 | 2.0958 | 2.0963 | 0.018 | 2.0649 | 140.7 | 0.0155 | 0.008 |
| phrase_grammar | 4 | throughput | 5 | 5 | 2.0714 | 2.1001 | 0.011 | 2.0411 | 199.4 | 0.0154 | 0.008 |
| phrase_grammar | 8 | single | 5 | 0 | 2.1111 | 2.1293 | 0.006 | n/a | 198.4 | n/a | n/a |
| phrase_grammar | 8 | throughput | 5 | 2 | 2.1275 | 2.1774 | 0.013 | 2.1348 | 286.0 | 0.0219 | 0.010 |
| phrase_grammar | 16 | single | 5 | 0 | 1.9418 | 1.9651 | 0.012 | n/a | 273.0 | n/a | n/a |
| phrase_grammar | 16 | throughput | 5 | 0 | 1.9283 | 1.9359 | 0.007 | n/a | 272.8 | n/a | n/a |
| phrase_grammar | 32 | single | 5 | 0 | 2.4263 | 2.4724 | 0.014 | n/a | 402.3 | n/a | n/a |
| phrase_grammar | 32 | throughput | 5 | 0 | 2.4299 | 2.4787 | 0.016 | n/a | 402.1 | n/a | n/a |
| rhythm_motifs | 1 | single | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| rhythm_motifs | 1 | throughput | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| rhythm_motifs | 2 | single | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| rhythm_motifs | 2 | throughput | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| rhythm_motifs | 4 | single | 5 | 1 | 2.0789 | 2.1021 | 0.008 | 2.0843 | 154.1 | 0.0158 | 0.008 |
| rhythm_motifs | 4 | throughput | 5 | 5 | 2.1209 | 2.1212 | 0.000 | 2.0898 | 240.3 | 0.0159 | 0.008 |
| rhythm_motifs | 8 | single | 5 | 0 | 2.0521 | 2.0988 | 0.015 | n/a | 211.4 | n/a | n/a |
| rhythm_motifs | 8 | throughput | 5 | 0 | 2.0652 | 2.0770 | 0.006 | n/a | 211.5 | n/a | n/a |
| rhythm_motifs | 16 | single | 5 | 0 | 2.2765 | 2.2922 | 0.008 | n/a | 317.2 | n/a | n/a |
| rhythm_motifs | 16 | throughput | 5 | 0 | 2.2876 | 2.3197 | 0.009 | n/a | 316.5 | n/a | n/a |
| rhythm_motifs | 32 | single | 5 | 0 | 2.2102 | 2.2268 | 0.005 | n/a | 465.4 | n/a | n/a |
| rhythm_motifs | 32 | throughput | 5 | 0 | 2.2056 | 2.2276 | 0.008 | n/a | 468.9 | n/a | n/a |
| secondary_harmony | 1 | single | 5 | 5 | 2.6822 | 2.6913 | 0.003 | 2.6571 | 132.9 | 0.0128 | 0.005 |
| secondary_harmony | 1 | throughput | 5 | 0 | 2.2825 | 2.4429 | 0.049 | n/a | 178.4 | n/a | n/a |
| secondary_harmony | 2 | single | 5 | 0 | 3.2349 | 3.2397 | 0.002 | n/a | 167.2 | n/a | n/a |
| secondary_harmony | 2 | throughput | 5 | 0 | 3.2576 | 3.2606 | 0.002 | n/a | 230.3 | n/a | n/a |
| secondary_harmony | 4 | single | 5 | 0 | 4.4410 | 4.4564 | 0.003 | n/a | 238.0 | n/a | n/a |
| secondary_harmony | 4 | throughput | 5 | 0 | 4.4337 | 4.4609 | 0.004 | n/a | 238.6 | n/a | n/a |
| secondary_harmony | 8 | single | 5 | 0 | 6.9571 | 6.9766 | 0.002 | n/a | 363.7 | n/a | n/a |
| secondary_harmony | 8 | throughput | 5 | 0 | 6.9459 | 7.0295 | 0.009 | n/a | 366.3 | n/a | n/a |
| secondary_harmony | 16 | single | 5 | 0 | 11.9233 | 12.0486 | 0.006 | n/a | 591.8 | n/a | n/a |
| secondary_harmony | 16 | throughput | 5 | 0 | 11.9571 | 12.1118 | 0.009 | n/a | 591.4 | n/a | n/a |
| secondary_harmony | 32 | single | 5 | 0 | 22.2850 | 22.5029 | 0.007 | n/a | 761.1 | n/a | n/a |
| secondary_harmony | 32 | throughput | 5 | 0 | 22.2628 | 22.4298 | 0.004 | n/a | 761.8 | n/a | n/a |

Raw rows preserve exclusions, UNKNOWN/no-solution outcomes, and crashes. 
These measurements apply only to the recorded commit/runner; optimization is outside EH-11.
