"""Hand-drawn device primitives for the second-order loop (sky130A, magic types).

All coordinates in um. Every function appends magic tcl lines through the caller's
`rect` / `sq` helpers (passed in once with `init`). A FET is drawn with horizontal
diffusion and vertical gate fingers; S/D contact columns carry li, mcon and a met1
strip; gate fingers join on poly strap(s) below (or above) the diffusion with poly
contact(s) (li + mcon + met1 pad).

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


def _poly_pad(gx, ys):
    R("poly", gx - 0.135, ys - 0.165, gx + 0.135, ys + 0.165)
    R("pc", gx - 0.085, ys - 0.085, gx + 0.085, ys + 0.085)
    R("li", gx - 0.085, ys - 0.165, gx + 0.085, ys + 0.165)
    SQ("mcon", gx, ys, 0.17)
    R("met1", gx - 0.16, ys - 0.19, gx + 0.16, ys + 0.19)


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
    gx = (gates[0] + gates[-1] + l) / 2 if gx is None else gx
    R("poly", min(gates[0], gx - 0.135), ys - 0.165, max(gates[-1] + l, gx + 0.135), ys + 0.165)
    _poly_pad(gx, ys)
    kinds = ["S" if k % 2 == 0 else "D" for k in range(nf + 1)]
    return dict(cols=list(zip(cols, kinds)), y0=y0, y1=y1, g=(gx, ys), x0=x0, x1=x1, gates=gates)


def cc_pair(kind, x0, y0, w, l, gate="bottom"):
    """Common-centroid A B B A 8-finger continuous diffusion array:
      fingers 0,1,6,7 -> device A (outer, 2+2 fingers)
      fingers 2,3,4,5 -> device B (inner, 4 fingers)
    Even columns (0, 2, 4, 6, 8) are shared source S; odd columns (1, 7) are A drains
    and odd columns (3, 5) are B drains.
    When gate='bottom' (NMOS diff pair), three separate poly straps are drawn:
      gA_L (fingers 0..1), gB (fingers 2..5), gA_R (fingers 6..7).
    When gate='top' (PMOS mirror), all 8 fingers share one poly strap with gate pad g."""
    nf = 8
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
    out = dict(
        x0=x0, x1=x1, y0=y0, y1=y1, cols=cols, gates=gates,
        s_cols=[cols[k] for k in (0, 2, 4, 6, 8)],
        da_cols=[cols[1], cols[7]],
        db_cols=[cols[3], cols[5]],
    )
    if gate == "bottom":
        # Three disjoint bottom poly straps (gap = GAP = 0.37 um >= 0.21 um)
        for key, i0, i1 in (("gA_L", 0, 1), ("gB", 2, 5), ("gA_R", 6, 7)):
            R("poly", gates[i0], ys - 0.165, gates[i1] + l, ys + 0.165)
            gx = (gates[i0] + gates[i1] + l) / 2
            _poly_pad(gx, ys)
            out[key] = (gx, ys)
    else:
        R("poly", gates[0], ys - 0.165, gates[-1] + l, ys + 0.165)
        gx = (gates[0] + gates[-1] + l) / 2
        _poly_pad(gx, ys)
        out["g"] = (gx, ys)
    return out


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


def active_clamp(cx0, yn, yp, ytap, gnd_y, y_out, vbn_jog_y,
                 ws=0.42, ls=8.0, wld=0.42, lld=8.0, wpd=6.0, lpd=0.5, wc=4.0, lc=3.0):
    """5-FET brick-wall active vctrl clamp (CLAMP_A5) immediately right of the OTA:
      XM_sns (PMOS, ws/ls):     D=c, G=gnd, S=out, B=vdd  (shares OTA nwell & n-tap)
      XM_ld1 (NMOS, wld/lld):   D=c, G=vbn, S=m1,  B=gnd
      XM_ld2 (NMOS, wld/lld):   D=m1, G=vbn, S=gnd, B=gnd
      XM_pd  (NMOS, wpd/lpd):   D=out, G=c, S=gnd, B=gnd  (2 fingers x wpd/2)
      XM_c   (NMOS, wc/lc):     S=D=c, G=out, B=gnd       (MOS clamp compensation cap)

    Layout (100% planar, zero metal crossings, compact 8.66 um width):
      - Bottom-left (yn): XM_pd (2 fingers, col 0 & 2 = S = gnd drop straight on met1
        to gnd_y; col 1 = D = out rises straight up on met2 to y_out; gate = c on top).
      - Bottom-right (yn): XM_c (1 finger, S=D=c tied to XM_pd.G on met1 at y_pd_g;
        gate = out on top jogs left on met2 to XM_pd.D out spine).
      - Upper NMOS (yn+6.86 & yn+8.66): XM_ld2 (below) & XM_ld1 (above), both 1-finger
        L=8 with col 0 (left) = m1 joined by met1, XM_ld2 col 1 = gnd to x_gnd trunk,
        XM_ld1 col 1 = c aligned with XM_sns col 1 on vertical met2 spine, gates tied on
        met1 and fed from vbn_jog_y via met2 riser at x_vbn_r.
      - Top PMOS (yp+2.5): XM_sns (1 finger, col 0 = S = out to y_out, col 1 = D = c,
        top gate = gnd routed right on met2 to x_gnd -> switches to met1 below nwell
        -> drops to gnd_y).
    Returns dict with x1, vbn=(x_vbn_r, vbn_jog_y), out_x, pm_x1, ws_top."""
    # 1. XM_pd (2 fingers x wpd/2, bottom-left): col 0,2 = S (gnd), col 1 = D (out), top gate = c
    mpd = fet("n", cx0, yn, wpd / 2, lpd, 2, gate="top")
    for x, k in mpd["cols"]:
        if k == "S":
            v("met1", x, gnd_y, yn + 0.1, 0.29)
    x_out = mpd["cols"][1][0]

    # 2. XM_c (1 finger wc/lc, bottom-right next to XM_pd): S=D=c, top gate = out
    mc = fet("n", mpd["x1"] + 0.75, yn, wc, lc, 1, gate="top")

    # 3. XM_ld2 (below) & XM_ld1 (above), stacked above XM_pd / XM_c (both gate='bottom')
    y_ld2 = yn + max(wpd / 2 + 1.1, wc + 1.1) + 1.76   # clear of XM_c top gate strap by >= 1.38 um
    y_ld1 = y_ld2 + wld + 1.38                          # clear poly/met1 between XM_ld2 and XM_ld1
    mld2 = fet("n", cx0, y_ld2, wld, lld, 1, gate="bottom")
    mld1 = fet("n", cx0, y_ld1, wld, lld, 1, gate="bottom")

    # 4. XM_sns (PMOS ws/ls inside OTA nwell, above y_out): col 0 = S (out), col 1 = D (c), top gate = gnd
    yp_sns = yp + 2.5
    msns = fet("p", cx0, yp_sns, ws, ls, 1, gate="top")

    # --- Net m1: XM_ld1 col 0 <-> XM_ld2 col 0 straight on met1
    v("met1", mld1["cols"][0][0], y_ld2 + 0.1, y_ld1 + wld - 0.1, 0.29)

    # --- Net vbn: XM_ld1.G <-> XM_ld2.G on met1; met2 riser at x_vbn_r from vbn_jog_y (met3 via2)
    x_ldg, y_ld2g = mld2["g"]
    v("met1", x_ldg, y_ld2g, mld1["g"][1], 0.30)
    x_vbn_r = mc["x1"] + 0.74                           # cleanly between XM_c.x1 and c spine (col 1)
    v1(x_ldg, y_ld2g)
    h("met2", x_ldg - 0.15, x_vbn_r + 0.15, y_ld2g, 0.30)
    v("met2", x_vbn_r, vbn_jog_y, y_ld2g + 0.15, 0.30)

    # --- Net c: XM_pd.G + XM_c (col 0 & col 1) on met1 bar -> via1 at x_c -> vertical met2 spine
    #     up through XM_ld1 col 1 (D=c) to XM_sns col 1 (D=c)
    x_c = mld1["cols"][1][0]                            # == msns["cols"][1][0] when ls == lld
    x_c_sns = msns["cols"][1][0]
    y_c_bar = mpd["g"][1]
    h("met1", mpd["g"][0] - 0.16, x_c + 0.19, y_c_bar, 0.30)
    v1(x_c, y_c_bar)
    y_ld1_m = y_ld1 + wld / 2
    y_sns_m = yp_sns + ws / 2
    v1(x_c, y_ld1_m)
    v1(x_c_sns, y_sns_m)
    if abs(x_c - x_c_sns) < 1e-6:
        v("met2", x_c, y_c_bar, y_sns_m, 0.30)
    else:
        v("met2", x_c, y_c_bar, ytap + 0.15, 0.30)
        h("met2", min(x_c, x_c_sns) - 0.15, max(x_c, x_c_sns) + 0.15, ytap, 0.30)
        v("met2", x_c_sns, ytap - 0.15, y_sns_m, 0.30)

    # --- Net out (vctrl): vertical met2 spine at x_out linking XM_pd.D, XM_c.G, y_out, and XM_sns.S
    y_pd_d = yn + wpd / 4
    v1(x_out, y_pd_d)
    v("met2", x_out, y_pd_d, y_out + 0.15, 0.30)
    v1(*mc["g"])
    h("met2", x_out - 0.15, mc["g"][0] + 0.15, mc["g"][1], 0.30)
    x_sns_s = msns["cols"][0][0]
    v1(x_sns_s, y_sns_m)
    v("met2", x_sns_s, y_out - 0.15, y_sns_m, 0.30)
    h("met2", min(x_sns_s, x_out) - 0.15, max(x_sns_s, x_out) + 0.15, y_out, 0.30)

    # --- Net gnd: XM_sns.G -> met2 right to x_gnd -> down across n-tap (ytap) -> via1 to met1
    #     below nwell (y_sw) -> met1 trunk straight down to gnd_y (picking up XM_ld2 col 1)
    x_gnd = max(mld1["x1"], mld2["x1"], msns["x1"]) + 0.72
    x_sg, y_sg = msns["g"]
    y_sw = y_ld1 + wld + 1.68                           # below nwell (yn + 12.45), above XM_ld1
    v1(x_sg, y_sg)
    h("met2", x_sg - 0.15, x_gnd + 0.15, y_sg, 0.30)
    v("met2", x_gnd, y_sw - 0.15, y_sg + 0.15, 0.30)
    v1(x_gnd, y_sw)
    v("met1", x_gnd, gnd_y, y_sw, 0.29)
    h("met1", mld2["cols"][1][0], x_gnd + 0.145, y_ld2 + wld / 2, 0.29)

    return dict(mpd=mpd, mc=mc, mld1=mld1, mld2=mld2, msns=msns,
                vbn=(x_vbn_r, vbn_jog_y), out_x=x_out,
                x1=x_gnd + 0.3, pm_x1=msns["x1"], ws_top=yp_sns + ws)


def ota(x0, y0, vbn_jog_y=None, clamp_params=None):
    """Upgraded common-centroid A B B A low-noise 5T OTA + 5-FET active vctrl clamp (CLAMP_A5):
      - M5 (tail): W=8, L=2 (4 fingers x 2/2, width 9.77 um)
      - M1/M2 (input pair): W=48, L=3 each (8-finger A B B A block, W_f=12, L=3, width 27.25 um)
        fingers 0,1,6,7 = M1 (vref), fingers 2,3,4,5 = M2 (vg)
      - M3/M4 (PMOS mirror): W=16, L=2 each (8-finger A B B A block, W_f=4, L=2, width 19.25 um)
        fingers 0,1,6,7 = M3 (diode, x), fingers 2,3,4,5 = M4 (out), centred above M1/M2
      - 5-FET CLAMP_A5 immediately to the right inside the same nwell/p-tap.
    Origin = lower-left corner (p-tap strip). Total height = 20.0 um (y0 .. y0 + 20.0).
    Returns inp_l, inp_r (met1 pads of M1), inn (M2), vbn (M5), vbn_c (clamp met2 via2 target),
    out (x, y on met2), gnd_y, vdd_y, x0, x1, vdd_x1, y1."""
    if clamp_params is None:
        clamp_params = dict(ws=0.42, ls=8.0, wld=0.42, lld=8.0, wpd=6.0, lpd=0.5, wc=4.0, lc=3.0)

    yn = y0 + 1.4
    if vbn_jog_y is None:
        vbn_jog_y = y0 + 1.70
    # M5 (nf=4, W_f=2, L=2): put gate pad under col 1 (D) so col 0,2,4 (S) drop cleanly to gnd_y
    x_m5 = x0 + 0.2
    m5 = fet("n", x_m5, yn, 2.0, 2.0, 4, gate="bottom", gx=x_m5 + END + 2.0 + 0.185)
    # M1/M2 common-centroid A B B A (nf=8, W_f=12, L=3)
    m12 = cc_pair("n", m5["x1"] + 0.6, yn, 12.0, 3.0, gate="bottom")
    ytap = yn + 12.0 + 1.0                      # y0 + 14.4
    yp = ytap + 0.6                             # y0 + 15.0
    # M3/M4 common-centroid A B B A (nf=8, W_f=4, L=2) centred above M1/M2 (snap to 0.005 um)
    w_m34 = 2 * END + 8 * 2.0 + 7 * GAP         # 19.25 um
    x_m34 = round(((m12["x0"] + m12["x1"]) / 2 - w_m34 / 2) * 200) / 200
    m34 = cc_pair("p", x_m34, yp, 4.0, 2.0, gate="top")

    # Active clamp placed right of M1/M2 inside same nwell + p-tap
    y_out = yp + 1.5                            # met2 out bar, cleanly above M3 via1 (yp + 0.5)
    gnd_y_nom = y0 + 0.22
    cl = active_clamp(m12["x1"] + 0.8, yn, yp, ytap, gnd_y_nom, y_out, vbn_jog_y, **clamp_params)

    xe = cl["x1"]
    gnd_y = tap("p", x0, y0, xe, y0 + 0.44)
    pm_x1 = max(m34["x1"], cl["pm_x1"])
    pm_top = max(yp + 4.0, cl["ws_top"])
    R("nwell", m34["x0"] - 0.6, yn + 12.0 + 0.45, pm_x1 + 0.6, pm_top + 1.0)
    vdd_y = tap("n", m34["x0"] - 0.2, ytap - 0.22, pm_x1 + 0.2, ytap + 0.22)

    # M5 sources (col 0, 2, 4) -> VGND p-tap
    for x, k in m5["cols"]:
        if k == "S":
            v("met1", x, gnd_y, yn + 0.1, 0.29)
    # M3/M4 sources (even cols 0, 2, 4, 6, 8) -> VDPWR n-tap
    for x in m34["s_cols"]:
        v("met1", x, vdd_y, yp + 0.1, 0.29)

    # Tail node t: M5 drains (col 1, 3) + M1/M2 sources (col 0, 2, 4, 6, 8) on met2 at yn + 0.5
    y_t = yn + 0.5
    xs_t = [x for x, k in m5["cols"] if k == "D"] + m12["s_cols"]
    for x in xs_t:
        v1(x, y_t)
    h("met2", min(xs_t), max(xs_t), y_t, 0.30)

    # Disjoint monotonic drain connections M1->M3 (x) and M2->M4 (out) across ytap on met2:
    # M1L (col 1) -> M3L (col 1), M2L (col 3) -> M4L (col 3),
    # M2R (col 5) -> M4R (col 5), M1R (col 7) -> M3R (col 7)
    y_nd = yn + 11.5
    for xn, xp_, yp_dst in (
        (m12["da_cols"][0], m34["da_cols"][0], yp + 0.5),
        (m12["db_cols"][0], m34["db_cols"][0], y_out),
        (m12["db_cols"][1], m34["db_cols"][1], y_out),
        (m12["da_cols"][1], m34["da_cols"][1], yp + 0.5),
    ):
        v1(xn, y_nd)
        v("met2", xn, y_nd, ytap + 0.15, 0.30)
        h("met2", min(xn, xp_) - 0.15, max(xn, xp_) + 0.15, ytap, 0.30)
        v("met2", xp_, ytap - 0.15, yp_dst, 0.30)
        v1(xp_, yp_dst)

    # M3 diode + M3/M4 gate tie on met1 at top poly strap (yp + 4.55):
    # M3L drain (col 1) and M3R drain (col 7) rise on met1 to top gate bar, shorting with g
    gx34, gy34 = m34["g"]
    for xd3 in m34["da_cols"]:
        v("met1", xd3, yp + 3.9, gy34 + 0.19, 0.29)
    h("met1", m34["da_cols"][0] - 0.145, m34["da_cols"][1] + 0.145, gy34, 0.38)

    # Output node (vctrl) met2 bar at y_out linking M4L (col 3), M4R (col 5), and clamp XM_sns/XM_pd
    h("met2", m34["db_cols"][0] - 0.15, cl["out_x"] + 0.15, y_out, 0.30)

    return dict(
        m12=m12, m34=m34, m5=m5, clamp=cl,
        gnd_y=gnd_y, vdd_y=vdd_y,
        inp_l=m12["gA_L"], inp_r=m12["gA_R"], inn=m12["gB"],
        vbn=m5["g"], vbn_c=cl["vbn"],
        out=(m34["db_cols"][0], y_out),
        x0=x0, x1=xe, vdd_x1=pm_x1 + 0.2, y1=pm_top + 1.0,
    )
