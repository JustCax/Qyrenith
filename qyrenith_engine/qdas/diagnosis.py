"""Evidence-linked failure hypotheses; these are not root-cause verdicts."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
import uuid
from typing import Any

from .events import ExecutionEvent, _canonical, classify_failure, digest_output, redact_output

_MAX_STREAM_BYTES = 8 * 1024 * 1024
_MAX_LINES = 200_000
_MAX_HYPOTHESES = 8
_MAX_EXCERPT = 320

_RULES = (
    (
        "DEPENDENCY_OR_IMPORT_PATH_MISSING",
        re.compile(r"\b(ModuleNotFoundError|ImportError|No module named)\b", re.IGNORECASE),
        "The output contains an import or module-resolution failure.",
        "Check the selected interpreter, declared dependency set, and import path before changing source code.",
    ),
    (
        "SOURCE_SYNTAX_INVALID",
        re.compile(r"\b(SyntaxError|syntax error|unexpected token)\b", re.IGNORECASE),
        "The output contains an explicit syntax diagnostic.",
        "Inspect the reported source location and parser/toolchain version; do not infer which edit introduced it.",
    ),
    (
        "ACCESS_PERMISSION_DENIED",
        re.compile(r"\b(PermissionError|Permission denied|Access is denied|operation not permitted)\b", re.IGNORECASE),
        "The output contains an explicit access-denied diagnostic.",
        "Inspect the exact file/process permission boundary and effective user; do not broaden permissions as a first response.",
    ),
    (
        "REQUIRED_FILE_OR_EXECUTABLE_MISSING",
        re.compile(r"\b(FileNotFoundError|No such file or directory|cannot find the path|file not found)\b", re.IGNORECASE),
        "The output reports a missing file, path, or executable.",
        "Confirm the exact path, working directory, artifact generation step, and executable resolution.",
    ),
    (
        "BEHAVIOR_OR_EXPECTATION_MISMATCH",
        re.compile(r"\b(AssertionError|AssertionFailed|assertion failed|expected .{1,80} but (?:was|got))\b", re.IGNORECASE),
        "The output contains an assertion or expected-versus-actual mismatch.",
        "Reproduce the exact test and inspect the behavioral contract; do not weaken the assertion to make the run pass.",
    ),
    (
        "NETWORK_OR_SERVICE_UNAVAILABLE",
        re.compile(r"\b(ConnectionRefusedError|Connection timed out|Could not resolve host|Temporary failure in name resolution|Name or service not known)\b", re.IGNORECASE),
        "The output contains a network, DNS, or service-connection failure.",
        "Separate DNS, routing, remote-service availability, credentials, and local proxy causes before changing networking policy.",
    ),
    (
        "MEMORY_RESOURCE_EXHAUSTION",
        re.compile(r"\b(OutOfMemoryError|MemoryError|out of memory|killed process|cannot allocate memory)\b", re.IGNORECASE),
        "The output contains a memory-exhaustion or process-kill indicator.",
        "Collect resource-limit and process-exit evidence; do not increase limits without measuring the workload.",
    ),
    (
        "SYMBOL_OR_API_MISMATCH",
        re.compile(r"\b(cannot find symbol|unresolved reference|unknown symbol|undefined reference|no member named)\b", re.IGNORECASE),
        "The output contains a symbol or API resolution diagnostic.",
        "Check source imports, generated sources, exact dependency/API versions, and target platform before assuming an API migration is needed.",
    ),
    (
        "VERSION_OR_TOOLCHAIN_INCOMPATIBILITY",
        re.compile(r"\b(unsupported class file major version|requires .* version|incompatible version|unsupported .* version)\b", re.IGNORECASE),
        "The output contains an explicit version or toolchain compatibility diagnostic.",
        "Capture exact runtime, compiler, plugin, and target versions; do not infer a compatibility mapping from the message alone.",
    ),
    (
        "COMPILER_REPORTED_DIAGNOSTIC",
        re.compile(r"(?m)(?:^|\s)(?:error|fatal error):\s+", re.IGNORECASE),
        "The output contains a compiler-style error diagnostic.",
        "Identify the compiler and source location, then reproduce the diagnostic with the pinned toolchain.",
    ),
)


@dataclass(frozen=True)
class FailureObservation:
    observation_id: str
    event_id: str
    stream: str
    line_number: int
    line_digest: str
    excerpt: str

    def __post_init__(self) -> None:
        for field, value in (
            ("observation_id", self.observation_id),
            ("line_digest", self.line_digest),
        ):
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError(f"{field} must be a SHA-256 digest")
        if not isinstance(self.event_id, str) or not re.fullmatch(r"[0-9a-f]{32}", self.event_id):
            raise ValueError("event_id must be a UUID hex value")
        if self.stream not in {"stdout", "stderr"}:
            raise ValueError("stream must be stdout or stderr")
        if type(self.line_number) is not int or not 1 <= self.line_number <= _MAX_LINES:
            raise ValueError("line_number is outside the supported bound")
        if not isinstance(self.excerpt, str) or len(self.excerpt) > _MAX_EXCERPT:
            raise ValueError("excerpt exceeds the supported bound")

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "event_id": self.event_id,
            "stream": self.stream,
            "line_number": self.line_number,
            "line_digest": self.line_digest,
            "excerpt": self.excerpt,
        }


@dataclass(frozen=True)
class FailureHypothesis:
    hypothesis_id: str
    event_id: str
    failure_category: str
    rule_id: str
    statement: str
    supporting_evidence: tuple[FailureObservation, ...]
    contradicting_evidence: tuple[FailureObservation, ...]
    confidence: str
    confidence_rationale: str
    missing_evidence: tuple[str, ...]
    state: str = "UNCONFIRMED"

    def __post_init__(self) -> None:
        if not isinstance(self.hypothesis_id, str) or not re.fullmatch(r"[0-9a-f]{32}", self.hypothesis_id):
            raise ValueError("hypothesis_id must be a UUID hex value")
        if not isinstance(self.event_id, str) or not re.fullmatch(r"[0-9a-f]{32}", self.event_id):
            raise ValueError("event_id must be a UUID hex value")
        for field, value in (
            ("failure_category", self.failure_category),
            ("rule_id", self.rule_id),
            ("statement", self.statement),
            ("confidence_rationale", self.confidence_rationale),
        ):
            if not isinstance(value, str) or not value or len(value) > 2048:
                raise ValueError(f"{field} must be non-empty bounded text")
        if self.confidence not in {"HIGH", "MEDIUM", "LOW"}:
            raise ValueError("confidence must be HIGH, MEDIUM, or LOW")
        if self.state != "UNCONFIRMED":
            raise ValueError("failure hypotheses must remain UNCONFIRMED")
        if not isinstance(self.supporting_evidence, tuple) or not all(
            isinstance(item, FailureObservation) for item in self.supporting_evidence
        ):
            raise ValueError("supporting_evidence must contain FailureObservation values")
        if not isinstance(self.contradicting_evidence, tuple) or not all(
            isinstance(item, FailureObservation) for item in self.contradicting_evidence
        ):
            raise ValueError("contradicting_evidence must contain FailureObservation values")
        if not isinstance(self.missing_evidence, tuple) or any(
            not isinstance(item, str) or not item or len(item) > 512 for item in self.missing_evidence
        ):
            raise ValueError("missing_evidence must contain bounded non-empty strings")
        if not self.supporting_evidence:
            raise ValueError("a failure hypothesis must cite supporting evidence")

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "event_id": self.event_id,
            "failure_category": self.failure_category,
            "rule_id": self.rule_id,
            "statement": self.statement,
            "supporting_evidence": [item.to_dict() for item in self.supporting_evidence],
            "contradicting_evidence": [item.to_dict() for item in self.contradicting_evidence],
            "confidence": self.confidence,
            "confidence_rationale": self.confidence_rationale,
            "missing_evidence": list(self.missing_evidence),
            "state": self.state,
        }

    @property
    def hypothesis_digest(self) -> str:
        return hashlib.sha256(_canonical(self.to_dict())).hexdigest()


def _observations(event: ExecutionEvent, stream: str, content: str, pattern: re.Pattern[str]) -> tuple[FailureObservation, ...]:
    observations = []
    for number, line in enumerate(content.splitlines(), start=1):
        if number > _MAX_LINES:
            break
        if not pattern.search(line):
            continue
        redacted_line = redact_output(line)
        line_digest = hashlib.sha256(redacted_line.encode("utf-8", "replace")).hexdigest()
        excerpt = redacted_line[:_MAX_EXCERPT]
        observation_payload = {
            "event_id": event.event_id,
            "stream": stream,
            "line_number": number,
            "line_digest": line_digest,
        }
        observation_id = hashlib.sha256(_canonical(observation_payload)).hexdigest()
        observations.append(FailureObservation(
            observation_id, event.event_id, stream, number, line_digest, excerpt
        ))
        if len(observations) >= 8:
            break
    return tuple(observations)


def diagnose_failure(
    event: ExecutionEvent,
    *,
    stdout: str,
    stderr: str,
) -> tuple[FailureHypothesis, ...]:
    """Create deterministic, unconfirmed hypotheses from event-bound redacted output."""
    if not isinstance(event, ExecutionEvent):
        raise TypeError("event must be an ExecutionEvent")
    if not isinstance(stdout, str) or not isinstance(stderr, str):
        raise TypeError("stdout and stderr must be text")
    if len(stdout.encode("utf-8", "replace")) > _MAX_STREAM_BYTES:
        raise ValueError("stdout exceeds the 8 MiB diagnosis input limit")
    if len(stderr.encode("utf-8", "replace")) > _MAX_STREAM_BYTES:
        raise ValueError("stderr exceeds the 8 MiB diagnosis input limit")
    if digest_output(stdout) != event.stdout_digest or digest_output(stderr) != event.stderr_digest:
        raise ValueError("diagnosis output does not match the exact execution event digests")
    if event.execution_status == "PASS":
        return ()
    redacted_streams = {
        "stdout": redact_output(stdout),
        "stderr": redact_output(stderr),
    }
    hypotheses = []
    for index, (rule_id, pattern, statement, next_action) in enumerate(_RULES):
        evidence = (
            _observations(event, "stderr", redacted_streams["stderr"], pattern)
            + _observations(event, "stdout", redacted_streams["stdout"], pattern)
        )
        if not evidence:
            continue
        # These are symptom-level matches. Even an exact exception marker is not proof
        # that the matching condition is the underlying root cause.
        confidence = "MEDIUM" if len(evidence) >= 2 else "LOW"
        rationale = (
            "A native text rule matched one or more redacted output lines. "
            "This supports the observed symptom only; causal attribution requires reproduction and independent evidence."
        )
        identity = hashlib.sha256(_canonical({
            "event_id": event.event_id,
            "rule_id": rule_id,
            "evidence_ids": sorted(item.observation_id for item in evidence),
        })).hexdigest()[:32]
        hypotheses.append(FailureHypothesis(
            hypothesis_id=identity,
            event_id=event.event_id,
            failure_category=classify_failure(event).category,
            rule_id=rule_id,
            statement=statement + " " + next_action,
            supporting_evidence=evidence,
            contradicting_evidence=(),
            confidence=confidence,
            confidence_rationale=rationale,
            missing_evidence=(
                "Independent reproduction of the same failure signature.",
                "A controlled test that distinguishes this hypothesis from alternative causes.",
                "Source, dependency, and environment context relevant to the matched diagnostic.",
            ),
        ))
        if len(hypotheses) >= _MAX_HYPOTHESES:
            break
    if hypotheses:
        return tuple(hypotheses)
    fallback_id = hashlib.sha256(
        (event.event_id + event.stdout_digest + event.stderr_digest).encode("ascii")
    ).hexdigest()[:32]
    fallback_observation = FailureObservation(
        observation_id=hashlib.sha256((fallback_id + ":no-output-rule").encode("ascii")).hexdigest(),
        event_id=event.event_id,
        stream="stderr",
        line_number=1,
        line_digest=event.stderr_digest,
        excerpt="[No native diagnostic pattern matched the bounded output]",
    )
    return (FailureHypothesis(
        hypothesis_id=fallback_id,
        event_id=event.event_id,
        failure_category=classify_failure(event).category,
        rule_id="QDAS-ROOT-UNKNOWN-001",
        statement="The native diagnostic rules did not recognize the available failure output.",
        supporting_evidence=(fallback_observation,),
        contradicting_evidence=(),
        confidence="LOW",
        confidence_rationale="No specific diagnostic signature matched; this is an explicit unknown, not a pass.",
        missing_evidence=(
            "Full untruncated diagnostic output, if policy permits retention.",
            "Tool-specific structured diagnostics or a reproducer.",
            "Independent inspection of the failing project state.",
        ),
    ),)


__all__ = ["FailureHypothesis", "FailureObservation", "diagnose_failure"]
