## not implemented
- `modules/source_intake/source_intake_brief.py` and `tests/test_source_intake_brief.py` added.
- No `commerce_detail` keys are emitted in brief markdown.
- Missing bundle now returns `status: input_missing` in `run_source_intake_brief(...)` and writes nothing.

## tests
- `py -m unittest tests.test_source_intake_brief -v`
- `py -m compileall modules/source_intake`

## next light Spark tasks only
- Hook brief generation into the Spark handoff run flow only after status bundle is written.
- Add optional ordering normalization in brief output for `top_queue_sources` if upstream changes queue shape.
