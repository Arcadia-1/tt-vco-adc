"""Generate publication-grade IEEE vector PDF figures for tt_um_arcadia1_vco_adc report.
All curves are 100% real BSIM4 / SKY130 simulation data from:
  - report/data/report_sim_data.json (exact TT OP, Tian stability, BSIM4 .noise, CLAMP_A5 I-V,
    VCO tuning, no-reset/overload waveforms, and full-transistor dig=0 isolation)
  - report/data/p2/*_y.npy (true in-band 14.65 kHz A/B transient spectra)
  - report/data/p3/*_y.npy (21-corner PVT + R/C + VDD +/-10% transient spectra)
  - report/data/p4/mc_s*_y.npy (16-seed tt_mm mismatch Monte Carlo transient spectra)
  - docs/img/core_layout.jpg (annotated layout floorplan)
"""
import glob, json, math, os
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
FIG_DIR = os.path.join(HERE, "figs")
LAYOUT_IMG = os.path.abspath(os.path.join(HERE, "..", "docs", "img", "core_layout.jpg"))
os.makedirs(FIG_DIR, exist_ok=True)

# IEEE publication styling
mpl.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "Nimbus Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "font.size": 8.0,
    "axes.titlesize": 8.5,
    "axes.labelsize": 8.0,
    "xtick.labelsize": 7.2,
    "ytick.labelsize": 7.2,
    "legend.fontsize": 6.8,
    "axes.linewidth": 0.65,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.minor.width": 0.45,
    "ytick.minor.width": 0.45,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.top": True,
    "ytick.right": True,
    "grid.color": "#CBD5E1",
    "grid.linewidth": 0.45,
    "grid.linestyle": "--",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.03,
})

# Refined IEEE color palette
C_NAVY   = "#0B3C5D"
C_TEAL   = "#147D64"
C_CRIM   = "#B91C1C"
C_AMBER  = "#D97706"
C_SLATE  = "#475569"
C_PURPLE = "#6D28D9"
C_DANGER = "#FEE2E2"
C_BAND   = "#DBEAFE"

with open(os.path.join(DATA_DIR, "report_sim_data.json")) as f:
    SIM = json.load(f)


def score_hann3(sig_y, fs=10e6, bins=3, bw=50e3):
    m = len(sig_y)
    win = np.hanning(m)
    spec = np.abs(np.fft.rfft((sig_y - sig_y.mean()) * win)) ** 2
    k = bins
    kb = int(round(bw / fs * m))
    grp = lambda c: spec[c - 1:c + 2].sum()
    sig = grp(k)
    band = spec[1:kb + 1].sum() - sig
    harm = sum(grp(h * k) for h in (2, 3) if h * k + 1 <= kb)
    noise_only = band - harm
    return dict(
        sndr=10 * np.log10(sig / band),
        snr=10 * np.log10(sig / noise_only) if noise_only > 0 else float("nan"),
        hd2=10 * np.log10(grp(2 * k) / sig),
        hd3=10 * np.log10(grp(3 * k) / sig),
        dc=float(sig_y.mean()),
    )


