#!/usr/bin/env python3
"""Offline artifacts only. Python 3.10+; no network or third-party dependencies."""
import argparse
import base64
from functools import lru_cache
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import plistlib
import re
import uuid

PROVIDERS = {
    "claude": ["claude.ai", "claude.com", "anthropic.com", "claudeusercontent.com"],
    "openai": ["openai.com", "chatgpt.com", "oaistatic.com", "oaiusercontent.com"],
    "gemini": ["gemini.google.com", "aistudio.google.com",
               "generativelanguage.googleapis.com", "cloudcode-pa.googleapis.com"],
}
KEYS = {"proxy_host", "proxy_port", "providers", "extra_domains", "unprotected",
        "profile_identifier", "router_sources"}
SHARED_ROOTS = {"google.com", "googleapis.com", "cloudflare.com", "googleusercontent.com"}


@lru_cache(maxsize=1)
def suffix_rules():
    exact, wildcard, exceptions = set(), set(), set()
    source = Path(__file__).resolve().parents[1] / "assets" / "public_suffix_list.dat"
    for raw in source.read_text(encoding="utf-8").splitlines():
        rule = raw.split("//", 1)[0].strip().lower()
        if not rule:
            continue
        target = exceptions if rule.startswith("!") else wildcard if rule.startswith("*.") else exact
        clean = rule[1:] if rule.startswith("!") else rule[2:] if rule.startswith("*.") else rule
        target.add(clean.encode("idna").decode("ascii"))
    if "com" not in exact or "co.uk" not in exact or not wildcard or not exceptions:
        raise ValueError("Public Suffix List is missing or invalid; do not bypass scope validation")
    return exact, wildcard, exceptions


def string_list(value, name):
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise ValueError(f"{name} must be a list of strings")
    return value


def domain(value, curated_provider=False):
    value = value.lower().rstrip(".")
    if len(value) > 253 or "." not in value:
        raise ValueError("Use a fully qualified domain without URL, wildcard or port")
    if not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", p)
               for p in value.split(".")):
        raise ValueError("Domain must be ASCII; convert IDNs to punycode first")
    try:
        ipaddress.ip_address(value)
    except ValueError:
        exact, wildcard, exceptions = suffix_rules()
        if value in SHARED_ROOTS or (not curated_provider and value not in exceptions and
                (value in exact or value.partition(".")[2] in wildcard)):
            raise ValueError("Public suffix or broad shared-provider root refused; choose specific hosts")
        return value
    raise ValueError("Protected targets must be domain names, not IP literals")


