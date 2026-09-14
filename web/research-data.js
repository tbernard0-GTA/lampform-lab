const cache=new Map();
export async function json(path){const url='/'+path.replace(/^\//,'');if(!cache.has(url))cache.set(url,fetch(url).then(r=>{if(!r.ok)throw Error('Não foi possível carregar este design. Tente novamente.');return r.json();}).catch(e=>{cache.delete(url);throw e;}));return cache.get(url);}
export async function bytes(path){const r=await fetch('/'+path.replace(/^\//,''));if(!r.ok)throw Error('Arquivo indisponível. Tente novamente.');return new Uint8Array(await r.arrayBuffer());}
