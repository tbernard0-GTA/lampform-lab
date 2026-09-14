import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const $ = id => document.getElementById(id);
const format = n => n.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const percent = n => `${format(n)}%`;
const cache = new Map();
let data, renderer, camera, controls, scene, lamp, tool, network, requestId = 0;
let view = 'flat', amount = 1;
const viewButtons = [...document.querySelectorAll('[data-view]')];
const palette = ['#45646f', '#7aaf83', '#d9b455', '#c65b34'].map(c => new THREE.Color(c));

function demandColor(value) {
  const t = THREE.MathUtils.clamp(value / 60, 0, 1) * (palette.length - 1);
  const i = Math.min(Math.floor(t), palette.length - 2);
  return palette[i].clone().lerp(palette[i + 1], t - i);
}

function initViewer() {
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor('#e8ebdf');
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.2;
  $('viewer').appendChild(renderer.domElement);
  renderer.domElement.setAttribute('aria-hidden', 'true');
  scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xffffff, 0x67735c, 3));
  const key = new THREE.DirectionalLight(0xffffff, 3.5);
  key.position.set(-70, -80, 150); scene.add(key);
  const fill = new THREE.DirectionalLight(0xf7ffdc, 2);
  fill.position.set(60, 90, 70); scene.add(fill);
  camera = new THREE.PerspectiveCamera(32, 1, .1, 2000);
  camera.up.set(0, 0, 1);
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = .09;
  controls.minDistance = 35; controls.maxDistance = 500;
  controls.enablePan = true;
  new ResizeObserver(() => {
    const { width, height } = $('viewer').getBoundingClientRect();
    if (!width || !height) return;
    renderer.setSize(width, height);
    camera.aspect = width / height; camera.updateProjectionMatrix();
    render();
  }).observe($('viewer'));
  controls.addEventListener('change', render);
  let inViewport = true;
  new IntersectionObserver(([entry]) => { inViewport = entry.isIntersecting; }).observe($('viewer'));
  renderer.setAnimationLoop(() => { if (inViewport && !document.hidden) controls.update(); });
  renderer.domElement.addEventListener('webglcontextlost', event => {
    event.preventDefault(); showError('O visualizador 3D foi interrompido. Recarregue a página para restaurá-lo.');
  });
}

function render() { if (renderer && scene && camera) renderer.render(scene, camera); }

function mesh(source, material) {
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(source.positions, 3));
  geometry.setIndex(source.indices);
  geometry.computeVertexNormals();
  return new THREE.Mesh(geometry, material);
}

function discard(object) {
  if (!object) return;
  scene.remove(object); object.geometry.dispose(); object.material.dispose();
}

function installGeometry() {
  if (!renderer) return;
  discard(lamp); discard(tool); discard(network);
  lamp = mesh(data.lamp, new THREE.MeshStandardMaterial({ color: '#dbdfc9', roughness: .64, metalness: .05, side: THREE.DoubleSide }));
  tool = mesh(data.tool, new THREE.MeshStandardMaterial({ color: '#6e7d67', roughness: .9, metalness: 0, transparent: true, opacity: .12, depthWrite: false, side: THREE.DoubleSide }));
  network = new THREE.InstancedMesh(new THREE.CylinderGeometry(.25, .25, 1, 6), new THREE.MeshBasicMaterial({depthTest: false}), data.edges.length);
  network.renderOrder = 2;
  scene.add(lamp, tool, network);
  updateGeometry(); resetCamera();
}

function resetCamera() {
  if (!camera || !data) return;
  const size = Math.max(...data.lamp.dimensions, ...data.tool.dimensions);
  const distance = size * 1.85 * Math.max(1, 1 / camera.aspect);
  camera.position.set(distance * .62, -distance * .75, distance * .72);
  controls.target.set(0, 0, view === 'flat' ? 0 : 18);
  controls.update(); render();
}

function updateGeometry() {
  if (!data || !renderer) return;
  lamp.visible = view === 'flat';
  network.visible = view !== 'flat';
  tool.visible = $('show-tool').checked;
  const dummy = new THREE.Object3D();
  const up = new THREE.Vector3(0, 1, 0);
  data.edges.forEach((edge, i) => {
    const color = view === 'demand' ? demandColor(edge.demand) : new THREE.Color('#415a37');
    const p = edge.flat.map((v, j) => THREE.MathUtils.lerp(v, edge.formed[j], amount));
    const start = new THREE.Vector3(...p.slice(0, 3));
    const end = new THREE.Vector3(...p.slice(3));
    const direction = end.clone().sub(start);
    dummy.position.copy(start).add(end).multiplyScalar(.5);
    dummy.quaternion.setFromUnitVectors(up, direction.clone().normalize());
    dummy.scale.set(1, direction.length(), 1);
    dummy.updateMatrix();
    network.setMatrixAt(i, dummy.matrix);
    network.setColorAt(i, color);
  });
  network.instanceMatrix.needsUpdate = true; network.instanceColor.needsUpdate = true;
  network.computeBoundingSphere();
  render();
}

