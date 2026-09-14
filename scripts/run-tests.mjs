import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
const python = process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python';
for (const [command, args] of [[process.execPath, ['--test', 'tests/data.test.mjs', 'tests/designs.test.mjs', 'tests/experiment.test.mjs', 'tests/catalog-selection.test.mjs']],
  [existsSync(python) ? python : 'python', ['-m', 'pytest', 'tests/test_analysis.py', 'tests/test_local_deformation.py', 'tests/test_physical.py', 'tests/test_parametric.py', '-q']]]) {
  const run = spawnSync(command, args, { stdio: 'inherit', env: { ...process.env, OPENBLAS_NUM_THREADS: '1', OMP_NUM_THREADS: '1' } });
  if (run.error) console.error(run.error.message);
  if (run.status !== 0) process.exit(run.status || 1);
}
