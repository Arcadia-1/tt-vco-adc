"""Second-order closed-loop version (so_tran.py). End-to-end transient of the pseudo-differential tile (2x VCO + DFF banks + monitors).

Drives ua[0] = vcm + amp*sin and ua[1] = vcm - amp*sin (amp is per side), clocks the
DFFs at fs, records uo_out[7:0] (P half) and uio_out[7:0] (N half), samples both phase
words after every clock edge and runs the off-chip DSP: XOR difference + popcount per
half, y = yN - yP (the integrator inverts). Works on the schematic netlist or on the
extracted layout.

usage: python3 so_tran.py <pdk_root> <outdir> [mode=sch|pex] [corner=tt] [temp=27]
       [fs=10e6] [n=1024] [amp=0.15] [bins=3] [pex=<file>] [tag=...] [dig=0|1]
Sign-off accuracy (default): reltol 1e-4, max step 0.5 ns. A 2 ns step mislocates the
digital edges and adds about 25 dB of fake DAC noise.
"""
import os, re, subprocess, sys
import numpy as np


DIG_MODELS = """
.model a2d adc_bridge(in_low=0.9 in_high=0.9)
.model d2a dac_bridge(out_low=0 out_high=1.8 t_rise=0.3n t_fall=0.3n)
.model dff d_dff(clk_delay=0.3n set_delay=0.3n reset_delay=0.3n)
.model dxor d_xor(rise_delay=0.1n fall_delay=0.1n)
.model dbuf d_buffer(rise_delay=0.1n fall_delay=0.1n)
.model dinv d_inverter(rise_delay=0.05n fall_delay=0.05n)
"""
CELL_BODY = {   # standard cell -> (input pins, behaviour lines using digital nets d_<pin>, output pins)
    "dfxtp": (["D", "CLK"], ["Aff d_D d_CLK null null d_Q nq dff"], ["Q"]),
    "xor2_1": (["A", "B"], ["Ax [d_A d_B] d_X dxor"], ["X"]),
    "buf_4": (["A"], ["Ab d_A d_X dbuf"], ["X"]),
    "inv_1": (["A"], ["Ai d_A d_Y dinv"], ["Y"]),
}


def behav_cells(txt):
    """replace the transistor bodies of the extracted standard cells (flip-flops, XOR, buffer,
    inverter) by XSPICE digital models with the same port lists; wiring parasitics stay."""
    def repl(m):
        head, name = m.group(1), m.group(2)
        key = next((k for k in CELL_BODY if k in name), None)
        if key is None or not name.startswith("sky130_fd_sc_hd__"):
            return m.group(0)
        ins, body, outs = CELL_BODY[key]
        lines = [head]
        for p in ins:
            lines += [f"Cin_{p} {p} VGND 2f", f"Aa_{p} [{p}] [d_{p}] a2d"]
        lines += body
        lines += [f"Ad_{p} [d_{p}] [{p}] d2a" for p in outs]
        return "\n".join(lines) + "\n.ends"
    txt = re.sub(r"^(\.subckt (\S+)[^\n]*(?:\n\+[^\n]*)*)\n.*?^\.ends", repl, txt, flags=re.S | re.M)
    return DIG_MODELS + txt


pdk, out = sys.argv[1], sys.argv[2]
opt = dict(mode='sch', corner='tt', temp='27', fs='10e6', n='1024', vcm='1.0', amp='0.15',
           bins='3', pex='', tag='', redecode='0', vcmp='0.9', skip='60', params='', idealc='1', xopt='reltol:1e-4', tmax='0.5n', dig='0', idealota='0', lr='', t1='0', t2='0', tmon='0', dump='0')
for a in sys.argv[3:]:
    k, v = a.split('=', 1); opt[k] = v
fs, n = float(opt['fs']), int(opt['n'])
vcm, amp = float(opt['vcmp']), float(opt['amp'])
SKIP = int(opt['skip'])
P = dict(WI=8, LI=1, WL=8, LL=1, WT=4, LT=2, LRIN=8.56, LRD=183.6, WCAP=25, LCAP=24, LRB=52.5, LRV=35)
for kv in filter(None, opt['params'].split(',')):
    k, v = kv.split(':'); P[k] = float(v)
