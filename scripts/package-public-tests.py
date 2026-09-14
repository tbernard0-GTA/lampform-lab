"""Friendly names and presentation-only packages around unchanged v0.8 files."""
from pathlib import Path
import json,shutil,zipfile,hashlib
from PIL import Image,ImageDraw,ImageFont
root=Path(__file__).resolve().parents[1];dist=root/'dist'
cat=json.loads((dist/'data/parametric/catalog.json').read_text(encoding='utf-8'))
slugs={'A_uniform':'controle','B_width':'largura','C_height':'altura','D_both':'combinada','honeycomb_equal':'hexagonal-volume-equivalente','triangle_equal':'triangular-volume-equivalente','diamond_equal':'losango-volume-equivalente'}
try:font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',30)
except OSError:font=ImageFont.load_default()
manifest=[]
for part,slug,tool in [('hab2','peca-1','obj_2_Mold.stl'),('submerged','peca-2','obj_4_Push.stl')]:
    folder=dist/'downloads'/slug;folder.mkdir(parents=True,exist_ok=True)
    toolpath=folder/f'molde-{slug}.stl';shutil.copyfile(root/'legacy/lampform_lab_v01'/tool,toolpath)
    entries=[e for e in cat['designs'] if e['part']==part]
    for e in entries:
        name=f'{slug}-{slugs.get(e["id"],e["id"].replace("_","-"))}.stl';target=folder/name;shutil.copyfile(dist/e['stl'],target)
        assert hashlib.sha256(target.read_bytes()).hexdigest()==e['validation']['sha256']
        baseline='honeycomb_equal' if e['parameters']['equal_material'] else 'A_uniform'
        image=Image.new('RGB',(1400,530),'#edf0e7');draw=ImageDraw.Draw(image)
        for i,(id,label) in enumerate([(baseline,'Referencia'),(e['id'],'Candidato')]):
            thumb=Image.open(dist/f'media/tests/{slug}-{id}.png').convert('RGB');thumb.thumbnail((700,480));image.paste(thumb,(i*700+(700-thumb.width)//2,40));draw.text((i*700+35,20),label,font=font,fill='#35573e')
        image.save(dist/f'media/comparisons/{slug}-{e["id"]}.png')
        manifest.append(dict(part=slug,design=e['id'],file=str(target.relative_to(dist)).replace('\\','/'),sha256=e['validation']['sha256']))
    selected=[e for e in entries if e['id'] in cat['doe']]
    params={slugs[e['id']]:e['parameters'] for e in selected};metrics={slugs[e['id']]:e['metrics'] for e in selected}
    readme=f'''{slug.upper()} — EXPERIMENTO DE LARGURA E ALTURA

controle: referencia uniforme gerada, largura e altura de 1 mm.
largura: varia a largura dos ligamentos.
altura: varia a altura local da impressao.
combinada: varia largura e altura.

O molde correspondente esta incluido como molde-{slug}.stl. E a ferramenta de referencia fornecida, apenas renomeada; nao foi redesenhada ou validada para um processo de fabricacao especifico.

1. Imprima os quatro testes com o mesmo material e camadas de 0,1 mm.
2. Aqueca sob a mesma condicao; registre tempo e temperatura.
3. Forme com o molde correspondente.
4. Compare onde as celulas abrem, torcem ou falham.
5. Registre medidas antes/depois e retorne com os dados.

Nenhum resultado fisico registrado. Previsoes geometricas; nao ha calibracao termica local. O controle gerado nao substitui silenciosamente o STL original fornecido.
'''
    with zipfile.ZipFile(folder/f'{slug}-testes.zip','w',zipfile.ZIP_DEFLATED) as z:
        for e in selected:
            name=f'{slug}-{slugs[e["id"]]}.stl';z.write(folder/name,name)
            z.write(dist/f'media/tests/{slug}-{e["id"]}.png',f'{slug}-{slugs[e["id"]]}.png')
        z.write(toolpath,toolpath.name)
        z.writestr('parametros.json',json.dumps(params,ensure_ascii=False,indent=2));z.writestr('previsoes.json',json.dumps(metrics,ensure_ascii=False,indent=2));z.writestr('LEIA-ME.txt',readme)
(dist/'media/public-files.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
