import csv
import json
import threading
import time

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


class TempLog:
    """Thread-safe store. The controller thread writes, the plot reads."""

    def __init__(self):
        self.lock = threading.Lock()
        self.atom_duty = 0.0          # current atomizer duty (%), stamped onto every sample
        self.reset()

    def reset(self):
        with self.lock:
            self.t0 = time.monotonic()
            self.t, self.temp, self.target, self.signal, self.atom = [], [], [], [], []

    def set_atomizer(self, duty):
        with self.lock:
            self.atom_duty = float(duty)

    def add(self, temp, target, signal=0.0):
        with self.lock:
            self.t.append(time.monotonic() - self.t0)
            self.temp.append(temp)
            self.target.append(target)
            self.signal.append(signal)
            self.atom.append(self.atom_duty)

    def snapshot(self):
        with self.lock:
            return {
                "t": np.array(self.t), "temp": np.array(self.temp),
                "target": np.array(self.target), "signal": np.array(self.signal),
                "atom": np.array(self.atom),
            }


# ---------------------------------------------------------------- plotting
def _make_figure(target, tol, title, figsize=(9, 7)):
    fig, (ax_t, ax_s, ax_a) = plt.subplots(
        3, 1, sharex=True, figsize=figsize, gridspec_kw={"height_ratios": [3, 1, 1]})

    (l_t,) = ax_t.plot([], [], lw=1.8, label="Vial temperature")
    ax_t.axhline(target, color="r", ls="--", lw=1.2, label=f"Target ({target} °C)")
    ax_t.axhspan(target - tol, target + tol, color="r", alpha=0.12, label=f"±{tol} °C band")
    ax_t.set_ylabel("Temperature (°C)")
    ax_t.set_title(title)
    ax_t.grid(alpha=0.3)

    (l_s,) = ax_s.plot([], [], lw=1.2, color="tab:orange")
    ax_s.axhline(0, color="k", lw=0.6)
    ax_s.set_ylabel("Controller\noutput")
    ax_s.grid(alpha=0.3)

    (l_a,) = ax_a.plot([], [], lw=1.5, color="tab:green", drawstyle="steps-post")
    ax_a.set_ylabel("Atomizer\nduty (%)")
    ax_a.set_ylim(-5, 105)
    ax_a.set_xlabel("Time (s)")
    ax_a.grid(alpha=0.3)

    return fig, (ax_t, ax_s, ax_a), (l_t, l_s, l_a)


def _draw(d, axes, lines, target, tol):
    t = d["t"]
    if len(t) == 0:
        return
    ax_t, ax_s, ax_a = axes
    l_t, l_s, l_a = lines
    l_t.set_data(t, d["temp"])
    l_s.set_data(t, d["signal"])
    l_a.set_data(t, d["atom"])
    ax_t.set_xlim(0, max(10, t[-1] * 1.02))
    ax_t.set_ylim(min(d["temp"].min(), target - tol) - 1, max(d["temp"].max(), target + tol) + 1)
    m = max(10.0, float(np.abs(d["signal"]).max()) * 1.1)
    ax_s.set_ylim(-m, m)


def _shade_atomizer(ax, t, atom):
    on = atom > 0
    if not on.any():
        return
    edges = np.diff(on.astype(int))
    starts = list(np.where(edges == 1)[0] + 1)
    ends = list(np.where(edges == -1)[0] + 1)
    if on[0]:
        starts.insert(0, 0)
    if on[-1]:
        ends.append(len(t) - 1)
    for i, (s, e) in enumerate(zip(starts, ends)):
        ax.axvspan(t[s], t[e], color="tab:green", alpha=0.10, label="Atomizer on" if i == 0 else None)


def run_live_plot(log, target, tol=0.5, interval_ms=500, duration_s=None,
                  title="Vial temperature control"):
    """Live plot. Blocks until the window is closed (or duration_s elapses).
    Must run on the main thread (matplotlib GUI requirement)."""
    fig, axes, lines = _make_figure(target, tol, title)
    axes[0].legend(loc="best")
    fig.tight_layout()

    def update(_):
        _draw(log.snapshot(), axes, lines, target, tol)
        return lines

    anim = FuncAnimation(fig, update, interval=interval_ms, cache_frame_data=False)

    timer = None
    if duration_s is not None:
        timer = fig.canvas.new_timer(interval=int(duration_s * 1000))
        timer.single_shot = True
        timer.add_callback(lambda: plt.close(fig))
        timer.start()

    plt.show()
    return anim, timer


# ---------------------------------------------------------------- metrics + report
def compute_metrics(d, target, tol=0.5, settle_window_s=60):
    """Numbers you can quote in the proposal."""
    t, temp, atom = d["t"], d["temp"], d["atom"]
    if len(t) < 2:
        return {}

    m = {"start_temp_C": float(temp[0]), "run_length_s": float(t[-1])}
    in_band = np.abs(temp - target) <= tol

    m["time_to_band_s"] = float(t[np.argmax(in_band)]) if in_band.any() else None

    outside = ~in_band
    if not outside.any():
        m["settling_time_s"] = 0.0
    elif outside[-1]:
        m["settling_time_s"] = None            # never settled inside the band
    else:
        m["settling_time_s"] = float(t[np.where(outside)[0][-1] + 1])

    heating = temp[0] < target
    over = temp.max() - target if heating else target - temp.min()
    m["overshoot_C"] = float(max(over, 0))

    mask = t >= (t[-1] - settle_window_s)
    ss = temp[mask]
    m["steady_state_mean_C"] = float(ss.mean())
    m["steady_state_error_C"] = float(ss.mean() - target)
    m["steady_state_std_C"] = float(ss.std())
    m["steady_state_pct_in_band"] = float(100 * in_band[mask].mean())

    on = atom > 0
    if on.any():
        err = temp[on] - target
        m["atomizer_on_mean_error_C"] = float(err.mean())
        m["atomizer_on_std_C"] = float(err.std())
        m["atomizer_on_max_abs_error_C"] = float(np.abs(err).max())
        m["atomizer_on_pct_in_band"] = float(100 * in_band[on].mean())
    return m


def save_report(log, target, tol=0.5, prefix="run", settle_window_s=60):
    """Writes <prefix>.csv, <prefix>.png (300 dpi) and <prefix>_summary.json, and prints the metrics."""
    d = log.snapshot()
    if len(d["t"]) == 0:
        print("No data recorded.")
        return {}

    with open(f"{prefix}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_s", "temp_C", "target_C", "controller_output", "atomizer_duty_pct"])
        w.writerows(zip(d["t"], d["temp"], d["target"], d["signal"], d["atom"]))

    m = compute_metrics(d, target, tol, settle_window_s)

    title = "Vial temperature control"
    if "steady_state_error_C" in m:
        title += (f"\nsteady state {m['steady_state_mean_C']:.2f} °C "
                  f"(error {m['steady_state_error_C']:+.2f} °C, σ = {m['steady_state_std_C']:.2f} °C)")
    fig, axes, lines = _make_figure(target, tol, title, figsize=(8, 8))
    _draw(d, axes, lines, target, tol)
    _shade_atomizer(axes[0], d["t"], d["atom"])
    axes[0].legend(loc="best")
    fig.tight_layout()
    fig.savefig(f"{prefix}.png", dpi=300)
    plt.close(fig)

    with open(f"{prefix}_summary.json", "w") as f:
        json.dump({"target_C": target, "tolerance_C": tol, **m}, f, indent=2)

    print(f"Saved {prefix}.csv, {prefix}.png, {prefix}_summary.json")
    for k, v in m.items():
        print(f"  {k}: {v}")
    return m
