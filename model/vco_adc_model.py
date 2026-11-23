"""Ring-oscillator quantizer model: phase word of an N-stage ring sampled by DFFs.

ring_phase_word() gives the sampled phase word; y[n] = popcount of the XOR with the
previous word = number of stage transitions in one clock period. so_model.py uses it
as the quantizer of the second-order loop; run alone, this file sweeps the open-loop
quantizer by itself.

Usage: python3 vco_adc_model.py   (prints SQNR vs settings)
"""
import numpy as np


def ring_phase_word(phase_cycles, n_stages):
    """Logic state of each stage for a ring whose total phase is given in cycles.

    In an N-stage ring the 2N half-period events are spread uniformly over one
    cycle. Stage k toggles at phase k/(2N) + m/2 (alternating polarity), so
    its state is floor(2*phi - k/N) mod 2 (up to a fixed inversion pattern
    that the XOR differencing removes).
    """
    k = np.arange(n_stages)
    return (np.floor(2.0 * phase_cycles[:, None] - k[None, :] / n_stages) % 2).astype(int)


def simulate(n_stages=7, fs=10e6, f_center=2.5e6, kvco=4e6, amp=0.4, fin=None,
             n=1 << 16, jitter_rms=0.0, nonlin=0.0, seed=1):
    """Return (y, f_inst). kvco in Hz per unit input; amp is input amplitude."""
    rng = np.random.default_rng(seed)
    if fin is None:
        fin = fs / n * 37  # coherent bin
    t = np.arange(n) / fs
    x = amp * np.sin(2 * np.pi * fin * t)
    f = f_center + kvco * (x + nonlin * x**2)
    phi = np.concatenate([[0.0], np.cumsum(f / fs)])
    if jitter_rms:
        # jitter_rms: rms phase increment noise per sample, in cycles (random walk)
        phi += np.cumsum(rng.normal(0, jitter_rms, n + 1))
    q = ring_phase_word(phi, n_stages)
    y = np.sum(q[1:] ^ q[:-1], axis=1)
    return y, f, fin, x


def sndr(y, fs, fin, bw):
    n = len(y)
    w = np.hanning(n)
    s = np.abs(np.fft.rfft((y - y.mean()) * w)) ** 2
    f = np.fft.rfftfreq(n, 1 / fs)
    kin = int(round(fin / fs * n))
    sig = s[kin - 3:kin + 4].sum()
    band = (f > 0) & (f <= bw)
    noise = s[band].sum() - sig
    return 10 * np.log10(sig / noise)


if __name__ == "__main__":
    fs = 10e6
    print("max transitions per sample must stay < N (f_vco < fs/2)")
    for n_st in (5, 7, 9):
        for bw in (20e3, 100e3):
            y, f, fin, _ = simulate(n_stages=n_st, fs=fs)
            print(f"N={n_st} fs=10M BW={bw/1e3:.0f}k  y in [{y.min()},{y.max()}]  "
                  f"SQNR={sndr(y, fs, fin, bw):.1f} dB")
    # sensitivity to VCO nonlinearity and phase noise
    for nl in (0.0, 0.05, 0.2):
        y, f, fin, _ = simulate(nonlin=nl)
        print(f"nonlin x^2 coef {nl}: SNDR(20k)={sndr(y, fs, fin, 20e3):.1f} dB")
    for jit in (1e-5, 1e-4, 1e-3):
        y, f, fin, _ = simulate(jitter_rms=jit)
        print(f"phase noise {jit:g} cycle/sample: SNDR(20k)={sndr(y, fs, fin, 20e3):.1f} dB")
