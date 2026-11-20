"""Layout generator for tt_um_arcadia1_vco_adc (sky130A, TT 1x2 analog tile), v2.

Floorplan (mirror-symmetric about the tile centre line x = XC):
  * cell vco_adc_half: VCO (V-to-I M1, bias mirror, 7-stage current-starved ring,
    NMOS load caps) inside a p-tap guard ring, the 7 sampling flip-flops plus a
    monitor buffer above it, local phase routing, rails strapped to the edge stripes.
    Placed twice: P half as drawn right of XC, N half mirrored left of XC.
  * Bias resistors of both halves: one xhigh-poly array on the centre line,
    D N P P N D (common centroid, dummies at both ends) with its own guard ring.
  * VINP / VINN: a parallel met3 pair with VGND shield lines on both sides.
  * Clock: from the clk pin to a met2 spine on the centre line, then a met3 bus that
    reaches both halves with equal length.
  * Power: VGND/VDPWR met4 stripes at both edges (mirror positions), decap rows
    (sky130_fd_sc_hd__decap_12) fill the lower part of the tile.

usage: python3 gen_layout.py <template.def> <outdir>
       writes <outdir>/half.tcl, <outdir>/top.tcl, <outdir>/lvs_ref.v
"""
import os
import sys

TOP = "tt_um_arcadia1_vco_adc"
HALF = "vco_adc_half"
L = []


def q(v):
    return f"{round(v * 200) / 200:.3f}um"


def rect(layer, x1, y1, x2, y2):
    x1, x2 = sorted((x1, x2))
    y1, y2 = sorted((y1, y2))
    L.append(f"box {q(x1)} {q(y1)} {q(x2)} {q(y2)}; paint {layer}")


def sq(layer, cx, cy, s):
    rect(layer, cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2)


def mcon(cx, cy, m1=0.29):
    sq("mcon", cx, cy, 0.17)
    sq("met1", cx, cy, m1)


def via1(cx, cy):
    sq("met1", cx, cy, 0.38); sq("met2", cx, cy, 0.38); sq("via1", cx, cy, 0.26)


def via2(cx, cy):
    sq("met2", cx, cy, 0.42); sq("met3", cx, cy, 0.5); sq("via2", cx, cy, 0.28)


def via3(cx, cy):
    sq("met3", cx, cy, 0.52); sq("met4", cx, cy, 0.52); sq("via3", cx, cy, 0.32)


def stack(cx, cy, frm, to):
    f = {1: via1, 2: via2, 3: via3}
    for lv in range(frm, to):
        f[lv](cx, cy)


def hwire(layer, x1, x2, y, w):
    rect(layer, x1, y - w / 2, x2, y + w / 2)


def vwire(layer, x, y1, y2, w):
    rect(layer, x - w / 2, y1, x + w / 2, y2)


def place(cell, x, y, inst, orient=""):
    L.append(f"box {q(x)} {q(y)} {q(x)} {q(y)}")
    L.append(f"getcell {cell} {orient} child 0 0".replace("  ", " "))
    L.append(f"identify {inst}")


def ptap_ring(x0, y0, x1, y1, w=0.44, pitch=0.5):
    """p+ substrate tap ring (psd + licon + li) centred on the rectangle edges."""
    h = w / 2
    for (a0, b0, a1, b1) in ((x0 - h, y0 - h, x1 + h, y0 + h), (x0 - h, y1 - h, x1 + h, y1 + h),
                             (x0 - h, y0 - h, x0 + h, y1 + h), (x1 - h, y0 - h, x1 + h, y1 + h)):
        rect("psd", a0, b0, a1, b1)
    for (a0, b0, a1, b1) in ((x0, y0, x1, y0), (x0, y1, x1, y1), (x0, y0, x0, y1), (x1, y0, x1, y1)):
        rect("li", a0 - 0.085, b0 - 0.085, a1 + 0.085, b1 + 0.085)
        n = int(max(a1 - a0, b1 - b0) / pitch)
        for k in range(1, n):
            cx = a0 + (a1 - a0) * k / n
            cy = b0 + (b1 - b0) * k / n
            sq("psubdiffcont", cx, cy, 0.17)


# ============================================================ tile constants (absolute)
DIE_W, DIE_H = 161.0, 225.76
XC = 73.6     # symmetry axis: midway between uio_out[0] (72.22) and uo_out[7] (74.98), so each half sits under its own 8 pins
STRIPES = {"VGND": [(1.0, 2.6), (158.4, 160.0)], "VDPWR": [(3.4, 5.0), (156.0, 157.6)]}   # edge stripes (decap field)
# inner stripes hug the core; x lies in the gaps of the 2.76 um top-pin lattice so they clear the met4 pin stubs
INNER = {"VGND": [(XC - 28.2, XC - 27.0), (XC + 27.0, XC + 28.2)],
         "VDPWR": [(XC - 30.96, XC - 29.76), (XC + 29.76, XC + 30.96)]}
STRIPE_Y = (5.0, 220.76)
INNER_Y = (186.0, 220.76)     # inner stripes only strap the VCO / flip-flop core (plain metal, not ports)
UA0_X, UA1_X = 152.26, 132.94

# ============================================================ half-cell constants
# local x: distance from the axis (outward), y: absolute
VDP_X = (29.76, 30.96)
VGN_X = (27.0, 28.2)
VDP_C = sum(VDP_X) / 2
VGN_C = sum(VGN_X) / 2
XV, YV = 2.6, 191.88         # YV - 181 is a whole number of decap rows (2.72 um), so the rail grid below lines up
PITCH, NST, XSTAGE0 = 2.4, 7, 5.5   # pitch set by the stage diffusions (2.11 um + 0.29 spacing)
Y_CAP = (-1.545, 1.95)   # load cap: rotated NMOS, W = 1.4 um along x, L = 2.86 um along y
Y_GND = (2.9, 3.38)
Y_VBN = (3.6, 3.9)
Y_N = (4.3, 4.8)
Y_P = (6.1, 7.1)
Y_VBP = (7.5, 7.8)
Y_VDD = (8.1, 8.58)
Y_NW = (5.9, 8.9)
Y_IN = (5.37, 5.54)
Y_RB = 5.07
Y_TAP = 5.985
LS = 1.0
XG0, XG1 = 0.33, 0.33 + LS
XI0 = XG1 + 0.30
XI1 = XI0 + 0.15
XD0, XD1 = XI1 + 0.10, XI1 + 0.27
XDE = XD1 + 0.06
XC1 = 0.33 + 2.0
RING = (XV - 1.6, YV - 4.6, XV + XSTAGE0 + PITCH * (NST - 1) + XDE + 1.4, YV + 9.6)

