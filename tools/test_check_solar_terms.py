"""Run with: python -m unittest discover -s tools -p 'test_*.py' -v"""

from __future__ import annotations

import copy
import json
import unittest

from build_year import DATA
from check_solar_terms import check, read_rows


class SolarTermCheckTests(unittest.TestCase):
    def setUp(self):
        self.terms = json.loads((DATA / "solar_terms.json").read_text(encoding="utf-8"))
        self.rows = read_rows()
        self.calendar = json.loads((DATA / "calendar.json").read_text(encoding="utf-8"))

    def test_current_data_passes(self):
        errors, _ = check(self.terms, self.rows, self.calendar)
        self.assertEqual(errors, [])

    def test_published_years_match_the_computation(self):
        published = [row for row in self.rows if row["published_jst"]]
        self.assertGreaterEqual({int(row["year"]) for row in published}, {2025, 2026, 2027})
        for row in published:
            self.assertEqual(row["published_jst"], row["computed_jst"], row)

    def test_date_mismatch_is_an_error(self):
        terms = copy.deepcopy(self.terms)
        terms["2029"]["冬至"] = "12-22"
        errors, _ = check(terms, self.rows)
        self.assertTrue(any("2029 冬至" in message for message in errors), errors)

    def test_published_almanac_must_replace_the_computed_source(self):
        rows = copy.deepcopy(self.rows)
        row = next(r for r in rows if r["year"] == "2028" and r["term"] == "立春")
        row["published_jst"] = "2028-02-04 16:31"
        row["published_source"] = "https://eco.mtk.nao.ac.jp/koyomi/yoko/2028/rekiyou282.html"
        errors, _ = check(self.terms, rows)
        self.assertTrue(any("_sources still says" in message for message in errors), errors)

    def test_almanac_overrides_the_computation(self):
        rows = copy.deepcopy(self.rows)
        terms = copy.deepcopy(self.terms)
        row = next(r for r in rows if r["year"] == "2029" and r["term"] == "冬至")
        row["published_jst"] = "2029-12-22 00:01"
        row["published_source"] = "https://eco.mtk.nao.ac.jp/koyomi/yoko/2029/rekiyou292.html"
        row["computed_jst"] = "2029-12-22 00:01"
        terms["_sources"]["2029"] = row["published_source"]
        errors, _ = check(terms, rows)
        self.assertTrue(any("2029 冬至: solar_terms.json 12-21, almanac" in m for m in errors), errors)
        terms["2029"]["冬至"] = "12-22"
        errors, _ = check(terms, rows)
        self.assertEqual(errors, [])

    def test_close_to_midnight_warns(self):
        rows = copy.deepcopy(self.rows)
        row = next(r for r in rows if r["year"] == "2029" and r["term"] == "冬至")
        row["computed_jst"] = "2029-12-21 23:45"
        _, warnings = check(self.terms, rows)
        self.assertTrue(any("2029 冬至" in message for message in warnings), warnings)

    def test_calendar_needs_all_four_terms(self):
        calendar = copy.deepcopy(self.calendar)
        next(row for row in calendar["entries"] if row.get("solar_term") == "処暑").pop("solar_term")
        errors, _ = check(self.terms, self.rows, calendar)
        self.assertTrue(any("solar_term entries" in message for message in errors), errors)


if __name__ == "__main__":
    unittest.main()
