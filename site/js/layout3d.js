/**
 * Real-GDS chip stage (Three.js).
 * Renders the 14,954 rectangles of tt_um_arcadia1_vco_adc.gds as instanced boxes on
 * nine Sky130A layers. One stage serves three modes:
 *   - hero:    layers are deposited bottom-up on load, the die turns slowly
 *   - tour:    the page scroll drives named scenes (camera, highlight, stack explode)
 *   - explore: full orbit / pan / top-down controls, block and layer filters
 */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const BG = 0x06071a;

export const BLOCKS = [
  {
    id: 'all',
    name: 'Full 1×2 analog tile',
    short: 'Whole tile',
    tag: '161 × 226 µm',
    color: '#8fb4ff',
    desc: 'Two mirrored half-circuits around the symmetry axis at x = 73.60 µm. Zero Magic DRC errors, unique Netgen LVS match on all 54 pins, 16 of 16 Tiny Tapeout precheck items.',
    metrics: ['161.0 × 225.76 µm²', '70.1 dB flat-PEX SNDR', '173.4 µW core', '699 decap cells'],
    regions: [],
    focus: { x: 80.5, y: 112.9, dist3d: 380, dist2d: 330 },
  },
  {
    id: 'rdac',
    name: 'Input resistor and 7-element resistor DAC',
    short: 'Rin + RDAC',
    tag: '7 × 1.04 MΩ',
    color: '#3fd1c1',
    desc: 'Seven 1.04 MΩ feedback elements built from 42 matched xhigh-poly strips plus dummies, next to a 49.7 kΩ input resistor on the same pitch. Sheet resistance cancels out of the full-scale gain, and the rotating VCO phase scrambles element mismatch.',
    metrics: ['7 × 1.04 MΩ', 'Rin = 49.7 kΩ', '±0.60 V differential FS', 'First-order DEM'],
    regions: [
      { label: 'RDAC + Rin, N', box: [24.04, 149.80, 65.47, 185.81] },
      { label: 'RDAC + Rin, P', box: [81.73, 149.80, 123.17, 185.81] },
    ],
    focus: { x: 73.6, y: 168.0, dist3d: 170, dist2d: 175 },
    cam: { az: 0.55, el: 0.72 },
    explode: 1.6,
  },
  {
    id: 'ota',
    name: 'Common-centroid 5T OTA',
    short: '5T OTA',
    tag: '48/3 µm',
    color: '#a98bff',
    desc: 'NMOS input pair of 48/3 µm interdigitated A A B B B B A A, PMOS load of 16/2 µm, 23 µA tail. Input-referred noise is 22.9 µVrms over 0.1 to 50 kHz.',
    metrics: ['A₀ = 47.8 dB', 'GBW = 14.7 MHz', 'PM = 72.2°', '22.9 µVrms'],
    regions: [
      { label: 'OTA, N', box: [26.38, 121.94, 54.63, 141.94] },
      { label: 'OTA, P', box: [92.57, 121.94, 120.82, 141.94] },
    ],
    focus: { x: 73.6, y: 132.0, dist3d: 160, dist2d: 170 },
    cam: { az: -0.45, el: 0.66 },
    explode: 1.6,
  },
  {
    id: 'mim',
    name: '2.43 pF MIM integration capacitors',
    short: 'MIM caps',
    tag: '2 × 24 × 25 µm',
    color: '#f2c14e',
    desc: 'Two 24 × 25 µm² MIM capacitors per half between metal 3 and metal 4, 2.432 pF in total, with an NMOS reset switch across them. Unity-gain frequency of the integrator is 1.316 MHz.',
    metrics: ['2.43 pF per half', 'f_int = 1.32 MHz', 'MIM layer 89/44', 'NMOS reset'],
    regions: [
      { label: 'MIM, N', box: [12.92, 95.14, 67.48, 120.54] },
      { label: 'MIM, P', box: [79.72, 95.14, 134.28, 120.54] },
    ],
    focus: { x: 73.6, y: 108.0, dist3d: 190, dist2d: 190 },
    cam: { az: 0.35, el: 0.42 },
    explode: 5.2,
  },
  {
    id: 'clamp',
    name: 'Control-voltage clamp',
    short: 'Clamp',
    tag: '5 FETs',
    color: '#ff6b5e',
    desc: 'Five standard-Vt transistors with Miller compensation, abutting each OTA. Leakage is 14 to 49 nA at 1.15 V, and the ring frequency can never exceed 6.66 MHz, safely under the 7.5 MHz point where the XOR detector aliases and the loop latches.',
    metrics: ['f_VCO ≤ 6.66 MHz', '14–49 nA leakage', '0.00 dB noise penalty', '4 of 4 PEX stress runs'],
    regions: [
      { label: 'Clamp, N', box: [16.52, 121.94, 26.28, 141.94] },
      { label: 'Clamp, P', box: [120.92, 121.94, 130.68, 141.94] },
    ],
    focus: { x: 73.6, y: 132.0, dist3d: 200, dist2d: 195 },
    cam: { az: 0.1, el: 0.9 },
    explode: 1.6,
  },
  {
    id: 'vco',
    name: '7-stage current-starved ring VCOs',
    short: 'Ring VCOs',
    tag: '2.50 MHz',
    color: '#3ddc84',
    desc: 'Mirrored seven-stage rings, each with a 4/1 µm V-to-I NMOS, 1:1 current mirrors and 1.4/2.86 µm MOS load capacitors inside guard rings. The loop holds both at fs/4 = 2.50 MHz at mid-scale.',
    metrics: ['7 stages per half', 'Lock at 2.50 MHz', 'K_VCO = 8.48 MHz/V', '11.5 µW for both'],
    regions: [
      { label: 'Ring VCO, N', box: [47.59, 187.28, 72.60, 201.48] },
      { label: 'Ring VCO, P', box: [74.60, 187.28, 99.61, 201.48] },
    ],
    focus: { x: 73.6, y: 194.4, dist3d: 105, dist2d: 96 },
    cam: { az: -0.6, el: 0.58 },
    explode: 2.2,
  },
  {
    id: 'digital',
    name: 'Samplers, XOR differentiators, output buffers',
    short: 'DFF + XOR + BUF',
    tag: 'buf_4 isolation',
    color: '#5b8cff',
    desc: 'Per half: seven dfxtp_1 samplers, seven dfxtp_1 + xor2_1 differentiators that stay on-chip, and seven buf_4 output buffers plus one for the monitor. The buffers keep 1 to 5 pF of pad load off the feedback path.',
    metrics: ['2 × (14 DFF + 7 XOR)', '16 buf_4', '≤ 0.16 ns glitch', '0.029 ns asymmetry'],
    regions: [
      { label: 'Digital, N', box: [12.91, 199.48, 73.79, 219.00] },
      { label: 'Digital, P', box: [73.41, 199.48, 134.29, 219.00] },
    ],
    focus: { x: 73.6, y: 209.5, dist3d: 150, dist2d: 145 },
    cam: { az: 0.5, el: 0.8 },
    explode: 1.6,
  },
  {
    id: 'rarray',
    name: 'Common-centroid VCO bias resistors',
    short: 'VCO bias R',
    tag: '229.7 kΩ',
    color: '#ff9f5a',
    desc: 'A shared D N₁ P₁ P₂ N₂ D xhigh-poly array on the symmetry axis, 229.7 kΩ per half, degenerating both V-to-I stages so linear process gradients hit the P and N rings equally.',
    metrics: ['D N₁ P₁ P₂ N₂ D', '229.7 kΩ per half', 'On the axis', 'Matched K_VCO'],
    regions: [{ label: 'VCO bias R', box: [70.58, 160.53, 76.62, 186.24] }],
    focus: { x: 73.6, y: 173.4, dist3d: 80, dist2d: 72 },
  },
  {
    id: 'bias',
    name: 'Shared reference, OTA bias, reset inverter',
    short: 'Bias row',
    tag: '0.90 V',
    color: '#ffd166',
    desc: 'A 200 kΩ / 200 kΩ divider makes Vref = VDD/2, decoupled by a 10 × 10 µm² NMOS capacitor. A 42.3 kΩ resistor into an 8/2 µm mirror sets the OTA tail current. The rst_n inverter sits here too.',
    metrics: ['Vref = 0.90 V', 'I_bias = 24.4 µA', 'Shared by both halves', 'rst_n inv_1'],
    regions: [{ label: 'Bias row', box: [46.73, 79.20, 101.45, 94.04] }],
    focus: { x: 74.1, y: 86.6, dist3d: 100, dist2d: 92 },
  },
  {
    id: 'conb',
    name: 'Eight conb_1 tie-high cells',
    short: '8 × conb_1',
    tag: 'uio_oe',
    color: '#ff5fa8',
    desc: 'One sky130_fd_sc_hd__conb_1 per uio_oe bit, each tied to 1.80 V. Separate cells avoid gate-antenna violations and the port-merge warnings Netgen raises when one cell drives all eight.',
    metrics: ['uio_oe[7:0] = 1.80 V', '0 antenna violations', '54 of 54 pins unique'],
    regions: [{ label: '8 × conb_1', box: [35.69, 213.08, 42.05, 219.00] }],
    focus: { x: 38.9, y: 216.0, dist3d: 60, dist2d: 52 },
  },
  {
    id: 'decap',
    name: 'Supply decoupling field',
    short: '699 × decap_12',
    tag: '28 rows',
    color: '#7f8cb8',
    desc: '28 rows of sky130_fd_sc_hd__decap_12 between the vertical metal-4 supply stripes. They absorb the 10 MHz switching current of the digital bank and stiffen the rail the analog half shares.',
    metrics: ['699 × decap_12', '28 standard-cell rows', 'Metal-4 edge rails'],
    regions: [{ label: 'Decap field', box: [5.0, 2.5, 155.5, 79.2] }],
    focus: { x: 80.2, y: 40.8, dist3d: 190, dist2d: 195 },
  },
];

