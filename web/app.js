import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const $ = id => document.getElementById(id);
const fmt = (n, digits = 1) => Number(n).toLocaleString('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits });
const esc = text => String(text).replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' })[c]);
const palette = ['#45646f', '#7aaf83', '#d9b455', '#c65b34'].map(c => new THREE.Color(c));
const fields = { demand:['Demanda de deformação', '%'], width:['Largura dos ligamentos', ' mm'], hole_size:['Abertura entre faces do hexágono', ' mm'], compliance:['Caminho / distância entre endpoints', '×'] };
let catalog, part = 'hab2', view = 'flat', field = 'demand', revision = 0;
let leftData, rightData, viewers = [], syncing = false;
const cache = new Map();

function colorFor(value) {
  const [lo, hi] = catalog.common_color_ranges[field];
  const scaled = THREE.MathUtils.clamp((value - lo) / (hi - lo), 0, 1) * 3;
  const i = Math.min(Math.floor(scaled), 2);
  return palette[i].clone().lerp(palette[i + 1], scaled - i);
}

function edgeValue(edge, dataset) {
  if (field !== 'hole_size') return edge[field];
  const x = (edge.flat[0] + edge.flat[3]) / 2, y = (edge.flat[1] + edge.flat[4]) / 2;
  let nearest, distance = Infinity;
  for (const cell of dataset.cells) {
    const coords = cell.candidate.slice(0, -1);
    const cx = coords.reduce((s, p) => s + p[0], 0) / coords.length;
    const cy = coords.reduce((s, p) => s + p[1], 0) / coords.length;
    const d = (x-cx)**2 + (y-cy)**2;
    if (d < distance) { distance = d; nearest = cell; }
  }
  return nearest.hole_size;
}

class Viewer {
  constructor(id) {
    this.element = $(id);
    this.renderer = new THREE.WebGLRenderer({ antialias:true });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.renderer.setClearColor('#e8ebdf');
    this.element.append(this.renderer.domElement);
    this.renderer.domElement.setAttribute('aria-hidden','true');
    this.scene = new THREE.Scene();
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x87917e, 3));
    const key = new THREE.DirectionalLight(0xffffff, 3); key.position.set(-100,-100,150); this.scene.add(key);
    this.camera = new THREE.PerspectiveCamera(33, 1, .1, 2000); this.camera.up.set(0,0,1);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.minDistance = 35; this.controls.maxDistance = 550;
    this.controls.addEventListener('change', () => {
      this.render();
      if (syncing) return;
      syncing = true;
      for (const other of viewers) if (other !== this) {
        other.camera.position.copy(this.camera.position);
        other.controls.target.copy(this.controls.target);
        other.controls.update(); other.render();
      }
      syncing = false;
    });
    new ResizeObserver(() => {
      const {width,height} = this.element.getBoundingClientRect();
      if (!width || !height) return;
      this.renderer.setSize(width,height); this.camera.aspect = width/height; this.camera.updateProjectionMatrix();
      this.render();
    }).observe(this.element);
    this.renderer.domElement.addEventListener('webglcontextlost', e => {
      e.preventDefault(); $('app-status').hidden=false;
      $('app-status').textContent='O 3D foi interrompido. Recarregue a página; as tabelas e os downloads continuam disponíveis.';
    });
  }
  render() { this.renderer.render(this.scene,this.camera); }
  clear() {
    for (const object of this.objects || []) { this.scene.remove(object); object.geometry.dispose(); object.material.dispose(); }
    this.objects=[];
  }
  mesh(source, material) {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(source.positions,3));
    geometry.setIndex(source.indices); geometry.computeVertexNormals();
    return new THREE.Mesh(geometry, material);
  }
  setData(dataset) {
    this.data=dataset; this.clear();
    this.lamp=this.mesh(dataset.lamp, new THREE.MeshStandardMaterial({vertexColors:true,roughness:.8,side:THREE.DoubleSide}));
    this.tool=this.mesh(dataset.tool, new THREE.MeshStandardMaterial({color:'#87917c',transparent:true,opacity:.10,depthWrite:false,side:THREE.DoubleSide}));
    this.network=new THREE.InstancedMesh(new THREE.CylinderGeometry(.19,.19,1,6), new THREE.MeshBasicMaterial({depthTest:false}), dataset.edges.length);
    this.network.renderOrder=2;
    this.objects=[this.lamp,this.tool,this.network]; this.scene.add(...this.objects);
    // Geometry-based nearest centerline association for the flat mesh's color.
    // Reused across field changes; no solver result is recomputed in the browser.
    const positions=dataset.lamp.positions;
    this.closest=new Int32Array(positions.length/3);
    for (let i=0; i<positions.length; i+=3) {
      let best=Infinity, index=-1;
      if (positions[i+2]>1.01) { this.closest[i/3]=-1; continue; }
      dataset.edges.forEach((edge,j) => {
        const p=edge.flat, dx=p[3]-p[0], dy=p[4]-p[1];
        const t=THREE.MathUtils.clamp(((positions[i]-p[0])*dx+(positions[i+1]-p[1])*dy)/(dx*dx+dy*dy),0,1);
        const d=(positions[i]-p[0]-t*dx)**2+(positions[i+1]-p[1]-t*dy)**2;
        if(d<best){best=d;index=j;}
      });
      this.closest[i/3]=best<4 ? index : -1;
    }
    this.update();
  }
  update() {
    if (!this.data) return;
    const dataset=this.data;
    this.lamp.visible=view==='flat'; this.tool.visible=view==='formed';
    const colors=dataset.edges.map(edge=>colorFor(edgeValue(edge,dataset)));
    const vertexColors=new Float32Array(this.closest.length*3);
    const neutral=new THREE.Color('#c8d0ba');
    this.closest.forEach((edge,i)=>(edge<0?neutral:colors[edge]).toArray(vertexColors,i*3));
    this.lamp.geometry.setAttribute('color',new THREE.Float32BufferAttribute(vertexColors,3));
    const dummy=new THREE.Object3D(), up=new THREE.Vector3(0,1,0);
    dataset.edges.forEach((edge,i)=>{
      const p=view==='flat'?edge.flat:edge.formed;
      const a=new THREE.Vector3(...p.slice(0,3)), b=new THREE.Vector3(...p.slice(3));
      if(view==='flat'){a.z=1.06;b.z=1.06;}
      const direction=b.clone().sub(a);
      dummy.position.copy(a).add(b).multiplyScalar(.5);
      dummy.quaternion.setFromUnitVectors(up,direction.clone().normalize());
      dummy.scale.set(1,direction.length(),1); dummy.updateMatrix();
      this.network.setMatrixAt(i,dummy.matrix); this.network.setColorAt(i,colors[i]);
    });
    this.network.instanceMatrix.needsUpdate=true; this.network.instanceColor.needsUpdate=true;
    this.network.computeBoundingSphere(); this.render();
  }
  reset() {
    const distance=195*Math.max(1,.8/this.camera.aspect);
    this.camera.position.set(distance*.62,-distance*.78,distance*.79);
    this.controls.target.set(0,0,view==='flat'?0:18); this.controls.update();this.render();
  }
}

