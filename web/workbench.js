import { Viewer } from './workbench-viewer.js';
const $=id=>document.getElementById(id);
const fmt=(n,d=1)=>Number(n).toLocaleString('pt-BR',{minimumFractionDigits:d,maximumFractionDigits:d});
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
const signed=(n,d=1)=>(n>0?'+':'')+fmt(n,d);
let catalog,part='hab2',selectedId,original,data,ticket=0,viewers=[],syncing=false,mapMode='field',sortKey='id',sortAsc=true,animation=null;
const cache=new Map();
const fields={demand:['Deformation demand','%'],delta:['Candidate − original',' p.p.'],width:['Ligament width',' mm'],hole_size:['Hole size equivalente',' mm'],compliance:['Caminho / corda','×'],xy_feed:['XY feed',' mm'],geometry_change:['Magnitude da intervenção',' mm']};
const S={view:'flat',representation:'stl',field:'demand',step:4,ghost:true,highlight:null,
  sync(source){if(syncing)return;syncing=true;for(const other of viewers)if(other!==source){other.camera.position.copy(source.camera.position);other.controls.target.copy(source.controls.target);other.controls.update();other.render();}syncing=false;},
  error(message){$('app-status').hidden=false;$('app-status').textContent=message;},
  color:(value)=>color(value,S.field),value:(edge,d)=>edgeValue(edge,d,S.field)};
