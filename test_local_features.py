import unittest
from datetime import date, datetime
from unittest.mock import Mock

from hospital_app import (
    HospitalApp,
    appointment_priority_rank,
    bed_status,
    dashboard_snapshot,
    financial_forecast,
    months_until_expiry,
    waiting_room_snapshot,
)


class LocalFeatureTests(unittest.TestCase):
    def test_bed_status_distinguishes_occupied_cleaning_and_available(self):
        self.assertEqual(bed_status({"patient": "مريض", "status": "متاح"}), "مشغول")
        self.assertEqual(bed_status({"patient": "", "status": "قيد التنظيف"}), "قيد التنظيف")
        self.assertEqual(bed_status({"patient": "", "status": "غير معروف"}), "متاح")

    def test_bed_form_preserves_cleaning_state_and_derives_occupancy(self):
        app = Mock(spec=HospitalApp)
        app.user_name = "مدير"
        app.store = Mock()
        app.store.list.side_effect = lambda entity: (
            [{"name": "مريض"}] if entity == "patients" else
            [{"name": "الجناح"}] if entity == "wards" else []
        )

        cleaning = HospitalApp.prepare_record(
            app,
            "beds",
            {"ward": "الجناح", "room": "101", "number": "1", "patient": "", "status": "قيد التنظيف"},
        )
        occupied = HospitalApp.prepare_record(
            app,
            "beds",
            {"ward": "الجناح", "room": "101", "number": "2", "patient": "مريض", "status": "متاح"},
        )

        self.assertEqual(cleaning["status"], "قيد التنظيف")
        self.assertEqual(occupied["status"], "مشغول")

    def test_bed_cannot_be_cleaned_while_patient_is_assigned(self):
        app = Mock(spec=HospitalApp)
        app.user_name = "مدير"
        app.store = Mock()
        app.store.list.side_effect = lambda entity: (
            [{"name": "مريض"}] if entity == "patients" else
            [{"name": "الجناح"}] if entity == "wards" else []
        )

        with self.assertRaisesRegex(ValueError, "أفرغ السرير"):
            HospitalApp.prepare_record(
                app,
                "beds",
                {"ward": "الجناح", "room": "101", "number": "1", "patient": "مريض", "status": "قيد التنظيف"},
            )

    def test_waiting_room_snapshot_separates_current_and_upcoming_today(self):
        store = Mock()
        store.list.side_effect = lambda entity: {
            "doctors": [{"name": "د. ليلى", "spec": "قلبية"}],
            "clinics": [{"name": "عيادة القلب", "specialty": "قلبية"}],
            "appts": [
                {"id": 4, "date": "2026-10-30", "time": "09:30", "status": "جار الكشف", "doctor": "د. ليلى"},
                {"id": 5, "date": "2026-10-30", "time": "10:00", "status": "بالانتظار", "doctor": "د. ليلى"},
                {"id": 6, "date": "2026-10-30", "time": "10:30", "status": "عاجل", "doctor": "د. ليلى"},
                {"id": 7, "date": "2026-10-29", "time": "08:00", "status": "بالانتظار", "doctor": "د. ليلى"},
                {"id": 8, "date": "2026-10-30", "time": "11:00", "status": "ملغي", "doctor": "د. ليلى"},
            ],
        }[entity]

        snapshot = waiting_room_snapshot(store, "2026-10-30")

        self.assertEqual(snapshot["current"]["id"], 4)
        self.assertEqual(snapshot["current"]["clinic"], "عيادة القلب")
        self.assertEqual([item["id"] for item in snapshot["upcoming"]], [6, 5])

    def test_queue_orders_emergency_then_booked_then_follow_up(self):
        appointments = [
            {"id": 1, "priority": "مراجعة"},
            {"id": 2, "priority": "موعد مسبق"},
            {"id": 3, "priority": "طارئة"},
            {"id": 4, "priority": "مراجعة", "status": "عاجل"},
        ]
        self.assertEqual(
            [item["id"] for item in sorted(appointments, key=appointment_priority_rank)],
            [3, 4, 2, 1],
        )

    def test_expiry_tracking_flags_batches_within_three_months_and_expired_batches(self):
        self.assertEqual(months_until_expiry("2026-03", date(2026, 1, 15)), 2)
        store = Mock()
        store.list.side_effect = lambda entity: {
            "appts": [],
            "beds": [],
            "meds": [],
            "bills": [],
            "patients": [],
            "doctors": [],
            "nurses": [],
            "clinics": [],
            "labs": [],
            "medication_batches": [
                {"id": 1, "expiry_month": "2026-04"},
                {"id": 2, "expiry_month": "2026-05"},
                {"id": 3, "expiry_month": "2025-12"},
                {"id": 4, "expiry_month": "invalid"},
            ],
            "assets": [],
            "feedback": [],
            "sterilization_cycles": [],
        }[entity]

        snapshot = dashboard_snapshot(store, "2026-01-15", datetime(2026, 1, 15))

        self.assertEqual([item["id"] for item in snapshot["expiring_batches"]], [1, 3])

    def test_emergency_mode_rejects_non_emergency_appointment_creation(self):
        app = Mock(spec=HospitalApp)
        app.user_name = "مدير"
        app.store = Mock()
        app.store.setting.return_value = "1"

        with self.assertRaisesRegex(ValueError, "وضع الطوارئ"):
            HospitalApp.prepare_record(
                app,
                "appts",
                {"patient": "مريض", "doctor": "طبيب", "priority": "موعد مسبق", "status": "بالانتظار"},
            )

    def test_registered_service_price_and_discount_are_used_for_invoice(self):
        app = Mock(spec=HospitalApp)
        app.store = Mock()
        app.store.list.side_effect = lambda entity: {
            "patients": [{"name": "مريض"}],
            "doctors": [],
            "service_prices": [{
                "service": "كشف",
                "cash_price": 100,
                "insurance_price": 80,
                "corporate_price": 70,
                "discount_percent": 10,
            }],
            "insurance": [],
        }.get(entity, [])

        bill = HospitalApp.prepare_record(
            app,
            "bills",
            {
                "patient": "مريض",
                "billing_type": "تعاقد شركات",
                "items_text": "كشف | 2",
                "paymentMethod": "نقدي",
                "status": "غير مدفوعة",
                "date": "2026-01-15",
            },
        )

        self.assertEqual(bill["items"][0]["unitPrice"], 63)
        self.assertEqual(bill["amount"], 126)

    def test_expiring_batch_is_saved_with_a_valid_month_and_existing_medicine(self):
        app = Mock(spec=HospitalApp)
        app.store = Mock()
        app.store.list.side_effect = lambda entity: (
            [{"name": "دواء"}] if entity == "meds" else []
        )

        batch = HospitalApp.prepare_record(
            app,
            "medication_batches",
            {
                "medicine": "دواء",
                "batch_number": "LOT-1",
                "quantity": "10",
                "expiry_month": "2027-03",
                "supplier": "المورد",
            },
        )

        self.assertEqual(batch["quantity"], 10)
        self.assertEqual(batch["expiry_month"], "2027-03")

    def test_insurance_claim_cannot_exceed_its_linked_invoice(self):
        app = Mock(spec=HospitalApp)
        app.store = Mock()
        app.store.get.return_value = {"id": 8, "patient": "مريض", "amount": 100}
        app.store.list.side_effect = lambda entity: (
            [{"name": "مريض"}] if entity == "patients" else []
        )

        with self.assertRaisesRegex(ValueError, "يتجاوز إجمالي الفاتورة"):
            HospitalApp.prepare_record(
                app,
                "insurance_claims",
                {
                    "company": "تأمين",
                    "patient": "مريض",
                    "bill_id": "8",
                    "amount": "101",
                    "approved_amount": "0",
                    "rejected_amount": "0",
                },
            )

    def test_financial_forecast_uses_prior_three_calendar_months(self):
        store = Mock()
        store.list.side_effect = lambda entity: (
            [
                {"date": "2025-10-10", "amount": 100},
                {"date": "2025-11-10", "amount": 200},
                {"date": "2025-12-10", "amount": 300},
                {"date": "2026-01-10", "amount": 10000},
            ] if entity == "bills" else
            [
                {"date": "2025-10", "net": 20},
                {"date": "2025-11", "net": 40},
                {"date": "2025-12", "net": 60},
            ]
        )

        forecast = financial_forecast(store, date(2026, 1, 15))

        self.assertEqual(forecast["revenue"], 200)
        self.assertEqual(forecast["payroll"], 40)

    def test_new_support_ticket_records_reporter_and_timestamp(self):
        app = Mock(spec=HospitalApp)
        app.user_name = "موظف الاستقبال"
        app.store = Mock()
        app.store.list.return_value = []

        ticket = HospitalApp.prepare_record(
            app,
            "support_tickets",
            {
                "title": "تعطل جهاز الأشعة",
                "category": "الأشعة",
                "description": "الجهاز لا يعمل في الطابق الأول",
                "priority": "عالية",
                "status": "جديدة",
                "assigned_to": "",
            },
        )

        self.assertEqual(ticket["reported_by"], "موظف الاستقبال")
        self.assertTrue(ticket["created_at"])

    def test_support_ticket_requires_title_and_description(self):
        app = Mock(spec=HospitalApp)
        app.user_name = "موظف"
        app.store = Mock()
        app.store.list.return_value = []

        with self.assertRaisesRegex(ValueError, "عنوان العطل مطلوب"):
            HospitalApp.prepare_record(
                app,
                "support_tickets",
                {"title": "", "description": "", "status": "جديدة"},
            )


if __name__ == "__main__":
    unittest.main()
