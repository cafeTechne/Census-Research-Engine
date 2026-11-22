# Round 87: ecologic versus individual-level associations on PUMS

Criterion commit: `d388e00da31fad2633d5fdc008a364bd0381ace9`. 1000 draws per cell; 90% SDR intervals. Author self-review, not independent.

| Family | Outcome | Lowest coverage | Cells |
| :--- | :--- | ---: | ---: |
| C1 | fail | 0.621 | 32 |
| C2 | fail | 0.621 | 32 |
| C1l | pass | 0.871 | 16 |

| J | Records | Contextual | Confounding | Outcome | Coverage |
| ---: | ---: | ---: | :--- | :--- | :--- |
| 30 | 5000 | 0.0 | off | continuous | within 0.872, between 0.896, contextual 0.885, ecologic 0.896, ecologic_gap 0.885 |
| 30 | 5000 | 0.0 | off | binary | within 0.888, between 0.888, contextual 0.888, ecologic 0.888, ecologic_gap 0.888, logit_within 0.907, logit_between 0.893, logit_contextual 0.888 |
| 30 | 5000 | 0.0 | on | continuous | within 0.880, between 0.893, contextual 0.894, ecologic 0.893, ecologic_gap 0.894 |
| 30 | 5000 | 0.0 | on | binary | within 0.889, between 0.895, contextual 0.903, ecologic 0.895, ecologic_gap 0.903, logit_within 0.898, logit_between 0.910, logit_contextual 0.906 |
| 30 | 5000 | 0.25 | off | continuous | within 0.882, between 0.881, contextual 0.895, ecologic 0.881, ecologic_gap 0.895 |
| 30 | 5000 | 0.25 | off | binary | within 0.883, between 0.890, contextual 0.881, ecologic 0.890, ecologic_gap 0.881, logit_within 0.888, logit_between 0.892, logit_contextual 0.885 |
| 30 | 5000 | 0.25 | on | continuous | within 0.888, between 0.876, contextual 0.861, ecologic 0.876, ecologic_gap 0.861 |
| 30 | 5000 | 0.25 | on | binary | within 0.899, between 0.899, contextual 0.898, ecologic 0.899, ecologic_gap 0.898, logit_within 0.902, logit_between 0.890, logit_contextual 0.897 |
| 30 | 30000 | 0.0 | off | continuous | within 0.882, between 0.902, contextual 0.876, ecologic 0.902, ecologic_gap 0.876 |
| 30 | 30000 | 0.0 | off | binary | within 0.888, between 0.877, contextual 0.896, ecologic 0.877, ecologic_gap 0.896, logit_within 0.885, logit_between 0.871, logit_contextual 0.894 |
| 30 | 30000 | 0.0 | on | continuous | within 0.884, between 0.899, contextual 0.886, ecologic 0.899, ecologic_gap 0.886 |
| 30 | 30000 | 0.0 | on | binary | within 0.905, between 0.895, contextual 0.895, ecologic 0.895, ecologic_gap 0.895, logit_within 0.905, logit_between 0.886, logit_contextual 0.891 |
| 30 | 30000 | 0.25 | off | continuous | within 0.882, between 0.903, contextual 0.894, ecologic 0.903, ecologic_gap 0.894 |
| 30 | 30000 | 0.25 | off | binary | within 0.901, between 0.887, contextual 0.908, ecologic 0.887, ecologic_gap 0.908, logit_within 0.896, logit_between 0.895, logit_contextual 0.908 |
| 30 | 30000 | 0.25 | on | continuous | within 0.885, between 0.896, contextual 0.895, ecologic 0.896, ecologic_gap 0.895 |
| 30 | 30000 | 0.25 | on | binary | within 0.877, between 0.889, contextual 0.889, ecologic 0.889, ecologic_gap 0.889, logit_within 0.895, logit_between 0.887, logit_contextual 0.885 |
| 150 | 5000 | 0.0 | off | continuous | within 0.905, between 0.898, contextual 0.899, ecologic 0.898, ecologic_gap 0.899 |
| 150 | 5000 | 0.0 | off | binary | within 0.871, between 0.910, contextual 0.902, ecologic 0.910, ecologic_gap 0.902, logit_within 0.891, logit_between 0.903, logit_contextual 0.906 |
| 150 | 5000 | 0.0 | on | continuous | within 0.879, between 0.739, contextual 0.801, ecologic 0.739, ecologic_gap 0.801 |
| 150 | 5000 | 0.0 | on | binary | within 0.881, between 0.836, contextual 0.832, ecologic 0.836, ecologic_gap 0.832, logit_within 0.886, logit_between 0.897, logit_contextual 0.893 |
| 150 | 5000 | 0.25 | off | continuous | within 0.886, between 0.785, contextual 0.844, ecologic 0.785, ecologic_gap 0.844 |
| 150 | 5000 | 0.25 | off | binary | within 0.876, between 0.865, contextual 0.865, ecologic 0.865, ecologic_gap 0.865, logit_within 0.886, logit_between 0.890, logit_contextual 0.902 |
| 150 | 5000 | 0.25 | on | continuous | within 0.878, between 0.621, contextual 0.690, ecologic 0.621, ecologic_gap 0.690 |
| 150 | 5000 | 0.25 | on | binary | within 0.863, between 0.728, contextual 0.760, ecologic 0.728, ecologic_gap 0.760, logit_within 0.878, logit_between 0.891, logit_contextual 0.877 |
| 150 | 30000 | 0.0 | off | continuous | within 0.876, between 0.898, contextual 0.886, ecologic 0.898, ecologic_gap 0.886 |
| 150 | 30000 | 0.0 | off | binary | within 0.889, between 0.892, contextual 0.898, ecologic 0.892, ecologic_gap 0.898, logit_within 0.904, logit_between 0.885, logit_contextual 0.898 |
| 150 | 30000 | 0.0 | on | continuous | within 0.890, between 0.854, contextual 0.863, ecologic 0.854, ecologic_gap 0.863 |
| 150 | 30000 | 0.0 | on | binary | within 0.885, between 0.894, contextual 0.882, ecologic 0.894, ecologic_gap 0.882, logit_within 0.887, logit_between 0.911, logit_contextual 0.892 |
| 150 | 30000 | 0.25 | off | continuous | within 0.878, between 0.854, contextual 0.880, ecologic 0.854, ecologic_gap 0.880 |
| 150 | 30000 | 0.25 | off | binary | within 0.882, between 0.892, contextual 0.885, ecologic 0.892, ecologic_gap 0.885, logit_within 0.892, logit_between 0.904, logit_contextual 0.874 |
| 150 | 30000 | 0.25 | on | continuous | within 0.887, between 0.875, contextual 0.862, ecologic 0.875, ecologic_gap 0.862 |
| 150 | 30000 | 0.25 | on | binary | within 0.867, between 0.877, contextual 0.855, ecologic 0.877, ecologic_gap 0.855, logit_within 0.880, logit_between 0.894, logit_contextual 0.872 |
