"""Transistor-level VCO f(Vin) sweep, all corners. Runs ngspice in parallel.
usage: python3 fsweep.py <pdk_root> <outdir> [params...]"""
import subprocess, sys, os, re, itertools, concurrent.futures as cf
pdk, out = sys.argv[1], sys.argv[2]
P = dict(WS=1.0, LS=1.0, WC=1.4, LC=2.86, W1=4.0, L1=1.0, LR=61.33)
for a in sys.argv[3:]:
    k, v = a.split('='); P[k] = float(v)
here = os.path.dirname(os.path.abspath(__file__))
core = open(os.path.join(here, '../netlist/vco_core.spice')).read()
os.makedirs(out, exist_ok=True)
open(os.path.join(out,'.spiceinit'),'w').write('set ngbehavior=hsa\nset skywaterpdk\nset ng_nomodcheck\nset num_threads=1\noption noinit\n')

def run(corner, temp, vin):
    tag = f"{corner}_{temp}_{vin:.2f}"
    net = f"""* fsweep {tag}
.lib {pdk}/sky130A/libs.tech/ngspice/sky130.lib.spice {corner}
.param {' '.join(f'{k}={v}' for k, v in P.items())}
{core}
Vdd vdd 0 1.8
Vin vin 0 {vin}
X vin vs ph0 ph1 ph2 ph3 ph4 ph5 ph6 vdd 0 vco_core
.ic v(x.ph0)=0
.option temp={temp}
.tran 2n 12u
.control
run
meas tran t1 when v(ph0)=0.9 rise=2
meas tran t2 when v(ph0)=0.9 rise=5
meas tran idd avg i(vdd) from=3u to=12u
meas tran vbn avg v(x.vbn) from=3u to=12u
meas tran vlo min v(ph3) from=3u to=12u
meas tran vhi max v(ph3) from=3u to=12u
echo "RES {tag} $&t1 $&t2 $&idd $&vbn $&vlo $&vhi"
.endc
.end
"""
    f = os.path.join(out, tag + '.sp'); open(f, 'w').write(net)
    r = subprocess.run(['ngspice', '-b', f], capture_output=True, text=True, cwd=out)
    m = re.search(r'RES (\S+) (\S+) (\S+) (\S+) (\S+) (\S+) (\S+)', r.stdout)
    if not m: return (tag, None)
    t1, t2, idd, vbn, vlo, vhi = map(float, m.groups()[1:])
    return (tag, (3 / (t2 - t1) if t2 > t1 else 0, -idd, vbn, vlo, vhi))

CORN = os.environ.get('CORNERS', 'tt,ss,ff,sf,fs').split(',')
TEMPS = [int(t) for t in os.environ.get('TEMPS', '27,-20,85').split(',')]
VINS = [float(v) for v in os.environ.get('VINS', '0.5,0.6,0.7,0.8,0.9,1.0,1.1,1.2,1.3,1.4,1.5,1.6').split(',')]
cases = list(itertools.product(CORN, TEMPS, VINS))
with cf.ThreadPoolExecutor(int(os.environ.get("NJ", "16"))) as ex:
    res = list(ex.map(lambda c: run(*c), cases))
for tag, v in res:
    print(tag, 'FAIL' if v is None else ' '.join(f'{x:.4g}' for x in v))
