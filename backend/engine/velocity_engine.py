"""Phase 7a: velocity metrics over a list of datetimes."""
import numpy as np


def velocity(times):
    ts = sorted(t.timestamp() for t in times)
    n = len(ts)
    if n < 2:
        return dict(transactions=n, elapsed_seconds=0, avg_delay_seconds=0, median_delay_seconds=0,
                    tx_per_minute=0, tx_per_hour=0, burst_max_per_minute=n, label="LOW")
    gaps, el = np.diff(ts), ts[-1] - ts[0]
    j, burst = 0, 1
    for i in range(n):
        while ts[i] - ts[j] > 60:
            j += 1
        burst = max(burst, i - j + 1)
    med = float(np.median(gaps))
    label = "HIGH" if (med <= 120 or el <= 1800) else "MEDIUM" if (med <= 900 or el <= 14400) else "LOW"
    pm = n / max(el, 1) * 60
    return dict(transactions=n, elapsed_seconds=int(el), avg_delay_seconds=round(float(gaps.mean()), 1),
                median_delay_seconds=round(med, 1), tx_per_minute=round(pm, 2), tx_per_hour=round(pm * 60, 1),
                burst_max_per_minute=burst, label=label)
