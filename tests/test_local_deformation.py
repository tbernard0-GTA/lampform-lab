import numpy as np
from analysis.local_deformation import affine_fit

def test_rigid_rotation_and_translation_preserve_stretches():
    a=np.linspace(0,2*np.pi,6,endpoint=False);x=np.c_[np.cos(a),np.sin(a)]
    q=np.array([[1,0,0],[0,.6,.8]])
    r=affine_fit(x,x@q+np.array([2,3,7]))
    assert np.allclose([r['lambda1'],r['lambda2'],r['J']],[1,1,1],atol=1e-12)
    assert not r['direction_resolved']

def test_known_anisotropic_affine_mapping_and_direction():
    a=np.linspace(0,2*np.pi,6,endpoint=False);x=np.c_[np.cos(a),np.sin(a)]
    angle=.43;v=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
    f=v@np.diag([1.5,.8])@v.T;y=np.c_[x@f.T,np.zeros(6)]
    r=affine_fit(x,y)
    assert np.allclose([r['lambda1'],r['lambda2'],r['J']],[1.5,.8,1.2])
    assert abs(np.dot(r['principal_direction_1'],v[:,0]))>1-1e-12
    assert r['fit_rms_mm']<1e-12

def test_curvature_fit_reports_nonplanarity():
    x=np.array([[-1,-1],[1,-1],[1,1],[-1,1],[0,0],[0,1.]])
    r=affine_fit(x,np.c_[x,.4*np.sum(x*x,axis=1)])
    assert r['out_of_plane_rms_mm']>.1