# flip-flop block: four abutting rows above the VCO, placement and wiring from plan_ff.py
import json as _json
PLAN = _json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ff_plan.json")))
assert abs(PLAN["XV"] - XV) < 1e-9 and abs(PLAN["YV"] - YV) < 1e-9
Y0 = PLAN["Y0"]
TAPW, DFFW, BUFW = 0.46, 8.74, 2.76
SLOTS = [1.38 + 2.76 * j for j in range(8)]          # top pin columns; slot j = uo_out[7-j] (P) / uio_out[j] (N)
TRK = [YV + 10.4 + 0.8 * t for t in range(NST)]      # met3 phase tracks between VCO and flip-flops
CLK_FEED_Y = Y0 + 16.02      # above the Q bus (second-order loop)

# second-order loop (local x outward from the axis, absolute y)
QBUS_Y = [219.4 + 0.6 * j for j in range(NST)]       # met2 Q bus above the flip-flops
SPINE_X = 39.0                                        # met3 clock spine of the second register
XD = [48.6 - 0.85 * r for r in range(NST)]            # met3 descents, Q bus -> row r (staircase)
BLK_X = 49.0                                          # second register rows: tap dfxtp_1 xor2_1 tap
XB = [61.4 + 0.85 * r for r in range(NST)]            # met3 bit descents to the DAC
# xhigh resistors: parallel strips with guard ring (the snake generator fails rpm.1), chained in metal
RD_XC, RD_YC, RD_LS, RD_NX = [15.0 + 6.6 * k for k in range(NST)], 167.8, 30.3, 6    # DAC resistors
RIN_XC, RIN_YC, RIN_LS = 9.5, 154.8, 4.3                                           # input resistor (2 strips)
VG_BUS_Y = 149.8
BIT_Y = [148.8 - 0.6 * r for r in range(NST)]
UA_Y, UA_X, UA_LOW = 144.0, 63.0, 97.8
OTA_X0, OTA_Y0 = 9.0, 130.5
CAP_XC, CAP_YC, CAP_W, CAP_L = (19.2, 47.6), 116.0, 24, 25
VG_X, VG_BR_Y, VG_H_Y = 8.0, 130.2, 130.75
VCTRL_X, VCTRL_Y = 4.0, 136.0
VREF_X, VBN_X, RST_X = 4.9, 5.8, 6.7
PAD_Y, RST_Y = 131.35, 134.47
RES_X0, RES_Y = 23.0, 133.5
BUS_Y = dict(vref=95.0, vbn=95.8, rst=96.6)
RAIL_END, NVDP, NVGN = 72.6, 69.4, 71.8              # half-cell rails reach the N-side edge stripes

# local positions exported to the top level
GATE = (XV + 0.83, YV - 2.535)       # VIN gate via1
VSRC = (XV + 0.145, YV - 3.535)      # vs (M1 source) mcon
VS_ROUTE_Y = VSRC[1]


def lrect(layer, x1, y1, x2, y2):
    rect(layer, XV + x1, YV + y1, XV + x2, YV + y2)


def contact_col(diff, cx0, cx1, y0, y1):
    c = {"ndiff": "ndiffc", "pdiff": "pdiffc", "psd": "psubdiffcont", "nsd": "nsubdiffcont"}[diff]
    lrect(c, cx0, y0, cx1, y1)
    lrect("li", cx0, y0 - 0.08, cx1, y1 + 0.08)


def poly_contact(cx, cy):
    lrect("pc", cx - 0.085, cy - 0.085, cx + 0.085, cy + 0.085)
    lrect("poly", cx - 0.135, cy - 0.165, cx + 0.135, cy + 0.165)
    lrect("li", cx - 0.085, cy - 0.165, cx + 0.085, cy + 0.165)


def lmcon(x, y):
    mcon(XV + x, YV + y)