fin = int(opt['bins']) * fs / n
here = os.path.dirname(os.path.abspath(__file__))
os.makedirs(out, exist_ok=True)
open(os.path.join(out, '.spiceinit'), 'w').write(
    'set ngbehavior=hsa\nset skywaterpdk\nset ng_nomodcheck\nset num_threads=1\noption noinit\noption klu\n')
tag = opt['tag'] or f"{opt['mode']}_{opt['corner']}_{opt['temp']}_{int(fs/1e6)}M_{amp}"

core = os.path.join(here, '../netlist/so_core.spice')
if opt['idealc'] == '1':      # MIM model (series R network) doubles the run time; use an ideal C for sizing
    txt = open(core).read()
    for c in ('XC1', 'XC2'):
        txt = txt.replace(f"{c} vg vctrl sky130_fd_pr__cap_mim_m3_1 W={{WCAP}} L={{LCAP}}",
                          f"{c[1:]} vg vctrl {{2e-15*WCAP*LCAP + 0.38e-15*(WCAP+LCAP)}}")
    if opt['idealota'] == '1':     # diagnostic: OTA as a stiff gain-2000 amplifier
        import re as _re
        txt = _re.sub(r"\.subckt ota5t.*?\.ends", ".subckt ota5t inp inn out vbn vdd gnd\n"
                      "Bo out gnd V=max(0.05, min(1.75, 1.0 + 2000*(V(inp)-V(inn))))\n.ends", txt, flags=_re.S)
    core = os.path.join(out, f"so_core_{opt['tag'] or 'x'}.spice")
    open(core, 'w').write(txt)
vcof = os.path.join(here, '../verify/vco_core_lvs.spice')
if opt['lr']:                     # sizing: V-to-I resistor strip length (both strips of each half)
    t_ = open(vcof).read()
    for r_ in ('XRP2 vsp mp', 'XRP1 mp gnd', 'XRN1 vsn mn', 'XRN2 mn gnd'):
        t_ = re.sub(rf"({r_} gnd \S+) L=\S+", rf"\1 L={opt['lr']}", t_)
    vcof = os.path.join(out, f"vco_core_{opt['tag'] or 'x'}.spice")
    open(vcof, 'w').write(t_)
