import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
export class Viewer {
  constructor(element,state){
    this.element=element;this.state=state;this.objects=[];
    this.renderer=new THREE.WebGLRenderer({antialias:true});this.renderer.setPixelRatio(Math.min(devicePixelRatio,2));this.renderer.setClearColor('#e8ebe5');element.append(this.renderer.domElement);this.scene=new THREE.Scene();
    this.scene.add(new THREE.HemisphereLight(0xffffff,0x747f70,3));const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(-80,-100,160);this.scene.add(light);
    this.camera=new THREE.PerspectiveCamera(33,1,.1,2000);this.camera.up.set(0,0,1);this.controls=new OrbitControls(this.camera,this.renderer.domElement);this.controls.minDistance=35;this.controls.maxDistance=500;
    this.controls.addEventListener('change',()=>{this.render();state.sync(this);});
    new ResizeObserver(()=>{const {width,height}=element.getBoundingClientRect();if(!width||!height)return;this.renderer.setSize(width,height);this.camera.aspect=width/height;this.camera.updateProjectionMatrix();this.render();}).observe(element);
    this.renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();state.error('O 3D foi interrompido. Os mapas planos e downloads continuam disponíveis.');});
  }
  render(){this.renderer.render(this.scene,this.camera);}
  clear(){for(const o of this.objects){this.scene.remove(o);o.geometry.dispose();o.material.dispose();}this.objects=[];}
  mesh(source,material){const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(source.positions,3));g.setIndex(source.indices);g.computeVertexNormals();return new THREE.Mesh(g,material);}
  setData(data){
    this.clear();this.data=data;this.lamp=this.mesh(data.lamp,new THREE.MeshStandardMaterial({vertexColors:true,roughness:.85,side:THREE.DoubleSide}));this.tool=this.mesh(data.tool,new THREE.MeshStandardMaterial({color:'#718175',transparent:true,opacity:.12,depthWrite:false,side:THREE.DoubleSide}));
    this.network=new THREE.InstancedMesh(new THREE.CylinderGeometry(.28,.28,1,6),new THREE.MeshBasicMaterial({depthTest:false}),data.edges.length);this.network.renderOrder=2;
    this.marker=new THREE.Mesh(new THREE.SphereGeometry(1.3,14,10),new THREE.MeshBasicMaterial({color:'#e231cb',depthTest:false}));this.marker.renderOrder=3;this.objects=[this.lamp,this.tool,this.network,this.marker];this.scene.add(...this.objects);
    const pos=data.lamp.positions;this.closest=new Int32Array(pos.length/3);
    for(let i=0;i<pos.length;i+=3){if(pos[i+2]>1.01){this.closest[i/3]=-1;continue;}let best=Infinity,index=-1;
      data.edges.forEach((edge,j)=>{const p=edge.flat,dx=p[3]-p[0],dy=p[4]-p[1],t=Math.max(0,Math.min(1,((pos[i]-p[0])*dx+(pos[i+1]-p[1])*dy)/(dx*dx+dy*dy))),d=(pos[i]-p[0]-t*dx)**2+(pos[i+1]-p[1]-t*dy)**2;if(d<best){best=d;index=j;}});this.closest[i/3]=best<4?index:-1;}
    this.update();
  }
  update(){if(!this.data)return;const S=this.state,data=this.data;this.lamp.visible=S.view==='flat'&&S.representation==='stl';this.network.visible=!this.lamp.visible;this.tool.visible=S.view==='formed'&&S.ghost;
    const colors=data.edges.map(e=>new THREE.Color(S.color(S.value(e,data)))),vertex=new Float32Array(this.closest.length*3),neutral=new THREE.Color('#b5c0ae');this.closest.forEach((edge,i)=>(edge<0?neutral:colors[edge]).toArray(vertex,i*3));this.lamp.geometry.setAttribute('color',new THREE.Float32BufferAttribute(vertex,3));
    const dummy=new THREE.Object3D(),up=new THREE.Vector3(0,1,0);let marker=null;
    data.edges.forEach((edge,i)=>{const p=S.view==='flat'?edge.flat:edge.stages[S.step],a=new THREE.Vector3(...p.slice(0,3)),b=new THREE.Vector3(...p.slice(3));if(S.view==='flat'){a.z=1.1;b.z=1.1;}const direction=b.clone().sub(a),active=edge.parent===S.highlight;dummy.position.copy(a).add(b).multiplyScalar(.5);dummy.quaternion.setFromUnitVectors(up,direction.clone().normalize());dummy.scale.set(active?2:1,direction.length(),active?2:1);dummy.updateMatrix();this.network.setMatrixAt(i,dummy.matrix);this.network.setColorAt(i,active?new THREE.Color('#e231cb'):colors[i]);if(active&&!marker)marker=dummy.position.clone();});
    this.marker.visible=!!marker;if(marker)this.marker.position.copy(marker);this.network.instanceMatrix.needsUpdate=true;this.network.instanceColor.needsUpdate=true;this.network.computeBoundingSphere();this.render();
  }
  reset(){const d=190*Math.max(1,.8/this.camera.aspect);this.camera.position.set(d*.6,-d*.78,d*.8);this.controls.target.set(0,0,this.state.view==='flat'?0:18);this.controls.update();this.render();}
}
