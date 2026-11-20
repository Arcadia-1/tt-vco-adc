"""Generate the Magic Tcl script that draws tt_um_arcadia1_vco_adc (sky130A, 1x2 tile).

Pseudo-differential: two identical halves (P on the right, N translated 70 um left).
P: VINP = ua[0], phases -> uo_out[6:0], monitor -> uo_out[7].
N: VINN = ua[1], phases -> uio_out[6:0], monitor -> uio_out[7]; uio_oe tied to VDPWR.

Blocks
  VCO      : V-to-I (M1 + R1), bias mirror (Mpd, Mp2, Mnd), 7 current-starved
             inverter stages with NMOS load caps, hand drawn.
  R1       : xhigh poly resistor from the PDK generator (vertical).
  DFF row  : sky130_fd_sc_hd taps + 7x dfxtp_4 + buf_4 (monitor).
  Routing  : met2 verticals, met3 horizontal tracks, met4 stubs to the TT pins.
  Power    : VDPWR / VGND met4 stripes on the right edge.

usage: python3 gen_layout.py > build.tcl ; magic -dnull -noconsole -rcfile ... build.tcl
"""
import os

TOP = "tt_um_arcadia1_vco_adc"
L = []          # tcl lines


def q(v):
    return f"{round(v * 200) / 200:.3f}um"


def rect(layer, x1, y1, x2, y2):
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    L.append(f"box {q(x1)} {q(y1)} {q(x2)} {q(y2)}; paint {layer}")


def sq(layer, cx, cy, s):
    rect(layer, cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2)


# ---------------------------------------------------------------- vias
def mcon(cx, cy, m1=0.29):
    """li -> met1 at (cx, cy); li is assumed to be present."""
    sq("mcon", cx, cy, 0.17)
    sq("met1", cx, cy, m1)


def via1(cx, cy):
    sq("met1", cx, cy, 0.38)
    sq("met2", cx, cy, 0.38)
    sq("via1", cx, cy, 0.26)


def via2(cx, cy):
    sq("met2", cx, cy, 0.42)
    sq("met3", cx, cy, 0.5)
    sq("via2", cx, cy, 0.28)


def via3(cx, cy):
    sq("met3", cx, cy, 0.52)
    sq("met4", cx, cy, 0.52)
    sq("via3", cx, cy, 0.32)


def stack(cx, cy, frm, to):
    """via stack between metal levels frm..to (1=met1 ... 4=met4)."""
    f = {1: via1, 2: via2, 3: via3}
    for lv in range(frm, to):
        f[lv](cx, cy)


def hwire(layer, x1, x2, y, w):
    rect(layer, x1, y - w / 2, x2, y + w / 2)


def vwire(layer, x, y1, y2, w):
    rect(layer, x - w / 2, y1, x + w / 2, y2)


# ---------------------------------------------------------------- geometry constants
DIE_W, DIE_H = 161.0, 225.76
VDP_X = (154.4, 156.4)      # VDPWR stripe
VGN_X = (157.9, 159.9)      # VGND stripe
STRIPE_Y = (5.0, 220.76)
VDP_C = sum(VDP_X) / 2
VGN_C = sum(VGN_X) / 2

# VCO block origin (local coordinates below are relative to it)
XV, YV = 80.0, 178.0
PITCH = 3.0                 # stage pitch
NST = 7
XSTAGE0 = 6.0               # column A at 0, column B at 3, ring from 6

# local y levels
Y_CAP = (0.0, 2.0)          # load cap diffusion (W = 2)
Y_GND = (2.9, 3.38)         # VGND rail (met1)
Y_VBN = (3.6, 3.9)          # vbn poly bus
Y_N = (4.3, 4.8)            # NMOS strip (W = 0.5)
Y_P = (6.1, 7.1)            # PMOS strip (W = 1.0)
Y_VBP = (7.5, 7.8)          # vbp poly bus
Y_VDD = (8.1, 8.58)         # VPWR rail (met1)
Y_NW = (5.9, 8.9)           # nwell
Y_IN = (5.37, 5.54)         # input li bar / poly contact
Y_RB = 5.07                 # ring-back met1 centre line
Y_TAP = 5.985               # phase tap mcon/via1 centre

