import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from market_pulse import select_market_pulse_questions

NOW = datetime(2026, 11, 10, tzinfo=timezone.utc)


def question(forecasted, close_in_hours=None, forecast_age_hours=None):
    return SimpleNamespace(
        already_forecasted=forecasted,
        close_time=None
        if close_in_hours is None
        else NOW + timedelta(hours=close_in_hours),
        timestamp_of_my_last_forecast=None
        if forecast_age_hours is None
        else NOW - timedelta(hours=forecast_age_hours),
    )


class SelectTest(unittest.TestCase):
    def selected(self, q):
        return select_market_pulse_questions([q], now=NOW) == [q]

    def test_new_question_is_selected(self):
        self.assertTrue(self.selected(question(False, 500)))

    def test_far_from_close_is_skipped(self):
        self.assertFalse(self.selected(question(True, 500, 100)))

    def test_closing_soon_with_stale_forecast_is_refreshed(self):
        self.assertTrue(self.selected(question(True, 20, 100)))

    def test_closing_soon_with_fresh_forecast_is_skipped(self):
        self.assertFalse(self.selected(question(True, 20, 5)))

    def test_refresh_happens_only_once(self):
        self.assertFalse(self.selected(question(True, 8, 12)))

    def test_missing_dates_are_skipped(self):
        self.assertFalse(self.selected(question(True, None, 100)))
        self.assertFalse(self.selected(question(True, 20, None)))

    def test_naive_close_time_is_treated_as_utc(self):
        q = question(True, 20, 100)
        q.close_time = q.close_time.replace(tzinfo=None)
        self.assertTrue(self.selected(q))


if __name__ == "__main__":
    unittest.main()
