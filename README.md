![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg)

# Second-order VCO Delta-Sigma ADC (Tiny Tapeout SKY26e, sky130A, 1x2 analog tile)

**Author:** Zhishuai Zhang · **Live Showcase & Interactive 3D GDS Viewer:** [vco-dsm.tokenzhang.com](https://vco-dsm.tokenzhang.com/) · **HTML Technical Report:** [report.html](https://vco-dsm.tokenzhang.com/report.html) · **IEEE PDF:** [vco_adc_report.pdf](report/vco_adc_report.pdf) · **Live Schematic:** [Analog Canvas](https://analog-canvas.tokenzhang.com/g/xjr6hy5ce5)

Two mirror-image second-order closed-loop VCO delta-sigma ADC halves. In each half, VINP (`ua[0]`) or VINN (`ua[1]`) drives a resistor into a common-centroid low-1/f 5T OTA-C integrator (with a zero-static-power 5-FET Miller-compensated brick-wall active clamp `CLAMP_A5`), whose output tunes a 7-stage current-starved ring oscillator; the sampled ring phases (P half on `uo_out`, N half on `uio`, isolated via dedicated `buf_4` pin buffers, one unsampled monitor each) are XORed with the previous sample on chip and fed back through a 7-element resistor DAC. The integrator plus the VCO phase give second-order noise shaping, and the loop suppresses the VCO nonlinearity. Off-chip, each half's code is the popcount of successive phase-word XORs and the ADC output is N minus P.

| Path | Content |
|---|---|
| `site/` | static showcase website (`index.html`: interactive WebGL 3D/2D real-GDS viewer + functional block highlighting + live charts; `report.html`: Distill-style web technical report) |
| `report/vco_adc_report.pdf` | 6-page IEEE two-column technical sign-off report (`vco_adc_report.tex`, `gen_figures.py`) |
| `docs/info.md` | datasheet: how it works, how to test |
| `VERIFICATION.md` | sign-off record: precheck, DRC, LVS, pre- and post-layout simulation |
| `gds/`, `lef/`, `mag/` | final layout (generated) |
| `layout/gen_layout.py`, `layout/devlib.py`, `layout/flow.sh` | layout generator, hand-drawn device primitives and OTA, build/DRC/LVS flow (Magic, netgen) |
| `layout/plan_ff.py`, `layout/ff_plan.json` | placement search for the flip-flop block (no spacing conflicts, each output straight to its pin) |
| `netlist/vco_core.spice`, `netlist/so_core.spice` | parametrized VCO and loop (OTA, DAC, bias) netlists used for sizing |
| `verify/` | LVS reference netlists, extracted RC netlist, precheck / LVS reports |
| `sim/` | VCO tuning sweeps (`fsweep.py`, `vco_lin.py`) and the full-tile transient with DSP (`so_tran.py`, schematic or extracted layout) |
| `model/` | behavioral model of the second-order loop (`so_model.py`, uses the ring decoder in `vco_adc_model.py`) |
| `test/` | RP2350 capture script and decoder for the real chip |

## Tiny Tapeout Analog Project Template (original notes)

- [Read the documentation for project](docs/info.md)

## What is Tiny Tapeout?

Tiny Tapeout is an educational project that aims to make it easier and cheaper than ever to get your digital designs manufactured on a real chip.

To learn more and get started, visit https://tinytapeout.com.

## Analog projects

For specifications and instructions, see the [analog specs page](https://tinytapeout.com/specs/analog/).

## Enable GitHub actions to build the results page

- [Enabling GitHub Pages](https://tinytapeout.com/faq/#my-github-action-is-failing-on-the-pages-part)

## Resources

- [FAQ](https://tinytapeout.com/faq/)
- [Digital design lessons](https://tinytapeout.com/digital_design/)
- [Learn how semiconductors work](https://tinytapeout.com/siliwiz/)
- [Join the community](https://tinytapeout.com/discord)

## What next?

- [Submit your design to the next shuttle](https://app.tinytapeout.com/).
- Edit [this README](README.md) and explain your design, how it works, and how to test it.
- Share your project on your social network of choice:
  - LinkedIn [#tinytapeout](https://www.linkedin.com/search/results/content/?keywords=%23tinytapeout) [@TinyTapeout](https://www.linkedin.com/company/100708654/)
  - Mastodon [#tinytapeout](https://chaos.social/tags/tinytapeout) [@matthewvenn](https://chaos.social/@matthewvenn)
  - X (formerly Twitter) [#tinytapeout](https://twitter.com/hashtag/tinytapeout) [@tinytapeout](https://twitter.com/tinytapeout)
  - Bluesky [@tinytapeout.com](https://bsky.app/profile/tinytapeout.com)
