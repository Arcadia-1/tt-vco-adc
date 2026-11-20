"""Behavioral model of the second-order closed-loop VCO delta-sigma ADC.

Loop (per half, pseudo-differential later):
  Vin -> Gm (input resistor into OTA virtual ground) -> integrator C -> Vctrl -> VCO
  VCO phase sampled by N flip-flops at fs; y[n] = popcount(PH[n] xor PH[n-1]) (0..N)
  each xor bit drives one unit current element of the feedback DAC (rotating use = DEM)
  DAC current is subtracted at the virtual ground during the next clock period.
Orders: the OTA integrator plus the VCO (phase integrates frequency) -> 2nd order.

Normalized: x = integrator output scaled so that the VCO increment per sample is
dphi = (f0 + kv*x)/fs cycles. u = input in code units (full scale +-N/2 around N/2).
Each sample: x += a1 * (u + N/2 - y_prev_dac)   (excess delay td in samples, 0..1)

usage: python3 so_model.py
"""
import sys
import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from vco_adc_model import ring_phase_word


def run(n_st=7, fs=10e6, f0=None, kv=0.5, a1=0.2, amp=0.5, n=1 << 15, bins=41, td=0.5,
        dac_mm=0.0, jit=0.0, sub=8, seed=1):
    """returns y and fin. Simulates with `sub` sub-steps per clock (continuous-time integrator)."""
    rng = np.random.default_rng(seed)
    f0 = fs * 0.25 if f0 is None else f0            # mid-scale: y around N/2 needs f = N/2 / (2N) fs = fs/4
    fin = fs / n * bins
    w = 1 + dac_mm * rng.standard_normal(n_st)      # DAC element mismatch
    phi, x = rng.uniform(), 0.0
    word_prev = ring_phase_word(np.array([phi]), n_st)[0]
    mid = np.full(n_st, 0.5)
    b_old, b_new = mid, mid          # bits from edges k-2 and k-1
    y = np.empty(n)
    for k in range(n):
        for s in range(sub):
            t = (k + s / sub) / fs
            u = amp * (n_st / 2) * np.sin(2 * np.pi * fin * t)
            dac = (b_old if s / sub < td else b_new) @ w
            x += a1 / sub * (u + n_st / 2 - dac)
            phi += (f0 + kv * fs * x) / fs / sub + (rng.normal(0, jit) if jit else 0)
        word = ring_phase_word(np.array([phi]), n_st)[0]
        bk = (word ^ word_prev).astype(float)
        y[k] = bk.sum()
        word_prev = word
        b_old, b_new = b_new, bk
    return y, fin


def sndr(y, fs, fin, bw):
    n = len(y)
    w = np.blackman(n)
    s = np.abs(np.fft.rfft((y - y.mean()) * w)) ** 2
    f = np.fft.rfftfreq(n, 1 / fs)
    k = int(round(fin / fs * n))
    sig = s[k - 4:k + 5].sum()
    band = (f > 3 * fs / n) & (f <= bw)
    return 10 * np.log10(sig / (s[band].sum() - sig))


if __name__ == "__main__":
    fs = 10e6
    print("loop-gain sweep (N=7, td=0.5, amp=0.5 FS, fin 12.5 kHz):")
    for kv in (0.2, 0.5, 1.0):
        for a1 in (0.1, 0.2, 0.4):
            y, fin = run(kv=kv, a1=a1, n=1 << 15)
            ok = y.max() < 7
            print(f"  kv={kv} a1={a1}: y[{y.min():.0f},{y.max():.0f}] "
                  f"SNDR@20k={sndr(y, fs, fin, 20e3):.1f} @50k={sndr(y, fs, fin, 50e3):.1f}"
                  + ("" if ok else "  (saturates)"))