function selected(side) { return catalog.designs.find(d=>d.id===$(`compare-${side}`).value); }
function cards() {
  const selectedId=$('compare-right').value;
  $('design-cards').innerHTML=catalog.designs.map(design=>{
    const m=design[part].metrics;
    const values=[['P95',`${fmt(m.p95)}%`],['Máximo',`${fmt(m.maximum)}%`],['Ligamentos >20%',`${fmt(m.above_20_pct)}%`],['Área aberta',`${fmt(m.open_area)}%`],['Material',`${fmt(m.material_area_proxy,0)} mm²`],['Score da peça',fmt(design[part].score.value,3)]];
    return `<button class="design-card" data-design="${design.id}" aria-label="Selecionar ${esc(design.name)}" aria-pressed="${design.id===selectedId}"><span class="rank">${design.id===catalog.recommendation.candidate_id?'MELHOR ALTERNATIVA COMBINADA':design.id==='original'?'REFERÊNCIA':'CANDIDATO'}</span><h3>${esc(design.name)}</h3><dl>${values.map(([label,value])=>`<div><dt>${label}</dt><dd>${value}</dd></div>`).join('')}</dl><span class="combined">Score das duas peças: ${fmt(design.combined_score,3)}</span></button>`;
  }).join('');
}

function table() {
  const left=selected('left'),right=selected('right'),a=left[part],b=right[part];
  $('metric-left').textContent=left.name; $('metric-right').textContent=right.name;
  const rows=[['P95','p95','%',1],['Máximo','maximum','%',1],['Ligamentos acima de 20%','above_20_pct','%',1],['Material projetado','material_area_proxy',' mm²',1],['Área aberta','open_area','%',1],['Volume proxy','mass_proxy',' mm³',1],['Alimentação XY média','mean_xy_feed',' mm',2],['Score da peça','score','',3]];
  $('metrics-body').innerHTML=rows.map(([label,key,unit,digits])=>{
    const va=key==='score'?a.score.value:a.metrics[key],vb=key==='score'?b.score.value:b.metrics[key];
    const delta=va ? (vb-va)/Math.abs(va)*100 : null;
    return `<tr><td>${label}</td><td>${fmt(va,digits)}${unit}</td><td>${fmt(vb,digits)}${unit}</td><td>${delta===null?'—':`${delta>0?'+':''}${fmt(delta)}%`}</td></tr>`;
  }).join('');
  const details=[...['mean','p50','p90','p99','std'].map(key=>[({mean:'Média',std:'Desvio padrão'})[key]||key.toUpperCase(),a.metrics[key],b.metrics[key],'%']),
    ...[5,10,30].map(q=>[`Ligamentos >${q}%`,a.metrics[`above_${q}_pct`],b.metrics[`above_${q}_pct`],'%']),
    ['Alimentação XY máxima',a.metrics.max_xy_feed,b.metrics.max_xy_feed,' mm'],
    ['Largura mínima nos caminhos',a.metrics.minimum_ligament_width,b.metrics.minimum_ligament_width,' mm'],
    ['Nós / ligações ao aro',`${a.nodes} / ${a.contacts}`,`${b.nodes} / ${b.contacts}`,''],
    ['Solver chegou à tolerância',a.solver.success?'Sim':'Não',b.solver.success?'Sim':'Não',''],
    ['Critério de término',a.solver.message,b.solver.message,''],
    ['Custo da energia proxy',a.solver.cost,b.solver.cost,''],
    ['Optimality numérica (não física)',a.solver.optimality,b.solver.optimality,''],
    ['STL watertight',a.validation.watertight?'Sim':'Não',b.validation.watertight?'Sim':'Não',''],
    ['Corpos',String(a.validation.body_count),String(b.validation.body_count),''],
    ['Faces',String(a.validation.face_count),String(b.validation.face_count),''],
    ['Faces duplicadas',String(a.validation.duplicate_faces),String(b.validation.duplicate_faces),''],
    ['Faces degeneradas',String(a.validation.degenerate_faces),String(b.validation.degenerate_faces),''],
    ['Dimensões',a.validation.dimensions.map(x=>fmt(x,2)).join(' × '),b.validation.dimensions.map(x=>fmt(x,2)).join(' × '),' mm']];
  $('detail-body').innerHTML=details.map(([label,va,vb,unit])=>`<tr><td>${label}</td><td>${esc(typeof va==='number'?fmt(va,3):va)}${unit}</td><td>${esc(typeof vb==='number'?fmt(vb,3):vb)}${unit}</td></tr>`).join('');
  $('score-components').textContent=`Componentes do score à direita: ${Object.entries(b.score.components).map(([key,value])=>`${key} = ${fmt(value,3)}`).join(' · ')}.`;
  $('original-note').hidden=left.id!=='original'&&right.id!=='original';
}

