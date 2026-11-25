"""When a headless session dies on the usage limit ("You've hit your 5-hour limit · resets 9:40am (UTC)"), print the systemd
OnCalendar time (UTC) for one retry 5 minutes after the reset; exit 1 if the log's last session did not hit the limit or the
reset is more than 10 h away. Used by scripts/agent.sh (2026-11-25: the 11-24 research and review sessions died at 06:40 and 08:25
on the limit, both reset at 09:40, and nothing re-ran them: a whole research day was lost).
  usage: python -m scripts.limit_retry <logfile> [now-iso]"""
import re
import sys
from datetime import datetime, timedelta, timezone

PAT = re.compile(r"hit your .*limit.*resets\s+(\d{1,2})(?::(\d{2}))?\s*([ap]m)", re.I)


def retry_time(text: str, now: datetime) -> datetime | None:
    last = text.rsplit("=== ", 2)            # only the most recent session's lines
    seg = "=== ".join(last[-2:]) if len(last) > 1 else text
    m = None
    for m in PAT.finditer(seg):
        pass
    if not m:
        return None
    h, mi, ap = int(m.group(1)) % 12, int(m.group(2) or 0), m.group(3).lower()
    h += 12 if ap == "pm" else 0
    t = now.replace(hour=h, minute=mi, second=0, microsecond=0)
    if t <= now:
        t += timedelta(days=1)
    t += timedelta(minutes=5)
    return t if t - now <= timedelta(hours=10) else None


if __name__ == "__main__":
    now = datetime.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else datetime.now(timezone.utc)
    t = retry_time(open(sys.argv[1], errors="replace").read(), now)
    if t is None:
        sys.exit(1)
    print(t.strftime("%Y-%m-%d %H:%M:00 UTC"))
