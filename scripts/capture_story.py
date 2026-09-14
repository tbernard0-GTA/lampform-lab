"""Offline, data-driven documentary frames; no browser or fake measurements."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import sys,json,textwrap
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection,PolyCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection,Line3DCollection
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from analysis.physical_pack import measurement_plan
PALETTE={'MATERIAL RESERVE':'#c57b35','DIRECTIONAL COMPLIANCE':'#297c95','BOUNDARY FEED':'#8c69ac','AREA EXPANSION':'#b65269','MIXED':'#75745a','LOW DEMAND':'#b3c7ac'}

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def main():
    catalog=read(ROOT/'dist/data/physical/results.json');scenes=read(ROOT/'story/storyboard.json');out=ROOT/'docs/video_frames';out.mkdir(parents=True,exist_ok=True)
    def data(id,p='submerged'):
        entry=next(d for d in catalog['designs'] if d['id']==id)[p]
        return read(ROOT/'dist'/entry['data']),read(ROOT/'dist'/entry['local_data'])
    for scene in scenes:
        fig=plt.figure(figsize=(19.2,10.8),dpi=100,facecolor='#f4f5ef');n=scene['scene']
        fig.text(.04,.955,f'LAMPFORM LAB                                      {n:02d} / 12',fontsize=16,color='#51664b')
        fig.text(.04,.88,scene['title'],fontsize=36,color='#263129')
        fig.text(.04,.07,'\n'.join(textwrap.wrap(scene['message'],110)),fontsize=18,color='#263129')
        fig.text(.04,.025,'Geometric model · NO PHYSICAL VALIDATION DATA YET · offline frame from the same datasets',fontsize=11,color='#677961')
        if n==6:fig.text(.5,.145,'λ1: 1.0 → 1.6 (saturated) · arrows ±d1, length ∝ |λ1−1|',ha='center',fontsize=13,color='#53644d')
        if n==11:
            fig.text(.5,.49,'Prediction\n↓\nPrint → Thermoform\n↓\nMeasure',ha='center',va='center',fontsize=42,color='#304b38')
        elif n==12:
            for i,id in enumerate(['test_a','test_b','test_c','test_d']):
                d,cells=data(id);ax=fig.add_axes([.03+i*.24,.21,.22,.59]);draw_map(ax,d,cells,'demand',False);ax.set_title(id.upper().replace('_',' '),fontsize=17)
            fig.text(.5,.15,'Predicted hotspots → measure after the physical test',ha='center',fontsize=18,color='#53644d')
        else:
            for i,id in enumerate(['original','original' if n in [1,2,4,5,8] else scene['candidate']]):
                d,cells=data(id)
                if n in [1,2,3,5]:
                    ax=fig.add_axes([.06+i*.46,.2,.42,.6],projection='3d');ax.set_facecolor('#f4f5ef');ax.set_axis_off()
                    if n==3:
                        d,cells=data('original','hab2' if i==0 else 'submerged');mesh=d['tool'];xyz=np.asarray(mesh['positions']).reshape(-1,3);faces=np.asarray(mesh['indices']).reshape(-1,3);poly=Poly3DCollection(xyz[faces],facecolor='#879980',edgecolor='none',alpha=.75);ax.add_collection3d(poly)
                    elif n==1 or (n==2 and i==0):
                        mesh=d['lamp'];xyz=np.asarray(mesh['positions']).reshape(-1,3);faces=np.asarray(mesh['indices']).reshape(-1,3);ax.add_collection3d(Poly3DCollection(xyz[faces],facecolor='#99ac8c',edgecolor='none'))
                    else:
                        lines=np.array([e['stages'][2 if n==5 and i==0 else 4] for e in d['edges']]).reshape(-1,2,3);xyz=lines.reshape(-1,3);lc=Line3DCollection(lines,cmap='RdYlGn_r',linewidths=1.8);lc.set_array(np.array([e['demand'] for e in d['edges']]));lc.set_clim(0,40);ax.add_collection3d(lc)
                    lo=xyz.min(axis=0);hi=xyz.max(axis=0);center=(lo+hi)/2;radius=max(hi-lo)/2;ax.set(xlim=(center[0]-radius,center[0]+radius),ylim=(center[1]-radius,center[1]+radius),zlim=(0,max(65,hi[2])));ax.set_box_aspect((1,1,.65));ax.view_init(elev=36,azim=-62)
                    ax.set_title(('Mold' if i==0 else 'Push') if n==3 else ('Original · flat' if n==2 and i==0 else 'Original · formed' if n==2 else 'Original · 50%' if n==5 and i==0 else 'Original · 100%' if n==5 else 'Original' if id=='original' else scene['candidate']),fontsize=16)
                else:
                    ax=fig.add_axes([.06+i*.46,.19,.42,.62]);field='lambda1' if n==6 else 'mechanism' if n==7 else 'delta' if n==10 and i==1 else 'demand';draw_map(ax,d,cells,field,n==6,overlay=n==9,ids=n==4)
                    ax.set_title(('Original · flat' if n==2 and i==0 else 'Original · formed' if n==2 else 'Original · 50%' if n==5 and i==0 else 'Original · 100%' if n==5 else 'Original' if id=='original' else scene['candidate'])+' · '+field,fontsize=16)
                    if n==8:ax.text(.5,-.04,f'P95 {d["metrics"]["p95"]:.1f}%  |  Max {d["metrics"]["maximum"]:.1f}%  |  Critical {d["metrics"]["critical_edges"]}',transform=ax.transAxes,ha='center',fontsize=14)
        fig.savefig(out/scene['frame'],dpi=100,facecolor=fig.get_facecolor());plt.close(fig);print(scene['frame'],flush=True)

def draw_map(ax,d,cells,field,arrows=False,overlay=False,ids=False):
    polys=[np.array(g['candidate']) for g in d['cells']];vals=[c['lambda1'] if field=='lambda1' else g['candidate_demand']-g['baseline_demand'] if field=='delta' else c['demand'] for g,c in zip(d['cells'],cells)]
    pc=PolyCollection(polys,edgecolors='#697c61',linewidths=.6,cmap='RdBu_r' if field=='delta' else 'RdYlGn_r')
    if field=='mechanism':pc.set_facecolor([PALETTE[c['mechanism']] for c in cells])
    else:pc.set_array(np.array(vals));pc.set_clim((-30,30) if field=='delta' else (1,1.6) if field=='lambda1' else (0,40))
    ax.add_collection(pc)
    for g,c in zip(d['cells'],cells):
        x,y=c['center']
        if arrows and c['direction_resolved']:
            dx,dy=np.array(c['principal_direction_1'])*min(4,max(.4,abs(c['lambda1']-1)*9))/2
            ax.annotate('',xy=(x+dx,y+dy),xytext=(x-dx,y-dy),arrowprops=dict(arrowstyle='<->',lw=.8,color='#203f4e'))
        if ids:ax.text(x,y,c['cell_id'],ha='center',va='center',fontsize=6)
        if overlay:
            p=np.array(g['original']);ax.plot(p[:,0],p[:,1],'--',color='#234b41',lw=1)
    ax.set(xlim=(-42,42),ylim=(-54,54),aspect='equal');ax.axis('off')

if __name__=='__main__':main()
