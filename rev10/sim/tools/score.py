import numpy as np, sys, pathlib
def load(tag):
    cols = pathlib.Path(tag+'.cols').read_text().split()
    d = np.loadtxt(tag+'.dat'); t = d[:,0]
    return {c: d[:,2*i+1] for i,c in enumerate(cols)}, t
def score(tag, t_on=12.0e-6, t_off=65e-6, expect=None, show=(), quiet=False, t_end=None, t0=0.0, label=None):
    v,t = load(tag); at=lambda x,tt: x[min(np.searchsorted(t,tt),len(t)-1)]
    t_on += t0; t_off += t0
    tend = (t0 + t_end) if t_end else t[-1]-1e-6
    trips={}
    for k in range(1,6):
        na=v[f'na{k}']; idx=np.where((t>t_on)[1:]&(t<tend)[1:]&(na[:-1]<1.65)&(na[1:]>=1.65))[0]
        if len(idx): trips[k]=t[idx[0]+1]
    if 'win' in v:   # new topology: lock when win rises past 2.05 V (header off)
        w=v['win']; idx=np.where((t>t_on)[1:]&(t<tend)[1:]&(w[:-1]<2.05)&(w[1:]>=2.05))[0]; lockname='win'
    else:
        w=v['winb']; idx=np.where((t>t_on)[1:]&(w[:-1]>2.0)&(w[1:]<=2.0))[0]; lockname='winb'
    tw=t[idx[0]+1] if len(idx) else None
    order="".join(str(k) for k in sorted(trips,key=trips.get)) or "-"
    latched="".join(str(k) for k in range(1,6) if at(v[f'na{k}'],tend)>2.5) or "none"
    first=min(trips.values()) if trips else None
    ro = max(at(v[f'na{k}'],tend) for k in range(1,6) if str(k)!=latched[:1]) if latched!='none' else float('nan')
    valid = first is not None and first < t_off and len(latched)==1 and latched==order[0] and (expect is None or latched==str(expect))
    lat = (tw-first)*1e6 if (tw and first) else float('nan')
    res = dict(tag=tag, trip=first, order=order, latched=latched, lock=tw, lat=lat, ro=ro, valid=valid)
    if not quiet:
        print(f"{(label or tag):26s} trip={'%.2fus'%(first*1e6) if first else 'none':>8} order={order:6s} latched={latched:5s} "
              f"lock({lockname})@{'%.2fus'%(tw*1e6) if tw else 'never':>8} latency={lat:5.2f}us runnerup_na_end={ro:.3f} "
              f"-> {'VALID' if valid else 'fail'}{'' if expect is None else ' (expect %d)'%expect}")
    for tt in show:
        print(f"   {tt*1e6:6.2f}us " + " ".join(f"{c}={at(v[c],tt):6.3f}" for c in ['ap1','ap2','ap5','d1','d2','na1','na2','nb1',lockname,'vls'] + (['tripvdd'] if 'tripvdd' in v else [])))
    return res
if __name__=="__main__":
    for tag in sys.argv[1:]: score(tag)
