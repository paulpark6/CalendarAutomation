import pytest
import importlib
import types
from unittest.mock import MagicMock
import project_code.calendar_methods as calendar_methods
from project_code.calendar_methods import create_event, delete_event_by_fields, list_local_records, USER_DATA_DIR

@pytest.fixture
def sandbox(tmp_path):
    """Redirect USER_DATA_DIR to a temp dir so tests don’t touch real files."""
    original = calendar_methods.USER_DATA_DIR
    USER_DATA_DIR = str(tmp_path)
    importlib.reload(calendar_methods)
    yield tmp_path
    USER_DATA_DIR = original
    importlib.reload(calendar_methods)


@pytest.fixture
def fake_service():
    """
    Build a stub that mimics
        service.events().<method>(...).execute()
    """
    svc = types.SimpleNamespace()
    svc._events = MagicMock()        # root mock
    svc.events = lambda: svc._events
    return svc

# -- testing create event  (no duplicates test) --
def test_duplicate_event_skipped(fake_service, sandbox):
    # -- Arrange ------------------------------------------------------------
    existing = {"id": "appCreated_X", "summary": "Demo"}
    # events().get(...).execute() returns an existing event
    fake_service._events.get.return_value.execute.return_value = existing

    # -- Act ---------------------------------------------------------------
    result = create_event(
        fake_service, "primary", "alice@example.com",
        title="Demo", description="",
        start_iso="2025-01-01T09:00:00Z", end_iso="2025-01-01T10:00:00Z",
        timezone_id="UTC",
        if_exists="skip"        # default is "skip" anyway
    )

    # -- Assert ------------------------------------------------------------
    assert result is existing                # got the same object back
    fake_service._events.insert.assert_not_called()
    fake_service._events.patch.assert_not_called()