const item=()=>catalog.designs.find(d=>d.id===selectedId);
const baseline=()=>catalog.designs[0][part];
function color(value,field){
  const ranges=catalog.common_color_ranges,[lo,hi]=ranges[field];let t=Math.max(0,Math.min(1,(value-lo)/(hi-lo)));
  const stops=field==='delta'?['#1860b6','#f9faf7','#c22632']:field==='demand'?['#527f65','#d7bc48','#e67b28','#d83632','#6e1022']:['#d9e4cd','#749c70','#244d50'];
  const z=t*(stops.length-1),i=Math.min(stops.length-2,Math.floor(z)),f=z-i;
  const rgb=hex=>hex.match(/\w\w/g).map(v=>parseInt(v,16));const a=rgb(stops[i].slice(1)),b=rgb(stops[i+1].slice(1));
  return `rgb(${a.map((v,k)=>Math.round(v+(b[k]-v)*f)).join(',')})`;
}
function nearestCell(edge,d){const x=(edge.flat[0]+edge.flat[3])/2,y=(edge.flat[1]+edge.flat[4])/2;let best=Infinity,result=d.cells[0];for(const c of d.cells){const p=c.candidate.slice(0,-1),cx=p.reduce((s,q)=>s+q[0],0)/p.length,cy=p.reduce((s,q)=>s+q[1],0)/p.length,dist=(x-cx)**2+(y-cy)**2;if(dist<best){best=dist;result=c;}}return result;}
function edgeValue(e,d,field){
  if(field==='hole_size')return nearestCell(e,d).hole_size;
  if(field==='geometry_change'){
    if(d.id==='original')return 0;const src=original.edges.find(x=>x.parent===e.parent),a=e.flat,b=src.flat;
    return Math.abs(e.width_change)+Math.hypot((a[0]+a[3]-b[0]-b[3])/2,(a[1]+a[4]-b[1]-b[4])/2);
  }
  return e[field];
}
function recordRow(label,a,b,unit='',digits=1){return `<tr><td>${label}</td><td>${fmt(a,digits)}${unit}</td><td>${fmt(b,digits)}${unit}</td><td>${signed(b-a,digits)}${unit==='%'?' p.p.':unit}</td></tr>`;}
function panels(){
  const d=item(),r=d[part],a=baseline().metrics,b=r.metrics,g=r.gate;
  $('selected-gate').textContent=g.status+' · '+(d.gate.passed?'PAR APROVADO':'PAR NÃO APROVADO');$('selected-gate').dataset.status=g.status;
  $('risk-table').innerHTML=[['Ligamentos críticos >30%','critical_edges','',0],['Células críticas >30%','critical_cells','',0],['Ligamentos >20%','above_20_pct','%'],['Ligamentos >30%','critical_pct','%'],['P90','p90','%'],['P95','p95','%'],['P99','p99','%'],['Máximo','maximum','%'],['Média dos 10 maiores','top10_mean','%'],['Risk Index','risk_index','',3]].map(([label,k,u,n])=>recordRow(label,a[k],b[k],u,n??1)).join('');
  const parents=[...new Map(data.edges.map(e=>[e.parent,e])).values()];
  $('danger-summary').textContent=`${parents.filter(e=>e.delta<-.1).length} ligamentos melhoraram; ${parents.filter(e=>e.delta>.1).length} pioraram (>0,1 p.p.). Pico: ${signed(b.maximum-a.maximum)} p.p. Tolerância do gate: +5 p.p.`;
  $('regions').innerHTML=data.top_regions.map(r=>`<tr class="selectable" data-region="${r.id}"><td><button data-region="${r.id}">L${r.id}</button></td><td>${fmt(r.x,2)}</td><td>${fmt(r.y,2)}</td><td>${fmt(r.baseline)}%</td><td>${fmt(r.candidate)}%</td><td class="${r.delta>0?'worse':'better'}">${signed(r.delta)}</td></tr>`).join('');
  $('manufacturing-table').innerHTML=[['Material projetado','material_area_proxy',' mm²'],['Volume proxy','mass_proxy',' mm³'],['Área aberta','open_area','%'],['Largura mínima dos caminhos','minimum_ligament_width',' mm',2],['Geometria plana alterada','geometry_change_pct','%'],['XY feed médio','mean_xy_feed',' mm',2],['XY feed máximo','max_xy_feed',' mm',2]].map(([l,k,u,n])=>recordRow(l,a[k],b[k],u,n??1)).join('')+recordRow('Complexidade · faces',baseline().validation.face_count,r.validation.face_count,'',0);
  const labels={watertight:'Watertight',single_body:'Single body',geometry:'Faces / winding',bounds:'Bounds',min_ligament:'Min ligament',aperture_probe:'Main-cell gap probe'};
  $('geometry-validation').innerHTML=Object.entries(labels).map(([key,label])=>`<div><span>${label}</span><strong class="${g.checks[key]?'better':'worse'}">${g.checks[key]?'PASS':'FAIL'}</strong></div>`).join('');
  $('source-note').textContent='Original preservado: 503 faces duplicadas por peça e malha não watertight. Os candidatos são novos sólidos. Validação geométrica não garante melhora estrutural nem qualquer perfil de impressão.';
  const mechanism={original:'Referência fornecida, preservada byte a byte. O baseline é recalculado com o mesmo modelo dos candidatos.',reserve:'Material reserve: furos menores aumentam a largura local. A hipótese é redistribuir a demanda; o mapa delta verifica se surgem novos picos.',boundary:'Boundary compliance: o núcleo é contraído e ligado ao aro por conectores curvos reais. Comprimento e largura entram no solver. A mudança de pitch também faz parte deste candidato.',hybrid:'Hybrid: combina reserva de material e transição flexível. A hipótese é distribuir demanda no núcleo e permitir alimentação junto ao aro, sem ocultar picos nos conectores.'};
  $('mechanism').textContent=mechanism[d.family];$('why-data').textContent=r.why;
  $('solver-detail').textContent=`Solver: ${r.solver.message} Custo ${fmt(r.solver.cost,4)}; optimality ${fmt(r.solver.optimality,4)}. Mesma ancoragem do aro em todos os designs. São mínimos locais de um modelo aproximado.`;
  $('score-detail').textContent=`Score v0.4 secundário: ${fmt(r.score.value,3)}; combinado ${fmt(d.combined_score,3)}. Componentes normalizados: ${Object.entries(r.score.components).map(([k,v])=>k+' '+fmt(v,3)).join(' · ')}. Este score não aprova o print gate.`;
  $('download-title').textContent=d.name;$('download-reason').textContent=d.gate.passed?'RECOMMENDED FOR PRINT TEST · os dois STL passam nos gates desta rodada.':`SEM RECOMENDAÇÃO CONJUNTA. ${d.gate.reasons.join(' · ')}. Downloads para investigação.`;
  $('download-zip').href=d.zip;$('download-hab2').href=d.hab2.stl;$('download-submerged').href=d.submerged.stl;$('download-metrics').href=`downloads/${d.id}/metrics.json`;
  $('caption-left').textContent=`${part==='hab2'?'HAB-2 → Mold':'Sub-Merged → Push'} · 246 ligamentos · referência`;
  $('caption-right').textContent=`${d.name} · 246 ligamentos · câmeras sincronizadas`;
  inspectCell();matrix();pareto('pareto-risk','material_change_pct','risk_index','Material Δ (%)','Risk Index');pareto('pareto-open','open_area','p95','Área aberta (%)','P95 (%)');
}
function points(coords){return coords.map(p=>`${p[0]},${-p[1]}`).join(' ');}
function changedCell(c){return Math.abs(c.hole_size-c.original_hole_size)>.01||Math.abs(c.ligament_width-c.original_ligament_width)>.01;}
function map(d,side){
  const overlay=mapMode==='overlay'&&side==='right',effective=mapMode==='delta'?'delta':mapMode==='feed'?'xy_feed':S.field,only=$('changed-only').checked;
  let drawing=only?'':`<path d="${esc(d.footprint_svg)}" fill="#c3ccba" fill-rule="evenodd"/>`;
  if(overlay){drawing=only?'':`<path d="${esc(d.footprint_svg)}" fill="#628672" fill-rule="evenodd" opacity=".5"/><path d="${esc(original.footprint_svg)}" fill="none" stroke="#444" stroke-width=".13" stroke-dasharray=".5 .35"/>`;}
  for(const e of d.edges){
    const changed=side==='right'&&edgeValue(e,d,'geometry_change')>.015;if(only&&!changed)continue;
    const p=e.flat,active=e.parent===S.highlight;
    const c=active?'#dc22ba':overlay?'#226450':color(edgeValue(e,d,effective),effective);
    if(!overlay||only)drawing+=`<path d="M${p[0]},${-p[1]} L${p[3]},${-p[4]}" fill="none" stroke="${c}" stroke-width="${active?1.3:Math.min(e.width,.8)}" stroke-linecap="round"/>`;
    if(mapMode==='feed'&&e.parent%3===0&&e===d.edges.find(k=>k.parent===e.parent)){
      const scale=Number($('arrow-scale').value),x=p[0],y=-p[1],dx=(e.formed[0]-p[0])*scale,dy=-(e.formed[1]-p[1])*scale;
      drawing+=`<path d="M${x},${y} l${dx},${dy}" stroke="#15344d" stroke-width=".25" marker-end="url(#arrow-${side})"/>`;
    }
  }
  for(const c of d.cells){
    if(only&&!changedCell(c))continue;const active=c.id===Number($('cell').value);
    if(overlay)drawing+=`<polygon points="${points(c.original)}" fill="none" stroke="#515851" stroke-width=".18" stroke-dasharray=".6 .4"/><polygon points="${points(c.candidate)}" fill="none" stroke="#226450" stroke-width=".3"/>`;
    const border=active?'#cf18af':effective==='hole_size'?color(c.hole_size,'hole_size'):'transparent';
    drawing+=`<polygon data-cell="${c.id}" tabindex="0" role="button" aria-label="Inspecionar célula ${c.id+1}" points="${points(c.candidate)}" fill="transparent" stroke="${border}" stroke-width="${active?.4:.25}"><title>Célula ${c.id+1}: ${fmt(c.baseline_demand)} → ${fmt(c.candidate_demand)}%; Δ ${signed(c.delta)} p.p.</title></polygon>`;
  }
  $(`heatmap-${side}`).innerHTML=`<svg viewBox="-42 -54 84 110" aria-label="Mapa plano ${side==='left'?'original':'candidato'}"><defs><marker id="arrow-${side}" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto"><path d="M0,0 L4,2 L0,4" fill="#15344d"/></marker></defs>${drawing}</svg>`;
}
function maps(){if(!data)return;map(original,'left');map(data,'right');$('map-caption').textContent=item().name;
  $('map-note').textContent=mapMode==='delta'?'Δ = candidato − original · azul −30 p.p. / branco 0 / vermelho +30 p.p. · extremos saturam':mapMode==='overlay'?`${fmt(data.metrics.geometry_change_pct)}% da geometria plana alterada (diferença simétrica / união).`:mapMode==='feed'?`Setas ${$('arrow-scale').value}× · média ${fmt(data.metrics.mean_xy_feed,2)} mm · máximo ${fmt(data.metrics.max_xy_feed,2)} mm`:'Mesmo campo e escala dos viewers 3D.';
}
function inspectCell(){if(!data)return;const c=data.cells[Number($('cell').value)||0];
  // Overlay preserves original XY location: contractions stay visible.
  const all=[...c.original,...c.candidate],xs=all.map(p=>p[0]),ys=all.map(p=>-p[1]),x=Math.min(...xs)-.5,y=Math.min(...ys)-.5,w=Math.max(...xs)-x+.5,h=Math.max(...ys)-y+.5;
  $('cell-preview').innerHTML=`<svg viewBox="${x} ${y} ${w} ${h}" aria-label="Overlay da célula ${c.id+1}"><polygon points="${points(c.candidate)}" fill="#dbe6c9" stroke="#225c4d" stroke-width=".14"/><polygon points="${points(c.original)}" fill="none" stroke="#535d52" stroke-width=".12" stroke-dasharray=".3 .2"/></svg>`;
  $('cell-risk').textContent=`Cell ${c.id+1} · ${c.risk_original} → ${c.risk_candidate}`;
  $('cell-values').innerHTML=recordRow('Hole size',c.original_hole_size,c.hole_size,' mm',2)+recordRow('Ligamento médio',c.original_ligament_width,c.ligament_width,' mm',2)+recordRow('Demanda',c.baseline_demand,c.candidate_demand,'%',1);
}
function update(){if(!catalog)return;const [lo,hi]=catalog.common_color_ranges[S.field];$('legend-title').textContent=fields[S.field][0];$('legend-low').textContent=fmt(lo)+fields[S.field][1];$('legend-high').textContent=fmt(hi)+fields[S.field][1]+'+';
  $('color-ramp').style.background=`linear-gradient(90deg,${Array.from({length:9},(_,i)=>color(lo+(hi-lo)*i/8,S.field)).join(',')})`;
  $('forming-controls').hidden=S.view!=='formed';$('representation').disabled=S.view==='formed';
  $('view-note').textContent=S.view==='formed'?`Solver network · etapa real ${S.step*25}% da continuação. Rede aproximada sobre a ferramenta; não é um STL sólido deformado. As cores mostram a demanda FINAL de 100% em todas as etapas.`:S.representation==='stl'?'Actual printable STL: vértices e faces do arquivo que será baixado, com campo associado ao caminho estrutural mais próximo. Arraste para girar os dois modelos.':'Solver network: caminhos materiais usados no cálculo. A geometria sólida exata está em Actual printable STL.';
  viewers.forEach(v=>v.update());maps();
}
const columns=[['Design','id'],['P95','p95'],['P99','p99'],['Max','maximum'],['Critical %','critical_pct'],['Risk','risk_index'],['Material Δ','material_change_pct'],['Open area','open_area'],['Gate','gate']];
function matrix(){const val=(d,k)=>k==='id'?d.name:k==='gate'?d[part].gate.status:d[part].metrics[k];
  $('matrix-head').innerHTML=columns.map(([l,k])=>`<th aria-sort="${sortKey===k?(sortAsc?'ascending':'descending'):'none'}"><button data-sort="${k}">${l}${sortKey===k?(sortAsc?' ↑':' ↓'):''}</button></th>`).join('');
  const rows=[...catalog.designs].sort((a,b)=>{const av=val(a,sortKey),bv=val(b,sortKey);return (typeof av==='string'?av.localeCompare(bv):av-bv)*(sortAsc?1:-1);});
  $('matrix-body').innerHTML=rows.map(d=>`<tr ${d.id===selectedId?'class="selected-row"':''}>${columns.map(([l,k])=>`<td>${k==='id'?`<button data-design="${d.id}">${esc(d.name)}</button>`:k==='gate'?`<span class="gate" data-status="${d[part].gate.status}">${d[part].gate.status}</span>`:fmt(val(d,k),k==='risk_index'?3:1)}</td>`).join('')}</tr>`).join('');
}
function pareto(id,xKey,yKey,xTitle,yTitle){
  const values=catalog.designs.map(d=>({d,x:d[part].metrics[xKey],y:d[part].metrics[yKey]}));
  const xs=values.map(p=>p.x),ys=values.map(p=>p.y),xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys),ymax=Math.max(...ys),dx=(xmax-xmin)||1,dy=(ymax-ymin)||1;
  const X=x=>55+(x-xmin)/dx*340,Y=y=>245-(y-ymin)/dy*200;
  const colors={original:'#222c24',reserve:'#267aa0',boundary:'#d66d24',hybrid:'#8867ae'};
  let svg=`<svg viewBox="0 0 450 310" role="img" aria-label="${xTitle} versus ${yTitle}"><path d="M55 35 V245 H405" fill="none" stroke="#899485"/>`;
  for(let i=0;i<=4;i++){const x=xmin+dx*i/4,y=ymin+dy*i/4;svg+=`<text x="${X(x)}" y="265" text-anchor="middle">${fmt(x)}</text><text x="48" y="${Y(y)+4}" text-anchor="end">${fmt(y)}</text>`;}
  for(const {d,x,y} of values)svg+=`<circle data-design="${d.id}" tabindex="0" role="button" aria-label="Selecionar ${esc(d.name)}" cx="${X(x)}" cy="${Y(y)}" r="${d.id==='original'?6:5}" fill="${colors[d.family]}" stroke="${d.id===selectedId?'#171b18':'white'}" stroke-width="${d.id===selectedId?3:1}"><title>${esc(d.name)}: ${xTitle} ${fmt(x)}; ${yTitle} ${fmt(y,3)}</title></circle>`;
  svg+=`<text x="230" y="294" text-anchor="middle">${xTitle}</text><text x="12" y="140" transform="rotate(-90 12 140)" text-anchor="middle">${yTitle}</text></svg><p class="fine">● Original · <span style="color:#267aa0">● Reserve</span> · <span style="color:#d66d24">● Boundary</span> · <span style="color:#8867ae">● Hybrid</span></p>`;$(id).innerHTML=svg;
}
function explorer(){const d=item();$('candidate').value=d.id;$('family').value=d.family;const group=catalog.designs.filter(v=>v.family===d.family);$('intensity').innerHTML=group.map(v=>`<option value="${v.id}">${esc(v.intensity)}</option>`).join('');$('intensity').value=d.id;}
async function load(record){if(!cache.has(record.data)){const r=await fetch(record.data);if(!r.ok)throw new Error('Dataset unavailable');cache.set(record.data,await r.json());}return cache.get(record.data);}
async function refresh(){const rev=++ticket;S.error('Carregando geometrias e campos…');try{
  const [a,b]=await Promise.all([load(baseline()),load(item()[part])]);if(rev!==ticket)return;original=a;data=b;S.highlight=null;explorer();panels();
  viewers[0]?.setData(a);viewers[1]?.setData(b);viewers.forEach(v=>v.reset());update();$('app-status').hidden=viewers.length===2;if(!viewers.length)S.error('3D indisponível. Use os mapas planos, tabelas e STL.');
}catch(e){if(rev!==ticket)return;data=null;original=null;viewers.forEach(v=>v.clear());['download-zip','download-hab2','download-submerged','download-metrics'].forEach(id=>$(id).removeAttribute('href'));S.error('Falha ao carregar a seleção. Recarregue a página.');console.error(e);}}
function select(id){if(!catalog.designs.some(d=>d.id===id))return;selectedId=id;refresh();}
function toggle(button,attr){document.querySelectorAll(`[${attr}]`).forEach(b=>b.setAttribute('aria-pressed',String(b===button)));}
function selectCell(id){$('cell').value=id;inspectCell();maps();}
async function main(){try{
  const r=await fetch('data/results.json');if(!r.ok)throw new Error('Results unavailable');catalog=await r.json();selectedId=catalog.recommendation.candidate_id||catalog.inspection_default_id;
  $('candidate').innerHTML=catalog.designs.map(d=>`<option value="${d.id}">${esc(d.name)}</option>`).join('');
  $('cell').innerHTML=Array.from({length:65},(_,i)=>`<option value="${i}">${i+1}</option>`).join('');
  const rec=catalog.recommendation;$('print-status').textContent=rec.status;$('print-reason').textContent=rec.reason+` ${catalog.attempts} designs avaliados; limite ${catalog.search_limit}.`;$('print-candidate').dataset.pass=String(!!rec.candidate_id);
  if(rec.zip)$('print-links').innerHTML=`<a href="${rec.hab2_stl}" download>HAB-2 TEST V1 ↓</a><a href="${rec.submerged_stl}" download>SubMerged TEST V1 ↓</a><a href="${rec.zip}" download>LAMPFORM_PRINT_TEST_V1.zip ↓</a>`;
  $('candidate').addEventListener('change',()=>select($('candidate').value));$('intensity').addEventListener('change',()=>select($('intensity').value));$('family').addEventListener('change',()=>select(catalog.designs.find(d=>d.family===$('family').value).id));
  document.querySelectorAll('[data-part]').forEach(b=>b.addEventListener('click',()=>{part=b.dataset.part;toggle(b,'data-part');refresh();}));
  document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>{S.view=b.dataset.view;toggle(b,'data-view');update();viewers.forEach(v=>v.reset());}));
  document.querySelectorAll('[data-map]').forEach(b=>b.addEventListener('click',()=>{mapMode=b.dataset.map;toggle(b,'data-map');maps();}));
  $('field').addEventListener('change',()=>{S.field=$('field').value;update();});$('representation').addEventListener('change',()=>{S.representation=$('representation').value;update();});
  $('forming-step').addEventListener('change',()=>{S.step=Number($('forming-step').value);update();});$('ghost').addEventListener('change',()=>{S.ghost=$('ghost').checked;update();});
  $('play-forming').addEventListener('click',()=>{if(animation){clearInterval(animation);animation=null;$('play-forming').textContent='Reproduzir etapas';return;}S.step=0;S.view='formed';update();$('play-forming').textContent='Pausar';animation=setInterval(()=>{S.step=(S.step+1)%5;$('forming-step').value=S.step;update();},1000);});
  $('reset-camera').addEventListener('click',()=>viewers.forEach(v=>v.reset()));$('changed-only').addEventListener('change',maps);$('arrow-scale').addEventListener('change',maps);$('cell').addEventListener('change',()=>selectCell($('cell').value));
  $('clear-highlight').addEventListener('click',()=>{S.highlight=null;update();});
  document.addEventListener('click',e=>{const region=e.target.closest('[data-region]'),cell=e.target.closest('[data-cell]'),design=e.target.closest('[data-design]'),sort=e.target.closest('[data-sort]');
    if(region){S.highlight=Number(region.dataset.region);update();$('workspace').scrollIntoView({behavior:'smooth'});}else if(cell){selectCell(cell.dataset.cell);$('cell-preview').scrollIntoView({behavior:'smooth',block:'center'});}else if(design)select(design.dataset.design);else if(sort){sortAsc=sortKey===sort.dataset.sort?!sortAsc:true;sortKey=sort.dataset.sort;matrix();}});
  document.addEventListener('keydown',e=>{if(['Enter',' '].includes(e.key)&&e.target.matches('[data-cell],[data-design]')){e.preventDefault();e.target.dispatchEvent(new MouseEvent('click',{bubbles:true}));}});
  try{viewers=[new Viewer($('viewer-left'),S),new Viewer($('viewer-right'),S)];}catch(e){viewers=[];console.warn(e);}
  await refresh();
}catch(e){S.error('Resultados indisponíveis. Recarregue a página.');console.error(e);}}
await main();
