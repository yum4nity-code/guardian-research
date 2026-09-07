#!/usr/bin/env python3
from __future__ import annotations
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

import challenge_probability_lab_v1_00 as lab


def make_days(rs, start=date(2025, 1, 1), adverse=None):
    out=[]
    for i,r in enumerate(rs):
        d=start+timedelta(days=i)
        t=lab.Trade(datetime(d.year,d.month,d.day,12),d,None,float(r),adverse,"synthetic",i+2)
        out.append(lab.DayBlock(d,(t,)))
    return out


class LabTests(unittest.TestCase):
    def cfg(self, **kw):
        base=dict(initial_balance=100000.0,profit_target_pct=10.0,daily_loss_pct=5.0,max_loss_pct=10.0,
                  max_days=100,block_days=1,risk_basis="initial",max_loss_anchor="initial",dense_calendar=True)
        base.update(kw)
        return lab.LabConfig(**base)

    def test_all_winners_pass(self):
        report=lab.run_lab(make_days([1.0]),self.cfg(),risks=[0.5],paths=200,seed=7,use_adverse_r=False)
        self.assertEqual(report["results"][0]["pass"]["probability"],1.0)
        self.assertEqual(report["results"][0]["any_dd_violation"]["probability"],0.0)
        self.assertEqual(report["results"][0]["pass_duration_days"]["median"],20.0)

    def test_all_losers_hit_max(self):
        report=lab.run_lab(make_days([-1.0]),self.cfg(daily_loss_pct=50.0),risks=[0.5],paths=200,seed=7,use_adverse_r=False)
        s=report["results"][0]
        self.assertEqual(s["pass"]["probability"],0.0)
        self.assertEqual(s["max_dd_violation"]["probability"],1.0)
        self.assertEqual(s["daily_dd_violation"]["probability"],0.0)

    def test_daily_limit_resets(self):
        # One -3R atomic trade per day at 1% risk is -3% each day: below 5% daily, but max DD eventually fails.
        report=lab.run_lab(make_days([-3.0]),self.cfg(),risks=[1.0],paths=200,seed=9,use_adverse_r=False)
        s=report["results"][0]
        self.assertEqual(s["daily_dd_violation"]["probability"],0.0)
        self.assertEqual(s["max_dd_violation"]["probability"],1.0)

    def test_adverse_r_can_trigger_daily_breach(self):
        days=make_days([0.25],adverse=-6.0)
        closed=lab.run_lab(days,self.cfg(),risks=[1.0],paths=200,seed=3,use_adverse_r=False)["results"][0]
        adverse=lab.run_lab(days,self.cfg(),risks=[1.0],paths=200,seed=3,use_adverse_r=True)["results"][0]
        self.assertEqual(closed["daily_dd_violation"]["probability"],0.0)
        self.assertEqual(adverse["daily_dd_violation"]["probability"],1.0)

    def test_two_losses_same_day_can_hit_daily_limit(self):
        d=date(2025,1,1)
        trades=(
            lab.Trade(datetime(2025,1,1,10),d,None,-3.0,None,"synthetic",2),
            lab.Trade(datetime(2025,1,1,11),d,None,-3.0,None,"synthetic",3),
        )
        report=lab.run_lab([lab.DayBlock(d,trades)],self.cfg(max_loss_pct=50.0),risks=[1.0],paths=200,seed=4,use_adverse_r=False)
        self.assertEqual(report["results"][0]["daily_dd_violation"]["probability"],1.0)

    def test_optimal_risk_targets_pass_probability(self):
        report=lab.run_lab(make_days([1.0]),self.cfg(max_days=30),risks=[0.1,0.5],paths=200,seed=11,use_adverse_r=False)
        self.assertEqual(report["optimal_risk_for_pass_pct"],0.5)

    def test_reproducible_and_common_risk_grid(self):
        days=make_days([2.0,-1.0,0.5,-1.0,3.0,-0.25])
        a=lab.run_lab(days,self.cfg(max_days=200,block_days=3),risks=[0.1,0.25,0.5],paths=300,seed=123,use_adverse_r=False)
        b=lab.run_lab(days,self.cfg(max_days=200,block_days=3),risks=[0.1,0.25,0.5],paths=300,seed=123,use_adverse_r=False)
        self.assertEqual(a,b)

    def test_csv_loader_guardian_schema(self):
        text=("run_stage,symbol,entry_time,exit_time,net_r,net_r_commission_x1_5\n"
              "DEV,EURUSD,2024.01.02 10:15,2024.01.02 11:00,1.25,1.20\n"
              "DEV,USDJPY,2024.01.03 12:00,2024.01.03 13:00,-1.05,-1.08\n")
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"trades.csv"; p.write_text(text,encoding="utf-8")
            trades,meta=lab.load_trades([str(p)],stage="DEV")
            self.assertEqual(len(trades),2)
            self.assertEqual(trades[0].r,1.25)
            self.assertEqual(meta["trade_count"],2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