def draw_vco():
    ring_end = XSTAGE0 + PITCH * NST
    lrect("nwell", -0.4, Y_NW[0], XSTAGE0 + PITCH * (NST - 1) + XDE + 0.4, Y_NW[1])   # 0.4 past the last pdiff
    rect("met1", XV - 0.5, YV + Y_GND[0], VGN_X[1] - 0.3, YV + Y_GND[1])
    rect("met1", XV - 0.5, YV + Y_VDD[0], VDP_X[1] - 0.3, YV + Y_VDD[1])   # rails end on the inner stripes
    lrect("poly", XG0, Y_VBP[0], XSTAGE0 + PITCH * (NST - 1) + XG1, Y_VBP[1])
    lrect("poly", PITCH + XG0, Y_VBN[0], XSTAGE0 + PITCH * (NST - 1) + XG1, Y_VBN[1])

    def ptap(xc):
        lrect("psd", xc - 0.22, 2.95, xc + 0.22, 3.33)
        lrect("psubdiffcont", xc - 0.085, 3.055, xc + 0.085, 3.225)
        lrect("li", xc - 0.085, 2.975, xc + 0.085, 3.305)
        lmcon(xc, 3.14)

    def ntap(xc):
        lrect("nsd", xc - 0.22, 7.98, xc + 0.22, 8.42)
        lrect("nsubdiffcont", xc - 0.085, 8.115, xc + 0.085, 8.285)
        lrect("li", xc - 0.085, 8.035, xc + 0.085, 8.43)
        lmcon(xc, 8.34)

    # column A: M1 (vin -> vbp, source vs) and Mpd (diode vbp)
    a = 0.0
    lrect("ndiff", a, -2.0, a + XG1 + 0.33, 2.0)
    lrect("poly", a + XG0, -2.75, a + XG1, 2.13)
    contact_col("ndiff", a + 0.06, a + 0.23, -1.9, 1.9)
    contact_col("ndiff", a + XG1 + 0.10, a + XG1 + 0.27, -1.9, 1.9)
    poly_contact(a + 0.83, -2.535)
    lmcon(a + 0.83, -2.535)
    lrect("pdiff", a, Y_P[0], a + XG1 + 0.33, Y_P[1])
    lrect("poly", a + XG0, Y_P[0] - 0.13, a + XG1, Y_VBP[1])
    contact_col("pdiff", a + 0.06, a + 0.23, Y_P[0] + 0.06, Y_P[1] - 0.06)
    contact_col("pdiff", a + XG1 + 0.10, a + XG1 + 0.27, Y_P[0] + 0.06, Y_P[1] - 0.06)
    lrect("li", a + 0.06, Y_P[0], a + 0.23, Y_VDD[1] - 0.1)
    lmcon(a + 0.145, 8.34)
    lrect("li", a + XG1 + 0.10, -1.98, a + XG1 + 0.27, 7.82)
    lrect("pc", a + XG1 + 0.10, 7.565, a + XG1 + 0.27, 7.735)
    lrect("li", a + 0.06, -3.62, a + 0.23, -1.9)
    lmcon(a + 0.145, -3.535)
    ptap(a + 0.7)
    ntap(a + 0.7)

    # column B: Mp2 (vbp -> vbn) and Mnd (diode vbn)
    b = PITCH
    lrect("pdiff", b, Y_P[0], b + XG1 + 0.33, Y_P[1])
    lrect("poly", b + XG0, Y_P[0] - 0.13, b + XG1, Y_VBP[1])
    contact_col("pdiff", b + 0.06, b + 0.23, Y_P[0] + 0.06, Y_P[1] - 0.06)
    contact_col("pdiff", b + XG1 + 0.10, b + XG1 + 0.27, Y_P[0] + 0.06, Y_P[1] - 0.06)
    lrect("li", b + 0.06, Y_P[0], b + 0.23, Y_VDD[1] - 0.1)
    lmcon(b + 0.145, 8.34)
    lrect("ndiff", b, Y_N[0], b + XG1 + 0.33, Y_N[1])
    lrect("poly", b + XG0, Y_VBN[0], b + XG1, Y_N[1] + 0.13)
    contact_col("ndiff", b + 0.06, b + 0.23, Y_N[0] + 0.06, Y_N[1] - 0.06)
    contact_col("ndiff", b + XG1 + 0.10, b + XG1 + 0.27, Y_N[0] + 0.06, Y_N[1] - 0.06)
    lrect("li", b + 0.06, Y_GND[0] + 0.1, b + 0.23, Y_N[1])
    lmcon(b + 0.145, 3.14)
    lrect("li", b + XG1 + 0.10, 3.585, b + XG1 + 0.27, Y_P[1] - 0.02)
    lrect("pc", b + XG1 + 0.10, 3.665, b + XG1 + 0.27, 3.835)
    ptap(b + 0.7)
    ntap(b + 0.7)

    # ring stages
    for i in range(NST):
        s = XSTAGE0 + PITCH * i
        lrect("ndiff", s, Y_N[0], s + XDE, Y_N[1])
        lrect("poly", s + XG0, Y_VBN[0], s + XG1, Y_N[1] + 0.13)
        contact_col("ndiff", s + 0.06, s + 0.23, Y_N[0] + 0.06, Y_N[1] - 0.06)
        contact_col("ndiff", s + XD0, s + XD1, Y_N[0] + 0.06, Y_N[1] - 0.06)
        lrect("pdiff", s, Y_P[0], s + XDE, Y_P[1])
        lrect("poly", s + XG0, Y_P[0] - 0.13, s + XG1, Y_VBP[1])
        contact_col("pdiff", s + 0.06, s + 0.23, Y_P[0] + 0.06, Y_P[1] - 0.06)
        contact_col("pdiff", s + XD0, s + XD1, Y_P[0] + 0.06, Y_P[1] - 0.06)
        lrect("poly", s + XI0, Y_N[0] - 0.13, s + XI1, Y_P[1] + 0.13)
        lrect("poly", s + XI0 - 0.32, 5.29, s + XI1, 5.62)
        lrect("pc", s + XI0 - 0.27, Y_IN[0], s + XI0 - 0.10, Y_IN[1])
        lrect("li", s + XI0 - 0.27, 5.29, s + XI0 - 0.10, 5.62)
        x_prev_out = s - PITCH + XD0 if i > 0 else s - 0.6
        lrect("li", x_prev_out, Y_IN[0], s + XI0 - 0.10, Y_IN[1])
        # load cap, rotated: diffusion x 0.40..1.80, gate band across it (L along y), source/drain
        # contact rows at the bottom and top, both tied to the stage's VGND source column
        lrect("ndiff", s + 0.40, Y_CAP[0], s + 1.80, Y_CAP[1])
        lrect("poly", s + 0.27, -1.26, s + 1.93, 1.60)
        lrect("poly", s + 1.875, 1.0, s + 2.13, 2.50)          # tab up to the output contact
        lrect("poly", s + 1.80, 2.12, s + 2.13, 2.50)
        lrect("ndiffc", s + 0.46, -1.485, s + 1.74, -1.315)
        lrect("ndiffc", s + 0.46, 1.70, s + 1.74, 1.87)
        lrect("li", s + 0.06, -1.565, s + 1.74, -1.235)
        lrect("li", s + 0.06, 1.62, s + 1.74, 1.95)
        lrect("pc", s + XD0, 2.25, s + XD1, 2.42)
        lrect("li", s + 0.06, -1.565, s + 0.23, Y_N[1] - 0.02)
        lmcon(s + 0.145, 3.14)
        lrect("li", s + 0.06, Y_P[0], s + 0.23, Y_VDD[1] - 0.1)
        lmcon(s + 0.145, 8.34)
        lrect("li", s + XD0, 2.17, s + XD1, Y_P[1] - 0.02)
        xo = s + (XD0 + XD1) / 2
        lmcon(xo, Y_TAP)
        via1(XV + xo, YV + Y_TAP)
        ptap(s + 1.15)
        ntap(s + 1.15)

    s6 = XSTAGE0 + PITCH * (NST - 1)
    xo6 = s6 + (XD0 + XD1) / 2
    lmcon(xo6, Y_RB)
    x_in0 = XSTAGE0 - 0.515
    lmcon(x_in0, (Y_IN[0] + Y_IN[1]) / 2)
    lrect("met1", x_in0 - 0.145, Y_RB - 0.145, xo6 + 0.145, Y_RB + 0.145)
    lrect("met1", x_in0 - 0.145, Y_RB - 0.145, x_in0 + 0.145, (Y_IN[0] + Y_IN[1]) / 2 + 0.145)

    # guard ring, tied to the VGND rail where the rail crosses its outer side
    ptap_ring(*RING)
    mcon(RING[2], YV + sum(Y_GND) / 2)


def phase_x(i):
    return XV + XSTAGE0 + PITCH * i + (XD0 + XD1) / 2


def pin_pad(x, y, h=0.5):
    sq("mcon", x, y, 0.17)
    rect("met1", x - 0.16, y - h / 2, x + 0.16, y + h / 2)
    sq("via1", x, y, 0.26)
    rect("met2", x - 0.16, y - 0.19, x + 0.16, y + 0.19)