# ==============================================================================
# FIG. 2: TIAN STABILITY BODE & BSIM4 INPUT-REFERRED NOISE PSD
# ==============================================================================
def make_fig2():
    fig = plt.figure(figsize=(7.15, 2.55))
    gs = gridspec.GridSpec(2, 2, width_ratios=[1.05, 1.0], height_ratios=[1.0, 1.0],
                           wspace=0.28, hspace=0.10)
    ax_mag = fig.add_subplot(gs[0, 0])
    ax_ph  = fig.add_subplot(gs[1, 0], sharex=ax_mag)
    ax_nz  = fig.add_subplot(gs[:, 1])

    # Panel (a): Use exact Tian closed-loop integrator stability sweeps (stb_V2_A5_2x8_m4x3_*.dat)
    def load_tian(fname):
        d = np.loadtxt(os.path.join(DATA_DIR, "stb", fname))
        freq = d[:, 0]
        T = d[:, 1] + 1j * d[:, 3]
        mag = 20.0 * np.log10(np.maximum(np.abs(T), 1e-12))
        mb = (freq >= 10e3) & (freq <= 5e6)
        pk_i = np.where(mb)[0][np.argmax(mag[mb])]
        ph = np.unwrap(np.angle(T)) * 180.0 / np.pi
        ph = ph - 360.0 * np.round(ph[pk_i] / 360.0)
        # Keep phase monotonic around 0 deg at midband peak
        if ph[pk_i] > 90.0:
            ph -= 360.0
        elif ph[pk_i] < -90.0:
            ph += 360.0
        iu = np.where((mag[pk_i:-1] >= 0) & (mag[pk_i + 1:] < 0))[0]
        ug = pm = gm = float("nan")
        if len(iu):
            i = pk_i + iu[0]
            fr = (0.0 - mag[i]) / (mag[i + 1] - mag[i])
            ug = float(freq[i] * (freq[i + 1] / freq[i]) ** fr)
            pm = float(180.0 + (ph[i] + fr * (ph[i + 1] - ph[i])))
        ig = np.where((ph[pk_i:-1] >= -180.0) & (ph[pk_i + 1:] < -180.0))[0]
        if len(ig):
            j = pk_i + ig[0]
            fr = (-180.0 - ph[j]) / (ph[j + 1] - ph[j])
            gm = float(-(mag[j] + fr * (mag[j + 1] - mag[j])))
        return dict(freq=freq, mag_db=mag, phase_deg=ph, ug_hz=ug, pm_deg=pm, gm_db=gm)

    dtt  = load_tian("stb_V2_A5_2x8_m4x3_tt.dat")
    dss  = load_tian("stb_V2_A5_2x8_m4x3_ss_hh.dat")
    dff  = load_tian("stb_V2_A5_2x8_m4x3_ff_ll.dat")
    curves_stb = [
        (dtt,  "tt, 27°C, 1.80 V",     C_NAVY,  "-",  1.35),
        (dss,  "ss_hh, 85°C, 1.62 V",  C_TEAL,  "--", 1.10),
        (dff,  "ff_ll, -20°C, 1.98 V", C_CRIM,  "-.", 1.10),
    ]
    for d, lbl, col, ls, lw in curves_stb:
        f_mhz = d["freq"] / 1e6
        ax_mag.semilogx(f_mhz, d["mag_db"], color=col, ls=ls, lw=lw, label=lbl)
        ax_ph.semilogx(f_mhz, d["phase_deg"], color=col, ls=ls, lw=lw)

    ax_mag.axhline(0, color=C_SLATE, ls=":", lw=0.7)
    ax_ph.axhline(-180, color=C_SLATE, ls=":", lw=0.7)
    ax_mag.set_xlim(1e-2, 200)
    ax_mag.set_ylim(-25, 25)
    ax_ph.set_ylim(-215, 45)
    ax_ph.set_yticks([-180, -120, -60, 0])
    ax_mag.set_ylabel(r"$|T(f)|$ (dB)")
    ax_ph.set_ylabel(r"$\angle T(f)$ (deg)")
    ax_ph.set_xlabel("Frequency (MHz)")
    plt.setp(ax_mag.get_xticklabels(), visible=False)
    ax_mag.grid(True, which="major", alpha=0.6)
    ax_ph.grid(True, which="major", alpha=0.6)

    pm_min = min(dtt["pm_deg"], dss["pm_deg"], dff["pm_deg"])
    pm_max = max(dtt["pm_deg"], dss["pm_deg"], dff["pm_deg"])
    ug_tt = dtt["ug_hz"] / 1e6
    ax_mag.plot(ug_tt, 0, "o", color=C_NAVY, ms=3.5, zorder=5)
    ax_ph.plot(ug_tt, dtt["pm_deg"] - 180.0, "o", color=C_NAVY, ms=3.5, zorder=5)
    ax_ph.annotate(
        f"PM = {dtt['pm_deg']:.1f}°\n[{pm_min:.1f}°–{pm_max:.1f}°]\nGM = {dtt['gm_db']:.1f} dB",
        xy=(ug_tt, dtt["pm_deg"] - 180.0),
        xytext=(0.03, -155),
        fontsize=6.4,
        bbox=dict(boxstyle="round,pad=0.22", fc="white", ec=C_NAVY, lw=0.55, alpha=0.92),
        arrowprops=dict(arrowstyle="->", color=C_NAVY, lw=0.65, connectionstyle="arc3,rad=0.12"),
    )
    ax_mag.legend(loc="lower left", frameon=True, framealpha=0.92, edgecolor="#CBD5E1",
                  handlelength=1.7, borderpad=0.26, labelspacing=0.18, fontsize=6.1)
    ax_mag.set_title("(a) Tian Closed-Loop Integrator Stability", pad=4)

    # Panel (b): BSIM4 Input-Referred Noise PSD
    nz = SIM["noise"]
    curves_nz = [
        ("V2_NoClmp_tt",  f"tt, clamp removed ({nz['V2_NoClmp_tt']['dn50_uv']:.1f} µVrms, {nz['V2_NoClmp_tt']['snr50_tone_db']:.1f} dB)", C_SLATE, ":",  1.60),
        ("V2_A5_tt",      f"tt ({nz['V2_A5_tt']['dn50_uv']:.1f} µVrms, {nz['V2_A5_tt']['snr50_tone_db']:.1f} dB)", C_NAVY,  "-",  1.35),
        ("V2_A5_ss_hh",   f"ss_hh/85/1.62V ({nz['V2_A5_ss_hh']['snr50_tone_db']:.1f} dB)", C_TEAL,  "-.", 1.05),
        ("V2_A5_ff_ll",   f"ff_ll/-20/1.98V ({nz['V2_A5_ff_ll']['snr50_tone_db']:.1f} dB)", C_CRIM,  "-.", 0.95),
    ]
    ax_nz.axvspan(100, 50e3, color=C_BAND, alpha=0.32, lw=0)
    for key, lbl, col, ls, lw in curves_nz:
        d = nz[key]
        f = np.array(d["freq"])
        # Plot differential input-referred PSD = sqrt(2) * single-ended Vn (nV/sqrt(Hz))
        vn_diff_nv = np.array(d["vn_v_rthz"]) * math.sqrt(2.0) * 1e9
        ax_nz.loglog(f, vn_diff_nv, color=col, ls=ls, lw=lw, label=lbl)

    ax_nz.axvline(50e3, color=C_SLATE, ls=":", lw=0.75)
    ax_nz.text(44e3, 3.3e3, "BW = 50 kHz", ha="right", va="top", fontsize=6.4, color=C_SLATE)
    d_v2   = nz["V2_A5_tt"]["snr50_tone_db"]
    ax_nz.annotate(
        f"{nz['V2_A5_tt']['dn50_uv']:.1f} µVrms, {d_v2:.1f} dB SNR\n(0.00 dB clamp penalty)",
        xy=(1.0e3, 1.3e2), xytext=(3.0e3, 7.5e2),
        fontsize=6.5, fontweight="bold", color=C_NAVY,
        bbox=dict(boxstyle="round,pad=0.22", fc="white", ec=C_NAVY, lw=0.55, alpha=0.92),
        arrowprops=dict(arrowstyle="->", color=C_NAVY, lw=0.7),
    )
    ax_nz.set_xlim(10, 5e5)
    ax_nz.set_ylim(18, 5e3)
    ax_nz.set_xlabel("Frequency (Hz)")
    ax_nz.set_ylabel(r"Diff. Input Noise ($\mathrm{nV/\sqrt{Hz}}$)")
    ax_nz.grid(True, which="major", alpha=0.6)
    ax_nz.legend(loc="lower left", frameon=True, framealpha=0.93, edgecolor="#CBD5E1",
                 handlelength=1.5, borderpad=0.25, labelspacing=0.17, fontsize=5.8)
    ax_nz.set_title("(b) BSIM4 Input-Referred Noise PSD (1/f + Thermal)", pad=4)

    out_pdf = os.path.join(FIG_DIR, "fig2_stb_noise.pdf")
    fig.savefig(out_pdf)
    plt.close(fig)
    print("Saved", out_pdf)


