from datetime import datetime, timezone, timedelta
from project_code.old_methods.calendar_methods import *
from project_code.auth import *

# ── Demo block ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from auth import get_user_service

    svc = get_user_service()
    user_email = "demo@example.com"
    cal_id = "primary"

    now = datetime.now(timezone.utc).replace(microsecond=0)
    evt = create_event(
        svc,
        cal_id,
        user_email,
        title="Sprint Demo",
        description="Weekly sprint showcase.",
        start_iso=(now + timedelta(hours=2)).isoformat(),
        end_iso=(now + timedelta(hours=3)).isoformat(),
        timezone_id="UTC",
        if_exists="skip",
    )
    print("Created:", evt["id"])

    deleted = delete_event_by_fields(
        svc,
        cal_id,
        email=user_email,
        title="Sprint Demo",
        event_date=now.date().isoformat(),
    )
    print("Deleted result:", deleted)
