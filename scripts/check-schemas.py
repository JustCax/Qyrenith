#!/usr/bin/env python3
"""Validate repository JSON schema contracts without third-party dependencies."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "worker-handoff.schema.json": ["schema", "worker", "task", "source", "target", "project_root", "constraints"],
    "worker-result.schema.json": ["schema", "worker", "status", "summary", "files_changed", "commands_run", "unresolved", "evidence", "dependency_changes"],
    "adapter-manifest.schema.json": ["schema", "name", "version", "capabilities", "task_types", "risk_profile", "evidence_requirements", "command"],
    "evidence.schema.json": ["id", "time", "claim", "source", "status", "confidence", "provider", "verification_method", "details"],
    "migration-assurance-record.schema.json": [
        "schema", "sequence", "run_id", "step_id", "transition_id", "source_identity",
        "target_identity", "plan_digest", "pre_state_digest", "worker_id", "worker_version",
        "worker_manifest_digest", "worker_qualification_id", "worker_qualification_digest", "worker_status",
        "changed_files", "diff_digest", "evidence_ids", "verdict", "post_state_digest",
        "artifact_digest", "commit_id", "recovery_reference", "created_at",
        "previous_digest", "record_digest",
    ],
    "migration-knowledge.schema.json": [
        "schema", "claim_id", "subject", "statement", "assertion", "source", "target",
        "status", "evidence", "verified_by", "verified_at", "valid_until",
        "verified_with", "verifier_version", "verifier_digest",
    ],
    "migration-transition.schema.json": [
        "schema", "transition_id", "source", "target", "kind", "knowledge_claim_ids",
        "worker_id", "worker_version", "required_capabilities", "enabled",
    ],
    "migration-worker-manifest.schema.json": [
        "schema", "worker_id", "worker_version", "implementation_digest",
        "protocol_version", "scopes", "capabilities", "permissions", "limits", "manifest_digest",
    ],
    "migration-worker-qualification.schema.json": [
        "schema", "qualification_id", "worker_id", "worker_version", "manifest_digest",
        "conformance_suite_id", "conformance_suite_version", "conformance_suite_digest",
        "result_digest", "result_status", "test_count", "qualified_by", "qualified_at", "valid_until",
    ],
    "migration-worker-assessment.schema.json": [
        "schema", "route_plan_digest", "evaluated_at", "status", "evaluations", "reason",
    ],
    "migration-authorization.schema.json": [
        "schema", "route_plan_digest", "worker_assessment_digest", "policy_digest",
        "approved_by", "approved_at", "expires_at", "grants", "authorization_digest",
    ],
    "migration-authorization-policy.schema.json": [
        "schema", "allowed_permissions", "max_timeout_seconds", "max_input_bytes",
        "max_output_bytes", "max_changed_files", "max_lifetime_seconds",
        "allowed_worker_ids", "policy_digest",
    ],
    "owner-trust-store.schema.json": [
        "schema", "store_id", "generation", "events", "hmac_sha256",
    ],
    "host-approval.schema.json": [
        "schema", "approval_id", "request_id", "action_type", "request_digest",
        "scope_digest", "issued_at", "approved_at", "expires_at", "nonce",
        "approved_by", "host_principal", "trust_store_id",
        "trust_store_generation", "signature",
    ],
    "qdas-execution-event.schema.json": [
        "schema", "event_id", "project_id", "project_revision", "workspace_id",
        "event_kind", "os_name", "os_version", "architecture", "runtime_name",
        "runtime_version", "tool_name", "tool_version", "argv", "working_directory",
        "environment_digest", "started_at", "finished_at", "duration_milliseconds",
        "exit_code", "execution_status", "timed_out", "output_limited",
        "output_incomplete", "input_incomplete", "unsupported_state",
        "stdout_bytes", "stderr_bytes", "stdout_digest", "stderr_digest",
    ],
    "qdas-event-ledger-record.schema.json": [
        "schema", "sequence", "previous_digest", "event", "classification", "record_digest",
    ],
    "migration-project-snapshot.schema.json": [
        "schema", "entries", "excluded_paths", "limits", "captured_at", "snapshot_digest",
    ],
    "migration-workspace-descriptor.schema.json": [
        "schema", "workspace_id", "workspace_path", "project_path", "target",
        "source_snapshot_digest", "file_count", "total_bytes", "created_at", "descriptor_digest",
    ],
}
EXPECTED_TRANSITION_KINDS = {
    "VERSION_UPGRADE", "LOADER_CONVERSION", "FRAMEWORK_CHANGE", "PLATFORM_MIGRATION",
    "TOOLCHAIN_CHANGE", "DEPENDENCY_MIGRATION", "PROJECT_PROFILE_CHANGE",
}
EXPECTED_WORKER_PERMISSIONS = {
    "READ_PROJECT", "WRITE_PROJECT", "EXECUTE_PROCESS", "NETWORK",
    "INSTALL_DEPENDENCIES", "GIT_WRITE", "PUBLISH_ARTIFACT",
}
EXPECTED_KNOWLEDGE_STATES = {
    "OBSERVED", "INFERRED", "UNKNOWN", "VERIFIED", "CONFLICTED", "STALE",
}


def require(condition, message):
    if not condition:
        raise SystemExit("JSON schema contract failed: " + message)


def read_schema(name):
    path = ROOT / "schemas" / name
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SystemExit(f"JSON schema contract failed: cannot read {name}: {exc}") from exc
    require(isinstance(schema, dict), f"{name} must be a JSON object")
    require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema",
            f"{name} must declare JSON Schema 2020-12")
    require(schema.get("type") == "object", f"{name} must define an object")
    require(isinstance(schema.get("properties"), dict), f"{name} must define properties")
    required = schema.get("required")
    require(isinstance(required, list), f"{name} must define a required array")
    require(len(required) == len(set(required)), f"{name} has duplicate required fields")
    require(set(required).issubset(schema["properties"]), f"{name} requires an undefined property")
    return schema


schemas = {name: read_schema(name) for name in EXPECTED}
for name, required_fields in EXPECTED.items():
    schema = schemas[name]
    require(all(field in schema["required"] for field in required_fields),
            f"{name} is missing required contract fields")
    if name.startswith("migration-"):
        require(schema.get("additionalProperties") is False,
                f"{name} must reject unknown top-level fields")
        expected_schema_version = 2 if name == "migration-knowledge.schema.json" else 1
        require(schema["properties"].get("schema") == {"const": expected_schema_version},
                f"{name} must pin schema version {expected_schema_version}")

owner_trust = schemas["owner-trust-store.schema.json"]
require(owner_trust.get("additionalProperties") is False,
        "owner trust store must reject unknown top-level fields")
require(owner_trust["properties"]["store_id"].get("pattern") == "^[0-9a-f]{32}$",
        "owner trust store identity format mismatch")
require(owner_trust["properties"]["hmac_sha256"].get("pattern") == "^[0-9a-f]{64}$",
        "owner trust store integrity MAC format mismatch")
require(owner_trust["properties"]["events"].get("maxItems") == 100000,
        "owner trust store event history must be bounded")
trust_event = owner_trust["$defs"]["event"]
require(trust_event.get("additionalProperties") is False,
        "owner trust events must reject unknown fields")
require(set(trust_event["properties"]["subject_kind"].get("enum", [])) == {
    "KNOWLEDGE_CATALOG", "WORKER_MANIFEST", "WORKER_QUALIFICATION",
    "EXECUTION_POLICY", "APPROVAL_NONCE",
}, "owner trust subject vocabulary mismatch")
require(set(trust_event["properties"]["decision"].get("enum", [])) == {"TRUST", "REVOKE", "CONSUME"},
        "owner trust decision vocabulary mismatch")
require(trust_event["properties"]["subject_digest"].get("pattern") == "^sha256:[0-9a-f]{64}$",
        "owner trust decisions must bind exact SHA-256 digests")
require(len(trust_event.get("allOf", [])) == 4,
        "owner trust revocation and nonce-consumption rules are incomplete")
require(all(
    rule.get("then", {}).get("properties", {}).get("expires_at", {}).get("type") == "null"
    for rule in trust_event["allOf"][:2]
), "owner trust revocations and nonce consumption must not expire")
require(trust_event["allOf"][2].get("then", {}).get("properties", {}).get("decision", {}).get("const") == "CONSUME",
        "approval nonce events must only record CONSUME")
require(set(trust_event["allOf"][3].get("then", {}).get("properties", {}).get("decision", {}).get("enum", [])) == {"TRUST", "REVOKE"},
        "non-nonce trust events must only record TRUST or REVOKE")

host_approval = schemas["host-approval.schema.json"]
require(host_approval.get("additionalProperties") is False,
        "host approval must reject unknown fields")
require(host_approval["properties"]["request_digest"].get("pattern") == "^[0-9a-f]{64}$",
        "host approval must bind the request digest")
require(host_approval["properties"]["scope_digest"].get("pattern") == "^[0-9a-f]{64}$",
        "host approval must bind the exact scope digest")
require(host_approval["properties"]["nonce"].get("pattern") == "^[0-9a-f]{48}$",
        "host approval must carry a one-time nonce")
require(host_approval["properties"]["signature"].get("pattern") == "^[0-9a-f]{64}$",
        "host approval must carry a keyed integrity signature")
require(host_approval["properties"]["trust_store_id"].get("pattern") == "^[0-9a-f]{32}$",
        "host approval must bind the owner trust store identity")
require(host_approval["properties"]["trust_store_generation"].get("minimum") == 0,
        "host approval must bind a non-negative owner trust-store generation")
require(host_approval["properties"]["action_type"].get("pattern") == "^[A-Z][A-Z0-9_]{1,63}$",
        "host approval action type must be a canonical identifier")

qdas_event = schemas["qdas-execution-event.schema.json"]
require(qdas_event.get("additionalProperties") is False,
        "QDAS execution events must reject undeclared fields")
require(set(qdas_event["properties"]["event_kind"].get("enum", [])) ==
        {"BUILD", "TEST", "STATIC_ANALYSIS", "RUNTIME", "VERIFICATION", "OTHER"},
        "QDAS event kind vocabulary mismatch")
require(set(qdas_event["properties"]["execution_status"].get("enum", [])) ==
        {"PASS", "FAIL", "BLOCKED", "ERROR"},
        "QDAS execution status vocabulary mismatch")
require(qdas_event["properties"]["environment_digest"].get("pattern") == "^[0-9a-f]{64}$",
        "QDAS events must carry an environment fingerprint")
require(qdas_event["properties"]["argv"].get("maxItems") == 256,
        "QDAS event argv must be bounded")
require(qdas_event["properties"]["stdout_bytes"].get("maximum") == 8388608 and
        qdas_event["properties"]["stderr_bytes"].get("maximum") == 8388608,
        "QDAS event output capture must be bounded")
require(len(qdas_event.get("allOf", [])) == 1,
        "QDAS event schema must prevent false PASS results")
pass_event_rule = qdas_event["allOf"][0].get("then", {}).get("properties", {})
require(pass_event_rule.get("exit_code", {}).get("const") == 0 and
        pass_event_rule.get("timed_out", {}).get("const") is False and
        pass_event_rule.get("unsupported_state", {}).get("const") is False,
        "QDAS PASS events must require successful exit and no blocking flags")

qdas_ledger = schemas["qdas-event-ledger-record.schema.json"]
require(qdas_ledger.get("additionalProperties") is False,
        "QDAS ledger records must reject undeclared fields")
require(qdas_ledger["properties"]["event"].get("$ref") == "qdas-execution-event.schema.json",
        "QDAS ledger records must embed the normalized execution event")
require(qdas_ledger["properties"]["record_digest"].get("pattern") == "^[0-9a-f]{64}$",
        "QDAS ledger records must carry a SHA-256 chain digest")
require(qdas_ledger["properties"]["sequence"].get("maximum") == 100000,
        "QDAS ledger record count must be bounded")
require(set(qdas_ledger["$defs"]["classification"]["properties"]["category"].get("enum", [])) == {
    "BUILD_FAILURE", "TEST_FAILURE", "STATIC_ANALYSIS_FAILURE", "RUNTIME_FAILURE",
    "INFRASTRUCTURE_FAILURE", "TIMEOUT", "RESOURCE_LIMIT", "ANALYZER_FAILURE",
    "UNSUPPORTED_STATE", "UNKNOWN_FAILURE",
}, "QDAS failure taxonomy mismatch")
require(len(qdas_ledger.get("allOf", [])) == 2,
        "QDAS ledger must enforce event/classification state consistency")

adapter = schemas["adapter-manifest.schema.json"]
alternatives = adapter.get("anyOf", [])
require(any(
    isinstance(item, dict) and set(item.get("required", [])) >= {
        "supported_loaders", "supported_minecraft_versions"
    } for item in alternatives
), "adapter-manifest.schema.json missing Minecraft scope alternative")
require(any(
    isinstance(item, dict) and set(item.get("required", [])) >= {
        "supported_platforms", "supported_versions"
    } for item in alternatives
), "adapter-manifest.schema.json missing generic scope alternative")

knowledge = schemas["migration-knowledge.schema.json"]
require(set(knowledge["properties"]["status"].get("enum", [])) == EXPECTED_KNOWLEDGE_STATES,
        "migration knowledge status vocabulary mismatch")
require(knowledge["$defs"]["identity"]["required"] == list(knowledge["$defs"]["identity"]["properties"]),
        "migration identity schema must explicitly represent every dimension")
require(knowledge["$defs"]["evidence"]["required"] == list(knowledge["$defs"]["evidence"]["properties"]),
        "evidence references must explicitly represent every field")
require(knowledge["$defs"]["evidence"]["properties"]["digest"].get("pattern") == "^sha256:[0-9a-f]{64}$",
        "evidence digest format mismatch")
verified_conditions = [
    item for item in knowledge.get("allOf", [])
    if item.get("if", {}).get("properties", {}).get("status", {}).get("const") == "VERIFIED"
]
require(len(verified_conditions) == 1, "VERIFIED knowledge must have exactly one conditional contract")
verified_then = verified_conditions[0].get("then", {})
require(set(verified_then.get("required", [])) >= {
    "assertion", "verified_by", "verified_at", "valid_until", "evidence",
    "verified_with", "verifier_version", "verifier_digest",
}, "VERIFIED knowledge must require reviewer, expiry, evidence, and pinned verifier provenance")
require(verified_then.get("properties", {}).get("evidence", {}).get("minItems") == 1,
        "VERIFIED knowledge must require at least one evidence reference")
require(
    verified_then.get("properties", {}).get("evidence", {}).get("items", {}).get("properties", {}).get("digest", {}).get("type") == "string",
    "VERIFIED evidence must require a content digest",
)
require(knowledge["properties"]["verifier_digest"].get("pattern") == "^sha256:[0-9a-f]{64}$",
        "verifier digest format mismatch")

transition = schemas["migration-transition.schema.json"]
require(set(transition["properties"]["kind"].get("enum", [])) == EXPECTED_TRANSITION_KINDS,
        "migration transition kind vocabulary mismatch")
require(transition["properties"]["required_capabilities"].get("uniqueItems") is True,
        "transition capability declarations must be unique")
require(transition["properties"]["worker_version"].get("type") == ["string", "null"],
        "worker version must be explicitly nullable but required in transition data")
require(len(transition.get("allOf", [])) == 2,
        "transition worker ID and version must be cross-validated")
require(all(
    condition.get("then", {}).get("properties", {}).get("worker_version") is not None
    for condition in transition["allOf"]
), "transition worker ID/version conditional contracts are incomplete")

worker_manifest = schemas["migration-worker-manifest.schema.json"]
require(worker_manifest["properties"]["permissions"]["uniqueItems"] is True,
        "worker permissions must be unique")
require(set(worker_manifest["properties"]["permissions"]["items"].get("enum", [])) ==
        EXPECTED_WORKER_PERMISSIONS, "worker permission vocabulary mismatch")
require(worker_manifest["properties"]["manifest_digest"].get("pattern") == "^[0-9a-f]{64}$",
        "worker manifest digest format mismatch")
require(worker_manifest["properties"]["implementation_digest"].get("pattern") ==
        "^sha256:[0-9a-f]{64}$", "worker implementation digest format mismatch")
require(worker_manifest["properties"]["protocol_version"].get("const") == 1,
        "unsupported worker manifest protocol contract")

worker_assessment = schemas["migration-worker-assessment.schema.json"]
require(set(worker_assessment["properties"]["status"].get("enum", [])) ==
        {"ROUTE_NOT_PLANNED", "NO_WORK_REQUIRED", "UNKNOWN", "BLOCKED", "QUALIFIED"},
        "worker assessment status vocabulary mismatch")
require(worker_assessment["properties"]["route_plan_digest"].get("pattern") == "^[0-9a-f]{64}$",
        "worker assessment route digest format mismatch")
require(worker_assessment["properties"]["evaluations"].get("items", {}).get("required") ==
        ["transition", "resolution"],
        "worker assessment entries must bind transitions to their worker resolutions")
resolution_schema = worker_assessment.get("$defs", {}).get("workerResolution", {})
require(len(resolution_schema.get("allOf", [])) == 7,
        "worker resolution must define all seven lifecycle status contracts")
resolution_rules = {
    item.get("if", {}).get("properties", {}).get("status", {}).get("const"): item.get("then", {})
    for item in resolution_schema.get("allOf", [])
}
for status in ("NOT_SELECTED", "NOT_REGISTERED", "BLOCKED", "INCOMPATIBLE", "UNQUALIFIED", "STALE", "QUALIFIED"):
    require(status in resolution_rules, f"worker resolution is missing {status} conditional validation")
for status in ("STALE", "QUALIFIED"):
    required = set(resolution_rules.get(status, {}).get("required", []))
    require(required >= {"worker_id", "worker_version", "manifest_digest", "qualification_id", "qualification_digest"},
            f"{status} worker resolution must bind full worker qualification provenance")
blocked_worker_identity = resolution_rules.get("BLOCKED", {}).get("oneOf", [])
require(len(blocked_worker_identity) == 2,
        "BLOCKED worker resolutions must have either no pinned identity or a complete ID/version pair")
assessment_rules = {
    item.get("if", {}).get("properties", {}).get("status", {}).get("const"): item.get("then", {})
    for item in worker_assessment.get("allOf", [])
}
require(len(assessment_rules) == 5, "worker assessment must define all five aggregate result-state contracts")
for status in ("ROUTE_NOT_PLANNED", "NO_WORK_REQUIRED"):
    require(assessment_rules.get(status, {}).get("properties", {}).get("evaluations", {}).get("maxItems") == 0,
            f"{status} assessment must not contain worker evaluations")
require(assessment_rules.get("QUALIFIED", {}).get("properties", {}).get("evaluations", {}).get("minItems") == 1,
        "QUALIFIED assessment must contain at least one evaluation")
unknown_evaluations = assessment_rules.get("UNKNOWN", {}).get("properties", {}).get("evaluations", {})
require(unknown_evaluations.get("minItems") == 1 and "contains" in unknown_evaluations and "not" in unknown_evaluations,
        "UNKNOWN assessment must require missing/stale qualification and exclude blocked/incompatible results")
blocked_evaluations = assessment_rules.get("BLOCKED", {}).get("properties", {}).get("evaluations", {})
require(blocked_evaluations.get("minItems") == 1 and "contains" in blocked_evaluations,
        "BLOCKED assessment must contain a disabled or incompatible worker result")
require(assessment_rules.get("QUALIFIED", {}).get("properties", {}).get("evaluations", {}).get("items", {}).get("properties", {}).get("resolution", {}).get("properties", {}).get("status", {}).get("const") == "QUALIFIED",
        "QUALIFIED aggregate must contain only qualified worker resolutions")

policy_schema = schemas["migration-authorization-policy.schema.json"]
require(policy_schema["properties"]["policy_digest"].get("pattern") == "^[0-9a-f]{64}$",
        "authorization policy must carry a canonical digest")
require(policy_schema["properties"]["allowed_permissions"].get("uniqueItems") is True,
        "authorization policy permissions must be unique")
require(policy_schema["properties"]["allowed_worker_ids"].get("uniqueItems") is True,
        "authorization policy worker allowlist must be unique")
require(policy_schema["properties"]["allowed_permissions"]["items"].get("enum") is not None and
        set(policy_schema["properties"]["allowed_permissions"]["items"]["enum"]) == EXPECTED_WORKER_PERMISSIONS,
        "authorization policy permission vocabulary mismatch")
require(policy_schema["properties"]["allowed_worker_ids"].get("maxItems") == 10000,
        "authorization policy worker allowlist must be bounded")
require(policy_schema["properties"]["max_lifetime_seconds"].get("maximum") == 86400,
        "authorization policy lifetime ceiling mismatch")

workspace = schemas["migration-workspace-descriptor.schema.json"]
require(workspace["properties"]["workspace_id"].get("pattern") == "^[0-9a-f]{32}$",
        "workspace descriptors must carry a canonical unique workspace ID")
require(workspace["properties"]["source_snapshot_digest"].get("pattern") == "^[0-9a-f]{64}$",
        "workspace descriptors must bind a source snapshot digest")
require(workspace["properties"]["descriptor_digest"].get("pattern") == "^[0-9a-f]{64}$",
        "workspace descriptors must carry an integrity digest")
require(workspace["properties"]["file_count"].get("maximum") == 1000000 and
        workspace["properties"]["total_bytes"].get("maximum") == 17179869184,
        "workspace descriptor resource counts must be bounded")
require(workspace["$defs"]["identity"]["required"] == list(workspace["$defs"]["identity"]["properties"]),
        "workspace target identity must explicitly represent every dimension")

snapshot = schemas["migration-project-snapshot.schema.json"]
require(snapshot["properties"]["snapshot_digest"].get("pattern") == "^[0-9a-f]{64}$",
        "project snapshot must carry a SHA-256 content digest")
require(snapshot["properties"]["entries"].get("maxItems") == 1000000,
        "project snapshot entry count must be bounded")
require(snapshot["properties"]["excluded_paths"].get("maxItems") == 10000,
        "project snapshot exclusions must be bounded")
entry_schema = snapshot["$defs"]["entry"]
require(entry_schema.get("additionalProperties") is False,
        "project snapshot entries must reject unknown fields")
require(entry_schema["properties"]["mode"].get("maximum") == 511,
        "project snapshot modes must contain only portable permission bits")
require(len(entry_schema.get("allOf", [])) == 3,
        "project snapshot must define distinct file, directory, and symlink contracts")
require(snapshot["$defs"]["limits"].get("additionalProperties") is False,
        "project snapshot limits must reject unknown fields")

authorization = schemas["migration-authorization.schema.json"]
require(authorization["properties"]["route_plan_digest"].get("pattern") == "^[0-9a-f]{64}$",
        "authorization must bind an exact route plan digest")
require(authorization["properties"]["worker_assessment_digest"].get("pattern") == "^[0-9a-f]{64}$",
        "authorization must bind an exact worker assessment digest")
require(authorization["properties"]["policy_digest"].get("pattern") == "^[0-9a-f]{64}$",
        "authorization must bind the policy digest")
require(authorization["properties"]["authorization_digest"].get("pattern") == "^[0-9a-f]{64}$",
        "authorization document must carry an integrity digest")
require(authorization["properties"]["grants"].get("maxItems") == 10000,
        "authorization grants must be bounded")
require(set(authorization["$defs"]["grant"]["properties"]["permissions"]["items"].get("enum", [])) == EXPECTED_WORKER_PERMISSIONS,
        "authorization grant permission vocabulary mismatch")
require(authorization["$defs"]["grant"]["additionalProperties"] is False,
        "authorization grants must reject undeclared fields")
require(authorization["$defs"]["grant"]["properties"]["permissions"]["uniqueItems"] is True,
        "authorization permissions must be unique")
require(authorization["$defs"]["grant"]["properties"]["manifest_digest"].get("pattern") == "^[0-9a-f]{64}$",
        "authorization grants must pin worker manifest digests")
require(authorization["$defs"]["grant"]["properties"]["qualification_digest"].get("pattern") == "^[0-9a-f]{64}$",
        "authorization grants must pin worker qualification digests")

worker_qualification = schemas["migration-worker-qualification.schema.json"]
require(worker_qualification["properties"]["manifest_digest"].get("pattern") == "^[0-9a-f]{64}$",
        "worker qualification manifest digest format mismatch")
require(worker_qualification["properties"]["conformance_suite_digest"].get("pattern") ==
        "^sha256:[0-9a-f]{64}$", "worker conformance suite digest format mismatch")
require(worker_qualification["properties"]["result_digest"].get("pattern") ==
        "^sha256:[0-9a-f]{64}$", "worker conformance result digest format mismatch")
require(worker_qualification["properties"]["result_status"].get("const") == "PASS",
        "only passing conformance records may qualify a worker")

assurance = schemas["migration-assurance-record.schema.json"]
require(set(assurance["properties"]["worker_status"].get("enum", [])) ==
        {"WORKED", "NO_CHANGE", "BLOCKED", "FAILED"},
        "assurance worker status vocabulary mismatch")
require(assurance["properties"]["plan_digest"].get("pattern") == "^[0-9a-f]{64}$",
        "assurance plan digest format mismatch")
require(assurance["properties"]["record_digest"].get("pattern") == "^[0-9a-f]{64}$",
        "assurance record digest format mismatch")
pass_conditions = [
    item for item in assurance.get("allOf", [])
    if item.get("if", {}).get("properties", {}).get("verdict", {}).get("const") == "PASS"
]
require(len(pass_conditions) == 1, "PASS assurance records must have exactly one conditional contract")
pass_then = pass_conditions[0].get("then", {})
require(set(pass_then.get("required", [])) >= {
    "changed_files", "diff_digest", "post_state_digest", "evidence_ids", "commit_id"
}, "PASS assurance records must require independent evidence and commit references")
require(pass_then.get("properties", {}).get("changed_files", {}).get("minItems") == 1,
        "PASS assurance records must include at least one changed file")
require(pass_then.get("properties", {}).get("evidence_ids", {}).get("minItems") == 1,
        "PASS assurance records must include at least one evidence reference")
require(pass_then.get("properties", {}).get("commit_id", {}).get("pattern") ==
        "^(?:[0-9a-f]{40}|[0-9a-f]{64})$",
        "PASS assurance records must reference a valid Git object identifier")
require(set(pass_then.get("required", [])) >= {
    "worker_manifest_digest", "worker_qualification_id", "worker_qualification_digest"
}, "PASS assurance records must bind the exact qualified worker manifest")
require(pass_then.get("properties", {}).get("worker_status", {}).get("const") == "WORKED",
        "PASS assurance records must require a WORKED worker result")
require(pass_then.get("properties", {}).get("worker_manifest_digest", {}).get("pattern") ==
        "^[0-9a-f]{64}$", "PASS assurance manifest digest format mismatch")
require(pass_then.get("properties", {}).get("worker_qualification_digest", {}).get("pattern") ==
        "^[0-9a-f]{64}$", "PASS assurance qualification digest format mismatch")

route_fixture = ROOT / "benchmarks" / "semantic-migration" / "ROUTES.json"
try:
    fixture = json.loads(route_fixture.read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    raise SystemExit(f"migration benchmark contract failed: cannot read route fixtures: {exc}") from exc
require(fixture.get("schema") == 1 and isinstance(fixture.get("cases"), list),
        "semantic migration route fixtures must use schema version 1")
require(len(fixture["cases"]) == len(EXPECTED_TRANSITION_KINDS),
        "semantic migration fixture must contain one scenario per transition kind")
require({item.get("kind") for item in fixture["cases"]} == EXPECTED_TRANSITION_KINDS,
        "semantic migration fixture must cover every transition kind")
require(all(item.get("expected_route_status") == "PLANNED" for item in fixture["cases"]),
        "synthetic route scenarios must declare their expected planner status")
require(all("worker_id" not in item and "worker_version" not in item for item in fixture["cases"]),
        "synthetic fixtures must not imply a qualified executable worker")

print(f"JSON schemas: PASS ({len(schemas)} structural contracts and migration invariants)")
print(f"Migration benchmark fixtures: PASS ({len(fixture['cases'])} typed transition scenarios)")