# ==============================================================================
# FIG. 3: ANTI-LATCHUP CLAMP, STARTUP/OVERLOAD RECOVERY, & DIGITAL ISOLATION
# ==============================================================================
def make_fig3():
    fig = plt.figure(figsize=(7.15, 2.55))
    gs = gridspec.GridSpec(1, 3, width_ratios=[1.05, 1.05, 1.0], wspace=0.28)
    ax_vco = fig.add_subplot(gs[0, 0])
    ax_tr  = fig.add_subplot(gs[0, 1])
    ax_iso = fig.add_subplot(gs[0, 2])

    # Panel (a): VCO f(vctrl) + CLAMP_A5 clamped ceilings + inset I_clamp(vctrl)
    vt = SIM["clamp"]["vco_tune"]
    civ = SIM["clamp"]["clamp_iv"]
    ax_vco.axhspan(7.5, 11.5, color=C_DANGER, alpha=0.75, lw=0)
    ax_vco.axhline(7.5, color=C_CRIM, ls="--", lw=0.8)
    ax_vco.text(0.64, 10.65, r"Aliasing Latch-Up ($>0.75 f_s$)", fontsize=6.0, color=C_CRIM, fontweight="bold", va="top")
    ax_vco.axhline(2.5, color=C_SLATE, ls=":", lw=0.65)
    ax_vco.text(1.94, 2.72, r"$f_s/4$", fontsize=6.1, color=C_SLATE, ha="right")

    corners_vco = [
        ("fs_ll_27_1.98",  "fs_ll/1.98V",    C_CRIM,  "-"),
        ("ss_ll_85_1.98",  "ss_ll/85/1.98V", C_AMBER, "--"),
        ("tt_27_1.80",     "tt/27/1.80V",    C_NAVY,  "-"),
        ("ff_hh_-20_1.62", "ff_hh/-20/1.62V",C_TEAL,  "-."),
    ]
    for ck, lbl, col, ls in corners_vco:
        vc = np.array(vt[ck]["vctrl"])
        fm = np.array(vt[ck]["f_mhz"])
        ax_vco.plot(vc, fm, color=col, ls=ls, lw=1.1, label=lbl)
        if ck in civ["CLAMP_A5"]:
            vc_cl = civ["CLAMP_A5"][ck]["vctrl_clamped"]
            f_cl  = civ["CLAMP_A5"][ck]["f_clamped_mhz"]
            if not math.isnan(f_cl):
                ax_vco.plot(vc_cl, f_cl, "o", color=col, ms=4.2, mec="white", mew=0.6, zorder=6)

    ax_vco.annotate(
        "Clamp\nceiling",
        xy=(civ["CLAMP_A5"]["tt_27_1.80"]["vctrl_clamped"],
            civ["CLAMP_A5"]["tt_27_1.80"]["f_clamped_mhz"]),
        xytext=(1.50, 3.65),
        fontsize=5.9, color=C_NAVY, fontweight="bold", ha="center",
        bbox=dict(boxstyle="round,pad=0.16", fc="white", ec=C_NAVY, lw=0.5, alpha=0.92),
        arrowprops=dict(arrowstyle="->", color=C_NAVY, lw=0.65),
    )
    ax_vco.set_xlim(0.60, 1.98)
    ax_vco.set_ylim(0, 11.2)
    ax_vco.set_xlabel(r"$V_{\mathrm{ctrl}}$ (V)")
    ax_vco.set_ylabel(r"VCO Frequency $f_{\mathrm{VCO}}$ (MHz)")
    ax_vco.grid(True, alpha=0.55)
    ax_vco.legend(loc="lower right", frameon=True, framealpha=0.92, edgecolor="#CBD5E1",
                  fontsize=5.6, handlelength=1.35, borderpad=0.22, labelspacing=0.16)
    ax_vco.set_title("(a) VCO Tuning & Brick-Wall Ceiling", pad=4)

    # Inset in (a): clamp current vs control voltage (log scale), clean upper-left
    ax_in1 = ax_vco.inset_axes([0.16, 0.56, 0.34, 0.27])
    for cname, col, ls, lbl in [
        ("CLAMP_A5", C_NAVY,  "-",  "Clamp"),
    ]:
        d = civ[cname]["tt_27_1.80"]
        vc = np.array(d["vctrl"])
        ic = np.maximum(np.array(d["i_clamp_a"]), 1e-11) * 1e6
        ax_in1.semilogy(vc, ic, color=col, ls=ls, lw=0.95, label=lbl)
    ax_in1.axvline(1.15, color=C_SLATE, ls=":", lw=0.55)
    ax_in1.set_xlim(0.88, 1.48)
    ax_in1.set_ylim(1e-3, 1e2)
    ax_in1.set_yticks([1e-2, 1e0, 1e2])
    ax_in1.tick_params(labelsize=4.9, pad=1.0)
    ax_in1.set_ylabel(r"$I_c$ (µA)", fontsize=5.1, labelpad=0.2)
    ax_in1.set_xlabel(r"$V_{\mathrm{ctrl}}$", fontsize=5.1, labelpad=0.3)
    ax_in1.set_facecolor("white")

    # Panel (b): No-reset startup & overload recovery at fs_ll/1.98V
    sw = SIM["clamp"]["stress_wf"]
    ax_tr.axhspan(7.5, 11.2, color=C_DANGER, alpha=0.75, lw=0)
    ax_tr.axhline(7.5, color=C_CRIM, ls="--", lw=0.75)
    ax_tr.axhline(2.5, color=C_SLATE, ls=":", lw=0.65)
    v_ov = sw["V2A5_fsll198_ovl"]
    v_nr = sw["V2A5_fsll198_norst"]
    ax_tr.axvspan(10, 25, color="#FEF3C7", alpha=0.55, lw=0)
    ax_tr.text(17.5, 10.65, "Rail OVL", ha="center", va="top", fontsize=6.0, color="#92400E", fontweight="bold")
    ax_tr.plot(v_ov["tf_us"], v_ov["fp_mhz"], color=C_NAVY, ls="-", lw=1.25,
               label=f"Rail overload ({v_ov['f_end_mhz']:.2f} MHz)")
    ax_tr.plot(v_nr["tf_us"], v_nr["fp_mhz"], color=C_TEAL, ls="-.", lw=1.05,
               label=f"No reset ({v_nr['f_end_mhz']:.2f} MHz)")
    ax_tr.set_xlim(0, 50)
    ax_tr.set_ylim(0, 11.2)
    ax_tr.set_xlabel("Time (µs)")
    ax_tr.set_ylabel(r"Instantaneous $f_{\mathrm{VCO}}$ (MHz)")
    ax_tr.grid(True, alpha=0.55)
    ax_tr.legend(loc="center right", bbox_to_anchor=(0.99, 0.54), frameon=True, framealpha=0.93,
                 edgecolor="#CBD5E1", fontsize=5.3, handlelength=1.3, borderpad=0.20, labelspacing=0.15)
    ax_tr.set_title(r"(b) Startup & Overload ($\mathrm{fs\_ll}$, 1.98 V)", pad=4)

    # Panel (c): Full-transistor digital isolation vs Cload + glitch inset
    diso = SIM["dig_iso"]
    def get_series(arch, corner, field):
        pts = sorted([r for r in diso if r["arch"] == arch and r["corner"] == corner],
                     key=lambda x: x["cload_pf"])
        return np.array([p["cload_pf"] for p in pts]), np.array([p[field] for p in pts])

    cl, v2_ss_loss   = get_series("V2_ISO", "ss_hh", "loss_max_ns")
    _,  v2_tt_loss   = get_series("V2_ISO", "tt", "loss_max_ns")
    _,  v2_ss_asym   = get_series("V2_ISO", "ss_hh", "asym_ns")

    ax_iso.semilogy(cl, v2_ss_loss,   "o-",  color=C_NAVY,  ms=3.3, lw=1.25, label="Glitch (ss_hh)")
    ax_iso.semilogy(cl, v2_tt_loss,   "s--", color=C_SLATE, ms=3.0, lw=1.0, label="Glitch (tt)")
    ax_iso.semilogy(cl, v2_ss_asym,   "^-",  color=C_TEAL,  ms=3.0, lw=1.1, label="Rise-fall asym. (ss_hh)")

    ax_iso.annotate(
        f"Flat to {v2_ss_loss.max():.3f} ns\nover 0–5 pF",
        xy=(3.0, v2_ss_loss[-2]), xytext=(2.7, 0.42),
        fontsize=5.8, fontweight="bold", color=C_NAVY,
        bbox=dict(boxstyle="round,pad=0.17", fc="white", ec=C_NAVY, lw=0.5, alpha=0.93),
        arrowprops=dict(arrowstyle="->", color=C_NAVY, lw=0.6),
    )
    ax_iso.set_xlim(-0.15, 5.25)
    ax_iso.set_ylim(0.018, 1.2)
    ax_iso.set_xlabel(r"External Pin Load $C_{\mathrm{load}}$ (pF)")
    ax_iso.set_ylabel("DAC Pulse Error (ns)")
    ax_iso.grid(True, which="major", alpha=0.55)
    ax_iso.legend(loc="upper left", frameon=True, framealpha=0.92, edgecolor="#CBD5E1",
                  fontsize=5.1, handlelength=1.3, borderpad=0.18, labelspacing=0.14)
    ax_iso.set_title("(c) DAC Pulse Error vs. Pin Load", pad=4)

    out_pdf = os.path.join(FIG_DIR, "fig3_clamp_iso.pdf")
    fig.savefig(out_pdf)
    plt.close(fig)
    print("Saved", out_pdf)


