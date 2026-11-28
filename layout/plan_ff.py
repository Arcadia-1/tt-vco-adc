"""Placement search for the flip-flop block of one half (local x = distance from the axis).

Four abutting rows above the VCO: three rows hold two (dfxtp_1 + buf_4) isolated output
pairs each, one row holds (dff6 + obuf6) and the monitor buf_4. Row offsets are whole
placement sites (0.46 um), otherwise the rail contacts of two rows sharing a rail collide
(mcon.2); one site is excluded because the n-wells of the two mirrored halves would sit
0.54 um apart.

Each DFF slot holds abutted dfxtp_1 (7.36 um) + buf_4 (2.76 um) = 10.12 um:
- dff.Q_low -> obuf.A via local met1 jumper at y = fy(1.195)
- dff.Q_hi internal node rises straight UP on met2 from (x + 7.05, fy(2.05)) in a planar
  staircase to QBUS_Y[qtrack] (219.4 + 0.6 * qtrack) -> second register (dq/xq)
- obuf.X at (x + 7.36 + XCOL[xcol], fy(2.15)) jogs on met3 to SLOTS[slot] -> met4 pin
- dff.D is tapped at (x + 1.51, fy(0.95)) to stay >= 0.33 um clear of dfxtp_1 internal met1
  at y = 1.46..1.60.

The first placement with no met2 / met3 spacing violation (own shapes plus the mirrored half)
is written to ff_plan.json, which gen_layout.py reads.
"""
import itertools
import json
import os

XV, YV = 2.6, 191.88
Y0 = YV + 16.0
TAPS = [XV + 5.5 + 1.965 + 2.4 * i for i in range(7)]   # XSTAGE0 + PITCH*i + output column
Y_TAPV = YV + 5.985
SLOTS = [1.38 + 2.76 * j for j in range(8)]
TRK = [YV + 10.4 + 0.8 * t for t in range(7)]
QBUS_Y = [219.4 + 0.6 * j for j in range(7)]
KS = [0] + list(range(2, 12))          # row offset in sites
XCOL = (1.10, 1.94)                    # the two X li columns of buf_4
SP = {"met2": 0.14, "met3": 0.30}
MAXW = 26.5


def rows_for(ks, short_row, buf_first, xcols):
    rows, dff = [], 0
    for r in range(4):
        yb = Y0 + 2.72 * r
        flip = r % 2 == 1
        fy = (lambda y, yb=yb: yb + 2.72 - y) if flip else (lambda y, yb=yb: yb + y)
        if r == short_row:
            members = ["buf", "6"] if buf_first else ["6", "buf"]
        else:
            members = [str(dff), str(dff + 1)]
            dff += 2
        x = 0.46 * ks[r]
        cells = []
        for m in members:
            x += 0.46
            if m == "buf":
                cells.append(dict(n=m, kind="buf", x=x, D=(x + 0.28, fy(1.195)),
                                  X=(x + 1.94, fy(2.15)), QI=None, C=None))
                x += 2.76
            else:
                xc = XCOL[xcols[int(m)]]
                cells.append(dict(n=m, kind="dff", x=x, D=(x + 1.51, fy(0.95)),
                                  QI=(x + 7.05, fy(2.05)),
                                  X=(x + 7.36 + xc, fy(2.15)),
                                  C=(x + 0.265, fy(1.30)), xcol=xcols[int(m)]))
                x += 10.12
        rows.append(dict(r=r, end=x + 0.46, cells=cells))
    return rows


def qtrack_map(rows):
    """Planar staircase: rightmost QI gets lowest QBUS_Y[0], leftmost gets QBUS_Y[6]."""
    qcells = sorted([c for row in rows for c in row["cells"] if c["QI"]],
                    key=lambda c: -c["QI"][0])
    return {c["n"]: idx for idx, c in enumerate(qcells)}