if opt['mode'] == 'sch' and opt['dig'] == '1':
    # fast testbench: registers / XORs as XSPICE digital models; VCO, OTA, DAC, bias at transistor
    # level. Diagnostics: t1=1 puts the first rank (dfxtp_4, sampling the ring) back at transistor
    # level, t2=1 the second rank and the XORs that drive the DAC. Otherwise 3 fF per ring phase
    # stands in for the flip-flop input.
    sc = "sky130_fd_sc_hd__"
    T1, T2 = opt['t1'] == '1', opt['t2'] == '1'
    ph = [f"p{i}" for i in range(7)] + [f"m{i}" for i in range(7)]
    dq = [f"q{i}" for i in range(7)] + [f"n{i + 1}" for i in range(7)]
    bits = [f"bp{i}" for i in range(7)] + [f"bn{i}" for i in range(7)]
    L_ = [f".include {vcof}", f".include {core}",
          f".include {pdk}/sky130A/libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice",
          f".param {' '.join(f'{k}={v}' for k, v in P.items())}",
          "XvcoP vcp vsp p0 p1 p2 p3 p4 p5 p6 vdd 0 vco_core",
          "XvcoN vcn vsn m0 m1 m2 m3 m4 m5 m6 vdd 0 vco_core",
          "Xr vsp vsn 0 rarray",
          "XlP ua0 vcp bp0 bp1 bp2 bp3 bp4 bp5 bp6 vref vbn rst vdd 0 so_loop",
          "XlN ua1 vcn bn0 bn1 bn2 bn3 bn4 bn5 bn6 vref vbn rst vdd 0 so_loop",
          "Xbias vref vbn vdd 0 so_bias", "Brst rst 0 V=1.8-V(rst_n)",
          ".model a2d adc_bridge(in_low=0.9 in_high=0.9)",
          ".model d2a dac_bridge(out_low=0 out_high=1.8 t_rise=0.3n t_fall=0.3n)",
          ".model dff d_dff(clk_delay=0.3n set_delay=0.3n reset_delay=0.3n)",
          ".model dxor d_xor(rise_delay=0.1n fall_delay=0.1n)",
          "Aclk [clk] [dclk] a2d",
          *(["XmonP p0 0 0 vdd vdd q7 sky130_fd_sc_hd__buf_4", "XmonN m0 0 0 vdd vdd n0 sky130_fd_sc_hd__buf_4"]
            if opt['tmon'] == '1' else ["Amon [p0 m0] [dp0 dm0] a2d", "Amo [dp0 dm0] [q7 n0] d2a"])]
    if T1:      # first rank at transistor level, its Q (analog, pin load) bridged into digital
        L_ += [f"Xd{i} clk {ph[i]} 0 0 vdd vdd {dq[i]} {sc}dfxtp_4" for i in range(14)]
        if not T2:
            L_.append(f"Aq [{' '.join(dq)}] [{' '.join('d' + q for q in dq)}] a2d")
    else:
        L_ += [f"Cph{p} {p} 0 3f" for p in ph]
        L_.append(f"Aph [{' '.join(ph)}] [{' '.join('d' + p for p in ph)}] a2d")
        L_ += [f"Ad1{i} d{ph[i]} dclk null null d{dq[i]} nul1{i} dff" for i in range(14)]
        L_.append(f"Aq [{' '.join('d' + q for q in dq)}] [{' '.join(dq)}] d2a")
    if T2:      # second rank + XOR at transistor level, the XOR drives the DAC element
        L_ += [f"Xe{i} clk {dq[i]} 0 0 vdd vdd qq{i} {sc}dfxtp_1\nXx{i} {dq[i]} qq{i} 0 0 vdd vdd {bits[i]} {sc}xor2_1"
               for i in range(14)]
    else:
        L_ += [f"Ad2{i} d{dq[i]} dclk null null dd{dq[i]} nul2{i} dff\nAx{i} [d{dq[i]} dd{dq[i]}] dx{i} dxor"
               for i in range(14)]
        L_.append(f"Ab [{' '.join(f'dx{i}' for i in range(14))}] [{' '.join(bits)}] d2a")
    dut = "\n".join(L_) + "\n"
