"""Run with: python -m unittest discover -s tools -p test_build_year.py -v"""

from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from build_year import DATA, build_year, calendar_rows, resolve_year, write_calendar


class BuildYearTests(unittest.TestCase):
    def setUp(self):
        self.base = json.loads((DATA / "calendar.json").read_text(encoding="utf-8"))

    def resolve(self, year, overrides=None, terms=None):
        with redirect_stderr(io.StringIO()):
            return resolve_year(year, self.base, overrides or {}, terms or {})

    def test_leap_and_common_years(self):
        for year, count in ((2028, 366), (2029, 365), (2100, 365), (2400, 366)):
            with self.subTest(year=year):
                result = self.resolve(year)
                rows = calendar_rows(result)
                self.assertEqual(len(rows), count)
                self.assertEqual(len({row["date"] for row in rows}), count)
                self.assertEqual("leap_day" in result, count == 366)

    def test_swaps_keep_contents_and_original_artwork(self):
        # Synthetic dates exercise all four swaps; these are not published predictions.
        dates = {"立春": "02-03", "夏至": "06-20", "処暑": "08-22", "冬至": "12-21"}
        before = {row["date"]: row for row in calendar_rows(self.base)}
        for year in (2028, 2029):
            result = self.resolve(year, terms={str(year): dates})
            after = {row["date"]: row for row in calendar_rows(result)}
            for term, target in dates.items():
                source = next(key for key, row in before.items() if row.get("solar_term") == term)
                self.assertEqual(after[target]["solar_term"], term)
                self.assertEqual(after[target]["illustration_date"], source)
                self.assertEqual(after[source]["illustration_date"], target)
                for key, original_key in ((target, source), (source, target)):
                    content = {k: v for k, v in after[key].items() if k not in {"date", "illustration_date"}}
                    original = {k: v for k, v in before[original_key].items() if k != "date"}
                    self.assertEqual(content, original)
            self.assertEqual(len(after), 366 if year == 2028 else 365)

    def test_published_2027_dates_and_sources(self):
        terms = json.loads((DATA / "solar_terms.json").read_text(encoding="utf-8"))
        result = build_year(2027)
        rows = {row["date"]: row for row in calendar_rows(result)}
        for term, target in terms["2027"].items():
            self.assertEqual(rows[target]["solar_term"], term)
        self.assertIn("/yoko/2027/", terms["_sources"]["2027"])

    def test_missing_year_warns_and_does_not_move_entries(self):
        errors = io.StringIO()
        with redirect_stderr(errors):
            result = resolve_year(2029, self.base, {}, {})
        self.assertIn("2029", errors.getvalue())
        self.assertIn("WARNING", errors.getvalue())
        self.assertEqual(result["entries"], self.base["entries"])

    def test_override_is_replacement_and_inputs_are_unchanged(self):
        original = copy.deepcopy(self.base)
        replacement = copy.deepcopy(self.base["entries"][0])
        replacement["title"] = "Replacement title"
        result = self.resolve(2028, {"01-01": replacement})
        self.assertEqual(result["entries"][0]["title"], "Replacement title")
        self.assertEqual(self.base, original)
        self.assertNotIn("illustration_date", replacement)

    def test_slot_rotation_and_slot1_needs_no_file(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            write_calendar(self.base, data / "calendar.json")
            (data / "solar_terms.json").write_text("{}", encoding="utf-8")
            (data / "years").mkdir()
            for slot in (2, 3, 4):
                replacement = self.base["entries"][0] | {"title": f"slot{slot}"}
                write_calendar({"01-01": replacement}, data / "years" / f"slot{slot}.json")
            for year, title in ((2027, self.base["entries"][0]["title"]), (2028, "slot2"),
                                (2029, "slot3"), (2030, "slot4"), (2031, self.base["entries"][0]["title"])):
                with self.subTest(year=year), redirect_stderr(io.StringIO()):
                    self.assertEqual(build_year(year, data)["entries"][0]["title"], title)

    def test_invalid_target_and_override_are_rejected(self):
        with self.assertRaises(ValueError):
            self.resolve(2029, terms={"2029": {"立春": "02-29"}})
        with self.assertRaises(ValueError):
            self.resolve(2029, {"13-01": {}})
        with self.assertRaises(ValueError):
            self.resolve(2029, {"01-01": {"date": "01-02"}})

    def test_json_round_trip_has_no_leap_day_in_common_year(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested" / "2029.json"
            result = self.resolve(2029)
            write_calendar(result, output)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), result)
            self.assertNotIn("02-29", [row["date"] for row in calendar_rows(result)])