LS = 1.0                    # starve device length
XG0, XG1 = 0.33, 0.33 + LS  # starve gate
XI0 = XG1 + 0.30            # input gate start
XI1 = XI0 + 0.15
XD0, XD1 = XI1 + 0.10, XI1 + 0.27   # drain contact
XDE = XD1 + 0.06            # stage diff end
XC1 = 0.33 + 2.0            # cap gate end (L = 2)

DFF_X0, DFF_Y0 = 78.0, 196.0
TAPW, DFFW, BUFW = 0.46, 8.74, 2.76

PH_TRACK_Y = [187.6 + 0.9 * i for i in range(NST)]   # met3, below DFF row
Q_TRACK_Y = [200.2 + 0.9 * i for i in range(8)]      # met3, above DFF row (P half)
Q_TRACK_N_Y = [210.0 + 0.9 * i for i in range(8)]    # met3, N half outputs
CLK_TRACK_Y = 208.2
TIE_BUS_Y = 219.8
HALF_DX = {"P": 0.0, "N": -70.0}
UA0_X, UA1_X = 152.26, 132.94
VIN_N_M3_Y = 170.0
R1_X = 79.0
R1_L = 60.0


def set_half(h):
    """move the drawing origin of the VCO block, R1 and DFF row to half h"""
    global XV, R1_X, DFF_X0
    XV = 80.0 + HALF_DX[h]
    R1_X = 79.0 + HALF_DX[h]
    DFF_X0 = 78.0 + HALF_DX[h]


def pin_x(name):
    tbl = {f"uo_out[{i}]": 94.3 - 2.76 * i for i in range(8)}
    tbl.update({f"uio_out[{i}]": 72.22 - 2.76 * i for i in range(8)})
    tbl.update({f"uio_oe[{i}]": 50.14 - 2.76 * i for i in range(8)})
    tbl["clk"] = 143.98
    return tbl[name]


def A(x, y):
    """local VCO coordinates -> absolute"""
    return XV + x, YV + y


def lrect(layer, x1, y1, x2, y2):
    rect(layer, XV + x1, YV + y1, XV + x2, YV + y2)


def contact_col(diff, cx0, cx1, y0, y1):
    """diffusion contact column with li on top (li extended 0.08 in y)."""
    c = {"ndiff": "ndiffc", "pdiff": "pdiffc", "psd": "psubdiffcont", "nsd": "nsubdiffcont"}[diff]
    lrect(c, cx0, y0, cx1, y1)
    lrect("li", cx0, y0 - 0.08, cx1, y1 + 0.08)


def poly_contact(cx, cy):
    """licon on poly at local (cx, cy) with poly pad and li pad."""
    lrect("pc", cx - 0.085, cy - 0.085, cx + 0.085, cy + 0.085)
    lrect("poly", cx - 0.135, cy - 0.165, cx + 0.135, cy + 0.165)
    lrect("li", cx - 0.085, cy - 0.165, cx + 0.085, cy + 0.165)


def lmcon(x, y):
    mcon(XV + x, YV + y)


