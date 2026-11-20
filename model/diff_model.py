"""Pseudo-differential VCO ADC model: two rings driven by vcm +/- x, post-layout tt
tuning curve, gain/curvature mismatch between halves. y = yP - yN."""
import sys, numpy as np
sys.path.insert(0, '../sim')
from vco_adc_model import ring_phase_word
from sndr_fit import sndr_fit
V = np.array([0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4])
F = np.array([0.669, 1.036, 1.429, 1.859, 2.297, 2.745, 3.184, 3.452]) * 1e6   # pex tt
cf = np.polyfit(V, F, 4)

def code(v, fs, gain=1.0, n_st=7, seed=0, jit=1e-4):
    f = np.polyval(cf, v) * gain
    rng = np.random.default_rng(seed)
    phi = np.concatenate([[0.0], np.cumsum(f / fs)]) + rng.uniform() + np.cumsum(rng.normal(0, jit, len(v) + 1))
    q = ring_phase_word(phi, n_st)
    return np.sum(q[1:] ^ q[:-1], axis=1).astype(float)

fs, n = 10e6, 1 << 15
fin = fs / n * 41
x = np.sin(2 * np.pi * fin * np.arange(n) / fs)
for amp in (0.1, 0.2, 0.3):
    yp = code(1.0 + amp * x, fs, seed=1)
    r = sndr_fit(yp, fs, fin, 50e3)
    line = f"amp {amp}: single SNDR {r['sndr']:.1f} HD2 {r['hd2']:.1f} HD3 {r['hd3']:.1f} |"
    for mm in (0.0, 0.02, 0.05):
        y = code(1.0 + amp * x, fs, seed=1) - code(1.0 - amp * x, fs, gain=1 + mm, seed=2)
        r = sndr_fit(y, fs, fin, 50e3)
        line += f" mm{mm:.0%}: SNDR {r['sndr']:.1f} HD2 {r['hd2']:.1f} HD3 {r['hd3']:.1f} |"
    print(line)
