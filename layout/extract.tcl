# extract tt_um_arcadia1_vco_adc from the written GDS for LVS / PEX
# env: MODE = lvs | pex
gds flatglob *__example_*
gds read ../gds/tt_um_arcadia1_vco_adc.gds
load tt_um_arcadia1_vco_adc
select top cell
if {$::env(MODE) eq "pex"} {
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
  # C-only post-layout netlist: the decap field makes a full R extraction (50k resistors) too slow
  # to simulate, and the signal routes are short (< 40 um met2/met3), so their R is negligible
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
