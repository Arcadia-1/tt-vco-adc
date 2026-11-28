/**
 * Interactive 3D / 2D Real-GDS Silicon Layout Explorer (Three.js WebGL)
 * Renders 100% authentic Sky130A GDS geometry extracted from tt_um_arcadia1_vco_adc.gds
 * (8,474 core + 6,480 decap boxes across 9 physical layers, 161.0 x 225.76 um).
 * Features:
 *   - 3D orbit / tilt / zoom + 2D top-down drag-pan / zoom CAD mode
 *   - Real-time Sky130 metal stack Z-axis explosion slider
 *   - 10 functional block highlights with smooth camera focus, dim-context & specs
 *   - Per-layer metal visibility & 699x decap_12 filter
 *   - Optional calibrated high-resolution die-photo overlay & live (X, Y) um cursor readout
 */
import * as THREE from 'https://esm.sh/three@0.170.0';
import { OrbitControls } from 'https://esm.sh/three@0.170.0/examples/jsm/controls/OrbitControls.js';

export const BLOCKS = [
  {
    id: 'all',
    name: 'Full 1×2 Analog Tile',
    short: 'All Blocks',
    tag: '161×226 µm',
    color: '#38bdf8',
    eyebrow: 'TINY TAPEOUT SKY26E · SKY130A',
    desc: 'Mirrored pseudo-differential second-order closed-loop VCO ΔΣ ADC around vertical symmetry axis x = 73.60 µm. Zero Magic DRC, unique Netgen 1.5.324 LVS (54/54 pins), 16/16 TT precheck.',
    metrics: ['161.0 × 225.76 µm²', '70.1 dB Flat-PEX SNDR', '173.4 µW Core', '699× decap_12'],
    regions: [],
    focus: { x: 80.5, y: 112.9, dist3d: 265, dist2d: 285 },
  },
  {
    id: 'ota',
    name: 'Common-Centroid 5T OTA (P / N)',
    short: 'CC 5T OTA',
    tag: '48/3 µm',
    color: '#a78bfa',
    eyebrow: 'FRONT-END INTEGRATOR AMPLIFIER',
    desc: 'Interdigitated A A B B B B A A common-centroid NMOS input pair (48/3 µm, 18× gate area vs. S13) and PMOS load (16/2 µm, 4×) at 23 µA tail. Cuts BSIM4 1/f noise by +10.2 dB to 22.9 µVrms (79.3 dB ceiling) with Tian PM = 72.2°.',
    metrics: ['A₀ = 47.8 dB', 'GBW = 14.7 MHz', '22.9 µVrms (+10.2 dB)', 'PM = 72.2°'],
    regions: [
      { label: 'CC 5T OTA (N)', box: [26.38, 121.94, 54.63, 141.94] },
      { label: 'CC 5T OTA (P)', box: [92.57, 121.94, 120.82, 141.94] },
    ],
    focus: { x: 73.6, y: 132.0, dist3d: 155, dist2d: 170 },
  },
  {
    id: 'clamp',
    name: 'CLAMP_A5 Brick-Wall Clamp (P / N)',
    short: 'CLAMP_A5',
    tag: '5 FETs',
    color: '#f43f5e',
    eyebrow: 'ZERO-STATIC-POWER ANTI-LATCHUP',
    desc: 'All-standard-Vt 5-FET Miller-compensated active clamp (Msns 0.42/8, Mld1/2 2×0.42/8, Mpd 6/0.5, Mc 4/3) abutting each OTA. Leaks only 14–49 nA at 1.15 V (0.00 dB noise/HD3 penalty) while capping f_VCO ≤ 6.66 MHz below the 7.5 MHz aliasing latch-up wall.',
    metrics: ['5.5 pA static (0.0%)', 'f_max ≤ 6.66 MHz', '0.00 dB HD3 penalty', '4/4 PEX PASS'],
    regions: [
      { label: 'CLAMP_A5 (N)', box: [16.52, 121.94, 26.28, 141.94] },
      { label: 'CLAMP_A5 (P)', box: [120.92, 121.94, 130.68, 141.94] },
    ],
    focus: { x: 73.6, y: 132.0, dist3d: 175, dist2d: 195 },
  },
  {
    id: 'mim',
    name: '2.43 pF MIM Integrators (P / N)',
    short: 'MIM Caps',
    tag: '2×24×25 µm',
    color: '#f59e0b',
    eyebrow: 'CONTINUOUS-TIME LOOP CAPACITORS',
    desc: 'Two matched 24 × 25 µm² metal-3 MIM capacitors per half (C_int = 2.432 pF, f_int = 1.316 MHz) with NMOS reset switch X_Mr across vg–vctrl. Visible on the upper capm/met3/met4 stack.',
    metrics: ['C_int = 2.43 pF / half', 'f_int = 1.32 MHz', 'Metal-3 MIM (89/44)', 'X_Mr reset'],
    regions: [
      { label: 'MIM Int. (N)', box: [12.92, 95.14, 67.48, 120.54] },
      { label: 'MIM Int. (P)', box: [79.72, 95.14, 134.28, 120.54] },
    ],
    focus: { x: 73.6, y: 108.0, dist3d: 175, dist2d: 190 },
  },
  {
    id: 'rdac',
    name: '42-Strip+Dummy RDAC + Rin (P / N)',
    short: '7-Elem RDAC',
    tag: '1.04 MΩ×7',
    color: '#14b8a6',
    eyebrow: 'INTRINSIC BARREL-SHIFTED FEEDBACK DAC',
    desc: 'Seven 1.04 MΩ NRZ resistor elements (42 matched res_xhigh_po_0p35 strips + dummies) paired with identically pitched Rin = 49.7 kΩ. Absolute sheet resistance cancels in full-scale gain (±0.60 V diff), and VCO phase rotation provides 1st-order intrinsic DEM.',
    metrics: ['7 × 1.04 MΩ RDAC', 'Rin = 49.7 kΩ', 'Intrinsic 1st-order DEM', '±0.60 V Diff FS'],
    regions: [
      { label: 'RDAC + Rin (N)', box: [24.04, 149.80, 65.47, 185.81] },
      { label: 'RDAC + Rin (P)', box: [81.73, 149.80, 123.17, 185.81] },
    ],
    focus: { x: 73.6, y: 168.0, dist3d: 160, dist2d: 175 },
  },
  {
    id: 'rarray',
    name: 'CC VCO Bias R-Array (Shared)',
    short: 'VCO Bias R',
    tag: '229.7 kΩ',
    color: '#fb923c',
    eyebrow: 'COMMON-CENTROID DEGENERATION ARRAY',
    desc: 'Shared central D N₁ P₁ P₂ N₂ D common-centroid xhigh-poly resistor array (229.7 kΩ/half) degenerating both VCO V-to-I NMOS stages to cancel linear process gradients between P and N channels.',
    metrics: ['D N₁ P₁ P₂ N₂ D', '229.7 kΩ / half', 'Axis x = 73.6 µm', 'Matched Kvco'],
    regions: [
      { label: 'CC VCO R-Array', box: [70.58, 160.53, 76.62, 186.24] },
    ],
    focus: { x: 73.6, y: 173.4, dist3d: 65, dist2d: 72 },
  },
  {
    id: 'vco',
    name: '7-Stage Ring VCOs (P / N)',
    short: 'Ring VCOs',
    tag: '2.50 MHz',
    color: '#10b981',
    eyebrow: 'TIME-DOMAIN PHASE QUANTIZER',
    desc: 'Mirrored 7-stage current-starved ring oscillators with 4/1 µm V-to-I NMOS, 1:1 PMOS/NMOS current mirrors, and 1.4/2.86 µm MOS stage load caps inside guard rings. Closed loop locks both rings to fs/4 = 2.50 MHz across PVT.',
    metrics: ['7 Stages / Half', 'Lock = 2.50 MHz (fs/4)', 'Kvco = 8.48 MHz/V', '11.5 µW Total VCO'],
    regions: [
      { label: 'Ring VCO (N)', box: [47.59, 187.28, 72.60, 201.48] },
      { label: 'Ring VCO (P)', box: [74.60, 187.28, 99.61, 201.48] },
    ],
    focus: { x: 73.6, y: 194.4, dist3d: 88, dist2d: 96 },
  },
  {
    id: 'digital',
    name: 'Isolated Digital Banks (P / N)',
    short: 'DFF+XOR+BUF',
    tag: 'buf_4 iso',
    color: '#3b82f6',
    eyebrow: 'PHASE DIFFERENTIATOR & PIN ISOLATION',
    desc: 'Per half: 7 first-rank dfxtp_1 samplers driving internal dfxtp_1 + xor2_1 differentiators strictly on-chip, isolated from external 1–5 pF pin loads by 7 dedicated buf_4 buffers (+1 monitor buf_4). Cuts BSIM4 XOR glitch charge theft 19×–90× and rise/fall asymmetry 20×–215×.',
    metrics: ['2×(14 dfxtp_1 + 7 xor2_1)', '16× buf_4 Pin Iso', '19×–90× Less Glitch', '20×–215× Less Asym'],
    regions: [
      { label: 'Digital Bank (N)', box: [12.91, 199.48, 73.79, 219.00] },
      { label: 'Digital Bank (P)', box: [73.41, 199.48, 134.29, 219.00] },
    ],
    focus: { x: 73.6, y: 209.5, dist3d: 130, dist2d: 145 },
  },
  {
    id: 'conb',
    name: '8× conb_1 Tie-High (uio_oe[7:0])',
    short: '8× conb_1',
    tag: 'LVS 54/54',
    color: '#ec4899',
    eyebrow: 'CLEAN OUTPUT-ENABLE TIE CELLS',
    desc: 'Eight dedicated sky130_fd_sc_hd__conb_1 tie-high cells individually driving uio_oe[7:0] = 1.80 V, eliminating both gate-antenna violations and Netgen 1.5.324 top-level port-merger warnings.',
    metrics: ['8× conb_1 HI', 'uio_oe = 1.80 V', '0 Antenna', '54/54 Unique LVS'],
    regions: [
      { label: '8× conb_1', box: [35.69, 213.08, 42.05, 219.00] },
    ],
    focus: { x: 38.9, y: 216.0, dist3d: 48, dist2d: 52 },
  },
  {
    id: 'bias',
    name: 'Shared Vref, OTA Bias & Reset Inv.',
    short: 'Shared Bias',
    tag: '0.90 V / 24 µA',
    color: '#eab308',
    eyebrow: 'CENTRAL REFERENCE & BIAS ROW',
    desc: 'Shared 200 kΩ/200 kΩ resistive Vref = VDD/2 divider decoupled by 10×10 µm² NMOS cap XMc, OTA tail mirror (Rb = 42.3 kΩ into 8/2 µm XMb), and active-low rst_n inverter.',
    metrics: ['Vref = 0.90 V', 'I_bias = 24.4 µA', 'Common-mode cancels', 'rst_n inv_1'],
    regions: [
      { label: 'Shared Bias & Vref', box: [46.73, 79.20, 101.45, 94.04] },
    ],
    focus: { x: 74.1, y: 86.6, dist3d: 85, dist2d: 92 },
  },
  {
    id: 'decap',
    name: '699× decap_12 Supply Field',
    short: '699× decap_12',
    tag: '28 Rows',
    color: '#64748b',
    eyebrow: 'LOW-IMPEDANCE SUPPLY DECOUPLING',
    desc: '28 rows of sky130_fd_sc_hd__decap_12 standard cells stitched between vertical met4 VDPWR/VGND edge stripes to absorb 10 MHz digital switching currents and stiffen the shared analog rail.',
    metrics: ['699× decap_12', '28 Std-Cell Rows', 'Dual met4 Edge Rails', 'Toggleable Layer'],
    regions: [
      { label: '699× decap_12 Field', box: [5.0, 2.5, 155.5, 79.2] },
    ],
    focus: { x: 80.2, y: 40.8, dist3d: 175, dist2d: 195 },
  },
];

