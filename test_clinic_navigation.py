import unittest
from unittest.mock import Mock, patch

from hospital_app import HospitalApp


class ClinicNavigationTests(unittest.TestCase):
    def setUp(self):
        self.app = Mock(spec=HospitalApp)
        self.app.store = Mock()
        self.app.selected_record.return_value = {"id": 12, "name": "عيادة العيون"}
        self.app.label_text.side_effect = lambda text: text

    def test_selected_clinic_opens_its_internal_page(self):
        self.app.can_view.return_value = True

        HospitalApp.open_selected_clinic(self.app)

        self.app.can_view.assert_called_once_with("clinic:12")
        self.app.show_page.assert_called_once_with("clinic:12")
        self.app.notify.assert_not_called()

    def test_clinic_page_link_respects_access_permissions(self):
        self.app.can_view.return_value = False

        HospitalApp.open_selected_clinic(self.app)

        self.app.show_page.assert_not_called()
        self.app.notify.assert_called_once_with("لا تملك صلاحية فتح هذه العيادة", "error")

    def test_no_selected_clinic_does_not_navigate(self):
        self.app.selected_record.return_value = None

        HospitalApp.open_selected_clinic(self.app)

        self.app.can_view.assert_not_called()
        self.app.show_page.assert_not_called()

    def test_booking_link_opens_appointment_form_for_selected_specialty(self):
        self.app.store.list.return_value = [
            {"id": 2, "specialty": "قلبية", "status": "مفتوحة"},
        ]
        self.app.store.list.side_effect = lambda entity: (
            [{"id": 2, "specialty": "قلبية", "status": "مفتوحة"}]
            if entity == "clinics"
            else [{"spec": "قلبية", "status": "نشط"}]
        )
        self.app.can_add.return_value = True
        captured_specialty = []
        self.app.open_form.side_effect = lambda page: captured_specialty.append(
            (page, self.app.clinic_booking_specialty)
        )

        HospitalApp.open_clinic_booking(self.app, "قلبية")

        self.assertEqual(captured_specialty, [("appts", "قلبية")])
        self.assertIsNone(self.app.clinic_booking_specialty)

    def test_donation_clinic_link_opens_donation_registration(self):
        self.app.store.list.side_effect = lambda entity: (
            [{"id": 13, "specialty": "تبرع بالدم", "status": "مفتوحة"}]
            if entity == "clinics"
            else []
        )
        self.app.can_add.return_value = True

        HospitalApp.open_clinic_booking(self.app, "تبرع بالدم")

        self.app.show_donation_form.assert_called_once_with()
        self.app.open_form.assert_not_called()

    def test_closed_clinic_rejects_booking(self):
        self.app.store.list.return_value = [
            {"id": 2, "specialty": "قلبية", "status": "مغلقة مؤقتاً"},
        ]

        HospitalApp.open_clinic_booking(self.app, "قلبية")

        self.app.open_form.assert_not_called()
        self.app.notify.assert_called_once()

    def test_clinic_booking_requires_permission(self):
        self.app.store.list.return_value = [
            {"id": 2, "specialty": "قلبية", "status": "مفتوحة"},
        ]
        self.app.can_add.return_value = False

        HospitalApp.open_clinic_booking(self.app, "قلبية")

        self.app.store.list.assert_called_once_with("clinics")
        self.app.open_form.assert_not_called()
        self.app.notify.assert_called_once()


if __name__ == "__main__":
    unittest.main()
