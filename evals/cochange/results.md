Validation (index = first 49% of window, validated on the next 21%), pooled over repos:

| method | cases | coverage | precision@3 | hit rate | noise | hit rate over all cases |
|---|---|---|---|---|---|---|
| ratio>=0.3 n>=2 | 1760 | 59.3% | 50.3% | 64.4% | 35.6% | 38.2% |
| ratio>=0.3 n>=3 | 1760 | 51.8% | 51.4% | 64.8% | 35.2% | 33.5% |
| ratio>=0.3 n>=4 | 1760 | 45.6% | 52.9% | 64.6% | 35.4% | 29.5% |
| ratio>=0.3 n>=5 | 1760 | 37.2% | 53.2% | 66.0% | 34.0% | 24.5% |
| ratio>=0.4 n>=2 | 1760 | 45.4% | 56.0% | 67.5% | 32.5% | 30.6% |
| ratio>=0.4 n>=3 | 1760 | 39.3% | 57.2% | 67.6% | 32.4% | 26.5% |
| ratio>=0.4 n>=4 | 1760 | 34.8% | 58.8% | 68.0% | 32.0% | 23.6% |
| ratio>=0.4 n>=5 | 1760 | 28.9% | 59.6% | 69.3% | 30.7% | 20.0% |
| ratio>=0.5 n>=2 | 1760 | 37.6% | 60.4% | 70.4% | 29.6% | 26.5% |
| ratio>=0.5 n>=3 | 1760 | 32.8% | 61.3% | 70.2% | 29.8% | 23.0% |
| ratio>=0.5 n>=4 | 1760 | 28.6% | 63.1% | 70.8% | 29.2% | 20.3% |
| ratio>=0.5 n>=5 | 1760 | 23.4% | 64.8% | 72.8% | 27.2% | 17.0% |
| ratio>=0.6 n>=2 | 1760 | 26.0% | 66.1% | 74.0% | 26.0% | 19.3% |
| ratio>=0.6 n>=3 | 1760 | 22.4% | 67.7% | 74.4% | 25.6% | 16.6% |
| ratio>=0.6 n>=4 | 1760 | 19.1% | 70.8% | 76.6% | 23.4% | 14.7% |
| ratio>=0.6 n>=5 | 1760 | 15.9% | 72.4% | 77.9% | 22.1% | 12.4% |
| ratio>=0.7 n>=2 | 1760 | 18.0% | 75.4% | 81.7% | 18.3% | 14.7% |
| ratio>=0.7 n>=3 | 1760 | 15.5% | 78.3% | 84.2% | 15.8% | 13.1% |
| ratio>=0.7 n>=4 | 1760 | 13.4% | 81.8% | 86.0% | 14.0% | 11.5% |
| ratio>=0.7 n>=5 | 1760 | 11.3% | 81.7% | 85.4% | 14.6% | 9.7% |
| ratio>=0.8 n>=2 | 1760 | 13.8% | 80.2% | 84.7% | 15.3% | 11.6% |
| ratio>=0.8 n>=3 | 1760 | 11.2% | 85.3% | 88.9% | 11.1% | 10.0% |
| ratio>=0.8 n>=4 | 1760 | 10.5% | 85.9% | 89.2% | 10.8% | 9.4% |
| ratio>=0.8 n>=5 | 1760 | 8.4% | 86.8% | 89.2% | 10.8% | 7.5% |

Held-out test, pooled, all cases:

| method | cases | coverage | precision@3 | hit rate | noise | hit rate over all cases |
|---|---|---|---|---|---|---|
| baton_chosen | 2716 | 36.5% | 54.8% | 64.9% | 35.1% | 23.7% |
| baton_default_0.5_3 | 2716 | 33.7% | 57.0% | 66.5% | 33.5% | 22.4% |
| baton_strict_0.7_3 | 2716 | 17.2% | 73.1% | 75.8% | 24.2% | 13.0% |
| baton_no_threshold_top3 | 2716 | 78.1% | 35.1% | 63.7% | 36.3% | 49.7% |
| same_directory | 2716 | 90.2% | 29.8% | 48.2% | 51.8% | 43.5% |
| global_most_changed | 2716 | 100.0% | 17.4% | 39.1% | 60.9% | 39.1% |

Held-out test, pooled, only the cases where the chosen baton setting shows a hint:

| method | cases | coverage | precision@3 | hit rate | noise | hit rate over all cases |
|---|---|---|---|---|---|---|
| baton_chosen | 991 | 100.0% | 54.8% | 64.9% | 35.1% | 64.9% |
| baton_default_0.5_3 | 991 | 92.2% | 57.0% | 66.5% | 33.5% | 61.4% |
| baton_strict_0.7_3 | 991 | 47.1% | 73.1% | 75.8% | 24.2% | 35.7% |
| baton_no_threshold_top3 | 991 | 100.0% | 42.8% | 73.1% | 26.9% | 73.1% |
| same_directory | 991 | 99.4% | 36.2% | 56.0% | 44.0% | 55.7% |
| global_most_changed | 991 | 100.0% | 23.0% | 53.1% | 46.9% | 53.1% |

click (700 index commits, 131 evaluation commits used of 300):