def validate(config):
    if not isinstance(config, dict) or set(config) - KEYS:
        raise ValueError("Unknown configuration keys or non-object configuration")
    host = config.get("proxy_host", "127.0.0.1")
    if host not in ("127.0.0.1", "::1"):
        raise ValueError("Only literal local loopback proxy addresses are supported")
    port = config.get("proxy_port")
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("proxy_port must be an integer from 1 to 65535")
    providers = string_list(config.get("providers", ["claude"]), "providers")
    if not providers or set(providers) - PROVIDERS.keys():
        raise ValueError("providers must select claude, openai and/or gemini")
    extra = string_list(config.get("extra_domains", []), "extra_domains")
    domains = sorted({domain(d, curated_provider=True) for p in providers for d in PROVIDERS[p]} |
                     {domain(d) for d in extra})
    mode = config.get("unprotected", "direct")
    if mode not in ("direct", "proxy-then-direct"):
        raise ValueError("unprotected must be direct or proxy-then-direct")
    identifier = config.get("profile_identifier", "local.claude-isolation.chrome")
    if not isinstance(identifier, str) or not re.fullmatch(
            r"[A-Za-z][A-Za-z0-9-]*(?:\.[A-Za-z0-9-]+)+", identifier):
        raise ValueError("Invalid reverse-DNS profile_identifier")
    sources = string_list(config.get("router_sources", []), "router_sources")
    normalized = []
    for source in sources:
        ip = ipaddress.IPv4Address(source)
        if not any(ip in ipaddress.ip_network(n) for n in
                   ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")):
            raise ValueError("Router sources must be individual RFC1918 IPv4 addresses")
        if (int(ip) & 255) in (0, 255):
            raise ValueError("Review network/broadcast-like addresses manually")
        normalized.append(str(ip))
    return host, port, domains, mode, identifier, sorted(set(normalized))


def make_pac(host, port, domains, mode):
    endpoint = f"[{host}]" if ":" in host else host
    proxy = f"PROXY {endpoint}:{port}"
    normal = "DIRECT" if mode == "direct" else proxy + "; DIRECT"
    return """// Generated by claude-isolation. Protected domains have no fallback.
var protectedDomains = %s;
function localLiteral(host) {
  if (host === '::1' || host === '[::1]') return true;
  var p = host.split('.');
  if (p.length !== 4) return false;
  for (var i = 0; i < 4; i++) {
    if (!/^(0|[1-9][0-9]{0,2})$/.test(p[i]) || Number(p[i]) > 255) return false;
    p[i] = Number(p[i]);
  }
  return p[0] === 127 || p[0] === 10 ||
    (p[0] === 172 && p[1] >= 16 && p[1] <= 31) ||
    (p[0] === 192 && p[1] === 168) ||
    (p[0] === 100 && p[1] >= 64 && p[1] <= 127);
}
function suffix(host, root) {
  return host === root || host.slice(-(root.length + 1)) === '.' + root;
}
function FindProxyForURL(url, host) {
  host = host.toLowerCase().replace(/\\.$/, '');
  for (var i = 0; i < protectedDomains.length; i++) {
    if (suffix(host, protectedDomains[i])) return %s;
  }
  if (host === 'localhost' || suffix(host, 'local') || suffix(host, 'ts.net') ||
      localLiteral(host)) return 'DIRECT';
  return %s;
}
""" % (json.dumps(domains), json.dumps(proxy), json.dumps(normal))


def make_policy(pac, domains):
    encoded = base64.b64encode(pac.encode()).decode()
    return {
        "ProxySettings": {"ProxyMode": "pac_script", "ProxyPacMandatory": True,
                          "ProxyPacUrl": "data:application/x-ns-proxy-autoconfig;base64," + encoded},
        "WebRtcIPHandlingUrl": [{"url": "https://[*.]" + d,
                                 "handling": "disable_non_proxied_udp"} for d in domains],
    }


def make_profile(policy, identifier):
    def payload(kind, suffix, name):
        return {"PayloadType": kind, "PayloadVersion": 1,
                "PayloadIdentifier": identifier + suffix,
                "PayloadUUID": str(uuid.uuid4()).upper(), "PayloadDisplayName": name}
    inner = payload("com.apple.ManagedClient.preferences", ".preferences", "Chrome policies")
    inner["PayloadContent"] = {"com.google.Chrome": {
        "Forced": [{"mcx_preference_settings": policy}]}}
    outer = payload("Configuration", "", "Claude Isolation - Chrome")
    outer.update({"PayloadScope": "User", "PayloadRemovalDisallowed": False,
                  "PayloadDescription": "Local Chrome website proxy and WebRTC policy. No certificates or enrollment.",
                  "PayloadContent": [inner]})
    return plistlib.dumps(outer, sort_keys=False)


def build(config):
    host, port, domains, mode, identifier, sources = validate(config)
    pac = make_pac(host, port, domains, mode)
    policy = make_policy(pac, domains)
    def dump(obj):
        return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode()
    files = {
        "protected.pac": pac.encode(),
        "chrome-policy.json": dump(policy),
        "chrome.mobileconfig": make_profile(policy, identifier),
        "protected-domains.txt": ("\n".join(domains) + "\n").encode(),
        "setup-requirements.json": dump({
            "status": "required_not_applied_or_verified",
            "tun": {"required": True, "routing_mode": "rule_based",
                    "keep_process_guard": True, "verified": False},
            "system_timezone": {"required": True, "iana_id": "Asia/Singapore",
                                "windows_id": "Singapore Standard Time",
                                "utc_offset": "+08:00", "verified": False},
            "browser_timezone": {"expected_iana_id": "Asia/Singapore", "verified": False},
            "reference": "references/tun-timezone.md",
        }),
    }
    if sources:
        files["ikuai-v4-plan.json"] = dump({
            "status": "plan_only_not_applied", "expected_adapter": "iKuai V4 url_black",
            "request": {"func_name": "url_black", "action": "add", "param": {
                "tagname": "ClaudeGuard", "enabled": "yes", "mode": 0,
                "src_addr": {"custom": sources, "object": []},
                "domain": {"custom": [x for d in domains for x in (d, "*." + d)], "object": []},
                "time": {"custom": [{"type": "weekly", "weekdays": "1234567",
                                     "start_time": "00:00", "end_time": "23:59"}], "object": []},
                "comment": "claude-isolation-domain-guard"}},
            "limits": ["IPv4 domain guard only", "Not an OAuth/API classifier",
                       "Not a full kill switch", "Verify live firmware schema before use"]})
    files["manifest.json"] = dump({
        "version": "1.1.0", "status": "generated_not_applied",
        "proxy": {"host": host, "port": port}, "unprotected": mode,
        "domains": domains, "profile_identifier": identifier,
        "sha256": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
        "pending": ["backup", "enable and verify rule-based TUN",
                    "set and verify Singapore system timezone", "verify browser timezone",
                    "policy application", "fixed node routing",
                    "native process guard", "normal egress test", "node failure test",
                    "proxy exit test", "IPv6/UDP/DNS coverage review"],
    })
    return files


def write_outputs(config, output):
    files = build(config)
    output = Path(output)
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    for name, data in files.items():
        target = output / name
        with target.open("xb") as stream:
            stream.write(data)
        if os.name != "nt":
            target.chmod(0o600)
    return sorted(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="New directory under an existing parent")
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text(encoding="utf-8-sig"))
        names = write_outputs(config, args.out)
    except (OSError, ValueError) as error:
        parser.exit(2, f"Generation refused: {error}\n")
    print(f"Generated {len(names)} files; no settings applied. Review manifest.json.")


if __name__ == "__main__":
    main()