def build_half():
    """cell vco_adc_half: VCO + guard ring, four flip-flop rows, phase tracks, clock spine, outputs to pins."""
    L.append("drc off")
    L.append("snap internal")
    L.append("addpath $::env(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/mag")
    L.append(f"load {HALF}")
    L.append("box 0um 0um 1um 1um")
    draw_vco()
    slot, phase = PLAN["slot"], PLAN["phase"]
    trk = {int(k): v for k, v in PLAN["trk"].items()}
    cells, ends, dff_next = [], [], 0
    for r in range(4):
        yb = Y0 + 2.72 * r
        flip = r % 2 == 1
        yplace, orient = (yb + 2.72, "v") if flip else (yb, "")
        fy = (lambda y, yb=yb: yb + 2.72 - y) if flip else (lambda y, yb=yb: yb + y)
        if r == PLAN["short_row"]:
            members = ["buf", "6"] if PLAN["buf_first"] else ["6", "buf"]
        else:
            members = [str(dff_next), str(dff_next + 1)]
            dff_next += 2
        x = 0.46 * PLAN["ks"][r]
        for m in members:
            place("sky130_fd_sc_hd__tapvpwrvgnd_1", x, yplace, f"tap{r}_{m}", orient)
            x += TAPW
            if m == "buf":
                place("sky130_fd_sc_hd__buf_4", x, yplace, "mon", orient)
                cells.append(dict(n=m, D=(x + 0.28, fy(1.195)), Dh=0.36, Q=(x + 1.94, fy(2.15)), C=None, row=r))
                x += BUFW
            else:
                place("sky130_fd_sc_hd__dfxtp_4", x, yplace, f"dff{m}", orient)
                cells.append(dict(n=m, D=(x + 1.58, fy(1.36)), Dh=0.5, Q=(x + (7.155, 8.005)[PLAN["qcol"][int(m)]], fy(2.15)),
                                  C=(x + 0.265, fy(1.3)), row=r))
                x += DFFW
        place("sky130_fd_sc_hd__tapvpwrvgnd_1", x, yplace, f"tap{r}_e", orient)
        ends.append(x + TAPW)
    # row rails out to the inner stripes: VGND at k = 0, 2, 4, VDPWR at k = 1, 3
    for k in range(5):
        y = Y0 + 2.72 * k
        xa = min(ends[j] for j in (k - 1, k) if 0 <= j < 4) - 0.2
        rect("met1", xa, y - 0.24, RAIL_END, y + 0.24)
        if k % 2 == 0:
            stack(VGN_C, y, 1, 4); stack(NVGN, y, 1, 4)
        else:
            stack(VDP_C, y, 1, 4); stack(NVDP, y, 1, 4)
    # VCO rails -> inner stripes
    stack(VDP_C, YV + sum(Y_VDD) / 2, 1, 4)
    stack(VGN_C, YV + sum(Y_GND) / 2, 1, 4)
    # phase tracks: VCO tap -> met2 riser -> met3 track -> met2 risers -> D pins
    for i in range(NST):
        xt, ty = phase_x(i), TRK[trk[i]]
        vwire("met2", xt, YV + Y_TAP, ty, 0.3)
        via2(xt, ty)
        xs = [xt]
        for c in cells:
            if phase[c["n"]] == i:
                xd, yd = c["D"]
                pin_pad(xd, yd, h=c["Dh"])
                vwire("met2", xd, ty, yd, 0.3)
                via2(xd, ty)
                xs.append(xd)
        hwire("met3", min(xs) - 0.25, max(xs) + 0.25, ty, 0.5)
    # outputs: Q pad -> via2 -> short met3 jog -> via3 under its own pin -> met4 to the pin
    for c in cells:
        xq, yq = c["Q"]
        pin_pad(xq, yq, h=0.36)
        via2(xq, yq)
        xs = SLOTS[slot[c["n"]]]
        hwire("met3", min(xq, xs) - 0.26, max(xq, xs) + 0.26, yq, 0.52)   # as tall as the via pads: no notches
        via3(xs, yq)
        met4_stub(xs, yq)
    # clock: per-row met3 track to a met2 spine on the axis
    ycs = []
    for r in range(4):
        cs = [c["C"] for c in cells if c["row"] == r and c["C"]]
        for xc, yc in cs:
            pin_pad(xc, yc, h=0.36)
            via2(xc, yc)
        yc = cs[0][1]
        ycs.append(yc)
        hwire("met3", -0.25, max(x for x, _ in cs) + 0.25, yc, 0.5)
        via2(0.0, yc)
    vwire("met2", 0.0, min(ycs), CLK_FEED_Y, 0.3)
    so_half(cells)
    L.append("select top cell")
    L.append("writeall force")
    L.append("quit -noprompt")
    return cells


def gencell(name, kind, params, xc, yc, top):
    """PDK generator cell placed with its bounding-box centre at (xc, yc)."""
    L.append(f"box {q(xc)} {q(yc)} {q(xc)} {q(yc)}")
    L.append(f"magic::gencell sky130::{kind} {name} {params}")
    L.append(f"load {top}")
    L.append(f"select cell {name}")
    L.append("set b [box values]")
    L.append(f"set nx [expr {{round({xc}*200 - ([lindex $b 2]-[lindex $b 0])/2.0)}}]")
    L.append(f"set ny [expr {{round({yc}*200 - ([lindex $b 3]-[lindex $b 1])/2.0)}}]")
    L.append("move to ${nx}i ${ny}i")
    L.append("select clear")


RES = "sky130_fd_pr__res_xhigh_po_" + "0p35"


def res_pads(xc, yc, ls, nx):
    """terminal pad centres (left, right) and bottom pad y range of a chained-strip resistor."""
    dx = 0.415 * (nx - 1)
    return (xc - dx, xc + dx), (yc - (ls / 2 + 2.05), yc - (ls / 2 - 0.055))


def chain_res(name, xc, yc, ls, nx, top):
    """xhigh resistor of nx parallel strips (guard ring) joined in series by met1 jumpers
    (top: strips 0-1, 2-3 ...; bottom: 1-2, 3-4 ...); both terminals end up at the bottom."""
    gencell(name, RES, f"w 0.35 l {ls} nx {nx} snake 0 guard 1", xc, yc, top)
    xs = [xc - 0.415 * (nx - 1) + 0.83 * i for i in range(nx)]
    for i in range(nx - 1):
        y = yc + ls / 2 + 1.0 if i % 2 == 0 else yc - ls / 2 - 1.0
        rect("met1", xs[i] - 0.125, y - 0.15, xs[i + 1] + 0.125, y + 0.15)
    return res_pads(xc, yc, ls, nx)


