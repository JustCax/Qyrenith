# semantic-migration

A domain-neutral fixture catalog for the typed migration route planner.

`ROUTES.json` contains one synthetic scenario for each atomic transition kind: version upgrade, loader conversion, framework change, platform migration, toolchain change, dependency migration, and project profile change.

These scenarios exercise identity dimensionality, exact source/target scope, evidence qualification, and deterministic route planning. They deliberately do not include worker identities or executable transformations. The fixture makes no claim that a real Minecraft, Python, Node, Unity, or other project can be converted by Qyrenith.

The benchmark is executed by `tests/test_migration_benchmarks_120.py`. All facts are synthetic test inputs, not production compatibility knowledge.
