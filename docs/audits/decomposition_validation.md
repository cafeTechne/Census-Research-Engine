# Round 79: Oaxaca-Blinder and Fairlie decompositions with SDR replicate weights

Criterion commit: `9e52bb4601edf078cd2b5497c3be19487a6bb25a`. 1000 draws per cell; 90% SDR intervals; Fairlie 10 orderings per draw. Lowest coverage over the quantities in each family. Author self-review, not independent.

| Group B size | Blocks | Explained share | O1 totals | O1 detailed | F1 totals | F1 detailed |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 300 | 3 | 0.2 | 0.892 | 0.874 | 0.867 | 0.888 |
| 300 | 3 | 0.6 | 0.889 | 0.878 | 0.876 | 0.875 |
| 300 | 8 | 0.2 | 0.884 | 0.866 | 0.853 | 0.802 |
| 300 | 8 | 0.6 | 0.880 | 0.851 | 0.873 | 0.868 |
| 1000 | 3 | 0.2 | 0.887 | 0.871 | 0.890 | 0.874 |
| 1000 | 3 | 0.6 | 0.862 | 0.872 | 0.886 | 0.894 |
| 1000 | 8 | 0.2 | 0.882 | 0.871 | 0.888 | 0.881 |
| 1000 | 8 | 0.6 | 0.894 | 0.863 | 0.885 | 0.885 |
| 5000 | 3 | 0.2 | 0.890 | 0.883 | 0.894 | 0.880 |
| 5000 | 3 | 0.6 | 0.885 | 0.871 | 0.894 | 0.894 |
| 5000 | 8 | 0.2 | 0.882 | 0.881 | 0.882 | 0.882 |
| 5000 | 8 | 0.6 | 0.874 | 0.870 | 0.888 | 0.883 |

Achieved population explained shares (O1, F1): k=3, s=0.2: 0.200, 0.200, k=3, s=0.6: 0.600, 0.600, k=8, s=0.2: 0.200, 0.200, k=8, s=0.6: 0.600, 0.600.

Outcomes: `{"O1_totals": {"passed": true, "failing_sizes": [], "validated_from": 300}, "O1_detailed": {"passed": false, "failing_sizes": [300], "validated_from": 1000}, "F1_totals": {"passed": false, "failing_sizes": [300], "validated_from": 1000}, "F1_detailed": {"passed": false, "failing_sizes": [300], "validated_from": 1000}}`.
