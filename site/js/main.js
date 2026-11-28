import { initChip } from './layout3d.js?v=3';
import { initAdcSim } from './adc-sim.js?v=3';
import { initMeasurementCharts } from './charts.js?v=3';

// ---- scroll tour: the step nearest the middle of the viewport picks the scene ----
const chipEl = document.getElementById('chip');
const steps = [...document.querySelectorAll('.step[data-scene]')];
let chip = null;
let scene = 'hero';

function pickScene() {
  const mid = innerHeight * 0.5;
  let best = steps[0], bestD = Infinity;
  for (const s of steps) {
    const r = s.getBoundingClientRect();
    const d = mid < r.top ? r.top - mid : mid > r.bottom ? mid - r.bottom : 0;
    if (d < bestD) { bestD = d; best = s; }
  }
  const name = best.dataset.scene;
  if (name !== scene) {
    scene = name;
    chipEl.classList.toggle('at-hero', name === 'hero');
    steps.forEach((s) => s.classList.toggle('current', s === best));
  }
  chip?.setScene(scene);
}
addEventListener('scroll', pickScene, { passive: true });
addEventListener('resize', pickScene);

initChip('data/layout3d.json?v=3').then((c) => { chip = c; pickScene(); });
pickScene();

// ---- the title's thin-film sheen follows the pointer ----
const title = document.getElementById('hero-title');
if (title && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
  addEventListener('pointermove', (e) => {
    title.style.setProperty('--sheen', `${(e.clientX / innerWidth) * 100}%`);
  }, { passive: true });
}

initAdcSim();
initMeasurementCharts('data/sim_data.json');

// ---- schematics ----
const SCH = {
  top:  { img: 'assets/sch_top.png?v=6',   alt: 'Top-level schematic', cap: 'Two mirrored halves share a 0.90 V resistive reference, the OTA tail bias, the common-centroid VCO bias resistors and the reset inverter.' },
  half: { img: 'assets/sch_half.png?v=6',  alt: 'Schematic of one half', cap: 'One half: the OTA-C loop, the seven-stage ring, two ranks of flip-flops with XOR gates that stay on-chip, and seven buf_4 buffers to the pins.' },
  loop: { img: 'assets/sch_loop.png?v=6',  alt: 'Integrator and resistor DAC schematic', cap: 'Integrator and DAC: Rin = 49.7 kΩ, seven 1.04 MΩ elements, two 24 × 25 µm MIM capacitors (2.43 pF) and an NMOS reset switch.' },
  ota:  { img: 'assets/sch_ota5t.png?v=6', alt: 'OTA and clamp schematic', cap: 'OTA and clamp: 48/3 µm NMOS pair, 16/2 µm PMOS load, 8/2 µm tail, and the five-transistor Miller-compensated clamp on the control voltage.' },
  vco:  { img: 'assets/sch_vco.png?v=6',   alt: 'Ring VCO schematic', cap: 'Ring VCO: a 4/1 µm V-to-I NMOS over the shared 229.7 kΩ array, 1:1 mirrors, and seven current-starved stages with MOS load capacitors.' },
};
const schImg = document.getElementById('sch-img');
const schCap = document.getElementById('sch-cap');
const schTabs = [...document.querySelectorAll('#sch-tabs .tab-btn')];
function showSch(key) {
  const s = SCH[key];
  schTabs.forEach((b) => b.classList.toggle('active', b.dataset.sch === key));
  schImg.src = s.img;
  schImg.alt = s.alt;
  schCap.textContent = s.cap;
}
schTabs.forEach((b) => b.addEventListener('click', () => showSch(b.dataset.sch)));
showSch('top');

// ---- lightbox ----
const lb = document.getElementById('lightbox');
const lbImg = document.getElementById('lightbox-img');
document.querySelectorAll('img[data-zoom="true"]').forEach((im) => {
  im.addEventListener('click', () => { lbImg.src = im.src; lbImg.alt = im.alt; lb.classList.add('open'); });
});
lb.addEventListener('click', () => lb.classList.remove('open'));
addEventListener('keydown', (e) => { if (e.key === 'Escape') lb.classList.remove('open'); });
