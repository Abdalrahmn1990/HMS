import tempfile
import unittest
from pathlib import Path

from hospital_app import HospitalStore


class UserAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = HospitalStore(Path(self.temp_dir.name) / "hospital.sqlite")

    def tearDown(self):
        self.store.close()
        self.temp_dir.cleanup()

    def test_accounts_start_empty_and_passwords_are_stored_as_salted_hashes(self):
        self.assertEqual(self.store.account_count(), 0)

        self.store.create_user("admin-user", "مدير النظام", "admin", "a-long-test-password")

        self.assertEqual(
            self.store.authenticate_user("ADMIN-USER", "a-long-test-password"),
            {"username": "admin-user", "name": "مدير النظام", "role": "admin"},
        )
        self.assertIsNone(self.store.authenticate_user("admin-user", "wrong-password"))
        row = self.store.connection.execute(
            "SELECT salt, password_hash FROM user_accounts WHERE username='admin-user'"
        ).fetchone()
        self.assertNotEqual(row["salt"], row["password_hash"])
        self.assertNotIn(b"a-long-test-password", row["password_hash"])

    def test_account_creation_rejects_weak_passwords_and_unknown_roles(self):
        with self.assertRaisesRegex(ValueError, "12 حرفاً"):
            self.store.create_user("short-pass", "اسم", "admin", "1234")
        with self.assertRaisesRegex(ValueError, "الدور"):
            self.store.create_user("bad-role", "اسم", "billing", "a-long-test-password")

    def test_multiple_accounts_are_created_in_one_atomic_operation(self):
        accounts = [
            {"username": f"staff{index}", "display_name": f"موظف {index}", "role": "reception", "password": "shared-long-password"}
            for index in range(1, 6)
        ]

        self.store.create_users(accounts)

        self.assertEqual(self.store.account_count(), 5)
        for index in range(1, 6):
            self.assertIsNotNone(
                self.store.authenticate_user(f"staff{index}", "shared-long-password")
            )

    def test_duplicate_name_in_bulk_batch_does_not_create_partial_accounts(self):
        accounts = [
            {"username": "staff1", "display_name": "موظف 1", "role": "doctor", "password": "shared-long-password"},
            {"username": "STAFF1", "display_name": "موظف 2", "role": "doctor", "password": "shared-long-password"},
        ]

        with self.assertRaisesRegex(ValueError, "مكرر"):
            self.store.create_users(accounts)

        self.assertEqual(self.store.account_count(), 0)

    def test_duplicate_usernames_are_rejected_case_insensitively(self):
        self.store.create_user("admin-user", "مدير", "admin", "a-long-test-password")

        with self.assertRaisesRegex(ValueError, "مستخدم بالفعل"):
            self.store.create_user("ADMIN-USER", "مدير آخر", "admin", "another-long-password")

    def test_inactive_accounts_cannot_authenticate_and_last_admin_stays_active(self):
        self.store.create_user("root-user", "مدير", "admin", "a-long-test-password")
        self.store.create_user("doctor-user", "طبيب", "doctor", "another-long-password")

        with self.assertRaisesRegex(ValueError, "آخر حساب مدير"):
            self.store.set_user_active("root-user", False, "مدير")
        self.store.set_user_active("doctor-user", False, "مدير")

        self.assertIsNone(self.store.authenticate_user("doctor-user", "another-long-password"))
        self.assertEqual(self.store.authenticate_user("root-user", "a-long-test-password")["role"], "admin")

    def test_password_reset_invalidates_the_previous_password(self):
        self.store.create_user("admin-user", "مدير النظام", "admin", "a-long-test-password")

        self.store.change_user_password("admin-user", "a-new-long-password", "مدير النظام")

        self.assertIsNone(self.store.authenticate_user("admin-user", "a-long-test-password"))
        self.assertIsNotNone(self.store.authenticate_user("admin-user", "a-new-long-password"))

    def test_inactive_account_can_be_reactivated(self):
        self.store.create_user("doctor-user", "طبيب", "doctor", "another-long-password")
        self.store.set_user_active("doctor-user", False, "مدير")

        self.assertIsNone(self.store.authenticate_user("doctor-user", "another-long-password"))

        self.store.set_user_active("doctor-user", True, "مدير")

        self.assertIsNotNone(self.store.authenticate_user("doctor-user", "another-long-password"))

    def test_accounts_can_be_deleted_but_last_active_admin_cannot(self):
        self.store.create_user("root-user", "مدير", "admin", "a-long-test-password")
        self.store.create_user("doctor-user", "طبيب", "doctor", "another-long-password")

        self.store.delete_user("doctor-user", "مدير")
        self.assertIsNone(self.store.authenticate_user("doctor-user", "another-long-password"))

        with self.assertRaisesRegex(ValueError, "آخر حساب مدير"):
            self.store.delete_user("root-user", "مدير")

        self.store.create_user("second-admin", "مدير ثان", "admin", "third-long-password")
        self.store.delete_user("root-user", "مدير ثان")
        self.assertIsNone(self.store.authenticate_user("root-user", "a-long-test-password"))


if __name__ == "__main__":
    unittest.main()
