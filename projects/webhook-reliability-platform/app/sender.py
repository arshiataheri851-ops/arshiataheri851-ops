"""HTTPS webhook transport with DNS-pinned connections and exact host allowlisting."""

from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from urllib.parse import urlsplit


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to a previously validated IP while retaining hostname TLS checks."""

    def __init__(
        self,
        hostname: str,
        port: int,
        address: str,
        timeout_seconds: float,
    ) -> None:
        super().__init__(
            host=hostname,
            port=port,
            timeout=timeout_seconds,
            context=ssl.create_default_context(),
        )
        self._pinned_address = address

    def connect(self) -> None:
        # address is numeric and was validated immediately before this request.
        # TLS SNI and certificate hostname verification still use self.host.
        raw_socket = socket.create_connection(
            (self._pinned_address, self.port),
            timeout=self.timeout,
            source_address=self.source_address,
        )
        self.sock = self._context.wrap_socket(raw_socket, server_hostname=self.host)


class HttpxWebhookSender:
    """Send HTTPS webhooks only to operator-approved public hostnames.

    DNS is resolved once per delivery, every returned address must be public, and
    the TCP connection is pinned to one of those validated numeric addresses.
    This prevents a second DNS lookup by the HTTP client from being redirected
    to a private address (DNS rebinding). TLS SNI and certificate verification
    continue to use the allowlisted hostname.
    """

    def __init__(
        self,
        allowed_hosts: set[str],
        timeout_seconds: float = 8.0,
    ) -> None:
        self.allowed_hosts = {
            host.strip().encode("idna").decode("ascii").lower().rstrip(".")
            for host in allowed_hosts
            if host.strip()
        }
        if not self.allowed_hosts:
            raise ValueError("At least one allowed webhook hostname is required")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.timeout_seconds = timeout_seconds

    def _resolve_public_address(self, hostname: str) -> str:
        try:
            records = socket.getaddrinfo(
                hostname, 443, type=socket.SOCK_STREAM
            )
        except OSError as exc:
            raise ValueError("Webhook destination DNS lookup failed") from exc

        addresses = sorted({record[4][0] for record in records})
        if not addresses:
            raise ValueError("Webhook destination has no resolved addresses")

        parsed_addresses = []
        for address in addresses:
            try:
                parsed = ipaddress.ip_address(address.split("%", 1)[0])
            except ValueError as exc:
                raise ValueError("Webhook destination returned an invalid IP address") from exc
            if not parsed.is_global:
                raise ValueError("Webhook destination resolves to a non-public IP address")
            parsed_addresses.append((str(parsed), address))

        # Every DNS answer is checked before one numeric address is selected.
        return parsed_addresses[0][1]

    def __call__(self, url: str, body: str, headers: dict[str, str]) -> int:
        parsed = urlsplit(url)
        hostname = (parsed.hostname or "").encode("idna").decode("ascii").lower().rstrip(".")
        if (
            parsed.scheme != "https"
            or not hostname
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise ValueError("Webhook destination must be an absolute HTTPS URL")
        try:
            port = parsed.port
        except ValueError as exc:
            raise ValueError("Webhook destination has an invalid port") from exc
        if port not in (None, 443):
            raise ValueError("Webhook destination must use HTTPS port 443")
        try:
            ipaddress.ip_address(hostname)
        except ValueError:
            pass
        else:
            raise ValueError("Webhook destination must use an allowlisted DNS hostname")
        if hostname not in self.allowed_hosts:
            raise ValueError("Webhook destination hostname is not allowlisted")

        pinned_address = self._resolve_public_address(hostname)
        connection = _PinnedHTTPSConnection(
            hostname, 443, pinned_address, self.timeout_seconds
        )
        target = parsed.path or "/"
        if parsed.query:
            target = f"{target}?{parsed.query}"
        request_headers = dict(headers)
        request_headers["Connection"] = "close"
        try:
            connection.request(
                "POST", target, body=body.encode("utf-8"), headers=request_headers
            )
            response = connection.getresponse()
            return response.status
        finally:
            connection.close()

    def close(self) -> None:
        """Compatibility lifecycle hook; each request owns and closes its socket."""
