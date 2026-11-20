#!/bin/bash
# full layout flow on the server: generate -> half cell -> top + GDS/LEF -> magic DRC -> extract -> LVS
# usage: flow.sh <rundir>
set -e
R=~/tt-vco-adc/$1; mkdir -p $R/mag $R/ext ~/tt-vco-adc/tt-def
cp ~/tt-vco-adc/tt-support-tools/tech/sky130A/def/analog/tt_analog_1x2.def ~/tt-vco-adc/tt-def/
cd ~/tt-vco-adc/proj/layout && python3 gen_layout.py /w/tt-def/tt_analog_1x2.def $R
cat >> $R/top.tcl <<'TCL'
load tt_um_arcadia1_vco_adc
select top cell
file mkdir ../gds ../lef
gds write ../gds/tt_um_arcadia1_vco_adc.gds
lef write ../lef/tt_um_arcadia1_vco_adc.lef -hide -pinonly
quit -noprompt
TCL
RUN="podman run --rm -v $HOME/tt-vco-adc:/w:z -e PDK_ROOT=/w/pdk -e PDK=sky130A --entrypoint bash localhost/ldo-layout:dev -lc"
M="magic -dnull -noconsole -rcfile /w/pdk/sky130A/libs.tech/magic/sky130A.magicrc"
$RUN "cd /w/$1/mag && $M ../half.tcl > ../half.log 2>&1 && $M ../top.tcl > ../top.log 2>&1"
grep -E "RBOX|rror" $R/half.log $R/top.log | head -20
$RUN "cd /w/$1/mag && $M /w/tt-support-tools/precheck/magic_drc.tcl ../gds/tt_um_arcadia1_vco_adc.gds tt_um_arcadia1_vco_adc /w/pdk/sky130A ../magic_drc.txt ../magic_drc.mag > ../drc.log 2>&1; grep COUNT ../magic_drc.txt"
cp $R/lvs_ref.v $R/ext/
RUNX="podman run --rm -v $HOME/tt-vco-adc:/w:z -e PDK_ROOT=/w/pdk -e PDK=sky130A --entrypoint bash localhost/tt-precheck:sky26b -lc"
$RUNX "cd /w/$1/ext && MODE=lvs $M /w/proj/layout/extract.tcl > extract.log 2>&1"
$RUN "cd /w/$1/ext && netgen-lvs -batch source /w/proj/layout/lvs.tcl > lvs.log 2>&1; grep -E 'Netlists match|do not match|roperty errors' lvs_report.txt | sort | uniq -c"
