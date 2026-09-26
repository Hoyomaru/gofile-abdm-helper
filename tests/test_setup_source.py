import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WindowsSetupSourceTests(unittest.TestCase):
    def test_setup_creates_local_venv_and_installs_requirements(self):
        source = (ROOT / "setup-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("'.venv'", source)
        self.assertIn("'Scripts\\python.exe'", source)
        self.assertIn("-m', 'venv'", source)
        self.assertIn("-m pip install", source)
        self.assertIn("requirements.txt", source)
        self.assertIn("Python 3.10+", source)

    def test_setup_launches_tray_from_local_venv(self):
        source = (ROOT / "setup-windows.ps1").read_text(encoding="utf-8")
        self.assertIn("'Scripts\\pythonw.exe'", source)
        self.assertIn("Start-Process -FilePath $VenvPythonw", source)
        self.assertIn("tray.py", source)

    def test_start_tray_prefers_local_venv(self):
        source = (ROOT / "start-tray.cmd").read_text(encoding="utf-8")
        self.assertIn(".venv\\Scripts\\pythonw.exe", source)
        self.assertIn('if exist "%PYTHONW%"', source)

    def test_cmd_wrapper_runs_powershell_setup(self):
        source = (ROOT / "setup-windows.cmd").read_text(encoding="utf-8")
        self.assertIn("setup-windows.ps1", source)
        self.assertIn("ExecutionPolicy Bypass", source)


if __name__ == "__main__":
    unittest.main()
