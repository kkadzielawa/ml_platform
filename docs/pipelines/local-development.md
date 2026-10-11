# Local pipeline development

The local runner executes the same component entrypoint commands and artifact
contracts used by a pipeline, in a declared sequence. It does not create a
second pipeline DSL and it does not emulate Kubernetes scheduling.

Each invocation supplies:

- the existing component command, usually `python -m <component-module>`;
- named output paths that the component contract promises to publish; and
- optional environment, working-directory, and timeout settings.

The runner starts one component at a time. A zero exit status is not enough to
complete a step: every declared output must also exist. Successful outputs are
copied to `<run-root>/captured-artifacts/<component>/<artifact>` and recorded
with a SHA-256 digest, byte count, and source path. The run summary is written
to `<run-root>/run-summary.json`.

For example, the filesystem-only SDK component can be run with the same
contract locally:

```python
from pathlib import Path

from ml_platform.local_runner import LocalPipelineRunner, python_module_invocation

root = Path("build/local-runs/example")
source = Path("examples/input.txt").resolve()
output = (root / "artifacts/output.txt").resolve()

step = python_module_invocation(
    "copy-fixture",
    "ml_platform.components.noop",
    (
        "--input-uri", source.as_uri(),
        "--output-uri", output.as_uri(),
        "--manifest", str(root / "evidence/manifest.json"),
        "--lineage", str(root / "evidence/lineage.jsonl"),
        "--run-id", "run-20261011t120000z-00000001",
    ),
    output_paths={"output": output},
    environment={"PYTHONPATH": "src"},
)

result = LocalPipelineRunner(root).run([step])
assert result.succeeded
```

The sequence is the only ordering mechanism. If a component exits non-zero,
times out, cannot start, or omits a declared artifact, `LocalPipelineError`
contains the failed component and its captured evidence. The runner writes the
failed summary, marks later invocations as skipped, and does not start them.
This makes quality-gate and model-regression failures visible without hiding
the component's exit status.

Run the integration checks with:

```bash
make test-local-pipeline
```

The runner is intended for fixture-based development and contract checks. It
does not replace the orchestrator, provide distributed execution, or mutate
durable inputs during cleanup.
