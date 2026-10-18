# Safety Model

## Non-negotiable invariants

`AUDIT_BEFORE_PATCH`

`BACKUP_BEFORE_PATCH`

`ONE_VERSION_STEP_AT_A_TIME`

`NO_GUESSING`

`MINIMAL_PATCH`

`BUILD_AFTER_PATCH`

`SUCCESS_REQUIRES_JAR`

`MAX_5_FIX_ITERATIONS`

`VALIDATE_BEFORE_COMMIT`

`COMMIT_BEFORE_NEXT_STEP`

`HONEST_FINAL_REPORT`

## Agent trust boundary

The agent is an untrusted executor of a bounded task. Agent text is not evidence of success. Only observed filesystem state, build results, validation, and Git state can advance the workflow.

## User-change protection

Dirty Git state blocks managed modification. Rollback also requires a clean tree. Qyrenith never silently resets, cleans, or discards user work.

## Archive safety

Backups reject absolute paths, drive-letter paths, traversal segments, NUL bytes, and case-colliding members.

## Recovery

State writes are atomic. A durable event stream records transitions. A lock prevents overlapping runs. Resume verifies the plan hash and active step identity.
