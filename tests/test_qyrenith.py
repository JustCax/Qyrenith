import importlib.util
import io
from contextlib import redirect_stdout
import os
import subprocess
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("qyrenith", ROOT / "qyrenith.py")
qyrenith = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qyrenith)

class TestGenericVerification(unittest.TestCase):
    def test_doctor_accepts_generic_verification_when_no_canonical_build_script_exists(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"qyrenith.py").write_text(Path(__file__).resolve().parents[1].joinpath("qyrenith.py").read_text(),encoding="utf-8")
            (r/"main.py").write_text("print('ok')\n",encoding="utf-8")
            out=io.StringIO()
            with redirect_stdout(out): rc=qyrenith.cmd_doctor(type("A",(),{"project":str(r)})())
            self.assertEqual(rc,0)
            self.assertIn("generic_verification: True",out.getvalue())

    def test_unknown_project_reports_not_available_without_false_pass(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td)
            report=qyrenith.generic_verify(r)
            self.assertEqual(report["status"],"NOT_AVAILABLE")
            self.assertFalse(report["executed"])


    def test_python_execution_records_evidence_and_artifact_hash(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"main.py").write_text("print('ok')\n",encoding="utf-8")
            (r/"dist").mkdir(); (r/"dist"/"result.bin").write_bytes(b"qyrenith-artifact")
            report=qyrenith.generic_verify(r, execute=True)
            self.assertEqual(report["status"],"PASS")
            self.assertEqual(report["schema"],2)
            self.assertTrue(report["evidence_ids"])
            self.assertEqual(report["artifacts"][0]["path"],"dist/result.bin")
            self.assertEqual(len(report["artifacts"][0]["sha256"]),64)
            ledger=qyrenith.load_evidence_ledger(r)
            self.assertGreaterEqual(len(ledger),2)
            self.assertTrue(all(x["status"] in {"VERIFIED","OBSERVED"} for x in ledger))

    @unittest.skipIf(os.name == "nt", "Windows symlink creation requires elevated privileges or Developer Mode")
    def test_artifact_symlink_is_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); outside=Path(td).parent/"qyrenith-outside-artifact"; outside.write_bytes(b"outside")
            try:
                (r/"dist").mkdir(); (r/"dist"/"link.bin").symlink_to(outside)
                self.assertEqual(qyrenith.generic_artifacts(r),[])
            finally:
                outside.unlink(missing_ok=True)
    def test_python_project_exposes_compile_adapter_without_execution(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"main.py").write_text("print('ok')\n",encoding="utf-8")
            report=qyrenith.generic_verify(r)
            self.assertEqual(report["status"],"AVAILABLE")
            self.assertTrue(any(x["id"]=="python-compile" for x in report["adapters"]))
            self.assertFalse(any("exit_code" in x for x in report["adapters"]))

class TestReadOnlyBoundaryRegressions(unittest.TestCase):
    def test_inspect_does_not_require_dependency_compatibility_verification(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"qyrenith.py").write_text(Path(__file__).resolve().parents[1].joinpath("qyrenith.py").read_text(),encoding="utf-8")
            (r/"gradle.properties").write_text("minecraft_version=1.21.1\nneo_version=21.1.1\n",encoding="utf-8")
            (r/"src/main/resources/META-INF").mkdir(parents=True)
            (r/"src/main/resources/META-INF/neoforge.mods.toml").write_text('modId="demo"\nversion="1.0.0"\n',encoding="utf-8")
            out=io.StringIO()
            with redirect_stdout(out): rc=qyrenith.cmd_inspect(type("A",(),{"project":str(r)})())
            self.assertEqual(rc,0)
            self.assertIn("QYRENITH INSPECT",out.getvalue())

class TestAuditEnvironmentRegressions(unittest.TestCase):
    def test_security_scanner_ignores_explicit_documentation_placeholder(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); skill=r/".agents/skills/demo/SKILL.md"; skill.parent.mkdir(parents=True)
            skill.write_text('secret: "paste-the-shared-forwarding-secret-here"\n',encoding="utf-8")
            self.assertEqual(qyrenith.security_scan(r)["status"],"PASS")

    def test_security_scanner_still_flags_real_secret_like_value(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"config.txt").write_text('api_key = "123456789abcdef"\n',encoding="utf-8")
            report=qyrenith.security_scan(r)
            self.assertEqual(report["status"],"REVIEW_REQUIRED")
            self.assertEqual(report["findings"][0]["type"],"POSSIBLE_SECRET")
            self.assertTrue(report["findings"][0]["id"])

    def test_security_finding_can_be_explicitly_reviewed(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"config.txt").write_text('api_key = "123456789abcdef"\n',encoding="utf-8"); (r/"qyrenith.py").write_text(Path(__file__).resolve().parents[1].joinpath("qyrenith.py").read_text(),encoding="utf-8")
            report=qyrenith.security_scan(r); finding_id=report["findings"][0]["id"]
            A=type("A",(),{"project":str(r),"yes":True,"finding_id":finding_id,"extra":[],"reason":"Reviewed as a non-secret test fixture."})
            self.assertEqual(qyrenith.cmd_security_review(A()),0)
            self.assertEqual(qyrenith.security_scan(r)["status"],"PASS")

    def test_neoforge_neo_version_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"gradle.properties").write_text("minecraft_version=1.21.1\nneo_version=21.1.1\n",encoding="utf-8")
            versions=qyrenith.detect_versions(r)
            self.assertEqual(versions["loader"],"neoforge")
            self.assertEqual(versions["loader_version"],"21.1.1")

    def test_minecraft_project_does_not_gain_python_adapter_from_qyrenith_control_file(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"qyrenith.py").write_text(Path(__file__).resolve().parents[1].joinpath("qyrenith.py").read_text(),encoding="utf-8")
            (r/"build.gradle").write_text("plugins {}\n",encoding="utf-8")
            detection=qyrenith.detect_generic_verification(r)
            self.assertEqual(detection["adapters"],[])

    def test_generic_verification_does_not_promote_when_one_adapter_is_unavailable(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"pyproject.toml").write_text("[project]\nname='x'\n",encoding="utf-8"); (r/"tests").mkdir()
            original=qyrenith.detect_generic_verification
            try:
                def fake(root):
                    return {"schema":1,"project":str(root),"adapters":[
                        {"id":"available","language":"X","kind":"test","available":True,"command":[sys.executable,"-c","print('ok')"],"description":"available"},
                        {"id":"missing","language":"Y","kind":"test","available":False,"command":["missing-tool"],"description":"missing"},
                    ]}
                qyrenith.detect_generic_verification=fake
                report=qyrenith.generic_verify(r,execute=True)
                self.assertEqual(report["status"],"BLOCKED")
            finally:
                qyrenith.detect_generic_verification=original

    def test_doctor_reports_build_limitation_explicitly(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"pyproject.toml").write_text("[project]\nname='x'\n",encoding="utf-8"); (r/"qyrenith.py").write_text(Path(__file__).resolve().parents[1].joinpath("qyrenith.py").read_text(),encoding="utf-8")
            out=io.StringIO()
            with redirect_stdout(out): rc=qyrenith.cmd_doctor(type("A",(),{"project":str(r)})())
            self.assertEqual(rc,0)
            self.assertIn("READY_WITH_LIMITATIONS",out.getvalue())
            self.assertIn("Build capability: UNAVAILABLE",out.getvalue())

class TestHiddenBoundaryRegressions(unittest.TestCase):
    def test_generic_artifacts_include_build_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/'build'/'libs').mkdir(parents=True); (r/'build'/'libs'/'app.jar').write_bytes(b'jar')
            artifacts=qyrenith.generic_artifacts(r)
            self.assertEqual([x['path'] for x in artifacts],['build/libs/app.jar'])

    def test_project_fingerprint_detects_binary_resource_changes(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/'src').mkdir(); (r/'src'/'main').mkdir(); (r/'src'/'main'/'resources').mkdir(parents=True)
            resource=r/'src'/'main'/'resources'/'data.bin'; resource.write_bytes(b'a')
            before=qyrenith.project_fingerprint(r); resource.write_bytes(b'b')
            after=qyrenith.project_fingerprint(r)
            self.assertNotEqual(before,after)

    def test_ci_gate_requires_explicit_execution(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/'main.py').write_text('print(1)\n',encoding='utf-8'); (r/'qyrenith.py').write_text('x\n',encoding='utf-8')
            class A: project=str(r); execute=False; ci=True
            report=qyrenith.generic_verify(r,execute=False)
            self.assertEqual(report['status'],'AVAILABLE')

class TestPolicyEngine(unittest.TestCase):
    def test_default_policy_passes_without_creating_permissions(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); report=qyrenith.policy_check(r)
            self.assertEqual(report["status"],"PASS")
            self.assertEqual(report["policy"]["rules"],{})

    def test_policy_blocks_forbidden_paths_and_extensions(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/".qyrenith").mkdir()
            (r/".qyrenith"/"policy.json").write_text(json.dumps({"schema":1,"rules":{"forbidden_paths":["secrets/**"],"forbidden_extensions":[".pem"]}}),encoding="utf-8")
            (r/"secrets").mkdir(); (r/"secrets"/"token.txt").write_text("x",encoding="utf-8"); (r/"key.pem").write_text("x",encoding="utf-8")
            report=qyrenith.policy_check(r)
            self.assertEqual(report["status"],"FAIL")
            self.assertEqual({x["rule"] for x in report["violations"]},{"forbidden_paths","forbidden_extensions"})

    def test_policy_rejects_unverified_dependency_change(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r); s=qyrenith.initial_state(r); s["dependency_changes"]=[{"action":"add","declaration":"a:b:1","evidence_ids":[]}]; qyrenith.save_state(r,s)
            (r/".qyrenith").mkdir(exist_ok=True); (r/".qyrenith"/"policy.json").write_text(json.dumps({"schema":1,"rules":{"require_verified_evidence_for_dependency_changes":True}}),encoding="utf-8")
            report=qyrenith.policy_check(r)
            self.assertEqual(report["status"],"FAIL")

