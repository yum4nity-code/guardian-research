from pathlib import Path
import ast,json,os,tempfile,unittest
from unittest.mock import patch

BASE=Path(__file__).resolve().parent
class AtomicJsonTests(unittest.TestCase):
    def setUp(self):
        self.old=(BASE/'strategy_factory_random_search_v1_01.py').read_text()
        self.new=(BASE/'strategy_factory_random_search_v1_02.py').read_text()
        tree=ast.parse(self.new)
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='atomic_json')
        ns={'Path':Path,'json':json,'os':os}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<atomic_json>','exec'),ns)
        self.atomic=ns['atomic_json']
        self.tmp=tempfile.TemporaryDirectory(dir=BASE)
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'progress.json'
        self.path.write_text('{"previous":true}')
    def test_only_atomic_json_changed(self):
        def without_atomic(source):
            t=ast.parse(source)
            t.body=[n for n in t.body if not (isinstance(n,ast.FunctionDef) and n.name=='atomic_json')]
            return ast.dump(t)
        self.assertEqual(without_atomic(self.old),without_atomic(self.new))
    def test_success(self):
        with patch('time.sleep') as sleep:
            self.atomic(self.path,{'completed':100})
        self.assertEqual(json.loads(self.path.read_text()),{'completed':100})
        self.assertFalse(self.path.with_suffix('.json.tmp').exists())
        sleep.assert_not_called()
    def test_transient_permission_error(self):
        replace=os.replace
        attempts=[]
        def transient(src,dst):
            attempts.append(1)
            if len(attempts)<6:raise PermissionError(13,'WinError 5 simulation')
            replace(src,dst)
        with patch('os.replace',side_effect=transient),patch('time.sleep') as sleep:
            self.atomic(self.path,{'completed':100})
        self.assertEqual(len(attempts),6)
        self.assertAlmostEqual(sum(c.args[0] for c in sleep.call_args_list),0.75)
        self.assertEqual(json.loads(self.path.read_text()),{'completed':100})
    def test_exhaustion_explicit_with_original_cause(self):
        error=PermissionError(13,'locked')
        with patch('os.replace',side_effect=error) as replace,patch('time.sleep') as sleep:
            with self.assertRaisesRegex(PermissionError,'after 6 attempts') as ctx:
                self.atomic(self.path,{'completed':100})
        self.assertIs(ctx.exception.__cause__,error)
        self.assertIn(str(self.path),str(ctx.exception))
        self.assertEqual(replace.call_count,6)
        self.assertEqual(sleep.call_count,5)
        self.assertEqual(json.loads(self.path.read_text()),{'previous':True})
    def test_other_replace_exceptions_propagate_immediately(self):
        for error in [OSError(28,'disk full'),ValueError('invalid'),FileNotFoundError('missing')]:
            with self.subTest(error=error),patch('os.replace',side_effect=error) as replace,patch('time.sleep') as sleep:
                with self.assertRaises(type(error)) as ctx:self.atomic(self.path,{})
                self.assertIs(ctx.exception,error)
                replace.assert_called_once()
                sleep.assert_not_called()
    def test_write_error_is_not_retried(self):
        error=PermissionError('write blocked')
        with patch.object(Path,'write_text',side_effect=error),patch('os.replace') as replace,patch('time.sleep') as sleep:
            with self.assertRaises(PermissionError) as ctx:self.atomic(self.path,{})
            self.assertIs(ctx.exception,error)
            replace.assert_not_called()
            sleep.assert_not_called()
    def test_queue_protocol_identical(self):
        q=json.loads((BASE/'RESEARCH_QUEUE_APPEND.json').read_text())
        jobs=[j for j in q['jobs'] if j['id']=='STRATEGY-FACTORY-MULTI-ASSET-RANDOM']
        r2=next(j for j in jobs if j['revision']==2)
        r3=next(j for j in jobs if j['revision']==3)
        self.assertEqual(sum(j['revision']==3 for j in jobs),1)
        normalized=json.loads(json.dumps(r3).replace('v1_02','v1_01').replace('strategy_factory_r3','strategy_factory_r2').replace('RANDOM-R3.json','RANDOM-R2.json'))
        normalized['revision']=2
        self.assertEqual(r2,normalized)

if __name__=='__main__':unittest.main()
