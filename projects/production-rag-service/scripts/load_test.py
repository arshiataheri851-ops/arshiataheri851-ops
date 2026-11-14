"""Bounded authenticated load test for an AtlasRAG staging endpoint.

This script deliberately requires --allow-target-load and caps concurrency.
Do not point it at production without an approved maintenance/test window.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import json
import os
import statistics
import time
import urllib.error
import urllib.request


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * fraction)))
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("ATLASRAG_BASE_URL"))
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--question", default="What information is available in the indexed documents?")
    parser.add_argument("--allow-target-load", action="store_true")
    args = parser.parse_args()

    api_key = os.getenv("ATLASRAG_API_KEY")
    if not args.allow_target_load:
        parser.error("Pass --allow-target-load to confirm that the target is approved for testing.")
    if not args.base_url or not args.base_url.startswith("https://"):
        parser.error("--base-url must be an HTTPS staging URL.")
    if not api_key or len(api_key) < 32:
        parser.error("Set ATLASRAG_API_KEY to a configured tenant key.")
    if not 1 <= args.requests <= 5000 or not 1 <= args.concurrency <= 50:
        parser.error("Use 1-5000 requests and concurrency 1-50.")
    payload = json.dumps({"question": args.question, "top_k": 5}).encode("utf-8")

    def send_one(_: int) -> tuple[float, int]:
        request = urllib.request.Request(
            f"{args.base_url.rstrip('/')}/v1/query",
            data=payload,
            headers={"Content-Type": "application/json", "X-API-Key": api_key},
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response.read()
                return (time.perf_counter() - started) * 1000, response.status
        except urllib.error.HTTPError as error:
            error.read()
            return (time.perf_counter() - started) * 1000, error.code

    latencies: list[float] = []
    statuses: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(send_one, index) for index in range(args.requests)]
        for future in as_completed(futures):
            latency, status = future.result()
            latencies.append(latency)
            statuses[str(status)] = statuses.get(str(status), 0) + 1

    success = statuses.get("200", 0)
    report = {
        "requests": args.requests,
        "concurrency": args.concurrency,
        "successful": success,
        "error_rate": round(1 - success / args.requests, 4),
        "latency_ms_p50": round(statistics.median(latencies), 2),
        "latency_ms_p95": round(percentile(latencies, 0.95), 2),
        "http_status_counts": statuses,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
