from datetime import datetime, timezone

from scripts.limit_retry import retry_time

NOW = datetime(2026, 11, 24, 6, 40, 8, tzinfo=timezone.utc)


def test_retry_after_the_usage_limit_reset():
    log = "=== 2026-11-24T06:40:05Z start research\nYou've hit your 5-hour limit · resets 9:40am (UTC)\n=== 2026-11-24T06:40:08Z end research rc=1\n"
    assert retry_time(log, NOW) == datetime(2026, 11, 24, 9, 45, tzinfo=timezone.utc)
    assert retry_time(log.replace("9:40am", "1pm"), NOW) == datetime(2026, 11, 24, 13, 5, tzinfo=timezone.utc)


def test_no_retry_for_other_failures_or_an_earlier_session():
    old = "=== x start research\nYou've hit your 5-hour limit · resets 9:40am (UTC)\n=== x end research rc=1\n"
    new = "=== y start research\nAPI Error: 500\n=== y end research rc=1\n"
    assert retry_time(old + new, NOW) is None
    assert retry_time("=== y start research\nYou've hit your weekly limit · resets 6am (UTC)\n=== y end rc=1\n",
                      datetime(2026, 11, 24, 6, 30, tzinfo=timezone.utc)) is None   # 23.6 h away: not a same-day retry
