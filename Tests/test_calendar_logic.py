import unittest
from unittest.mock import MagicMock, call, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from project_code import calendar_creation
from project_code import event_creation

class TestCalendarCreation(unittest.TestCase):

    def setUp(self):
        self.mock_service = MagicMock()

    def test_get_user_default_timezone_settings_success(self):
        # Setup: settings().get().execute() returns {"value": "Europe/London"}
        self.mock_service.settings().get.return_value.execute.return_value = {"value": "Europe/London"}
        
        tz = calendar_creation.get_user_default_timezone(self.mock_service)
        self.assertEqual(tz, "Europe/London")

    def test_get_user_default_timezone_fallback(self):
        # Setup: settings().get() raises Exception
        self.mock_service.settings().get.side_effect = Exception("Auth error")
        # Setup: calendars().get("primary") returns {"timeZone": "Asia/Tokyo"}
        self.mock_service.calendars().get.return_value.execute.return_value = {"timeZone": "Asia/Tokyo"}

        tz = calendar_creation.get_user_default_timezone(self.mock_service)
        self.assertEqual(tz, "Asia/Tokyo")

    def test_create_calendar_no_tz(self):
        # Should call get_user_default_timezone
        with patch('project_code.calendar_creation.get_user_default_timezone', return_value="America/Chicago") as mock_tz:
            self.mock_service.calendars().insert.return_value.execute.return_value = {"id": "cal123"}
            
            calendar_creation.create_calendar(self.mock_service, "Test Cal")
            
            # Check insert called with resolved TZ
            self.mock_service.calendars().insert.assert_called_with(body={"summary": "Test Cal", "timeZone": "America/Chicago"})

    def test_create_calendar_with_defaults(self):
        self.mock_service.calendars().insert.return_value.execute.return_value = {"id": "cal123"}
        
        create_res = calendar_creation.create_calendar(
            self.mock_service, 
            "Test", 
            time_zone="UTC", 
            default_reminders=[{"method": "popup", "minutes": 10}]
        )
        
        # Verify reminders patched
        self.mock_service.calendarList().patch.assert_called_with(
            calendarId="cal123",
            body={"defaultReminders": [{"method": "popup", "minutes": 10}]}
        )

    def test_delete_calendar_owner(self):
        # Check permissions: role=owner
        self.mock_service.calendarList().get.return_value.execute.return_value = {"accessRole": "owner"}
        
        calendar_creation.delete_calendar(self.mock_service, "cal123")
        
        # Should call calendars().delete()
        self.mock_service.calendars().delete.assert_called_with(calendarId="cal123")

    def test_delete_calendar_not_owner(self):
        # Check permissions: role=reader
        self.mock_service.calendarList().get.return_value.execute.return_value = {"accessRole": "reader"}
        
        calendar_creation.delete_calendar(self.mock_service, "cal123")
        
        # Should call calendarList().delete() (unsubscribe)
        self.mock_service.calendarList().delete.assert_called_with(calendarId="cal123")


class TestEventCreation(unittest.TestCase):

    def setUp(self):
        self.mock_service = MagicMock()

    def test_generate_unique_key(self):
        key1 = event_creation.generate_unique_key("Meeting", "2023-01-01", "2023-01-02", "Office", "")
        key2 = event_creation.generate_unique_key("Meeting", "2023-01-01", "2023-01-02", "Office", "")
        key3 = event_creation.generate_unique_key("Meeting", "2023-01-02", "2023-01-02", "Office", "")
        
        self.assertEqual(key1, key2)
        self.assertNotEqual(key1, key3)

    def test_create_event_dedupe_skip(self):
        # Mock finding an existing event
        existing = {"id": "existing_123", "summary": "Meeting"}
        # Patch find_event_by_dedupe_key to return existing
        with patch('project_code.event_creation.find_event_by_dedupe_key', return_value=existing):
            # Also need get_user_default_timezone mocked because create_event lazy loads it if needed
            with patch('project_code.calendar_creation.get_user_default_timezone', return_value="UTC"):
                
                res = event_creation.create_event(
                    self.mock_service, 
                    "cal1", 
                    {"summary": "Meeting", "start": {"dateTime": "2023-01-01T10:00:00"}}, 
                    dedupe=True, 
                    if_exists="skip"
                )
                
                # Should NOT insert
                self.mock_service.events().insert.assert_not_called()
                self.assertEqual(res["status"], "skipped")
                self.assertEqual(res["event_id"], "existing_123")

    def test_create_event_dedupe_update(self):
        existing = {"id": "existing_123", "summary": "Old Title"}
        
        with patch('project_code.event_creation.find_event_by_dedupe_key', return_value=existing):
            with patch('project_code.calendar_creation.get_user_default_timezone', return_value="UTC"):
                
                # We mock updated event response
                self.mock_service.events().patch.return_value.execute.return_value = {"id": "existing_123"}
                
                res = event_creation.create_event(
                    self.mock_service, 
                    "cal1", 
                    {"summary": "New Title", "start": {"dateTime": "2023-01-01T10:00:00"}}, 
                    dedupe=True, 
                    if_exists="update"
                )
                
                # Should call patch
                self.mock_service.events().patch.assert_called()
                self.assertEqual(res["status"], "updated")

if __name__ == '__main__':
    unittest.main()
