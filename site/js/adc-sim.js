/**
 * Behavioural model of the converter, running live in the page.
 *
 * Per half:  an RC integrator sums input current (Rin) and feedback current (7 x Rd),
 *            its output sets the ring frequency, the ring phase is sampled at fs and
 *            differenced, and the 0..7 count drives the resistor DAC.
 * Component values are the ones on the chip. Three things are idealised or fitted and
 * the page says so next to the plot: the sampler and DAC are ideal, the VCO curvature is
 * fitted to the first open-loop version (50-56 dB), and input noise is white at the
 * 22.9 uVrms (0.1-50 kHz) that BSIM4 noise simulation reports.
 */
const FS = 10e6;
const N = 16384;                 // FFT length, 610 Hz per bin
const BW = 50e3;
const RIN = 49.7e3, RD = 1.04e6, CINT = 2.432e-12, VDD = 1.8, KVCO = 8.48e6;
const KC = (14 * KVCO) / FS;     // phase steps per sample per volt (14 steps per ring period)
const GI = 1 / (FS * CINT);      // integrator: volts per ampere, per sample
const FS_HALF = 0.3;             // full-scale amplitude per half, volts
const SIGMA_HALF = (22.9e-6 * Math.sqrt(FS / 2 / BW)) / Math.SQRT2;
const C2 = 0.06, C3 = -0.036;    // VCO curvature on the normalised drive

const INK = '#eceaf6', DIM = '#8a8fb5', LINE = 'rgba(160,170,255,0.16)';
const GOLD = '#f2c14e', BLUE = '#5b8cff', TEAL = '#3fd1c1', PINK = '#ff5fa8', GREEN = '#3ddc84';

function makeFFT(n) {
  const rev = new Uint32Array(n);
  const bits = Math.log2(n);
  for (let i = 0; i < n; i++) {
    let r = 0;
    for (let b = 0; b < bits; b++) r |= ((i >> b) & 1) << (bits - 1 - b);
    rev[i] = r;
  }
  const cos = new Float64Array(n / 2), sin = new Float64Array(n / 2);
  for (let i = 0; i < n / 2; i++) { cos[i] = Math.cos((2 * Math.PI * i) / n); sin[i] = -Math.sin((2 * Math.PI * i) / n); }
  const re = new Float64Array(n), im = new Float64Array(n);
  return (x, win, out) => {
    for (let i = 0; i < n; i++) { re[rev[i]] = x[i] * win[i]; im[rev[i]] = 0; }
    for (let len = 2; len <= n; len <<= 1) {
      const half = len >> 1, step = n / len;
      for (let i = 0; i < n; i += len) {
        for (let j = 0, k = 0; j < half; j++, k += step) {
          const a = i + j, b = a + half;
          const tr = re[b] * cos[k] - im[b] * sin[k], ti = re[b] * sin[k] + im[b] * cos[k];
          re[b] = re[a] - tr; im[b] = im[a] - ti; re[a] += tr; im[a] += ti;
        }
      }
    }
    for (let i = 0; i < n / 2; i++) out[i] = re[i] * re[i] + im[i] * im[i];
  };
}

function fitCanvas(c) {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = c.clientWidth, h = c.clientHeight;
  if (c.width !== Math.round(w * dpr) || c.height !== Math.round(h * dpr)) { c.width = Math.round(w * dpr); c.height = Math.round(h * dpr); }
  const g = c.getContext('2d');
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { g, w, h };
}

