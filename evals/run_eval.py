"""Unified Evaluation Harness CLI for InsurAI benchmark suites."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add project root and backend to sys.path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "backend"))

from evals.run_extraction_eval import run_evaluation as run_extraction_eval  # noqa: E402
from evals.run_retrieval_eval import run_retrieval_evaluation  # noqa: E402


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run InsurAI Evaluation Benchmarks.")
    parser.add_argument(
        "--split", choices=["dev", "test", "smoke"], default="dev", help="Dataset split to evaluate"
    )
    parser.add_argument("--provider", default="fake", help="LLM Provider (fake | gemini)")
    args = parser.parse_args()

    print("\n=======================================================")
    print("  InsurAI Unified Evaluation Suite")
    print(f"  Split: {args.split} | Provider: {args.provider}")
    print("=======================================================\n")

    # 1. Extraction Evaluation
    extraction_results = await run_extraction_eval(args.split)

    # 2. Retrieval Evaluation
    retrieval_results = run_retrieval_evaluation()

    combined_results = {
        "split": args.split,
        "provider": args.provider,
        "extraction_metrics": extraction_results,
        "retrieval_metrics": retrieval_results,
    }

    out_json = repo_root / "evals" / "reports" / f"unified_eval_{args.split}.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(combined_results, f, indent=2)

    print(f"\n[SUCCESS] Unified evaluation complete. Results written to: {out_json}\n")


if __name__ == "__main__":
    asyncio.run(main())
