import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from scripts import health


def test_running_session_counts_as_activity(tmp_path: Path):
    """11-27 19:35: an InSilico session that had started but not ended was reported as 'slot idle 8h'."""
    now = datetime.now(timezone.utc)
    ts = lambda h: (now - timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ")
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "agent-2026-11-27-insilico.log").write_text(
        f"=== {ts(9)} start insilico\nx\n=== {ts(8)} end insilico rc=0\n=== {ts(0.5)} start insilico\nworking\n")
    f = health.gather(tmp_path, tmp_path / "none.db")
    assert ("insilico" in [m for _, m in f["starts"]])
    assert max(t for t, m in f["starts"] if m == "insilico") == ts(0.5)