function heatmap(dataset,side) {
  const lines=dataset.edges.map(edge=>{
    const p=edge.flat, color=colorFor(edgeValue(edge,dataset)).getStyle();
    return `<path d="M${p[0]},${-p[1]} L${p[3]},${-p[4]}" stroke="${color}" stroke-width="${Math.min(edge.width,.9)}" stroke-linecap="round"/>`;
  }).join('');
  const holes=field==='hole_size'?dataset.cells.map(cell=>`<polygon points="${cell.candidate.map(p=>`${p[0]},${-p[1]}`).join(' ')}" fill="none" stroke="${colorFor(cell.hole_size).getStyle()}" stroke-width=".4"/>`).join(''):'';
  $(`heatmap-${side}`).innerHTML=`<svg viewBox="-42 -54 84 110" role="img" aria-label="Mapa plano de ${esc(selected(side).name)}: ${esc(fields[field][0])}"><path d="${esc(dataset.footprint_svg)}" fill="#cad2bf" fill-rule="evenodd"/>${lines}${holes}</svg>`;
  $(`heatmap-label-${side}`).textContent=`${selected(side).name} · ${fields[field][0]}`;
}

function inspectCell() {
  if(!rightData) return;
  const cell=rightData.cells[Number($('cell').value)||0];
  const centered=coords=>{
    const pts=coords.slice(0,-1),x=pts.reduce((s,p)=>s+p[0],0)/pts.length,y=pts.reduce((s,p)=>s+p[1],0)/pts.length;
    return pts.map(p=>`${p[0]-x},${-(p[1]-y)}`).join(' ');
  };
  $('cell-preview').innerHTML=`<svg viewBox="-12 -6 24 12" role="img" aria-label="Furo original e furo do design selecionado, na mesma escala"><g transform="translate(-6,0)"><polygon points="${centered(cell.original)}" fill="none" stroke="#657456" stroke-width=".18"/></g><g transform="translate(6,0)"><polygon points="${centered(cell.candidate)}" fill="#d9ef86" stroke="#657456" stroke-width=".18"/></g><text x="-6" y="5.5" text-anchor="middle" font-size=".8">Original</text><text x="6" y="5.5" text-anchor="middle" font-size=".8">Selecionado</text></svg>`;
  const rows=[['Furo original',`${fmt(cell.original_hole_size,2)} mm`],['Furo selecionado',`${fmt(cell.hole_size,2)} mm`],['Ligamento médio original',`${fmt(cell.original_ligament_width,2)} mm`],['Ligamento médio selecionado',`${fmt(cell.ligament_width,2)} mm`],['Variação da largura',`${fmt((cell.ligament_width/cell.original_ligament_width-1)*100)}%`],['Demanda baseline da célula',`${fmt(cell.baseline_demand)}%`]];
  $('cell-values').innerHTML=rows.map(([label,value])=>`<div><dt>${label}</dt><dd>${value}</dd></div>`).join('');
}