# ==============================================================================
# FIG. 4: TRUE IN-BAND 14.65 kHz PSD SPECTRA + 16-SEED MC & 21-PVT SUMMARY
# ==============================================================================
def make_fig4():
    fig = plt.figure(figsize=(7.15, 2.55))
    gs = gridspec.GridSpec(2, 2, width_ratios=[1.22, 1.0], height_ratios=[1.0, 0.92],
                           wspace=0.26, hspace=0.40)
    ax_psd = fig.add_subplot(gs[:, 0])
    ax_mc  = fig.add_subplot(gs[0, 1])
    ax_pvt = fig.add_subplot(gs[1, 1])

    fs = 10e6
    # Panel (a): 14.65 kHz Spectra (Schematic + Full-Transistor Flat PEX)
    specs = [
        ("p2", "V2A5_tt",   "tt sch (71.8 dB, HD3=-76.1 dBc)",     C_NAVY,  "-",  1.25),
        ("p2", "V2A5_sf",   "sf sch (71.5 dB, HD3=-75.0 dBc)",     C_TEAL,  "--", 0.90),
        ("p2", "V2A5_ffhh", "ff_hh/-20°C sch (68.9 dB, -70.3)",    C_CRIM,  "-.", 0.90),
    ]
    ax_psd.axvspan(4.88, 50, color=C_BAND, alpha=0.28, lw=0)
    for sub, tag, lbl, col, ls, lw in specs:
        y = np.load(os.path.join(DATA_DIR, sub, f"{tag}_y.npy"))
        m = len(y)
        win = np.hanning(m)
        Y = np.abs(np.fft.rfft((y - y.mean()) * win))
        f_khz = np.fft.rfftfreq(m, 1.0 / fs) / 1e3
        p_sig = np.sum(Y[2:5] ** 2)
        psd_dbc = 10.0 * np.log10(np.maximum(Y ** 2 / p_sig, 1e-16))
        ax_psd.semilogx(f_khz[1:], psd_dbc[1:], color=col, ls=ls, lw=lw, label=lbl)

    # Overlay full-transistor flat-PEX TT spectrum (16x 1pF loads, 2443 parasitic caps)
    pex_yp = os.path.join(DATA_DIR, "pex_flat", "pex_tt_27_yp.npy")
    pex_yn = os.path.join(DATA_DIR, "pex_flat", "pex_tt_27_yn.npy")
    if os.path.exists(pex_yp) and os.path.exists(pex_yn):
        y_pex = np.load(pex_yn) - np.load(pex_yp)
        m = len(y_pex)
        win = np.hanning(m)
        Y = np.abs(np.fft.rfft((y_pex - y_pex.mean()) * win))
        f_khz = np.fft.rfftfreq(m, 1.0 / fs) / 1e3
        p_sig = np.sum(Y[2:5] ** 2)
        psd_dbc = 10.0 * np.log10(np.maximum(Y ** 2 / p_sig, 1e-16))
        ax_psd.semilogx(f_khz[1:], psd_dbc[1:], color=C_AMBER, ls="-", lw=1.05, alpha=0.92,
                        label="Flat-PEX tt (70.1 dB, HD3=-71.9 dBc)")

    # 40 dB/dec reference slope
    f_ref = np.array([25.0, 1500.0])
    y_ref = -98.0 + 40.0 * np.log10(f_ref / 25.0)
    ax_psd.semilogx(f_ref, y_ref, color=C_SLATE, ls=":", lw=1.0)
    ax_psd.text(320, -48, "+40 dB/dec\n(2nd-order)", fontsize=6.4, color=C_SLATE, ha="center")
    ax_psd.axvline(50.0, color=C_SLATE, ls="--", lw=0.75)
    ax_psd.text(55.0, -3.5, "BW = 50 kHz", fontsize=6.3, color=C_SLATE, ha="left", va="top")
    # Mark HD2 & HD3 in-band
    ax_psd.annotate("HD2\n29.3 kHz", xy=(29.3, -75.9), xytext=(15.5, -52),
                    fontsize=6.0, color=C_NAVY, ha="center",
                    arrowprops=dict(arrowstyle="->", color=C_NAVY, lw=0.55))
    ax_psd.annotate("HD3\n43.95 kHz", xy=(43.95, -70.3), xytext=(88, -56),
                    fontsize=6.0, color=C_CRIM, ha="center",
                    arrowprops=dict(arrowstyle="->", color=C_CRIM, lw=0.55))

    ax_psd.set_xlim(4.8, 5000)
    ax_psd.set_ylim(-120, 6)
    ax_psd.set_xlabel("Frequency (kHz)")
    ax_psd.set_ylabel("Normalized PSD (dBc / bin)")
    ax_psd.grid(True, which="major", alpha=0.55)
    ax_psd.legend(loc="lower right", frameon=True, framealpha=0.92, edgecolor="#CBD5E1",
                  fontsize=6.0, handlelength=1.5, borderpad=0.25, labelspacing=0.18)
    ax_psd.set_title(r"(a) Output Spectra ($f_{\mathrm{in}}=14.65$ kHz, $N=2048$, Hann)", pad=4)

    # Panel (b) top: 16-seed tt_mm Mismatch MC SNDR histogram + DC offset inset
    mcs, dcs = [], []
    for i in range(16):
        y = np.load(os.path.join(DATA_DIR, "p4", f"mc_s{i}_y.npy"))
        r = score_hann3(y, bw=50e3)
        mcs.append(r["sndr"]); dcs.append(r["dc"])
    mcs = np.array(mcs); dcs = np.array(dcs)
    bins_h = np.linspace(67.5, 72.5, 11)
    ax_mc.hist(mcs, bins=bins_h, color=C_NAVY, alpha=0.80, edgecolor="white", lw=0.6)
    ax_mc.axvline(np.median(mcs), color=C_CRIM, ls="--", lw=1.0)
    ax_mc.text(67.65, 5.2,
               f"N = 16 (tt_mm)\nmed = {np.median(mcs):.1f} dB\n$\\sigma$ = {np.std(mcs):.2f} dB\ndc $\\sigma$ = {np.std(dcs):.3f} LSB",
               fontsize=6.0, va="top",
               bbox=dict(boxstyle="round,pad=0.20", fc="white", ec=C_NAVY, lw=0.5, alpha=0.92))
    ax_mc.set_xlim(67.3, 72.5)
    ax_mc.set_ylim(0, 6.2)
    ax_mc.set_xlabel("In-Band SNDR @ 50 kHz (dB)")
    ax_mc.set_ylabel("Count")
    ax_mc.grid(True, axis="y", alpha=0.5)
    ax_mc.set_title("(b) 16-Seed Mismatch MC & 21-Corner PVT", pad=4)

    # Panel (b) bottom: 21-corner PVT + R/C + VDD SNDR overview grouped by VDD
    pvt_180, pvt_198, pvt_162 = [], [], []
    for fp in sorted(glob.glob(os.path.join(DATA_DIR, "p3", "*_y.npy"))):
        nm = os.path.basename(fp)
        r = score_hann3(np.load(fp), bw=50e3)
        if "1.62" in nm:   pvt_162.append(r["sndr"])
        elif "1.98" in nm: pvt_198.append(r["sndr"])
        else:              pvt_180.append(r["sndr"])

    y_pos = [0, 1, 2]
    for yp, vals, col, lbl in [
        (2, pvt_198, C_TEAL,  "1.98 V (+10%)"),
        (1, pvt_180, C_NAVY,  "1.80 V (Nom.)"),
        (0, pvt_162, C_AMBER, "1.62 V (-10%)"),
    ]:
        ax_pvt.plot([min(vals), max(vals)], [yp, yp], color=col, lw=2.2, alpha=0.55)
        ax_pvt.scatter(vals, [yp] * len(vals), color=col, s=16, zorder=5, edgecolors="white", linewidths=0.4)
        ax_pvt.text(max(vals) + 0.35, yp, f"{min(vals):.1f}–{max(vals):.1f} dB",
                    va="center", fontsize=6.0, color=col, fontweight="bold")
    ax_pvt.set_yticks([0, 1, 2])
    ax_pvt.set_yticklabels(["1.62 V\n(4)", "1.80 V\n(13)", "1.98 V\n(4)"], fontsize=6.4)
    ax_pvt.set_xlim(62.0, 79.0)
    ax_pvt.set_ylim(-0.55, 2.55)
    ax_pvt.set_xlabel("21-Corner PVT+R/C SNDR @ 50 kHz (dB)")
    ax_pvt.grid(True, axis="x", alpha=0.55)

    out_pdf = os.path.join(FIG_DIR, "fig4_spectra_mc.pdf")
    fig.savefig(out_pdf)
    plt.close(fig)
    print("Saved", out_pdf)


