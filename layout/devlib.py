"""Hand-drawn device primitives for the second-order loop (sky130A, magic types).

All coordinates in um. Every function appends magic tcl lines through the caller's
`rect` / `sq` helpers (passed in once with `init`). A FET is drawn with horizontal
diffusion and vertical gate fingers; S/D contact columns carry li, mcon and a met1
strip; all gate fingers join on a poly strap below (or above) the diffusion with one
poly contact (li + mcon + met1 pad).

fet(...) returns a dict:
  cols : list of (x, kind) for the S/D columns left to right, kind 'S' or 'D'
  y0,y1: diffusion y range (met1 columns span exactly this range)
  g    : (x, y) of the gate contact met1 pad centre
  x0,x1: diffusion x range
"""
R = None
SQ = None


def init(rect, sq):
    global R, SQ
    R, SQ = rect, sq


END = 0.33          # diffusion edge -> first gate (0.06 + licon 0.17 + 0.10)
GAP = 0.37          # gate -> gate with a shared contact column
STRAP = 0.55        # diffusion edge -> poly strap centre


def fet(kind, x0, y0, w, l, nf, gate="bottom", gx=None):
    diff, dc = ("ndiff", "ndiffc") if kind == "n" else ("pdiff", "pdiffc")
    x1 = x0 + 2 * END + nf * l + (nf - 1) * GAP
    y1 = y0 + w
    R(diff, x0, y0, x1, y1)
    gates = [x0 + END + k * (l + GAP) for k in range(nf)]
    cols = [x0 + 0.145] + [g + l + 0.185 for g in gates]
    for c in cols:
        R(dc, c - 0.085, y0 + 0.06, c + 0.085, y1 - 0.06)
        R("li", c - 0.085, y0 - 0.02, c + 0.085, y1 + 0.02)
        R("mcon", c - 0.085, y0 + 0.06, c + 0.085, y1 - 0.06)
        R("met1", c - 0.145, y0, c + 0.145, y1)
    ys = y0 - STRAP if gate == "bottom" else y1 + STRAP
    for g in gates:
        if gate == "bottom":
            R("poly", g, ys - 0.165, g + l, y1 + 0.13)
        else:
            R("poly", g, y0 - 0.13, g + l, ys + 0.165)
    R("poly", gates[0], ys - 0.165, gates[-1] + l, ys + 0.165)
    gx = (gates[0] + gates[-1] + l) / 2 if gx is None else gx
    R("poly", gx - 0.135, ys - 0.165, gx + 0.135, ys + 0.165)
    R("pc", gx - 0.085, ys - 0.085, gx + 0.085, ys + 0.085)
    R("li", gx - 0.085, ys - 0.165, gx + 0.085, ys + 0.165)
    SQ("mcon", gx, ys, 0.17)
    R("met1", gx - 0.16, ys - 0.19, gx + 0.16, ys + 0.19)
    kinds = ["S" if k % 2 == 0 else "D" for k in range(nf + 1)]
    return dict(cols=list(zip(cols, kinds)), y0=y0, y1=y1, g=(gx, ys), x0=x0, x1=x1)


def tap(kind, x0, y0, x1, y1):
    """substrate (p) or well (n) tap strip with li + mcon + met1 along its length (horizontal)."""
    d, c = ("psd", "psubdiffcont") if kind == "p" else ("nsd", "nsubdiffcont")
    R(d, x0, y0, x1, y1)
    yc = (y0 + y1) / 2
    R(c, x0 + 0.12, yc - 0.085, x1 - 0.12, yc + 0.085)
    R("li", x0 + 0.06, yc - 0.17, x1 - 0.06, yc + 0.17)
    R("mcon", x0 + 0.12, yc - 0.085, x1 - 0.12, yc + 0.085)
    R("met1", x0 + 0.06, yc - 0.16, x1 - 0.06, yc + 0.16)
    return yc


def v1(x, y):
    SQ("met1", x, y, 0.38); SQ("met2", x, y, 0.38); SQ("via1", x, y, 0.26)


def v2(x, y):
    SQ("met2", x, y, 0.42); SQ("met3", x, y, 0.5); SQ("via2", x, y, 0.28)


def v3(x, y):
    SQ("met3", x, y, 0.52); SQ("met4", x, y, 0.52); SQ("via3", x, y, 0.32)


def h(layer, xa, xb, y, w):
    R(layer, min(xa, xb), y - w / 2, max(xa, xb), y + w / 2)


def v(layer, x, ya, yb, w):
    R(layer, x - w / 2, min(ya, yb), x + w / 2, max(ya, yb))


def ota(x0, y0):
    """5T OTA: NMOS pair M1 (inp, drain x) / M2 (inn, drain out), tail M5 (vbn),
    PMOS mirror M3 (diode, x) / M4 (out). Origin = lower-left corner (p-tap strip).
    Rows bottom-up: p-tap | NMOS (M5 M1 M2, gates below) | n-tap | PMOS (M3 M4, gates above).
    Returns gate pads (met1) inp / inn / vbn, out (met2 riser x, y), rails and extent."""
    yn = y0 + 1.4
    m5 = fet("n", x0 + 0.2, yn, 2.0, 2.0, 2)
    m1 = fet("n", m5["x1"] + 0.6, yn, 4.0, 1.0, 2)
    m2 = fet("n", m1["x1"] + 0.6, yn, 4.0, 1.0, 2)
    xe = m2["x1"] + 0.2
    gnd_y = tap("p", x0, y0, xe, y0 + 0.44)
    ytap = yn + 4.0 + 1.0
    yp = ytap + 0.6
    m3 = fet("p", m1["x0"], yp, 4.0, 1.0, 2, gate="top")
    m4 = fet("p", m2["x0"], yp, 4.0, 1.0, 2, gate="top")
    R("nwell", m3["x0"] - 0.6, yn + 4.0 + 0.45, m4["x1"] + 0.6, yp + 4.0 + 1.0)
    vdd_y = tap("n", m3["x0"] - 0.2, ytap - 0.22, m4["x1"] + 0.2, ytap + 0.22)
    for x, k in m5["cols"]:
        if k == "S":
            v("met1", x, gnd_y, yn + 0.1, 0.29)
    for m in (m3, m4):
        for x, k in m["cols"]:
            if k == "S":
                v("met1", x, vdd_y, yp + 0.1, 0.29)
    y_t = yn + 0.5
    xs = [x for x, k in m5["cols"] if k == "D"] + [x for m in (m1, m2) for x, k in m["cols"] if k == "S"]
    for x in xs:
        v1(x, y_t)
    h("met2", min(xs), max(xs), y_t, 0.3)
    xd1 = [x for x, k in m1["cols"] if k == "D"][0]
    xd2 = [x for x, k in m2["cols"] if k == "D"][0]
    for xd in (xd1, xd2):              # M1->M3 (x) and M2->M4 (out) drains
        v1(xd, yn + 3.5); v("met2", xd, yn + 3.5, yp + 0.5, 0.3); v1(xd, yp + 0.5)
    g3, g4 = m3["g"], m4["g"]
    v("met1", g3[0], yp + 3.9, g3[1], 0.29)          # M3 diode: drain column up to its gate pad
    h("met1", g3[0], g4[0], g3[1], 0.38)             # M3/M4 gate bar
    return dict(m1=m1, m2=m2, m3=m3, m4=m4, m5=m5, gnd_y=gnd_y, vdd_y=vdd_y,
                inp=m1["g"], inn=m2["g"], vbn=m5["g"], out=(xd2, (ytap + yp) / 2 + 1.0),
                x0=x0, x1=xe, y1=yp + 4.0 + 1.0)
