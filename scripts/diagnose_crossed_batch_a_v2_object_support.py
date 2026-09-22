from pathlib import Path
import argparse, importlib.util, json
import numpy as np
import pandas as pd

def load_engine(repo):
    p=repo/"scripts"/"gef_crossed_batch_a_v2.py"
    spec=importlib.util.spec_from_file_location("ba2",p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m

def count(s):
    a=np.asarray(s,dtype=float)
    return int(np.isfinite(a).sum())

def yearly(mask,times):
    z={}
    for y in [2013,2014,2015,2016]:
        ym=np.asarray(times.year==y)
        z[str(y)]=int(np.sum(mask&ym))
    return z

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"D:\MT5_Backtests");args=ap.parse_args()
    root=Path(args.root);repo=root/"guardian-research";m=load_engine(repo)
    print("=== BATCH A V2 OBJECT-SUPPORT DIAGNOSTIC ===")
    print("READ ONLY; NO OLS; NO 2017+; uses engine aligned_mask")
    P=m.load_hour_prices(root,2012,2016)
    times=P.index
    disc=np.asarray((times>=pd.Timestamp("2013-01-01"))&(times<pd.Timestamp("2017-01-01")))
    print("\n=== PRICE / RETURN SUPPORT ===")
    rows=[]
    r60={}
    rz={}
    for s in m.MARKETS:
        r60[s]=P[s]/P[s].shift(1)-1
        rz[s]=m.causal_z(r60[s],m.FAST_Z_MIN)
        pr=np.isfinite(P[s].to_numpy(dtype=float))&disc
        rr=np.isfinite(r60[s].to_numpy(dtype=float))&disc
        zz=np.isfinite(rz[s].to_numpy(dtype=float))&disc
        ex=zz&(np.abs(rz[s].to_numpy(dtype=float))>=m.EVENT_Z)
        cd=m.cooldown_mask(times,rz[s].to_numpy(),m.EVENT_Z,m.COOLDOWN_MIN)&disc
        vals=rz[s].to_numpy(dtype=float)
        fv=vals[zz]
        rows.append({
          "market":s,"price_finite":int(pr.sum()),"ret60_finite":int(rr.sum()),"z_finite":int(zz.sum()),
          "absz_ge_1p5":int(ex.sum()),"cooldown_events":int(cd.sum()),
          "z_q01":float(np.nanquantile(fv,.01)) if len(fv) else np.nan,
          "z_q50":float(np.nanquantile(fv,.50)) if len(fv) else np.nan,
          "z_q99":float(np.nanquantile(fv,.99)) if len(fv) else np.nan,
          "events_by_year":json.dumps(yearly(cd,times),sort_keys=True)
        })
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n=== BETA SUPPORT ===")
    betas={
      "XAU|UDX":m.rolling_beta(r60["XAUUSD"],r60["UDXUSD"]),
      "CAD|UDX":m.rolling_beta(r60["USDCAD"],r60["UDXUSD"]),
      "NSX|SPX":m.rolling_beta(r60["NSXUSD"],r60["SPXUSD"]),
      "XAU|XAG":m.rolling_beta(r60["XAUUSD"],r60["XAGUSD"]),
    }
    brows=[]
    for name,b in betas.items():
        ok=np.isfinite(b.to_numpy(dtype=float))&disc
        brows.append({"beta":name,"finite":int(ok.sum()),"by_year":json.dumps(yearly(ok,times),sort_keys=True)})
    print(pd.DataFrame(brows).to_string(index=False))

    print("\n=== DERIVED EVENT OBJECT SUPPORT ===")
    beta_nsx_spx=betas["NSX|SPX"];beta_xau_xag=betas["XAU|XAG"]
    z_nsx=m.causal_z(r60["NSXUSD"]-beta_nsx_spx*r60["SPXUSD"],m.FAST_Z_MIN)
    z_xau=m.causal_z(r60["XAUUSD"]-beta_xau_xag*r60["XAGUSD"],m.FAST_Z_MIN)
    synthetic=pd.concat([-rz["EURUSD"],-rz["GBPUSD"],-rz["AUDUSD"],rz["USDJPY"],rz["USDCHF"],rz["USDCAD"]],axis=1).mean(axis=1,skipna=False)
    z_breadth=m.causal_z(rz["UDXUSD"]-synthetic,m.FAST_Z_MIN)
    objs={"NSXSPX_resid_z":z_nsx,"XAUXAG_resid_z":z_xau,"USD_breadth_z":z_breadth}
    orows=[]
    for name,z in objs.items():
        a=z.to_numpy(dtype=float);finite=np.isfinite(a)&disc;exc=finite&(np.abs(a)>=m.EVENT_Z)
        cd=m.cooldown_mask(times,a,m.EVENT_Z,m.COOLDOWN_MIN)&disc
        fv=a[finite]
        orows.append({"object":name,"finite":int(finite.sum()),"absz_ge_1p5":int(exc.sum()),"cooldown_events":int(cd.sum()),
                      "q01":float(np.nanquantile(fv,.01)) if len(fv) else np.nan,
                      "q50":float(np.nanquantile(fv,.50)) if len(fv) else np.nan,
                      "q99":float(np.nanquantile(fv,.99)) if len(fv) else np.nan,
                      "events_by_year":json.dumps(yearly(cd,times),sort_keys=True)})
    print(pd.DataFrame(orows).to_string(index=False))

    print("\n=== RATE SUPPORT ===")
    rate_z,meta=m.build_rate_objects(root,2016,times)
    rr=[]
    for ten,z in rate_z.items():
        a=z.to_numpy(dtype=float);ok=np.isfinite(a)&disc
        rr.append({"tenor":ten,"raw":meta[ten]["raw_column"],"finite_hours":int(ok.sum()),
                   "distinct_days":int(pd.DatetimeIndex(times[ok]).normalize().nunique()),
                   "by_year":json.dumps(yearly(ok,times),sort_keys=True)})
    print(pd.DataFrame(rr).to_string(index=False))

    print("\n=== FORWARD TARGET SUPPORT ===")
    tr=[]
    for s in ["XAUUSD","UDXUSD","USDCAD","NSXUSD","SPXUSD","XAGUSD"]:
        for h in [60,120,240]:
            y=m.forward_return(P,s,h).to_numpy(dtype=float)
            al=m.aligned_mask(times,h)
            ok=np.isfinite(y)&disc&al
            tr.append({"target":s,"h":h,"finite_aligned":int(ok.sum()),"by_year":json.dumps(yearly(ok,times),sort_keys=True)})
    print(pd.DataFrame(tr).to_string(index=False))

    print("\n=== P01 INTERSECTION SUPPORT ===")
    bu=betas["XAU|UDX"].to_numpy(dtype=float)
    zu=rz["UDXUSD"].to_numpy(dtype=float)
    pr=[]
    for ten,zrS in rate_z.items():
        zr=zrS.to_numpy(dtype=float)
        for h in [60,120,240]:
            y=m.forward_return(P,"XAUUSD",h).to_numpy(dtype=float)-bu*m.forward_return(P,"UDXUSD",h).to_numpy(dtype=float)
            mask=disc&m.aligned_mask(times,h)&np.isfinite(y)&np.isfinite(zr)&np.isfinite(zu)&np.isfinite(zr*zu)
            pr.append({"tenor":ten,"h":h,"intersection_n":int(mask.sum()),"days":int(pd.DatetimeIndex(times[mask]).normalize().nunique()),
                       "by_year":json.dumps(yearly(mask,times),sort_keys=True)})
    print(pd.DataFrame(pr).to_string(index=False))

if __name__=="__main__":
    main()
