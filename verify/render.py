# klayout -zz -r render.py -rd gds=in.gds -rd png=out.png -rd lyp=layers.lyp [-rd box=x1,y1,x2,y2] [-rd w=1600]
import pya
lv = pya.LayoutView()
lv.load_layout(gds, 0)
try:
    lv.load_layer_props(lyp)
except Exception:
    pass
lv.max_hier()
lv.set_config("background-color", "#ffffff")
lv.set_config("grid-visible", "false")
if "box" in globals() and box:
    b = [float(v) for v in box.split(",")]
    lv.zoom_box(pya.DBox(b[0], b[1], b[2], b[3]))
else:
    lv.zoom_fit()
W = int(globals().get("w", 1600))
bb = lv.box()
H = int(W * bb.height() / bb.width())
lv.save_image(png, W, H)
print("saved", png, W, H)
