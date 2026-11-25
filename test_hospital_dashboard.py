import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from hospital_app import HospitalApp, appointment_wait_minutes, dashboard_snapshot


class DashboardStore:
    def __init__(self, records):
        self.records = records

    def list(self, entity):
        return list(self.records.get(entity, []))


class DashboardSnapshotTests(unittest.TestCase):
    def test_dashboard_only_counts_non_cancelled_appointments_for_selected_day(self):
        store = DashboardStore({
            "appts": [
                {"date": "2026-10-30", "time": "11:00", "status": "بالانتظار", "patient": "مريض ب"},
                {"date": "2026-10-30", "time": "09:00", "status": "عاجل", "patient": "مريض أ"},
                {"date": "2026-10-30", "time": "08:00", "status": "ملغي", "patient": "مريض ج"},
                {"date": "2026-10-29", "time": "10:00", "status": "بالانتظار", "patient": "مريض د"},
                {"date": "2026-10-31", "time": "10:00", "status": "بالانتظار", "patient": "مريض هـ"},
            ],
        })

        snapshot = dashboard_snapshot(store, "2026-10-30")

        self.assertEqual(len(snapshot["appointments_today"]), 2)
        self.assertEqual(snapshot["waiting_today"], 2)
        self.assertEqual(
            [item["time"] for item in snapshot["appointments_today"]],
            ["09:00", "11:00"],
        )

    def test_dashboard_reports_inventory_beds_and_operational_follow_up(self):
        store = DashboardStore({
            "patients": [
                {"status": "حرج"},
                {"status": "Critical"},
                {"status": "مستقر"},
            ],
            "doctors": [{"status": "نشط"}, {"status": "بانتظار التحقق"}],
            "nurses": [{"status": "Active"}],
            "clinics": [{"status": "مفتوحة"}, {"status": "مغلقة مؤقتاً"}],
            "meds": [
                {"name": "دواء أ", "qty": 10, "status": "منخفض"},
                {"name": "دواء ب", "qty": 0, "status": "متوفر"},
                {"name": "دواء ج", "qty": 5, "status": "متوفر"},
            ],
            "beds": [
                {"patient": "", "status": "متاح"},
                {"patient": "مريض أ", "status": "متاح"},
                {"patient": "", "status": "Occupied"},
            ],
            "labs": [{"status": "جاهز"}, {"status": "Ready"}, {"status": "قيد التنفيذ"}],
        })

        snapshot = dashboard_snapshot(store, "2026-10-30")

        self.assertEqual(snapshot["patients"], 3)
        self.assertEqual(snapshot["beds_total"], 3)
        self.assertEqual(snapshot["beds_occupied"], 2)
        self.assertEqual([item["name"] for item in snapshot["low_stock_medicines"]], ["دواء أ", "دواء ب"])
        self.assertEqual(snapshot["ready_labs"], 2)
        self.assertEqual(snapshot["critical_patients"], 2)
        self.assertEqual(snapshot["active_staff"], 2)
        self.assertEqual(snapshot["open_clinics"], 1)

    def test_empty_store_has_zero_counts_without_division(self):
        snapshot = dashboard_snapshot(DashboardStore({}), "2026-10-30")

        self.assertEqual(snapshot["appointments_today"], [])
        self.assertEqual(snapshot["beds_total"], 0)
        self.assertEqual(snapshot["beds_occupied"], 0)
        self.assertEqual(snapshot["waiting_today"], 0)
        self.assertEqual(snapshot["low_stock_medicines"], [])
        self.assertIsNone(snapshot["average_wait_minutes"])

    def test_dashboard_uses_recorded_check_in_times_for_average_wait(self):
        now = datetime(2026, 10, 30, 10, 30, tzinfo=timezone.utc)
        store = DashboardStore({
            "appts": [
                {"date": "2026-10-30", "status": "بالانتظار", "check_in_at": "2026-10-30T10:00:00+00:00"},
                {"date": "2026-10-30", "status": "عاجل", "check_in_at": "2026-10-30T10:10:00+00:00"},
                {"date": "2026-10-30", "status": "مكتمل", "check_in_at": "2026-10-30T09:00:00+00:00"},
            ],
        })

        snapshot = dashboard_snapshot(store, "2026-10-30", now)

        self.assertEqual(snapshot["average_wait_minutes"], 25)
        self.assertEqual(appointment_wait_minutes({"check_in_at": "not-a-timestamp"}, now), None)

    def test_minimum_stock_threshold_is_an_alert_even_if_status_is_available(self):
        store = DashboardStore({
            "meds": [
                {"name": "حد أدنى", "qty": 5, "min_qty": 5, "status": "متوفر"},
                {"name": "فوق الحد", "qty": 6, "min_qty": 5, "status": "متوفر"},
            ],
        })

        snapshot = dashboard_snapshot(store, "2026-10-30")

        self.assertEqual([item["name"] for item in snapshot["low_stock_medicines"]], ["حد أدنى"])

    def test_medicine_status_is_derived_from_quantity_and_minimum(self):
        app = Mock(spec=HospitalApp)
        app.store = Mock()
        app.store.list.return_value = []

        record = HospitalApp.prepare_record(app, "meds", {"qty": "5", "min_qty": "5"})

        self.assertEqual(record["status"], "منخفض")


if __name__ == "__main__":
    unittest.main()