function setView(next) {
  view = next;
  viewButtons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.view === view)));
  $('forming-control').hidden = view === 'flat';
  $('legend').hidden = view !== 'demand';
  $('state-description').textContent = {
    flat: 'O STL original da peça, antes da conformação.',
    formed: 'Rede equivalente de ligamentos sobre a ferramenta, com a borda ancorada em 2,0.',
    demand: 'Cores do resultado final da rede de referência. A escala não muda durante a interpolação.'
  }[view];
  $('show-tool').checked = view !== 'flat';
  amount = 1; $('progress').value = '100'; $('progress-value').textContent = '100%';
  updateModelLabel(); updateGeometry(); resetCamera();
}

function updateModelLabel() {
  const name = $('piece').value === 'hab2_mold' ? 'HAB-2' : 'SUB-MERGED';
  $('model-label').textContent = `${name} / ${ { flat: 'STL ORIGINAL', formed: 'REDE CONFORMADA', demand: 'DEMANDA V0.2' }[view] }`;
}

function fillMetrics() {
  const metrics = data.summary.relaxed;
  [['mean', 'mean_strain_pct'], ['p95', 'p95_strain_pct'], ['maximum', 'max_strain_pct']].forEach(([id, key]) => {
    $(id).replaceChildren(document.createTextNode(format(metrics[key])));
    const small = document.createElement('small'); small.textContent = '%'; $(id).append(small);
  });
  $('geometry-info').textContent = `${data.lamp.dimensions.map(format).join(' × ')} mm · ${data.summary.cells} células · ${data.summary.ligaments} ligamentos na rede`;
  $('comparison-piece').textContent = data.summary.pair;
  updateComparison();
}

function updateComparison() {
  if (!data) return;
  const anchor = Number($('anchor').value);
  const row = data.sensitivity.find(item => item.boundary_anchor === anchor);
  const baseline = data.summary.relaxed.p95_strain_pct;
  const max = Math.max(...data.sensitivity.map(item => item.p95_strain_pct)) * 1.1;
  $('base-bar-value').textContent = percent(baseline);
  $('selected-bar-value').textContent = percent(row.p95_strain_pct);
  $('base-bar').style.width = `${baseline / max * 100}%`;
  $('selected-bar').style.width = `${row.p95_strain_pct / max * 100}%`;
  $('selected-bar-label').textContent = `Selecionada · ${anchor.toLocaleString('pt-BR')}`;
  const delta = (1 - row.p95_strain_pct / baseline) * 100;
  $('comparison-insight').textContent = Math.abs(delta) < .01 ? 'A referência para comparar o efeito da borda.' : `${percent(Math.abs(delta))} ${delta > 0 ? 'menos' : 'mais'} demanda no P95, dentro deste modelo.`;
}

function showError(message) {
  $('loading').hidden = false;
  $('loading').textContent = message;
}

async function loadPiece() {
  const id = ++requestId;
  const slug = $('piece').value;
  $('loading').hidden = false;
  $('loading').textContent = 'Carregando os modelos reais…';
  $('piece').setAttribute('aria-busy', 'true');
  try {
    if (!cache.has(slug)) {
      const response = await fetch(`data/${slug}.json`);
      if (!response.ok) throw new Error('Dados indisponíveis');
      cache.set(slug, await response.json());
    }
    if (id !== requestId) return;
    data = cache.get(slug);
    fillMetrics(); updateModelLabel(); installGeometry();
    $('loading').hidden = Boolean(renderer);
    if (!renderer) showError('O navegador não conseguiu iniciar o 3D. Os resultados e a história continuam disponíveis abaixo.');
  } catch {
    if (id !== requestId) return;
    data = null;
    if (lamp) lamp.visible = false;
    if (tool) tool.visible = false;
    if (network) network.visible = false;
    ['mean', 'p95', 'maximum', 'base-bar-value', 'selected-bar-value'].forEach(key => $(key).textContent = '—');
    $('geometry-info').textContent = 'Geometria indisponível.';
    $('comparison-insight').textContent = 'Os dados desta peça não puderam ser carregados.';
    render();
    showError('Não foi possível carregar esta peça. Selecione-a novamente ou recarregue a página.');
  } finally { if (id === requestId) $('piece').removeAttribute('aria-busy'); }
}

try { initViewer(); } catch { renderer = null; }
viewButtons.forEach(button => button.addEventListener('click', () => setView(button.dataset.view)));
$('piece').addEventListener('change', loadPiece);
$('anchor').addEventListener('change', updateComparison);
$('show-tool').addEventListener('change', updateGeometry);
$('reset-camera').addEventListener('click', resetCamera);
$('progress').addEventListener('input', () => {
  amount = Number($('progress').value) / 100;
  $('progress-value').textContent = `${$('progress').value}%`;
  updateGeometry();
});
await loadPiece();
