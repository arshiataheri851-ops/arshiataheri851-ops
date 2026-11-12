"""Production HTTP webhook transport with explicit host allowlisting."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx


class HttpxWebhookSender:
    """Synchronous HTTP sender restricted to operator-approved public hostnames.

    Redirects and environment proxy inheritance are disabled. A host allowlist is
    mandatory to reduce SSRF exposure; deployments should also enforce egress
    restrictions at the network layer.
    """

    def __init__(
        self,
        allowed_hosts: set[str],
        timeout_seconds: float = 8.0,
    ) -> None:
        self.allowed_hosts = {host.strip().lower().rstrip(".") for host in allowed_hosts if host.strip()}
        if not self.allowed_hosts:
            raise ValueError("At least one allowed webhook hostname is required")
        self.client = httpx.Client(
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
            trust_env=False,
            verify=True,
        )

    def _validate_destination(self, url: str) -> None:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme != "https" or not host or parsed.username or parsed.password:
            raise ValueError("Webhook destination must be an absolute HTTPS URL")
        if host not in self.allowed_hosts:
            raise ValueError("Webhook destination hostname is not allowlisted")
        try:
            addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)}
        except OSError as exc:
            raise ValueError("Webhook destination DNS lookup failed") from exc
        if not addresses:
            raise ValueError("Webhook destination has no resolved addresses")
        for address in addresses:
            ip = ipaddress.ip_address(address)
            if not ip.is_global:
                raise ValueError("Webhook destination resolves to a non-public IP address")

    def __call__(self, url: str, body: str, headers: dict[str, str]) -> int:
        self._validate_destination(url)
        response = self.client.post(url, content=body.encode("utf-8"), headers=headers)
        return response.status_code

    def close(self) -> None:
        self.client.close()
