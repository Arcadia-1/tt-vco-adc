
.subckt ota5t inp inn out vbn vdd gnd
XM1 x inp t gnd sky130_fd_pr__nfet_01v8 l=1 w=4 nf=2
XM2 out inn t gnd sky130_fd_pr__nfet_01v8 l=1 w=4 nf=2
XM3 x x vdd vdd sky130_fd_pr__pfet_01v8 l=1 w=4 nf=2
XM4 out x vdd vdd sky130_fd_pr__pfet_01v8 l=1 w=4 nf=2
XM5 t vbn gnd gnd sky130_fd_pr__nfet_01v8 l=2 w=2 nf=2
.ends ota5t

.subckt so_loop vin vctrl b0 b1 b2 b3 b4 b5 b6 vref vbn rst vdd gnd
Rd0 b0 vg 1.04Meg
Rd1 b1 vg 1.04Meg
Rd2 b2 vg 1.04Meg
Rd3 b3 vg 1.04Meg
Rd4 b4 vg 1.04Meg
Rd5 b5 vg 1.04Meg
Rd6 b6 vg 1.04Meg
Rin vin vg 49.2k
XC0 vg vctrl sky130_fd_pr__cap_mim_m3_1 w=24 l=25
XC1 vg vctrl sky130_fd_pr__cap_mim_m3_1 w=24 l=25
XMr vg rst vctrl gnd sky130_fd_pr__nfet_01v8 l=0.15 w=0.42
XOTA vref vg vctrl vbn vdd gnd ota5t
.ends so_loop