def rects(rows, slot, phase, trk):
    R = []

    def sq(l, n, x, y, s):
        R.append((l, n, x - s / 2, y - s / 2, x + s / 2, y + s / 2))

    def vw(l, n, x, y1, y2, w):
        R.append((l, n, x - w / 2, min(y1, y2), x + w / 2, max(y1, y2)))

    def hw(l, n, x1, x2, y, w):
        R.append((l, n, min(x1, x2), y - w / 2, max(x1, x2), y + w / 2))

    qtrack = qtrack_map(rows)
    cy_all = []
    for row in rows:
        cxs = []
        for c in row["cells"]:
            n = c["n"]
            xx, xy = c["X"]
            sq("met2", f"pin{n}", xx, xy, 0.42)
            s = SLOTS[slot[n]]
            hw("met3", f"pin{n}", min(xx, s) - 0.26, max(xx, s) + 0.26, xy, 0.52)
            if c["QI"]:
                qx, qy = c["QI"]
                qby = QBUS_Y[qtrack[n]]
                netq = f"qi{n}"
                sq("met2", netq, qx, qy, 0.38)
                vw("met2", netq, qx, qy, qby + 0.15, 0.30)
                hw("met2", netq, qx - 0.15, 26.5, qby, 0.30)
            dx, dy = c["D"]
            net = f"ph{phase[n]}"
            R.append(("met2", net, dx - 0.16, dy - 0.19, dx + 0.16, dy + 0.19))
            ty = TRK[trk[phase[n]]]
            vw("met2", net, dx, ty, dy, 0.30)
            sq("met2", net, dx, ty, 0.42)
            if c["C"]:
                cx, cy = c["C"]
                cxs.append(cx)
                cy_all.append(cy)
                sq("met2", "clk", cx, cy, 0.42)
        y = [c["C"][1] for c in row["cells"] if c["C"]][0]
        hw("met3", "clk", -0.25, max(cxs) + 0.25, y, 0.50)
        sq("met2", "clk", 0, y, 0.42)
    vw("met2", "clk", 0, min(cy_all), Y0 + 16.02, 0.30)
    for i, t in enumerate(TAPS):
        net = f"ph{i}"
        ty = TRK[trk[i]]
        sq("met2", net, t, Y_TAPV, 0.38)
        vw("met2", net, t, Y_TAPV, ty, 0.30)
        sq("met2", net, t, ty, 0.42)
        xs = [t] + [c["D"][0] for row in rows for c in row["cells"] if phase[c["n"]] == i]
        hw("met3", net, min(xs) - 0.25, max(xs) + 0.25, ty, 0.50)
    R += [(l, n if n == "clk" else "M" + n, -x2, y1, -x1, y2) for (l, n, x1, y1, x2, y2) in R]
    return R


def violations(R, stop=True):
    v = []
    for l, sp in SP.items():
        rs = sorted((r for r in R if r[0] == l), key=lambda r: r[2])
        for i, a in enumerate(rs):
            for b in rs[i + 1:]:
                if b[2] - a[4] >= sp:
                    break
                if a[1] == b[1]:
                    continue
                dx = max(a[2] - b[4], b[2] - a[4], 0)
                dy = max(a[3] - b[5], b[3] - a[5], 0)
                if dx < sp and dy < sp and (dx * dx + dy * dy) < sp * sp - 1e-9:
                    v.append((l, a, b))
                    if stop:
                        return v
    return v


def pre_ok(rows):
    """D risers go DOWN from row r; QI risers go UP from row r. Clear each other and pads."""
    dris = [(c["D"][0], r) for r, row in enumerate(rows) for c in row["cells"]]
    qris = [(c["QI"][0], r) for r, row in enumerate(rows) for c in row["cells"] if c["QI"]]
    for i, (x1, _) in enumerate(dris):
        for x2, _ in dris[i + 1:]:
            if abs(x1 - x2) < 0.56:
                return False
    for i, (x1, _) in enumerate(qris):
        for x2, _ in qris[i + 1:]:
            if abs(x1 - x2) < 0.56:
                return False
    for xd, rd in dris:
        for xq, rq in qris:
            if rq <= rd and abs(xd - xq) < 0.56:
                return False
    for x, r in dris:
        for row in rows[:r]:
            for c in row["cells"]:
                for key in ("C", "QI", "X"):
                    if c[key] and abs(c[key][0] - x) < 0.54:
                        return False
    for x, r in qris:
        for row in rows[r + 1:]:
            for c in row["cells"]:
                for key in ("C", "D", "X"):
                    if c[key] and abs(c[key][0] - x) < 0.54:
                        return False
    return True