/** Scroll-tour scenes. `block` picks focus + highlight; the rest overrides the block defaults. */
const SCENES = {
  hero:  { block: 'all', az: -0.62, el: 0.56, dist: 390, explode: 3.4, shift: [0.15, -0.17], spin: true, y: 118 },
  rdac: {}, ota: {}, mim: {}, clamp: {}, vco: {}, digital: {},
  outro: { block: 'all', az: 0.0, el: 1.18, dist: 330, explode: 1.6, shift: [0.2, 0] },
};

const LAYER_META = {
  met4:  { label: 'met4',  color: '#f2c14e', metal: 0.9,  rough: 0.32 },
  capm:  { label: 'MIM',   color: '#ff9f5a', metal: 0.85, rough: 0.28 },
  met3:  { label: 'met3',  color: '#3fd1c1', metal: 0.85, rough: 0.34 },
  met2:  { label: 'met2',  color: '#ff5fa8', metal: 0.8,  rough: 0.36 },
  met1:  { label: 'met1',  color: '#5b8cff', metal: 0.8,  rough: 0.36 },
  li1:   { label: 'li1',   color: '#a98bff', metal: 0.6,  rough: 0.45 },
  poly:  { label: 'poly',  color: '#ff6b5e', metal: 0.25, rough: 0.55 },
  diff:  { label: 'diff',  color: '#3ddc84', metal: 0.2,  rough: 0.6 },
  nwell: { label: 'nwell', color: '#55608f', metal: 0.05, rough: 0.85 },
};
const LAYER_ORDER = ['met4', 'capm', 'met3', 'met2', 'met1', 'li1', 'poly', 'diff', 'nwell'];
const STACK_TOP = 5.29;
const BASE_EXPLODE = 1.6;

