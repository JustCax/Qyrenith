# Exit Codes

| Code | Meaning |
|---:|---|
| 0 | SUCCESS |
| 1 | FAILED / generic failure |
| 2 | BLOCKED |
| 3 | STOPPED |
| 10 | PREFLIGHT_FAILURE |
| 11 | AUDIT_BLOCKER |
| 12 | UNKNOWN_API |
| 13 | DEPENDENCY_BLOCKER |
| 14 | PORTING_FAILURE |
| 15 | BUILD_FAILURE |
| 16 | VALIDATION_FAILURE |
| 17 | FIX_LIMIT_REACHED |
| 18 | UNTRUSTED_BUILD |
| 20 | USAGE |
| 70 | INTERNAL_ERROR |

Exit codes are intended for agents and automation. Do not parse human-readable text when a stable code is available.
