"""End-to-end smoke check for a running AtlasRAG instance."""

import argparse
import json
import urllib.request
from uuid import uuid4


def request_json(base_url: str, path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if data is not None else {}
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}", data=data, headers=headers, method="POST" if data else "GET"
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    document_id = f"smoke-{uuid4().hex[:12]}"
    phrase = f"atlasrag-smoke-anchor-{uuid4().hex[:8]}"
    ingest = request_json(args.base_url, "/v1/documents", {
        "document_id": document_id,
        "title": "AtlasRAG Docker smoke test",
        "source": "local://smoke-test",
        "text": f"This local smoke-test document contains the unique reference {phrase}.",
        "metadata": {"purpose": "smoke-test"},
    })
    if ingest.get("document_id") != document_id:
        raise SystemExit("Document ingestion returned an unexpected result.")

    query = request_json(args.base_url, "/v1/query", {
        "question": phrase,
        "top_k": 3,
    })
    if not query.get("grounded") or not any(
        item.get("document_id") == document_id for item in query.get("citations", [])
    ):
        raise SystemExit("Indexed retrieval did not return the ingested document citation.")

    health = request_json(args.base_url, "/health")
    if health.get("status") != "ok":
        raise SystemExit("Health endpoint did not report status=ok.")

    print(json.dumps({
        "status": "passed",
        "document_id": document_id,
        "retrieval_method": query.get("retrieval_method"),
        "citation_count": len(query.get("citations", [])),
        "indexed_documents": health.get("indexed_documents"),
        "indexed_chunks": health.get("indexed_chunks"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
