# Lane Collection Summary Runner Handoff

- Not implemented: WorkflowEngine wiring to schedule `run_lane_collection_summary`.
- Not implemented: CLI/entrypoint exposure for the new runner.
- Next Spark tasks: add explicit integration smoke test that exercises default path resolution.
- Next Spark tasks: add one lightweight test asserting `status='write_failed'` only on write errors.
