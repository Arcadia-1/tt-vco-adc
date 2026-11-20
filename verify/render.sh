#!/bin/bash
# usage (inside the precheck image, cwd = run dir): render.sh <gds>
L=/w/pdk/sky130A/libs.tech/klayout/tech/sky130A.lyp
klayout -zz -r /w/proj/verify/render.py -rd gds=$1 -rd png=full.png -rd lyp=$L -rd w=1400
klayout -zz -r /w/proj/verify/render.py -rd gds=$1 -rd png=core.png -rd lyp=$L -rd box=${BOX:-0,62,148,226} -rd w=2400
