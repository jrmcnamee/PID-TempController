"""Side quest: find the PWM frequency that gives the widest, smoothest range of mist control.

For every (frequency, duty) pair the atomizer runs for DWELL_S seconds, then you rate the mist 0-9
(0 = nothing, 9 = maximum). Any number works, so you can replace the rating with a measured mass-loss
rate (g/min) if you weigh the reservoir. Results go to a CSV and a heatmap, and the best frequency is printed.
"""
import csv
import threading
import time

import numpy as np
import matplotlib.pyplot as plt
import serial

import communicationTools as comm

# ---------------- settings ----------------
PORT = "COM3"
FREQS = [5000, 10000, 25000, 50000, 100000]      # Hz; narrow this around the winner for a second, finer pass
DUTIES = list(range(10, 101, 10))                # %
DWELL_S = 6                                      # seconds of mist before you rate it


class KeepAlive(threading.Thread):
    """The Arduino shuts everything off after 2 s of silence, so ping it while you're typing a rating."""

    def __init__(self, arduino, period=0.5):
        super().__init__(daemon=True)
        self.arduino, self.period = arduino, period
        self._halt = threading.Event()

    def run(self):
        while not self._halt.wait(self.period):
            comm.ping(self.arduino)

    def stop(self):
        self._halt.set()


def ask_rating():
    while True:
        s = input("   rating 0-9 (q = stop sweep): ").strip().lower()
        if s == "q":
            return None
        try:
            r = float(s)
            if r >= 0:
                return r
        except ValueError:
            pass
        print("   enter a number, or q")


def run_sweep(arduino):
    rows = []
    for f in FREQS:
        comm.setAtomizerDuty(arduino, 0)
        comm.setAtomizerFreq(arduino, f)
        time.sleep(0.5)
        print(f"\n=== {f} Hz ===")
        for d in DUTIES:
            comm.setAtomizerDuty(arduino, d)
            print(f" {f} Hz, {d}% duty - watching for {DWELL_S} s...")
            time.sleep(DWELL_S)
            r = ask_rating()
            if r is None:
                return rows
            rows.append((f, d, r))
        comm.setAtomizerDuty(arduino, 0)
        time.sleep(2)
    return rows


def analyze(rows):
    """Per frequency: onset duty, saturation duty, how monotonic the response is, and a score."""
    results = {}
    for f in sorted({r[0] for r in rows}):
        pts = sorted((d, r) for ff, d, r in rows if ff == f)
        duties = [p[0] for p in pts]
        ratings = np.array([p[1] for p in pts], dtype=float)
        nz = np.where(ratings > 0)[0]
        if len(nz) == 0:
            results[f] = dict(onset=None, saturation=None, mono=0.0, peak=0.0, range=0.0, score=0.0)
            continue
        peak = ratings.max()
        onset = duties[nz[0]]
        first_nonzero = ratings[nz[0]]
        saturation = duties[int(np.argmax(ratings >= 0.9 * peak))]
        mono = float(np.mean(np.diff(ratings) >= 0)) if len(ratings) > 1 else 1.0
        rng = peak - first_nonzero            # controllable span from weakest to strongest mist
        results[f] = dict(onset=onset, saturation=saturation, mono=mono, peak=peak,
                          range=rng, score=rng * mono)
    return results


def save_outputs(rows, results, prefix):
    with open(f"{prefix}.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["freq_Hz", "duty_pct", "rating"])
        w.writerows(rows)

    freqs = sorted({r[0] for r in rows})
    duties = sorted({r[1] for r in rows})
    grid = np.full((len(freqs), len(duties)), np.nan)
    for f, d, r in rows:
        grid[freqs.index(f), duties.index(d)] = r

    fig, ax = plt.subplots(figsize=(8, 4.5))
    im = ax.imshow(grid, aspect="auto", origin="lower", cmap="viridis")
    ax.set_xticks(range(len(duties)), [str(d) for d in duties])
    ax.set_yticks(range(len(freqs)), [f"{f/1000:g} kHz" for f in freqs])
    ax.set_xlabel("PWM duty (%)")
    ax.set_ylabel("PWM frequency")
    ax.set_title("Mist output vs. PWM frequency and duty")
    fig.colorbar(im, label="Mist rating")
    for i in range(len(freqs)):
        for j in range(len(duties)):
            if not np.isnan(grid[i, j]):
                ax.text(j, i, f"{grid[i, j]:g}", ha="center", va="center", color="w", fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{prefix}.png", dpi=300)
    plt.close(fig)


def main():
    arduino = serial.Serial(port=PORT, baudrate=9600, timeout=1)
    time.sleep(2)
    keep = KeepAlive(arduino)
    keep.start()
    rows = []
    try:
        rows = run_sweep(arduino)
    except KeyboardInterrupt:
        print("\nAborted.")
    finally:
        keep.stop()
        comm.setAtomizerDuty(arduino, 0)
        arduino.flush()
        arduino.close()

    if not rows:
        print("No data.")
        return
    results = analyze(rows)
    prefix = time.strftime("sweep_%Y%m%d_%H%M%S")
    save_outputs(rows, results, prefix)

    print(f"\n{'freq (Hz)':>10} {'onset %':>8} {'sat. %':>7} {'peak':>6} {'range':>6} {'smooth':>7} {'score':>7}")
    for f, r in results.items():
        print(f"{f:>10} {str(r['onset']):>8} {str(r['saturation']):>7} {r['peak']:>6.1f} "
              f"{r['range']:>6.1f} {r['mono']:>7.2f} {r['score']:>7.2f}")
    best = max(results.items(), key=lambda kv: (kv[1]["score"], -(kv[1]["onset"] or 1e9)))
    if best[1]["score"] > 0:
        print(f"\nBest frequency: {best[0]} Hz (onset {best[1]['onset']}% duty). "
              f"Put ATOM_FREQ = {best[0]} and ATOM_ONSET = {best[1]['onset']} in main.py.")
    print(f"Saved {prefix}.csv and {prefix}.png")


if __name__ == "__main__":
    main()