def so_half(cells):
    """Second-order loop of one half: second register + XOR (pocket), resistor DAC, input
    resistor, 5T OTA integrator with MIM capacitors and reset switch, vctrl to the VCO gate."""
    import devlib as D
    D.init(rect, sq)
    phase, slot = PLAN["phase"], PLAN["slot"]
    n_of = {phase[c["n"]]: c["n"] for c in cells if c["n"] != "buf"}   # phase -> DFF1 cell
    # ---- rails of the second-register rows (k = -3 .. -1 are new; k >= 0 extended above)
    for k in (-3, -2, -1):
        y = Y0 + 2.72 * k
        rect("met1", 32.0, y - 0.24, RAIL_END, y + 0.24)
        stack(NVGN if k % 2 == 0 else NVDP, y, 1, 4)
    # ---- clock: feed extension + spine
    hwire("met3", -0.25, SPINE_X + 0.25, CLK_FEED_Y, 0.3)
    ylow = []
    for r in range(NST):
        k = 3 - r
        yb = Y0 + 2.72 * k
        flip = k % 2 == 1
        yplace, orient = (yb + 2.72, "v") if flip else (yb, "")
        fy = (lambda y, yb=yb: yb + 2.72 - y) if flip else (lambda y, yb=yb: yb + y)
        x = BLK_X
        place("sky130_fd_sc_hd__tapvpwrvgnd_1", x, yplace, f"tq{r}a", orient); x += TAPW
        dffx = x
        place("sky130_fd_sc_hd__dfxtp_1", x, yplace, f"dq{r}", orient); x += 7.36
        xorx = x
        place("sky130_fd_sc_hd__xor2_1", x, yplace, f"xq{r}", orient); x += 3.22
        place("sky130_fd_sc_hd__tapvpwrvgnd_1", x, yplace, f"tq{r}b", orient)
        # pins
        pd, pc, pa, px = (dffx + 1.51, fy(0.9)), (dffx + 0.265, fy(1.1)), (xorx + 1.115, fy(1.175)), (xorx + 2.975, fy(2.0))
        pin_pad(*pd, h=0.32); pin_pad(*pc, h=0.32); pin_pad(*pa, h=0.36); pin_pad(*px, h=0.5)
        # Q (second register) -> xor B, met1 jumper
        qx, qy, bx, by = dffx + 7.19, fy(1.155), xorx + 0.5475, fy(1.22)
        sq("mcon", qx, qy, 0.17); sq("mcon", bx, by, 0.17)
        rect("met1", qx - 0.145, min(qy, by) - 0.145, bx + 0.145, max(qy, by) + 0.145)
        # clock
        via2(SPINE_X, pc[1])
        hwire("met2", SPINE_X, pc[0], pc[1], 0.3)
        ylow.append(pc[1])
        # Q bus line r (Q of the DFF1 cell sampling phase r) -> descent -> D and A
        n = n_of[r]
        xs, yq = SLOTS[slot[n]], QBUS_Y[r]
        via3(xs, yq); via2(xs, yq)
        hwire("met2", xs, XD[r], yq, 0.3)
        via2(XD[r], yq)
        vwire("met3", XD[r], pd[1] - 0.15, yq, 0.3)
        via2(*pd); via2(*pa)
        hwire("met3", XD[r] - 0.15, pa[0] + 0.25, pd[1], 0.3)
        # bit r: xor X -> met2 jog -> met3 descent -> DAC element r
        hwire("met2", px[0], XB[r], px[1], 0.3)
        via2(XB[r], px[1])
        vwire("met3", XB[r], BIT_Y[r], px[1], 0.3)
    vwire("met3", SPINE_X, min(ylow), CLK_FEED_Y, 0.3)
    # ---- DAC resistors, terminals at the bottom: left = bit, right = vg
    for k in range(NST):
        (xl, xr), (py0, py1) = chain_res(f"RD{k}", RD_XC[k], RD_YC, RD_LS, RD_NX, HALF)
        vwire("met1", xr, VG_BUS_Y, py0 + 0.15, 0.25); via1(xr, VG_BUS_Y)
        vwire("met1", xl, BIT_Y[k], py0 + 0.15, 0.25); via1(xl, BIT_Y[k])
        via2(XB[k], BIT_Y[k])
        hwire("met2", xl, XB[k], BIT_Y[k], 0.3)
    # ---- input resistor: left = ua, right = vg
    (xl, xr), (py0, py1) = chain_res("RIN", RIN_XC, RIN_YC, RIN_LS, 2, HALF)
    vwire("met1", xr, VG_BUS_Y, py0 + 0.15, 0.25); via1(xr, VG_BUS_Y)
    vwire("met1", xl, UA_Y, py0 + 0.15, 0.25); via1(xl, UA_Y); via2(xl, UA_Y)
    hwire("met3", xl, UA_X, UA_Y, 0.4)
    via3(UA_X, UA_Y)
    vwire("met4", UA_X, UA_LOW, UA_Y + 0.26, 0.6)
    hwire("met2", VG_X - 0.15, res_pads(RD_XC[-1], RD_YC, RD_LS, RD_NX)[0][1] + 0.19, VG_BUS_Y, 0.3)
    # ---- OTA
    o = D.ota(OTA_X0, OTA_Y0)
    # rails to the N-side edge stripes
    hwire("met1", o["x1"] - 0.3, RAIL_END, o["gnd_y"], 0.32); stack(NVGN, o["gnd_y"], 1, 4)
    hwire("met1", o["x1"] - 0.3, RAIL_END, o["vdd_y"], 0.32); stack(NVDP, o["vdd_y"], 1, 4)
    # vg: bus -> vertical -> OTA inn, reset drain, capacitor top plates
    vwire("met2", VG_X, VG_BR_Y, VG_BUS_Y, 0.3)
    xin, yin = o["inn"]
    hwire("met2", VG_X - 0.15, RES_X0 + 0.665 + 0.15, VG_H_Y, 0.3)
    vwire("met2", xin, VG_H_Y, yin, 0.3); via1(xin, yin)
    hwire("met2", VG_X - 0.15, CAP_XC[1] - 5.1, VG_BR_Y, 0.3)
    for x in (CAP_XC[0] - 7.2, CAP_XC[1] - 5.1):          # top plates: met4 tabs from via stacks
        via2(x, VG_BR_Y); via3(x, VG_BR_Y)
        rect("met4", x - 1.0, CAP_YC + CAP_L / 2 - 0.5, x + 1.0, VG_BR_Y + 0.26)
    # vctrl: OTA out -> left riser to the VCO gate, down to the capacitor bottom plates
    xo, _ = o["out"]
    via2(xo, VCTRL_Y)
    hwire("met3", VCTRL_X - 0.15, xo, VCTRL_Y, 0.3)
    y_bp = RES_Y - 0.5                 # vctrl met3 track to both bottom-plate terminal strips
    for xc in CAP_XC:
        xsrp = xc + CAP_W / 2 + 0.82
        rect("met4", xsrp - 0.24, CAP_YC, xsrp + 0.24, y_bp + 0.26)
        via3(xsrp, y_bp)
    hwire("met3", xo - 0.15, CAP_XC[1] + CAP_W / 2 + 0.82, y_bp, 0.3)
    vwire("met3", xo, y_bp, VCTRL_Y, 0.3)
    vwire("met3", VCTRL_X, VCTRL_Y - 0.15, GATE[1] + 0.15, 0.3)
    rect("met3", GATE[0] - 0.25, GATE[1] - 0.25, VCTRL_X + 0.15, GATE[1] + 0.25)   # solid junction, no notches
    via1(*GATE); via2(*GATE)
    # MIM capacitors (top = vg, bottom = vctrl) and the bottom-plate bridge
    for i, xc in enumerate(CAP_XC):
        gencell(f"CM{i}", "sky130_fd_pr__cap_mim_m3_1", f"w {CAP_W} l {CAP_L}", xc, CAP_YC, HALF)
    # vref / vbn: risers from the shared bias buses to the OTA gate pads
    vwire("met2", VREF_X, BUS_Y["vref"], PAD_Y, 0.3); via2(VREF_X, PAD_Y); via3(VREF_X, PAD_Y)
    xp_, yp_ = o["inp"]
    hwire("met4", VREF_X, xp_, PAD_Y, 0.3); via3(xp_, yp_); via2(xp_, yp_); via1(xp_, yp_)
    vwire("met2", VBN_X, BUS_Y["vbn"], PAD_Y, 0.3); via2(VBN_X, PAD_Y)
    xb_, yb_ = o["vbn"]
    hwire("met3", VBN_X, xb_, PAD_Y, 0.3); via2(xb_, yb_); via1(xb_, yb_)
    # reset switch: drain vg, source vctrl, gate rst
    m = D.fet("n", RES_X0, RES_Y, 0.42, 0.15, 1, gate="top")
    xs_, xd_ = m["cols"][0][0], m["cols"][1][0]
    vwire("met1", xd_, VG_H_Y + 1.25, RES_Y + 0.1, 0.29); via1(xd_, VG_H_Y + 1.25)
    vwire("met2", xd_, VG_H_Y, VG_H_Y + 1.25, 0.3)
    vwire("met1", xs_, RES_Y - 0.5, RES_Y + 0.1, 0.29); via1(xs_, RES_Y - 0.5); via2(xs_, RES_Y - 0.5)
    gx, gy = m["g"]
    vwire("met2", RST_X, BUS_Y["rst"], RST_Y, 0.3); via2(RST_X, RST_Y); via3(RST_X, RST_Y)
    hwire("met4", RST_X, gx, RST_Y, 0.3)
    via1(gx, gy); via2(gx, gy); via3(gx, gy)


