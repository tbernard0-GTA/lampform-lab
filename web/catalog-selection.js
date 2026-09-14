export const controls={topology:'topology',pitch:'pitch_mm',width:'base_width_mm',height:'base_height_mm',adaptation:'adaptation',wg:'width_response',hg:'height_response',budget:'material_budget_pct',equal:'equal_material',response:'response',orientation:'orientation_deg'};
export function selectComputed(entries,current,key,value){
 const pool=entries.filter(e=>e.part===current.part&&(key==='topology'||e.parameters.topology===current.parameters.topology));let available;
 if(typeof value==='number'){const distance=Math.min(...pool.map(e=>Math.abs(e.parameters[key]-value)));available=pool.filter(e=>Math.abs(Math.abs(e.parameters[key]-value)-distance)<1e-7);}
 else available=pool.filter(e=>e.parameters[key]===value);
 if(!available.length)return current;
 const score=e=>Object.values(controls).reduce((sum,k)=>{if(k===key||!Object.hasOwn(e.parameters,k))return sum;const a=current.parameters[k],b=e.parameters[k];if(typeof a==='number')return sum+Math.abs(a-b)/(k==='material_budget_pct'?10:1);return sum+(a===b?0:['topology','equal_material'].includes(k)?30:4);},0);
 return available.reduce((a,b)=>score(b)<score(a)?b:a);
}
