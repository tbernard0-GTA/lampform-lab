export const hypotheses=[
 {id:'A_uniform',name:'Original',test:'Controle',sample:'A',description:'Malha uniforme. A referência do experimento.'},
 {id:'B_width',name:'Largura',test:'Teste de largura',sample:'B',description:'Redistribui a largura dos ligamentos conforme a deformação.'},
 {id:'C_height',name:'Altura',test:'Teste de altura',sample:'C',description:'Redistribui a altura local da impressão.'},
 {id:'D_both',name:'Largura + altura',test:'Teste combinado',sample:'D',description:'Usa as duas variáveis no mesmo desenho.'}
];
export const partName=p=>p==='hab2'?'Peça 1':'Peça 2';
export const partSlug=p=>p==='hab2'?'peca-1':'peca-2';
export const partId=p=>p==='peca-1'?'hab2':p==='peca-2'?'submerged':p;
export const designSlug=id=>({A_uniform:'controle',B_width:'largura',C_height:'altura',D_both:'combinada',honeycomb_equal:'hexagonal-volume-equivalente',triangle_equal:'triangular-volume-equivalente',diamond_equal:'losango-volume-equivalente'}[id]||id.replaceAll('_','-'));
export const stlPath=e=>`/downloads/${partSlug(e.part)}/${partSlug(e.part)}-${designSlug(e.id)}.stl`;
export const imagePath=(p,id)=>`/media/tests/${partSlug(p)}-${id}.png`;
export const baselineId=entry=>entry.parameters.equal_material?'honeycomb_equal':'A_uniform';
export function metricDirection(before,after,tolerance=0){return Math.abs(after-before)<=tolerance?'similar':after<before?'better':'worse';}
export function comparison(reference,current){
 const a=reference.metrics,b=current.metrics;
 const metrics=[['p95','Demanda P95','95% dos ligamentos ficam abaixo deste valor.',.1,'%'],['maximum','Demanda máxima','O ligamento com maior demanda.',.1,'%'],['critical_edges','Regiões críticas','Ligamentos com demanda acima de 30%.',0,'']].map(([key,label,question,tolerance,unit])=>({key,label,question,before:a[key],after:b[key],unit,direction:metricDirection(a[key],b[key],tolerance)}));
 const better=metrics.filter(m=>m.direction==='better'),worse=metrics.filter(m=>m.direction==='worse');
 const control=reference.id===current.id;
 const status=control?'CONTROL SAMPLE':better.length&&worse.length?'MIXED RESULT':better.length?'PROMISING CANDIDATE':'NO CLEAR BENEFIT';
 const labels=items=>items.map(m=>m.label.toLowerCase()).join(' e ');
 const explanation=control?'Esta é a referência para comparar as outras hipóteses.':status==='MIXED RESULT'?`Reduz ${labels(better)}, mas aumenta ${labels(worse)}. Útil como experimento; não demonstra uma melhora geral.`:status==='PROMISING CANDIDATE'?`Reduz ${labels(better)} sem piora relevante nas demais métricas. Promissor neste modelo; precisa de ensaio físico.`:worse.length?`Aumenta ${labels(worse)} sem benefício claro nas demais métricas. Serve para testar a hipótese, não como melhoria comprovada.`:'As diferenças ficam dentro do limiar de similaridade. Não há benefício claro neste modelo.';
 return {metrics,status,explanation,materialDelta:100*(b.lattice_volume_mm3/a.lattice_volume_mm3-1)};
}
// Only exact parameter combinations can be selected. No nearest-value search.
export function exactAlternative(entries,current,key,value){
 const keys=['topology','pitch_mm','base_width_mm','base_height_mm','orientation_deg','adaptation','response','width_response','height_response','material_budget_pct','equal_material'];
 return entries.find(e=>e.part===current.part&&keys.every(k=>Math.abs(Number(e.parameters[k])-Number(k===key?value:current.parameters[k]))<1e-8||e.parameters[k]===(k===key?value:current.parameters[k])))||null;
}