# ---------------------------------------------------------------- VCO block
def draw_vco():
    ring_end = XSTAGE0 + PITCH * NST
    # rails, buses, well
    lrect("nwell", -0.4, Y_NW[0], ring_end - 0.4, Y_NW[1])
    rect("met1", XV - 0.5, YV + Y_GND[0], VGN_X[1] - 0.3, YV + Y_GND[1])
    rect("met1", XV - 0.5, YV + Y_VDD[0], VDP_X[1] - 0.3, YV + Y_VDD[1])
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

    # ---- column A: M1 (vin -> vbp, source vs) and Mpd (diode vbp)
    a = 0.0
    lrect("ndiff", a, -2.0, a + XG1 + 0.33, 2.0)                  # M1 W=4 L=1
    lrect("poly", a + XG0, -2.75, a + XG1, 2.13)
    contact_col("ndiff", a + 0.06, a + 0.23, -1.9, 1.9)           # source = vs
    contact_col("ndiff", a + XG1 + 0.10, a + XG1 + 0.27, -1.9, 1.9)  # drain = vbp
    poly_contact(a + 0.83, -2.535)                                # gate = vin
    lmcon(a + 0.83, -2.535)
    lrect("pdiff", a, Y_P[0], a + XG1 + 0.33, Y_P[1])            # Mpd W=1 L=1
    lrect("poly", a + XG0, Y_P[0] - 0.13, a + XG1, Y_VBP[1])
    contact_col("pdiff", a + 0.06, a + 0.23, Y_P[0] + 0.06, Y_P[1] - 0.06)
    contact_col("pdiff", a + XG1 + 0.10, a + XG1 + 0.27, Y_P[0] + 0.06, Y_P[1] - 0.06)
    lrect("li", a + 0.06, Y_P[0], a + 0.23, Y_VDD[1] - 0.1)      # source to VPWR
    lmcon(a + 0.145, 8.34)
    lrect("li", a + XG1 + 0.10, -1.98, a + XG1 + 0.27, 7.82)     # vbp strip M1.d - Mpd.d
    lrect("pc", a + XG1 + 0.10, 7.565, a + XG1 + 0.27, 7.735)    # strip -> vbp bus
    lrect("li", a + 0.06, -3.62, a + 0.23, -1.9)                  # vs down
    lmcon(a + 0.145, -3.535)
    ptap(a + 0.7)
    ntap(a + 0.7)

    # ---- column B: Mp2 (vbp -> vbn) and Mnd (diode vbn)
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
    lrect("li", b + XG1 + 0.10, 3.585, b + XG1 + 0.27, Y_P[1] - 0.02)   # vbn strip
    lrect("pc", b + XG1 + 0.10, 3.665, b + XG1 + 0.27, 3.835)
    ptap(b + 0.7)
    ntap(b + 0.7)

    # ---- ring stages
    for i in range(NST):
        s = XSTAGE0 + PITCH * i
        # NMOS stack footer(vbn) + input
        lrect("ndiff", s, Y_N[0], s + XDE, Y_N[1])
        lrect("poly", s + XG0, Y_VBN[0], s + XG1, Y_N[1] + 0.13)
        contact_col("ndiff", s + 0.06, s + 0.23, Y_N[0] + 0.06, Y_N[1] - 0.06)
        contact_col("ndiff", s + XD0, s + XD1, Y_N[0] + 0.06, Y_N[1] - 0.06)
        # PMOS stack header(vbp) + input
        lrect("pdiff", s, Y_P[0], s + XDE, Y_P[1])
        lrect("poly", s + XG0, Y_P[0] - 0.13, s + XG1, Y_VBP[1])
        contact_col("pdiff", s + 0.06, s + 0.23, Y_P[0] + 0.06, Y_P[1] - 0.06)
        contact_col("pdiff", s + XD0, s + XD1, Y_P[0] + 0.06, Y_P[1] - 0.06)
        # input gate + contact
        lrect("poly", s + XI0, Y_N[0] - 0.13, s + XI1, Y_P[1] + 0.13)
        lrect("poly", s + XI0 - 0.32, 5.29, s + XI1, 5.62)
        lrect("pc", s + XI0 - 0.27, Y_IN[0], s + XI0 - 0.10, Y_IN[1])
        lrect("li", s + XI0 - 0.27, 5.29, s + XI0 - 0.10, 5.62)
        x_prev_out = s - PITCH + XD0 if i > 0 else s - 0.6
        lrect("li", x_prev_out, Y_IN[0], s + XI0 - 0.10, Y_IN[1])
        # load cap: NMOS, gate = out, S/D = gnd
        lrect("ndiff", s, Y_CAP[0], s + XC1 + 0.33, Y_CAP[1])
        lrect("poly", s + XG0, Y_CAP[0] - 0.13, s + XC1, 2.50)
        contact_col("ndiff", s + 0.06, s + 0.23, Y_CAP[0] + 0.1, Y_CAP[1] - 0.1)
        contact_col("ndiff", s + XC1 + 0.10, s + XC1 + 0.27, Y_CAP[0] + 0.1, Y_CAP[1] - 0.1)
        lrect("pc", s + XD0, 2.25, s + XD1, 2.42)
        # li: source column (cap left + N source) to VGND rail
        lrect("li", s + 0.06, Y_CAP[0] + 0.02, s + 0.23, Y_N[1] - 0.02)
        lmcon(s + 0.145, 3.14)
        lrect("li", s + XC1 + 0.10, Y_CAP[0] + 0.02, s + XC1 + 0.27, 3.305)
        lmcon(s + XC1 + 0.185, 3.14)
        # P source to VPWR
        lrect("li", s + 0.06, Y_P[0], s + 0.23, Y_VDD[1] - 0.1)
        lmcon(s + 0.145, 8.34)
        # output strip: cap gate contact .. N drain .. P drain
        lrect("li", s + XD0, 2.17, s + XD1, Y_P[1] - 0.02)
        # phase tap li -> met1 -> met2
        xo = s + (XD0 + XD1) / 2
        lmcon(xo, Y_TAP)
        x_abs, y_abs = A(xo, Y_TAP)
        via1(x_abs, y_abs)
        ptap(s + 1.15)
        ntap(s + 1.15)

    # ring-back: stage 6 output -> stage 0 input, on met1
    s6 = XSTAGE0 + PITCH * (NST - 1)
    xo6 = s6 + (XD0 + XD1) / 2
    lmcon(xo6, Y_RB)
    x_in0 = XSTAGE0 - 0.515
    lmcon(x_in0, (Y_IN[0] + Y_IN[1]) / 2)
    lrect("met1", x_in0 - 0.145, Y_RB - 0.145, xo6 + 0.145, Y_RB + 0.145)
    lrect("met1", x_in0 - 0.145, Y_RB - 0.145, x_in0 + 0.145, (Y_IN[0] + Y_IN[1]) / 2 + 0.145)


