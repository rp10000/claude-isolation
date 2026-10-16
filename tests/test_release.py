import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release", ROOT / "scripts" / "make_release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def test_allowlist_and_repeatability(self):
        with tempfile.TemporaryDirectory() as tmp:
            one, two = Path(tmp) / "one.zip", Path(tmp) / "two.zip"
            self.assertEqual(release.package(ROOT, one), release.package(ROOT, two))
            with zipfile.ZipFile(one) as archive:
                self.assertEqual(set(archive.namelist()),
                                 {"claude-isolation/" + p for p in release.FILES})
                self.assertIsNone(archive.testzip())
                for name in archive.namelist():
                    archive.read(name).decode("utf-8")
            self.assertTrue(one.with_name("one.zip.sha256").is_file())
            before = one.read_bytes()
            with self.assertRaises(FileExistsError):
                release.package(ROOT, one)
            self.assertEqual(before, one.read_bytes())

    def test_no_output_in_skill(self):
        with self.assertRaises(ValueError):
            release.package(ROOT, ROOT / "forbidden.zip")
        self.assertFalse((ROOT / "forbidden.zip").exists())


if __name__ == "__main__":
    unittest.main()
