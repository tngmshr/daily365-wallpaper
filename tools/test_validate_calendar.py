"""Run with: python -m unittest discover -s tools -p 'test_*.py' -v"""

from __future__ import annotations

import copy
import json
import unittest

from validate_calendar import DATA, THEMES_FILE, load_slots, validate


class ValidateCalendarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((DATA / "calendar.json").read_text(encoding="utf-8"))
        cls.slots = load_slots()
        cls.themes = {t["id"] for t in json.loads(THEMES_FILE.read_text(encoding="utf-8"))["themes"]}
        cls.terms = json.loads((DATA / "solar_terms.json").read_text(encoding="utf-8"))

    def run_validate(self, data=None, slots=None, terms=None):
        errors, _, _ = validate(
            data if data is not None else self.data,
            slots if slots is not None else self.slots,
            self.themes,
            terms if terms is not None else self.terms,
            illustrations=None,
        )
        return errors

    def assertError(self, errors, fragment):
        self.assertTrue(any(fragment in message for message in errors),
                        f"{fragment!r} not in {errors}")

    def test_repository_data_passes(self):
        self.assertEqual(self.run_validate(), [])

    def test_duplicate_and_missing_dates_are_named(self):
        data = copy.deepcopy(self.data)
        data["entries"][1] = copy.deepcopy(data["entries"][0]) | {"title": "x", "work_tip": "y" * 20}
        errors = self.run_validate(data)
        self.assertError(errors, "duplicate dates ['01-01']")
        self.assertError(errors, "missing dates ['01-02']")

    def test_order_is_checked_separately(self):
        data = copy.deepcopy(self.data)
        data["entries"][0], data["entries"][1] = data["entries"][1], data["entries"][0]
        errors = self.run_validate(data)
        self.assertError(errors, "not in calendar order")
        self.assertFalse(any("missing" in message for message in errors))

    def test_leap_day_must_be_separate(self):
        data = copy.deepcopy(self.data)
        data["entries"].insert(59, data.pop("leap_day"))
        errors = self.run_validate(data)
        self.assertError(errors, "02-29 must be stored in leap_day")
        self.assertError(errors, "leap_day: missing")
        data = copy.deepcopy(self.data)
        data["leap_day"]["date"] = "03-01"
        self.assertError(self.run_validate(data), "leap_day: date is '03-01'")

    def test_text_limits(self):
        data = copy.deepcopy(self.data)
        data["entries"][0]["summary"] = "あ" * 71 + "。"
        data["entries"][1]["work_tip"] = "あ" * 31
        data["entries"][2]["title"] = " 前後に空白 "
        errors = self.run_validate(data)
        self.assertError(errors, "01-01 summary length 72")
        self.assertError(errors, "01-02 work_tip length 31")
        self.assertError(errors, "01-03 title has surrounding spaces")

    def test_unknown_theme_and_missing_field(self):
        data = copy.deepcopy(self.data)
        data["entries"][0]["theme"] = "no_such_theme"
        del data["entries"][1]["work_tip"]
        errors = self.run_validate(data)
        self.assertError(errors, "01-01 unknown theme 'no_such_theme'")
        self.assertError(errors, "01-02 missing fields ['work_tip']")

    def test_movable_day_needs_solar_term(self):
        data = copy.deepcopy(self.data)
        data["entries"][32]["title"] = "節分"  # 02-02 fixed date would be wrong in some years
        self.assertError(self.run_validate(data), "02-02 title mentions 節分")

    def test_every_year_needs_every_term(self):
        terms = copy.deepcopy(self.terms)
        del terms["2030"]["立春"]
        terms["2031"]["夏至"] = "02-29"
        errors = self.run_validate(terms=terms)
        self.assertError(errors, "2030 has no date for ['立春']")
        self.assertError(errors, "2031 夏至 has invalid date '02-29'")

    def test_slot_rules(self):
        slots = copy.deepcopy(self.slots)
        sample = next(iter(slots[2].values()))
        slots[2]["02-04"] = sample | {"date": "02-04", "title": "立春を上書き", "work_tip": "z" * 20}
        slots[2]["13-01"] = sample
        slots[3]["01-01"] = copy.deepcopy(self.data["entries"][1]) | {"date": "01-01"}
        errors = self.run_validate(slots=slots)
        self.assertError(errors, "slot2/02-04: replaces the 立春 entry")
        self.assertError(errors, "slot2/13-01: invalid date key")
        # 01-02 の題材を 01-01 に置くと、その年は同じ見出しが2回出る。
        self.assertError(errors, "slot3 year: duplicate title")

    def test_slot_date_mismatch(self):
        slots = copy.deepcopy(self.slots)
        key = next(iter(slots[4]))
        slots[4][key] = slots[4][key] | {"date": "12-31"}
        self.assertError(self.run_validate(slots=slots), f"slot4/{key}: date '12-31' does not match")


if __name__ == "__main__":
    unittest.main()
