from __future__ import annotations

import argparse
from pathlib import Path

from ml_platform.ingestion import run_baseline_ingestion
from ml_platform.ingestion.lakefs_client import lakefs_port_forward
from ml_platform.lineage import InMemoryLineageCollector


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the baseline housing-sale dataset into lakeFS.")
    parser.add_argument("--repository", default="housing-sale-ingestion")
    parser.add_argument("--storage-namespace")
    parser.add_argument("--train", type=Path)
    parser.add_argument("--test", type=Path)
    parser.add_argument("--manifest", type=Path, default=Path("/tmp/ml-platform-baseline-ingestion/run-manifest.json"))
    parser.add_argument("--lineage-events", type=Path, default=Path("/tmp/ml-platform-baseline-ingestion/openlineage-events.jsonl"))
    args = parser.parse_args()

    input_paths = None
    if args.train or args.test:
        if not args.train or not args.test:
            parser.error("--train and --test must be provided together")
        input_paths = {"train": args.train, "test": args.test}

    collector = InMemoryLineageCollector()
    with lakefs_port_forward():
        result = run_baseline_ingestion(
            input_paths=input_paths,
            repository=args.repository,
            storage_namespace=args.storage_namespace,
            output_manifest_path=args.manifest,
            lineage_collector=collector,
        )
    collector.write_jsonl(args.lineage_events)
    status = "no-op" if result.no_op else "committed"
    print(f"baseline ingestion {status}")
    print(f"repository={result.repository}")
    print(f"branch={result.branch}")
    print(f"lakefs_commit_id={result.lakefs_commit_id}")
    print(f"manifest={result.manifest_path}")
    print(f"lineage_events={args.lineage_events}")


if __name__ == "__main__":
    main()
