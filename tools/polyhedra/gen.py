import itertools, math, json, sys
import numpy as np
from scipy.spatial import ConvexHull
phi=(1+5**0.5)/2

def perms_all(v):
    return set(itertools.permutations(v))
def even_perms(v):
    a,b,c=v; return {(a,b,c),(b,c,a),(c,a,b)}
def signs(v):
    out=set()
    for s in itertools.product(*[(1,-1) if abs(x)>1e-12 else (1,) for x in v]):
        out.add(tuple(x*k for x,k in zip(v,s)))
    return out
def P_all(*vs):
    S=set()
    for v in vs:
        for s in signs(v): S|=perms_all(s)
    return S
def P_even(*vs):
    S=set()
    for v in vs:
        for s in signs(v): S|=even_perms(s)
    return S

def tetra(): return {(1,1,1),(1,-1,-1),(-1,1,-1),(-1,-1,1)}
def octa(): return P_all((1,0,0))
def icosa(): return P_even((0,1,phi))
def dodeca(): return signs((1,1,1))|P_even((0,1/phi,phi))
def trunc_tetra():
    return {p for p in P_all((3,1,1)) if sum(1 for x in p if x<0)%2==0}
def cubocta(): return P_all((1,1,0))
def trunc_cube(): x=2**0.5-1; return P_all((x,1,1))
def trunc_octa(): return P_all((0,1,2))
def rhombicubocta(): return P_all((1,1,1+2**0.5))
def trunc_cubocta(): return P_all((1,1+2**0.5,1+2*2**0.5))
def snub_cube():
    t=1.839286755214161
    S=set()
    for s in signs((1,1/t,t)):
        npos=sum(1 for x in s if x>0)
        if npos%2==0: S|=even_perms(s)
        else:
            a,b,c=s; S|={(b,a,c),(a,c,b),(c,b,a)}
    return S
def icosidodeca(): return P_even((0,0,phi))|P_even((0.5,phi/2,phi*phi/2))
def trunc_dodeca(): return P_even((0,1/phi,2+phi),(1/phi,phi,2*phi),(phi,2,phi+1))
def trunc_icosa(): return P_even((0,1,3*phi),(1,2+phi,2*phi),(phi,2,phi**3))
def rhombicosidodeca(): return P_even((1,1,phi**3),(phi**2,phi,2*phi),(2+phi,0,phi**2))
def trunc_icosidodeca(): return P_even((1/phi,1/phi,3+phi),(2/phi,phi,1+2*phi),(1/phi,phi**2,-1+3*phi),(2*phi-1,2,2+phi),(phi,3,2*phi))
def snub_dodeca():
    V=np.load("/tmp/claude-0/poly/snub_dodeca.npy")
    return {tuple(map(float,v)) for v in V}

def hull_faces(V):
    V=np.array(V,float)
    h=ConvexHull(V)
    planes=[]
    for eq,simp in zip(h.equations,h.simplices):
        n=eq[:3]; d=-eq[3]
        for p in planes:
            if np.allclose(p[0],n,atol=1e-6) and abs(p[1]-d)<1e-6:
                p[2].update(simp); break
        else: planes.append([n,d,set(simp)])
    faces=[]
    for n,d,idx in planes:
        idx=[i for i in range(len(V)) if abs(V[i]@n-d)<1e-6]
        c=V[idx].mean(0)
        u=V[idx[0]]-c; u/=np.linalg.norm(u); w=np.cross(n,u)
        idx.sort(key=lambda i: math.atan2((V[i]-c)@w,(V[i]-c)@u))
        faces.append((idx,n))
    return V,faces

def dual(V,faces):
    pts=[tuple(n/d) for (idx,n),d in zip(faces,[V[f[0]]@f[1] for f in faces])]
    return pts

def dedupe(S):
    out=[]
    for p in S:
        if not any(np.allclose(p,q,atol=1e-9) for q in out): out.append(p)
    return out

def orient_and_scale(V,faces,mode):
    # pick bottom face: largest area
    def area(idx):
        P=V[idx]; s=np.zeros(3)
        for k in range(len(P)): s+=np.cross(P[k],P[(k+1)%len(P)])
        return np.linalg.norm(s)/2
    best=max(range(len(faces)),key=lambda k:(round(area(faces[k][0]),6), -faces[k][1][1]))
    n=faces[best][1]
    target=np.array([0,-1.0,0])
    v=np.cross(n,target); c=n@target
    if np.linalg.norm(v)<1e-9:
        R=np.eye(3) if c>0 else np.diag([1,-1,-1])
    else:
        vx=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
        R=np.eye(3)+vx+vx@vx*(1/(1+c))
    W=V@R.T
    # rotate about y so bottom face front edge is along x
    idx=faces[best][0]
    P=W[idx]
    # choose edge with smallest mean z (front)
    k=min(range(len(idx)),key=lambda k:(P[k][2]+P[(k+1)%len(idx)][2]))
    e=P[(k+1)%len(idx)]-P[k]; ang=math.atan2(e[2],e[0])
    cy,sy=math.cos(-ang),math.sin(-ang)
    Ry=np.array([[cy,0,-sy],[0,1,0],[sy,0,cy]])
    W=W@Ry.T
    # center bbox
    W-= (W.max(0)+W.min(0))/2
    # scale
    if mode=="edge":
        L=min(np.linalg.norm(W[f[0][k]]-W[f[0][(k+1)%len(f[0])]]) for f in faces for k in range(len(f[0])))
        W/=L
    else:
        W/=np.linalg.norm(W,axis=1).max()
    return W,best