const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const easeOut = (t) => 1 - Math.pow(1 - t, 3);
const $ = (id) => document.getElementById(id);

export async function initChip(dataUrl = 'data/layout3d.json') {
  const root = $('chip');
  const canvasWrap = $('chip-canvas');
  const labelLayer = $('chip-labels');
  const ticker = $('chip-ticker');
  const coordReadout = $('hud-coords');
  const infoCard = $('info-card');
  const blockListEl = $('block-list');
  const layerGridEl = $('layer-grid');
  if (!root || !canvasWrap) return null;

  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const coarse = matchMedia('(pointer: coarse)').matches;

  const fail = (msg) => {
    root.classList.add('no-webgl');
    if (ticker) ticker.textContent = msg;
    return null;
  };

  let gds;
  try {
    const resp = await fetch(dataUrl);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    gds = await resp.json();
  } catch (err) {
    return fail(`Layout data did not load (${err.message}). Serve the site over HTTP.`);
  }

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: false, powerPreference: 'high-performance' });
  } catch (err) {
    return fail('WebGL is not available, showing a still image of the layout.');
  }

  const W = gds.meta.width_um;
  const H = gds.meta.height_um;
  const U = gds.meta.unit_um;
  const CX = W / 2;
  const CY = H / 2;
  // tile (x, y, z) µm -> world: +X right, +Y out of the die, tile +y away from the viewer
  const toWorld = (x, y, z = 0) => new THREE.Vector3(x - CX, z, -(y - CY));

  const dpr = Math.min(window.devicePixelRatio || 1, coarse ? 1.5 : 2);
  renderer.setPixelRatio(dpr);
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.toneMappingExposure = 1.05;
  canvasWrap.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(BG);
  scene.fog = new THREE.FogExp2(BG, 0.00105);
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.75;

  const camera = new THREE.PerspectiveCamera(30, 1, 1, 6000);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.screenSpacePanning = false;
  controls.panSpeed = 1.2;
  controls.rotateSpeed = 0.8;
  controls.maxDistance = 900;
  controls.minDistance = 18;
  controls.maxPolarAngle = Math.PI * 0.495;
  controls.autoRotateSpeed = 0.45;

  const key = new THREE.DirectionalLight(0xfff1dc, 2.1);
  key.position.set(140, 260, 180);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0x7aa2ff, 1.3);
  rim.position.set(-200, 120, -220);
  scene.add(rim);
  scene.add(new THREE.AmbientLight(0x8090ff, 0.25));

  // The die: a polished slab with thin-film interference, like a wafer under white light.
  const slab = new THREE.Mesh(
    new THREE.BoxGeometry(W + 3, 2.4, H + 3),
    new THREE.MeshPhysicalMaterial({
      color: 0x070818, metalness: 0.85, roughness: 0.3, envMapIntensity: 0.55,
      iridescence: 0.7, iridescenceIOR: 1.6, iridescenceThicknessRange: [240, 520],
    })
  );
  slab.position.y = -1.25;
  scene.add(slab);

  // Neighbouring tiles of the shuttle, fading into fog.
  {
    const pts = [];
    const gx = W + 14, gy = H + 14;
    for (let i = -9; i <= 9; i++) {
      for (let j = -6; j <= 6; j++) {
        if (i === 0 && j === 0) continue;
        const x0 = i * gx - W / 2, x1 = x0 + W, z0 = j * gy - H / 2, z1 = z0 + H;
        pts.push(x0, 0, z0, x1, 0, z0, x1, 0, z0, x1, 0, z1, x1, 0, z1, x0, 0, z1, x0, 0, z1, x0, 0, z0);
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
    const grid = new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: 0x2a3270, transparent: true, opacity: 0.7 }));
    grid.position.y = -2.4;
    scene.add(grid);
    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(9000, 9000),
      new THREE.MeshStandardMaterial({ color: 0x05061a, metalness: 0.9, roughness: 0.45 })
    );
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = -2.5;
    scene.add(floor);
  }

  const photoTex = new THREE.TextureLoader().load('assets/core_layout.jpg');
  photoTex.colorSpace = THREE.SRGBColorSpace;
  const photoPlane = new THREE.Mesh(
    new THREE.PlaneGeometry(W, H),
    new THREE.MeshBasicMaterial({ map: photoTex })
  );
  photoPlane.rotation.x = -Math.PI / 2;
  photoPlane.position.y = 0.12;
  photoPlane.visible = false;
  scene.add(photoPlane);

  // ---- layers as instanced boxes -------------------------------------------------
  const unitBox = new THREE.BoxGeometry(1, 1, 1);
  const layers = {};
  const dummy = new THREE.Object3D();

  function buildInstanced(rects, l, meta, isDecap) {
    const count = rects.length / 4;
    if (!count) return null;
    const isWell = l.key === 'nwell';
    const mat = new THREE.MeshStandardMaterial({
      color: 0xffffff, metalness: meta.metal, roughness: meta.rough,
      transparent: true, opacity: 0,
    });
    const mesh = new THREE.InstancedMesh(unitBox, mat, count);
    const centers = new Float32Array(count * 2);
    const zMid = (l.z0 + l.z1) * 0.5;
    const zH = Math.max((l.z1 - l.z0) * BASE_EXPLODE, 0.14);
    const col = new THREE.Color(meta.color);
    if (isDecap) col.multiplyScalar(0.5);
    for (let i = 0; i < count; i++) {
      const x0 = rects[i * 4] * U, y0 = rects[i * 4 + 1] * U;
      const x1 = rects[i * 4 + 2] * U, y1 = rects[i * 4 + 3] * U;
      const cx = (x0 + x1) * 0.5, cy = (y0 + y1) * 0.5;
      centers[i * 2] = cx;
      centers[i * 2 + 1] = cy;
      dummy.position.set(cx - CX, zMid, -(cy - CY));
      dummy.scale.set(Math.max(x1 - x0, 0.08), zH, Math.max(y1 - y0, 0.08));
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
      mesh.setColorAt(i, col);
    }
    mesh.instanceMatrix.needsUpdate = true;
    mesh.instanceColor.needsUpdate = true;
    mesh.frustumCulled = false;
    scene.add(mesh);
    return { mesh, mat, count, centers, zMid, zH, base: col.clone(), isDecap, fullOpacity: isWell ? 0.4 : 1 };
  }

  gds.layers.forEach((l, i) => {
    const meta = LAYER_META[l.key];
    if (!meta) return;
    layers[l.key] = {
      key: l.key, gdsNum: l.gds, index: i, visible: true, meta, reveal: 0,
      objs: [buildInstanced(l.core, l, meta, false), buildInstanced(l.decap, l, meta, true)].filter(Boolean),
    };
  });
  const layerList = Object.values(layers).sort((a, b) => a.index - b.index);

  // Contacts and vias: unit-height pillars, stretched per frame to span the gap
  // between the two layers they join, so they stay connected as the stack separates.
  const VIA_SPAN = { licon: ['diff', 'li1'], mcon: ['li1', 'met1'], via: ['met1', 'met2'], via2: ['met2', 'met3'], via3: ['met3', 'met4'] };
  const viaList = [];
  let showVias = true;
  function buildVias(rects, v, isDecap) {
    const count = rects.length / 4;
    if (!count) return null;
    const mat = new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 0.9, roughness: 0.3, transparent: true, opacity: 0 });
    const mesh = new THREE.InstancedMesh(unitBox, mat, count);
    const centers = new Float32Array(count * 2);
    const col = new THREE.Color(isDecap ? '#6f7699' : '#e4e7ff');
    for (let i = 0; i < count; i++) {
      const x0 = rects[i * 4] * U, y0 = rects[i * 4 + 1] * U, x1 = rects[i * 4 + 2] * U, y1 = rects[i * 4 + 3] * U;
      const cx = (x0 + x1) * 0.5, cy = (y0 + y1) * 0.5;
      centers[i * 2] = cx;
      centers[i * 2 + 1] = cy;
      dummy.position.set(cx - CX, 0, -(cy - CY));
      dummy.scale.set(x1 - x0, 1, y1 - y0);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
      mesh.setColorAt(i, col);
    }
    mesh.instanceMatrix.needsUpdate = true;
    mesh.instanceColor.needsUpdate = true;
    mesh.frustumCulled = false;
    scene.add(mesh);
    return { mesh, mat, count, centers, base: col.clone(), isDecap, fullOpacity: 1 };
  }
  for (const v of gds.vias || []) {
    const [lo, hi] = (VIA_SPAN[v.key] || []).map((k) => layers[k]);
    if (!lo || !hi) continue;
    let core = v.core;
    if (v.key === 'via3' && layers.capm) {
      // over a MIM capacitor via3 lands on the top plate, not on metal 3
      const caps = gds.layers.find((l) => l.key === 'capm').core;
      const onCap = [], rest = [];
      for (let i = 0; i < core.length; i += 4) {
        const cx = (core[i] + core[i + 2]) / 2, cy = (core[i + 1] + core[i + 3]) / 2;
        let hit = false;
        for (let j = 0; j < caps.length; j += 4) if (cx > caps[j] && cx < caps[j + 2] && cy > caps[j + 1] && cy < caps[j + 3]) { hit = true; break; }
        (hit ? onCap : rest).push(core[i], core[i + 1], core[i + 2], core[i + 3]);
      }
      core = rest;
      viaList.push({ key: 'via3-mim', lo: layers.capm, hi, objs: [buildVias(onCap, v, false)].filter(Boolean) });
    }
    viaList.push({ key: v.key, lo, hi, objs: [buildVias(core, v, false), buildVias(v.decap, v, true)].filter(Boolean) });
  }
  const paintList = [...layerList, ...viaList];

  // ---- state -----------------------------------------------------------------------
  let explode = 3.4;          // current stack explode factor
  let explodeTarget = 3.4;
  let shift = [0, 0];         // principal-point shift as a fraction of the viewport
  let shiftTarget = [0, 0];
  let mode = 'tour';          // 'tour' | 'explore'
  let viewMode = '3d';        // '3d' | '2d' (explore only)
  let dragTool = 'orbit';
  let spacePan = false;
  let activeBlock = 'all';
  let sceneName = '';
  let showDecap = true, showPhoto = false, showLabels = true, showPins = true;
  let dirtyUntil = 0;
  let onScreen = true;
  const touch = () => { dirtyUntil = performance.now() + 900; };

  function applyStack() {
    for (const L of layerList) {
      const r = L.reveal;
      const drop = (1 - easeOut(r)) * 46;
      for (const o of L.objs) {
        o.mesh.position.y = o.zMid * (explode - 1) + 0.08 + drop;
        o.mat.opacity = o.fullOpacity * Math.min(1, r * 1.6);
        const opaque = r >= 1 && o.fullOpacity === 1;
        if (o.mat.transparent === opaque) { o.mat.transparent = !opaque; o.mat.depthWrite = true; o.mat.needsUpdate = true; }
      }
    }
    for (const V of viaList) {
      const a = V.lo.objs[0], b = V.hi.objs[0];
      const bot = a.mesh.position.y + a.zMid + a.zH * 0.5 - 0.02;
      const top = b.mesh.position.y + b.zMid - b.zH * 0.5 + 0.02;
      const r = Math.min(V.lo.reveal, V.hi.reveal);
      for (const o of V.objs) {
        o.mesh.scale.y = Math.max(top - bot, 0.01);
        o.mesh.position.y = (top + bot) * 0.5;
        o.mat.opacity = r;
        if (o.mat.transparent === (r >= 1)) { o.mat.transparent = r < 1; o.mat.needsUpdate = true; }
      }
    }
    const zTop = STACK_TOP * explode;
    hiGroup.scale.y = zTop + 2;
    pinGroup.position.y = zTop + 1.2;
  }

  // ---- block highlight -----------------------------------------------------------
  const hiGroup = new THREE.Group();
  scene.add(hiGroup);
  const unitEdges = new THREE.EdgesGeometry(new THREE.BoxGeometry(1, 1, 1));
  const cA = new THREE.Color(), cB = new THREE.Color(), cBg = new THREE.Color(0x0b0e2a);

  function selectBlock(id) {
    const blk = BLOCKS.find((b) => b.id === id) || BLOCKS[0];
    activeBlock = blk.id;
    const filter = blk.regions.length > 0;
    const pad = 0.6;
    for (const L of paintList) {
      for (const o of L.objs) {
        cA.copy(o.base).lerp(new THREE.Color(0xffffff), 0.12);
        cB.copy(o.base).multiplyScalar(0.13).lerp(cBg, 0.5);
        for (let i = 0; i < o.count; i++) {
          let c = o.base;
          if (filter) {
            const x = o.centers[i * 2], y = o.centers[i * 2 + 1];
            c = cB;
            for (const r of blk.regions) {
              const b = r.box;
              if (x >= b[0] - pad && x <= b[2] + pad && y >= b[1] - pad && y <= b[3] + pad) { c = cA; break; }
            }
          }
          o.mesh.setColorAt(i, c);
        }
        o.mesh.instanceColor.needsUpdate = true;
      }
    }
    // glowing outline boxes; colour above 1.0 so the bloom pass picks them up
    hiGroup.clear();
    const col = new THREE.Color(blk.color).multiplyScalar(2.6);
    for (const r of blk.regions) {
      const [x0, y0, x1, y1] = r.box;
      const e = new THREE.LineSegments(unitEdges, new THREE.LineBasicMaterial({ color: col, toneMapped: false }));
      e.scale.set(x1 - x0 + 1.2, 1, y1 - y0 + 1.2);
      e.position.set((x0 + x1) / 2 - CX, 0.5, -((y0 + y1) / 2 - CY));
      hiGroup.add(e);
      const f = new THREE.Mesh(unitBox, new THREE.MeshBasicMaterial({ color: blk.color, transparent: true, opacity: 0.06, depthWrite: false }));
      f.scale.copy(e.scale);
      f.position.copy(e.position);
      hiGroup.add(f);
    }
    blockListEl?.querySelectorAll('.block-btn').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.block === blk.id)));
    if (infoCard) {
      infoCard.style.setProperty('--blk', blk.color);
      infoCard.innerHTML = `<h3>${blk.name}</h3><p>${blk.desc}</p><ul>${blk.metrics.map((m) => `<li>${m}</li>`).join('')}</ul>`;
    }
    renderLabels();
    touch();
    return blk;
  }

  // ---- pins ------------------------------------------------------------------------
  const pinGroup = new THREE.Group();
  scene.add(pinGroup);
  const PIN_LABELS = { 'ua[0]': 'VINP', 'ua[1]': 'VINN', clk: 'clk', rst_n: 'rst_n', 'uo_out[7]': 'MONP', 'uio_out[0]': 'MONN' };
  const pinGeo = new THREE.CylinderGeometry(0.9, 0.9, 1.2, 14);
  for (const p of gds.pins) {
    const used = p.name.startsWith('uo_out') || p.name.startsWith('uio_out') || p.name in PIN_LABELS;
    if (!used) continue;
    const analog = p.name.startsWith('ua');
    const m = new THREE.Mesh(pinGeo, new THREE.MeshBasicMaterial({ color: new THREE.Color(analog ? '#f2c14e' : '#8fb4ff').multiplyScalar(1.8), toneMapped: false }));
    m.position.set(p.x - CX, 0, -(p.y - CY));
    pinGroup.add(m);
  }

  // ---- camera ----------------------------------------------------------------------
  const pose = { tx: 0, ty: 0, tz: 0, az: -0.62, el: 0.56, dist: 330 };
  let anim = null;
  const portrait = () => canvasWrap.clientWidth < canvasWrap.clientHeight * 0.9;

  function readPose() {
    const d = camera.position.clone().sub(controls.target);
    const dist = d.length();
    return {
      tx: controls.target.x, ty: controls.target.y, tz: controls.target.z,
      az: Math.atan2(d.x, d.z), el: Math.asin(THREE.MathUtils.clamp(d.y / dist, -1, 1)), dist,
    };
  }
  function writePose(p) {
    controls.target.set(p.tx, p.ty, p.tz);
    const ce = Math.cos(p.el);
    camera.position.set(p.tx + p.dist * Math.sin(p.az) * ce, p.ty + p.dist * Math.sin(p.el), p.tz + p.dist * Math.cos(p.az) * ce);
  }
  function flyTo(to, dur = 1.25) {
    const from = readPose();
    let daz = (to.az - from.az) % (Math.PI * 2);
    if (daz > Math.PI) daz -= Math.PI * 2;
    if (daz < -Math.PI) daz += Math.PI * 2;
    to = { ...to, az: from.az + daz };
    if (reduceMotion || dur <= 0) { writePose(to); controls.update(); anim = null; touch(); return; }
    anim = { t: 0, dur, from, to };
    touch();
  }
  function poseFor(blk, o = {}) {
    const t = toWorld(blk.focus.x, o.y ?? blk.focus.y, 2);
    const pf = portrait() ? 1.75 : 1;
    return {
      tx: t.x, ty: t.y, tz: t.z,
      az: o.az ?? blk.cam?.az ?? 0.45, el: o.el ?? blk.cam?.el ?? 0.7,
      dist: (o.dist ?? blk.focus.dist3d) * pf,
    };
  }

  /** Scroll tour entry point. */
  function setScene(name) {
    if (mode !== 'tour' || name === sceneName || !(name in SCENES)) return;
    sceneName = name;
    const sc = SCENES[name];
    const blk = selectBlock(sc.block || name);
    explodeTarget = sc.explode ?? blk.explode ?? BASE_EXPLODE;
    shiftTarget = portrait() ? [0, name === 'hero' ? -0.1 : -0.2] : (sc.shift || [0.2, 0]);
    controls.autoRotate = !!sc.spin && !reduceMotion;
    flyTo(poseFor(blk, sc), name === 'hero' ? 1.6 : 1.25);
  }

  function applyControls() {
    const el = renderer.domElement;
    if (mode === 'tour') {
      controls.enabled = !coarse;
      controls.enableZoom = false;
      controls.enablePan = false;
      controls.enableRotate = true;
      controls.mouseButtons = { LEFT: THREE.MOUSE.ROTATE, MIDDLE: null, RIGHT: null };
      el.style.touchAction = coarse ? 'auto' : 'none';
      el.style.cursor = coarse ? '' : 'grab';
      return;
    }
    controls.enabled = true;
    controls.enableZoom = true;
    controls.enablePan = true;
    el.style.touchAction = 'none';
    if (viewMode === '2d') {
      controls.enableRotate = false;
      controls.mouseButtons = { LEFT: THREE.MOUSE.PAN, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN };
      controls.touches = { ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_PAN };
      el.style.cursor = 'grab';
    } else if (dragTool === 'pan' || spacePan) {
      controls.enableRotate = true;
      controls.mouseButtons = { LEFT: THREE.MOUSE.PAN, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.ROTATE };
      controls.touches = { ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_ROTATE };
      el.style.cursor = 'grab';
    } else {
      controls.enableRotate = true;
      controls.mouseButtons = { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN };
      controls.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN };
      el.style.cursor = 'default';
    }
    const hint = $('stage-hint');
    if (hint) {
      hint.textContent = viewMode === '2d' ? 'Drag to pan, scroll to zoom, click a block'
        : dragTool === 'pan' ? 'Drag to pan, right-drag to rotate, scroll to zoom'
        : 'Drag to rotate, right-drag or hold Space to pan, scroll to zoom';
    }
  }

  function focusBlock(id, fly = true) {
    const blk = selectBlock(id);
    if (!fly) return;
    if (viewMode === '2d') {
      const t = toWorld(blk.focus.x, blk.focus.y, 2);
      flyTo({ tx: t.x, ty: t.y, tz: t.z, az: 0, el: Math.PI / 2 - 0.0005, dist: blk.focus.dist2d * 1.25 }, 0.8);
    } else {
      flyTo(poseFor(blk, blk.id === 'all' ? { az: -0.5, el: 0.7 } : {}), 0.9);
    }
  }

  function setViewMode(m, tool = 'orbit') {
    const prev = viewMode;
    viewMode = m;
    if (m === '3d') dragTool = tool;
    $('btn-mode-3d')?.setAttribute('aria-pressed', String(m === '3d' && dragTool === 'orbit'));
    $('btn-mode-3d-pan')?.setAttribute('aria-pressed', String(m === '3d' && dragTool === 'pan'));
    $('btn-mode-2d')?.setAttribute('aria-pressed', String(m === '2d'));
    applyControls();
    // looking straight down, every metal face mirrors the key light: turn the glare off
    const flat = m === '2d';
    bloom.strength = flat ? 0.08 : 0.42;
    scene.environmentIntensity = flat ? 0.22 : 0.75;
    key.intensity = flat ? 0.7 : 2.1;
    if (prev !== m) {
      explodeTarget = m === '2d' ? 1 : parseFloat($('slider-explode')?.value || BASE_EXPLODE);
      focusBlock(activeBlock);
    }
  }

  function setExplore(on) {
    if ((mode === 'explore') === on) return;
    mode = on ? 'explore' : 'tour';
    root.classList.toggle('exploring', on);
    document.documentElement.classList.toggle('lock-scroll', on);
    controls.autoRotate = false;
    if (on) {
      viewMode = '3d'; dragTool = 'orbit';
      setViewMode('3d', 'orbit');
      explodeTarget = parseFloat($('slider-explode')?.value || BASE_EXPLODE);
      shiftTarget = portrait() ? [0, -0.12] : [Math.min(0.14, 170 / canvasWrap.clientWidth), 0];
      focusBlock('all');
    } else {
      viewMode = '2d';
      setViewMode('3d', 'orbit');
      syncVisibility();
      const s = sceneName;
      sceneName = '';
      setScene(s || 'outro');
    }
    renderLabels();
  }

  function syncVisibility() {
    const ex = mode === 'explore';
    for (const L of layerList) {
      for (const o of L.objs) o.mesh.visible = (!ex || (L.visible && !showPhoto)) && (!o.isDecap || !ex || showDecap);
    }
    for (const V of viaList) {
      const on = !ex || (showVias && V.lo.visible && V.hi.visible && !showPhoto);
      for (const o of V.objs) o.mesh.visible = on && (!o.isDecap || !ex || showDecap);
    }
    photoPlane.visible = ex && showPhoto;
    pinGroup.visible = !ex || showPins;
    touch();
  }

  // ---- explore UI ------------------------------------------------------------------
  if (blockListEl) {
    blockListEl.innerHTML = BLOCKS.map((b) => `
      <button class="block-btn" data-block="${b.id}" aria-pressed="${b.id === 'all'}">
        <i style="background:${b.color}"></i><span>${b.short}</span><em>${b.tag}</em>
      </button>`).join('');
    blockListEl.addEventListener('click', (e) => {
      const btn = e.target.closest('.block-btn');
      if (btn) focusBlock(btn.dataset.block);
    });
  }
  if (layerGridEl) {
    layerGridEl.innerHTML = LAYER_ORDER.map((k) => `
      <button class="layer-chip" data-layer="${k}" aria-pressed="true" title="GDS ${layers[k]?.gdsNum || ''}">
        <i style="background:${LAYER_META[k].color}"></i>${LAYER_META[k].label}
      </button>`).join('');
    layerGridEl.addEventListener('click', (e) => {
      const chip = e.target.closest('.layer-chip');
      if (!chip) return;
      const L = layers[chip.dataset.layer];
      L.visible = !L.visible;
      chip.setAttribute('aria-pressed', String(L.visible));
      syncVisibility();
    });
  }
  $('btn-mode-3d')?.addEventListener('click', () => setViewMode('3d', 'orbit'));
  $('btn-mode-3d-pan')?.addEventListener('click', () => setViewMode('3d', 'pan'));
  $('btn-mode-2d')?.addEventListener('click', () => setViewMode('2d'));
  $('btn-reset')?.addEventListener('click', () => focusBlock('all'));
  $('slider-explode')?.addEventListener('input', (e) => {
    const v = parseFloat(e.target.value);
    $('explode-val').textContent = `${v.toFixed(1)}×`;
    if (viewMode === '3d') explodeTarget = v;
    touch();
  });
  const toggle = (id, fn) => $(id)?.addEventListener('click', (e) => {
    const on = fn();
    e.currentTarget.setAttribute('aria-pressed', String(on));
    syncVisibility();
  });
  toggle('btn-toggle-decap', () => (showDecap = !showDecap));
  toggle('btn-toggle-photo', () => (showPhoto = !showPhoto));
  toggle('btn-toggle-pins', () => (showPins = !showPins));
  toggle('btn-toggle-vias', () => (showVias = !showVias));
  toggle('btn-toggle-labels', () => { showLabels = !showLabels; renderLabels(); return showLabels; });
  $('explore-open')?.addEventListener('click', () => setExplore(true));
  document.querySelectorAll('[data-explore]').forEach((b) => b.addEventListener('click', () => {
    root.scrollIntoView({ block: 'start', behavior: 'instant' });
    setExplore(true);
  }));
  $('explore-close')?.addEventListener('click', () => setExplore(false));

  let pointerInside = false;
  renderer.domElement.addEventListener('pointerenter', () => { pointerInside = true; });
  renderer.domElement.addEventListener('pointerleave', () => { pointerInside = false; });
  window.addEventListener('keydown', (e) => {
    if (mode !== 'explore') return;
    if (e.key === 'Escape') setExplore(false);
    if (e.code === 'Space' && pointerInside && viewMode === '3d' && !spacePan) {
      e.preventDefault();
      spacePan = true;
      applyControls();
    }
  });
  window.addEventListener('keyup', (e) => {
    if (e.code === 'Space' && spacePan) { spacePan = false; applyControls(); }
  });

  // ---- projected HTML labels -----------------------------------------------------
  const labelNodes = [];
  const LANDMARKS = [
    { id: 'digital', text: 'Samplers and buffers', x: 108, y: 213 },
    { id: 'vco', text: 'Ring VCOs', x: 52, y: 194 },
    { id: 'rdac', text: 'Rin + RDAC', x: 102, y: 168 },
    { id: 'ota', text: 'OTA + clamp', x: 40, y: 132 },
    { id: 'mim', text: 'MIM capacitors', x: 108, y: 108 },
    { id: 'decap', text: 'Decap field', x: 80, y: 40 },
  ];
  function renderLabels() {
    if (!labelLayer) return;
    labelLayer.innerHTML = '';
    labelNodes.length = 0;
    if (!showLabels) return;
    const blk = BLOCKS.find((b) => b.id === activeBlock);
    let targets = [];
    if (blk.regions.length) {
      targets = blk.regions.map((r) => ({ id: blk.id, text: r.label, x: (r.box[0] + r.box[2]) / 2, y: (r.box[1] + r.box[3]) / 2, color: blk.color }));
    } else if (mode === 'explore') {
      targets = LANDMARKS;
    }
    for (const t of targets) {
      const el = document.createElement(mode === 'explore' ? 'button' : 'span');
      el.className = 'die-label';
      el.textContent = t.text;
      if (t.color) el.style.setProperty('--blk', t.color);
      if (mode === 'explore') el.addEventListener('click', () => focusBlock(t.id));
      labelLayer.appendChild(el);
      labelNodes.push({ el, x: t.x, y: t.y });
    }
  }

  // ---- picking -----------------------------------------------------------------------
  const raycaster = new THREE.Raycaster();
  const ptr = new THREE.Vector2();
  const diePlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -1);
  const hit = new THREE.Vector3();
  const PICK_ORDER = ['conb', 'clamp', 'rarray', 'vco', 'ota', 'bias', 'mim', 'rdac', 'digital', 'decap'];
  function blockAt(x, y) {
    for (const id of PICK_ORDER) {
      const blk = BLOCKS.find((b) => b.id === id);
      for (const r of blk.regions) {
        const b = r.box;
        if (x >= b[0] && x <= b[2] && y >= b[1] && y <= b[3]) return blk;
      }
    }
    return null;
  }
  function dieAt(ev) {
    const rect = renderer.domElement.getBoundingClientRect();
    ptr.set(((ev.clientX - rect.left) / rect.width) * 2 - 1, -((ev.clientY - rect.top) / rect.height) * 2 + 1);
    raycaster.setFromCamera(ptr, camera);
    if (!raycaster.ray.intersectPlane(diePlane, hit)) return null;
    const x = hit.x + CX, y = -hit.z + CY;
    return x < 0 || x > W || y < 0 || y > H ? null : { x, y };
  }
  let down = null;
  renderer.domElement.addEventListener('pointermove', (ev) => {
    if (mode !== 'explore' || !coordReadout) return;
    const pt = dieAt(ev);
    const blk = pt && blockAt(pt.x, pt.y);
    coordReadout.textContent = pt ? `x ${pt.x.toFixed(1)}  y ${pt.y.toFixed(1)} µm${blk ? '  ' + blk.short : ''}` : '161.0 × 225.8 µm';
  });
  renderer.domElement.addEventListener('pointerdown', (ev) => {
    down = ev.button === 0 ? { x: ev.clientX, y: ev.clientY } : null;
    anim = null;
    controls.autoRotate = false;
    if (renderer.domElement.style.cursor === 'grab') renderer.domElement.style.cursor = 'grabbing';
    touch();
  });
  window.addEventListener('pointerup', (ev) => {
    if (renderer.domElement.style.cursor === 'grabbing') renderer.domElement.style.cursor = 'grab';
    if (!down || mode !== 'explore') { down = null; return; }
    const moved = Math.hypot(ev.clientX - down.x, ev.clientY - down.y);
    down = null;
    if (moved > 5 || ev.target !== renderer.domElement) return;
    const pt = dieAt(ev);
    const blk = pt && blockAt(pt.x, pt.y);
    if (blk) focusBlock(blk.id);
  });
  controls.addEventListener('change', touch);

  // ---- post-processing ------------------------------------------------------------
  const rt = new THREE.WebGLRenderTarget(4, 4, { type: THREE.HalfFloatType, samples: 4 });
  const composer = new EffectComposer(renderer, rt);
  composer.setPixelRatio(dpr);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(4, 4), 0.42, 0.55, 0.95);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());

  let vw = 1, vh = 1;
  function resize() {
    vw = canvasWrap.clientWidth || 1;
    vh = canvasWrap.clientHeight || 1;
    camera.aspect = vw / vh;
    renderer.setSize(vw, vh, false);
    composer.setSize(vw, vh);
    touch();
  }
  new ResizeObserver(resize).observe(canvasWrap);
  resize();
  new IntersectionObserver(([e]) => { onScreen = e.isIntersecting; touch(); }).observe(canvasWrap);

  // ---- boot ----------------------------------------------------------------------------
  selectBlock('all');
  applyControls();
  writePose({ ...poseFor(BLOCKS[0], SCENES.hero), dist: 420 * (portrait() ? 1.75 : 1), el: 0.82 });
  controls.update();
  shift = shiftTarget = portrait() ? [0, -0.1] : SCENES.hero.shift.slice();

  const introStart = performance.now() + 250;
  let introDone = reduceMotion;
  if (reduceMotion) {
    layerList.forEach((L) => { L.reveal = 1; });
    if (ticker) ticker.textContent = '14,954 rectangles and 48,126 vias';
  }
  applyStack();
  root.classList.add('ready');

  const proj = new THREE.Vector3();
  let last = performance.now();
  function tick(now) {
    requestAnimationFrame(tick);
    const dt = Math.min((now - last) / 1000, 0.05);
    last = now;
    if (!onScreen) return;

    let busy = false;
    if (!introDone) {
      busy = true;
      const t = (now - introStart) / 1000;
      let current = null;
      layerList.forEach((L, i) => {
        L.reveal = THREE.MathUtils.clamp((t - i * 0.26) / 0.85, 0, 1);
        if (L.reveal > 0) current = L;
      });
      if (ticker && current) ticker.textContent = `Depositing ${current.meta.label}  ${current.gdsNum}`;
      if (t > layerList.length * 0.26 + 0.9) {
        introDone = true;
        if (ticker) ticker.textContent = '14,954 rectangles and 48,126 vias';
      }
      applyStack();
    }
    if (Math.abs(explodeTarget - explode) > 0.002) {
      explode += (explodeTarget - explode) * Math.min(1, dt * 4.5);
      applyStack();
      busy = true;
    }
    const sx = shiftTarget[0] - shift[0], sy = shiftTarget[1] - shift[1];
    if (Math.abs(sx) + Math.abs(sy) > 0.0005) {
      shift = [shift[0] + sx * Math.min(1, dt * 4), shift[1] + sy * Math.min(1, dt * 4)];
      busy = true;
    }
    if (anim) {
      anim.t += dt / anim.dur;
      const u = easeInOut(Math.min(anim.t, 1));
      const p = {};
      for (const k in anim.from) p[k] = anim.from[k] + (anim.to[k] - anim.from[k]) * u;
      writePose(p);
      if (anim.t >= 1) anim = null;
      busy = true;
    }
    if (controls.autoRotate) busy = true;
    if (!busy && now > dirtyUntil) return;

    controls.update();
    camera.setViewOffset(vw, vh, -shift[0] * vw, -shift[1] * vh, vw, vh);
    composer.render();

    if (labelNodes.length) {
      const zl = STACK_TOP * explode + 5;
      for (const n of labelNodes) {
        proj.set(n.x - CX, zl, -(n.y - CY)).project(camera);
        const vis = proj.z < 1;
        n.el.style.display = vis ? '' : 'none';
        if (vis) n.el.style.transform = `translate(${((proj.x * 0.5 + 0.5) * vw).toFixed(1)}px, ${((-proj.y * 0.5 + 0.5) * vh).toFixed(1)}px) translate(-50%, -100%)`;
      }
    }
  }
  requestAnimationFrame(tick);

  return { setScene, setExplore, focusBlock };
}