def phase_x(i):
    return XV + XSTAGE0 + PITCH * i + (XD0 + XD1) / 2


# ---------------------------------------------------------------- std cell row
def place(cell, x, y, inst):
    L.append(f"box position {q(x)} {q(y)}")
    L.append(f"getcell {cell} child 0 0")
    L.append(f"identify {inst}")


def draw_row(h):
    x = DFF_X0
    dffs = []
    for i in range(NST):
        place("sky130_fd_sc_hd__tapvpwrvgnd_1", x, DFF_Y0, f"tap{h}{i}")
        x += TAPW
        place("sky130_fd_sc_hd__dfxtp_4", x, DFF_Y0, f"dff{h}{i}")
        dffs.append(x)
        x += DFFW
    place("sky130_fd_sc_hd__tapvpwrvgnd_1", x, DFF_Y0, f"tap{h}7")
    x += TAPW
    xbuf = x
    place("sky130_fd_sc_hd__buf_4", x, DFF_Y0, f"mon{h}")
    x += BUFW
    place("sky130_fd_sc_hd__tapvpwrvgnd_1", x, DFF_Y0, f"tap{h}8")
    x += TAPW
    # extend rails to the stripes
    rect("met1", x - 0.2, DFF_Y0 - 0.24, VGN_X[1] - 0.3, DFF_Y0 + 0.24)
    rect("met1", x - 0.2, DFF_Y0 + 2.48, VDP_X[1] - 0.3, DFF_Y0 + 2.96)
    return dffs, xbuf


def pin_pad(x, y, h=0.5):
    """li pin -> mcon -> met1 pad (0.32 x h) -> via1 -> met2 at (x, y)."""
    sq("mcon", x, y, 0.17)
    rect("met1", x - 0.16, y - h / 2, x + 0.16, y + h / 2)
    sq("via1", x, y, 0.26)
    rect("met2", x - 0.16, y - 0.19, x + 0.16, y + 0.19)