export function initAdcSim() {
  const root = document.getElementById('sim');
  if (!root) return;
  const cScope = document.getElementById('sim-scope');
  const cRings = document.getElementById('sim-rings');
  const cSpec = document.getElementById('sim-spec');
  const out = (id) => document.getElementById(id);
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;

  const P = { dbfs: -6, fin: 14.648e3, closed: true, noise: true, curve: true };
  const fft = makeFFT(N);
  const win = new Float64Array(N);
  for (let i = 0; i < N; i++) win[i] = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / N);
  const yBuf = new Float64Array(N), uBuf = new Float64Array(N), ipBuf = new Float32Array(N), inBuf = new Float32Array(N);
  const pow = new Float64Array(N / 2), avg = new Float64Array(N / 2);
  let wr = 0, total = 0, frames = 0, sndr = NaN;
  let n = 0;                       // absolute sample counter (input phase)
  const half = [{ v: 0, phi: 0.31, fl: 0 }, { v: 0, phi: 0.77, fl: 0 }];
  let spare = null;
  const gauss = () => {
    if (spare !== null) { const s = spare; spare = null; return s; }
    let u = 0, v = 0, r = 0;
    do { u = Math.random() * 2 - 1; v = Math.random() * 2 - 1; r = u * u + v * v; } while (r >= 1 || r === 0);
    const m = Math.sqrt((-2 * Math.log(r)) / r);
    spare = v * m;
    return u * m;
  };

  function reset() {
    half[0].v = half[1].v = 0; half[0].phi = 0.31; half[1].phi = 0.77; half[0].fl = half[1].fl = 0;
    wr = 0; total = 0; frames = 0; n = 0; avg.fill(0); sndr = NaN; snap = null;
  }

  function run(count) {
    const amp = 2 * FS_HALF * Math.pow(10, P.dbfs / 20);      // differential amplitude
    const bin = Math.max(1, Math.round((P.fin * N) / FS));
    const w = (2 * Math.PI * bin) / N;
    const c2 = P.curve ? C2 : 0, c3 = P.curve ? C3 : 0;
    for (let i = 0; i < count; i++, n++) {
      const u = amp * Math.sin(w * n);
      let yd = 0;
      for (let h = 0; h < 2; h++) {
        const s = half[h];
        const uh = (h ? -0.5 : 0.5) * u + (P.noise ? SIGMA_HALF * gauss() : 0);
        const x = P.closed ? (KC * s.v) / 3.5 : uh / FS_HALF;
        let inc = 3.5 + 3.5 * (x + c2 * x * x + c3 * x * x * x);
        if (inc < 0.05) inc = 0.05; else if (inc > 9.3) inc = 9.3;   // 9.3 steps = the 6.66 MHz clamp
        s.phi += inc;
        const fl = Math.floor(s.phi);
        let y = fl - s.fl;
        s.fl = fl;
        if (y > 7) y = 14 - y;                                       // XOR of 7 bits aliases past half a period
        if (s.phi > 1e6) { s.phi -= 1e6; s.fl -= 1e6; }
        if (P.closed) s.v += GI * (uh / RIN - ((y - 3.5) * VDD) / RD);
        yd += h ? -y : y;
        (h ? inBuf : ipBuf)[wr] = inc;
      }
      yBuf[wr] = yd; uBuf[wr] = u;
      wr = (wr + 1) & (N - 1);
    }
    total += count;
  }

  const lin = new Float64Array(N);
  function analyse() {
    if (total < N) return;
    for (let i = 0; i < N; i++) lin[i] = yBuf[(wr + i) & (N - 1)];
    fft(lin, win, pow);
    frames++;
    const a = frames === 1 ? 1 : Math.max(0.12, 1 / frames);
    for (let i = 0; i < N / 2; i++) avg[i] += (pow[i] - avg[i]) * a;
    const bin = Math.max(1, Math.round((P.fin * N) / FS));
    const hi = Math.floor((BW * N) / FS);
    let sig = 0, noise = 0;
    for (let i = 2; i <= hi; i++) (Math.abs(i - bin) <= 3 ? (sig += avg[i]) : (noise += avg[i]));
    sndr = 10 * Math.log10(sig / noise);
  }

  // ---- drawing ---------------------------------------------------------------------
  let snap = null, play = 0;
  const PRE = 160, BOX = 24;
  function takeSnap() {
    const bin = Math.max(1, Math.round((P.fin * N) / FS));
    const per = N / bin;
    const len = Math.round(Math.min(Math.max(per * 2, 500), 3200));
    const tot = len + PRE;
    const y = new Float32Array(tot), u = new Float32Array(tot), fp = new Float32Array(tot), fn = new Float32Array(tot);
    for (let i = 0; i < tot; i++) {
      const k = (wr - tot + i + N * 2) & (N - 1);
      y[i] = yBuf[k]; u[i] = uBuf[k]; fp[i] = ipBuf[k]; fn[i] = inBuf[k];
    }
    let f = Float32Array.from(y);                    // three cascaded moving averages
    for (let pass = 0; pass < 3; pass++) {
      const o = new Float32Array(tot);
      let acc = 0;
      for (let i = 0; i < tot; i++) { acc += f[i]; if (i >= BOX) acc -= f[i - BOX]; o[i] = acc / BOX; }
      f = o;
    }
    snap = { len, y, u, f, fp, fn, delay: Math.round((3 * (BOX - 1)) / 2) };
    play = 0;
  }

  function drawScope() {
    const { g, w, h } = fitCanvas(cScope);
    g.clearRect(0, 0, w, h);
    if (!snap) return;
    const padL = 8, padR = 8, mid = h / 2, sc = (h * 0.42) / 7.6;
    const X = (i) => padL + (i / (snap.len - 1)) * (w - padL - padR);
    g.strokeStyle = LINE; g.lineWidth = 1;
    g.beginPath();
    for (const lv of [-7, -3.5, 0, 3.5, 7]) { g.moveTo(padL, mid - lv * sc); g.lineTo(w - padR, mid - lv * sc); }
    g.stroke();
    // raw output code
    g.strokeStyle = 'rgba(91,140,255,0.55)'; g.lineWidth = 1;
    g.beginPath();
    const stepPx = (w - padL - padR) / snap.len;
    if (stepPx >= 0.6) {
      for (let i = 0; i < snap.len; i++) { const yy = mid - snap.y[PRE + i] * sc; if (i === 0) g.moveTo(X(i), yy); else { g.lineTo(X(i), g._py); g.lineTo(X(i), yy); } g._py = yy; }
    } else {
      for (let px = 0; px < w - padL - padR; px++) {            // min/max per pixel column
        const i0 = Math.floor(px / stepPx), i1 = Math.min(snap.len, Math.ceil((px + 1) / stepPx));
        let lo = 99, hi = -99;
        for (let i = i0; i < i1; i++) { const v = snap.y[PRE + i]; if (v < lo) lo = v; if (v > hi) hi = v; }
        g.moveTo(padL + px + 0.5, mid - lo * sc); g.lineTo(padL + px + 0.5, mid - hi * sc - 0.5);
      }
    }
    g.stroke();
    // filtered output
    g.strokeStyle = GOLD; g.lineWidth = 2; g.lineJoin = 'round';
    g.beginPath();
    for (let i = 0; i < snap.len; i++) {
      const v = snap.f[Math.min(PRE + i + snap.delay, snap.f.length - 1)];
      i ? g.lineTo(X(i), mid - v * sc) : g.moveTo(X(i), mid - v * sc);
    }
    g.stroke();
    // input
    g.strokeStyle = INK; g.lineWidth = 1.2; g.setLineDash([4, 4]);
    g.beginPath();
    for (let i = 0; i < snap.len; i += 2) {
      const v = (snap.u[PRE + i] / (2 * FS_HALF)) * 7;
      i ? g.lineTo(X(i), mid - v * sc) : g.moveTo(X(i), mid - v * sc);
    }
    g.stroke(); g.setLineDash([]);
    // playhead
    const px = X(play);
    g.strokeStyle = 'rgba(236,234,246,0.7)'; g.lineWidth = 1;
    g.beginPath(); g.moveTo(px, 6); g.lineTo(px, h - 6); g.stroke();
    g.font = '11px "Geist Mono", ui-monospace, monospace'; g.fillStyle = DIM; g.textBaseline = 'top';
    g.fillText(`${((snap.len / FS) * 1e6).toFixed(0)} µs`, w - padR - 46, h - 18);
    g.fillText('+7', padL + 2, mid - 7 * sc + 3);
    g.fillText('−7', padL + 2, mid + 7 * sc - 14);
  }

  const ring = [0, 0];
  function drawRings(dt) {
    const { g, w, h } = fitCanvas(cRings);
    g.clearRect(0, 0, w, h);
    if (!snap) return;
    const i = Math.min(PRE + Math.floor(play), snap.fp.length - 1);
    const inc = [snap.fp[i], snap.fn[i]];
    const horiz = w > h * 1.2;
    const R = Math.min(horiz ? w / 4 : w / 2, horiz ? h / 2 : h / 4) * 0.6;
    const names = ['P ring', 'N ring'], cols = [TEAL, PINK];
    for (let k = 0; k < 2; k++) {
      const cx = horiz ? w * (0.25 + 0.5 * k) : w / 2;
      const cy = horiz ? h * 0.46 : h * (0.25 + 0.5 * k) - 6;
      ring[k] = (ring[k] + dt * 0.55 * (inc[k] / 3.5)) % 1;
      const ph = ring[k] * 14;                       // 14 edge positions: rising pass, then falling pass
      g.strokeStyle = LINE; g.lineWidth = 1;
      g.beginPath(); g.arc(cx, cy, R, 0, Math.PI * 2); g.stroke();
      for (let s = 0; s < 7; s++) {
        const a = -Math.PI / 2 + (s / 7) * Math.PI * 2;
        const x = cx + R * Math.cos(a), y = cy + R * Math.sin(a);
        const d = (ph - s + 14) % 14;                // steps since the edge last passed this stage
        const high = d < 7;
        const glow = Math.max(0, 1 - (d % 7) / 2.2);
        g.beginPath(); g.arc(x, y, 5 + 4 * glow, 0, Math.PI * 2);
        g.fillStyle = high ? cols[k] : 'rgba(160,170,255,0.18)';
        g.globalAlpha = high ? 0.55 + 0.45 * glow : 1;
        g.fill(); g.globalAlpha = 1;
      }
      g.fillStyle = INK; g.textAlign = 'center'; g.textBaseline = 'middle';
      g.font = '600 15px "Geist Mono", ui-monospace, monospace';
      g.fillText(`${((inc[k] / 14) * FS / 1e6).toFixed(2)}`, cx, cy - 6);
      g.font = '11px "Geist Mono", ui-monospace, monospace'; g.fillStyle = DIM;
      g.fillText('MHz', cx, cy + 11);
      g.fillText(names[k], cx, cy + R + 20);
    }
    g.textAlign = 'left';
  }

  function drawSpec() {
    const { g, w, h } = fitCanvas(cSpec);
    g.clearRect(0, 0, w, h);
    const pl = 44, pr = 12, pt = 14, pb = 28;
    const f0 = 1e3, f1 = FS / 2, d0 = -170, d1 = 0;
    const X = (f) => pl + (Math.log10(f / f0) / Math.log10(f1 / f0)) * (w - pl - pr);
    const Y = (d) => pt + ((d1 - d) / (d1 - d0)) * (h - pt - pb);
    g.fillStyle = 'rgba(242,193,78,0.07)';
    g.fillRect(pl, pt, X(BW) - pl, h - pt - pb);
    g.font = '11px "Geist Mono", ui-monospace, monospace'; g.textBaseline = 'middle';
    g.strokeStyle = LINE; g.lineWidth = 1; g.fillStyle = DIM;
    g.beginPath();
    for (let d = -160; d <= 0; d += 40) { g.moveTo(pl, Y(d)); g.lineTo(w - pr, Y(d)); g.textAlign = 'right'; g.fillText(`${d}`, pl - 8, Y(d)); }
    g.textAlign = 'center';
    for (const [f, t] of [[1e3, '1 k'], [1e4, '10 k'], [1e5, '100 k'], [1e6, '1 M'], [5e6, '5 MHz']]) { g.moveTo(X(f), pt); g.lineTo(X(f), h - pb); g.fillText(t, Math.min(X(f), w - pr - 18), h - pb + 14); }
    g.stroke();
    g.textAlign = 'left'; g.fillStyle = GOLD;
    g.fillText('signal band, 50 kHz', pl + 8, pt + 10);
    g.fillStyle = DIM; g.textAlign = 'right'; g.fillText('dBFS', w - pr - 6, pt + 10); g.textAlign = 'left';
    if (!frames) return;
    // slope guide through the shaped noise at 1 MHz
    const slope = P.closed ? 40 : 20;
    const b1 = Math.round((1e6 * N) / FS);
    let ref = 0;
    for (let i = b1 - 80; i < b1 + 80; i++) ref += avg[i];
    const K = 10 * Math.log10(4 / (N * N * 0.25 * 49));         // amplitude 7 (differential full scale) = 0 dBFS
    const refDb = 10 * Math.log10(ref / 160) + K + 9;
    g.strokeStyle = 'rgba(236,234,246,0.5)'; g.setLineDash([5, 5]); g.lineWidth = 1;
    g.beginPath(); g.moveTo(X(4e4), Y(refDb + slope * Math.log10(4e4 / 1e6))); g.lineTo(X(2.5e6), Y(refDb + slope * Math.log10(2.5))); g.stroke();
    g.setLineDash([]);
    g.fillStyle = INK; g.fillText(`${slope} dB per decade`, X(2.2e5), Y(refDb + slope * Math.log10(0.22)) - 14);
    // spectrum, max per pixel column
    const grad = g.createLinearGradient(0, pt, 0, h - pb);
    grad.addColorStop(0, 'rgba(91,140,255,0.55)'); grad.addColorStop(1, 'rgba(91,140,255,0)');
    g.beginPath();
    let started = false, lastX = pl;
    const cols = Math.floor(w - pl - pr);
    for (let c = 0; c <= cols; c++) {
      const fa = f0 * Math.pow(f1 / f0, c / cols), fb = f0 * Math.pow(f1 / f0, (c + 1) / cols);
      const i0 = Math.max(1, Math.floor((fa * N) / FS)), i1 = Math.min(N / 2 - 1, Math.max(i0, Math.floor((fb * N) / FS)));
      let m = 0;
      for (let i = i0; i <= i1; i++) if (avg[i] > m) m = avg[i];
      const yy = Y(Math.max(d0, 10 * Math.log10(m + 1e-300) + K));
      lastX = pl + c;
      started ? g.lineTo(lastX, yy) : g.moveTo(lastX, yy);
      started = true;
    }
    g.strokeStyle = BLUE; g.lineWidth = 1.4; g.stroke();
    g.lineTo(lastX, h - pb); g.lineTo(pl, h - pb); g.closePath(); g.fillStyle = grad; g.fill();
  }

  function readouts() {
    const ok = Number.isFinite(sndr);
    out('sim-sndr').textContent = ok ? sndr.toFixed(1) : '…';
    out('sim-enob').textContent = ok ? ((sndr - 1.76) / 6.02).toFixed(1) : '…';
  }

  // ---- controls ----------------------------------------------------------------------
  const amp = out('sim-amp'), freq = out('sim-freq');
  const sync = () => {
    P.dbfs = parseFloat(amp.value);
    P.fin = Math.round((Math.pow(10, parseFloat(freq.value)) * N) / FS) * FS / N;
    out('sim-amp-val').textContent = `${P.dbfs.toFixed(1).replace('-', '−')} dBFS`;
    out('sim-freq-val').textContent = `${(P.fin / 1e3).toFixed(2)} kHz`;
    reset(); kick();
  };
  amp.addEventListener('input', sync);
  freq.addEventListener('input', sync);
  root.querySelectorAll('[data-loop]').forEach((b) => b.addEventListener('click', () => {
    P.closed = b.dataset.loop === 'closed';
    root.querySelectorAll('[data-loop]').forEach((o) => o.setAttribute('aria-pressed', String(o === b)));
    out('sim-order').textContent = P.closed ? 'second' : 'first';
    reset(); kick();
  }));
  for (const [id, key] of [['sim-noise', 'noise'], ['sim-curve', 'curve']]) {
    out(id).addEventListener('change', (e) => { P[key] = e.target.checked; reset(); kick(); });
  }

  // ---- loop ----------------------------------------------------------------------------
  let visible = false, raf = 0, last = 0, sinceFFT = 0;
  function frame(now) {
    raf = 0;
    const dt = Math.min((now - last) / 1000 || 0.016, 0.05);
    last = now;
    run(4096);
    if (++sinceFFT >= 3 || frames === 0) { analyse(); sinceFFT = 0; drawSpec(); readouts(); }
    if (!snap && total >= N) takeSnap();
    if (snap) {
      play += dt * (snap.len / 4.2);
      if (play >= snap.len - 1) takeSnap();
      drawScope(); drawRings(dt);
    }
    if (visible && !reduce) raf = requestAnimationFrame(frame);
  }
  function still() {                 // reduced motion: settle once, draw once
    run(N * 2);
    for (let i = 0; i < 10; i++) { run(N / 2); analyse(); }
    takeSnap(); play = snap.len * 0.4;
    drawSpec(); drawScope(); drawRings(0); readouts();
  }
  function kick() {
    if (reduce) still();
    else if (visible && !raf) raf = requestAnimationFrame(frame);
  }
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; if (visible) kick(); }, { rootMargin: '200px' }).observe(root);
  new ResizeObserver(() => { if (reduce && snap) { drawSpec(); drawScope(); drawRings(0); } }).observe(root);
  sync();
}
