/**
 * Interactive SVG Measurement Charts (100% Real ngspice-47 Sign-Off Data)
 * Zero external charting library dependencies; crisp vector rendering with live
 * hover crosshairs, tooltips, and interactive series toggles.
 */

const C = {
  navy: '#0B3C5D',
  teal: '#147D64',
  amber: '#D97706',
  crimson: '#B91C1C',
  purple: '#6D28D9',
  blue: '#2563EB',
  slate: '#475569',
  grid: 'rgba(15,23,42,0.10)',
  band: '#DBEAFE',
  danger: '#FEE2E2',
};

function el(tag, attrs = {}, text = '') {
  const n = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  if (text) n.textContent = text;
  return n;
}

function drawPlot(container, cfg) {
  const W = cfg.width || 620;
  const H = cfg.height || 300;
  const pad = cfg.pad || { l: 56, r: 18, t: 24, b: 40 };
  const pw = W - pad.l - pad.r;
  const ph = H - pad.t - pad.b;

  const xMap = cfg.logX
    ? (v) => pad.l + ((Math.log10(Math.max(v, 1e-12)) - Math.log10(cfg.xMin)) / (Math.log10(cfg.xMax) - Math.log10(cfg.xMin))) * pw
    : (v) => pad.l + ((v - cfg.xMin) / (cfg.xMax - cfg.xMin)) * pw;
  const yMap = cfg.logY
    ? (v) => pad.t + ph - ((Math.log10(Math.max(v, 1e-12)) - Math.log10(cfg.yMin)) / (Math.log10(cfg.yMax) - Math.log10(cfg.yMin))) * ph
    : (v) => pad.t + ph - ((v - cfg.yMin) / (cfg.yMax - cfg.yMin)) * ph;

  const invX = cfg.logX
    ? (px) => Math.pow(10, Math.log10(cfg.xMin) + ((px - pad.l) / pw) * (Math.log10(cfg.xMax) - Math.log10(cfg.xMin)))
    : (px) => cfg.xMin + ((px - pad.l) / pw) * (cfg.xMax - cfg.xMin);

  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': cfg.title || 'Chart' });

  // Background bands
  if (cfg.bands) {
    for (const b of cfg.bands) {
      const x0 = b.x0 !== undefined ? Math.max(xMap(b.x0), pad.l) : pad.l;
      const x1 = b.x1 !== undefined ? Math.min(xMap(b.x1), pad.l + pw) : pad.l + pw;
      const y0 = b.y1 !== undefined ? Math.max(yMap(b.y1), pad.t) : pad.t;
      const y1 = b.y0 !== undefined ? Math.min(yMap(b.y0), pad.t + ph) : pad.t + ph;
      svg.appendChild(el('rect', { x: x0, y: y0, width: Math.max(0, x1 - x0), height: Math.max(0, y1 - y0), fill: b.fill, opacity: b.opacity ?? 0.5 }));
      if (b.label) {
        svg.appendChild(el('text', { x: (x0 + x1) / 2, y: y0 + 13, 'text-anchor': 'middle', fill: b.labelColor || C.slate, 'font-size': 10.5, 'font-family': 'Geist Mono, ui-monospace, monospace', 'font-weight': 600 }, b.label));
      }
    }
  }

  // Gridlines & Ticks
  for (const xt of cfg.xTicks) {
    const x = xMap(xt.v);
    if (x < pad.l - 1 || x > pad.l + pw + 1) continue;
    svg.appendChild(el('line', { x1: x, y1: pad.t, x2: x, y2: pad.t + ph, stroke: C.grid, 'stroke-width': 1 }));
    svg.appendChild(el('text', { x, y: pad.t + ph + 16, 'text-anchor': 'middle', fill: C.slate, 'font-size': 10.5, 'font-family': 'Geist Mono, ui-monospace, monospace' }, xt.l));
  }
  for (const yt of cfg.yTicks) {
    const y = yMap(yt.v);
    if (y < pad.t - 1 || y > pad.t + ph + 1) continue;
    svg.appendChild(el('line', { x1: pad.l, y1: y, x2: pad.l + pw, y2: y, stroke: C.grid, 'stroke-width': 1 }));
    svg.appendChild(el('text', { x: pad.l - 8, y: y + 3.5, 'text-anchor': 'end', fill: C.slate, 'font-size': 10.5, 'font-family': 'Geist Mono, ui-monospace, monospace' }, yt.l));
  }

  // Reference lines
  if (cfg.vLines) {
    for (const vl of cfg.vLines) {
      const x = xMap(vl.x);
      svg.appendChild(el('line', { x1: x, y1: pad.t, x2: x, y2: pad.t + ph, stroke: vl.color || C.slate, 'stroke-dasharray': vl.dash || '4 3', 'stroke-width': 1.1 }));
      if (vl.label) {
        const align = vl.align || 'start';
        const dx = align === 'end' ? -4 : 4;
        const dy = vl.dy ?? 13;
        svg.appendChild(el('text', { x: x + dx, y: pad.t + dy, 'text-anchor': align, fill: vl.color || C.slate, 'font-size': 10, 'font-family': 'Geist Mono, ui-monospace, monospace', 'font-weight': 600 }, vl.label));
      }
    }
  }
  if (cfg.hLines) {
    for (const hl of cfg.hLines) {
      const y = yMap(hl.y);
      svg.appendChild(el('line', { x1: pad.l, y1: y, x2: pad.l + pw, y2: y, stroke: hl.color || C.slate, 'stroke-dasharray': hl.dash || '4 3', 'stroke-width': 1.1 }));
      if (hl.label) {
        const align = hl.align || 'end';
        const tx = align === 'start' ? pad.l + 6 : pad.l + pw - 6;
        const dy = hl.dy ?? -5;
        svg.appendChild(el('text', { x: tx, y: y + dy, 'text-anchor': align, fill: hl.color || C.slate, 'font-size': 10, 'font-family': 'Geist Mono, ui-monospace, monospace', 'font-weight': 600 }, hl.label));
      }
    }
  }

  // Plot frame
  svg.appendChild(el('rect', { x: pad.l, y: pad.t, width: pw, height: ph, fill: 'none', stroke: 'rgba(15,23,42,0.35)', 'stroke-width': 1 }));

  // Clip path for traces
  const clipId = 'clip-' + Math.random().toString(36).slice(2, 8);
  const defs = el('defs');
  const cp = el('clipPath', { id: clipId });
  cp.appendChild(el('rect', { x: pad.l, y: pad.t, width: pw, height: ph }));
  defs.appendChild(cp);
  svg.appendChild(defs);

  const traceGroup = el('g', { 'clip-path': `url(#${clipId})` });
  for (const s of cfg.series) {
    if (s.hidden) continue;
    const pts = [];
    for (let i = 0; i < s.x.length; i++) {
      const xv = s.x[i], yv = s.y[i];
      if (!Number.isFinite(xv) || !Number.isFinite(yv)) continue;
      if (cfg.logX && xv <= 0) continue;
      if (cfg.logY && yv <= 0) continue;
      pts.push(`${xMap(xv).toFixed(1)},${yMap(yv).toFixed(1)}`);
    }
    if (pts.length > 1) {
      traceGroup.appendChild(el('polyline', {
        points: pts.join(' '),
        fill: 'none',
        stroke: s.color,
        'stroke-width': s.lw || 1.8,
        'stroke-dasharray': s.dash || '',
        'stroke-linejoin': 'round',
        opacity: s.opacity ?? 1,
      }));
    }
    if (s.markers) {
      for (let i = 0; i < s.x.length; i++) {
        traceGroup.appendChild(el('circle', {
          cx: xMap(s.x[i]), cy: yMap(s.y[i]), r: s.r || 3.2,
          fill: s.color, stroke: '#ffffff', 'stroke-width': 1,
        }));
      }
    }
  }
  if (cfg.extra) cfg.extra(traceGroup, xMap, yMap);
  svg.appendChild(traceGroup);

  // Title & Axis Labels
  if (cfg.title) {
    svg.appendChild(el('text', { x: pad.l, y: 15, fill: '#111827', 'font-size': 12.5, 'font-weight': 600, 'font-family': 'Geist, -apple-system, sans-serif' }, cfg.title));
  }
  if (cfg.xLabel) {
    svg.appendChild(el('text', { x: pad.l + pw / 2, y: H - 6, 'text-anchor': 'middle', fill: '#475569', 'font-size': 11, 'font-family': 'Geist, -apple-system, sans-serif' }, cfg.xLabel));
  }
  if (cfg.yLabel) {
    svg.appendChild(el('text', {
      x: 14, y: pad.t + ph / 2, 'text-anchor': 'middle',
      transform: `rotate(-90 14 ${pad.t + ph / 2})`,
      fill: '#475569', 'font-size': 11, 'font-family': 'Geist, -apple-system, sans-serif',
    }, cfg.yLabel));
  }

  // Interactive Crosshair
  const cross = el('line', { x1: 0, y1: pad.t, x2: 0, y2: pad.t + ph, stroke: '#111827', 'stroke-dasharray': '3 3', 'stroke-width': 0.9, opacity: 0 });
  svg.appendChild(cross);

  container.innerHTML = '';
  if (cfg.showLegend) {
    const leg = document.createElement('div');
    leg.className = 'chart-legend';
    leg.innerHTML = cfg.series.filter((s) => !s.hidden).map((s) => {
      const cls = s.dash ? (s.dash.startsWith('2') ? 'dotted' : 'dashed') : '';
      return `<span class="legend-item"><span class="legend-line ${cls}" style="color:${s.color}"></span>${s.short || s.label}</span>`;
    }).join('');
    container.appendChild(leg);
  }
  const wrap = document.createElement('div');
  wrap.className = 'svg-chart-wrap';
  wrap.appendChild(svg);
  const tip = document.createElement('div');
  tip.className = 'chart-tooltip';
  wrap.appendChild(tip);
  container.appendChild(wrap);

  const hit = el('rect', { x: pad.l, y: pad.t, width: pw, height: ph, fill: 'transparent', style: 'cursor:crosshair' });
  svg.appendChild(hit);

  hit.addEventListener('pointermove', (ev) => {
    const rect = svg.getBoundingClientRect();
    const sx = ((ev.clientX - rect.left) / rect.width) * W;
    const xVal = invX(sx);
    cross.setAttribute('x1', sx);
    cross.setAttribute('x2', sx);
    cross.setAttribute('opacity', 0.45);

    const lines = [`<strong>${cfg.fmtX ? cfg.fmtX(xVal) : xVal.toFixed(2)}</strong>`];
    for (const s of cfg.series) {
      if (s.hidden || !s.x.length) continue;
      // nearest point
      let bestI = 0, bestD = Infinity;
      for (let i = 0; i < s.x.length; i++) {
        const d = Math.abs(s.x[i] - xVal);
        if (d < bestD) { bestD = d; bestI = i; }
      }
      lines.push(`<span style="color:${s.color}">●</span> ${s.short || s.label}: ${cfg.fmtY ? cfg.fmtY(s.y[bestI]) : s.y[bestI].toFixed(1)}`);
    }
    tip.innerHTML = lines.join('<br>');
    tip.style.display = 'block';
    const leftPx = ev.clientX - rect.left + 12;
    const topPx = ev.clientY - rect.top - 12;
    tip.style.left = `${Math.min(leftPx, rect.width - 210)}px`;
    tip.style.top = `${Math.max(8, topPx)}px`;
  });
  hit.addEventListener('pointerleave', () => {
    cross.setAttribute('opacity', 0);
    tip.style.display = 'none';
  });
}

