---
name: claude-isolation
description: Audit and configure fixed-proxy, fail-closed networking for official Claude websites, Desktop and Claude Code on macOS or Windows, with scoped rules, backups, failure tests and rollback. Use for proxy-exit/direct-egress prevention; preserve separate third-party API relay settings. Optional iKuai domain guard is supplementary.
---

# Claude Isolation

Configure predictable egress and stop protected clients connecting when their chosen proxy fails. This is network privacy and availability control, not an account-safety or region-eligibility guarantee. Respect service terms and organizational policy.

## Start with evidence

1. Identify OS, actual client paths/signatures, browser, proxy client/core, listening HTTP/mixed port, selected outbound and any relay. Read configuration with secrets redacted. Do not collect chats, cookies, tokens or passwords.
2. Distinguish official web/Desktop/CLI OAuth from third-party API relay traffic. Do not edit CC Switch providers or authentication. A common process/domain cannot be separated by OAuth versus API using network rules; use separate clients/runtimes if required.
3. Report current coverage and gaps before changes. Ask only for unresolved choices that affect scope: protected clients/sites, fixed node, normal-traffic behavior and permitted network interruption. Discover ports; never assume the example port is correct.
4. Read [references/verification.md](references/verification.md) and [references/proxy-clients.md](references/proxy-clients.md), then the relevant platform reference: [macOS](references/macos.md) or [Windows](references/windows.md). Read [iKuai](references/ikuai.md) only if router changes are requested.

## Configure the smallest applicable layers

- **Websites:** Mandatory Chrome PAC; protected exact/suffix domains return one local proxy without `DIRECT`. Keep other sites' behavior explicit. Add per-site WebRTC policy. This only covers managed Chrome, not all browsers/apps or every DNS/UDP packet.
- **Desktop / standalone CLI:** Configure the actual client to use that local proxy; add OS-level process egress protection. Environment variables, system proxy and TUN alone are not a persistent kill switch. Refuse shared-runtime blanket blocks.
- **Proxy core / relay:** Route protected domains to one explicit outbound. No direct fallback, automatic switching, load balancing or emergency node. A local port does not identify the remote node; verify the active core route and relay's onward path. Do not change relay servers without scope/credentials.
- **Router (optional):** Add a source-scoped domain guard while leaving the encrypted proxy endpoint reachable. Do not label a domain blacklist a complete kill switch.

Use `python scripts/generate.py --config <local.json> --out <new-directory>` to generate PAC, policy, removable macOS profile and optional router plan. Read [references/generator.md](references/generator.md) first. It never applies settings. Review the generated plan with the user; authorization for setup covers scoped reversible application, not unrelated global changes or unapproved fault tests.

Before applying, back up the exact relevant policies/rules and record their effective source. Stop on an enterprise policy conflict, unknown adapter version, ambiguous application identity, unavailable rollback or a change that risks the only remote-management path. Do not disable TLS verification, modify signed app bundles, bypass application security controls, or install interception certificates.

## Verify and hand off

Follow the verification reference, including independent **node failure** and **proxy application exit** tests only when the interruption is authorized. Keep a recovery channel that does not depend on the tested proxy; restore changes in `finally` or equivalent. Do not force-quit an app with unsaved work.

Report per client: generated → applied → effective policy observed → normal egress observed → fault tests passed. Mark unrun stages pending. HTTP 403 does not prove a successful login; an IP-check page does not prove every client uses that route. Include narrow rollback commands and recheck after app/proxy upgrades, network changes and router bypass.

## Release hygiene

Use examples with synthetic addresses only. Never ship generated customer profiles, real exports, receipts, logs, credentials or subscription URLs. Share the skill folder, not a live machine's configuration. See README for installation, support status and offline tests.