function selectionInfo() {
  const design=selected('right');
  const explanations={original:'A geometria fornecida permanece intacta. Nesta versão, a rede de referência é recalculada com larguras medidas e ligações explícitas ao aro.',gradient:'Os centros dos furos e o pitch foram mantidos. O campo de demanda do baseline orienta uma redução suave de até 10% na abertura, aumentando a largura dos ligamentos.',gradient_boundary:'O núcleo do gradiente foi reduzido a 90% para abrir espaço às pontes em S de 0,95 mm junto ao aro. O pitch interno passa a 7,2 mm. As pontes aparecem no STL e entram no cálculo, inclusive seus picos.',compliant:`${design[part].changed_edges} ligamentos interiores críticos desta peça receberam um caminho em S, com largura de 0,95 mm. O solver considera seu comprimento e suas mudanças de direção.`};
  $('design-explanation').textContent=explanations[design.id];
  $('download-title').textContent=design.name;
  $('download-description').textContent=`Score combinado ${fmt(design.combined_score,3)}. ${design.id==='original'?'Arquivos originais preservados; exigem revisão no slicer.':'Dois sólidos fechados, de corpo único, sem faces duplicadas ou degeneradas na validação.'}`;
  $('download-zip').href=design.zip; $('download-hab2').href=design.hab2.stl; $('download-submerged').href=design.submerged.stl;
  $('download-metrics').href=`downloads/${design.id.replaceAll('_','-')}/metrics.json`;
  inspectCell();
}

