"""VCO sizing for linearity: N-stage ring, f(Vin) by short transients, then the
harmonics of the pseudo-differential output predicted from the fitted curve.

Each config: f at Vin = 0.70 .. 1.30 V (step 0.05), polynomial fit, then
y(t) = f(1 + A sin) - f(1 - A sin) sampled and FFT'd -> HD3 (HD2 cancels) and the
single-ended HD2. A 3 fF load per phase stands in for the flip-flop input and wiring.

usage: python3 vco_lin.py <pdk_root> <outdir> [corner=tt] [temp=27] [amp=0.15]
       configs are listed in CONFIGS below (name, params)
"""
import concurrent.futures as cf
import os
import re
import subprocess
import sys

import numpy as np

pdk, out = sys.argv[1], sys.argv[2]
opt = dict(corner='tt', temp='27', amp='0.15', only='')
for a in sys.argv[3:]:
    k, v = a.split('=', 1); opt[k] = v
os.makedirs(out, exist_ok=True)
open(os.path.join(out, '.spiceinit'), 'w').write(
    'set ngbehavior=hsa\nset skywaterpdk\nset ng_nomodcheck\nset num_threads=1\noption noinit\n')

BASE = dict(N=7, WS=1.0, LS=1.0, WC=1.4, LC=2.86, W1=4.0, L1=1.0, LR=61.33, CL=3e-15)
CONFIGS = [
    ("now7", {}),
    ("n15_lc1.0", dict(N=15, LC=1.0)),
    ("n15_lc0.8", dict(N=15, LC=0.8)),
    ("n15_lc0.6", dict(N=15, LC=0.6)),
    ("n15_lc1.0_w1x2", dict(N=15, LC=1.0, W1=8.0)),
    ("n15_lc1.0_w1x4", dict(N=15, LC=1.0, W1=16.0)),
    ("n15_lc1.0_w1x4_l2", dict(N=15, LC=1.0, W1=32.0, L1=2.0)),
    ("n15_lc1.0_ws2", dict(N=15, LC=1.0, WS=2.0, W1=16.0)),
    ("n15_lc1.0_ls2", dict(N=15, LC=1.0, LS=2.0, WS=2.0, W1=16.0)),
]
VINS = [round(0.70 + 0.05 * k, 2) for k in range(13)]


def netlist(p):
    n = int(p["N"])
    st = "\n".join(f"X{i} ph{(i - 1) % n} ph{i} vbp vbn vdd gnd csinv" for i in range(n))
    cl = "\n".join(f"Cl{i} ph{i} gnd {p['CL']}" for i in range(n))
    return f"""
.subckt csinv in out vbp vbn vdd gnd
XMph x   vbp vdd vdd sky130_fd_pr__pfet_01v8 W={p['WS']} L={p['LS']}
XMpi out in  x   vdd sky130_fd_pr__pfet_01v8 W=1.0 L=0.15
XMni out in  y   gnd sky130_fd_pr__nfet_01v8 W=0.5 L=0.15
XMnf y   vbn gnd gnd sky130_fd_pr__nfet_01v8 W={p['WS'] / 2} L={p['LS']}
XMc  gnd out gnd gnd sky130_fd_pr__nfet_01v8 W={p['WC']} L={p['LC']}
.ends
.subckt vco vin vdd gnd
XM1  vbp vin vs  gnd sky130_fd_pr__nfet_01v8 W={p['W1']} L={p['L1']}
XR1  vs  gnd gnd sky130_fd_pr__res_xhigh_po_0p35 L={p['LR']}
XMpd vbp vbp vdd vdd sky130_fd_pr__pfet_01v8 W={p['WS']} L={p['LS']}
XMp2 vbn vbp vdd vdd sky130_fd_pr__pfet_01v8 W={p['WS']} L={p['LS']}
XMnd vbn vbn gnd gnd sky130_fd_pr__nfet_01v8 W={p['WS'] / 2} L={p['LS']}
{st}
{cl}
.ends
"""


def run(name, p, vin):
    tag = f"{name}_{vin:.2f}"
    net = f"""* {tag}
.lib {pdk}/sky130A/libs.tech/ngspice/sky130.lib.spice {opt['corner']}
{netlist(p)}
Vdd vdd 0 1.8
Vin vin 0 {vin}
X vin vdd 0 vco
.ic v(x.ph0)=0
.option temp={opt['temp']}
.tran 2n 16u
.control
run
meas tran t1 when v(x.ph0)=0.9 rise=3
meas tran t2 when v(x.ph0)=0.9 rise=8
meas tran idd avg i(vdd) from=4u to=16u
echo "RES $&t1 $&t2 $&idd"
.endc
.end
"""
    f = os.path.join(out, tag + '.sp'); open(f, 'w').write(net)
    r = subprocess.run(['ngspice', '-b', f], capture_output=True, text=True, cwd=out)
    m = re.search(r'RES (\S+) (\S+) (\S+)', r.stdout)
    if not m:
        return name, vin, float('nan'), float('nan')
    t1, t2, idd = map(float, m.groups())
    return name, vin, 5 / (t2 - t1) if t2 > t1 else float('nan'), -idd


cfgs = [(n, {**BASE, **c}) for n, c in CONFIGS if not opt['only'] or n in opt['only'].split(',')]
jobs = [(n, p, v) for n, p in cfgs for v in VINS]
with cf.ThreadPoolExecutor(int(os.environ.get('NJ', '24'))) as ex:
    res = list(ex.map(lambda j: run(*j), jobs))

A = float(opt['amp'])
print(f"corner {opt['corner']} {opt['temp']}C, amplitude {A} V per side")
for n, p in cfgs:
    v = np.array([r[1] for r in res if r[0] == n])
    f = np.array([r[2] for r in res if r[0] == n])
    i = np.array([r[3] for r in res if r[0] == n])
    ok = np.isfinite(f)
    c = np.polyfit(v[ok] - 1.0, f[ok], 5)
    t = np.arange(4096) / 4096 * 2 * np.pi * 7
    def hd(y):
        s = np.abs(np.fft.rfft(y - y.mean()))
        return 20 * np.log10(s[14] / s[7]), 20 * np.log10(s[21] / s[7])
    hd2se, hd3se = hd(np.polyval(c, A * np.sin(t)))
    _, hd3d = hd(np.polyval(c, A * np.sin(t)) - np.polyval(c, -A * np.sin(t)))
    kv = np.polyval(np.polyder(c), 0)
    n_st = int(p['N'])
    # quantization-limited SNR of the differential code (first order, OSR from fs/(2*50k))
    fs, osr = 10e6, 100
    amp_lsb = 2 * n_st * kv * A / fs * 2           # P - N amplitude in code units
    sqnr = 10 * np.log10((amp_lsb ** 2 / 2) / ((1 / 12) * 2 * np.pi ** 2 / 3 / osr ** 3))
    print(f"{n:22s} f(0.7/1.0/1.3)={f[0]/1e6:.2f}/{f[6]/1e6:.2f}/{f[-1]/1e6:.2f} MHz "
          f"Kv={kv/1e6:.2f} MHz/V I(1.0)={i[6]*1e6:.1f} uA  HD2se={hd2se:.1f} HD3se={hd3se:.1f} "
          f"HD3diff={hd3d:.1f} dBc  SQNR~{sqnr:.1f} dB")