def route_digital(dffs, xbuf, h):
    W2, W3 = 0.3, 0.3
    # phases: VCO tap (met2) -> met3 track -> DFF D (and buf A for ph3)
    for i in range(NST):
        xp = phase_x(i)
        yt = PH_TRACK_Y[i]
        vwire("met2", xp, YV + Y_TAP, yt + 0.15, W2)
        via2(xp, yt)
        xd = dffs[i] + 1.58
        yd = DFF_Y0 + 1.36
        pin_pad(xd, yd)
        via2(xd, yt)
        vwire("met2", xd, yt - 0.15, yd, W2)
        xs = [xp, xd]
        if i == 3:                                   # monitor buffer input
            xa = xbuf + 0.28
            ya = DFF_Y0 + 1.195
            pin_pad(xa, ya, h=0.36)
            via2(xa, yt)
            vwire("met2", xa, yt - 0.15, ya, W2)
            xs.append(xa)
        hwire("met3", min(xs) - 0.2, max(xs) + 0.2, yt, W3)

    # outputs: Q -> met2 up -> met3 track -> met4 stub to uo pin
    port = "uo_out" if h == "P" else "uio_out"
    tracks = Q_TRACK_Y if h == "P" else Q_TRACK_N_Y
    outs = [(dffs[i] + 8.53, DFF_Y0 + 1.18, f"{port}[{i}]") for i in range(NST)]
    outs.append((xbuf + 1.78, DFF_Y0 + 1.175, f"{port}[7]"))
    for k, (xq, yq, pin) in enumerate(outs):
        yt = tracks[k]
        pin_pad(xq, yq, h=0.36)
        vwire("met2", xq, yq, yt + 0.15, W2)
        via2(xq, yt)
        xp = pin_x(pin)
        hwire("met3", min(xq, xp) - 0.2, max(xq, xp) + 0.2, yt, W3)
        via3(xp, yt)
        met4_stub(xp, yt)

    return [d + 0.265 for d in dffs]


def route_clock_ties(xc_pins):
    W3 = 0.3
    # clock: pin -> met4 stub -> met3 track -> met2 drops -> CLK pins (both halves)
    for xc in xc_pins:
        yc = DFF_Y0 + 1.36
        pin_pad(xc, yc, h=0.36)
        vwire("met2", xc, yc, CLK_TRACK_Y + 0.15, 0.3)
        via2(xc, CLK_TRACK_Y)
    xk = pin_x("clk")
    hwire("met3", min(xc_pins) - 0.2, xk + 0.2, CLK_TRACK_Y, W3)
    via3(xk, CLK_TRACK_Y)
    met4_stub(xk, CLK_TRACK_Y)

    # uio_oe[7:0] tied high (uio used as outputs) through a met3 bus to VDPWR
    xs = [pin_x(f"uio_oe[{i}]") for i in range(8)]
    hwire("met3", min(xs) - 0.4, VDP_C + 0.4, TIE_BUS_Y, 0.8)
    for xp in xs:
        via3(xp, TIE_BUS_Y)
        met4_stub(xp, TIE_BUS_Y)
    via3(VDP_C, TIE_BUS_Y)


def met4_stub(xp, y):
    """met4 from a top pin (y 224.76..225.76, 0.3 wide) down to y."""
    vwire("met4", xp, 222.0, DIE_H, 0.3)
    vwire("met4", xp, y - 0.23, 222.2, 0.6)