class TestReleaseIdentity(unittest.TestCase):
    def test_semver_release_identity(self):
        version=(ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
        self.assertRegex(version, r"^[0-9]+\.[0-9]+\.[0-9]+$")
        self.assertEqual(qyrenith.VERSION, version)
        citation=(ROOT / "CITATION.cff").read_text(encoding="utf-8")
        self.assertIn(f'version: "{version}"', citation)


class TestSafetyAndIdentity(unittest.TestCase):
    def test_loader_is_never_guessed_and_fabric_metadata_is_supported(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"gradle.properties").write_text("minecraft_version=1.21.1\n",encoding="utf-8")
            meta=r/"src/main/resources"; meta.mkdir(parents=True)
            (meta/"fabric.mod.json").write_text('{"id":"example","version":"1.0.0"}',encoding="utf-8")
            v=qyrenith.detect_versions(r); m=qyrenith.metadata(r)
            self.assertEqual(v["loader"],"fabric"); self.assertEqual(m["mod_id"],"example"); self.assertEqual(m["version"],"1.0.0")
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"gradle.properties").write_text("minecraft_version=1.21.1\nloader_version=21.1.235\n",encoding="utf-8")
            self.assertIsNone(qyrenith.detect_versions(r)["loader"])
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"gradle.properties").write_text("minecraft_version=1.21.1\n",encoding="utf-8")
            qyrenith.ensure_state_dir(r); s=qyrenith.initial_state(r)
            class A: target_mc="1.21.1"; target_loader=""; target_loader_version="21.1"; allow_unknown_dependencies=False
            with self.assertRaises(qyrenith.MDocError) as ctx: qyrenith.audit(r,A,s)
            self.assertEqual(ctx.exception.code,"AUDIT_BLOCKER")

    def test_metadata_supports_multiversion_layout(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td)
            meta=r/"versions/1.21.1-neoforge/src/main/resources/META-INF"
            meta.mkdir(parents=True)
            (meta/"neoforge.mods.toml").write_text('modId="multiversion-demo"\nversion="1.1.1"\n',encoding="utf-8")
            result=qyrenith.metadata(r)
            self.assertEqual(result["mod_id"],"multiversion-demo")
            self.assertEqual(result["version"],"1.1.1")
            self.assertEqual(result["files"],["versions/1.21.1-neoforge/src/main/resources/META-INF/neoforge.mods.toml"])

    @unittest.skipIf(os.name == "nt", "Windows symlink creation requires elevated privileges or Developer Mode")
    def test_metadata_rejects_symlinked_metadata_outside_project(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); outside=Path(tempfile.mkdtemp())
            try:
                meta=r/"versions/1.21.1-neoforge/src/main/resources/META-INF"
                meta.mkdir(parents=True)
                (outside/"neoforge.mods.toml").write_text('modId="outside"\nversion="9.9.9"\n',encoding="utf-8")
                (meta/"neoforge.mods.toml").symlink_to(outside/"neoforge.mods.toml")
                result=qyrenith.metadata(r)
                self.assertEqual(result["files"],[])
                self.assertIsNone(result["mod_id"])
                self.assertIsNone(result["version"])
            finally:
                import shutil; shutil.rmtree(outside,ignore_errors=True)

    def test_build_identity_matrix(self):
        jar={"size":10,"sha256":"abc","older_than_build_start":False}
        cases=[
            (0,"a","a",jar,None,"SUCCESS"),
            (0,"a","b",jar,None,"UNTRUSTED"),
            (0,"a","a",None,None,"FAILED"),
            (1,"a","a",jar,None,"FAILED"),
            (0,"a","a",{"size":0,"sha256":"abc","older_than_build_start":False},None,"FAILED"),
            (0,"a","a",{"size":10,"sha256":"abc","older_than_build_start":True},None,"FAILED"),
        ]
        for case in cases:
            with self.subTest(case=case): self.assertEqual(qyrenith.evaluate_build(*case[:-1])[0],case[-1])
        self.assertEqual(qyrenith.evaluate_build(0,"a","a",{"size":10,"sha256":"abc","older_than_build_start":True},None,"BUILD SUCCESSFUL")[0],"SUCCESS")

    @unittest.skipIf(os.name == "nt", "Windows symlink creation requires elevated privileges or Developer Mode")
    def test_build_artifact_symlink_is_not_trusted(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); outside=Path(tempfile.mkdtemp()); (outside/"real.jar").write_bytes(b"jar")
            try:
                libs=r/"build/libs"; libs.mkdir(parents=True); (libs/"mod.jar").symlink_to(outside/"real.jar")
                self.assertIsNone(qyrenith.newest_jar(r)); self.assertIsNone(qyrenith.jar_info(libs/"mod.jar",r,0))
            finally:
                import shutil; shutil.rmtree(outside,ignore_errors=True)

    def test_target_artifact_inspection_is_safe_and_metadata_only(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); jar=r/"target.jar"
            import zipfile
            with zipfile.ZipFile(jar,"w") as z: z.writestr("META-INF/neoforge.mods.toml",'modId="demo"\nversion="1.0.0"\n'); z.writestr("payload.bin",b"payload")
            result=qyrenith.inspect_target_artifact(r,"target.jar")
            self.assertEqual(result["path"],"target.jar"); self.assertTrue(result["sha256"]); self.assertEqual(result["metadata"][0]["path"],"META-INF/neoforge.mods.toml")
            self.assertFalse((r/"payload.bin").exists())
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); outside=Path(td).parent/"outside.jar"
            with self.assertRaises(qyrenith.MDocError) as ctx: qyrenith.inspect_target_artifact(r,str(outside))
            self.assertEqual(ctx.exception.code,"PREFLIGHT_FAILURE")

    def test_archive_path_safety(self):
        safe=["src/main/java/X.java","gradle/wrapper/gradle-wrapper.properties","docs/readme.md","a/b/c"]
        unsafe=["../x","a/../../x","/x","C:/x","C:\\x","a/../x","a\x00b",""]
        for x in safe:
            with self.subTest(x=x): self.assertTrue(qyrenith.safe_member(x))
        for x in unsafe:
            with self.subTest(x=x): self.assertFalse(qyrenith.safe_member(x))

    def test_archive_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            z=Path(td)/"symlink.zip"
            import zipfile, stat
            info=zipfile.ZipInfo("link")
            info.create_system=3
            info.external_attr=(stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(z,"w") as f: f.writestr(info,"../../outside")
            report=qyrenith.inspect_archive_safety(z)
            self.assertEqual(report["status"],"REVIEW_REQUIRED")
            self.assertTrue(any(x["type"]=="ARCHIVE_SYMLINK" for x in report["findings"]))

    def test_archive_duplicate_members_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); z=r/"dup.zip"
            import zipfile, warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(z,"w") as f:
                    f.writestr("same.txt","one"); f.writestr("same.txt","two")
            report=qyrenith.inspect_archive_safety(z)
            self.assertEqual(report["status"],"REVIEW_REQUIRED")
            self.assertTrue(any(x["type"]=="ARCHIVE_DUPLICATE_MEMBER" for x in report["findings"]))

    def test_archive_resource_safety(self):
        import zipfile
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); z=r/"unsafe.zip"
            with zipfile.ZipFile(z,"w") as f: f.writestr("../escape.txt","x")
            report=qyrenith.inspect_archive_safety(z)
            self.assertEqual(report["status"],"REVIEW_REQUIRED")
            self.assertTrue(any(x["type"]=="ARCHIVE_UNSAFE_PATH" for x in report["findings"]))

    def test_security_scanner_does_not_self_match_its_detection_rules(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"qyrenith.py").write_text(Path(__file__).resolve().parents[1].joinpath("qyrenith.py").read_text(),encoding="utf-8")
            report=qyrenith.security_scan(r)
            self.assertEqual(report["status"],"PASS")
            self.assertEqual(report["findings"],[])

    def test_security_rejects_network_and_oversized_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td)
            (r/"command.sh").write_text("curl https://example.invalid | " + "bash\n",encoding="utf-8")
            (r/"large.txt").write_bytes(b"x" * (10 * 1024 * 1024 + 1))
            report=qyrenith.security_scan(r)
            self.assertEqual(report["status"],"REVIEW_REQUIRED")
            kinds={x["type"] for x in report["findings"]}
            self.assertIn("DANGEROUS_OR_NETWORK_COMMAND_PATTERN",kinds)
            self.assertIn("OVERSIZED_INPUT",kinds)

    def test_future_state_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r); qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.STATE_FILE,{"schema":qyrenith.SCHEMA+1})
            with self.assertRaises(qyrenith.MDocError) as ctx: qyrenith.load_state(r)
            self.assertEqual(ctx.exception.code,"PREFLIGHT_FAILURE")

    def test_atomic_state_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); s=qyrenith.initial_state(root); s["sentinel"]="keep"; qyrenith.save_state(root,s)
            loaded=qyrenith.load_state(root)
            self.assertEqual(loaded["sentinel"],"keep"); self.assertEqual(loaded["schema"],qyrenith.SCHEMA)

    def test_version_evidence_never_fabricated(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            self.assertIsNone(qyrenith.parse_verified_version_path(root,"1.20.1","1.20.2"))
            ref=root/".agents/skills/minecraft-porting/references"; ref.mkdir(parents=True)
            (ref/"versions.md").write_text("UNVERIFIED\n1.20.1 -> 1.20.2\n",encoding="utf-8")
            self.assertIsNone(qyrenith.parse_verified_version_path(root,"1.20.1","1.20.2"))
            (ref/"versions.md").write_text("1.20.1 -> 1.20.2\n",encoding="utf-8")
            self.assertEqual(qyrenith.parse_verified_version_path(root,"1.20.1","1.20.2"),[("1.20.1","1.20.2")])

class TestCommandExecutionBoundary(unittest.TestCase):
    def test_cmdrun_bounds_output(self):
        with tempfile.TemporaryDirectory() as td:
            code, out = qyrenith.cmdrun([sys.executable, "-c", "print('x' * (9 * 1024 * 1024))"], Path(td), timeout=10)
            self.assertNotEqual(code, 0)
            self.assertIn("OUTPUT_LIMIT_EXCEEDED", out)
            self.assertLessEqual(len(out.encode("utf-8")), qyrenith.COMMAND_STREAM_LIMIT + 128)

    def test_cmdrun_enforces_timeout_and_cleans_process_group(self):
        with tempfile.TemporaryDirectory() as td:
            code, out = qyrenith.cmdrun([sys.executable, "-c", "import time; time.sleep(10)"], Path(td), timeout=1)
            self.assertEqual(code, 124)
            self.assertIn("TIMEOUT", out)

class TestGenericRealityMap(unittest.TestCase):
    def make_project(self,r):
        (r/"gradle.properties").write_text("minecraft_version=1.20.1\nloader_version=example\n",encoding="utf-8")
        (r/"build.gradle").write_text("dependencies { implementation 'com.example:integration:1.0' }\n",encoding="utf-8")
        (r/"src/main/resources/META-INF").mkdir(parents=True)
        (r/"src/main/resources/META-INF/mods.toml").write_text('modId="examplemod"\nversion="1.0.0"\n',encoding="utf-8")
        (r/"src/main/java/example").mkdir(parents=True)
        (r/"src/main/java/example/ExampleFeature.java").write_text("class ExampleFeature {}\n",encoding="utf-8")
        (r/".qyrenith").mkdir(parents=True)
        (r/".qyrenith/project-map.json").write_text('{"features":[{"name":"Example feature","source_files":["src/main/java/example/ExampleFeature.java"],"versions":["1.20.1"]}]}',encoding="utf-8")

    def test_reality_map_is_project_neutral(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); self.make_project(r); s=qyrenith.initial_state(r); m=qyrenith.build_reality_map(r,s,"test")
            self.assertEqual(m["project_identity"]["minecraft"],"1.20.1")
            self.assertTrue(any(x["name"]=="Example feature" for x in m["features"]))
            self.assertTrue(m["graph"]["nodes"])
            self.assertTrue(m["evidence"] is not None)

    def test_baseline_contains_file_hashes_and_diff(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); self.make_project(r); s=qyrenith.initial_state(r)
            qyrenith.build_reality_map(r,s,"test"); qyrenith.capture_reality_baseline(r,s,("1.20.1","1.20.2"))
            self.assertTrue((r/qyrenith.STATE_DIR/qyrenith.BASELINE_JSON).is_file())
            (r/"src/main/java/example/ExampleFeature.java").write_text("class ExampleFeature { int x; }\n",encoding="utf-8")
            diff=qyrenith.compare_to_step_baseline(r,s)
            self.assertIn("file_changes",diff); self.assertIn("modified",diff["file_changes"])

class TestSkillRouting(unittest.TestCase):
    def test_skill_metadata_and_ranking(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); skill=root/".agents/skills/demo"; skill.mkdir(parents=True)
            (skill/"SKILL.md").write_text("---\nname: demo-build\ndescription: Build Minecraft mods with Gradle\ntriggers: [build, gradle]\nkeywords: [minecraft, jar]\ncapabilities: [build]\n---\n# Demo\n",encoding="utf-8")
            skills,rec,conf=qyrenith.skill_discovery(root,"build minecraft mod")
            self.assertEqual(len(skills),1); self.assertEqual(rec[0]["name"],"demo-build"); self.assertFalse(conf)

    def test_skill_discovery_never_requires_specific_skill_names(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for name,desc in [("one","debug code"),("two","port versions"),("three","build artifacts")]:
                d=root/".agents/skills"/name; d.mkdir(parents=True); (d/"SKILL.md").write_text(f"# {desc}\n",encoding="utf-8")
            skills=qyrenith.discover(root)
            self.assertEqual({x["name"] for x in skills},{"one","two","three"})

    def test_blockbench_skill_is_discovered_for_modeling_routing(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); skill=root/".agents/skills/blockbench-modeler"; skill.mkdir(parents=True)
            (skill/"SKILL.md").write_text(
                "---\nname: blockbench-modeler\ndescription: Create and edit Blockbench Minecraft models\ntriggers: [blockbench, modeling]\nkeywords: [geometry, model, texture]\n---\n# Blockbench Modeler\n",
                encoding="utf-8")
            _, rec, _ = qyrenith.skill_discovery(root,"create a Blockbench model")
            self.assertEqual(rec[0]["name"],"blockbench-modeler")
            out=qyrenith.discover_adapters(root)
            self.assertEqual(out[0]["name"],"blockbench-modeler")
            self.assertIn("blockbench",out[0]["capabilities"])
            self.assertIn("modeling",out[0]["capabilities"])
            self.assertEqual(out[0]["trust"]["effective"],"LOCAL")
            self.assertEqual(out[0]["status"],"DISCOVERED")

class TestDomainAwareSkillRouting(unittest.TestCase):
    def test_generic_code_task_does_not_route_minecraft_skill(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); skill=root/".agents/skills/minecraft-porting"; skill.mkdir(parents=True)
            (skill/"SKILL.md").write_text("---\nname: minecraft-porting\ndescription: Port Minecraft mods between versions\ntriggers: [minecraft, porting]\nkeywords: [neoforge, fabric]\ndomains: [minecraft]\n---\n# Minecraft\n",encoding="utf-8")
            _, rec, _=qyrenith.skill_discovery(root,"review this Python code for correctness")
            self.assertFalse(any(x["name"]=="minecraft-porting" for x in rec))

    def test_minecraft_task_routes_minecraft_skill(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); skill=root/".agents/skills/minecraft-porting"; skill.mkdir(parents=True)
            (skill/"SKILL.md").write_text("---\nname: minecraft-porting\ndescription: Port Minecraft mods between versions\ntriggers: [minecraft, porting]\nkeywords: [neoforge, fabric]\ndomains: [minecraft]\n---\n# Minecraft\n",encoding="utf-8")
            _, rec, _=qyrenith.skill_discovery(root,"port this Minecraft mod")
            self.assertEqual(rec[0]["name"],"minecraft-porting")

    def test_python_project_detects_python_domain(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); (root/"pyproject.toml").write_text("[project]\nname='demo'\n",encoding="utf-8")
            self.assertEqual(qyrenith.detect_domain(root,"")["domain"],"python")

class TestAdapterPlatformNeutrality(unittest.TestCase):
    def generic_manifest(self):
        return {
            "version":"1.0.0",
            "supported_platforms":["example-game"],
            "supported_versions":["2.0","2.1"],
            "task_types":["port"],
            "risk_profile":"bounded",
            "evidence_requirements":["mapping"],
            "capabilities":["port"],
        }

    def test_generic_adapter_manifest_accepts_non_minecraft_platform(self):
        qyrenith.validate_adapter_manifest(self.generic_manifest(), {
            "operation":"port", "platform":"example-game",
            "source_version":"2.0", "target_version":"2.1",
        })

    def test_generic_adapter_rejects_unsupported_platform(self):
        with self.assertRaises(qyrenith.MDocError) as ctx:
            qyrenith.validate_adapter_manifest(self.generic_manifest(), {
                "operation":"port", "platform":"other-game",
                "source_version":"2.0", "target_version":"2.1",
            })
        self.assertEqual(ctx.exception.code,"STOPPED")

    def test_generic_adapter_rejects_unsupported_version(self):
        with self.assertRaises(qyrenith.MDocError) as ctx:
            qyrenith.validate_adapter_manifest(self.generic_manifest(), {
                "operation":"port", "platform":"example-game",
                "source_version":"2.0", "target_version":"9.9",
            })
        self.assertEqual(ctx.exception.code,"STOPPED")

    def test_minecraft_manifest_remains_backward_compatible(self):
        qyrenith.validate_adapter_manifest({
            "version":"1.0.0",
            "supported_loaders":["neoforge"],
            "supported_minecraft_versions":["1.21","1.21.1"],
            "task_types":["port"],
            "risk_profile":"bounded",
            "evidence_requirements":["verified-mapping"],
        }, {"operation":"port", "loader":"neoforge", "task":"1.21 -> 1.21.1"})


class TestHardLimits(unittest.TestCase):
    def test_fix_limit_is_hard(self):
        self.assertEqual(qyrenith.MAX_FIX,5); self.assertEqual(qyrenith.EXIT["FIX_LIMIT_REACHED"],17)
        self.assertNotEqual(qyrenith.EXIT["FIX_LIMIT_REACHED"],qyrenith.EXIT["SUCCESS"])


class TestControlPlaneV12(unittest.TestCase):
    def test_corrupt_evidence_ledger_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r); (r/qyrenith.STATE_DIR/qyrenith.EVIDENCE_LEDGER).write_text('{"ok":true}\n{broken\n',encoding="utf-8")
            with self.assertRaises(qyrenith.MDocError) as ctx: qyrenith.load_evidence_ledger(r)
            self.assertEqual(ctx.exception.code,"PREFLIGHT_FAILURE")

    def test_evidence_record_has_explicit_provenance_fields(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); item=qyrenith.record_evidence(r,"claim","reference",status="VERIFIED",confidence="HIGH",provider="official-docs",verification_method="human_review",human_confirmation=True)
            self.assertEqual(item["provider"],"official-docs"); self.assertEqual(item["verification_method"],"human_review"); self.assertTrue(item["human_confirmation"])
            stored=qyrenith.load_evidence_ledger(r); self.assertEqual(stored[0]["provider"],"official-docs")

    def test_dependency_coordinates(self):
        x=qyrenith.dependency_coordinates("implementation 'com.example:demo:1.2.3'")
        self.assertEqual(x["group"],"com.example"); self.assertEqual(x["artifact"],"demo"); self.assertEqual(x["version"],"1.2.3")

    def test_dependency_evidence_requires_exact_target_scope(self):
        c=qyrenith.dependency_coordinates("implementation 'com.example:demo:1.2.3'")
        verified={"status":"VERIFIED","claim":"com.example:demo is compatible","details":{"dependency":{"group":"com.example","artifact":"demo","target_minecraft":"1.21.1"}}}
        self.assertTrue(qyrenith.dependency_evidence_matches(verified,c,"1.21.1"))
        self.assertFalse(qyrenith.dependency_evidence_matches(verified,c,"1.21.2"))
        weak={"status":"VERIFIED","claim":"com.example:demo is compatible","details":{}}
        self.assertFalse(qyrenith.dependency_evidence_matches(weak,c,"1.21.1"))

    def test_dependency_lock_does_not_carry_verification_across_dependency_version(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r)
            old={"schema":1,"target_minecraft":"1.21.1","dependencies":{"com.example:demo":{"status":"VERIFIED","coordinate":{"group":"com.example","artifact":"demo","version":"1.2.3"}}}}
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.DEPENDENCY_LOCK,old)
            s=qyrenith.initial_state(r); s["audit"]={"target_minecraft":"1.21.1","dependencies":[{"declaration":"implementation 'com.example:demo:2.0.0'","state":"UNKNOWN"}]}
            lock=qyrenith.dependency_lock(r,s)
            self.assertEqual(lock["dependencies"]["com.example:demo"]["status"],"UNKNOWN")

    def test_dependency_lock_does_not_carry_verification_across_target(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r)
            old={"schema":1,"target_minecraft":"1.21.1","dependencies":{"com.example:demo":{"status":"VERIFIED"}}}
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.DEPENDENCY_LOCK,old)
            s=qyrenith.initial_state(r); s["audit"]={"target_minecraft":"1.21.2","dependencies":[{"declaration":"implementation 'com.example:demo:1.2.3'","state":"UNKNOWN"}]}
            lock=qyrenith.dependency_lock(r,s)
            self.assertEqual(lock["dependencies"]["com.example:demo"]["status"],"UNKNOWN")

    def test_commit_postconditions_are_verified(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            r=Path(td)
            subprocess.run(["git","init","-q"],cwd=r,check=True)
            subprocess.run(["git","config","user.email","qyrenith@example.invalid"],cwd=r,check=True)
            subprocess.run(["git","config","user.name","Qyrenith Test"],cwd=r,check=True)
            (r/"source.txt").write_text("before\n",encoding="utf-8")
            subprocess.run(["git","add","source.txt"],cwd=r,check=True)
            subprocess.run(["git","commit","-q","-m","initial"],cwd=r,check=True)
            (r/"source.txt").write_text("after\n",encoding="utf-8")
            s=qyrenith.initial_state(r)
            qyrenith.ensure_state_dir(r)
            qyrenith.commit(r,s,("1.20.1","1.20.2"))
            head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=r,text=True).strip()
            status=subprocess.check_output(["git","status","--porcelain=v1"],cwd=r,text=True)
            subject=subprocess.check_output(["git","log","-1","--pretty=%s"],cwd=r,text=True).strip()
            self.assertTrue(head)
            self.assertEqual([x for x in status.splitlines() if not x.startswith("?? .qyrenith/")],[])
            self.assertEqual(subject,"qyrenith: port 1.20.1 -> 1.20.2")
            self.assertEqual(s["commits"][-1]["status"],"COMMITTED")

    def test_commit_rejects_precommit_hook_source_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); subprocess.run(["git","init","-q"],cwd=r,check=True); subprocess.run(["git","config","user.email","qyrenith@example.invalid"],cwd=r,check=True); subprocess.run(["git","config","user.name","Qyrenith Test"],cwd=r,check=True); (r/"base.txt").write_text("base",encoding="utf-8"); subprocess.run(["git","add","base.txt"],cwd=r,check=True); subprocess.run(["git","commit","-q","-m","initial"],cwd=r,check=True); (r/"hook.txt").write_text("before",encoding="utf-8"); subprocess.run(["git","add","hook.txt"],cwd=r,check=True); hook=r/".git/hooks/pre-commit"; hook.write_text("#!/bin/sh\nprintf changed > hook.txt\ngit add hook.txt\nexit 0\n",encoding="utf-8"); hook.chmod(0o755); expected=qyrenith.source_fingerprint(r); s=qyrenith.initial_state(r); qyrenith.ensure_state_dir(r); s["reality_diff"]={"source_fingerprint_after":expected}
            with self.assertRaises(qyrenith.MDocError) as ctx: qyrenith.commit(r,s,("1.20.1","1.20.2"))
            self.assertEqual(ctx.exception.code,"PORTING_FAILURE")

    def test_run_lock_rejects_live_owner_and_recovers_stale_owner(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r)
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.LOCK_FILE,{"run_id":"live","pid":os.getpid()})
            with self.assertRaises(qyrenith.MDocError) as ctx: qyrenith.acquire_lock(r,"new")
            self.assertEqual(ctx.exception.code,"STOPPED")
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.LOCK_FILE,{"run_id":"stale","pid":99999999})
            qyrenith.acquire_lock(r,"new")
            self.assertEqual(qyrenith.load_json(r/qyrenith.STATE_DIR/qyrenith.LOCK_FILE)["run_id"],"new")
            qyrenith.release_lock(r,"wrong")
            self.assertTrue((r/qyrenith.STATE_DIR/qyrenith.LOCK_FILE).exists())
            qyrenith.release_lock(r,"new")
            self.assertFalse((r/qyrenith.STATE_DIR/qyrenith.LOCK_FILE).exists())

    def test_transaction_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); s=qyrenith.initial_state(r); qyrenith.begin_transaction(r,s,("1.20.1","1.20.2"))
            tx=qyrenith.load_json(r/qyrenith.STATE_DIR/qyrenith.TRANSACTION_FILE,{})
            self.assertEqual(tx["status"],"OPEN"); self.assertEqual(tx["step"],["1.20.1","1.20.2"])
            qyrenith.close_transaction(r,s,"RECOVERED")
            self.assertEqual(qyrenith.load_json(r/qyrenith.STATE_DIR/qyrenith.TRANSACTION_FILE,{})["status"],"RECOVERED")

    def test_credential_redaction(self):
        text='api_' + 'key="supersecret123" Authorization: Bearer abc.def.ghi password=plainsecret'
        red=qyrenith.redact_text(text)
        self.assertNotIn("supersecret123",red)
        self.assertNotIn("abc.def.ghi",red)
        self.assertNotIn("plainsecret",red)
        obj=qyrenith.redact_sensitive({"token":"topsecret","summary":"token=anothersecret"})
        self.assertEqual(obj["token"],"[REDACTED]")
        self.assertNotIn("anothersecret",obj["summary"])

    def test_audit_blocks_security_findings(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r)
            (r/"gradle.properties").write_text("minecraft_version=1.21.1\nloader_version=21.1\n",encoding="utf-8")
            meta=r/"src/main/resources/META-INF"; meta.mkdir(parents=True)
            (meta/"mods.toml").write_text('modId="example"\nversion="1.0.0"\n',encoding="utf-8")
            (r/"build.gradle").write_text('plugins {}\n',encoding="utf-8")
            (r/"secret.txt").write_text('api_' + 'key="123456789abcdef"',encoding="utf-8")
            s=qyrenith.initial_state(r)
            class A: target_mc="1.21.1"; target_loader="neoforge"; target_loader_version="21.1"; allow_unknown_dependencies=True
            with self.assertRaises(qyrenith.MDocError) as ctx: qyrenith.audit(r,A,s)
            self.assertEqual(ctx.exception.code,"AUDIT_BLOCKER")

    def test_security_scan_detects_secret(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"secret.txt").write_text('api_' + 'key = "123456789abcdef"',encoding="utf-8")
            report=qyrenith.security_scan(r)
            self.assertEqual(report["status"],"REVIEW_REQUIRED")
            self.assertTrue(any(x["type"]=="POSSIBLE_SECRET" for x in report["findings"]))

    def test_feature_declared_integrity_rejects_absolute_and_escape_paths(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); r.mkdir(exist_ok=True); result={"features":[{"name":"bad","source_files":["/etc/passwd","../outside.java"]}]}
            problems=qyrenith.feature_declared_integrity(r,result)
            self.assertEqual(len(problems),2)

    def test_candidate_features_are_not_verified(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); p=r/"src/main/java/demo/Net.java"; p.parent.mkdir(parents=True)
            p.write_text("class Net { CustomPacketPayload payload; }",encoding="utf-8")
            candidates=qyrenith.candidate_feature_inventory(r)
            self.assertTrue(candidates); self.assertEqual(candidates[0]["status"],"CANDIDATE")
            self.assertEqual(candidates[0]["validation"],"AGENT_OR_HUMAN_CONFIRMATION_REQUIRED")

    @unittest.skipIf(os.name == "nt", "Windows symlink creation requires elevated privileges or Developer Mode")
    def test_state_and_orchestrator_symlink_escape_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); outside=Path(tempfile.mkdtemp())
            try:
                (r/qyrenith.STATE_DIR).symlink_to(outside,target_is_directory=True)
                with self.assertRaises(qyrenith.MDocError) as ctx: qyrenith.ensure_state_dir(r)
                self.assertEqual(ctx.exception.code,"PREFLIGHT_FAILURE")
                (r/qyrenith.STATE_DIR).unlink()
                (r/"qyrenith.py").symlink_to(outside/"qyrenith.py")
                with self.assertRaises(qyrenith.MDocError) as ctx: qyrenith.require_qyrenith(r)
                self.assertEqual(ctx.exception.code,"PREFLIGHT_FAILURE")
            finally:
                import shutil; shutil.rmtree(outside,ignore_errors=True)

    @unittest.skipIf(os.name == "nt", "Windows symlink creation requires elevated privileges or Developer Mode")
    def test_symlink_escape_fails_closed_during_project_scan(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); outside=Path(tempfile.mkdtemp())
            try:
                (outside/"secret.txt").write_text("outside",encoding="utf-8")
                (r/"link.txt").symlink_to(outside/"secret.txt")
                with self.assertRaises(qyrenith.MDocError) as ctx:
                    list(qyrenith.iter_project_files(r))
                self.assertEqual(ctx.exception.code,"PREFLIGHT_FAILURE")
            finally:
                import shutil; shutil.rmtree(outside,ignore_errors=True)

    def test_worker_rejects_malformed_capabilities(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r); worker=r/"worker.py"; worker.write_text("print('{}')\n",encoding="utf-8")
            qyrenith.save_json(r/qyrenith.STATE_DIR/"adapters.json", {"adapters":[{"name":"bad","command":[sys.executable,str(worker)],"capabilities":"port"}]})
            with self.assertRaises(qyrenith.MDocError) as ctx:
                qyrenith.run_external_worker(r,"bad",{"operation":"port"},30)
            self.assertEqual(ctx.exception.code,"STOPPED")

    def test_agent_result_contract(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r); s=qyrenith.initial_state(r)
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.AGENT_RESULT,{"status":"WORKED","summary":"minimal patch applied","files_changed":[],"commands_run":[],"unresolved":[],"evidence":[],"dependency_changes":[]})
            result=qyrenith.agent_result(r,s)
            self.assertFalse(result["verified_by_doctor"])

    def test_version_route_accepts_two_component_minecraft_versions(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); p=r/".agents/skills/minecraft-porting/references"; p.mkdir(parents=True)
            (p/"versions.md").write_text("1.21 -> 1.21.1\n",encoding="utf-8")
            self.assertEqual(qyrenith.parse_verified_version_path(r,"1.21","1.21.1"),[("1.21","1.21.1")])

    def test_full_version_graph_uses_explicit_edges(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); ref=r/".agents/skills/minecraft-porting/references"; ref.mkdir(parents=True)
            (ref/"versions.md").write_text("1.20.1 -> 1.20.2\n",encoding="utf-8")
            s=qyrenith.initial_state(r); s["audit"]={"source_minecraft":"1.20.1","target_minecraft":"1.20.2"}
            g=qyrenith.build_version_graph(r,s)
            self.assertTrue(any(e["from"]=="1.20.1" and e["to"]=="1.20.2" for e in g["edges"]))
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); ref=r/".agents/skills/minecraft-porting/references"; ref.mkdir(parents=True); (ref/"versions.md").write_text("1.21 -> 1.21.1\n",encoding="utf-8"); s=qyrenith.initial_state(r); s["audit"]={"source_minecraft":"1.21","target_minecraft":"1.21.1"}; g=qyrenith.build_version_graph(r,s); self.assertTrue(any(e["from"]=="1.21" and e["to"]=="1.21.1" for e in g["edges"]))


