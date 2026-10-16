import os
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"), "Windows PowerShell required")
class WindowsBoundaryTests(unittest.TestCase):
    def test_mocked_system_boundaries(self):
        script = Path(__file__).with_name("test_windows_mock.ps1")
        result = subprocess.run([shutil.which("powershell.exe"), "-NoProfile", "-NonInteractive",
                                 "-File", str(script)], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS:", result.stdout)


if __name__ == "__main__":
    unittest.main()
