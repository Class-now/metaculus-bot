"""Question selection for the Market Pulse Challenge (spot-scored at close)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

MARKET_PULSE_TOURNAMENT_ID = "market-pulse-26q4"

# Runs are 4 hours apart, so a 36-hour window gets several chances to refresh.
REFRESH_WINDOW = timedelta(hours=36)
MIN_REFRESH_AGE = timedelta(hours=24)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def select_market_pulse_questions(
    questions: Iterable[Any], now: datetime | None = None
) -> list[Any]:
    """Pick questions never forecast, or closing soon with a stale forecast."""
    current = _as_utc(now or datetime.now(timezone.utc))
    selected = []
    for question in questions:
        if not question.already_forecasted:
            selected.append(question)
            continue
        close_time = question.close_time
        last_forecast = question.timestamp_of_my_last_forecast
        if close_time is None or last_forecast is None:
            continue
        closes_soon = _as_utc(close_time) - current <= REFRESH_WINDOW
        is_stale = current - _as_utc(last_forecast) >= MIN_REFRESH_AGE
        if closes_soon and is_stale:
            selected.append(question)
    return selected