| method | cases | coverage | precision@3 | hit rate | noise | hit rate over all cases |
|---|---|---|---|---|---|---|
| baton_chosen | 468 | 32.1% | 58.9% | 65.3% | 34.7% | 20.9% |
| baton_default_0.5_3 | 468 | 29.5% | 62.2% | 68.1% | 31.9% | 20.1% |
| baton_strict_0.7_3 | 468 | 13.7% | 75.0% | 76.6% | 23.4% | 10.5% |
| baton_no_threshold_top3 | 468 | 76.3% | 26.9% | 61.1% | 38.9% | 46.6% |
| same_directory | 468 | 89.3% | 15.1% | 28.9% | 71.1% | 25.9% |
| global_most_changed | 468 | 100.0% | 11.8% | 35.5% | 64.5% | 35.5% |

fastapi (700 index commits, 83 evaluation commits used of 300):

| method | cases | coverage | precision@3 | hit rate | noise | hit rate over all cases |
|---|---|---|---|---|---|---|
| baton_chosen | 267 | 42.7% | 72.1% | 83.3% | 16.7% | 35.6% |
| baton_default_0.5_3 | 267 | 40.4% | 73.8% | 85.2% | 14.8% | 34.5% |
| baton_strict_0.7_3 | 267 | 34.5% | 79.5% | 87.0% | 13.0% | 30.0% |
| baton_no_threshold_top3 | 267 | 68.9% | 48.0% | 73.9% | 26.1% | 50.9% |
| same_directory | 267 | 85.4% | 25.0% | 30.7% | 69.3% | 26.2% |
| global_most_changed | 267 | 100.0% | 14.5% | 43.4% | 56.6% | 43.4% |

flask (700 index commits, 134 evaluation commits used of 300):

| method | cases | coverage | precision@3 | hit rate | noise | hit rate over all cases |
|---|---|---|---|---|---|---|
| baton_chosen | 628 | 43.9% | 58.8% | 71.0% | 29.0% | 31.2% |
| baton_default_0.5_3 | 628 | 40.8% | 62.4% | 72.3% | 27.7% | 29.5% |
| baton_strict_0.7_3 | 628 | 18.9% | 76.2% | 79.0% | 21.0% | 15.0% |
| baton_no_threshold_top3 | 628 | 85.8% | 39.7% | 69.0% | 31.0% | 59.2% |
| same_directory | 628 | 93.3% | 37.3% | 57.3% | 42.7% | 53.5% |
| global_most_changed | 628 | 100.0% | 24.3% | 53.7% | 46.3% | 53.7% |

httpx (700 index commits, 105 evaluation commits used of 300):

| method | cases | coverage | precision@3 | hit rate | noise | hit rate over all cases |
|---|---|---|---|---|---|---|
| baton_chosen | 469 | 62.0% | 38.9% | 48.5% | 51.5% | 30.1% |
| baton_default_0.5_3 | 469 | 56.5% | 38.0% | 47.9% | 52.1% | 27.1% |
| baton_strict_0.7_3 | 469 | 21.1% | 46.5% | 46.5% | 53.5% | 9.8% |
| baton_no_threshold_top3 | 469 | 89.3% | 27.5% | 57.3% | 42.7% | 51.2% |
| same_directory | 469 | 95.7% | 24.2% | 46.3% | 53.7% | 44.3% |
| global_most_changed | 469 | 100.0% | 19.9% | 44.3% | 55.7% | 44.3% |

jinja (700 index commits, 125 evaluation commits used of 300):

| method | cases | coverage | precision@3 | hit rate | noise | hit rate over all cases |
|---|---|---|---|---|---|---|
| baton_chosen | 551 | 25.4% | 64.0% | 75.0% | 25.0% | 19.1% |
| baton_default_0.5_3 | 551 | 23.4% | 68.3% | 79.8% | 20.2% | 18.7% |
| baton_strict_0.7_3 | 551 | 15.6% | 90.3% | 91.9% | 8.1% | 14.3% |
| baton_no_threshold_top3 | 551 | 86.8% | 42.3% | 68.4% | 31.6% | 59.3% |
| same_directory | 551 | 99.5% | 41.9% | 61.9% | 38.1% | 61.5% |
| global_most_changed | 551 | 100.0% | 22.1% | 38.1% | 61.9% | 38.1% |

requests (700 index commits, 95 evaluation commits used of 300):

| method | cases | coverage | precision@3 | hit rate | noise | hit rate over all cases |
|---|---|---|---|---|---|---|
| baton_chosen | 333 | 6.0% | 38.3% | 40.0% | 60.0% | 2.4% |
| baton_default_0.5_3 | 333 | 5.4% | 38.9% | 38.9% | 61.1% | 2.1% |
| baton_strict_0.7_3 | 333 | 2.1% | 85.7% | 85.7% | 14.3% | 1.8% |
| baton_no_threshold_top3 | 333 | 43.2% | 19.6% | 40.3% | 59.7% | 17.4% |
| same_directory | 333 | 66.7% | 24.3% | 48.6% | 51.4% | 32.4% |
| global_most_changed | 333 | 100.0% | 3.4% | 7.5% | 92.5% | 7.5% |
