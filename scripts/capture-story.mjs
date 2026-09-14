import {spawnSync} from 'node:child_process';
import {existsSync} from 'node:fs';
const local=process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python';
const run=spawnSync(existsSync(local)?local:'python',['scripts/capture_story.py'],{stdio:'inherit',env:{...process.env,OPENBLAS_NUM_THREADS:'1',OMP_NUM_THREADS:'1'}});
if(run.error)throw run.error;process.exitCode=run.status??1;
