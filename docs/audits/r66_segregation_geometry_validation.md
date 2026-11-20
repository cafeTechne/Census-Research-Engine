# Round 66 S: segregation coverage on GA, TX and AZ

Criterion commit: `d30d7ed`. 2,000 draws per cell.

| Procedure | Validated range | Judged bins | Failed bins | Outcome |
| :--- | :--- | ---: | :--- | :--- |
| D_bc | [0.15, 1.0] | 13 | [('black2_TX', '[.75, 1)')] | fails |
| I_bc | [0.0, 'inf'] | 16 | none | passes |
| H_bc | [0.0, 1.0] | 13 | none | passes |

| Design | Counties | Procedure | Bin | Counties in bin | Mean coverage (rho 0 / -.3) | Passed |
| :--- | ---: | :--- | :--- | ---: | :--- | :--- |
| black2_GA | 110 | D_naive | [.15, .30) | 63 | 0.876 / 0.869 | True |
| black2_GA | 110 | D_naive | [.30, .50) | 22 | 0.904 / 0.901 | True |
| black2_GA | 110 | D_naive | [.50, .75) | 11 | 0.844 / 0.831 | False |
| black2_GA | 110 | D_naive | [1, inf) | 6 | 0.869 / 0.856 | False |
| black2_GA | 110 | I_bc | [.15, .30) | 63 | 0.898 / 0.897 | True |
| black2_GA | 110 | I_bc | [.30, .50) | 22 | 0.887 / 0.891 | True |
| black2_GA | 110 | I_bc | [.50, .75) | 11 | 0.882 / 0.883 | True |
| black2_GA | 110 | I_bc | [1, inf) | 6 | 0.873 / 0.874 | True |
| black2_GA | 110 | H_bc | [.15, .30) | 63 | 0.929 / 0.931 | True |
| black2_GA | 110 | H_bc | [.30, .50) | 22 | 0.930 / 0.933 | True |
| black2_GA | 110 | H_bc | [.50, .75) | 11 | 0.935 / 0.931 | True |
| black2_GA | 110 | H_bc | [1, inf) | 6 | 0.864 / 0.861 | True |
| black2_GA | 110 | H_naive | [.15, .30) | 63 | 0.894 / 0.890 | True |
| black2_GA | 110 | H_naive | [.30, .50) | 22 | 0.921 / 0.919 | True |
| black2_GA | 110 | H_naive | [.50, .75) | 11 | 0.889 / 0.881 | True |
| black2_GA | 110 | H_naive | [1, inf) | 6 | 0.897 / 0.888 | True |
| black2_GA | 110 | D_bc | [.15, .30) | 63 | 0.882 / 0.882 | True |
| black2_GA | 110 | D_bc | [.30, .50) | 22 | 0.884 / 0.885 | True |
| black2_GA | 110 | D_bc | [.50, .75) | 11 | 0.890 / 0.885 | True |
| black2_GA | 110 | D_bc | [1, inf) | 6 | 0.829 / 0.824 | False |
| black2_GA | 110 | I_naive | [.15, .30) | 63 | 0.876 / 0.873 | True |
| black2_GA | 110 | I_naive | [.30, .50) | 22 | 0.886 / 0.886 | True |
| black2_GA | 110 | I_naive | [.50, .75) | 11 | 0.871 / 0.870 | True |
| black2_GA | 110 | I_naive | [1, inf) | 6 | 0.907 / 0.909 | True |
| pov_GA | 109 | D_naive | [.15, .30) | 26 | 0.877 / 0.870 | True |
| pov_GA | 109 | D_naive | [.30, .50) | 81 | 0.861 / 0.849 | False |
| pov_GA | 109 | I_bc | [.15, .30) | 26 | 0.882 / 0.888 | True |
| pov_GA | 109 | I_bc | [.30, .50) | 81 | 0.884 / 0.888 | True |
| pov_GA | 109 | H_bc | [.15, .30) | 26 | 0.931 / 0.936 | True |
| pov_GA | 109 | H_bc | [.30, .50) | 81 | 0.939 / 0.942 | True |
| pov_GA | 109 | H_naive | [.15, .30) | 26 | 0.930 / 0.930 | True |
| pov_GA | 109 | H_naive | [.30, .50) | 81 | 0.898 / 0.893 | True |
| pov_GA | 109 | D_bc | [.15, .30) | 26 | 0.873 / 0.870 | True |
| pov_GA | 109 | D_bc | [.30, .50) | 81 | 0.883 / 0.882 | True |
| pov_GA | 109 | I_naive | [.15, .30) | 26 | 0.877 / 0.880 | True |
| pov_GA | 109 | I_naive | [.30, .50) | 81 | 0.855 / 0.853 | False |
| black2_TX | 141 | D_naive | [.15, .30) | 17 | 0.899 / 0.893 | True |
| black2_TX | 141 | D_naive | [.30, .50) | 49 | 0.836 / 0.824 | False |
| black2_TX | 141 | D_naive | [.50, .75) | 36 | 0.841 / 0.831 | False |
| black2_TX | 141 | D_naive | [.75, 1) | 18 | 0.880 / 0.872 | True |
| black2_TX | 141 | D_naive | [1, inf) | 11 | 0.864 / 0.858 | False |
| black2_TX | 141 | I_bc | [.15, .30) | 17 | 0.895 / 0.899 | True |
| black2_TX | 141 | I_bc | [.30, .50) | 49 | 0.901 / 0.904 | True |
| black2_TX | 141 | I_bc | [.50, .75) | 36 | 0.889 / 0.897 | True |
| black2_TX | 141 | I_bc | [.75, 1) | 18 | 0.884 / 0.888 | True |
| black2_TX | 141 | I_bc | [1, inf) | 11 | 0.868 / 0.871 | True |
| black2_TX | 141 | H_bc | [.15, .30) | 17 | 0.932 / 0.932 | True |
| black2_TX | 141 | H_bc | [.30, .50) | 49 | 0.943 / 0.942 | True |
| black2_TX | 141 | H_bc | [.50, .75) | 36 | 0.948 / 0.953 | True |
| black2_TX | 141 | H_bc | [.75, 1) | 18 | 0.926 / 0.924 | True |
| black2_TX | 141 | H_bc | [1, inf) | 11 | 0.868 / 0.864 | False |
| black2_TX | 141 | H_naive | [.15, .30) | 17 | 0.900 / 0.895 | True |
| black2_TX | 141 | H_naive | [.30, .50) | 49 | 0.879 / 0.870 | False |
| black2_TX | 141 | H_naive | [.50, .75) | 36 | 0.895 / 0.888 | True |
| black2_TX | 141 | H_naive | [.75, 1) | 18 | 0.905 / 0.899 | True |
| black2_TX | 141 | H_naive | [1, inf) | 11 | 0.894 / 0.892 | True |
| black2_TX | 141 | D_bc | [.15, .30) | 17 | 0.883 / 0.883 | True |
| black2_TX | 141 | D_bc | [.30, .50) | 49 | 0.903 / 0.901 | True |
| black2_TX | 141 | D_bc | [.50, .75) | 36 | 0.909 / 0.910 | True |
| black2_TX | 141 | D_bc | [.75, 1) | 18 | 0.888 / 0.886 | False |
| black2_TX | 141 | D_bc | [1, inf) | 11 | 0.853 / 0.849 | False |
| black2_TX | 141 | I_naive | [.15, .30) | 17 | 0.878 / 0.877 | True |
| black2_TX | 141 | I_naive | [.30, .50) | 49 | 0.850 / 0.845 | False |
| black2_TX | 141 | I_naive | [.50, .75) | 36 | 0.852 / 0.855 | False |
| black2_TX | 141 | I_naive | [.75, 1) | 18 | 0.881 / 0.888 | True |
| black2_TX | 141 | I_naive | [1, inf) | 11 | 0.897 / 0.903 | True |
| pov_TX | 140 | D_naive | [.15, .30) | 33 | 0.883 / 0.875 | True |
| pov_TX | 140 | D_naive | [.30, .50) | 106 | 0.812 / 0.793 | False |
| pov_TX | 140 | I_bc | [.15, .30) | 33 | 0.879 / 0.886 | True |
| pov_TX | 140 | I_bc | [.30, .50) | 106 | 0.895 / 0.901 | True |
| pov_TX | 140 | H_bc | [.15, .30) | 33 | 0.926 / 0.930 | True |
| pov_TX | 140 | H_bc | [.30, .50) | 106 | 0.952 / 0.954 | True |
| pov_TX | 140 | H_naive | [.15, .30) | 33 | 0.928 / 0.928 | True |
| pov_TX | 140 | H_naive | [.30, .50) | 106 | 0.877 / 0.866 | False |
| pov_TX | 140 | D_bc | [.15, .30) | 33 | 0.870 / 0.868 | True |
| pov_TX | 140 | D_bc | [.30, .50) | 106 | 0.900 / 0.898 | True |
| pov_TX | 140 | I_naive | [.15, .30) | 33 | 0.880 / 0.884 | True |
| pov_TX | 140 | I_naive | [.30, .50) | 106 | 0.829 / 0.823 | False |
| black2_AZ | 14 | D_naive | [1, inf) | 6 | 0.790 / 0.770 | False |
| black2_AZ | 14 | I_bc | [1, inf) | 6 | 0.878 / 0.893 | True |
| black2_AZ | 14 | H_bc | [1, inf) | 6 | 0.935 / 0.940 | True |
| black2_AZ | 14 | H_naive | [1, inf) | 6 | 0.843 / 0.840 | False |
| black2_AZ | 14 | D_bc | [1, inf) | 6 | 0.937 / 0.936 | True |
| black2_AZ | 14 | I_naive | [1, inf) | 6 | 0.859 / 0.876 | False |
| pov_AZ | 14 | D_naive | [.15, .30) | 5 | 0.872 / 0.858 | False |
| pov_AZ | 14 | D_naive | [.30, .50) | 9 | 0.737 / 0.711 | False |
| pov_AZ | 14 | I_bc | [.15, .30) | 5 | 0.900 / 0.903 | True |
| pov_AZ | 14 | I_bc | [.30, .50) | 9 | 0.929 / 0.935 | True |
| pov_AZ | 14 | H_bc | [.15, .30) | 5 | 0.938 / 0.940 | True |
| pov_AZ | 14 | H_bc | [.30, .50) | 9 | 0.971 / 0.974 | True |
| pov_AZ | 14 | H_naive | [.15, .30) | 5 | 0.896 / 0.887 | True |
| pov_AZ | 14 | H_naive | [.30, .50) | 9 | 0.793 / 0.776 | False |
| pov_AZ | 14 | D_bc | [.15, .30) | 5 | 0.889 / 0.890 | True |
| pov_AZ | 14 | D_bc | [.30, .50) | 9 | 0.929 / 0.928 | True |
| pov_AZ | 14 | I_naive | [.15, .30) | 5 | 0.875 / 0.869 | True |
| pov_AZ | 14 | I_naive | [.30, .50) | 9 | 0.753 / 0.743 | False |
