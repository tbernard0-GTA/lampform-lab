import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const root = new URL('../', import.meta.url);
const read = path => readFile(new URL(path, root), 'utf8');
const summary = JSON.parse(await read('legacy/lampform_lab_v01/results_v02/summary_v02.json'));
for (const [i, slug] of ['hab2_mold', 'submerged_push'].entries()) {
  test(`${slug}: meshes retain the source geometry and provenance`, async () => {
    const data = JSON.parse(await read(`dist/data/${slug}.json`));
    for (const mesh of [data.lamp, data.tool]) {
      const original = await readFile(new URL(`legacy/lampform_lab_v01/${mesh.file}`, root));
      assert.equal(mesh.sha256, createHash('sha256').update(original).digest('hex'));
      assert.equal(mesh.indices.length / 3, original.readUInt32LE(80));
      assert.ok(mesh.positions.every(Number.isFinite));
      assert.ok(mesh.indices.every(index => Number.isInteger(index) && index >= 0 && index < mesh.positions.length / 3));
      assert.ok(mesh.dimensions.every(n => n > 0 && n < 500));
    }
  });
  test(`${slug}: displayed metrics match the supplied solver output and network`, async () => {
    const data = JSON.parse(await read(`dist/data/${slug}.json`));
    assert.deepEqual(data.summary, summary[i]);
    assert.equal(data.edges.length, data.summary.ligaments);
    for (const edge of data.edges) {
      assert.equal(edge.flat.length, 6); assert.equal(edge.formed.length, 6);
      assert.ok([...edge.flat, ...edge.formed, edge.demand].every(Number.isFinite));
      const length = vector => Math.hypot(vector[3] - vector[0], vector[4] - vector[1], vector[5] - vector[2]);
      assert.ok(Math.abs((length(edge.formed) / length(edge.flat) - 1) * 100 - edge.demand) < 1e-8);
    }
    const demands = data.edges.map(e => e.demand).sort((a, b) => a - b);
    const index = (demands.length - 1) * .95;
    const p95 = demands[Math.floor(index)] + (index % 1) * (demands[Math.ceil(index)] - demands[Math.floor(index)]);
    assert.ok(Math.abs(p95 - data.summary.relaxed.p95_strain_pct) < 1e-8);
    const base = data.sensitivity.find(row => row.boundary_anchor === 2);
    assert.equal(base.p95_strain_pct, data.summary.relaxed.p95_strain_pct);
    assert.deepEqual(data.sensitivity.map(row => row.boundary_anchor), [5, 2, 1, .5, .2, .05]);
  });
}
