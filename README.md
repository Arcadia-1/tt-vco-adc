![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg)

# Second-order VCO Delta-Sigma ADC (Tiny Tapeout SKY26e, sky130A, 1x2 analog tile)

Two mirror-image second-order closed-loop VCO delta-sigma ADC halves. In each half, VINP (`ua[0]`) or VINN (`ua[1]`) drives a resistor into an OTA-C integrator, whose output tunes a 7-stage current-starved ring oscillator; the sampled ring phases (P half on `uo_out`, N half on `uio`, one unsampled monitor each) are XORed with the previous sample on chip and fed back through a 7-element resistor DAC. The integrator plus the VCO phase give second-order noise shaping, and the loop suppresses the VCO nonlinearity. Off-chip, each half's code is the popcount of successive phase-word XORs and the ADC output is N minus P. The first-order open-loop version is tagged `v1.0-pseudodiff`.

| Path | Content |
|---|---|
| `docs/info.md` | datasheet: how it works, how to test |
| `VERIFICATION.md` | sign-off record: precheck, DRC, LVS, pre- and post-layout simulation |
| `gds/`, `lef/`, `mag/` | final layout (generated) |
| `layout/gen_layout.py`, `layout/flow.sh` | layout generator and build/DRC/LVS flow (Magic, netgen) |
| `layout/plan_ff.py`, `layout/ff_plan.json` | placement search for the flip-flop block (no spacing conflicts, each output straight to its pin) |
| `netlist/vco_core.spice`, `netlist/so_core.spice` | parametrized VCO and loop (OTA, DAC, bias) netlists used for sizing |
| `layout/devlib.py` | hand-drawn device primitives and the OTA layout |
| `verify/` | LVS reference netlists, extracted RC netlist, precheck / LVS reports |
| `sim/` | corner sweep (`fsweep.py`), full-tile transients with DSP (`so_tran.py` for the second-order loop, `adc_tran.py` for v1) |
| `model/` | behavioral models (`so_model.py` for the second-order loop; first-order models) |
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
