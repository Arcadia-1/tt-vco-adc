set pdk $::env(PDK_ROOT)/sky130A
set c1 [readnet spice tt_um_arcadia1_vco_adc_lvs.spice]
set c2 [readnet spice /w/proj/verify/vco_core_lvs.spice]
readnet spice $pdk/libs.ref/sky130_fd_sc_hd/spice/sky130_fd_sc_hd.spice $c2
readnet spice /w/proj/verify/so_lvs.spice $c2
readnet verilog lvs_ref.v $c2
lvs "$c1 tt_um_arcadia1_vco_adc" "$c2 tt_um_arcadia1_vco_adc" $pdk/libs.tech/netgen/sky130A_setup.tcl lvs_report.txt -json
quit
