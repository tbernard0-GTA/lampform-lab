import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {comparison,baselineId,exactAlternative,stlPath,partName} from '../web/experiment-library.js';
import {buildPairFiles} from '../web/test-download.js';
const root=new URL('../',import.meta.url),read=p=>readFileSync(new URL(p,root)),cat=JSON.parse(read('dist/data/parametric/catalog.json'));
const entry=(part,id)=>cat.designs.find(e=>e.part===part&&e.id===id);
test('the combined Piece 2 experiment exposes improvements and worsening together',()=>{
 const c=comparison(entry('submerged','A_uniform'),entry('submerged','D_both'));
 assert.equal(c.status,'MIXED RESULT');assert.deepEqual(c.metrics.map(m=>m.direction),['better','better','worse']);assert.equal(c.metrics[2].before,94);assert.equal(c.metrics[2].after,100);assert.ok(c.materialDelta>9.8&&c.materialDelta<10.1);
});
test('status never confuses a control, similar results or a clear worsening with improvement',()=>{
 const a=entry('hab2','A_uniform');assert.equal(comparison(a,a).status,'CONTROL SAMPLE');
 const worse={...a,id:'worse',metrics:{...a.metrics,p95:a.metrics.p95+1}};assert.equal(comparison(a,worse).status,'NO CLEAR BENEFIT');
 const similar={...a,id:'similar',metrics:{...a.metrics,p95:a.metrics.p95-.05}};assert.equal(comparison(a,similar).status,'NO CLEAR BENEFIT');
 const good={...a,id:'good',metrics:{...a.metrics,p95:a.metrics.p95-1}};assert.equal(comparison(a,good).status,'PROMISING CANDIDATE');
});
test('topology comparison uses the equal-volume baseline and material denominator',()=>{
 const d=entry('hab2','diamond_equal'),a=entry('hab2',baselineId(d));assert.equal(a.id,'honeycomb_equal');assert.ok(Math.abs(comparison(a,d).materialDelta)<.01);
});
test('fine tuning requires exact existing combinations, not snapping',()=>{
 const a=entry('hab2','A_uniform');assert.equal(exactAlternative(cat.designs,a,'base_width_mm',1.13),null);assert.equal(exactAlternative(cat.designs,a,'base_width_mm',1.2).id,'uniform_w12_h10');assert.equal(exactAlternative(cat.designs,entry('hab2','B_width'),'base_width_mm',1.2),null);
});
test('all backend, catalogue, metric and original export bytes stay frozen',()=>{
 const manifest=JSON.parse(read('docs/V09_FROZEN_DATA.json'));for(const [path,hash] of Object.entries(manifest))assert.equal(createHash('sha256').update(read(path)).digest('hex'),hash,path);
});
test('friendly part names point to byte-identical STL files for every design',()=>{
 for(const e of cat.designs){assert.match(partName(e.part),/^Peça [12]$/);assert.equal(createHash('sha256').update(read('dist'+stlPath(e))).digest('hex'),e.validation.sha256);}
});
test('test-pair download includes the correct reference, candidate, mold and comparison',async()=>{
 const originalFetch=globalThis.fetch;globalThis.fetch=async url=>{try{const data=read('dist'+url);return {ok:true,arrayBuffer:async()=>data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength)};}catch{return {ok:false};}};
 try{for(const id of ['D_both','diamond_equal','uniform_w12_h10']){const e=entry('submerged',id),ref=entry('submerged',baselineId(e)),r=await buildPairFiles(ref,e);assert.match(r.name,/^peca-2-/);assert.equal(createHash('sha256').update(r.files['peca-2-referencia.stl']).digest('hex'),ref.validation.sha256);assert.ok(r.files['molde-peca-2.stl']);assert.ok(r.files['comparacao.png']);const m=JSON.parse(new TextDecoder().decode(r.files['metrics.json']));assert.equal(m.candidate.p95,e.metrics.p95);}}
 finally{globalThis.fetch=originalFetch;}
});
