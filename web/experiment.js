export const columns='experiment_id sample_id date part design material filament_brand filament_batch nozzle_mm line_width_mm layer_height_mm print_temperature_c bed_temperature_c print_orientation heating_device heating_power heating_distance_mm heating_time_s surface_temperature_c forming_time_s hold_time_s cooling_time_s cell_id L1_before_mm L1_after_mm L2_before_mm L2_after_mm failure failure_type notes'.split(' ');
export const failures=['OK','stretched','opened','cracked','ruptured','wrinkled','other'];
export function parseCSV(text){
  const rows=[];let row=[],value='',quoted=false;
  text=text.replace(/^\uFEFF/,'');
  for(let i=0;i<text.length;i++){const c=text[i];if(c==='"'){if(quoted&&text[i+1]==='"'){value+='"';i++;}else quoted=!quoted;}else if(!quoted&&(c===','||c==='\n')){row.push(value.replace(/\r$/,''));value='';if(c==='\n'){if(row.some(v=>v.trim()))rows.push(row);row=[];}}else value+=c;}
  if(quoted)throw Error('CSV com aspas não fechadas.');row.push(value.replace(/\r$/,''));if(row.some(v=>v.trim()))rows.push(row);
  const header=rows.shift();if(!header||new Set(header).size!==header.length)throw Error('Cabeçalho ausente ou duplicado.');
  return rows.map((r,i)=>{if(r.length!==header.length)throw Error(`Linha ${i+2}: número de colunas diferente do cabeçalho.`);return Object.fromEntries(header.map((h,j)=>[h.trim(),r[j].trim()]));});
}
export function csv(rows){return [columns,...rows.map(r=>columns.map(k=>r[k]??''))].map(r=>r.map(v=>'"'+String(v).replaceAll('"','""')+'"').join(',')).join('\r\n');}
export function ranks(v){const sorted=v.map((value,i)=>({value,i})).sort((a,b)=>a.value-b.value);const out=[];for(let i=0;i<sorted.length;){let j=i+1;while(j<sorted.length&&sorted[j].value===sorted[i].value)j++;for(let k=i;k<j;k++)out[sorted[k].i]=(i+j-1)/2+1;i=j;}return out;}
export function spearman(x,y){if(x.length<3)return null;const a=ranks(x),b=ranks(y),am=a.reduce((s,v)=>s+v,0)/a.length,bm=b.reduce((s,v)=>s+v,0)/b.length;let cov=0,aa=0,bb=0;for(let i=0;i<a.length;i++){cov+=(a[i]-am)*(b[i]-bm);aa+=(a[i]-am)**2;bb+=(b[i]-bm)**2;}return aa&&bb?cov/Math.sqrt(aa*bb):null;}
export const groupKey=r=>[r.experiment_id,r.sample_id,r.part,r.design].join(' / ');
export function validateRows(rows,catalog){
  if(!Array.isArray(rows))throw Error('O JSON deve conter uma lista de medições.');const seen=new Set(),metadata=new Map();
  return rows.map((raw,i)=>{const r=Object.fromEntries(columns.map(k=>[k,String(raw[k]??'').trim()]));const design=catalog.designs.find(d=>d.id===r.design);
    if(!design?.[r.part]||!new RegExp(`^${r.part==='hab2'?'H':'S'}0(?:0[1-9]|[1-5][0-9]|6[0-5])$`).test(r.cell_id))throw Error(`Linha ${i+1}: peça, design ou célula inválidos.`);
    const values=['L1_before_mm','L1_after_mm','L2_before_mm','L2_after_mm'];const count=values.filter(k=>r[k]!=='').length;
    if(count&&count!==4)throw Error(`Linha ${i+1}: preencha as quatro medidas ou deixe todas vazias.`);
    if(count&&values.some(k=>!Number.isFinite(Number(r[k]))||Number(r[k])<=0))throw Error(`Linha ${i+1}: comprimentos devem ser positivos e finitos (use ponto decimal).`);
    const observed=count||r.failure!==''||r.failure_type!=='';
    if(observed&&(!r.experiment_id||!r.sample_id))throw Error(`Linha ${i+1}: uma observação exige experiment_id e sample_id.`);
    if(r.failure&&!['true','false','1','0'].includes(r.failure.toLowerCase()))throw Error(`Linha ${i+1}: failure deve ser true ou false.`);
    if(r.failure_type&&!failures.includes(r.failure_type))throw Error(`Linha ${i+1}: tipo de ocorrência inválido.`);
    const group=groupKey(r);for(const k of columns.slice(5,columns.indexOf('cell_id'))){if(!r[k])continue;const mk=group+' / '+k;if(metadata.has(mk)&&metadata.get(mk)!==r[k])throw Error(`Condições conflitantes na mesma amostra: ${k}`);metadata.set(mk,r[k]);}const key=group+' / '+r.cell_id;if(seen.has(key))throw Error(`Célula duplicada na mesma amostra: ${key}`);seen.add(key);
    return r;});
}
export function measurements(rows,cells){return rows.map(r=>{const c=cells.find(c=>c.cell_id===r.cell_id);if(!c)return null;const measured=r.L1_before_mm!=='';
  const l1=measured?Number(r.L1_after_mm)/Number(r.L1_before_mm):null,l2=measured?Number(r.L2_after_mm)/Number(r.L2_before_mm):null;
  return {...r,c,lambda1_measured:l1,lambda2_measured:l2,J_measured:measured?l1*l2:null,predicted:100*(c.lambda1-1),measured:measured?100*(l1-1):null,error:measured?100*(l1-c.lambda1):null,failed:r.failure===''?null:['true','1'].includes(r.failure.toLowerCase())};}).filter(Boolean);}
export function statistics(data){const pairs=data.filter(r=>r.measured!==null),n=pairs.length,k=Math.min(10,Math.max(1,Math.floor(n/3)));
  const pred=ranks(pairs.map(r=>r.predicted)),obs=ranks(pairs.map(r=>r.measured));pairs.forEach((r,i)=>r.rank_error=obs[i]-pred[i]);
  // Ties use fractional membership at the top-K boundary. K is bounded away
  // from n, avoiding a meaningless 100% hit with fewer than ten observations.
  const membership=values=>{const sorted=[...values].sort((a,b)=>b-a),cut=sorted[k-1],above=values.filter(v=>v>cut).length,tied=values.filter(v=>v===cut).length;return values.map(v=>v>cut?1:v===cut?(k-above)/tied:0);};
  const pm=membership(pairs.map(r=>r.predicted)),om=membership(pairs.map(r=>r.measured));
  const labeled=data.filter(r=>r.failed!==null),tp=labeled.filter(r=>r.c.demand>30&&r.failed).length,pp=labeled.filter(r=>r.c.demand>30).length,ap=labeled.filter(r=>r.failed).length;
  return {n,k,spearman:spearman(pairs.map(r=>r.predicted),pairs.map(r=>r.measured)),hit:n>=3?pm.reduce((s,v,i)=>s+Math.min(v,om[i]),0)/k:null,precision:pp?tp/pp:null,recall:ap?tp/ap:null,labeled:labeled.length,pairs};
}