elif opt['mode'] == 'sch':
    sc = "sky130_fd_sc_hd__"
    dut = f"""
.include {vcof}
.include {pdk}/sky130A/libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice
.include {core}
.param {' '.join(f'{k}={v}' for k, v in P.items())}
XvcoP vcp vsp p0 p1 p2 p3 p4 p5 p6 vdd 0 vco_core
XvcoN vcn vsn m0 m1 m2 m3 m4 m5 m6 vdd 0 vco_core
Xr vsp vsn 0 rarray
XlP ua0 vcp bp0 bp1 bp2 bp3 bp4 bp5 bp6 vref vbn rst vdd 0 so_loop
XlN ua1 vcn bn0 bn1 bn2 bn3 bn4 bn5 bn6 vref vbn rst vdd 0 so_loop
Xbias vref vbn vdd 0 so_bias
Xrst rst_n 0 0 vdd vdd rst {sc}inv_1
""" + "\n".join(f"XdP{i} clk p{i} 0 0 vdd vdd q{i} {sc}dfxtp_4\nXdN{i} clk m{i} 0 0 vdd vdd n{i + 1} {sc}dfxtp_4\n"
                f"XeP{i} clk q{i} 0 0 vdd vdd qq{i} {sc}dfxtp_1\nXeN{i} clk n{i + 1} 0 0 vdd vdd nn{i} {sc}dfxtp_1\n"
                f"XxP{i} q{i} qq{i} 0 0 vdd vdd bp{i} {sc}xor2_1\nXxN{i} n{i + 1} nn{i} 0 0 vdd vdd bn{i} {sc}xor2_1"
                for i in range(7)) + f"""
XmonP p0 0 0 vdd vdd q7 {sc}buf_4
XmonN m0 0 0 vdd vdd n0 {sc}buf_4
"""
else:
    # extracted top cell; pin order taken from its .subckt line
    txt = open(opt['pex']).read()
    if opt['dig'] == '1':
        txt = behav_cells(txt)
        pexf = os.path.join(out, f"pex_dig_{opt['tag'] or 'x'}.spice")
        open(pexf, 'w').write(txt)
        opt['pex'] = pexf
    m = re.search(r"^\.subckt tt_um_arcadia1_vco_adc (.*?)\n(?!\+)", txt, re.S | re.M)
    pins = m.group(1).replace('\n+', ' ').split()
    conn = {'VGND': '0', 'VDPWR': 'vdd', 'clk': 'clk', 'rst_n': 'rst_n', 'ua[0]': 'ua0', 'ua[1]': 'ua1'}
    conn.update({f'uo_out[{i}]': f'q{i}' for i in range(8)})
    conn.update({f'uio_out[{i}]': f'n{i}' for i in range(8)})
    conn.update({f'uio_oe[{i}]': 'vdd' for i in range(8)})
    # stripes left unconnected in a copy without the decap field come out as VDPWR_uq<n> / VGND_uq<n>
    conn.update({p: ('vdd' if p.startswith('VDPWR') else '0') for p in pins if re.match(r'(VDPWR|VGND)_uq', p)})
    nodes = [conn.get(p, f"nc_{re.sub(r'[^A-Za-z0-9]', '_', p)}") for p in pins]
    dut = f".include {os.path.abspath(opt['pex'])}\nXdut {' '.join(nodes)} tt_um_arcadia1_vco_adc\n"

tstop = (n + SKIP + 8) / fs
outs = [f"q{i}" for i in range(8)] + [f"n{i}" for i in range(8)]
# save only what is read back: the default (every node of the circuit) needs tens of GB at
# a 0.5 ns step and drove the server out of memory
sv = ['v(clk)'] + [f'v({o})' for o in outs] + ['i(vdd)']
if opt['mode'] == 'sch':
    sv += ['v(vcp)', 'v(vcn)', 'v(vref)', 'v(vbn)', 'v(xlp.vg)']
if opt['dump'] == '1':
    sv += [f'v({x}{i})' for i in range(7) for x in ('bp', 'q', 'p')]
save_line = '.save ' + ' '.join(dict.fromkeys(sv))
net = f"""* {tag}
.lib {pdk}/sky130A/libs.tech/ngspice/sky130.lib.spice {opt['corner']}
{dut}
Vdd vdd 0 1.8
Vinp ua0 0 sin({vcm} {amp} {fin} {4/fs})
Vinn ua1 0 sin({vcm} {-amp} {fin} {4/fs})
Vrst rst_n 0 pwl(0 0 {SKIP / 3 / fs} 0 {SKIP / 3 / fs + 1e-9} 1.8)
Vclk clk 0 pulse(0 1.8 {0.5/fs} 1n 1n {0.5/fs - 1e-9} {1/fs})
""" + "\n".join(f"Cl_{o} {o} 0 1p" for o in outs) + f"""
.option temp={opt['temp']} method=gear {opt['xopt'].replace(':', '=')}
{save_line}
.tran 1n {tstop} 0 {opt['tmax']}
.control
run
meas tran idd avg i(vdd) from={20/fs} to={tstop}
wrdata {tag}.dat v(clk) {' '.join(f'v({o})' for o in outs)}
{'wrdata ' + tag + '_vc.dat v(vcp) v(vcn) v(vref) v(vbn) v(xlp.vg)' if opt['mode'] == 'sch' else ''}
{'wrdata ' + tag + '_bits.dat v(clk) v(xlp.vg) ' + ' '.join(f'v(bp{i}) v(q{i}) v(p{i})' for i in range(7)) if opt['dump'] == '1' else ''}
.endc
.end
"""
if opt['redecode'] == '1':          # analyse an earlier run from its saved waveforms
    stdout = open(os.path.join(out, tag + '.log')).read()
