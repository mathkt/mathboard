import json, math, sys, random
import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union
sys.path.insert(0,"/home/claude/dohyeong")
import solid as S
d=json.load(open("/tmp/claude-0/poly/raw2.json"))

def mesh_of(o):
    m=S.Mesh()
    for v in o["v"]: m.add(*v)
    for i,f in enumerate(o["faces"]): m.face(f,f"f{i}")
    return m

def unfold(m, root, parent):
    # parent: child -> (par, (u,v))
    order=[root]; k=0
    kids={}
    for c,(p,e) in parent.items(): kids.setdefault(p,[]).append(c)
    while k<len(order):
        order+=kids.get(order[k],[]); k+=1
    pos={}
    f=m.faces[root]; n=S._vnorm(S.newell(m,f)); p0=m.v[f[0]]
    e1=S._vnorm(S._vsub(m.v[f[1]],p0)); e2=S.cross(n,e1)
    pos[root]={vi:(S._vdot(S._vsub(m.v[vi],p0),e1),S._vdot(S._vsub(m.v[vi],p0),e2)) for vi in f}
    for b in order[1:]:
        a,(u,v)=parent[b]
        U,Vv=pos[a][u],pos[a][v]
        cen=[sum(q[c] for q in pos[a].values())/len(pos[a]) for c in (0,1)]
        E=(Vv[0]-U[0],Vv[1]-U[1]); L=math.hypot(*E) or 1; E=(E[0]/L,E[1]/L); N=(-E[1],E[0])
        if (cen[0]-U[0])*N[0]+(cen[1]-U[1])*N[1]>0: N=(-N[0],-N[1])
        e=S._vnorm(S._vsub(m.v[v],m.v[u])); pts={}
        for w in m.faces[b]:
            dd=S._vsub(m.v[w],m.v[u]); s=S._vdot(dd,e); pp=S._vsub(dd,(e[0]*s,e[1]*s,e[2]*s)); t=math.sqrt(S._vdot(pp,pp))
            pts[w]=(U[0]+E[0]*s+N[0]*t,U[1]+E[1]*s+N[1]*t)
        pos[b]=pts
    return [[pos[fi][vi] for vi in m.faces[fi]] for fi in range(len(m.faces))]

def overlaps(polys):
    P=[Polygon(p) for p in polys]
    tot=sum(p.area for p in P)
    U=unary_union(P)
    if abs(U.area-tot)>1e-6*tot: return True
    return False

def tree_from_cut(m, cut, root):
    adj={}
    for fi,f in enumerate(m.faces):
        for k in range(len(f)):
            e=frozenset((f[k],f[(k+1)%len(f)])); adj.setdefault(e,[]).append(fi)
    nb={}
    for e,fs in adj.items():
        if e in cut or len(fs)!=2: continue
        a,b=fs; nb.setdefault(a,[]).append((b,tuple(e))); nb.setdefault(b,[]).append((a,tuple(e)))
    parent={}; seen={root}; q=[root]
    while q:
        a=q.pop(0)
        for b,e in nb.get(a,[]):
            if b not in seen: seen.add(b); parent[b]=(a,e); q.append(b)
    if len(seen)!=len(m.faces): return None
    return parent

def steepest(m, c):
    V=np.array(m.v); nbr={}
    for f in m.faces:
        for k in range(len(f)):
            a,b=f[k],f[(k+1)%len(f)]; nbr.setdefault(a,set()).add(b); nbr.setdefault(b,set()).add(a)
    top=int(np.argmax(V@c)); cut=set()
    for v in range(len(V)):
        if v==top: continue
        best=max(nbr[v],key=lambda u:((V[u]-V[v])@c)/np.linalg.norm(V[u]-V[v]))
        cut.add(frozenset((v,best)))
    return cut

def score(polys):
    pts=np.array([q for p in polys for q in p]); w,h=pts.max(0)-pts.min(0)
    return w*h*(max(w,h)/min(w,h))**0.5

rng=np.random.default_rng(7)
result={}
for k,o in d.items():
    m=mesh_of(o); root=o["bottom"]; best=None
    tries=0
    while tries<400 and (best is None or tries<120):
        tries+=1
        c=rng.normal(size=3); c/=np.linalg.norm(c)
        cut=steepest(m,c); par=tree_from_cut(m,cut,root)
        if par is None: continue
        polys=unfold(m,root,par)
        if overlaps(polys): continue
        sc=score(polys)
        if best is None or sc<best[0]: best=(sc,par)
    print(k, "ok" if best else "FAIL", tries)
    if best: result[k]={c:[p,list(e)] for c,(p,e) in best[1].items()}
    o["net"]=result.get(k)
json.dump(d,open("/tmp/claude-0/poly/final.json","w"))
