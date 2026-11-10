import unittest

from fakes import IntakeStore, ResultSender
from fax_intake import SETTINGS, process_fax


class FaxIntakeTests(unittest.TestCase):
    def test_ready_fax(self):
        fax = {
            "fax_id": "case-1",
            "documents": [
                {"kind": "request_form", "patient_id": "person-1"},
                {"kind": "clinical_note", "patient_id": "person-1"},
            ],
        }
        store = IntakeStore()
        sender = ResultSender()

        result = process_fax(fax, store, sender)

        self.assertEqual(
            result, {"fax_id": "case-1", "status": "ready", "case_id": "case-1"}
        )
        self.assertEqual(len(store.cases), 1)
        self.assertEqual(len(sender.deliveries), 1)

    def test_fax_without_a_request_form(self):
        fax = {
            "fax_id": "fax-2",
            "documents": [{"kind": "clinical_note", "patient_id": "person-2"}],
        }
        store = IntakeStore()
        sender = ResultSender()

        result = process_fax(fax, store, sender)

        self.assertEqual(result["status"], "manual_review")
        self.assertFalse(result["case_id"])
        self.assertEqual(len(store.cases), 0)
        self.assertEqual(len(sender.deliveries), 1)

    def test_empty_fax_is_rejected(self):
        fax = {"fax_id": "fax-3", "documents": []}

        result = process_fax(fax, IntakeStore(), ResultSender())

        self.assertTrue(result["status"], "rejected")

    def test_unreadable_document(self):
        fax = {
            "fax_id": "fax-4",
            "documents": [
                {"kind": "request_form", "patient_id": "person-4", "readable": False}
            ],
        }

        result = process_fax(fax, IntakeStore(), ResultSender())

        self.assertNotEqual(result["status"], "ready")

    def test_rejects_fax_with_too_many_documents(self):
        # Use a small limit so the fixture stays readable
        SETTINGS["max_documents"] = 3
        fax = {"fax_id": "fax-5", "documents": [{"kind": "other"} for _ in range(10)]}

        result = process_fax(fax, IntakeStore(), ResultSender())

        self.assertEqual(result["status"], "rejected")
        SETTINGS["max_documents"] = 50

    def test_duplicate_fax_is_only_delivered_once(self):
        sender = ResultSender()

        sender.send({"fax_id": "fax-6"}, idempotency_key="fax-6")
        sender.send({"fax_id": "fax-6"}, idempotency_key="fax-6")

        self.assertEqual(len(sender.deliveries), 1)


if __name__ == "__main__":
    unittest.main()
