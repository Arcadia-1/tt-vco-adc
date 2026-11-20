"""Off-chip DSP for tt_um_arcadia1_vco_adc captures (pseudo-differential, second-order loop).

Input: one 16-bit sample per clock, low byte = uio[7:0] (N half), high byte =
uo_out[7:0] (P half). P: uo_out[6:0] are the 7 sampled ring phases, uo_out[7] the monitor.
N: uio[7:1] are the sampled phases, uio[0] the monitor (the N half is the mirror image of
the P half, so its monitor lands on the mirrored pin). The bit order of the phases does not
matter: the popcount below is the same for any permutation. The PIO capture script packs two samples per
little-endian 32-bit word, first sample in the upper half.

    python3 decode_vco_adc.py vco_adc.bin [--fs 10e6] [--bw 50e3] [--raw16]

Per half: y[n] = popcount(phase[n] xor phase[n-1]), the same count the on-chip DAC fed back
(second-order shaped). The loop integrator inverts, so a higher VINP lowers yP.
ADC output: y = yN - yP, then low-pass/decimate. Prints both VCO frequencies and the
SNDR of P alone and of the difference.
"""
import argparse
import numpy as np


def load(path, raw16):
    if raw16:
        return np.fromfile(path, dtype='<u2').astype(np.uint16)
    w = np.fromfile(path, dtype='<u4')
    return np.stack([w >> 16, w & 0xFFFF], axis=1).reshape(-1).astype(np.uint16)


def phases_to_code(p):
    """y[n] = popcount(phase[n] XOR phase[n-1]) over the 7 ring phases."""
    p = (p & 0x7F).astype(np.uint8)
    x = p[1:] ^ p[:-1]
    return np.unpackbits(x[:, None], axis=1).sum(axis=1).astype(float)


def sndr(y, fs, bw):
    n = len(y)
    w = np.blackman(n)
    s = np.abs(np.fft.rfft((y - y.mean()) * w)) ** 2
    f = np.fft.rfftfreq(n, 1 / fs)
    band = (f > 2 * fs / n) & (f <= bw)
    k = np.argmax(np.where(band, s, 0))
    sig = s[max(k - 3, 1):k + 4].sum()
    noise = s[band].sum() - sig
    return f[k], 10 * np.log10(sig / noise)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('file')
    ap.add_argument('--fs', type=float, default=10e6)
    ap.add_argument('--bw', type=float, default=50e3)
    ap.add_argument('--raw16', action='store_true', help='plain little-endian 16-bit stream')
    a = ap.parse_args()
    s = load(a.file, a.raw16)
    yp, yn = phases_to_code(s >> 8), phases_to_code(s >> 1)
    for name, y in (('P', yp), ('N', yn)):
        print(f'{name}: code range [{y.min():.0f}, {y.max():.0f}]  f_vco = {y.mean()*a.fs/14/1e6:.4f} MHz')
        if y.max() >= 7:
            print(f'WARNING: {name} code reached 7: the input is beyond full scale (about +-0.3 V per side)')
    for name, y in (('P only', yp), ('N - P', yn - yp)):
        fin, v = sndr(y, a.fs, a.bw)
        print(f'{name}: tone {fin:.1f} Hz, SNDR in {a.bw/1e3:.0f} kHz = {v:.1f} dB')


if __name__ == '__main__':
    main()
