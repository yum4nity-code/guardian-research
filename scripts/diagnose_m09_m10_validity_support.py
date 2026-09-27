from pathlib import Path
import argparse, json
import numpy as np
import pandas as pd

RUN_ID = "GEFM5MD-20260927-104939"

def pct(s, q):
    s = pd.to_numeric(s, errors="coerce").dropna()
    return float(s.quantile(q)) if len(s) else np.nan

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root", default=r"D:\MT5_Backtests")
    args=ap.parse_args()
    root=Path(args.root)

    run = root/"Research"/"Autonomous"/"guardian_m5_motion_topology_m09_m10_discovery"/RUN_ID
    p = run/"DISCOVERY_ALL.csv"
    if not p.exists():
        raise RuntimeError(f"Missing {p}")

    d = pd.read_csv(p)
    need = ["family","target","lookback_min","sequence_len","motif","census_episodes_30m","census_utc_days",
            "episodes","days","p_one","valid","mean_endpoint"]
    miss=[c for c in need if c not in d.columns]
    if miss:
        raise RuntimeError(f"Missing columns: {miss}")

    d["p_finite"] = np.isfinite(pd.to_numeric(d["p_one"],errors="coerce"))
    d["ep_ok"] = pd.to_numeric(d["episodes"],errors="coerce") >= 200
    d["days_ok"] = pd.to_numeric(d["days"],errors="coerce") >= 120
    d["support_ok"] = d["ep_ok"] & d["days_ok"]
    d["valid_recalc"] = d["support_ok"] & d["p_finite"]

    rows=[]
    for fam,g in d.groupby("family"):
        rows.append({
            "family":fam,
            "tests":len(g),
            "valid_reported":int(g["valid"].astype(bool).sum()),
            "valid_recalc":int(g["valid_recalc"].sum()),
            "episodes_ge_200":int(g["ep_ok"].sum()),
            "days_ge_120":int(g["days_ok"].sum()),
            "support_both":int(g["support_ok"].sum()),
            "p_finite":int(g["p_finite"].sum()),
            "max_episodes":int(pd.to_numeric(g["episodes"],errors="coerce").max()),
            "p95_episodes":pct(g["episodes"],.95),
            "median_episodes":pct(g["episodes"],.50),
            "max_days":int(pd.to_numeric(g["days"],errors="coerce").max()),
            "p95_days":pct(g["days"],.95),
            "median_days":pct(g["days"],.50),
            "max_census_episodes":int(pd.to_numeric(g["census_episodes_30m"],errors="coerce").max()),
            "p95_census_episodes":pct(g["census_episodes_30m"],.95)
        })
    S=pd.DataFrame(rows)
    S.to_csv(run/"VALIDITY_SUPPORT_AUDIT.csv",index=False)

    d["episode_retention_ratio"] = pd.to_numeric(d["episodes"],errors="coerce") / pd.to_numeric(d["census_episodes_30m"],errors="coerce").replace(0,np.nan)
    top=d.sort_values(["episodes","days","census_episodes_30m"],ascending=False).head(100)
    top.to_csv(run/"TOP_SUPPORT_OBJECTS.csv",index=False)

    suspect=d[
        (pd.to_numeric(d["census_episodes_30m"],errors="coerce") >= 200)
        & (pd.to_numeric(d["episodes"],errors="coerce") < 200)
    ].sort_values(["census_episodes_30m","episodes"],ascending=[False,True])
    suspect.head(200).to_csv(run/"CENSUS_TO_OUTCOME_SUPPORT_COLLAPSE.csv",index=False)

    reason = pd.DataFrame({
        "reason":[
            "episodes_below_200",
            "days_below_120",
            "support_both_fail",
            "support_ok_but_p_nonfinite",
            "support_ok_and_p_finite",
            "census_ge200_but_outcome_lt200"
        ],
        "count":[
            int((~d["ep_ok"]).sum()),
            int((~d["days_ok"]).sum()),
            int((~d["support_ok"]).sum()),
            int((d["support_ok"] & ~d["p_finite"]).sum()),
            int(d["valid_recalc"].sum()),
            int(((pd.to_numeric(d["census_episodes_30m"],errors="coerce")>=200) & (~d["ep_ok"])).sum())
        ]
    })
    reason.to_csv(run/"INVALID_REASON_COUNTS.csv",index=False)

    summary={
        "run_id":RUN_ID,
        "tests":int(len(d)),
        "reported_valid":int(d["valid"].astype(bool).sum()),
        "recalc_valid":int(d["valid_recalc"].sum()),
        "episodes_ge_200":int(d["ep_ok"].sum()),
        "days_ge_120":int(d["days_ok"].sum()),
        "support_both":int(d["support_ok"].sum()),
        "p_finite":int(d["p_finite"].sum()),
        "support_ok_but_p_nonfinite":int((d["support_ok"] & ~d["p_finite"]).sum()),
        "census_ge200_but_outcome_lt200":int(((pd.to_numeric(d["census_episodes_30m"],errors="coerce")>=200)&(~d["ep_ok"])).sum()),
        "max_episodes":int(pd.to_numeric(d["episodes"],errors="coerce").max()),
        "max_days":int(pd.to_numeric(d["days"],errors="coerce").max()),
        "median_episode_retention_ratio":float(pd.to_numeric(d["episode_retention_ratio"],errors="coerce").median()),
        "scientific_verdict":"DO_NOT_CLOSE_LINEAGE_UNTIL_SUPPORT_AUDIT_REVIEWED"
    }
    (run/"VALIDITY_SUPPORT_AUDIT.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")

    print("\n=== M09/M10 VALIDITY SUPPORT AUDIT ===")
    print(json.dumps(summary,indent=2))
    print("\n=== BY FAMILY ===")
    print(S.to_string(index=False))
    print("\n=== INVALID REASONS ===")
    print(reason.to_string(index=False))
    print("\n=== TOP 20 SUPPORT OBJECTS ===")
    cols=["family","target","lookback_min","sequence_len","census_episodes_30m","episodes","days","p_one","mean_endpoint","motif"]
    print(top[cols].head(20).to_string(index=False))
    print("\nRUN:",run)

if __name__=="__main__":
    main()