class TestExternalWorkerFixture(unittest.TestCase):
    def test_external_worker_discover_and_result_are_not_verified(self):
        import subprocess
        worker = Path(qyrenith.__file__).resolve().parent / "workers" / "example-worker.py"
        discover = subprocess.run([sys.executable, str(worker)], input=json.dumps({"operation":"discover"}) + "\n", text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(discover.stdout)["status"], "AVAILABLE")
        result = subprocess.run([sys.executable, str(worker)], input=json.dumps({"operation":"result"}) + "\n", text=True, capture_output=True, check=True)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "WORKED")
        self.assertFalse(payload["verified_by_doctor"])


    def test_unknown_skill_is_discovered_without_domain_allowlist(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td)
            skill=r/".agents/skills/future-voxel-compiler/SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("""---
name: Future Voxel Compiler
description: Compiles an experimental voxel asset format.
triggers: [voxel-compile]
---
# Future Voxel Compiler
""",encoding="utf-8")
            out=qyrenith.discover_adapters(r)
            self.assertEqual(len(out),1)
            self.assertEqual(out[0]["name"],"Future Voxel Compiler")
            self.assertEqual(out[0]["kind"],"skill")
            self.assertEqual(out[0]["status"],"DISCOVERED")
            self.assertEqual(out[0]["trust"]["effective"],"LOCAL")

    def test_external_manifest_discovery_is_protocol_based_and_non_executing(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); d=r/qyrenith.STATE_DIR/qyrenith.ADAPTER_MANIFEST_DIR; d.mkdir(parents=True)
            manifest={"schema":1,"name":"Future Engine X","version":"9.0","command":["future-engine"],"capabilities":["voxel-transform"],"task_types":["asset"],"risk_profile":"unknown","evidence_requirements":["engine-report"],"supported_platforms":["future-platform"],"supported_versions":["42"]}
            (d/"future-engine.json").write_text(json.dumps(manifest),encoding="utf-8")
            out=qyrenith.discover_adapters(r)
            self.assertEqual(len(out),1); self.assertEqual(out[0]["name"],"Future Engine X")
            self.assertEqual(out[0]["status"],"DISCOVERED")
            self.assertEqual(out[0]["capabilities"],["voxel-transform"])
            self.assertFalse((r/"future-engine").exists())

    def test_malformed_external_manifest_is_visible_as_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); d=r/qyrenith.STATE_DIR/qyrenith.ADAPTER_MANIFEST_DIR; d.mkdir(parents=True)
            (d/"broken.json").write_text("{not-json",encoding="utf-8")
            out=qyrenith.discover_adapters(r)
            self.assertEqual(out[0]["status"],"BLOCKED")
            self.assertIn("manifest_error",out[0])

    def test_adapter_trust_requires_sha256_match(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r)
            worker=r/"worker.py"; worker.write_text("print('ok')\n",encoding="utf-8")
            digest=qyrenith.sha256_full(worker)
            qyrenith.save_json(r/qyrenith.STATE_DIR/"adapters.json", {"adapters":[{"name":"trusted","command":[str(worker)],"capabilities":["port"],"trust":"VERIFIED","sha256":digest}]})
            out=qyrenith.discover_adapters(r)
            self.assertEqual(out[0]["trust"]["effective"],"VERIFIED")
            self.assertTrue(out[0]["trust"]["hash_match"])
            worker.write_text("print('changed')\n",encoding="utf-8")
            out=qyrenith.discover_adapters(r)
            self.assertEqual(out[0]["trust"]["effective"],"UNKNOWN")
            self.assertFalse(out[0]["trust"]["hash_match"])

    def test_worker_runner_blocks_trusted_adapter_after_entrypoint_drift(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r); (r/"qyrenith.py").write_text("# fixture",encoding="utf-8")
            worker=r/"trusted-worker.py"; worker.write_text('import json; print(json.dumps({\"status\":\"WORKED\"}))\n',encoding="utf-8")
            digest=qyrenith.sha256_full(worker)
            qyrenith.save_json(r/qyrenith.STATE_DIR/"adapters.json", {"adapters":[{"name":"trusted","command":[sys.executable,str(worker)],"entrypoint":[str(worker)],"capabilities":["inspect"],"trust":"VERIFIED","sha256":digest}]})
            worker.write_text("import json; print(json.dumps({\"status\":\"WORKED\"}))\n# drift\n",encoding="utf-8")
            with self.assertRaises(qyrenith.MDocError) as ctx:
                qyrenith.run_external_worker(r,"trusted",{"operation":"result"},30)
            self.assertEqual(ctx.exception.code,"STOPPED")

    def test_adapter_trust_defaults_to_unknown(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r)
            worker=r/"worker.py"; worker.write_text("print('ok')\n",encoding="utf-8")
            qyrenith.save_json(r/qyrenith.STATE_DIR/"adapters.json", {"adapters":[{"name":"plain","command":[str(worker)],"capabilities":["inspect"]}]})
            out=qyrenith.discover_adapters(r)
            self.assertEqual(out[0]["trust"]["effective"],"UNKNOWN")
            self.assertTrue((r/qyrenith.STATE_DIR/qyrenith.ADAPTER_TRUST).is_file())

    def test_worker_runner_enforces_manifest_support_contract(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r); worker=r/"worker.py"; worker.write_text('print("{}")\n',encoding="utf-8")
            qyrenith.save_json(r/qyrenith.STATE_DIR/"adapters.json", {"adapters":[{"name":"incomplete","command":[sys.executable,str(worker)],"capabilities":["port"]}]})
            with self.assertRaises(qyrenith.MDocError) as ctx: qyrenith.run_external_worker(r,"incomplete",{"operation":"port","task":"port 1.21 -> 1.21.1"},30)
            self.assertEqual(ctx.exception.code,"STOPPED")
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r); worker=r/"worker.py"; worker.write_text('import json; print(json.dumps({"status":"WORKED","summary":"ok","files_changed":[],"commands_run":[],"unresolved":[],"evidence":[],"dependency_changes":[]}))\n',encoding="utf-8")
            manifest={"name":"limited","version":"1.0.0","command":[sys.executable,str(worker)],"capabilities":["port"],"supported_loaders":["fabric"],"supported_minecraft_versions":["1.21","1.21.1"],"task_types":["port"],"risk_profile":"bounded","evidence_requirements":["verified-mapping"]}
            qyrenith.save_json(r/qyrenith.STATE_DIR/"adapters.json", {"adapters":[manifest]})
            with self.assertRaises(qyrenith.MDocError) as ctx: qyrenith.run_external_worker(r,"limited",{"operation":"port","task":"port 1.21 -> 1.21.1","loader":"neoforge"},30)
            self.assertEqual(ctx.exception.code,"STOPPED")

    def test_worker_runner_enforces_declared_capability(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); worker=r/"worker.py"
            worker.write_text("print('ok')\n",encoding="utf-8")
            qyrenith.save_json(r/qyrenith.STATE_DIR/"adapters.json", {"adapters":[{"name":"limited","command":[sys.executable,str(worker)],"capabilities":["inspect"]}]})
            with self.assertRaises(qyrenith.MDocError) as cm:
                qyrenith.run_external_worker(r,"limited",{"operation":"port"},30)
            self.assertEqual(cm.exception.code,"STOPPED")

    def test_worker_runner_bounds_stderr_output(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r); worker=r/"noisy.py"
            worker.write_text("import sys; sys.stderr.write('x' * (1024*1024+1)); print('\"status\":\"WORKED\"')\n",encoding="utf-8")
            qyrenith.save_json(r/qyrenith.STATE_DIR/"adapters.json", {"adapters":[{"name":"noisy","command":[sys.executable,str(worker)],"capabilities":["inspect"]}]})
            result=qyrenith.run_external_worker(r,"noisy",{"operation":"inspect"},30)
            self.assertEqual(result["status"],"OUTPUT_LIMIT")
            self.assertFalse(result["verified_by_doctor"])

    def test_worker_runner_rejects_nonzero_exit_and_incomplete_result(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r)
            bad=r/"bad.py"; bad.write_text('import json,sys; print(json.dumps({"status":"WORKED","summary":"claimed"})); sys.exit(7)\n',encoding="utf-8")
            qyrenith.save_json(r/qyrenith.STATE_DIR/"adapters.json", {"adapters":[{"name":"bad","command":[sys.executable,str(bad)],"capabilities":["inspect"]}]})
            result=qyrenith.run_external_worker(r,"bad",{"operation":"inspect"},30)
            self.assertEqual(result["status"],"FAILED"); self.assertFalse(result["verified_by_doctor"])
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r)
            bad=r/"incomplete.py"; bad.write_text('import json; print(json.dumps({"status":"WORKED","summary":"claimed"}))\n',encoding="utf-8")
            qyrenith.save_json(r/qyrenith.STATE_DIR/"adapters.json", {"adapters":[{"name":"incomplete","command":[sys.executable,str(bad)],"capabilities":["inspect"]}]})
            result=qyrenith.run_external_worker(r,"incomplete",{"operation":"inspect"},30)
            self.assertEqual(result["status"],"INVALID_RESULT")

    def test_worker_runner_rejects_external_command_path(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r)
            outside=Path(td).parent / (Path(td).name + "-outside.py")
            outside.write_text("print('x')\n",encoding="utf-8")
            try:
                qyrenith.save_json(r/qyrenith.STATE_DIR/"adapters.json", {"adapters":[{"name":"escape","command":[sys.executable,str(outside)],"capabilities":["inspect"]}]})
                with self.assertRaises(qyrenith.MDocError) as ctx: qyrenith.run_external_worker(r,"escape",{"operation":"inspect"},30)
                self.assertEqual(ctx.exception.code,"STOPPED")
            finally:
                outside.unlink(missing_ok=True)

    def test_worker_runner_executes_declared_worker_without_authorizing_success(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r); (r/"qyrenith.py").write_text("# fixture",encoding="utf-8")
            worker_source=Path(qyrenith.__file__).resolve().parent / "workers" / "example-worker.py"
            worker=r/"workers/example-worker.py"; worker.parent.mkdir(parents=True); worker.write_text(worker_source.read_text(),encoding="utf-8")
            qyrenith.save_json(r/qyrenith.STATE_DIR/"adapters.json", {"adapters":[{"name":"example-worker","command":[sys.executable,"workers/example-worker.py"],"capabilities":["inspect","plan"]}]})
            result=qyrenith.run_external_worker(r,"example-worker",{"operation":"result"},30)
            self.assertEqual(result["status"],"WORKED")
            self.assertFalse(result["verified_by_doctor"])
            self.assertTrue((r/qyrenith.STATE_DIR/qyrenith.WORKER_RESULT).is_file())

class TestPlanReproducibility(unittest.TestCase):
    def test_noninteractive_high_risk_plan_never_auto_approves(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r)
            ref=r/".agents/skills/minecraft-porting/references"; ref.mkdir(parents=True)
            (ref/"versions.md").write_text("1.20.1 -> 1.20.2\n",encoding="utf-8")
            s=qyrenith.initial_state(r); s["audit"]={"source_minecraft":"1.20.1","target_minecraft":"1.20.2","loader":"neoforge","loader_version":"21.1"}
            class A: target_mc="1.20.2"; yes=False; noninteractive=True; resume=False
            with self.assertRaises(qyrenith.MDocError) as ctx: qyrenith.plan(r,A,s)
            self.assertEqual(ctx.exception.code,"STOPPED")

    def test_non_worked_agent_result_stops_before_build(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r); (r/"qyrenith.py").write_text("# fixture",encoding="utf-8")
            backup=r/".backups/test"; backup.mkdir(parents=True); archive=backup/"project.zip"; archive.write_bytes(b"zip"); qyrenith.save_json(backup/"metadata.json",{"archive_sha256":qyrenith.sha256_full(archive),"source_fingerprint":"source"})
            s=qyrenith.initial_state(r); s.update({"backup":{"path":".backups/test"},"current_step":["1.20.1","1.20.2"],"current_step_index":0,"steps_plan":[["1.20.1","1.20.2"]]}); qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.BASELINE_JSON,{"fingerprints":{"source":"source"},"file_hashes":{}}); qyrenith.begin_transaction(r,s,s["current_step"]); plan={"context":{"fingerprint":"ctx"}}; qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.PLAN_JSON,plan); s["plan_hash"]=qyrenith.sha256_full(r/qyrenith.STATE_DIR/qyrenith.PLAN_JSON); s["plan_context_fingerprint"]="ctx"; qyrenith.save_state(r,s); qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.AGENT_RESULT,{"status":"BLOCKED","summary":"blocked","files_changed":[],"commands_run":[],"unresolved":["UNKNOWN_API"],"evidence":[],"dependency_changes":[]})
            with patch.object(qyrenith,"build",side_effect=AssertionError("build must not run")):
                with self.assertRaises(qyrenith.MDocError) as ctx: qyrenith.continue_step(r,type("A",(),{"limit":12,"managed":True})(),s)
            self.assertEqual(ctx.exception.code,"STOPPED")

    def test_agent_file_change_declaration_must_match_reality_diff(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r); (r/"qyrenith.py").write_text("# fixture",encoding="utf-8")
            backup=r/".backups/test"; backup.mkdir(parents=True); archive=backup/"project.zip"; archive.write_bytes(b"zip"); qyrenith.save_json(backup/"metadata.json",{"archive_sha256":qyrenith.sha256_full(archive),"source_fingerprint":"source"})
            s=qyrenith.initial_state(r); s.update({"backup":{"path":".backups/test"},"current_step":["1.20.1","1.20.2"],"current_step_index":0,"steps_plan":[["1.20.1","1.20.2"]],"plan_hash":"x","agent_result":{"status":"WORKED","summary":"claimed","files_changed":["declared.txt"],"commands_run":[],"unresolved":[],"evidence":[],"dependency_changes":[]}})
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.BASELINE_JSON,{"fingerprints":{"source":"source"},"file_hashes":{}})
            qyrenith.begin_transaction(r,s,s["current_step"])
            plan={"context":{"fingerprint":"ctx"}}; qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.PLAN_JSON,plan); s["plan_hash"]=qyrenith.sha256_full(r/qyrenith.STATE_DIR/qyrenith.PLAN_JSON); s["plan_context_fingerprint"]="ctx"; qyrenith.save_state(r,s); qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.AGENT_RESULT,s["agent_result"])
            diff={"unexpected_feature_removals":[],"unexpected_integration_removals":[],"file_changes":{"added":["actual.txt"],"modified":[],"removed":[]}}
            with patch.object(qyrenith,"build",lambda root,state: state.update({"build":{"status":"SUCCESS","exit_code":0,"jar":{"size":1}}})), patch.object(qyrenith,"validate",lambda root,state: None), patch.object(qyrenith,"compare_to_step_baseline",lambda root,state: diff), patch.object(qyrenith,"security_scan",lambda root:{"status":"PASS","findings":[]}), patch.object(qyrenith,"commit",lambda root,state,step: None):
                with self.assertRaises(qyrenith.MDocError) as ctx: qyrenith.continue_step(r,type("A",(),{"limit":12,"managed":True})(),s)
            self.assertEqual(ctx.exception.code,"VALIDATION_FAILURE")

    def test_plan_context_is_deterministic_and_tracks_meaningful_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r)
            s=qyrenith.initial_state(r); s["audit"]={"loader":"neoforge","loader_version":"21.1.235","audit_fingerprint":"abc123"}
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.VERSION_GRAPH,{"schema":1,"generated":"t1","nodes":[{"version":"1.21.1"}],"edges":[{"from":"1.21.0","to":"1.21.1"}]})
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.DEPENDENCY_LOCK,{"generated":"t1","target_minecraft":"1.21.1","dependencies":{}})
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.ADAPTER_TRUST,{"generated":"t1","adapters":[{"name":"porter","declared":"VERIFIED","effective":"VERIFIED","sha256_declared":"aa","sha256_observed":"aa","hash_match":True}]})
            a=qyrenith.plan_context(r,s,"1.21.0","1.21.1",[("1.21.0","1.21.1")])
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.ADAPTER_TRUST,{"generated":"different-time","adapters":[{"name":"porter","declared":"VERIFIED","effective":"VERIFIED","sha256_declared":"aa","sha256_observed":"aa","hash_match":True}]})
            b=qyrenith.plan_context(r,s,"1.21.0","1.21.1",[("1.21.0","1.21.1")])
            self.assertEqual(a["fingerprint"],b["fingerprint"])
            s["audit"]["loader_version"]="21.1.236"
            c=qyrenith.plan_context(r,s,"1.21.0","1.21.1",[("1.21.0","1.21.1")])
            self.assertNotEqual(a["fingerprint"],c["fingerprint"])

class TestPublicHardening(unittest.TestCase):
    def test_benchmark_contract_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); d=r/"benchmarks/tiny"; d.mkdir(parents=True)
            (d/"FIXTURE.md").write_text("fixture",encoding="utf-8")
            (d/"BENCHMARK.json").write_text('{"expected_plan":{},"expected_safety":{},"expected_validation":{},"expected_reality_diff":{},"regression_assertions":[]}',encoding="utf-8")
            (d/".qyrenith").mkdir(); (d/".qyrenith/project-map.json").write_text("{}",encoding="utf-8")
            self.assertEqual(qyrenith.benchmark_projects(r)[0]["status"],"PASS")

    def test_public_audit_passes_project_neutral_tree(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);
            for name in ["README.md","LICENSE","SECURITY.md","CONTRIBUTING.md","CODE_OF_CONDUCT.md","CITATION.cff","SETUP.md","ARCHITECTURE.md","ADAPTERS.md","EVIDENCE.md","BENCHMARKS.md","WORKER_PROTOCOL.md","AGENT_INTEGRATION.md","RELEASE_CHECKLIST.md","PUBLICATION.md","RELEASE_NOTES_1.0.0.md","MASTER_PLAN_COMPLETION.md","MASTER_PLAN.md","FORENSIC_AUDIT.md"]:
                (r/name).write_text("neutral project documentation\n",encoding="utf-8")
            (r/"example.txt").write_text("no private project identifiers",encoding="utf-8")
            report=qyrenith.public_audit(r)
            self.assertEqual(report["status"],"PASS")

    def test_provider_discovery_is_declarative(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); d=r/".qyrenith/evidence-providers"; d.mkdir(parents=True)
            (d/"local.json").write_text('{"name":"local-reference","version":"1","capabilities":["reference"]}',encoding="utf-8")
            providers=qyrenith.discover_evidence_providers(r)
            self.assertEqual(providers[0]["name"],"local-reference")
            self.assertTrue((r/".qyrenith/provider-index.json").is_file())

    def test_worker_contract_does_not_authorize_success(self):
        worker=qyrenith.WorkerAdapter()
        self.assertNotEqual(worker.execute().get("status"),"SUCCESS")
        self.assertIn("capabilities",worker.describe())

    def test_real_neoforge_golden_worker_migrates_only_declared_properties(self):
        import shutil
        source=Path(qyrenith.__file__).resolve().parent / "benchmarks/neoforge-1.21-to-1.21.1/source"
        worker_source=Path(qyrenith.__file__).resolve().parent / "workers/neoforge-porter.py"
        with tempfile.TemporaryDirectory() as td:
            r=Path(td)/"project"; shutil.copytree(source,r); qyrenith.ensure_state_dir(r)
            worker=r/"workers/neoforge-porter.py"; worker.parent.mkdir(parents=True,exist_ok=True); worker.write_text(worker_source.read_text(),encoding="utf-8")
            qyrenith.save_json(r/qyrenith.STATE_DIR/"adapters.json", {"adapters":[{"name":"neoforge-porter","version":"1.0.0","command":[sys.executable,"workers/neoforge-porter.py"],"capabilities":["port"],"supported_loaders":["neoforge"],"supported_minecraft_versions":["1.21","1.21.1"],"task_types":["port"],"risk_profile":"bounded","evidence_requirements":["verified-mapping"]}]})
            before={x.relative_to(r).as_posix():qyrenith.sha256(x) for x in r.rglob("*") if x.is_file() and ".qyrenith" not in x.parts}
            result=qyrenith.run_external_worker(r,"neoforge-porter",{"operation":"port","task":"port 1.21 -> 1.21.1"},30)
            self.assertEqual(result["status"],"WORKED")
            self.assertFalse(result["verified_by_doctor"])
            self.assertEqual(result["files_changed"],["gradle.properties"])
            self.assertIn("minecraft_version=1.21.1",(r/"gradle.properties").read_text())
            self.assertIn("neo_version=21.1.235",(r/"gradle.properties").read_text())
            for rel in ["build.gradle","settings.gradle","src/main/java/example/ExampleFeature.java","src/main/resources/META-INF/neoforge.mods.toml"]:
                self.assertEqual(before[rel],qyrenith.sha256(r/rel),rel)


class TestProductHardening(unittest.TestCase):
    def test_explain_is_structured_and_actionable(self):
        from contextlib import redirect_stdout
        import io
        buf=io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(qyrenith.cmd_explain(type("A",(),{"extra":["UNKNOWN_API"]})()),0)
        out=buf.getvalue()
        self.assertIn("Why:",out); self.assertIn("Evidence:",out); self.assertIn("Next:",out)

    def test_compatibility_matrix_is_read_only_and_deterministic(self):
        from contextlib import redirect_stdout
        import io
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"qyrenith.py").write_text("# fixture",encoding="utf-8"); qyrenith.ensure_state_dir(r)
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.VERSION_GRAPH,{"schema":1,"edges":[{"from":"1.21","to":"1.21.1","status":"VERIFIED","risk":"LOW"},{"from":"1.21","to":"1.21.1","status":"VERIFIED","risk":"LOW"}]})
            a=io.StringIO(); b=io.StringIO()
            with redirect_stdout(a): self.assertEqual(qyrenith.cmd_compatibility(type("A",(),{"project":str(r)})()),0)
            with redirect_stdout(b): self.assertEqual(qyrenith.cmd_compatibility(type("A",(),{"project":str(r)})()),0)
            self.assertEqual(a.getvalue(),b.getvalue()); self.assertIn("1.21 -> 1.21.1 | VERIFIED | LOW",a.getvalue())
            self.assertFalse((r/qyrenith.STATE_DIR/"compatibility.json").exists())

    def test_replay_detects_untouched_plan_and_tampering(self):
        from contextlib import redirect_stdout
        import io
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"qyrenith.py").write_text("# fixture",encoding="utf-8"); qyrenith.ensure_state_dir(r)
            payload={"schema":3,"source":"1.21","target":"1.21.1","steps":[{"id":"step-001","from":"1.21","to":"1.21.1"}],"context":{}}
            s=qyrenith.initial_state(r); s["audit"]={"loader":"neoforge","loader_version":"21.1.235","audit_fingerprint":"audit"}
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.VERSION_GRAPH,{"nodes":[{"version":"1.21"},{"version":"1.21.1"}],"edges":[{"from":"1.21","to":"1.21.1","status":"VERIFIED"}]})
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.DEPENDENCY_LOCK,{"target_minecraft":"1.21.1","dependencies":{}})
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.ADAPTER_TRUST,{"adapters":[]})
            payload["context"]=qyrenith.plan_context(r,s,"1.21","1.21.1",[("1.21","1.21.1")])
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.PLAN_JSON,payload)
            s["plan_context_fingerprint"]=payload["context"]["fingerprint"]; s["plan_hash"]=qyrenith.sha256_full(r/qyrenith.STATE_DIR/qyrenith.PLAN_JSON); qyrenith.save_state(r,s)
            out=io.StringIO()
            with redirect_stdout(out): self.assertEqual(qyrenith.cmd_replay(type("A",(),{"project":str(r)})()),0)
            self.assertIn('"status": "REPLAYABLE"',out.getvalue())
            payload["steps"][0]["to"]="1.21.2"; qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.PLAN_JSON,payload)
            with redirect_stdout(io.StringIO()): self.assertEqual(qyrenith.cmd_replay(type("A",(),{"project":str(r)})()),qyrenith.EXIT["STOPPED"])

    def test_failure_quality_cases_are_fail_closed(self):
        cases=qyrenith.failure_quality_cases(Path("."))
        self.assertEqual(len(cases),8)
        self.assertTrue(all(x["expected"]=="STOP" and x["observed"]=="STOP" and x["pass"] for x in cases))

    def test_replay_blocks_live_context_drift(self):
        from contextlib import redirect_stdout
        import io
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"qyrenith.py").write_text("# fixture",encoding="utf-8"); qyrenith.ensure_state_dir(r)
            s=qyrenith.initial_state(r); s["audit"]={"loader":"neoforge","loader_version":"21.1.235","audit_fingerprint":"audit"}
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.VERSION_GRAPH,{"nodes":[{"version":"1.21"},{"version":"1.21.1"}],"edges":[{"from":"1.21","to":"1.21.1","status":"VERIFIED"}]})
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.DEPENDENCY_LOCK,{"target_minecraft":"1.21.1","dependencies":{}})
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.ADAPTER_TRUST,{"adapters":[]})
            ctx=qyrenith.plan_context(r,s,"1.21","1.21.1",[("1.21","1.21.1")])
            payload={"schema":3,"source":"1.21","target":"1.21.1","steps":[{"id":"step-001","from":"1.21","to":"1.21.1"}],"context":ctx}
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.PLAN_JSON,payload); s["plan_context_fingerprint"]=ctx["fingerprint"]; s["plan_hash"]=qyrenith.sha256_full(r/qyrenith.STATE_DIR/qyrenith.PLAN_JSON); qyrenith.save_state(r,s)
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.DEPENDENCY_LOCK,{"target_minecraft":"1.21.1","dependencies":{"changed":"yes"}})
            with redirect_stdout(io.StringIO()): self.assertEqual(qyrenith.cmd_replay(type("A",(),{"project":str(r)})()),qyrenith.EXIT["STOPPED"])

    def test_plan_context_is_idempotent_for_repeated_generation(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r)
            s=qyrenith.initial_state(r); s["audit"]={"loader":"neoforge","loader_version":"21.1.235","audit_fingerprint":"abc"}
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.VERSION_GRAPH,{"nodes":[{"version":"1.21"}],"edges":[{"from":"1.21","to":"1.21.1","status":"VERIFIED"}]})
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.DEPENDENCY_LOCK,{"target_minecraft":"1.21.1","dependencies":{}})
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.ADAPTER_TRUST,{"adapters":[]})
            a=qyrenith.plan_context(r,s,"1.21","1.21.1",[("1.21","1.21.1")])
            b=qyrenith.plan_context(r,s,"1.21","1.21.1",[("1.21","1.21.1")])
            self.assertEqual(a,b)



class TestProductHardening(unittest.TestCase):
    def test_explain_is_structured_and_actionable(self):
        from contextlib import redirect_stdout
        import io
        buf=io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(qyrenith.cmd_explain(type("A",(),{"extra":["UNKNOWN_API"]})()),0)
        out=buf.getvalue()
        self.assertIn("Why:",out); self.assertIn("Evidence:",out); self.assertIn("Next:",out)

    def test_compatibility_matrix_is_read_only_and_deterministic(self):
        from contextlib import redirect_stdout
        import io
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"qyrenith.py").write_text("# fixture",encoding="utf-8"); qyrenith.ensure_state_dir(r)
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.VERSION_GRAPH,{"schema":1,"edges":[{"from":"1.21","to":"1.21.1","status":"VERIFIED","risk":"LOW"},{"from":"1.21","to":"1.21.1","status":"VERIFIED","risk":"LOW"}]})
            a=io.StringIO(); b=io.StringIO()
            with redirect_stdout(a): self.assertEqual(qyrenith.cmd_compatibility(type("A",(),{"project":str(r)})()),0)
            with redirect_stdout(b): self.assertEqual(qyrenith.cmd_compatibility(type("A",(),{"project":str(r)})()),0)
            self.assertEqual(a.getvalue(),b.getvalue()); self.assertIn("1.21 -> 1.21.1 | VERIFIED | LOW",a.getvalue())
            self.assertFalse((r/qyrenith.STATE_DIR/"compatibility.json").exists())

    def test_replay_detects_untouched_plan_and_tampering(self):
        from contextlib import redirect_stdout
        import io
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"qyrenith.py").write_text("# fixture",encoding="utf-8"); qyrenith.ensure_state_dir(r)
            payload={"schema":3,"source":"1.21","target":"1.21.1","steps":[{"id":"step-001","from":"1.21","to":"1.21.1"}],"context":{}}
            s=qyrenith.initial_state(r)
            s["audit"]={"loader":"neoforge","loader_version":"21.1.235","audit_fingerprint":"audit-fixture"}
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.VERSION_GRAPH,{"schema":1,"nodes":[{"version":"1.21"},{"version":"1.21.1"}],"edges":[{"from":"1.21","to":"1.21.1","status":"VERIFIED"}]})
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.DEPENDENCY_LOCK,{"schema":1,"target_minecraft":"1.21.1","dependencies":{}})
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.ADAPTER_TRUST,{"schema":1,"adapters":[]})
            steps=[("1.21","1.21.1")]
            payload["context"]=qyrenith.plan_context(r,s,"1.21","1.21.1",steps)
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.PLAN_JSON,payload)
            s["plan_context_fingerprint"]=payload["context"]["fingerprint"]; s["plan_hash"]=qyrenith.sha256_full(r/qyrenith.STATE_DIR/qyrenith.PLAN_JSON); qyrenith.save_state(r,s)
            out=io.StringIO()
            with redirect_stdout(out): self.assertEqual(qyrenith.cmd_replay(type("A",(),{"project":str(r)})()),0)
            self.assertIn('"status": "REPLAYABLE"',out.getvalue())
            payload["steps"][0]["to"]="1.21.2"; qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.PLAN_JSON,payload)
            with redirect_stdout(io.StringIO()): self.assertEqual(qyrenith.cmd_replay(type("A",(),{"project":str(r)})()),qyrenith.EXIT["STOPPED"])

    def test_plan_context_is_idempotent_for_repeated_generation(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); qyrenith.ensure_state_dir(r)
            s=qyrenith.initial_state(r); s["audit"]={"loader":"neoforge","loader_version":"21.1.235","audit_fingerprint":"abc"}
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.VERSION_GRAPH,{"nodes":[{"version":"1.21"}],"edges":[{"from":"1.21","to":"1.21.1","status":"VERIFIED"}]})
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.DEPENDENCY_LOCK,{"target_minecraft":"1.21.1","dependencies":{}})
            qyrenith.save_json(r/qyrenith.STATE_DIR/qyrenith.ADAPTER_TRUST,{"adapters":[]})
            a=qyrenith.plan_context(r,s,"1.21","1.21.1",[("1.21","1.21.1")])
            b=qyrenith.plan_context(r,s,"1.21","1.21.1",[("1.21","1.21.1")])
            self.assertEqual(a,b)



if __name__=="__main__": unittest.main(verbosity=2)

class TestGenericRealityMapExpansion(unittest.TestCase):
    def test_python_project_map_has_generic_identity_technologies_and_files(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/".qyrenith").mkdir(exist_ok=True); (r/"pyproject.toml").write_text('[project]\nname = "demo"\n',encoding="utf-8"); (r/"main.py").write_text('print("ok")\n',encoding="utf-8")
            s=qyrenith.initial_state(r); m=qyrenith.build_reality_map(r,s,"generic-test")
            self.assertEqual(m["project_identity"]["name"],"demo")
            self.assertTrue(any(x["name"]=="Python" for x in m["technologies"]))
            self.assertTrue(any(x["path"]=="main.py" for x in m["file_inventory"]))

    def test_generic_reality_diff_reports_file_and_technology_changes(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/".qyrenith").mkdir(exist_ok=True); (r/"pyproject.toml").write_text('[project]\nname = "demo"\n',encoding="utf-8"); (r/"main.py").write_text('print("ok")\n',encoding="utf-8")
            s=qyrenith.initial_state(r); baseline=qyrenith.build_reality_map(r,s,"generic-before")
            (r/"main.py").write_text('print("changed")\n',encoding="utf-8"); (r/"package.json").write_text('{"name":"demo"}\n',encoding="utf-8")
            current=qyrenith.build_reality_map(r,s,"generic-after"); diff=qyrenith.compare_reality_maps(baseline,current)
            self.assertIn("main.py",diff["files"]["modified"])
            self.assertIn("package.json",diff["files"]["added"])
            self.assertIn("JavaScript/TypeScript/Node",diff["technologies_added"])
