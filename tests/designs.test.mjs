import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const root=new URL('../',import.meta.url),bytes=p=>readFile(new URL(p,root)),json=async p=>JSON.parse(await bytes(p));
const catalog=await json('dist/data/results.json');
test('bounded design space and recommendation gated on both parts',()=>{
  assert.ok(catalog.designs.length>=10&&catalog.designs.length<=13);
  assert.deepEqual(catalog.designs.slice(0,10).map(d=>d.id),['original','reserve_low','reserve_medium','reserve_high','boundary_low','boundary_medium','boundary_high','hybrid_low','hybrid_medium','hybrid_high']);
  const accepted=catalog.designs.filter(d=>d.hab2.gate.passed&&d.submerged.gate.passed).sort((a,b)=>a.combined_risk-b.combined_risk);
  assert.equal(catalog.recommendation.candidate_id,accepted[0]?.id||null);
  assert.deepEqual(catalog.common_color_ranges.demand,[0,40]);
});
for(const design of catalog.designs)for(const part of ['hab2','submerged'])test(`${design.id}/${part}: actual STL, metrics, stages and correspondence`,async()=>{
  const record=design[part],data=await json(`dist/${record.data}`);
  assert.deepEqual(data.metrics,record.metrics);assert.equal(data.parent_count,246);assert.equal(data.cells.length,65);
  assert.equal(createHash('sha256').update(await bytes(`dist/${record.stl}`)).digest('hex'),record.validation.sha256);
  const length=a=>Math.hypot(a[3]-a[0],a[4]-a[1],a[5]-a[2]);
  for(const e of data.edges){assert.ok(Math.abs(100*(length(e.formed)/length(e.flat)-1)-e.demand)<1e-7);assert.equal(e.stages.length,5);assert.deepEqual(e.stages[4],e.formed);assert.equal(e.delta,e.parent_demand-e.baseline_demand);assert.ok(e.width>=.8);}
  for(const c of data.cells){assert.equal(c.delta,c.candidate_demand-c.baseline_demand);assert.ok(c.hole_size>0&&c.candidate.length>3);}
  assert.ok(data.lamp.positions.every(Number.isFinite));assert.ok(data.tool.positions.every(Number.isFinite));
});
