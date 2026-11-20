"""Sine-fit SNDR for short coherent records (FFT windows leak too much when the
band holds only ~20 bins). Fit dc + drift + fundamental (+ harmonics for SNR),
then measure the residual power below bw with a rectangular FFT."""
import numpy as np


def sndr_fit(y, fs, fin, bw, nharm=5):
    n = len(y)
    t = np.arange(n)
    w0 = 2 * np.pi * fin / fs

    def fit(h):
        cols = [np.ones(n), t / n]
        for k in range(1, h + 1):
            cols += [np.sin(k * w0 * t), np.cos(k * w0 * t)]
        A = np.array(cols).T
        c, *_ = np.linalg.lstsq(A, y, rcond=None)
        return c, y - A @ c

    def band_power(r):
        R = np.abs(np.fft.rfft(r)) ** 2 / n ** 2 * 2
        f = np.fft.rfftfreq(n, 1 / fs)
        return R[(f > 0) & (f <= bw)].sum()

    c1, r1 = fit(1)
    ch, rh = fit(nharm)
    a1 = np.hypot(c1[2], c1[3])
    ps = a1 ** 2 / 2
    hd = [20 * np.log10(np.hypot(ch[2 + 2 * k], ch[3 + 2 * k]) / a1) for k in range(1, nharm)]
    return dict(amp=a1, sndr=10 * np.log10(ps / band_power(r1)),
                snr=10 * np.log10(ps / band_power(rh)), hd2=hd[0], hd3=hd[1])
