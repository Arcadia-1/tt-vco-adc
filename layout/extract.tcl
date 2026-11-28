# extract tt_um_arcadia1_vco_adc from the written GDS for LVS / PEX
# env: MODE = lvs | pex
gds flatglob *__example_*
gds read ../gds/tt_um_arcadia1_vco_adc.gds
load tt_um_arcadia1_vco_adc
select top cell
if {$::env(MODE) eq "pex"} {
  flatten tt_um_arcadia1_vco_adc_flat
  load tt_um_arcadia1_vco_adc_flat
  cellname delete tt_um_arcadia1_vco_adc
  cellname rename tt_um_arcadia1_vco_adc_flat tt_um_arcadia1_vco_adc
  select top cell
  extract do resistance
  extract all
  ext2sim labels on
  ext2sim
  extresist tolerance 10
  extresist all
  ext2spice lvs
  ext2spice cthresh 0.01
  ext2spice extresist on
  ext2spice -o tt_um_arcadia1_vco_adc_pex.spice
} elseif {$::env(MODE) eq "pexc"} {
  # Flat C-only post-layout netlist: flattening before extract eliminates hierarchical negative
  # adjustment caps and unexported cross-hierarchy coupling nodes in magic 8.3.685.
  flatten tt_um_arcadia1_vco_adc_flat
  load tt_um_arcadia1_vco_adc_flat
  cellname delete tt_um_arcadia1_vco_adc
  cellname rename tt_um_arcadia1_vco_adc_flat tt_um_arcadia1_vco_adc
  select top cell
  extract all
  ext2spice lvs
  ext2spice cthresh 0.01
  ext2spice -o tt_um_arcadia1_vco_adc_pex.spice
} else {
  extract all
  ext2spice lvs
  ext2spice -o tt_um_arcadia1_vco_adc_lvs.spice
}
quit -noprompt
