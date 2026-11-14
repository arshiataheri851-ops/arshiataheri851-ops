# RelayForge outbound network policy — deployment checklist

RelayForge validates webhook URLs, allowlists exact hostnames, resolves A/AAAA
records, rejects private/mixed answers, and pins the TCP connection to the
validated numeric address while retaining TLS SNI and hostname verification.
That is application-layer protection; it is not a substitute for an egress
boundary.

## Required host/network policy

1. Keep the RelayForge container on a private application network. Do not attach
   it to a public ingress network.
2. Deny outbound traffic by default at the host/cloud firewall or container
   network policy.
3. Permit DNS only to the explicitly selected recursive resolver(s).
4. Permit outbound TCP 443 only to the currently approved destination IP
   addresses for the exact hostnames in `RELAYFORGE_ALLOWED_HOSTS`.
5. Do not permit container egress to RFC1918, loopback, link-local, multicast,
   IPv6 unique-local, IPv6 link-local, cloud metadata, or internal service
   networks. Preserve the application's own address validation as a second
   independent control.
6. Prefer a cloud firewall or CNI with FQDN-aware egress policy. If using IP
   sets, automate refresh from the approved hostname list, validate every A
   and AAAA answer, apply updates atomically, and alert when an approved host
   changes address. Never accept arbitrary tenant-supplied hostnames.
7. Keep PostgreSQL reachable only from the AtlasRAG service; never publish its
   port to the host or internet.
8. Test both allowed delivery and blocked private/metadata destinations from
   the deployed network before enabling the worker.

The exact implementation depends on the hosting provider, firewall/CNI, DNS
resolver, and approved webhook destinations. Do not enable
`RELAYFORGE_ENABLE_WORKER=true` until the effective egress policy has been
verified from inside the running container.