# ============================================================ top level
RX, RY = XC, YV - 23.5           # resistor array centre
R_STRIP = [-2.075, -1.245, -0.415, 0.415, 1.245, 2.075]   # D N1 P1 P2 N2 D
R_TOP, R_BOT = 16.0, -16.0   # contact pad centres (pads +/-1.05 tall)
R_RING_X, R_RING_Y = 2.815, 17.645
Y_SH_T, Y_INP, Y_INN, Y_SH_B = YV - 7.4, YV - 8.2, YV - 9.0, YV - 9.8
DEC_Y0, DEC_ROWS = 6.0, 31
BIAS_ROW = DEC_ROWS - 1         # top decap row: holds the reset inverter; the bias block sits on its VDPWR rail
N_RAILS = DEC_ROWS + 1          # row rails are drawn even in the no-decap copy (they power the bias block)
if os.environ.get("NODECAP"):   # post-layout simulation copy: decaps only load the ideal supply
    DEC_ROWS = 0
DEC_X0, DEC_X1 = 5.6, 155.4
# the top decap row leaves a gap (on the 0.46 site grid) for the reset inverter of the bias block
INV_GAP = (79.66, 82.42)


def pin_x(name):
    tbl = {f"uo_out[{i}]": 94.3 - 2.76 * i for i in range(8)}
    tbl.update({f"uio_out[{i}]": 72.22 - 2.76 * i for i in range(8)})
    tbl.update({f"uio_oe[{i}]": 50.14 - 2.76 * i for i in range(8)})
    tbl["clk"] = 143.98
    return tbl[name]


def P(xl):
    return XC + xl


def N(xl):
    return XC - xl


def met4_stub(xp, y):
    vwire("met4", xp, 222.0, DIE_H, 0.3)
    vwire("met4", xp, y - 0.23, 222.2, 0.6)


def so_top():
    """Shared parts of the second-order loop: bias block on the axis (Vref divider + MOS
    decoupling, tail-current reference, reset inverter), buses, analog inputs, rst_n,
    P-side rail extensions."""
    import devlib as D
    D.init(rect, sq)
    gy, py = DEC_Y0 + 2.72 * BIAS_ROW, DEC_Y0 + 2.72 * (BIAS_ROW + 1)   # VGND / VDPWR rails under the bias block
    yb = py + 0.74                    # bottom of the bias devices (clear of the row nwell)
    X = lambda lx: XC + lx

    def to_gnd(x, y):                 # met2 jumper from a device column down onto the VGND rail
        via1(x, y); vwire("met2", x, gy, y, 0.3); via1(x, gy)

    # one compact row on the top decap rail, left to right: Rb | Mb | Mc | Rt | Rbt
    # MOS decoupling cap on Vref (gate, 2 x W5/L10) with grounded source/drain
    mc = D.fet("n", X(-10.5), yb, 5.0, 10.0, 2, gate="top")
    for x, _ in mc["cols"]:
        to_gnd(x, yb + 0.2)
    via1(*mc["g"]); vwire("met2", mc["g"][0], mc["g"][1], BUS_Y["vref"], 0.3); via2(mc["g"][0], BUS_Y["vref"])
    tp = D.tap("p", X(-10.2), mc["g"][1] + 0.85, X(10.2), mc["g"][1] + 1.29)   # substrate tap above the MOS cap
    to_gnd(X(-9.6), tp)
    # tail reference: Rb (VDPWR -> vbn) into diode Mb
    mb = D.fet("n", X(-17.2), yb + 1.7, 2.0, 2.0, 2)
    xd = mb["cols"][1][0]
    rect("met1", xd - 0.145, mb["g"][1], xd + 0.145, mb["y0"] + 0.1)
    for x, k in mb["cols"]:
        if k == "S":
            to_gnd(x, mb["y0"] + 0.2)
    via1(xd, mb["y0"] + 1.8); vwire("met2", xd, mb["y0"] + 1.8, BUS_Y["vbn"], 0.3); via2(xd, BUS_Y["vbn"])
    tap_y = D.tap("p", mb["x0"], mb["y1"] + 0.6, mb["x1"], mb["y1"] + 1.04)   # substrate tap next to Mb
    to_gnd(mb["x0"] + 0.4, tap_y)
    lb = 3.25                          # Rb = 4 x 3.25 um (about 74 kOhm): about 15 uA tail per OTA
    (xl, xr), (p0, _) = chain_res("RB", X(-21.8), py + 2.0 + lb / 2 + 2.645, lb, 4, TOP)
    xrb = xr
    vwire("met1", xl, py, p0 + 0.15, 0.25)
    via1(xr, p0 + 1.0); vwire("met2", xr, p0 + 1.0, BUS_Y["vbn"], 0.3); via2(xr, BUS_Y["vbn"])
    # Vref divider: Rt (VDPWR -> vref), Rbt (vref -> VGND)
    lt = 4.375
    yt_c = py + 2.0 + lt / 2 + 2.645
    (tl, tr), (p0, _) = chain_res("RT", X(15.5), yt_c, lt, 8, TOP)
    (bl, br), _ = chain_res("RBT", X(24.0), yt_c, lt, 8, TOP)
    vwire("met1", tl, py, p0 + 0.15, 0.25)
    yv = p0 + 0.8
    via1(tr, yv); via1(bl, yv); hwire("met2", tr, bl, yv, 0.3)
    vwire("met2", tr, yv, BUS_Y["vref"], 0.3); via2(tr, BUS_Y["vref"])
    to_gnd(br, p0 + 0.3)
    # reset inverter in the gap of the top decap row
    place("sky130_fd_sc_hd__tapvpwrvgnd_1", INV_GAP[0], gy, "itap0")
    place("sky130_fd_sc_hd__inv_1", INV_GAP[0] + 0.46, gy, "irst")
    place("sky130_fd_sc_hd__tapvpwrvgnd_1", INV_GAP[0] + 1.84, gy, "itap1")
    place("sky130_fd_sc_hd__fill_1", INV_GAP[0] + 2.3, gy, "ifill")
    xa, ya = INV_GAP[0] + 0.46 + 0.485, gy + 1.195
    xy, yy = INV_GAP[0] + 0.46 + 0.885, gy + 1.9
    pin_pad(xa, ya, h=0.36); via2(xa, ya); via3(xa, ya)
    xyr = X(8.2)                     # rst riser clear of the P half's rst via at X(RST_X)
    pin_pad(xy, yy, h=0.36); hwire("met2", xy - 0.15, xyr + 0.15, yy, 0.3)
    vwire("met2", xyr, yy, BUS_Y["rst"], 0.3); via2(xyr, BUS_Y["rst"])
    # rst_n: pin -> met4 down -> met3 west -> met4 down to the inverter input
    xr_pin, y_rn = 141.22, 100.0
    met4_stub(xr_pin, y_rn); via3(xr_pin, y_rn)
    hwire("met3", xa, xr_pin, y_rn, 0.3)
    via3(xa, y_rn); vwire("met4", xa, ya, y_rn, 0.3)
    # buses (met3) feeding both halves' risers at +-VREF_X / VBN_X / RST_X
    hwire("met3", X(-VREF_X), tr, BUS_Y["vref"], 0.3)
    hwire("met3", xrb, X(VBN_X), BUS_Y["vbn"], 0.3)
    hwire("met3", X(-RST_X), xyr, BUS_Y["rst"], 0.3)
    for f in (P, N):
        via2(f(VREF_X), BUS_Y["vref"]); via2(f(VBN_X), BUS_Y["vbn"]); via2(f(RST_X), BUS_Y["rst"])
    # analog inputs: ua[0] -> P riser, ua[1] -> N riser (met4 up, met3 across)
    for xu, xt, y in ((UA0_X, P(UA_X), 98.0), (UA1_X, N(UA_X), 98.8)):
        vwire("met4", xu, 0.0, y + 0.26, 0.9)
        via3(xu, y); via3(xt, y)
        hwire("met3", min(xu, xt), max(xu, xt), y, 0.4)
    # P side: half-cell rails continue to the P edge stripes
    ys = [Y0 + 2.72 * k for k in range(-3, 5)] + [OTA_Y0 + 0.22, OTA_Y0 + 6.4]
    for y in ys:
        k = round((y - Y0) / 2.72) if y > 190 else None
        gnd = (k % 2 == 0) if k is not None else abs(y - (OTA_Y0 + 0.22)) < 0.01
        w = 0.48 if k is not None else 0.32
        hwire("met1", P(RAIL_END) - 0.3, 159.8 if gnd else 157.4, y, w)
        stack(159.2 if gnd else 156.8, y, 1, 4)