# ==============================================================================
# FIG. 5: ANNOTATED CORE LAYOUT WITH CLEAN BLOCK CALLOUTS
# ==============================================================================
def make_fig5():
    im = Image.open(LAYOUT_IMG).convert("RGB")
    w, h = im.size
    fig, ax = plt.subplots(figsize=(3.42, 3.65))
    ax.imshow(im, extent=[0, 161.0, 0, 225.76], origin="upper", interpolation="bilinear")

    # Crisp IEEE-style white-backed callout badges (coords in um, y=0 bottom, y=225.76 top)
    # Note: extent=[0, 161, 0, 225.76] with origin='upper' maps top of image to y=225.76, bottom to y=0!
    badges = [
        (80.5, 214.0, "Digital: 2×(7×dfxtp_1+xor2_1+buf_4) + 8×conb_1", C_NAVY, 5.2),
        (80.5, 184.0, "Mirrored 7-Stage Ring VCOs (P / N)", C_TEAL, 5.6),
        (80.5, 159.0, "CC VCO Bias R-Array", C_CRIM, 5.4),
        (43.0, 132.0, "42-Strip+Dummy\nRDAC (P)", C_NAVY, 5.5),
        (118.0, 132.0, "42-Strip+Dummy\nRDAC (N)", C_NAVY, 5.5),
        (43.0, 88.0,  "CC 5T OTA +\nclamp (P)", C_PURPLE, 5.5),
        (118.0, 88.0, "CC 5T OTA +\nclamp (N)", C_PURPLE, 5.5),
        (80.5, 61.0,  "Integrators: 2×(24×25 µm MIM) / Half", C_TEAL, 5.5),
        (80.5, 36.0,  "Shared Bias, Vref & Reset Inv.", C_AMBER, 5.5),
        (80.5, 14.0,  "699× sky130_fd_sc_hd__decap_12 Field", C_SLATE, 5.5),
    ]
    for x, y, txt, col, fs_b in badges:
        ax.text(
            x, y, txt, ha="center", va="center", fontsize=fs_b, fontweight="bold", color=col,
            bbox=dict(boxstyle="round,pad=0.17", fc="white", ec=col, lw=0.72, alpha=0.90),
        )

    ax.set_xlim(0, 161.0)
    ax.set_ylim(0, 225.76)
    ax.set_xlabel(r"Tile Width: $161.0\,\mu\mathrm{m}$ (TT 1×2 Analog Tile)")
    ax.set_ylabel(r"Tile Height: $225.76\,\mu\mathrm{m}$")
    ax.tick_params(direction="out", top=False, right=False, labelsize=6.5)

    out_pdf = os.path.join(FIG_DIR, "fig5_layout.pdf")
    fig.savefig(out_pdf, dpi=300)
    plt.close(fig)
    print("Saved", out_pdf)


if __name__ == "__main__":
    make_fig2()
    make_fig3()
    make_fig4()
    make_fig5()
    print("All publication figures generated cleanly!")
