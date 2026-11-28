import sys, json, gdstk
gds, out = sys.argv[1], sys.argv[2]
VIAS = [('licon','66/44',66,44),('mcon','67/44',67,44),('via','68/44',68,44),('via2','69/44',69,44),('via3','70/44',70,44)]
def boxes(keep_decap):
    lib = gdstk.read_gds(gds)
    for c in lib.cells:
        isd = 'decap' in c.name
        if isd != keep_decap:
            c.remove(*c.polygons); c.remove(*c.paths)
    top = [c for c in lib.top_level() if c.name.startswith('tt_um')][0]
    res = {}
    for key, _, l, d in VIAS:
        s = set()
        for p in top.get_polygons(layer=l, datatype=d):
            (x0, y0), (x1, y1) = p.bounding_box()
            s.add((round(x0*100), round(y0*100), round(x1*100), round(y1*100)))
        res[key] = sorted(s)
    return res
core, dec = boxes(False), boxes(True)
data = json.load(open(out))
data['vias'] = []
for key, g, _, _ in VIAS:
    print(key, len(core[key]), len(dec[key]))
    data['vias'].append({'key': key, 'gds': g, 'core': [v for b in core[key] for v in b], 'decap': [v for b in dec[key] for v in b]})
json.dump(data, open(out, 'w'), separators=(',', ':'))
