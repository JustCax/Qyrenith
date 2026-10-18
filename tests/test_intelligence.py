import json
from pathlib import Path
import tempfile
import unittest

import qyrenith


class IntelligenceTests(unittest.TestCase):
    def make_project(self):
        td=tempfile.TemporaryDirectory(); root=Path(td.name)
        (root/'src').mkdir(); (root/'tests').mkdir()
        (root/'src'/'app.py').write_text('def alpha(x):\n    return x\n\nclass Worker:\n    pass\n',encoding='utf-8')
        (root/'tests'/'test_app.py').write_text('def test_alpha():\n    assert True\n',encoding='utf-8')
        qyrenith.ensure_state_dir(root)
        return td,root

    def test_semantic_inventory_and_unknown_baseline(self):
        td,r=self.make_project()
        try:
            result=qyrenith.build_semantic_reality_diff(r,None)
            self.assertEqual(result['diff']['status'],'UNKNOWN')
            self.assertTrue(result['inventory']['symbols'])
        finally: td.cleanup()

    def test_semantic_diff_detects_removed_and_modified_symbols(self):
        td,r=self.make_project()
        try:
            before=qyrenith.semantic_inventory(r)
            (r/'src'/'app.py').write_text('def alpha(x, y):\n    return x+y\n',encoding='utf-8')
            after=qyrenith.semantic_inventory(r)
            d=qyrenith.semantic_reality_diff(r,before,after)
            self.assertTrue(d['removed_symbols'])
            self.assertTrue(d['modified_symbols'])
        finally: td.cleanup()

    def test_regression_candidates_are_non_executable(self):
        td,r=self.make_project()
        try:
            before=qyrenith.semantic_inventory(r)
            (r/'src'/'app.py').write_text('def beta(x):\n    return x\n',encoding='utf-8')
            sem=qyrenith.build_semantic_reality_diff(r,before)
            c=qyrenith.synthesize_regression_candidates(r,sem)
            t=qyrenith.build_regression_validation_tasks(r,c)
            self.assertTrue(c['candidates'])
            self.assertTrue(all(x['execution_authority']=='NONE' for x in c['candidates']))
            self.assertTrue(all(x['execution_authority']=='NONE' for x in t['tasks']))
        finally: td.cleanup()

    def test_feature_contract_and_coverage(self):
        td,r=self.make_project()
        try:
            qyrenith._iq_write(r,'feature_contracts',{'schema':1,'features':[{'id':'alpha','verification':{}}]})
            cov=qyrenith.verification_coverage(r)
            self.assertEqual(len(cov['contract_gaps']),1)
            self.assertIn('runtime',cov['contract_gaps'][0]['missing'])
        finally: td.cleanup()

    def test_proof_bundle_does_not_certify_unknown_baseline(self):
        td,r=self.make_project()
        try:
            qyrenith.build_semantic_reality_diff(r,None)
            qyrenith.verification_coverage(r)
            qyrenith.causal_analysis(r)
            qyrenith.intent_preservation(r)
            qyrenith.build_regression_validation_tasks(r, qyrenith.synthesize_regression_candidates(r))
            qyrenith.resolve_evidence_contradictions(r)
            proof=qyrenith.proof_carrying_change(r)
            self.assertEqual(proof['status'],'READY_FOR_VERIFICATION')
            self.assertEqual(proof['execution_authority'],'NONE')
        finally: td.cleanup()

    def test_mutation_plan_is_read_only(self):
        td,r=self.make_project()
        try:
            result=qyrenith.mutation_plan(r)
            self.assertTrue(result['safe_mode'])
            self.assertFalse(result['project_mutation_permitted'])
            self.assertTrue(result['mutations'])
        finally: td.cleanup()

    def test_engineering_memory_is_append_only(self):
        td,r=self.make_project()
        try:
            qyrenith.engineering_memory(r,{'kind':'incident','subject':'alpha','status':'VERIFIED'})
            qyrenith.engineering_memory(r,{'kind':'decision','subject':'alpha','status':'VERIFIED'})
            m=qyrenith.engineering_memory(r)
            self.assertEqual(len(m['entries']),2)
            self.assertTrue(m['append_only'])
        finally: td.cleanup()

    def test_compatibility_graph_does_not_fabricate_edges(self):
        td,r=self.make_project()
        try:
            c=qyrenith.compatibility_graph(r)
            self.assertFalse(c['fabricated_edges'])
            self.assertEqual(c['edges'],[])
        finally: td.cleanup()

    def test_counterfactual_plan_requires_isolation(self):
        td,r=self.make_project()
        try:
            c=qyrenith.counterfactual_plan(r)
            self.assertTrue(c['isolated_execution_required'])
            self.assertEqual(len(c['variants']),4)
        finally: td.cleanup()

    def test_failure_injection_is_plan_only(self):
        td,r=self.make_project()
        try:
            f=qyrenith.failure_injection_plan(r)
            self.assertTrue(f['cases'])
            self.assertTrue(all(x['execution_authority']=='NONE' for x in f['cases']))
        finally: td.cleanup()

    def test_runtime_lab_requires_explicit_declared_command(self):
        td,r=self.make_project()
        try:
            result=qyrenith.execute_runtime_lab(r)
            self.assertEqual(result["status"],"NOT_AVAILABLE")
            self.assertEqual(result["execution_authority"],"NONE")
        finally: td.cleanup()

    def test_failure_lab_requires_explicit_declared_command(self):
        td,r=self.make_project()
        try:
            qyrenith.failure_injection_plan(r)
            result=qyrenith.execute_failure_injection_lab(r)
            self.assertEqual(result["status"],"NOT_AVAILABLE")
            self.assertEqual(result["execution_authority"],"NONE")
        finally: td.cleanup()

    def test_explicit_runtime_command_isolated_and_verified(self):
        td,r=self.make_project()
        try:
            qyrenith.save_json(r/qyrenith.STATE_DIR/"intelligence-config.json",{"commands":{"runtime":["python","-c","print(123)"]}})
            result=qyrenith.execute_runtime_lab(r,timeout=10)
            self.assertEqual(result["status"],"PASS")
            self.assertEqual(result["execution_authority"],"EXPLICIT")
            self.assertEqual(result["commands"]["runtime"]["exit_code"],0)
        finally: td.cleanup()

    def test_intelligence_generation_is_not_verification_pass(self):
        td,r=self.make_project()
        try:
            result=qyrenith.intelligence_suite(r)
            self.assertEqual(result["status"],"GENERATED")
            self.assertNotEqual(result["status"],"PASS")
        finally: td.cleanup()

    def test_feature_gap_matches_symbol_names_not_symbol_dicts(self):
        td,r=self.make_project()
        try:
            qyrenith._iq_write(r,'feature_contracts',{'schema':1,'features':[{'id':'f','implementation_symbols':['alpha'],'verification':{k:True for k in ['source','build','runtime','server','client','multiplayer','regression','docs','performance','security']}}]})
            gaps=qyrenith.feature_verification_gaps(r)
            self.assertEqual(gaps['gaps'],[])
        finally: td.cleanup()

    def test_unrelated_verified_evidence_does_not_mark_build_observed(self):
        td,r=self.make_project()
        try:
            qyrenith.record_evidence(r,'Unrelated claim','foo',status='VERIFIED',confidence='HIGH',provider='unrelated',verification_method='unit')
            cov=qyrenith.verification_coverage(r)
            self.assertEqual(cov['dimensions']['build']['status'],'UNKNOWN')
        finally: td.cleanup()

    def test_empty_failure_injection_execution_is_not_pass(self):
        td,r=self.make_project()
        try:
            qyrenith._iq_write(r,'failure_lab',{'schema':1,'cases':[]})
            qyrenith.save_json(r/qyrenith.STATE_DIR/'intelligence-config.json',{'commands':{'failure-validation':['python','-c','print(0)']}})
            result=qyrenith.execute_failure_injection_lab(r)
            self.assertEqual(result['status'],'NOT_AVAILABLE')
        finally: td.cleanup()

    def test_verdict_never_promotes_unknown_to_pass(self):
        td,r=self.make_project()
        try:
            qyrenith.intelligence_suite(r)
            verdict=qyrenith.verification_verdict(r)
            self.assertNotEqual(verdict["verdict"],"PASS")
            self.assertTrue(verdict["independent_verification_required"])
        finally: td.cleanup()

    def test_intelligence_suite_is_deterministic_on_unchanged_tree(self):
        td,r=self.make_project()
        try:
            first=qyrenith.intelligence_suite(r)
            second=qyrenith.intelligence_suite(r)
            self.assertEqual(first['status'],'GENERATED')
            self.assertEqual(second['status'],'GENERATED')
            self.assertIn(first['proof_status'], {'READY_FOR_VERIFICATION','CANDIDATE'}); self.assertEqual(second['proof_status'],'CANDIDATE')
            a=json.loads((r/'.qyrenith'/'semantic-reality-diff.json').read_text())
            self.assertEqual(a['diff']['status'],'OBSERVED')
        finally: td.cleanup()


if __name__=='__main__':
    unittest.main()
