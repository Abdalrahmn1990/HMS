import tempfile
import unittest
from pathlib import Path

from hospital_app import DEMO_MEDICATION_CATALOG, HospitalStore


class DemoMedicationSeedTests(unittest.TestCase):
    def test_seeds_one_hundred_labeled_demo_medicines_once(self):
        catalog_size = sum(len(names) for _category, names in DEMO_MEDICATION_CATALOG)
        self.assertEqual(catalog_size, 100)

        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "hospital.sqlite"
            store = HospitalStore(database)
            seeded = [item for item in store.list("meds") if item.get("sample_data")]
            names = [item["name"] for item in seeded]

            self.assertEqual(len(seeded), 100)
            self.assertEqual(len(names), len(set(names)))
            self.assertTrue(all(item.get("data_source") == "بيانات تجريبية" for item in seeded))
            self.assertTrue(all(item.get("price") == 0 for item in seeded))
            self.assertTrue(all(item.get("min_qty") == 10 for item in seeded))
            self.assertEqual(len(store.list("meds")), 103)
            store.close()

            reopened = HospitalStore(database)
            self.assertEqual(len([item for item in reopened.list("meds") if item.get("sample_data")]), 100)
            self.assertEqual(len(reopened.list("meds")), 103)
            reopened.close()

    def test_existing_medicine_records_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "hospital.sqlite"
            store = HospitalStore(database)
            existing = next(item for item in store.list("meds") if item["name"] == "باراسيتامول")
            store.save("meds", {
                "id": 0,
                "name": "دواء أضافه المستخدم",
                "cat": "مخصص",
                "qty": 7,
                "price": 25,
                "status": "متوفر",
            }, "اختبار")
            store.close()

            reopened = HospitalStore(database)
            self.assertEqual(reopened.get("meds", existing["id"])["name"], "باراسيتامول")
            custom = next(item for item in reopened.list("meds") if item["name"] == "دواء أضافه المستخدم")
            self.assertEqual(custom["qty"], 7)
            self.assertEqual(custom["price"], 25)
            reopened.close()

    def test_legacy_backup_gets_optional_entities_and_inventory_thresholds(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "hospital.sqlite"
            store = HospitalStore(database)
            backup = store.export_data()
            backup.pop("attendance")
            backup.pop("messages")
            backup.pop("support_tickets")
            for entity in (
                "medication_batches",
                "insurance_claims",
                "assets",
                "sterilization_cycles",
                "feedback",
                "service_prices",
            ):
                backup.pop(entity)
            for medicine in backup["meds"]:
                medicine.pop("min_qty", None)
            backup["settings"].pop("inventory_minimum_threshold_v1", None)

            store.import_data(backup, "اختبار")

            self.assertEqual(store.list("attendance"), [])
            self.assertEqual(store.list("messages"), [])
            self.assertEqual(store.list("support_tickets"), [])
            self.assertEqual(store.list("medication_batches"), [])
            self.assertEqual(store.list("insurance_claims"), [])
            self.assertEqual(store.list("assets"), [])
            self.assertEqual(store.list("sterilization_cycles"), [])
            self.assertEqual(store.list("feedback"), [])
            self.assertEqual(store.list("service_prices"), [])
            self.assertTrue(all(item.get("min_qty") == 10 for item in store.list("meds")))
            store.close()


if __name__ == "__main__":
    unittest.main()
