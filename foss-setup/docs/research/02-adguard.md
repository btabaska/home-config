# AdGuard/DNS audit (agent complete)
- Both instances: ONLY stock AdGuard DNS filter (155k rules, auto-updates OK). Rec: add HaGeZi Multi Normal + OISD Big on both (near-zero false positives). Skip Pro++/aggressive.
- No sync between primary/NAS — parity is coincidence. Rec: bakito/adguardhome-sync v0.9.2 container, origin=mini, replica=NAS, dnsServerConfig sync OFF (NAS keeps independent Quad9 DoH upstream = deliberate resilience). Effort M.
- Primary chain textbook: AdGuard→unbound recursive, DNSSEC, qname-min. AGH-side DNSSEC redundant but keep (cheap defense).
- Bug LOW: mini publishes :853 (DoT) but tls.enabled=false — dead listener; remove mapping or enable DoT properly.
- Privacy LOW: 90d query logs on both; rec 7d + optional client-IP anonymize; stats 1d→7d.
- Family features (safesearch/parental/per-service blocks) all off — available when needed, prefer per-client.
Sources: hagezi/dns-blocklists, OISD, bakito/adguardhome-sync.
