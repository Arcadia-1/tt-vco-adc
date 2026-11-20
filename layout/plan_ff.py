"""Placement search for the flip-flop block of one half (local x = distance from the axis).

Four abutting rows above the VCO: three rows hold two dfxtp_4 each, one row holds dff6 and the
monitor buf_4. Row offsets are whole placement sites (0.46 um), otherwise the rail contacts of
two rows sharing a rail collide (mcon.2); one site is excluded because the n-wells of the two
mirrored halves would sit 0.54 um apart. Every Q drops on its own top pin through a short met3
jog (slot j at x = 1.38 + 2.76 j, slot 0 = monitor buffer); every D is fed by a met2 riser from a
met3 phase track between the VCO and the block. A dff Q may use either of its two li columns.

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
KS = [0] + list(range(2, 11))          # row offset in sites
QCOL = (7.155, 8.005)                  # the two Q li columns of dfxtp_4
SP = {"met2": 0.14, "met3": 0.3}
MAXW = 25.0


def rows_for(ks, short_row, buf_first, qcols):
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
                cells.append(dict(n=m, kind="buf", D=(x + 0.28, fy(1.195)), Q=(x + 1.94, fy(2.15)), C=None))
                x += 2.76
            else:
                cells.append(dict(n=m, kind="dff", D=(x + 1.58, fy(1.36)), Q=(x + QCOL[qcols[int(m)]], fy(2.15)),
                                  C=(x + 0.265, fy(1.3)), qcol=qcols[int(m)]))
                x += 8.74
        rows.append(dict(r=r, end=x + 0.46, cells=cells))
    return rows


def rects(rows, slot, phase, trk):
    R = []

    def sq(l, n, x, y, s):
        R.append((l, n, x - s / 2, y - s / 2, x + s / 2, y + s / 2))

    def vw(l, n, x, y1, y2, w):
        R.append((l, n, x - w / 2, min(y1, y2), x + w / 2, max(y1, y2)))

    def hw(l, n, x1, x2, y, w):
        R.append((l, n, min(x1, x2), y - w / 2, max(x1, x2), y + w / 2))

    cy_all = []
    for row in rows:
        cxs = []
        for c in row["cells"]:
            n = c["n"]
            qx, qy = c["Q"]
            sq("met2", f"q{n}", qx, qy, 0.42)
            s = SLOTS[slot[n]]
            hw("met3", f"q{n}", min(qx, s) - 0.26, max(qx, s) + 0.26, qy, 0.52)
            dx, dy = c["D"]
            net = f"ph{phase[n]}"
            R.append(("met2", net, dx - 0.16, dy - 0.19, dx + 0.16, dy + 0.19))
            ty = TRK[trk[phase[n]]]
            vw("met2", net, dx, ty, dy, 0.3); sq("met2", net, dx, ty, 0.42)
            if c["C"]:
                x, y = c["C"]
                cxs.append(x); cy_all.append(y)
                sq("met2", "clk", x, y, 0.42)
        y = [c["C"][1] for c in row["cells"] if c["C"]][0]
        hw("met3", "clk", -0.25, max(cxs) + 0.25, y, 0.5); sq("met2", "clk", 0, y, 0.42)
    vw("met2", "clk", 0, min(cy_all), Y0 + 13.6, 0.3)
    for i, t in enumerate(TAPS):
        net = f"ph{i}"
        ty = TRK[trk[i]]
        sq("met2", net, t, Y_TAPV, 0.38)
        vw("met2", net, t, Y_TAPV, ty, 0.3); sq("met2", net, t, ty, 0.42)
        xs = [t] + [c["D"][0] for row in rows for c in row["cells"] if phase[c["n"]] == i]
        hw("met3", net, min(xs) - 0.25, max(xs) + 0.25, ty, 0.5)
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
    """risers must clear each other and every met2 pad of the rows below their own."""
    ris = [(c["D"][0], r) for r, row in enumerate(rows) for c in row["cells"]]
    xs = sorted(x for x, _ in ris)
    if any(b - a < 0.56 for a, b in zip(xs, xs[1:])):
        return False
    for x, r in ris:
        for row in rows[:r]:
            for c in row["cells"]:
                for key in ("C", "Q"):
                    if c[key] and abs(c[key][0] - x) < 0.5:
                        return False
    return True


def assign_slots(rows):
    cells = [c for row in rows for c in row["cells"]]
    dffs = [c for c in cells if c["kind"] == "dff"]
    best = None
    for p in itertools.permutations(range(1, 8)):
        slot = {"buf": 0}
        slot.update({c["n"]: p[k] for k, c in enumerate(dffs)})
        cost = sum(abs(SLOTS[slot[c["n"]]] - c["Q"][0]) for c in cells)
        if best is not None and cost >= best[0]:
            continue
        ok = True
        for row in rows:
            iv = sorted((min(c["Q"][0], SLOTS[slot[c["n"]]]) - 0.26,
                         max(c["Q"][0], SLOTS[slot[c["n"]]]) + 0.26) for c in row["cells"])
            if any(b[0] - a[1] < 0.3 for a, b in zip(iv, iv[1:])):
                ok = False
        if ok:
            best = (cost, slot)
    return best


def placements():
    for short_row in range(4):
        for bf in (True, False):
            for ks in itertools.product([0], KS, KS, KS):
                rows0 = rows_for(ks, short_row, bf, [1] * 7)
                if max(r["end"] for r in rows0) > MAXW:
                    continue
                ris = [(c["D"][0], r) for r, row in enumerate(rows0) for c in row["cells"]]
                qcols = []
                for d in range(7):
                    r_d, c_d = [(r, c) for r, row in enumerate(rows0) for c in row["cells"] if c["n"] == str(d)][0]
                    x_cell = c_d["D"][0] - 1.58
                    good = [q for q in (1, 0) if all(abs(x_cell + QCOL[q] - x) >= 0.5 for x, rr in ris if rr > r_d)]
                    qcols.append(good[0] if good else 1)
                rows = rows_for(ks, short_row, bf, qcols)
                if pre_ok(rows):
                    yield ks, short_row, bf, qcols, rows


def main():
    cands = []
    for ks, short_row, bf, qcols, rows in placements():
        b = assign_slots(rows)
        if b:
            cands.append((b[0], ks, short_row, bf, qcols, b[1]))
    cands.sort(key=lambda c: c[0])
    print("placements passing pre-checks:", len(cands))
    for cost, ks, short_row, bf, qcols, slot in cands[:400]:
        rows = rows_for(ks, short_row, bf, qcols)
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
                ph = dict(phase); ph["buf"] = pb
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
            out = dict(ks=ks, short_row=short_row, buf_first=bf, qcol=qcols, slot=slot, phase=best[1],
                       trk={str(k): v for k, v in best[2].items()}, jog_cost=round(cost, 3),
                       riser_cost=round(best[0], 3), width=max(r["end"] for r in rows), XV=XV, YV=YV, Y0=Y0)
            print(json.dumps(out))
            json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ff_plan.json"), "w"),
                      indent=1)
            return
    print("no solution")


if __name__ == "__main__":
    main()