const LAYER_META = {
  met4:  { label: 'met4',  gds: '71/20', color: '#eab308', metal: 0.72, rough: 0.28 },
  capm:  { label: 'MIM',   gds: '89/44', color: '#f59e0b', metal: 0.55, rough: 0.25 },
  met3:  { label: 'met3',  gds: '70/20', color: '#14b8a6', metal: 0.65, rough: 0.30 },
  met2:  { label: 'met2',  gds: '69/20', color: '#ec4899', metal: 0.60, rough: 0.34 },
  met1:  { label: 'met1',  gds: '68/20', color: '#3b82f6', metal: 0.60, rough: 0.34 },
  li1:   { label: 'li1',   gds: '67/20', color: '#a855f7', metal: 0.45, rough: 0.42 },
  poly:  { label: 'poly',  gds: '66/20', color: '#ef4444', metal: 0.20, rough: 0.55 },
  diff:  { label: 'diff',  gds: '65/20', color: '#10b981', metal: 0.15, rough: 0.60 },
  nwell: { label: 'nwell', gds: '64/20', color: '#475569', metal: 0.05, rough: 0.85 },
};

export async function initLayoutExplorer(containerId, dataUrl = 'data/layout3d.json') {
  const wrap = document.getElementById(containerId);
  if (!wrap) return;

  const canvasWrap = document.getElementById('die-canvas-wrap');
  const labelLayer = document.getElementById('die-labels');
  const coordReadout = document.getElementById('hud-coords');
  const hoverReadout = document.getElementById('hud-hover');
  const infoCard = document.getElementById('stage-info-card');
  const blockListEl = document.getElementById('block-list');
  const layerGridEl = document.getElementById('layer-grid');

  // Load real GDS JSON
  let gds;
  try {
    const resp = await fetch(dataUrl);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    gds = await resp.json();
  } catch (err) {
    canvasWrap.innerHTML = `<div style="padding:32px;color:#94a3b8;font-family:var(--font-mono);font-size:13px;">Could not load real GDS geometry (${err.message}). Serve via HTTP (e.g. GitHub Pages or <code>python3 -m http.server</code>).</div>`;
    return;
  }

  const W = gds.meta.width_um;   // 161.0
  const H = gds.meta.height_um;  // 225.76
  const U = gds.meta.unit_um;    // 0.01 um
  const CX = W / 2;
  const CY = H / 2;

  // Map tile (x_um, y_um, z_um) -> Three.js (x - CX, z, -(y - CY)) so +X right, +Y up on top-down screen, +Z out of die
  const toWorld = (x, y, z = 0) => new THREE.Vector3(x - CX, z, -(y - CY));

  // Scene & Renderer
  const scene = new THREE.Scene();
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.12;
  canvasWrap.appendChild(renderer.domElement);

  const camera = new THREE.PerspectiveCamera(40, 1, 0.5, 2500);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.maxDistance = 680;
  controls.minDistance = 18;
  controls.maxPolarAngle = Math.PI * 0.495;

  // Studio-grade silicon lighting
  scene.add(new THREE.AmbientLight(0xdbeafe, 0.72));
  const dir1 = new THREE.DirectionalLight(0xffffff, 1.35);
  dir1.position.set(140, 260, 180);
  scene.add(dir1);
  const dir2 = new THREE.DirectionalLight(0x93c5fd, 0.55);
  dir2.position.set(-160, 140, -180);
  scene.add(dir2);

  // Silicon substrate die slab + subtle micron border + mirror axis line
  const subGeo = new THREE.BoxGeometry(W + 2, 1.2, H + 2);
  const subMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.9, metalness: 0.1 });
  const substrate = new THREE.Mesh(subGeo, subMat);
  substrate.position.set(0, -0.65, 0);
  scene.add(substrate);

  const dieBorder = new THREE.LineSegments(
    new THREE.EdgesGeometry(new THREE.BoxGeometry(W, 0.1, H)),
    new THREE.LineBasicMaterial({ color: 0x334155 })
  );
  dieBorder.position.set(0, 0.05, 0);
  scene.add(dieBorder);

  // Symmetry axis x = 73.60 um
  const axisPts = [toWorld(73.6, 82, 0.15), toWorld(73.6, 224, 0.15)];
  const axisLine = new THREE.Line(
    new THREE.BufferGeometry().setFromPoints(axisPts),
    new THREE.LineDashedMaterial({ color: 0x38bdf8, dashSize: 3, gapSize: 2, transparent: true, opacity: 0.45 })
  );
  axisLine.computeLineDistances();
  scene.add(axisLine);

  // Optional calibrated high-resolution die photo plane (exact 161.0 x 225.76 um!)
  const photoTex = new THREE.TextureLoader().load('assets/core_layout.jpg');
  photoTex.colorSpace = THREE.SRGBColorSpace;
  const photoPlane = new THREE.Mesh(
    new THREE.PlaneGeometry(W, H),
    new THREE.MeshBasicMaterial({ map: photoTex, transparent: true, opacity: 0.96 })
  );
  photoPlane.rotation.x = -Math.PI / 2;
  photoPlane.position.set(0, 0.12, 0);
  photoPlane.visible = false;
  scene.add(photoPlane);

  // Build GPU InstancedMesh per layer (core + decap separated!)
  const unitBox = new THREE.BoxGeometry(1, 1, 1);
  const layerMeshes = {}; // key -> { coreMesh, decapMesh, coreData, decapData, z0, z1, baseColor }
  const dummy = new THREE.Object3D();
  const cBase = new THREE.Color();
  const cDim = new THREE.Color();
  const cHi = new THREE.Color();

  let explodeFactor = 1.6;
  let showDecap = true;
  let showPhoto = false;
  let showLabels = true;
  let showPins = true;
  let viewMode = '3d';
  let activeBlockId = 'all';

  function buildInstanced(rects, z0, z1, meta, isDecap) {
    const count = rects.length / 4;
    if (count === 0) return null;
    const mat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      metalness: meta.metal,
      roughness: meta.rough,
      transparent: meta.label === 'nwell',
      opacity: meta.label === 'nwell' ? 0.35 : 1.0,
    });
    const mesh = new THREE.InstancedMesh(unitBox, mat, count);
    const col = new THREE.Color(meta.color);
    if (isDecap) col.multiplyScalar(0.62);
    const centers = new Float32Array(count * 2);
    const sizes = new Float32Array(count * 2);
    for (let i = 0; i < count; i++) {
      const x0 = rects[i * 4] * U;
      const y0 = rects[i * 4 + 1] * U;
      const x1 = rects[i * 4 + 2] * U;
      const y1 = rects[i * 4 + 3] * U;
      const cx = (x0 + x1) * 0.5;
      const cy = (y0 + y1) * 0.5;
      const sx = Math.max(x1 - x0, 0.08);
      const sy = Math.max(y1 - y0, 0.08);
      centers[i * 2] = cx;
      centers[i * 2 + 1] = cy;
      sizes[i * 2] = sx;
      sizes[i * 2 + 1] = sy;
      mesh.setColorAt(i, col);
    }
    mesh.instanceColor.needsUpdate = true;
    scene.add(mesh);
    return { mesh, count, centers, sizes, z0, z1, baseHex: meta.color, isDecap };
  }

  for (const l of gds.layers) {
    const meta = LAYER_META[l.key];
    if (!meta) continue;
    const coreObj = buildInstanced(l.core, l.z0, l.z1, meta, false);
    const decapObj = buildInstanced(l.decap, l.z0, l.z1, meta, true);
    layerMeshes[l.key] = { key: l.key, visible: true, coreObj, decapObj, z0: l.z0, z1: l.z1, meta };
  }

  function updateStackGeometry() {
    const zScale = viewMode === '2d' ? 0.25 : explodeFactor;
    for (const entry of Object.values(layerMeshes)) {
      for (const obj of [entry.coreObj, entry.decapObj]) {
        if (!obj) continue;
        const zMid = ((obj.z0 + obj.z1) * 0.5) * zScale + 0.08;
        const zH = Math.max((obj.z1 - obj.z0) * Math.min(zScale, 2.4), 0.12);
        for (let i = 0; i < obj.count; i++) {
          dummy.position.set(obj.centers[i * 2] - CX, zMid, -(obj.centers[i * 2 + 1] - CY));
          dummy.scale.set(obj.sizes[i * 2], zH, obj.sizes[i * 2 + 1]);
          dummy.updateMatrix();
          obj.mesh.setMatrixAt(i, dummy.matrix);
        }
        obj.mesh.instanceMatrix.needsUpdate = true;
      }
    }
    updateHighlightBoxes();
    updatePinPositions();
  }

  // Highlight 3D Wireframe + Translucent Floor Volume for Selected Functional Block
  const hiGroup = new THREE.Group();
  scene.add(hiGroup);

  function updateHighlightBoxes() {
    while (hiGroup.children.length) hiGroup.remove(hiGroup.children[0]);
    const blk = BLOCKS.find((b) => b.id === activeBlockId);
    if (!blk || blk.regions.length === 0) return;
    const zTop = 5.4 * (viewMode === '2d' ? 0.25 : explodeFactor) + 1.4;
    const col = new THREE.Color(blk.color);
    for (const r of blk.regions) {
      const [x0, y0, x1, y1] = r.box;
      const bw = x1 - x0;
      const bh = y1 - y0;
      const cx = (x0 + x1) * 0.5 - CX;
      const cz = -((y0 + y1) * 0.5 - CY);
      const boxGeo = new THREE.BoxGeometry(bw, zTop, bh);
      const fill = new THREE.Mesh(
        boxGeo,
        new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0.11, depthWrite: false })
      );
      fill.position.set(cx, zTop * 0.5, cz);
      hiGroup.add(fill);
      const edges = new THREE.LineSegments(
        new THREE.EdgesGeometry(boxGeo),
        new THREE.LineBasicMaterial({ color: col, transparent: true, opacity: 0.95 })
      );
      edges.position.set(cx, zTop * 0.5, cz);
      hiGroup.add(edges);
    }
  }

  // Pin markers (key active analog/digital pins: ua[0..1], clk, rst_n, uo_out[7], uio_out[0])
  const pinGroup = new THREE.Group();
  scene.add(pinGroup);
  const KEY_PINS = new Set(['ua[0]', 'ua[1]', 'clk', 'rst_n', 'uo_out[7]', 'uio_out[0]', 'uo_out[0]', 'uio_out[7]', 'VDPWR', 'VGND']);
  const pinMarkers = [];
  const pinGeo = new THREE.CylinderGeometry(0.95, 0.95, 1.0, 12);
  for (const p of gds.pins) {
    if (!KEY_PINS.has(p.name)) continue;
    const isAnalog = p.name.startsWith('ua');
    const isPower = p.name === 'VDPWR' || p.name === 'VGND';
    const col = isAnalog ? 0xf59e0b : (isPower ? 0xef4444 : 0x38bdf8);
    const m = new THREE.Mesh(pinGeo, new THREE.MeshBasicMaterial({ color: col }));
    pinGroup.add(m);
    pinMarkers.push({ mesh: m, pin: p });
  }
  function updatePinPositions() {
    const zTop = 5.35 * (viewMode === '2d' ? 0.25 : explodeFactor) + 0.7;
    for (const pm of pinMarkers) {
      pm.mesh.position.set(pm.pin.x - CX, zTop, -(pm.pin.y - CY));
    }
    pinGroup.visible = showPins;
  }

  // Color Highlighting across InstancedMeshes
  function applyBlockColors() {
    const blk = BLOCKS.find((b) => b.id === activeBlockId);
    const hasFilter = blk && blk.regions.length > 0;
    const pad = 0.6;
    for (const entry of Object.values(layerMeshes)) {
      for (const obj of [entry.coreObj, entry.decapObj]) {
        if (!obj) continue;
        cBase.set(obj.baseHex);
        if (obj.isDecap) cBase.multiplyScalar(0.62);
        cDim.copy(cBase).multiplyScalar(0.18).lerp(new THREE.Color(0x1e293b), 0.55);
        cHi.copy(cBase).lerp(new THREE.Color(0xffffff), 0.22);

        for (let i = 0; i < obj.count; i++) {
          if (!hasFilter) {
            obj.mesh.setColorAt(i, cBase);
          } else {
            const x = obj.centers[i * 2];
            const y = obj.centers[i * 2 + 1];
            let inside = false;
            for (const r of blk.regions) {
              const [x0, y0, x1, y1] = r.box;
              if (x >= x0 - pad && x <= x1 + pad && y >= y0 - pad && y <= y1 + pad) {
                inside = true;
                break;
              }
            }
            obj.mesh.setColorAt(i, inside ? cHi : cDim);
          }
        }
        obj.mesh.instanceColor.needsUpdate = true;
      }
    }
    updateHighlightBoxes();
    updateInfoCard(blk);
  }

  function syncVisibility() {
    for (const entry of Object.values(layerMeshes)) {
      if (entry.coreObj) entry.coreObj.mesh.visible = entry.visible && !showPhoto;
      if (entry.decapObj) entry.decapObj.mesh.visible = entry.visible && showDecap && !showPhoto;
    }
    photoPlane.visible = showPhoto;
    pinGroup.visible = showPins;
  }

  // Smooth Camera Animation
  let anim = null;
  function flyTo(tx, ty, dist, mode = viewMode, instant = false) {
    const target = toWorld(tx, ty, 2.0);
    const pos = mode === '2d'
      ? new THREE.Vector3(target.x, dist, target.z + 0.01)
      : new THREE.Vector3(target.x + dist * 0.42, dist * 0.72, target.z + dist * 0.62);
    if (instant) {
      camera.position.copy(pos);
      controls.target.copy(target);
      controls.update();
      anim = null;
      return;
    }
    anim = {
      t: 0,
      dur: 0.55,
      p0: camera.position.clone(),
      p1: pos,
      t0: controls.target.clone(),
      t1: target,
    };
  }

  function setViewMode(mode) {
    viewMode = mode;
    document.getElementById('btn-mode-3d')?.classList.toggle('active', mode === '3d');
    document.getElementById('btn-mode-2d')?.classList.toggle('active', mode === '2d');
    if (mode === '2d') {
      controls.enableRotate = false;
      controls.mouseButtons = { LEFT: THREE.MOUSE.PAN, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN };
      controls.touches = { ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_PAN };
    } else {
      controls.enableRotate = true;
      controls.mouseButtons = { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN };
      controls.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN };
    }
    updateStackGeometry();
    const blk = BLOCKS.find((b) => b.id === activeBlockId) || BLOCKS[0];
    flyTo(blk.focus.x, blk.focus.y, mode === '2d' ? blk.focus.dist2d : blk.focus.dist3d, mode);
  }

  function selectBlock(id, shouldFly = true) {
    activeBlockId = id;
    blockListEl.querySelectorAll('.block-btn').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.block === id);
    });
    applyBlockColors();
    const blk = BLOCKS.find((b) => b.id === id) || BLOCKS[0];
    if (shouldFly) {
      flyTo(blk.focus.x, blk.focus.y, viewMode === '2d' ? blk.focus.dist2d : blk.focus.dist3d, viewMode);
    }
    renderLabels();
  }

  function updateInfoCard(blk) {
    if (!blk || !infoCard) return;
    infoCard.innerHTML = `
      <div class="card-eyebrow" style="color:${blk.color}">${blk.eyebrow}</div>
      <h3>${blk.name}</h3>
      <p>${blk.desc}</p>
      <div class="stage-info-metrics">
        ${blk.metrics.map((m) => `<span class="stage-badge">${m}</span>`).join('')}
      </div>
    `;
  }

  // Build Sidebar UI: Functional Blocks
  blockListEl.innerHTML = BLOCKS.map((b) => `
    <button class="block-btn ${b.id === 'all' ? 'active' : ''}" data-block="${b.id}">
      <span class="block-swatch" style="background:${b.color}"></span>
      <span class="block-name">${b.short}</span>
      <span class="block-tag">${b.tag}</span>
    </button>
  `).join('');
  blockListEl.addEventListener('click', (e) => {
    const btn = e.target.closest('.block-btn');
    if (btn) selectBlock(btn.dataset.block, true);
  });

  // Build Sidebar UI: Sky130 Layers
  const layerOrder = ['met4', 'capm', 'met3', 'met2', 'met1', 'li1', 'poly', 'diff', 'nwell'];
  layerGridEl.innerHTML = layerOrder.map((k) => {
    const m = LAYER_META[k];
    return `<button class="layer-chip" data-layer="${k}" title="GDS ${m.gds}">
      <span class="layer-dot" style="background:${m.color}"></span>
      <span>${m.label}</span>
    </button>`;
  }).join('');
  layerGridEl.addEventListener('click', (e) => {
    const chip = e.target.closest('.layer-chip');
    if (!chip) return;
    const k = chip.dataset.layer;
    layerMeshes[k].visible = !layerMeshes[k].visible;
    chip.classList.toggle('off', !layerMeshes[k].visible);
    syncVisibility();
  });

  // Controls Wiring
  document.getElementById('btn-mode-3d')?.addEventListener('click', () => setViewMode('3d'));
  document.getElementById('btn-mode-2d')?.addEventListener('click', () => setViewMode('2d'));
  document.getElementById('btn-reset')?.addEventListener('click', () => selectBlock('all', true));

  const explodeSlider = document.getElementById('slider-explode');
  const explodeVal = document.getElementById('explode-val');
  explodeSlider?.addEventListener('input', () => {
    explodeFactor = parseFloat(explodeSlider.value);
    if (explodeVal) explodeVal.textContent = `${explodeFactor.toFixed(1)}×`;
    updateStackGeometry();
  });

  const btnDecap = document.getElementById('btn-toggle-decap');
  btnDecap?.addEventListener('click', () => {
    showDecap = !showDecap;
    btnDecap.classList.toggle('active', showDecap);
    syncVisibility();
  });
  const btnPhoto = document.getElementById('btn-toggle-photo');
  btnPhoto?.addEventListener('click', () => {
    showPhoto = !showPhoto;
    btnPhoto.classList.toggle('active', showPhoto);
    syncVisibility();
  });
  const btnLbls = document.getElementById('btn-toggle-labels');
  btnLbls?.addEventListener('click', () => {
    showLabels = !showLabels;
    btnLbls.classList.toggle('active', showLabels);
    labelLayer.style.display = showLabels ? 'block' : 'none';
  });
  const btnPins = document.getElementById('btn-toggle-pins');
  btnPins?.addEventListener('click', () => {
    showPins = !showPins;
    btnPins.classList.toggle('active', showPins);
    syncVisibility();
  });

  // Floating 3D-Projected Labels (well-spaced landmarks clear of HUD/info card)
  const labelNodes = [];
  function renderLabels() {
    labelLayer.innerHTML = '';
    labelNodes.length = 0;
    const targets = activeBlockId === 'all'
      ? [
          { id: 'digital', text: 'Digital Banks (dfxtp_1+buf_4)', x: 108.0, y: 215.5 },
          { id: 'vco',     text: '7-Stage Ring VCOs', x: 52.0, y: 193.0 },
          { id: 'rdac',    text: '42-Strip RDACs & Bias R', x: 102.0, y: 166.0 },
          { id: 'ota',     text: 'CC 5T OTA + CLAMP_A5', x: 52.0, y: 132.0 },
          { id: 'mim',     text: '2.43 pF MIM Caps', x: 112.0, y: 106.0 },
          { id: 'decap',   text: '699× decap_12 Field', x: 132.0, y: 58.0 },
        ]
      : (BLOCKS.find((b) => b.id === activeBlockId)?.regions || []).map((r) => ({
          id: activeBlockId,
          text: r.label,
          x: (r.box[0] + r.box[2]) * 0.5,
          y: (r.box[1] + r.box[3]) * 0.5,
        }));

    for (const t of targets) {
      const el = document.createElement('button');
      el.className = 'die-label' + (t.id === activeBlockId ? ' active' : '');
      el.textContent = t.text;
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        selectBlock(t.id, true);
      });
      labelLayer.appendChild(el);
      labelNodes.push({ el, x: t.x, y: t.y });
    }
  }

  // Hover Raycast on Die Plane for Live (X, Y) µm + Block Hit Test + Click-to-Select
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  const diePlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -1.0);
  const hitPt = new THREE.Vector3();
  let downPos = null;

  function blockAtPoint(x, y) {
    // Check specific small blocks first (conb, clamp, rarray, vco, ota, bias, mim, rdac, digital, decap)
    const order = ['conb', 'clamp', 'rarray', 'vco', 'ota', 'bias', 'mim', 'rdac', 'digital', 'decap'];
    for (const id of order) {
      const blk = BLOCKS.find((b) => b.id === id);
      for (const r of blk.regions) {
        const [x0, y0, x1, y1] = r.box;
        if (x >= x0 && x <= x1 && y >= y0 && y <= y1) return blk;
      }
    }
    return null;
  }

  function raycastDie(ev) {
    const rect = renderer.domElement.getBoundingClientRect();
    pointer.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    if (!raycaster.ray.intersectPlane(diePlane, hitPt)) return null;
    const x = hitPt.x + CX;
    const y = -hitPt.z + CY;
    if (x < 0 || x > W || y < 0 || y > H) return null;
    return { x, y };
  }

  renderer.domElement.addEventListener('pointermove', (ev) => {
    const pt = raycastDie(ev);
    if (!pt) {
      if (coordReadout) coordReadout.textContent = `161.0 × 225.8 µm`;
      if (hoverReadout) hoverReadout.textContent = '';
      return;
    }
    if (coordReadout) coordReadout.textContent = `X ${pt.x.toFixed(1)} · Y ${pt.y.toFixed(1)} µm`;
    const blk = blockAtPoint(pt.x, pt.y);
    if (hoverReadout) hoverReadout.textContent = blk ? blk.short : '';
  });

  renderer.domElement.addEventListener('pointerdown', (ev) => {
    downPos = { x: ev.clientX, y: ev.clientY };
    anim = null; // user takes manual control
  });
  renderer.domElement.addEventListener('pointerup', (ev) => {
    if (!downPos) return;
    const dist = Math.hypot(ev.clientX - downPos.x, ev.clientY - downPos.y);
    downPos = null;
    if (dist > 5) return; // was a drag, not a click
    const pt = raycastDie(ev);
    if (!pt) return;
    const blk = blockAtPoint(pt.x, pt.y);
    if (blk) selectBlock(blk.id, true);
  });

  // Resize Handling
  function resize() {
    const w = canvasWrap.clientWidth || 720;
    const h = canvasWrap.clientHeight || 620;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
  }
  const ro = new ResizeObserver(resize);
  ro.observe(canvasWrap);
  resize();

  // Initialize Stack, Labels & Camera
  updateStackGeometry();
  syncVisibility();
  applyBlockColors();
  renderLabels();
  flyTo(80.5, 118.0, 265, '3d', true);

  // Render Loop
  let lastT = performance.now();
  const projV = new THREE.Vector3();
  function tick(now) {
    requestAnimationFrame(tick);
    const dt = Math.min((now - lastT) / 1000, 0.05);
    lastT = now;

    if (anim) {
      anim.t += dt / anim.dur;
      const u = Math.min(anim.t, 1);
      const ease = 1 - Math.pow(1 - u, 3);
      camera.position.lerpVectors(anim.p0, anim.p1, ease);
      controls.target.lerpVectors(anim.t0, anim.t1, ease);
      if (u >= 1) anim = null;
    }

    controls.update();
    renderer.render(scene, camera);

    // Project 3D labels (clamped inside canvas bounds to prevent right/left edge clipping)
    if (showLabels) {
      const cw = canvasWrap.clientWidth;
      const ch = canvasWrap.clientHeight;
      const zLbl = 5.5 * (viewMode === '2d' ? 0.25 : explodeFactor) + 2.5;
      for (const n of labelNodes) {
        projV.set(n.x - CX, zLbl, -(n.y - CY)).project(camera);
        if (projV.z > 1) {
          n.el.style.display = 'none';
        } else {
          const sx = (projV.x * 0.5 + 0.5) * cw;
          const sy = (-projV.y * 0.5 + 0.5) * ch;
          const halfW = Math.max(48, (n.el.offsetWidth || 96) * 0.52);
          n.el.style.display = 'block';
          n.el.style.left = `${Math.max(halfW + 8, Math.min(cw - halfW - 8, sx))}px`;
          n.el.style.top = `${Math.max(52, Math.min(ch - 26, sy))}px`;
        }
      }
    }
  }
  requestAnimationFrame(tick);

  // Expose quick focus helper for external links (e.g. URL hash #block=ota)
  const hashBlock = new URLSearchParams(location.hash.replace(/^#/, '')).get('block');
  if (hashBlock && BLOCKS.some((b) => b.id === hashBlock)) {
    setTimeout(() => selectBlock(hashBlock, true), 200);
  }
  return { selectBlock, setViewMode };
}
