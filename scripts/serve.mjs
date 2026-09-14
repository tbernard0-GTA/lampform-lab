import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve, extname, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFile } from 'node:child_process';

const root = fileURLToPath(new URL('../dist/', import.meta.url));
const port = Number(process.env.PORT || 4173);
const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png' };
const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, 'http://localhost');
    const route=url.pathname.replace(/\/$/,'');
    const pathname = ['/design','/test','/advanced'].includes(route) ? route+'/index.html' : url.pathname === '/' ? '/index.html' : url.pathname;
    const path = resolve(root, '.' + decodeURIComponent(pathname));
    if (!path.startsWith(resolve(root) + sep)) { res.writeHead(403).end(); return; }
    const data = await readFile(path);
    res.writeHead(200, { 'Content-Type': types[extname(path)] || 'application/octet-stream', 'X-Content-Type-Options': 'nosniff' });
    res.end(data);
  } catch { res.writeHead(404).end('Arquivo não encontrado.'); }
});
server.on('error', error => { console.error(error.message); process.exitCode = 1; });
server.listen(port, '127.0.0.1', () => {
  console.log(`LampForm Lab: http://localhost:${port}`);
  if (process.argv.includes('--open') && process.platform === 'win32') {
    execFile('powershell.exe', ['-NoProfile', '-Command', `Start-Process 'http://localhost:${port}'`], { windowsHide: true }, () => {});
  }
});