def build_top(template, cells, verilog):
    L.append("drc off")
    L.append("snap internal")
    L.append("addpath $::env(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/mag")
    L.append(f"def read {template}")
    L.append(f"cellname rename tt_um_template {TOP}")
    L.append(f"load {TOP}")
    place(HALF, XC, 0.0, "halfP")
    place(HALF, XC, 0.0, "halfN", "h")

    # ---- clock: pin -> met4 -> met3 feed -> the shared spine on the axis
    xk = pin_x("clk")
    via3(xk, CLK_FEED_Y)
    met4_stub(xk, CLK_FEED_Y)
    hwire("met3", XC - 0.25, xk + 0.26, CLK_FEED_Y, 0.3)
    via2(XC, CLK_FEED_Y)

    # ---- uio_oe tied high: each pin stub drops onto the VDPWR row rail at Y0 + 3 rows
    y_tie = Y0 + 2.72 * 3
    for xp in [pin_x(f"uio_oe[{i}]") for i in range(8)]:
        met4_stub(xp, y_tie)
        stack(xp, y_tie, 1, 4)

    # ---- resistor array on the centre line
    L.append(f"box {q(RX)} {q(RY)} {q(RX)} {q(RY)}")
    L.append("magic::gencell sky130::sky130_fd_pr__res_xhigh_po_0p35 RARR "
             "w 0.35 l 30 nx 6 snake 0 guard 1")
    L.append(f"load {TOP}")
    L.append("select cell RARR")
    L.append("set b [box values]")
    L.append(f"set nx [expr {{round({RX}*200 - ([lindex $b 2]-[lindex $b 0])/2.0)}}]")
    L.append(f"set ny [expr {{round({RY}*200 - ([lindex $b 3]-[lindex $b 1])/2.0)}}]")
    L.append("move to ${nx}i ${ny}i")
    L.append("select cell RARR")
    L.append('puts "RBOX [box values]"')
    L.append("select clear")
    xs = [RX + v for v in R_STRIP]
    yt, yb = RY + R_TOP, RY + R_BOT
    ring_t, ring_b = RY + R_RING_Y, RY - R_RING_Y

    def to_ring(x, yfrom, yring):
        vwire("met1", x, min(yfrom, yring), max(yfrom, yring), 0.25)
        sq("mcon", x, yring, 0.17)
        rect("met1", x - 0.125, yring - 0.205, x + 0.125, yring + 0.205)

    # dummies: both ends to the ring (VGND)
    for x in (xs[0], xs[5]):
        to_ring(x, yt, ring_t)
        to_ring(x, yb, ring_b)
    # P: vsP -> top of P2, P2 bottom - P1 bottom, P1 top -> VGND
    hwire("met1", xs[2] - 0.125, xs[3] + 0.125, yb, 0.3)
    to_ring(xs[2], yt, ring_t)
    # N: vsN -> top of N1, N1 bottom - N2 bottom (met2 bridge), N2 top -> VGND
    via1(xs[1], yb - 0.6)
    via1(xs[4], yb - 0.6)
    hwire("met2", xs[1], xs[4], yb - 0.6, 0.3)
    to_ring(xs[4], yt, ring_t)
    # vs routes (met1) from each half's M1 source down to its resistor
    for f, xr in ((P, xs[3]), (N, xs[1])):
        xsrc = f(VSRC[0])
        hwire("met1", min(xsrc, xr) - 0.15, max(xsrc, xr) + 0.15, VS_ROUTE_Y, 0.3)
        vwire("met1", xr, yt, VS_ROUTE_Y + 0.15, 0.3)
    # resistor-array ring (resistor ground ends) -> VCO guard rings (VGND), li straps
    for f in (P, N):
        rect("li", f(2.0) - 0.085, RY + R_RING_Y, f(2.0) + 0.085, RING[1] + 0.1)

    so_top()

    # ---- decap rows (split around the resistor column where they overlap it)
    decaps = []

    def fill_segment(r, xa, xb, yp, orient):
        x = xa
        place("sky130_fd_sc_hd__tapvpwrvgnd_1", x, yp, f"dtap{r}_{xa:.0f}", orient)
        x += TAPW
        n_since_tap, c = 0, 0
        while x + 5.52 + TAPW <= xb + 1e-6:
            if n_since_tap == 2:            # taps every 11 um (latch-up rules LU.2/LU.3)
                place("sky130_fd_sc_hd__tapvpwrvgnd_1", x, yp, f"dtap{r}_{xa:.0f}_{c}", orient)
                x += TAPW
                n_since_tap = 0
                continue
            name = f"dcap{r}_{xa:.0f}_{c}"
            place("sky130_fd_sc_hd__decap_12", x, yp, name, orient)
            decaps.append(name)
            x += 5.52
            c += 1
            n_since_tap += 1
        for cell, w in (("fill_8", 3.68), ("fill_4", 1.84), ("fill_2", 0.92), ("fill_1", 0.46)):
            while x + w + TAPW <= xb + 1e-6:
                place(f"sky130_fd_sc_hd__{cell}", x, yp, f"dfill{r}_{xa:.0f}_{c}", orient)
                x += w
                c += 1
        place("sky130_fd_sc_hd__tapvpwrvgnd_1", x, yp, f"dtap{r}_{xa:.0f}_e", orient)

    def segs(r):
        if r < 0 or r >= DEC_ROWS:
            return []
        if r == BIAS_ROW:
            return [(DEC_X0, INV_GAP[0]), (INV_GAP[1], DEC_X1)]
        return [(DEC_X0, DEC_X1)]

    for r in range(DEC_ROWS):
        y0 = DEC_Y0 + 2.72 * r
        flip = r % 2 == 1
        yp = y0 + 2.72 if flip else y0
        orient = "v" if flip else ""
        for xa, xb in segs(r):
            fill_segment(r, xa, xb, yp, orient)
    for k in range(N_RAILS):
        y = DEC_Y0 + 2.72 * k
        net = "VGND" if k % 2 == 0 else "VDPWR"
        lo, hi = (1.2, 159.8) if net == "VGND" else (3.6, 157.4)
        hwire("met1", lo, hi, y, 0.48)                 # rails run through (also under the inverter gap)
        for s_ in STRIPES[net]:
            stack(sum(s_) / 2, y, 1, 4)

    # ---- power stripes
    for name in INNER:
        for (x0, x1) in INNER[name]:
            rect("met4", x0, INNER_Y[0], x1, INNER_Y[1])
    for name in STRIPES:
        for (x0, x1) in STRIPES[name]:
            L.append(f"box {q(x0)} {q(STRIPE_Y[0])} {q(x1)} {q(STRIPE_Y[1])}")
            L.append("paint met4")
            L.append(f"label {name} FreeSans 0.25u -met4")
            L.append("port make")
            L.append(f"port use {'ground' if name == 'VGND' else 'power'}")
            L.append("port class bidirectional")
            L.append("port connections n s e w")
    L.append("select top cell")
    L.append("writeall force")

    # ---- LVS reference
    with open(verilog, "w") as fv:
        sc = "sky130_fd_sc_hd__"
        pw = ".VGND(VGND), .VNB(VGND), .VPB(VDPWR), .VPWR(VDPWR)"
        fv.write("// LVS reference for tt_um_arcadia1_vco_adc v2 (generated by layout/gen_layout.py)\n")
        fv.write(f"module {TOP} (\n    inout wire VGND, inout wire VDPWR,\n"
                 "    input wire [7:0] ui_in, output wire [7:0] uo_out,\n"
                 "    input wire [7:0] uio_in, output wire [7:0] uio_out, output wire [7:0] uio_oe,\n"
                 "    inout wire [7:0] ua, input wire ena, input wire clk, input wire rst_n);\n")
        fv.write("  wire vsP, vsN, vref, vbn, rst;\n")
        fv.write(f"  so_bias xbias (.vref(vref), .vbn(vbn), .vdd(VDPWR), .gnd(VGND));\n")
        fv.write(f"  {sc}inv_1 irst (.A(rst_n), .Y(rst), {pw});\n")
        for h, vin, port in (("P", "ua[0]", "uo_out"), ("N", "ua[1]", "uio_out")):
            fv.write(f"  wire vctrl{h}, " + ", ".join(f"ph{h}{i}, qq{h}{i}, bit{h}{i}" for i in range(7)) + ";\n")
            fv.write(f"  so_ana xana{h} (.vin({vin}), .vctrl(vctrl{h}), "
                     + ", ".join(f".b{i}(bit{h}{i})" for i in range(7))
                     + ", .vref(vref), .vbn(vbn), .rst(rst), .vdd(VDPWR), .gnd(VGND));\n")
            qnet = lambda n: f"{port}[{7 - PLAN['slot'][n] if h == 'P' else PLAN['slot'][n]}]"
            n_of = {PLAN["phase"][c["n"]]: c["n"] for c in cells if c["n"] != "buf"}
            for r in range(7):
                fv.write(f"  {sc}dfxtp_1 dq{h}{r} (.CLK(clk), .D({qnet(n_of[r])}), .Q(qq{h}{r}), {pw});\n")
                fv.write(f"  {sc}xor2_1 xq{h}{r} (.A({qnet(n_of[r])}), .B(qq{h}{r}), .X(bit{h}{r}), {pw});\n")
            fv.write(f"  vco_core xvco{h} (.vin(vctrl{h}), .vs(vs{h}), "
                     + ", ".join(f".ph{i}(ph{h}{i})" for i in range(7)) + ", .vdd(VDPWR), .gnd(VGND));\n")
            for c in cells:
                ph = PLAN["phase"][c["n"]]
                s_ = PLAN["slot"][c["n"]]
                q_ = f"{port}[{7 - s_ if h == 'P' else s_}]"
                if c["n"] == "buf":
                    fv.write(f"  {sc}buf_4 mon{h} (.A(ph{h}{ph}), .X({q_}), {pw});\n")
                else:
                    fv.write(f"  {sc}dfxtp_4 dff{h}{c['n']} (.CLK(clk), .D(ph{h}{ph}), .Q({q_}), {pw});\n")
        fv.write("  rarray xr (.vsp(vsP), .vsn(vsN), .gnd(VGND));\n")
        for nme in decaps:
            fv.write(f"  {sc}decap_12 {nme} ({pw});\n")
        fv.write("  assign uio_oe = {VDPWR, VDPWR, VDPWR, VDPWR, VDPWR, VDPWR, VDPWR, VDPWR};\n")
        fv.write("endmodule\n")
    return len(decaps)


if __name__ == "__main__":
    template, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    cells = build_half()
    open(os.path.join(outdir, "half.tcl"), "w").write("\n".join(L) + "\n")
    L.clear()
    n = build_top(template, cells, os.path.join(outdir, "lvs_ref.v"))
    open(os.path.join(outdir, "top.tcl"), "w").write("\n".join(L) + "\n")
    print(f"half.tcl, top.tcl, lvs_ref.v written ({n} decap_12)")