def assign_slots(rows):
    cells = [c for row in rows for c in row["cells"]]
    dffs = [c for c in cells if c["kind"] == "dff"]
    best = None
    for p in itertools.permutations(range(1, 8)):
        slot = {"buf": 0}
        slot.update({c["n"]: p[k] for k, c in enumerate(dffs)})
        cost = sum(abs(SLOTS[slot[c["n"]]] - c["X"][0]) for c in cells)
        if best is not None and cost >= best[0]:
            continue
        ok = True
        for row in rows:
            iv = sorted((min(c["X"][0], SLOTS[slot[c["n"]]]) - 0.26,
                         max(c["X"][0], SLOTS[slot[c["n"]]]) + 0.26) for c in row["cells"])
            if any(b[0] - a[1] < 0.34 for a, b in zip(iv, iv[1:])):
                ok = False
                break
        if ok:
            best = (cost, slot)
    return best


def placements():
    for short_row in range(4):
        for bf in (True, False):
            for ks in itertools.product(KS, KS, KS, KS):
                if max(ks) > 11 and min(ks) > 6:
                    continue
                rows0 = rows_for(ks, short_row, bf, [1] * 7)
                if max(r["end"] for r in rows0) > MAXW:
                    continue
                dris = [(c["D"][0], r) for r, row in enumerate(rows0) for c in row["cells"]]
                qris = [(c["QI"][0], r) for r, row in enumerate(rows0) for c in row["cells"] if c["QI"]]
                xcols = []
                for d in range(7):
                    r_d, c_d = [(r, c) for r, row in enumerate(rows0) for c in row["cells"] if c["n"] == str(d)][0]
                    x_cell = c_d["x"]
                    good = [q for q in (1, 0)
                            if all(abs(x_cell + 7.36 + XCOL[q] - x) >= 0.54 for x, rr in dris if rr > r_d)
                            and all(abs(x_cell + 7.36 + XCOL[q] - x) >= 0.54 for x, rr in qris if rr < r_d)]
                    xcols.append(good[0] if good else 1)
                rows = rows_for(ks, short_row, bf, xcols)
                if pre_ok(rows):
                    yield ks, short_row, bf, xcols, rows


def main():
    cands = []
    for ks, short_row, bf, xcols, rows in placements():
        b = assign_slots(rows)
        if b:
            cands.append((b[0], ks, short_row, bf, xcols, b[1]))
    cands.sort(key=lambda c: c[0])
    print("placements passing pre-checks:", len(cands))
    for cost, ks, short_row, bf, xcols, slot in cands[:400]:
        rows = rows_for(ks, short_row, bf, xcols)
        cells = [c for row in rows for c in row["cells"]]
        dffs = [c for c in cells if c["kind"] == "dff"]
        buf = [c for c in cells if c["kind"] == "buf"][0]
        perms = sorted(itertools.permutations(range(7)),
                       key=lambda p: sum(abs(TAPS[p[k]] - c["D"][0]) for k, c in enumerate(dffs)))[:150]
        best = None
        for perm in perms:
            phase = {c["n"]: perm[k] for k, c in enumerate(dffs)}
            dx_of = {perm[k]: c["D"][0] for k, c in enumerate(dffs)}
            rl = sum(abs(TAPS[i] - dx_of[i]) for i in range(7))
            for pb in sorted(range(7), key=lambda i: abs(TAPS[i] - buf["D"][0])):
                ph = dict(phase)
                ph["buf"] = pb
                keys = [lambda i: TAPS[i], lambda i: -TAPS[i], lambda i: dx_of[i], lambda i: -dx_of[i],
                        lambda i: abs(TAPS[i] - dx_of[i]), lambda i: -abs(TAPS[i] - dx_of[i]),
                        lambda i: TAPS[i] - dx_of[i], lambda i: dx_of[i] - TAPS[i]]
                for kf in keys:
                    order = sorted(range(7), key=kf)
                    trk = {i: order.index(i) for i in range(7)}
                    if not violations(rects(rows, slot, ph, trk)):
                        best = (rl + abs(TAPS[pb] - buf["D"][0]), ph, trk)
                        break
                if best:
                    break
            if best:
                break
        if best:
            qtrack = qtrack_map(rows)
            out = dict(ks=list(ks), short_row=short_row, buf_first=bf, xcol=xcols, slot=slot,
                       phase=best[1], trk={str(k): v for k, v in best[2].items()},
                       qtrack=qtrack, jog_cost=round(cost, 3), riser_cost=round(best[0], 3),
                       width=round(max(r["end"] for r in rows), 3), XV=XV, YV=YV, Y0=Y0)
            print(json.dumps(out))
            json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ff_plan.json"), "w"),
                      indent=1)
            return
    print("no solution")


if __name__ == "__main__":
    main()