function updateField() {
  const [lo,hi]=catalog.common_color_ranges[field];
  $('legend-title').textContent=fields[field][0];
  $('legend-low').textContent=fmt(lo)+fields[field][1];
  $('legend-high').textContent=fmt(hi)+fields[field][1]+'+';
  viewers.forEach(viewer=>viewer.update());
  if(leftData)heatmap(leftData,'left'); if(rightData)heatmap(rightData,'right');
}

async function fetchData(design) {
  const path=design[part].data;
  if(!cache.has(path)){
    const response=await fetch(path); if(!response.ok)throw new Error('Falha ao carregar o design');
    cache.set(path,await response.json());
  }
  return cache.get(path);
}

async function refresh() {
  const ticket=++revision;
  $('app-status').hidden=false; $('app-status').textContent='Carregando as geometrias selecionadas…';
  try {
    const [a,b]=await Promise.all([fetchData(selected('left')),fetchData(selected('right'))]);
    if(ticket!==revision)return;
    leftData=a;rightData=b;
    cards();table();selectionInfo();
    viewers[0]?.setData(a);viewers[1]?.setData(b);viewers.forEach(v=>v.reset());
    $('caption-left').textContent=`${part==='hab2'?'HAB-2 → Mold':'Sub-Merged → Push'} · ${a.parent_count} caminhos`;
    $('caption-right').textContent=`${part==='hab2'?'HAB-2 → Mold':'Sub-Merged → Push'} · ${b.parent_count} caminhos`;
    updateField(); $('app-status').hidden=viewers.length===2;
    if(viewers.length!==2)$('app-status').textContent='O 3D não está disponível neste navegador. Use os mapas planos, as tabelas e os downloads abaixo.';
  } catch(error) {
    if(ticket!==revision)return;
    viewers.forEach(v=>v.clear());leftData=null;rightData=null;
    $('app-status').textContent='Não foi possível carregar a comparação. Recarregue a página para tentar novamente.';
    ['download-zip','download-hab2','download-submerged','download-metrics'].forEach(id=>$(id).removeAttribute('href'));
    console.error(error);
  }
}

async function main() {
  try {
    const response=await fetch('data/designs.json'); if(!response.ok)throw new Error('Catálogo indisponível');
    catalog=await response.json();
    for(const side of ['left','right']){
      $(`compare-${side}`).innerHTML=catalog.designs.map(d=>`<option value="${d.id}">${esc(d.name)}</option>`).join('');
      $(`compare-${side}`).addEventListener('change',refresh);
    }
    $('compare-right').value=catalog.recommendation.candidate_id;
    $('recommendation-text').textContent=catalog.recommendation.reason;
    $('cell').innerHTML=Array.from({length:65},(_,i)=>`<option value="${i}">${i+1}</option>`).join('');
    $('cell').addEventListener('change',inspectCell);
    $('design-cards').addEventListener('click',event=>{
      const button=event.target.closest('[data-design]');if(!button)return;
      $('compare-right').value=button.dataset.design;refresh();
    });
    document.querySelectorAll('[data-part]').forEach(button=>button.addEventListener('click',()=>{
      part=button.dataset.part;
      document.querySelectorAll('[data-part]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
      refresh();
    }));
    document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>{
      view=button.dataset.view;document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
      $('view-note').textContent=view==='flat'?'Geometria dos STL planos, com o campo calculado sobreposto. O aro permanece neutro.':'Rede equivalente de caminhos materiais sobre a ferramenta. A forma é prevista pelo solver; não é um STL sólido deformado nem uma simulação calibrada do polímero.';
      viewers.forEach(v=>{v.update();v.reset();});
    }));
    $('field').addEventListener('change',()=>{field=$('field').value;updateField();});
    $('reset-camera').addEventListener('click',()=>viewers.forEach(v=>v.reset()));
    try { viewers=[new Viewer('viewer-left'),new Viewer('viewer-right')]; } catch { viewers=[]; }
    await refresh();
  } catch(error) {
    $('app-status').textContent='Os resultados não puderam ser carregados. Recarregue a página.';console.error(error);
  }
}
await main();
