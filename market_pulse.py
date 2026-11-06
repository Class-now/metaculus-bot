"""Question selection for the Market Pulse Challenge (spot-scored at close)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

MARKET_PULSE_TOURNAMENT_ID = "market-pulse-26q4"

# Only the forecast standing at close is scored, so forecast late and once.
# Runs are 4 hours apart, which leaves many retries inside the window.
FORECAST_WINDOW = timedelta(hours=72)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def select_market_pulse_questions(
    questions: Iterable[Any], now: datetime | None = None
) -> list[Any]:
    """Pick unforecast questions closing within the window, soonest first."""
    current = _as_utc(now or datetime.now(timezone.utc))
    selected = []
    for question in questions:
        if question.already_forecasted or question.close_time is None:
            continue
        time_left = _as_utc(question.close_time) - current
        if timedelta(0) < time_left <= FORECAST_WINDOW:
            selected.append(question)
    return sorted(selected, key=lambda q: _as_utc(q.close_time))
