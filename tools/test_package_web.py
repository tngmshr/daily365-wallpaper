"""Run with: python -m unittest discover -s tools -p 'test_*.py' -v"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import package_web

ROOT = Path(__file__).resolve().parents[1]


class VersionTests(unittest.TestCase):
    def test_reads_pubspec_build(self):
        self.assertEqual(package_web.read_version("name: x\nversion: 1.3.2+8\n"), ("1.3.2", 8))

    def test_build_number_must_survive_versioncode_modulo(self):
        # split-per-abi: arm64 versionCode = 2000 + build; the device compares versionCode % 1000.
        package_web.read_version("version: 1.0.0+999\n")
        for text in ("version: 1.0.0+1000\n", "version: 1.0.0+0\n", "version: 1.0.0\n"):
            with self.subTest(text=text), self.assertRaises(SystemExit):
                package_web.read_version(text)

    def test_version_json_uses_notes_of_the_pubspec_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools").mkdir()
            (root / "pubspec.yaml").write_text("version: 1.4.0+9\n", encoding="utf-8")
            (root / "tools" / "whats_new.json").write_text(
                json.dumps({"1.4.0": ["a"], "1.3.0": ["b"]}), encoding="utf-8")
            package_web.write_version(root, root)
            payload = json.loads((root / "version.json").read_text(encoding="utf-8"))
            self.assertEqual(payload, {"version": "1.4.0", "build": 9, "notes": ["a"]})

    def test_repository_version_is_valid(self):
        version, build = package_web.read_version((ROOT / "pubspec.yaml").read_text(encoding="utf-8"))
        self.assertLess(build, 1000)
        notes = json.loads((ROOT / "tools" / "whats_new.json").read_text(encoding="utf-8"))
        self.assertIn(version, notes, "tools/whats_new.json has no notes for the pubspec version")


class PrecacheTests(unittest.TestCase):
    def make_build(self, root: Path, main_js: str = "a") -> None:
        (root / "assets").mkdir(parents=True, exist_ok=True)
        (root / "wallpapers").mkdir(exist_ok=True)
        (root / "index.html").write_text("<html>", encoding="utf-8")
        (root / "main.dart.js").write_text(main_js, encoding="utf-8")
        (root / "assets" / "calendar.json").write_text("{}", encoding="utf-8")
        (root / "wallpapers" / "01-01.jpg").write_bytes(b"jpg")
        (root / ".nojekyll").write_text("", encoding="utf-8")
        (root / ".last_build_id").write_text("x", encoding="utf-8")
        (root / "version.json").write_text("{}", encoding="utf-8")
        (root / "flutter_service_worker.js").write_text("", encoding="utf-8")
        source = (ROOT / "web" / "service-worker.js").read_text(encoding="utf-8")
        (root / "service-worker.js").write_text(source, encoding="utf-8")

    def test_manifest_lists_app_files_with_revisions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_build(root)
            files = package_web.write_precache(root)
            self.assertEqual(files, ["./", "./assets/calendar.json", "./index.html", "./main.dart.js"])
            manifest = json.loads((root / "precache-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["files"], files)
            self.assertEqual(manifest["revisions"]["./"], manifest["revisions"]["./index.html"])

    def test_cache_name_changes_only_when_files_change(self):
        names = []
        for main_js in ("a", "a", "b"):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_build(root, main_js)
                package_web.write_precache(root)
                worker = (root / "service-worker.js").read_text(encoding="utf-8")
                self.assertNotIn(package_web.CACHE_VERSION_PLACEHOLDER, worker)
                names.append(next(line for line in worker.splitlines() if line.startswith("const CACHE_NAME")))
        self.assertEqual(names[0], names[1])
        self.assertNotEqual(names[0], names[2])

    def test_packaging_twice_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_build(root)
            package_web.write_precache(root)
            with self.assertRaises(SystemExit):
                package_web.write_precache(root)

    def test_source_worker_keeps_the_placeholder(self):
        source = (ROOT / "web" / "service-worker.js").read_text(encoding="utf-8")
        self.assertIn(package_web.CACHE_VERSION_PLACEHOLDER, source)


if __name__ == "__main__":
    unittest.main()
