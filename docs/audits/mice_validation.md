# Round 100: multiple imputation by fully conditional specification

Criterion commit: `b4d101c27eafed41f6644b2f8f57c9bea0512145`. 1000 draws per cell; m = 20; 90% intervals; coverage and bias for the x1/x2/x3 slopes. Author self-review, not independent.

| Method | Outcome | Lowest coverage |
| :--- | :--- | ---: |
| I1-pmm | pass | 0.885 |
| I1-norm | pass | 0.887 |

| N | Share missing | Mean FMI | PMM | Norm | Complete cases | CC bias |
| ---: | ---: | ---: | :--- | :--- | :--- | :--- |
| 145 | 0.10 | 0.19 | 0.893/0.892/0.898 | 0.889/0.887/0.898 | 0.886/0.903/0.912 | -0.002/-0.000/0.003 |
| 145 | 0.40 | 0.59 | 0.890/0.885/0.912 | 0.896/0.900/0.911 | 0.896/0.906/0.914 | 0.006/-0.000/-0.008 |
| 600 | 0.10 | 0.19 | 0.886/0.910/0.888 | 0.887/0.915/0.897 | 0.895/0.899/0.897 | -0.002/0.000/-0.001 |
| 600 | 0.40 | 0.60 | 0.897/0.908/0.910 | 0.897/0.902/0.908 | 0.912/0.894/0.898 | -0.000/-0.000/0.004 |
