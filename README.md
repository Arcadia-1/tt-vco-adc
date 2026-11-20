![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg)

# Pseudo-differential VCO Delta-Sigma ADC (Tiny Tapeout SKY26e, sky130A, 1x2 analog tile)

Two mirror-image ring-VCO delta-sigma ADC halves. VINP (`ua[0]`) and VINN (`ua[1]`) each set the current of a 7-stage current-starved ring oscillator; 7 flip-flops per half sample the ring phases at `clk` (P half on `uo_out`, N half on `uio`, one unsampled monitor each). Off-chip, each half's code is the popcount of successive phase-word XORs and the ADC output is P minus N, which cancels the even-order distortion of the single-ended VCOs.

| Path | Content |
|---|---|
| `docs/info.md` | datasheet: how it works, how to test |
| `VERIFICATION.md` | sign-off record: precheck, DRC, LVS, pre- and post-layout simulation |
| `gds/`, `lef/`, `mag/` | final layout (generated) |
| `layout/gen_layout.py`, `layout/flow.sh` | layout generator and build/DRC/LVS flow (Magic, netgen) |
| `layout/plan_ff.py`, `layout/ff_plan.json` | placement search for the flip-flop block (no spacing conflicts, each output straight to its pin) |
| `netlist/vco_core.spice` | parametrized VCO netlist used for sizing |
| `verify/` | LVS reference netlists, extracted RC netlist, precheck / LVS reports |
| `sim/` | corner sweep (`fsweep.py`) and full-tile transient with DSP (`adc_tran.py`) |
| `model/` | behavioral models (single-ended and pseudo-differential with mismatch) |
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
