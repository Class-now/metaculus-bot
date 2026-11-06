import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from market_pulse import select_market_pulse_questions

NOW = datetime(2026, 11, 10, tzinfo=timezone.utc)


def question(forecasted=False, close_in_hours=None):
    return SimpleNamespace(
        already_forecasted=forecasted,
        close_time=None
        if close_in_hours is None
        else NOW + timedelta(hours=close_in_hours),
    )


class SelectTest(unittest.TestCase):
    def selected(self, q):
        return select_market_pulse_questions([q], now=NOW) == [q]

    def test_inside_window_is_selected(self):
        self.assertTrue(self.selected(question(close_in_hours=20)))

    def test_far_from_close_is_skipped(self):
        self.assertFalse(self.selected(question(close_in_hours=500)))

    def test_already_closed_is_skipped(self):
        self.assertFalse(self.selected(question(close_in_hours=-1)))

    def test_already_forecast_is_skipped(self):
        self.assertFalse(self.selected(question(True, 20)))

    def test_missing_close_time_is_skipped(self):
        self.assertFalse(self.selected(question()))

    def test_naive_close_time_is_treated_as_utc(self):
        q = question(close_in_hours=20)
        q.close_time = q.close_time.replace(tzinfo=None)
        self.assertTrue(self.selected(q))

    def test_soonest_close_comes_first(self):
        late, soon = question(close_in_hours=50), question(close_in_hours=5)
        self.assertEqual(
            select_market_pulse_questions([late, soon], now=NOW), [soon, late]
        )


if __name__ == "__main__":
    unittest.main()