else:
    f = os.path.join(out, tag + '.sp'); open(f, 'w').write(net)
    r = subprocess.run(['ngspice', '-b', f], capture_output=True, text=True, cwd=out)
    stdout = r.stdout
    open(os.path.join(out, tag + '.log'), 'w').write(r.stdout + r.stderr)
mi = re.search(r"idd\s+=\s+(\S+)", stdout)
idd = -float(mi.group(1)) if mi else float('nan')

d = np.loadtxt(os.path.join(out, tag + '.dat'))
t = d[:, 0]
v = d[:, 3::2]            # 16 outputs (wrdata repeats the time column)
# sample 0.4/fs after each rising clock edge (Q settled, before next edge)
edges = 1.0 / fs * (np.arange(n + SKIP + 6) + 0.5) + 0.4 / fs
idx = np.searchsorted(t, edges)
idx = idx[idx < len(t)]


def code(cols):
    word = (v[idx][:, cols] > 0.9).astype(int)
    y = np.sum(word[1:] ^ word[:-1], axis=1)
    return y[SKIP:SKIP + n].astype(float)


def fmon(col):
    b = v[:, col] > 0.9
    rises = t[1:][(~b[:-1]) & b[1:]]
    return (len(rises) - 1) / (rises[-1] - rises[0]) if len(rises) > 2 else 0


# P: uo_out[6:0] = phases, uo_out[7] = monitor; N (mirror image): uio_out[7:1] = phases, uio_out[0] = monitor
yp, yn = code(list(range(7))), code(list(range(9, 16)))


def score(y, bw):
    """coherent tone at bin `bins`, Hann window, 5-bin signal and harmonic groups."""
    m = len(y); s_ = np.abs(np.fft.rfft((y - y.mean()) * np.hanning(m))) ** 2
    k, kb = int(opt['bins']), int(bw / fs * m)
    grp = lambda c: s_[c - 2:c + 3].sum()
    sig, band = grp(k), s_[1:kb + 1].sum() - grp(k)
    harm = sum(grp(h * k) for h in (2, 3) if h * k + 2 <= kb)
    return dict(sndr=10 * np.log10(sig / band), snr=10 * np.log10(sig / (band - harm)),
                hd2=10 * np.log10(grp(2 * k) / sig), hd3=10 * np.log10(grp(3 * k) / sig), amp=np.sqrt(sig))


y = yn - yp                       # the integrator inverts: VINP up -> yP down
res = {bw: score(y, bw) for bw in (20e3, 50e3, 100e3)}
rp = score(-yp, 50e3)
np.save(os.path.join(out, tag + '_yp.npy'), yp)
np.save(os.path.join(out, tag + '_yn.npy'), yn)
print(f"RESULT {tag} samples={len(y)} yP=[{yp.min():.0f},{yp.max():.0f}] yN=[{yn.min():.0f},{yn.max():.0f}] "
      f"fP={yp.mean()*fs/14/1e6:.3f}MHz(mon {fmon(7)/1e6:.3f}) fN={yn.mean()*fs/14/1e6:.3f}MHz(mon {fmon(8)/1e6:.3f}) "
      f"Idd={idd*1e6:.2f}uA | P-only@50k SNDR={rp['sndr']:.1f} HD2={rp['hd2']:.1f} | "
      f"diff amp={res[50e3]['amp']:.3f} HD2={res[50e3]['hd2']:.1f} HD3={res[50e3]['hd3']:.1f} "
      + " ".join(f"@{int(bw/1e3)}k:SNDR={r['sndr']:.1f}/SNR={r['snr']:.1f}" for bw, r in res.items()))