export async function initMeasurementCharts(dataUrl = 'data/sim_data.json') {
  const root = document.getElementById('meas-stage');
  if (!root) return;
  let sim;
  try {
    const r = await fetch(dataUrl);
    sim = await r.json();
  } catch (e) {
    root.innerHTML = `<p style="color:var(--muted);font-family:var(--font-mono);font-size:13px;">Could not load sim_data.json (${e.message}).</p>`;
    return;
  }

  const tabs = document.querySelectorAll('#meas-tabs .tab-btn');
  let activeTab = 'spectra';

  // Spectra toggle state
  const specDefs = [
    { key: 'pex_tt_27',    short: 'Flat-PEX tt (70.1 dB)',    color: C.amber,   lw: 2.1, on: true },
    { key: 'pex_sf_27',    short: 'Flat-PEX sf (69.3 dB)',    color: C.crimson, lw: 1.7, on: true },
    { key: 'pex_fs_ll_27', short: 'Flat-PEX fs_ll (70.4 dB)', color: C.purple,  lw: 1.6, on: false },
    { key: 'pex_ss_85',    short: 'Flat-PEX ss/85°C (69.0)',  color: '#0891B2', lw: 1.6, on: false },
    { key: 'V2A5_tt',      short: 'Sch. tt (71.8 dB)',        color: C.navy,    lw: 1.8, dash: '5 3', on: true },
    { key: 'V2A5_ffhh',    short: 'Sch. ff_hh/-20°C (68.9)',  color: C.teal,    lw: 1.5, dash: '3 2', on: false },
  ];

  function renderSpectra() {
    root.innerHTML = `
      <div class="chart-card">
        <div class="chart-controls" id="spec-toggles"></div>
        <div id="chart-psd"></div>
        <p style="margin:12px 0 0;font-size:12.8px;color:var(--muted);">
          Coherent <code>fin = 14.648 kHz</code> (<code>N = 2048</code>, bin 3, Hann, <code>Δtmax = 0.5 ns</code>, <code>reltol = 1e-4</code>) places both <code>HD2 = 29.3 kHz</code> and <code>HD3 = 43.95 kHz</code> strictly inside the 50 kHz band. Click pills above to compare any full-transistor flat-PEX corner against schematic.
        </p>
      </div>
    `;
    const tog = document.getElementById('spec-toggles');
    const draw = () => {
      tog.innerHTML = specDefs.map((d, i) => `
        <button class="series-pill ${d.on ? '' : 'off'}" data-idx="${i}">
          <span class="series-swatch" style="background:${d.color}"></span>${d.short}
        </button>
      `).join('');
      tog.querySelectorAll('.series-pill').forEach((btn) => {
        btn.addEventListener('click', () => {
          const i = +btn.dataset.idx;
          specDefs[i].on = !specDefs[i].on;
          draw();
        });
      });

      drawPlot(document.getElementById('chart-psd'), {
        width: 960, height: 340,
        title: 'True In-Band 14.65 kHz Output PSD (Full-Transistor Flat PEX vs. Schematic)',
        xLabel: 'Frequency (kHz)', yLabel: 'Normalized PSD (dBc / bin)',
        logX: true, xMin: 4.8, xMax: 5000, yMin: -120, yMax: 6,
        xTicks: [
          { v: 5, l: '5' }, { v: 10, l: '10' }, { v: 20, l: '20' }, { v: 50, l: '50' },
          { v: 100, l: '100' }, { v: 500, l: '500' }, { v: 1000, l: '1M' }, { v: 5000, l: '5M' },
        ],
        yTicks: [-120, -100, -80, -60, -40, -20, 0].map((v) => ({ v, l: String(v) })),
        bands: [{ x0: 4.8, x1: 50, fill: C.band, opacity: 0.45, label: '50 kHz Signal Band', labelColor: C.navy }],
        vLines: [
          { x: 50, color: C.navy, dash: '5 3', label: 'BW=50k', align: 'start', dy: 13 },
          { x: 29.3, color: C.slate, dash: '2 3', label: 'HD2', align: 'end', dy: 26 },
          { x: 43.95, color: C.crimson, dash: '2 3', label: 'HD3', align: 'end', dy: 40 },
        ],
        series: specDefs.map((d) => ({
          short: d.short, color: d.color, lw: d.lw, dash: d.dash, hidden: !d.on,
          x: sim.spectra[d.key].f_khz, y: sim.spectra[d.key].dbc,
        })),
        extra: (g, xm, ym) => {
          // +40 dB/dec reference line + clean non-overlapping label above the noise slope
          g.appendChild(el('line', { x1: xm(25), y1: ym(-98), x2: xm(1500), y2: ym(-98 + 40 * Math.log10(1500 / 25)), stroke: C.slate, 'stroke-dasharray': '3 3', 'stroke-width': 1.2 }));
          g.appendChild(el('text', { x: xm(190), y: ym(-16), fill: C.slate, 'font-size': 10.5, 'font-family': 'Geist Mono, ui-monospace, monospace', 'font-weight': 600 }, '+40 dB/dec (2nd-order)'));
        },
        fmtX: (v) => v >= 1000 ? `${(v / 1000).toFixed(2)} MHz` : `${v.toFixed(1)} kHz`,
        fmtY: (v) => `${v.toFixed(1)} dBc`,
      });
    };
    draw();
  }

  function renderNoiseStb() {
    root.innerHTML = `
      <div class="chart-grid-2">
        <div class="chart-card"><div id="chart-noise"></div></div>
        <div class="chart-card"><div id="chart-stb"></div></div>
      </div>
    `;
    drawPlot(document.getElementById('chart-noise'), {
      width: 560, height: 295, showLegend: true,
      title: 'BSIM4 Diff. Input Noise PSD (22.8 µVrms, 0.1–50 kHz, tt)',
      xLabel: 'Frequency (Hz)', yLabel: 'Input Noise (nV / √Hz)',
      logX: true, logY: true, xMin: 10, xMax: 5e5, yMin: 40, yMax: 8000,
      xTicks: [{ v: 10, l: '10' }, { v: 100, l: '100' }, { v: 1e3, l: '1k' }, { v: 1e4, l: '10k' }, { v: 5e4, l: '50k' }, { v: 5e5, l: '500k' }],
      yTicks: [{ v: 50, l: '50' }, { v: 100, l: '100' }, { v: 500, l: '500' }, { v: 1000, l: '1k' }, { v: 5000, l: '5k' }],
      bands: [{ x0: 100, x1: 5e4, fill: C.band, opacity: 0.4, label: '100 Hz – 50 kHz' }],
      series: [
        { short: 'tt (22.8 µVrms)',    color: C.navy,  lw: 2.2, x: sim.noise.V2_A5_tt.f_hz, y: sim.noise.V2_A5_tt.n_nv },
        { short: 'ss_hh/85°C/1.62V',   color: C.teal,  dash: '5 3', lw: 1.6, x: sim.noise.V2_A5_ss_hh.f_hz, y: sim.noise.V2_A5_ss_hh.n_nv },
        { short: 'ff_ll/-20°C/1.98V',  color: C.crimson, dash: '2 2', lw: 1.4, x: sim.noise.V2_A5_ff_ll.f_hz, y: sim.noise.V2_A5_ff_ll.n_nv },
      ],
      fmtX: (v) => v >= 1e3 ? `${(v / 1e3).toFixed(1)} kHz` : `${v.toFixed(0)} Hz`,
      fmtY: (v) => `${v.toFixed(0)} nV/√Hz`,
    });

    drawPlot(document.getElementById('chart-stb'), {
      width: 560, height: 295, showLegend: true,
      title: 'Exact Tian Closed-Loop Integrator |T(f)| (PM = 72.2° [67.7°–79.8°])',
      xLabel: 'Frequency (MHz)', yLabel: 'Loop Return Ratio |T(f)| (dB)',
      logX: true, xMin: 0.01, xMax: 100, yMin: -25, yMax: 35,
      xTicks: [{ v: 0.01, l: '10k' }, { v: 0.1, l: '100k' }, { v: 1, l: '1M' }, { v: 5, l: '5M' }, { v: 10, l: '10M' }, { v: 100, l: '100M' }],
      yTicks: [-20, -10, 0, 10, 20, 30].map((v) => ({ v, l: String(v) })),
      hLines: [{ y: 0, color: C.slate, dash: '4 3', label: '0 dB (fug = 4.95 MHz)', align: 'start', dy: 13 }],
      series: [
        { short: 'tt (PM 72.2°)',      color: C.navy,    lw: 2.2, x: sim.stb.V2_A5_tt.f_mhz, y: sim.stb.V2_A5_tt.mag_db },
        { short: 'ss_hh/85°C/1.62V',   color: C.teal,    dash: '5 3', lw: 1.7, x: sim.stb.V2_A5_ss_hh.f_mhz, y: sim.stb.V2_A5_ss_hh.mag_db },
        { short: 'ff_ll/-20°C/1.98V',  color: C.crimson, dash: '3 2', lw: 1.7, x: sim.stb.V2_A5_ff_ll.f_mhz, y: sim.stb.V2_A5_ff_ll.mag_db },
      ],
      fmtX: (v) => v < 1 ? `${(v * 1e3).toFixed(0)} kHz` : `${v.toFixed(2)} MHz`,
      fmtY: (v) => `${v.toFixed(1)} dB`,
    });
  }

  function renderClampIso() {
    root.innerHTML = `
      <div class="chart-grid-2">
        <div class="chart-card"><div id="chart-ovl"></div></div>
        <div class="chart-card"><div id="chart-iso"></div></div>
      </div>
    `;
    drawPlot(document.getElementById('chart-ovl'), {
      width: 560, height: 295, showLegend: true,
      title: 'Forced No-Reset & Rail Overload Recovery (fs_ll, 1.98 V)',
      xLabel: 'Time (µs)', yLabel: 'Instantaneous f_VCO (MHz)',
      xMin: 0, xMax: 50, yMin: 0, yMax: 10.5,
      xTicks: [0, 10, 20, 30, 40, 50].map((v) => ({ v, l: String(v) })),
      yTicks: [0, 2.5, 5, 7.5, 10].map((v) => ({ v, l: String(v) })),
      bands: [
        { y0: 7.5, y1: 10.5, fill: C.danger, opacity: 0.7, label: 'Aliasing Latch-Up Zone (> 0.75 fs)', labelColor: C.crimson },
        { x0: 10, x1: 25, y0: 0, y1: 7.5, fill: '#FEF3C7', opacity: 0.55, label: 'Rail OVL', labelColor: C.amber },
      ],
      hLines: [{ y: 2.5, color: C.slate, dash: '2 3', label: 'Lock = fs/4 (2.5 MHz)', align: 'end', dy: 14 }],
      series: [
        { short: 'OVL (2.50 MHz)', color: C.navy, lw: 2.2, x: sim.stress.V2A5_fsll198_ovl.t_us, y: sim.stress.V2A5_fsll198_ovl.f_mhz },
        { short: 'NoRst (2.50 MHz)', color: C.teal, dash: '6 2', lw: 1.7, x: sim.stress.V2A5_fsll198_norst.t_us, y: sim.stress.V2A5_fsll198_norst.f_mhz },
      ],
      fmtX: (v) => `${v.toFixed(1)} µs`,
      fmtY: (v) => `${v.toFixed(2)} MHz`,
    });

    const getIso = (arch, corner, f) => {
      const pts = sim.dig_iso.filter((r) => r.arch === arch && r.corner === corner).sort((a, b) => a.cload_pf - b.cload_pf);
      return { x: pts.map((p) => p.cload_pf), y: pts.map((p) => p[f]) };
    };
    const vss = getIso('V2_ISO', 'ss_hh', 'loss_ns');
    const vas = getIso('V2_ISO', 'ss_hh', 'asym_ns');

    drawPlot(document.getElementById('chart-iso'), {
      width: 560, height: 295, showLegend: true,
      title: 'Full-Transistor Digital Output Isolation (dfxtp_1 + buf_4, ss_hh)',
      xLabel: 'External Pin Load Capacitance Cload (pF)', yLabel: 'DAC Pulse Error (ns)',
      logY: true, xMin: 0, xMax: 5.2, yMin: 0.02, yMax: 0.3,
      xTicks: [0, 1, 2, 3, 4, 5].map((v) => ({ v, l: `${v} pF` })),
      yTicks: [{ v: 0.03, l: '0.03' }, { v: 0.1, l: '0.1' }, { v: 0.3, l: '0.3' }],
      series: [
        { short: 'Glitch',   color: C.navy,    lw: 2.2, markers: true, x: vss.x, y: vss.y },
        { short: 'Rise-fall asymmetry',     color: C.teal,    lw: 1.9, markers: true, x: vas.x, y: vas.y },
      ],
      fmtX: (v) => `${v.toFixed(2)} pF`,
      fmtY: (v) => `${v.toFixed(3)} ns`,
    });
  }

  function renderPvtMc() {
    const pexRows = [
      ['tt (27°C, 1.80 V)',    173.5, '1.80 V', '2.49 / 2.49', -77.8, -71.9, 70.1, 77.7],
      ['ss (85°C, 1.80 V)',    176.1, '1.80 V', '2.50 / 2.50', -77.4, -70.4, 69.0, 77.9],
      ['ff (-20°C, 1.80 V)',   173.2, '1.80 V', '2.49 / 2.49', -76.8, -70.7, 69.3, 79.6],
      ['sf (27°C, 1.80 V)',    177.1, '1.80 V', '2.50 / 2.50', -76.8, -70.5, 69.3, 81.9],
      ['fs (27°C, 1.80 V)',    170.9, '1.80 V', '2.49 / 2.49', -76.9, -72.5, 70.6, 79.7],
      ['fs_ll (27°C, 1.80 V)', 175.4, '1.80 V', '2.49 / 2.49', -76.9, -72.5, 70.4, 78.4],
    ];
    root.innerHTML = `
      <div class="table-wrap" style="margin-bottom:18px;">
        <table class="eng-table">
          <thead>
            <tr>
              <th>Full-Transistor Flat-PEX Corner (14.65 kHz, 16×1 pF)</th>
              <th class="num">Idd (µA)</th>
              <th class="num">uio_oe</th>
              <th class="num">fP / fN (MHz)</th>
              <th class="num">HD2 (dBc)</th>
              <th class="num">HD3 (dBc)</th>
              <th class="num">SNDR @ 50k</th>
              <th class="num">SNR @ 50k</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${pexRows.map((r) => `
              <tr>
                <td><strong>${r[0]}</strong></td>
                <td class="num">${r[1].toFixed(1)}</td>
                <td class="num">${r[2]}</td>
                <td class="num">${r[3]}</td>
                <td class="num">${r[4].toFixed(1)}</td>
                <td class="num">${r[5].toFixed(1)}</td>
                <td class="num"><strong>${r[6].toFixed(1)} dB</strong></td>
                <td class="num">${r[7].toFixed(1)} dB</td>
                <td><span class="badge-pass">PASS</span></td>
              </tr>`).join('')}
          </tbody>
        </table>
      </div>
      <div class="chart-grid-2">
        <div class="chart-card"><div id="chart-mc"></div></div>
        <div class="chart-card"><div id="chart-pvt"></div></div>
      </div>
    `;
    // 16-Seed MC scatter/stem
    drawPlot(document.getElementById('chart-mc'), {
      width: 560, height: 260,
      title: '16-Seed tt_mm Mismatch MC (Med 71.1 dB, σ = 1.17 dB)',
      xLabel: 'Monte Carlo Seed Index', yLabel: 'In-Band SNDR @ 50 kHz (dB)',
      xMin: -0.5, xMax: 15.5, yMin: 66, yMax: 73.5,
      xTicks: [0, 3, 6, 9, 12, 15].map((v) => ({ v, l: `#${v}` })),
      yTicks: [66, 68, 70, 72].map((v) => ({ v, l: `${v}` })),
      hLines: [{ y: 71.1, color: C.crimson, dash: '5 3' }],
      extra: (g, xm, ym) => {
        g.appendChild(el('text', { x: xm(15.2), y: ym(72.65), 'text-anchor': 'end', fill: C.crimson, 'font-size': 10.5, 'font-family': 'Geist Mono, ui-monospace, monospace', 'font-weight': 600 }, '--- Median 71.1 dB (min 68.1, max 71.7)'));
      },
      series: [{
        short: 'tt_mm MC SNDR', color: C.navy, lw: 1.5, markers: true, r: 4.0,
        x: sim.mc.map((m) => m.seed), y: sim.mc.map((m) => m.sndr),
      }],
      fmtX: (v) => `Seed #${Math.round(v)}`,
      fmtY: (v) => `${v.toFixed(1)} dB`,
    });

    // 21-Corner PVT scatter
    const pvtSorted = [...sim.pvt].sort((a, b) => a.sndr - b.sndr);
    drawPlot(document.getElementById('chart-pvt'), {
      width: 560, height: 260,
      title: '21-Corner PVT + R/C + VDD ±10% SNDR Distribution',
      xLabel: 'Corner Rank (Sorted by SNDR)', yLabel: 'In-Band SNDR @ 50 kHz (dB)',
      xMin: -0.5, xMax: 20.5, yMin: 62, yMax: 75,
      xTicks: [0, 5, 10, 15, 20].map((v) => ({ v, l: `${v + 1}` })),
      yTicks: [62, 65, 68, 71, 74].map((v) => ({ v, l: `${v}` })),
      hLines: [{ y: 68.5, color: C.teal, dash: '4 3', label: '1.80/1.98 V min (68.5 dB)' }],
      series: [
        {
          short: 'All 21 Corners', color: C.navy, lw: 1.4, markers: true, r: 3.8,
          x: pvtSorted.map((_, i) => i), y: pvtSorted.map((p) => p.sndr),
        },
      ],
      fmtX: (v) => {
        const p = pvtSorted[Math.max(0, Math.min(pvtSorted.length - 1, Math.round(v)))];
        return p ? `${p.name} (${p.vdd}V)` : '';
      },
      fmtY: (v) => `${v.toFixed(1)} dB`,
    });
  }

  function render() {
    if (activeTab === 'spectra') renderSpectra();
    else if (activeTab === 'noise') renderNoiseStb();
    else if (activeTab === 'clamp') renderClampIso();
    else renderPvtMc();
  }

  tabs.forEach((btn) => {
    btn.addEventListener('click', () => {
      activeTab = btn.dataset.tab;
      tabs.forEach((b) => b.classList.toggle('active', b === btn));
      render();
    });
  });
  render();
}
