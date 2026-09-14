import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {selectComputed,controls} from '../web/catalog-selection.js';
const entries=JSON.parse(readFileSync(new URL('../dist/data/parametric/catalog.json',import.meta.url))).designs;
test('every control selects only an existing exact configuration of the same part',()=>{
 for(const current of entries)for(const key of Object.values(controls)){
  const choices=[...new Set(entries.map(e=>e.parameters[key]))];
  for(const value of choices){const result=selectComputed(entries,current,key,value);assert.ok(entries.includes(result));assert.equal(result.part,current.part);if(key!=='topology')assert.equal(result.parameters.topology,current.parameters.topology);}
 }
});
test('equal-volume comparison stays enabled while switching topology',()=>{
 for(const current of entries.filter(e=>e.parameters.equal_material))for(const topology of ['honeycomb','triangle','diamond']){
  const result=selectComputed(entries,current,'topology',topology);assert.equal(result.parameters.topology,topology);assert.equal(result.parameters.equal_material,true);
 }
});
test('unsupported adaptation never silently switches topology',()=>{
 const current=entries.find(e=>e.id==='triangle_uniform');assert.equal(selectComputed(entries,current,'adaptation','adaptive'),current);
});