DEFS=[
 ("tetrahedron","정사면체","edge",tetra),
 ("octahedron","정팔면체","edge",octa),
 ("dodecahedron","정십이면체","edge",dodeca),
 ("icosahedron","정이십면체","edge",icosa),
 ("trunc_tetra","깎은 정사면체","edge",trunc_tetra),
 ("cubocta","육팔면체","edge",cubocta),
 ("trunc_cube","깎은 정육면체","edge",trunc_cube),
 ("trunc_octa","깎은 정팔면체","edge",trunc_octa),
 ("rhombicubocta","마름모육팔면체","edge",rhombicubocta),
 ("trunc_cubocta","깎은 육팔면체","edge",trunc_cubocta),
 ("snub_cube","다듬은 정육면체","edge",snub_cube),
 ("icosidodeca","십이이십면체","edge",icosidodeca),
 ("trunc_dodeca","깎은 정십이면체","edge",trunc_dodeca),
 ("trunc_icosa","깎은 정이십면체 (축구공)","edge",trunc_icosa),
 ("rhombicosidodeca","마름모십이이십면체","edge",rhombicosidodeca),
 ("trunc_icosidodeca","깎은 십이이십면체","edge",trunc_icosidodeca),
 ("snub_dodeca","다듬은 정십이면체","edge",snub_dodeca),
]
CAT=[("triakis_tetra","삼각사면체 (Triakis tetrahedron)","trunc_tetra"),
 ("rhombic_dodeca","마름모십이면체 (Rhombic dodecahedron)","cubocta"),
 ("triakis_octa","삼각팔면체 (Triakis octahedron)","trunc_cube"),
 ("tetrakis_hexa","사각육면체 (Tetrakis hexahedron)","trunc_octa"),
 ("deltoidal_icositetra","연꼴이십사면체 (Deltoidal icositetrahedron)","rhombicubocta"),
 ("disdyakis_dodeca","육각십이면체 (Disdyakis dodecahedron)","trunc_cubocta"),
 ("pentagonal_icositetra","오각이십사면체 (Pentagonal icositetrahedron)","snub_cube"),
 ("rhombic_triaconta","마름모삼십면체 (Rhombic triacontahedron)","icosidodeca"),
 ("triakis_icosa","삼각이십면체 (Triakis icosahedron)","trunc_dodeca"),
 ("pentakis_dodeca","오각십이면체 (Pentakis dodecahedron)","trunc_icosa"),
 ("deltoidal_hexeconta","연꼴육십면체 (Deltoidal hexecontahedron)","rhombicosidodeca"),
 ("disdyakis_triaconta","육각삼십면체 (Disdyakis triacontahedron)","trunc_icosidodeca"),
 ("pentagonal_hexeconta","오각육십면체 (Pentagonal hexecontahedron)","snub_dodeca"),
]
EXPECT={"tetrahedron":(4,6,4),"octahedron":(6,12,8),"dodecahedron":(20,30,12),"icosahedron":(12,30,20),
"trunc_tetra":(12,18,8),"cubocta":(12,24,14),"trunc_cube":(24,36,14),"trunc_octa":(24,36,14),"rhombicubocta":(24,48,26),
"trunc_cubocta":(48,72,26),"snub_cube":(24,60,38),"icosidodeca":(30,60,32),"trunc_dodeca":(60,90,32),"trunc_icosa":(60,90,32),
"rhombicosidodeca":(60,120,62),"trunc_icosidodeca":(120,180,62),"snub_dodeca":(60,150,92)}
out={}
raw={}
for key,name,mode,fn in DEFS:
    V=dedupe(fn()); V,faces=hull_faces(V); raw[key]=(V,faces)
    E=len({frozenset((f[k],f[(k+1)%len(f)])) for f,_ in faces for k in range(len(f))})
    got=(len(V),E,len(faces))
    lens=[np.linalg.norm(V[f[k]]-V[f[(k+1)%len(f)]]) for f,_ in faces for k in range(len(f))]
    ok=got==EXPECT[key] and max(lens)-min(lens)<1e-6*max(lens)
    print(key,got,"OK" if ok else "BAD", round(min(lens),4), round(max(lens),4))
    W,bottom=orient_and_scale(V,faces,mode)
    out[key]={"name":name,"group":"정다면체" if key in ("tetrahedron","octahedron","dodecahedron","icosahedron") else "아르키메데스 다면체",
              "scale":"edge","v":W.round(6).tolist(),"faces":[list(map(int,f)) for f,_ in faces],"bottom":bottom}
for key,name,src in CAT:
    V,faces=raw[src]
    D=dedupe([tuple(n/(V[f[0]]@n)) for f,n in faces])
    D,dfaces=hull_faces(D)
    # congruent check: sorted edge length multiset per face
    sig=set()
    for f,_ in dfaces:
        L=sorted(round(float(np.linalg.norm(D[f[k]]-D[f[(k+1)%len(f)]])/np.linalg.norm(D,axis=1).max()),4) for k in range(len(f)))
        sig.add(tuple(L))
    print(key,(len(D),len(dfaces)),"congruent" if len(sig)==1 else ("NOT",len(sig)))
    W,bottom=orient_and_scale(D,dfaces,"radius")
    out[key]={"name":name,"group":"카탈랑 다면체","scale":"radius","v":W.round(6).tolist(),"faces":[list(map(int,f)) for f,_ in dfaces],"bottom":bottom}
json.dump(out,open("/tmp/claude-0/poly/raw.json","w"))
