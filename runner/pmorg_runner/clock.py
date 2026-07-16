"""Ceas virtual determinist: timpul avansează doar explicit."""

from datetime import datetime, timedelta


class VirtualClock:
    def __init__(self, start="2026-07-16 08:00:00"):
        self._now = datetime.fromisoformat(start)

    @property
    def now(self):
        return self._now.strftime("%Y-%m-%d %H:%M:%S")

    def advance(self, minutes=0, hours=0, days=0):
        self._now += timedelta(minutes=minutes, hours=hours, days=days)
        return self.now