# ---------------------------------------------------------------- analog pins, R1, power
def route_analog(h):
    xg, yg = A(0.83, -2.535)
    via1(xg, yg)
    if h == "P":
        # VINP: M1 gate pad -> via1 -> met2 east -> ua[0] met4
        hwire("met2", xg - 0.2, UA0_X + 0.2, yg, 0.3)
        via2(UA0_X, yg)
        via3(UA0_X, yg)
        vwire("met4", UA0_X, 0.0, yg + 0.23, 0.9)
    else:
        # VINN: gate pad -> met2 down -> met3 east (below the P half) -> ua[1] met4
        vwire("met2", xg, VIN_N_M3_Y - 0.15, yg, 0.3)
        via2(xg, VIN_N_M3_Y)
        hwire("met3", xg - 0.25, UA1_X + 0.26, VIN_N_M3_Y, 0.4)
        via3(UA1_X, VIN_N_M3_Y)
        vwire("met4", UA1_X, 0.0, VIN_N_M3_Y + 0.26, 0.9)

    # vs: M1 source (mcon at local (0.145, -3.535)) -> met1 bar -> met2 down to R1
    xs, ys = A(0.145, -3.535)
    rect("met1", R1_X - 1.1, ys - 0.15, xs + 0.15, ys + 0.15)
    # R1: folded xhigh poly resistor (2 strips, snake) so the URPM implant is wide
    # enough (rpm.1). Terminals (both at the bottom): R1 at x-0.415, R2 at x+0.415.
    rname = "sky130_fd_pr__res_xhigh_po_" + "0p35"
    yc = YV - 4.5 - 16.4
    L.append(f"box position {q(R1_X)} {q(yc)}")
    L.append(f"magic::gencell sky130::{rname} R1{h} w 0.35 l {R1_L / 2} nx 2 snake 1 guard 0")
    L.append("load " + TOP)
    # gencell puts the lower-left corner at the box; re-centre the instance
    L.append(f"select cell R1{h}")
    L.append("set b [box values]")
    L.append(f"set nx [expr {{round({R1_X}*200 - ([lindex $b 2]-[lindex $b 0])/2.0)}}]")
    L.append(f"set ny [expr {{round({yc}*200 - ([lindex $b 3]-[lindex $b 1])/2.0)}}]")
    L.append("move to ${nx}i ${ny}i")
    L.append(f"select cell R1{h}")
    L.append('puts "R1BOX [box values]"')
    L.append("select clear")
    y_term = yc - 15.25                         # terminal pads span yc-16.31 .. yc-14.205
    xm2 = R1_X - 0.9
    via1(xm2, ys)
    vwire("met2", xm2, y_term, ys, 0.3)
    via1(xm2, y_term)
    hwire("met1", xm2, R1_X - 0.29, y_term, 0.3)
    # R2 terminal -> met3 -> VGND stripe
    xr2 = R1_X + 0.415
    stack(xr2, y_term, 1, 3)
    hwire("met3", xr2 - 0.2, VGN_C + 0.3, y_term, 0.6)
    via3(VGN_C, y_term)
    return yc


def power():
    for name, (x0, x1) in (("VDPWR", VDP_X), ("VGND", VGN_X)):
        L.append(f"box {q(x0)} {q(STRIPE_Y[0])} {q(x1)} {q(STRIPE_Y[1])}")
        L.append("paint met4")
        L.append(f"label {name} FreeSans 0.25u -met4")
        L.append("port make")
        L.append(f"port use {'ground' if name == 'VGND' else 'power'}")
        L.append("port class bidirectional")
        L.append("port connections n s e w")
    # rails -> stripes (met1 -> met4 stacks)
    for y in (YV + sum(Y_VDD) / 2, DFF_Y0 + 2.72):
        stack(VDP_C - 0.5, y, 1, 4)
        stack(VDP_C + 0.5, y, 1, 4)
    for y in (YV + sum(Y_GND) / 2, DFF_Y0):
        stack(VGN_C - 0.5, y, 1, 4)
        stack(VGN_C + 0.5, y, 1, 4)


def main(template):
    L.append("drc off")
    L.append("snap internal")
    L.append(f"addpath $::env(PDK_ROOT)/sky130A/libs.ref/sky130_fd_sc_hd/mag")
    L.append(f"def read {template}")
    L.append(f"cellname rename tt_um_template {TOP}")
    L.append(f"load {TOP}")
    clk_pins = []
    for h in ("P", "N"):
        set_half(h)
        draw_vco()
        dffs, xbuf = draw_row(h)
        clk_pins += route_digital(dffs, xbuf, h)
        yc = route_analog(h)
    set_half("P")
    route_clock_ties(clk_pins)
    power()
    L.append(f"puts \"R1CENTER {yc}\"")
    L.append("select top cell")
    L.append("writeall force")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    import sys
    print(main(sys.argv[1] if len(sys.argv) > 1 else "tt_analog_1x2.def"))
