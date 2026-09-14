import {zipSync,strToU8} from 'fflate';
import {bytes} from './research-data.js';
import {comparison,partName,partSlug,designSlug,stlPath,imagePath} from './experiment-library.js';
export async function buildPairFiles(reference,current){
 const slug=partSlug(current.part);
 const [a,b,ai,bi,picture,mold]=await Promise.all([bytes(stlPath(reference)),bytes(stlPath(current)),bytes(imagePath(reference.part,reference.id)),bytes(imagePath(current.part,current.id)),bytes(`media/comparisons/${slug}-${current.id}.png`),bytes(`downloads/${slug}/molde-${slug}.stl`)]);
 const result=comparison(reference,current),name=slug+'-'+designSlug(current.id);
 const files={[`${slug}-referencia.stl`]:a,[`${slug}-${designSlug(current.id)}.stl`]:b,[`molde-${slug}.stl`]:mold,'original.png':ai,'candidate.png':bi,'comparacao.png':picture,
 'parameters.json':strToU8(JSON.stringify({reference:reference.parameters,candidate:current.parameters},null,2)),
 'metrics.json':strToU8(JSON.stringify({reference:reference.metrics,candidate:current.metrics,comparison:result},null,2)),
 'comparison.html':strToU8(`<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>${name}</title><style>body{font:18px Arial;background:#f4f5ef;color:#294132;margin:4vw}section{display:flex}figure{margin:1em;width:45%}img{width:100%}p{max-width:800px}</style><h1>${partName(current.part)} · original e candidato</h1><section><figure><img src="original.png"><figcaption>${reference.name}</figcaption></figure><figure><img src="candidate.png"><figcaption>${current.name}</figcaption></figure></section><h2>${result.status}</h2><p>${result.explanation}</p><p>As imagens mostram os sólidos calculados. Consulte metrics.json para os valores completos.</p></html>`),
 'LEIA-ME.txt':strToU8(`${name}\n\nReferência: ${reference.name}\nCandidato: ${current.name}\n\nOriginal significa a referência gerada deste experimento; não é uma substituição silenciosa do arquivo original fornecido.\n\n1. Imprima as duas peças com o mesmo material e camadas de 0,1 mm.\n2. Aqueça sob a mesma condição, registrando tempo e temperatura.\n3. Forme usando o molde correspondente à peça.\n4. Compare onde as células abrem, torcem ou falham.\n5. Registre medidas antes/depois e retorne com os dados.\n\n${result.status}\n${result.explanation}\n\nPrevisões geométricas, sem validação física. Altura altera rigidez e aquecimento; a resposta térmica local não foi calibrada.\n`)};
 return {files,name};
}
export async function downloadPair(reference,current){
 const {files,name}=await buildPairFiles(reference,current);
 const blob=new Blob([zipSync(files)],{type:'application/zip'}),url=URL.createObjectURL(blob),aTag=document.createElement('a');aTag.href=url;aTag.download=name+'-par-de-teste.zip';aTag.click();setTimeout(()=>URL.revokeObjectURL(url),2000);
}
