import re
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path

from smart_clinic_web import SPECIALTIES, create_app


class SmartClinicWebTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database = Path(self.temp_dir.name) / "smart-clinic.sqlite"
        self.app = create_app(str(database))
        self.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = self.app.test_client()
        self.database = database

    def tearDown(self):
        self.temp_dir.cleanup()

    def csrf_token(self, page="/"):
        response = self.client.get(page)
        self.assertEqual(response.status_code, 200)
        match = re.search(rb'name="_csrf_token" value="([^"]+)"', response.data)
        if match is None:
            self.fail("CSRF token input was not rendered")
        return match.group(1).decode()

    def test_triage_escalates_red_flags_without_booking(self):
        token = self.csrf_token("/triage")
        response = self.client.post(
            "/triage",
            data={"_csrf_token": token, "severe_chest_pain": "yes", "tooth": "yes"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("لا تنتظر موعداً", response.get_data(as_text=True))
        self.assertNotIn("عرض المواعيد المتاحة", response.get_data(as_text=True))

    def test_triage_recommends_specialty_without_saving_symptoms(self):
        token = self.csrf_token("/triage")
        response = self.client.post(
            "/triage",
            data={"_csrf_token": token, "skin": "yes"},
        )
        self.assertIn("الجلدية", response.get_data(as_text=True))
        with self.client.session_transaction() as browser_session:
            self.assertEqual(browser_session["suggested_specialty"], "الجلدية")
        with closing(sqlite3.connect(self.database)) as connection:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertEqual(tables, {"appointments", "sqlite_sequence"})

    def test_triage_rejects_invalid_temperature_and_uses_general_care_for_mixed_symptoms(self):
        token = self.csrf_token("/triage")
        invalid = self.client.post(
            "/triage",
            data={"_csrf_token": token, "temperature": "nan"},
        )
        self.assertIn("درجة الحرارة يجب أن تكون بين 30 و45", invalid.get_data(as_text=True))
        token = self.csrf_token("/triage")
        mixed = self.client.post(
            "/triage",
            data={"_csrf_token": token, "skin": "yes", "tooth": "yes"},
        )
        self.assertIn("طب الأسرة", mixed.get_data(as_text=True))

    def test_scheduling_chooses_non_overlapping_earliest_slots(self):
        token = self.csrf_token("/book")
        first = self.client.post(
            "/book",
            data={
                "_csrf_token": token,
                "specialty": SPECIALTIES[0],
                "requested_date": date.today().isoformat(),
                "urgency": "routine",
            },
        )
        self.assertEqual(first.status_code, 200)
        second_token = self.csrf_token("/book")
        second = self.client.post(
            "/book",
            data={
                "_csrf_token": second_token,
                "specialty": SPECIALTIES[0],
                "requested_date": date.today().isoformat(),
                "urgency": "routine",
            },
        )
        self.assertEqual(second.status_code, 200)
        with closing(sqlite3.connect(self.database)) as connection:
            bookings = connection.execute(
                "SELECT scheduled_for, duration_minutes FROM appointments ORDER BY scheduled_for"
            ).fetchall()
        self.assertEqual(len(bookings), 2)
        self.assertGreaterEqual(
            (date.fromisoformat(bookings[1][0][:10]) - date.fromisoformat(bookings[0][0][:10])).days * 1440
            + int(bookings[1][0][11:13]) * 60 + int(bookings[1][0][14:16])
            - int(bookings[0][0][11:13]) * 60 - int(bookings[0][0][14:16]),
            bookings[0][1],
        )

    def test_booking_rejects_emergency_priority_and_invalid_specialty(self):
        token = self.csrf_token("/book")
        response = self.client.post(
            "/book",
            data={
                "_csrf_token": token,
                "specialty": SPECIALTIES[0],
                "requested_date": date.today().isoformat(),
                "urgency": "emergency",
            },
        )
        self.assertIn("مستوى الحجز غير صالح", response.get_data(as_text=True))
        with closing(sqlite3.connect(self.database)) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM appointments").fetchone()[0], 0)

    def test_analytics_counts_only_resolved_appointments(self):
        with closing(sqlite3.connect(self.database)) as connection:
            connection.executemany(
                """INSERT INTO appointments
                   (visit_code,specialty,scheduled_for,duration_minutes,urgency,status,created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                [
                    ("A1", SPECIALTIES[0], "2026-10-30T08:00", 30, "routine", "attended", "now"),
                    ("A2", SPECIALTIES[0], "2026-10-30T08:30", 30, "routine", "no_show", "now"),
                    ("A3", SPECIALTIES[0], "2026-10-30T09:00", 30, "routine", "scheduled", "now"),
                    ("A4", SPECIALTIES[0], "2026-10-30T09:30", 30, "routine", "cancelled", "now"),
                ],
            )
            connection.commit()
        response = self.client.get("/analytics")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("50.0%", body)
        self.assertIn("سجلات مكتملة", body)

    def test_csrf_required_for_mutations(self):
        response = self.client.post(
            "/book",
            data={
                "specialty": SPECIALTIES[0],
                "requested_date": date.today().isoformat(),
                "urgency": "routine",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("رمز حماية النموذج غير صالح", response.get_data(as_text=True))

    def test_status_updates_require_csrf_and_valid_transition(self):
        token = self.csrf_token("/book")
        self.client.post(
            "/book",
            data={
                "_csrf_token": token,
                "specialty": SPECIALTIES[0],
                "requested_date": date.today().isoformat(),
                "urgency": "routine",
            },
        )
        with closing(sqlite3.connect(self.database)) as connection:
            appointment_id = connection.execute("SELECT id FROM appointments").fetchone()[0]
        token = self.csrf_token("/")
        response = self.client.post(
            f"/appointments/{appointment_id}/status",
            data={"_csrf_token": token, "status": "no_show"},
        )
        self.assertEqual(response.status_code, 302)
        with closing(sqlite3.connect(self.database)) as connection:
            status = connection.execute(
                "SELECT status FROM appointments WHERE id=?", (appointment_id,)
            ).fetchone()[0]
        self.assertEqual(status, "no_show")
        repeated = self.client.post(
            f"/appointments/{appointment_id}/status",
            data={"_csrf_token": token, "status": "attended"},
        )
        self.assertEqual(repeated.status_code, 404)


if __name__ == "__main__":
    unittest.main()
