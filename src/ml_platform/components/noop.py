"""A filesystem-only example component that copies one artifact to another."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from typing import Sequence

from .artifacts import Artifact, download_file, upload_file
from .runtime import ComponentContext, run_component


def copy_one_artifact(context: ComponentContext) -> Path:
    """Copy the single declared input to the single declared output."""

    if len(context.inputs) != 1 or len(context.outputs) != 1:
        raise ValueError("the no-op component requires exactly one input and one output")
    with tempfile.TemporaryDirectory(prefix="ml-platform-component-") as temporary_directory:
        working_copy = download_file(context.inputs[0], Path(temporary_directory) / "input")
        published = upload_file(working_copy, context.outputs[0])
    if context.logger:
        context.logger.info("published output artifact", artifact_name=context.outputs[0].name)
    return published


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-uri", required=True)
    parser.add_argument("--output-uri", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--lineage", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--component-name", default="noop-copy")
    parser.add_argument("--attempt", type=int, default=1)
    arguments = parser.parse_args(argv)
    context = ComponentContext(
        run_id=arguments.run_id,
        component_name=arguments.component_name,
        attempt=arguments.attempt,
        inputs=(Artifact("input", arguments.input_uri),),
        outputs=(Artifact("output", arguments.output_uri),),
        manifest_path=arguments.manifest,
        lineage_path=arguments.lineage,
    )
    run_component(context, copy_one_artifact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
