"""Authenticated end-to-end smoke check for a running AtlasRAG instance."""

import argparse
import json
import os
import urllib.request
from uuid import uuid4


def request_json(base_url: str, path: str, api_key: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"X-API-Key": api_key}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}", data=data, headers=headers,
        method="POST" if data else "GET",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8002")
    parser.add_argument("--api-key", default=os.getenv("ATLASRAG_API_KEY"))
    args = parser.parse_args()
    if not args.api_key or len(args.api_key) < 32:
        raise SystemExit("Provide a configured tenant API key (minimum 32 characters) via --api-key or ATLASRAG_API_KEY.")

    document_id = f"smoke-{uuid4().hex[:12]}"
    phrase = f"atlasrag-smoke-anchor-{uuid4().hex[:8]}"
    ingest = request_json(args.base_url, "/v1/documents", args.api_key, {
        "document_id": document_id,
        "title": "AtlasRAG authenticated smoke test",
        "source": "local://smoke-test",
        "text": f"This local smoke-test document contains the unique reference {phrase}.",
        "metadata": {"purpose": "smoke-test"},
    })
    if ingest.get("document_id") != document_id:
        raise SystemExit("Document ingestion returned an unexpected result.")

    query = request_json(args.base_url, "/v1/query", args.api_key, {
        "question": phrase,
        "top_k": 3,
    })
    if not query.get("grounded") or not any(
        item.get("document_id") == document_id for item in query.get("citations", [])
    ):
        raise SystemExit("Tenant-scoped retrieval did not return the ingested document citation.")

    listing = request_json(args.base_url, "/v1/documents", args.api_key)
    if not any(item.get("document_id") == document_id for item in listing):
        raise SystemExit("Tenant-scoped document listing did not return the ingested document.")

    health = request_json(args.base_url, "/health", args.api_key)
    if health.get("status") != "ok":
        raise SystemExit("Health endpoint did not report status=ok.")

    print(json.dumps({
        "status": "passed",
        "document_id": document_id,
        "retrieval_method": query.get("retrieval_method"),
        "citation_count": len(query.get("citations", [])),
        "tenant_scoped_listing": True,
        "health": health["status"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
