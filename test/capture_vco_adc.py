# MicroPython capture script for the Tiny Tapeout demo board (DB v3, RP2350B).
#
# Takes over the project clock pin with a PIO state machine that produces
# clk = fs and samples uio[7:0] (N half) and uo_out[7:0] (P half), 16 contiguous
# GPIOs 25..40, once per clock period (half a period after
# the rising edge, when the flip-flop outputs are settled). Samples are moved
# into RAM with DMA, no gaps, then written to flash as raw bytes.
#
#   mpremote run capture_vco_adc.py        (or copy to the board and import)
#   mpremote cp :vco_adc.bin .             then: python3 decode_vco_adc.py vco_adc.bin
#
# NOT TESTED ON HARDWARE. Pin numbers follow ttboard/pins/gpio_map_dbv3.py
# (RP_PROJCLK = 16, UIO0..7 = 25..32, UO_OUT0..7 = 33..40). Check them against your
# SDK version. GPIOs above 31 need the RP2350B PIO GPIO window (base 16); recent
# MicroPython sets it from the pins given to StateMachine.

import array
import machine
import rp2
from ttboard.demoboard import DemoBoard

SYS_HZ = 150_000_000
CYCLES = 15              # PIO cycles per sample: fs = SYS_HZ / CYCLES = 10 MHz
NSAMP = 65536            # samples to capture (2 per 32-bit word, 16 bits each)
CLK_PIN = 16
UIO0_PIN = 25

tt = DemoBoard.get()
tt.shuttle.tt_um_arcadia1_vco_adc.enable()
tt.clock_project_stop()          # release the clock pin from the SDK PWM
tt.reset_project(False)          # the design has no reset, keep rst_n high
for p in range(UIO0_PIN, UIO0_PIN + 8):   # the chip drives uio, the RP2350 must only read
    machine.Pin(p, machine.Pin.IN)
machine.freq(SYS_HZ)


@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW, in_shiftdir=rp2.PIO.SHIFT_LEFT,
             autopush=True, push_thresh=32, fifo_join=rp2.PIO.JOIN_RX)
def vco_cap():
    wrap_target()
    nop()            .side(1) [6]     # clk high for 7 cycles
    in_(pins, 16)    .side(0) [7]     # sample uio + uo_out, clk low for 8 cycles
    wrap()


sm = rp2.StateMachine(0, vco_cap, freq=SYS_HZ,
                      sideset_base=machine.Pin(CLK_PIN),
                      in_base=machine.Pin(UIO0_PIN))
buf = array.array('I', bytes(2 * NSAMP))  # 2*NSAMP bytes = NSAMP/2 words
dma = rp2.DMA()
ctrl = dma.pack_ctrl(size=2, inc_read=False, inc_write=True, treq_sel=4)  # DREQ_PIO0_RX0
dma.config(read=sm, write=buf, count=len(buf), ctrl=ctrl, trigger=True)
sm.active(1)
while dma.active():
    pass
sm.active(0)
dma.close()

with open('vco_adc.bin', 'wb') as f:
    f.write(buf)
print('captured', NSAMP, 'samples at', SYS_HZ // CYCLES, 'Hz into vco_adc.bin')
