import numpy as np, math
from scipy.spatial import ConvexHull
from scipy.optimize import minimize
phi=(1+5**0.5)/2
def rot(axis,ang):
    a=np.array(axis,float); a/=np.linalg.norm(a); x,y,z=a; c,s=math.cos(ang),math.sin(ang); C=1-c
    return np.array([[c+x*x*C,x*y*C-z*s,x*z*C+y*s],[y*x*C+z*s,c+y*y*C,y*z*C-x*s],[z*x*C-y*s,z*y*C+x*s,c+z*z*C]])
gens=[rot((0,1,phi),2*math.pi/5),rot((1,1,1),2*math.pi/3)]
G=[np.eye(3)]
changed=True
while changed:
    changed=False
    for A in list(G):
        for g in gens:
            B=g@A
            if not any(np.allclose(B,C,atol=1e-9) for C in G):
                G.append(B); changed=True
print("group",len(G))
def orbit(p): return np.array([g@p for g in G])
def edges(V):
    h=ConvexHull(V); E=set()
    for s in h.simplices:
        for i in range(3):
            E.add(tuple(sorted((s[i],s[(i+1)%3]))))
    return E,h
def obj(p):
    p=p/np.linalg.norm(p); V=orbit(p)
    try: E,h=edges(V)
    except Exception: return 1e3
    # snub: each vertex degree 5, all triangle-face edges equal; coplanar pentagon diagonals are hull edges too though
    L=np.array([np.linalg.norm(V[i]-V[j]) for i,j in E])
    L.sort()
    k=150  # true edges = shortest 150
    t=L[:k]
    return t.std()/t.mean()
best=None
rng=np.random.default_rng(1)
for trial in range(300):
    p0=rng.normal(size=3)
    r=minimize(obj,p0,method="Nelder-Mead",options={"xatol":1e-12,"fatol":1e-14,"maxiter":4000})
    if best is None or r.fun<best.fun: best=r
    if r.fun<1e-10: break
p=best.x/np.linalg.norm(best.x); V=orbit(p); print("fun",best.fun)
np.save("/tmp/claude-0/poly/snub_dodeca.npy",V)
