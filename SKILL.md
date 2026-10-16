---
name: claude-isolation
description: Audit and configure fixed-proxy, fail-closed networking for official Claude websites, Desktop and Claude Code on macOS or Windows. The standard setup includes rule-based TUN and Singapore system time zone, scoped guards, backups, failure tests and rollback. Preserve separate third-party API relay settings; optional iKuai domain guard is supplementary.
---

# Claude Isolation

Configure predictable egress and stop protected clients connecting when their chosen proxy fails. This is network privacy and availability control, not an account-safety or region-eligibility guarantee. Respect service terms and organizational policy.

## Start with evidence

1. Identify OS, actual client paths/signatures, browser, proxy client/core, listening HTTP/mixed port, selected outbound and any relay. Read configuration with secrets redacted. Do not collect chats, cookies, tokens or passwords.
2. Distinguish official web/Desktop/CLI OAuth from third-party API relay traffic. Do not edit CC Switch providers or authentication. A common process/domain cannot be separated by OAuth versus API using network rules; use separate clients/runtimes if required.
3. Report current coverage and gaps before changes. Disclose that the standard setup enables rule-based TUN and changes the whole system time zone to Singapore. Confirm authority for these system-wide changes if not already given. Ask only for unresolved choices that affect scope: protected clients/sites, fixed node, normal-traffic behavior and permitted network interruption. Discover ports; never assume the example port is correct.
4. Read [references/verification.md](references/verification.md), [references/proxy-clients.md](references/proxy-clients.md) and [references/tun-timezone.md](references/tun-timezone.md), then the relevant platform reference: [macOS](references/macos.md) or [Windows](references/windows.md). Read [iKuai](references/ikuai.md) only if router changes are requested.

## Configure the smallest applicable layers

- **Standard setup prerequisites:** Enable and verify rule-based TUN in the actual running proxy instance; set the system time zone to `Asia/Singapore` (`Singapore Standard Time` on Windows, UTC+08:00). Back up original TUN/routes and time-zone/automatic-zone settings. TUN must preserve explicit domestic/API/LAN rules and the recovery channel. Do not claim standard setup completion if either prerequisite is unsupported, refused or unverified; report the gap. These are this skill's deployment defaults, not universal Claude requirements. Time zone does not change egress IP or provide account-safety assurance.
- **Websites:** Mandatory Chrome PAC; protected exact/suffix domains return one local proxy without `DIRECT`. Keep other sites' behavior explicit. Add per-site WebRTC policy. This only covers managed Chrome, not all browsers/apps or every DNS/UDP packet.
- **Desktop / standalone CLI:** Configure the actual client to use that local proxy; add OS-level process egress protection. Environment variables, system proxy and TUN alone are not a persistent kill switch. Refuse shared-runtime blanket blocks.
- **Proxy core / relay:** Route protected domains to one explicit outbound. No direct fallback, automatic switching, load balancing or emergency node. A local port does not identify the remote node; verify the active core route and relay's onward path. Do not change relay servers without scope/credentials.
- **Router (optional):** Add a source-scoped domain guard while leaving the encrypted proxy endpoint reachable. Do not label a domain blacklist a complete kill switch.

Use `python scripts/generate.py --config <local.json> --out <new-directory>` to generate PAC, policy, removable macOS profile, TUN/time-zone requirements and optional router plan. Read [references/generator.md](references/generator.md) first. It never applies settings. Review the generated plan with the user; authorization for setup covers scoped reversible application, not unrelated global changes or unapproved fault tests.

Before applying, back up the exact relevant policies/rules and record their effective source. Stop on an enterprise policy conflict, unknown adapter version, ambiguous application identity, unavailable rollback or a change that risks the only remote-management path. Do not disable TLS verification, modify signed app bundles, bypass application security controls, or install interception certificates.

## Verify and hand off

Follow the verification reference, including independent **node failure** and **proxy application exit** tests only when the interruption is authorized. Keep a recovery channel that does not depend on the tested proxy; restore changes in `finally` or equivalent. Do not force-quit an app with unsaved work.

Report per client: generated → applied → effective policy observed → normal egress observed → fault tests passed. Separately report TUN enabled/effective routes and Singapore system/browser time-zone checks. Mark unrun stages pending. HTTP 403 does not prove a successful login; an IP-check page does not prove every client uses that route. Include narrow rollback commands and recheck after app/proxy upgrades, network changes and router bypass.

## Release hygiene

Use examples with synthetic addresses only. Never ship generated customer profiles, real exports, receipts, logs, credentials or subscription URLs. Share the skill folder, not a live machine's configuration. See README for installation, support status and offline tests.
