import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("generator", ROOT / "scripts" / "generate.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class GeneratorTests(unittest.TestCase):
    def config(self, **overrides):
        return dict(proxy_port=18080, **overrides)

    def test_default_scope(self):
        output = generator.build(self.config())
        manifest = json.loads(output["manifest.json"])
        self.assertEqual(set(manifest["domains"]), set(generator.PROVIDERS["claude"]))
        self.assertEqual(manifest["status"], "generated_not_applied")
        self.assertNotIn("ikuai-v4-plan.json", output)

    def test_tun_and_singapore_requirements_are_pending(self):
        output = generator.build(self.config())
        requirements = json.loads(output["setup-requirements.json"])
        self.assertEqual(requirements["status"], "required_not_applied_or_verified")
        self.assertEqual(requirements["tun"], {"required": True, "routing_mode": "rule_based",
                                               "keep_process_guard": True, "verified": False})
        self.assertEqual(requirements["system_timezone"], {
            "required": True, "iana_id": "Asia/Singapore", "windows_id": "Singapore Standard Time",
            "utc_offset": "+08:00", "verified": False})
        self.assertEqual(requirements["browser_timezone"], {
            "expected_iana_id": "Asia/Singapore", "verified": False})
        manifest = json.loads(output["manifest.json"])
        self.assertEqual(manifest["version"], "1.1.0")
        self.assertIn("setup-requirements.json", manifest["sha256"])
        self.assertIn("enable and verify rule-based TUN", manifest["pending"])
        self.assertIn("set and verify Singapore system timezone", manifest["pending"])

    def test_artifacts_agree(self):
        output = generator.build(self.config())
        policy = json.loads(output["chrome-policy.json"])
        data_url = policy["ProxySettings"]["ProxyPacUrl"]
        self.assertEqual(base64.b64decode(data_url.split(",", 1)[1]), output["protected.pac"])
        self.assertIs(policy["ProxySettings"]["ProxyPacMandatory"], True)
        profile = plistlib.loads(output["chrome.mobileconfig"])
        self.assertFalse(profile["PayloadRemovalDisallowed"])
        self.assertEqual(profile["PayloadScope"], "User")
        nested = profile["PayloadContent"][0]["PayloadContent"]["com.google.Chrome"]
        self.assertEqual(nested["Forced"][0]["mcx_preference_settings"], policy)
        self.assertTrue(all(x["handling"] == "disable_non_proxied_udp"
                            for x in policy["WebRtcIPHandlingUrl"]))

    def test_manifest_hashes(self):
        output = generator.build(self.config())
        for name, digest in json.loads(output["manifest.json"])["sha256"].items():
            self.assertEqual(hashlib.sha256(output[name]).hexdigest(), digest)

    def test_bad_ports_and_hosts(self):
        for port in (True, "8080", 0, -1, 65536, None):
            with self.subTest(port=port), self.assertRaises(ValueError):
                generator.build({"proxy_port": port})
        for host in ("localhost", "proxy.example", "192.0.2.1", "user:pass@127.0.0.1"):
            with self.subTest(host=host), self.assertRaises(ValueError):
                generator.build(self.config(proxy_host=host))

    def test_bad_domains(self):
        for value in ("*.claude.ai", "https://claude.ai", "claude.ai:443", "ai", "192.0.2.1",
                      "bad_name.example", "claude.ai\nDIRECT", "-bad.example", "co.uk", "com.cn",
                      "github.io", "foo.ck", "google.com", "googleapis.com", "cloudflare.com"):
            with self.subTest(domain=value), self.assertRaises(ValueError):
                generator.build(self.config(extra_domains=[value]))

    def test_public_suffix_exception_and_specific_hosts(self):
        output = generator.build(self.config(extra_domains=["www.ck", "accounts.google.com",
                                                             "project.github.io"]))
        domains = json.loads(output["manifest.json"])["domains"]
        self.assertTrue({"www.ck", "accounts.google.com", "project.github.io"}.issubset(domains))

    def test_bad_options(self):
        for options in ({"api_key": "fake"}, {"providers": []}, {"providers": ["unknown"]},
                        {"providers": "claude"}, {"extra_domains": [3]},
                        {"unprotected": "system"}, {"profile_identifier": "broken/value"}):
            config = self.config()
            config.update(options)
            with self.subTest(options=options), self.assertRaises(ValueError):
                generator.build(config)

    def test_router_scope(self):
        output = generator.build(self.config(router_sources=["10.77.8.21", "10.77.8.21"]))
        plan = json.loads(output["ikuai-v4-plan.json"])
        param = plan["request"]["param"]
        self.assertEqual(param["src_addr"]["custom"], ["10.77.8.21"])
        self.assertEqual(param["mode"], 0)
        self.assertEqual(set(param["domain"]["custom"]),
                         {x for d in generator.PROVIDERS["claude"] for x in (d, "*." + d)})
        for value in ("0.0.0.0/0", "10.77.8.0/24", "192.0.2.1", "::1", "10.77.8.255"):
            with self.subTest(source=value), self.assertRaises(ValueError):
                generator.build(self.config(router_sources=[value]))

    def test_no_overwrite_or_partial_on_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "output"
            generator.write_outputs(self.config(), path)
            original = {p.name: p.read_bytes() for p in path.iterdir()}
            with self.assertRaises(FileExistsError):
                generator.write_outputs(self.config(), path)
            self.assertEqual(original, {p.name: p.read_bytes() for p in path.iterdir()})
            bad_path = Path(tmp) / "bad"
            with self.assertRaises(ValueError):
                generator.write_outputs({"proxy_port": 0}, bad_path)
            self.assertFalse(bad_path.exists())

    @unittest.skipUnless(shutil.which("node"), "Node.js required for actual PAC execution")
    def test_pac_actual_javascript(self):
        for mode in ("direct", "proxy-then-direct"):
            config = self.config(unprotected=mode, providers=["claude", "openai", "gemini"])
            pac = generator.build(config)["protected.pac"].decode()
            protected = ["claude.ai", "api.anthropic.com", "A.B.CLAUDE.AI.", "chatgpt.com",
                         "cdn.oaistatic.com", "gemini.google.com", "cloudcode-pa.googleapis.com"]
            unprotected = ["evilclaude.ai", "claude.ai.evil.example", "anthropic.com.evil.example",
                           "10.foo.example", "172.20.fake.example", "100.64.fake.example",
                           "10.999.1.1", "100.128.0.1", "172.32.0.1", "192.169.1.1", "example.com"]
            local = ["localhost", "192.168.44.5", "10.77.8.21", "172.16.0.3", "100.64.0.1",
                     "100.127.255.254", "127.23.4.5", "::1", "[::1]", "box.local", "box.test.ts.net"]
            hosts = protected + unprotected + local
            js = pac + "\nconsole.log(JSON.stringify(" + json.dumps(hosts) + ".map(function(h){return FindProxyForURL('https://'+h,h);})));"
            result = subprocess.run([shutil.which("node"), "-e", js], check=True,
                                    capture_output=True, text=True)
            actual = json.loads(result.stdout)
            proxy = "PROXY 127.0.0.1:18080"
            normal = "DIRECT" if mode == "direct" else proxy + "; DIRECT"
            self.assertEqual(actual, [proxy] * len(protected) + [normal] * len(unprotected) +
                             ["DIRECT"] * len(local))

    @unittest.skipUnless(shutil.which("node"), "Node.js required")
    def test_ipv6_proxy_endpoint_and_custom_domain(self):
        config = self.config(proxy_host="::1", extra_domains=["LOGIN.EXAMPLE."])
        pac = generator.build(config)["protected.pac"].decode()
        result = subprocess.run([shutil.which("node"), "-e", pac +
            "console.log(FindProxyForURL('https://sub.login.example', 'sub.login.example'));"],
            check=True, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "PROXY [::1]:18080")


if __name__ == "__main__":
    unittest.main()
