"""Evaluate tenant-scoped retrieval against human-judged JSONL relevance cases."""

import argparse
import json
import os
from pathlib import Path
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("ATLASRAG_BASE_URL"))
    parser.add_argument("--cases", required=True, type=Path)
    args = parser.parse_args()
    api_key = os.getenv("ATLASRAG_API_KEY")
    if not args.base_url or not args.base_url.startswith("https://"):
        parser.error("--base-url must be an HTTPS staging URL.")
    if not api_key or len(api_key) < 32:
        parser.error("Set ATLASRAG_API_KEY to a configured tenant key.")

    cases = []
    for line_number, line in enumerate(args.cases.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item, dict) or not item.get("question") or not item.get("expected_document_id"):
            raise SystemExit(f"Invalid evaluation case at line {line_number}.")
        cases.append({
            "question": item["question"],
            "expected_document_id": item["expected_document_id"],
        })
    if not 1 <= len(cases) <= 200:
        raise SystemExit("Provide 1-200 human-judged cases.")

    payload = json.dumps({"cases": cases, "top_k": 5}).encode("utf-8")
    request = urllib.request.Request(
        f"{args.base_url.rstrip('/')}/v1/evaluate",
        data=payload,
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        metrics = json.load(response)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