class WebPackagingTests(unittest.TestCase):
    def test_jst_year_and_december_rollover(self):
        from package_web import publishing_year
        self.assertEqual(publishing_year(datetime(2026, 12, 31, 15, tzinfo=timezone.utc)), 2027)
        before_midnight = datetime(2026, 12, 31, 14, 30, tzinfo=timezone.utc)
        self.assertEqual(publishing_year(before_midnight), 2026)
        self.assertEqual(publishing_year(before_midnight, rollover=True), 2027)
        self.assertEqual(publishing_year(datetime(2027, 1, 1, tzinfo=timezone.utc), rollover=True), 2027)

    def test_year_directories_and_shortcut_copy(self):
        from PIL import Image
        import package_web
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            with Image.new("RGB", (12, 24), "green") as image:
                image.save(source / "01-01.webp", "WEBP")
            with patch.object(package_web, "SOURCE_WALLPAPERS", source), redirect_stderr(io.StringIO()):
                counts = package_web.package_wallpapers(2027, root / "web", ["01-01"])
            self.assertEqual(counts, (1, 1))
            public = root / "web" / "wallpapers"
            first = (public / "2027" / "01-01.jpg").read_bytes()
            self.assertEqual(first, (public / "01-01.jpg").read_bytes())
            self.assertEqual(first, (public / "2028" / "01-01.jpg").read_bytes())
            with Image.open(public / "2028" / "01-01.jpg") as image:
                image.load()
                self.assertEqual(image.size, (1080, 2400))

    def test_leap_image_exists_only_in_the_leap_year_directory(self):
        from PIL import Image
        import package_web
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            with Image.new("RGB", (12, 24), "blue") as image:
                image.save(source / "02-29.webp", "WEBP")
            with patch.object(package_web, "SOURCE_WALLPAPERS", source), redirect_stderr(io.StringIO()):
                counts = package_web.package_wallpapers(2027, root / "web", ["02-29"])
            self.assertEqual(counts, (0, 1))
            public = root / "web" / "wallpapers"
            self.assertFalse((public / "02-29.jpg").exists())
            self.assertFalse((public / "2027" / "02-29.jpg").exists())
            self.assertTrue((public / "2028" / "02-29.jpg").is_file())

    def test_changed_entries_are_composed_instead_of_reusing_base_images(self):
        from PIL import Image
        import compose_wallpapers
        import package_web
        base = json.loads((DATA / "calendar.json").read_text(encoding="utf-8"))
        current = build_year(2027)
        with redirect_stderr(io.StringIO()):
            following = resolve_year(2028, base, {}, {"2028": {"立春": "02-03"}})

        def render(entry, out_dir):
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / f"{entry['date']}.webp"
            color = "red" if entry.get("solar_term") else "yellow"
            with Image.new("RGB", (12, 24), color) as image:
                image.save(path, "WEBP")
            return path

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            for key in ("02-03", "02-04"):
                with Image.new("RGB", (12, 24), "green") as image:
                    image.save(source / f"{key}.webp", "WEBP")
            with patch.object(package_web, "SOURCE_WALLPAPERS", source), \
                    patch.object(package_web, "build_year", side_effect=[current, following]), \
                    patch.object(compose_wallpapers, "compose", side_effect=render) as composed:
                self.assertEqual(package_web.package_wallpapers(2027, root / "web", ["02-03", "02-04"]), (2, 2))
            self.assertEqual(composed.call_count, 2)
            for key in ("02-03", "02-04"):
                public = root / "web" / "wallpapers"
                self.assertNotEqual((public / "2027" / f"{key}.jpg").read_bytes(),
                                    (public / "2028" / f"{key}.jpg").read_bytes())


if __name__ == "__main__":
    unittest.main()
