"""In-memory stand-ins for the intake database and the downstream receiver."""


class IntakeStore:
    def __init__(self):
        self.cases = []
        self.outcomes = {}

    def create_case(self, fax_id, patient_id):
        case_id = f"case-{len(self.cases) + 1}"
        self.cases.append(
            {"case_id": case_id, "fax_id": fax_id, "patient_id": patient_id}
        )
        return case_id

    def get_outcome(self, fax_id):
        result = self.outcomes.get(fax_id)
        if result is None:
            return None
        return result.copy()

    def save_outcome(self, result):
        self.outcomes[result["fax_id"]] = result.copy()


class ResultSender:
    def __init__(self):
        self.deliveries = []
        self.delivered_keys = set()
        self.fail_before_delivery_once = False
        self.fail_after_delivery_once = False

    def send(self, result, idempotency_key=None):
        if idempotency_key in self.delivered_keys:
            return
        if self.fail_before_delivery_once:
            self.fail_before_delivery_once = False
            raise OSError("delivery failed")

        self.deliveries.append(result.copy())
        if idempotency_key is not None:
            self.delivered_keys.add(idempotency_key)

        if self.fail_after_delivery_once:
            self.fail_after_delivery_once = False
            raise OSError("delivery status unknown")
