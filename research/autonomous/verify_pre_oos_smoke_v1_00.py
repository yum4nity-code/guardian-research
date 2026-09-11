"""Inspect smoke functionality only, without printing/ranking candidate PnL."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re


def verify(root,progress):
    root=Path(root)
    if not root.name.startswith('pre_oos_economic_feasibility_smoke_'):
        raise ValueError('smoke output required')
    data=(root/'feasibility_result.json').read_bytes()
    obj=json.loads(data)
    assert obj['status']=='SMOKE_PASS' and obj['source_candidates_ingested']==500 and obj['candidates_evaluated']==8
    assert len(obj['results'])==8 and not obj['provenance']['denied_accesses']
    market_reads=[x for x in obj['provenance']['input_accesses'] if x['path'].endswith('.csv')]
    assert len(market_reads)==4 and all(x['status']=='VERIFIED' for x in market_reads)
    identities=set(); trades=0
    for summary in obj['results']:
        ident=summary['id']; assert re.fullmatch(r'R4P-\d{4}',ident) and ident not in identities
        identities.add(ident)
        assert summary['status']=='SMOKE_NOT_FOR_SELECTION' and not summary['fail_reasons']
        assert summary['FUNDENDNEXT_PROFILE']['results'] is None
        ledger=json.loads((root/(ident+'.json')).read_text())['trades']
        assert len(ledger)==summary['executable_trades']
        previous=-1
        for row in ledger:
            assert row['signal']<row['available']<=row['entry']<=row['exit']<1767225600
            assert row['entry']>=previous and row['exit']>=row['exit_available']
            previous=row['exit']; trades+=1
            for p,c,s,l in [('E1',.000007,.0002,.0001),('STRESS',.000014,.0005,.0002)]:
                v=row['profiles'][p]; oe=row['entry_reference']; ox=row['exit_reference']
                assert math.isclose(v['spread'],(oe+ox)*s/2,rel_tol=1e-12)
                assert math.isclose(v['slippage'],(oe+ox)*l,rel_tol=1e-12)
                assert math.isclose(v['commission'],(v['entry_model']+v['exit_model'])*c,rel_tol=1e-12)
                assert math.isclose(v['net'],v['gross']-v['spread']-v['slippage']-v['commission'],abs_tol=1e-10)
    hb=json.loads(Path(progress).read_text())
    assert hb['phase']=='complete' and hb['completed']==hb['total']==8
    return {'status':'PASS','checks':'causal timing, overlap, bounds, costs, output identity, 500 ingestion, eight smoke-only records, four verified CSV reads, heartbeat','candidates':8,'ledger_rows_checked':trades,'elapsed_seconds':hb['elapsed_seconds'],'result_sha256':hashlib.sha256(data).hexdigest(),'denied_accesses':0,'performance_ranking_or_calibration':False,'source':str(root),'progress':str(progress)}


if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--output',required=True); ap.add_argument('--progress',required=True); ap.add_argument('--report',required=True)
    a=ap.parse_args(); result=verify(a.output,a.progress)
    Path(a.report).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result))
