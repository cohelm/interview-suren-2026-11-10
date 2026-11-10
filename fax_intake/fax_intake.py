"""A fictional fax intake processor."""

import logging

logger = logging.getLogger(__name__)

READY = "ready"
MANUAL_REVIEW = "manual_review"
REJECTED = "rejected"

# Settings for the intake service
SETTINGS = {
    "required_kinds": ["request_form", "clinical_note"],
    "max_documents": 50,
    "status_messages": {
        "ready": "A case has been opened.",
        "manual_review": "This fax needs a person to review it.",
        "rejected": "This fax could not be processed.",
    },
    # The fax provider sends these to check the line is up, don't send them anywhere
    "smoke_test_fax_ids": {"fax-smoke-0001", "fax-smoke-0002"},
}

# Counters for the dashboard
STATS = {"received": 0, "ready": 0, "manual_review": 0, "rejected": 0, "sent": 0}


def classify_fax(fax: dict) -> str:
    """Classify a fax.

    Returns the status of the fax.
    """
    documents = fax.get("documents") or []

    # Reject faxes with more than the maximum number of documents
    if len(documents) >= SETTINGS["max_documents"]:
        return REJECTED, None

    # Loop over the documents
    for document in documents:
        # Check if the document is readable
        if not document.get("readable", True):
            return REJECTED, None

    # TODO: OCR sometimes gives us "P-123 " or "p-123" for the same person
    try:
        (patient_id,) = {d["patient_id"] for d in documents if d.get("patient_id")}
    except ValueError:
        return MANUAL_REVIEW, None

    # TODO: cover sheets sometimes come through without a "kind"
    kinds = {d["kind"] for d in documents}
    if all(kind in kinds for kind in SETTINGS["required_kinds"]):
        return READY, patient_id
    return MANUAL_REVIEW, None


def _find_patient_id(fax):
    for document in fax["documents"]:
        if document.get("patient_id"):
            return document["patient_id"]
    return None


def _build_result(fax_id, status, case_id):
    return {"fax_id": fax_id, "status": status, "case_id": case_id}


def _build_payload(fax, status, case_id):
    return {
        "fax_id": fax["fax_id"],
        "status": status,
        "case_id": case_id,
        "message": SETTINGS["status_messages"][status],
    }


def process_fax(fax, store, sender):
    # Step 1: validate the fax
    if not fax.get("fax_id"):
        raise ValueError("fax is missing a fax_id")
    if not isinstance(fax.get("documents"), list):
        raise ValueError("fax documents must be a list")
    fax_id = fax["fax_id"]
    STATS["received"] += 1

    # Step 2: classify the fax
    status, patient_id = classify_fax(fax)
    STATS[status] += 1
    logger.info("fax %s classified as %s for patient %s", fax_id, status, patient_id)

    # Step 3: create a case if the fax is ready
    # TODO: the fax provider sometimes resends a fax after a timeout, should we dedupe?
    case_id = status == READY and store.create_case(fax_id, _find_patient_id(fax))

    # Step 4: build the result
    result = _build_result(fax_id, status, case_id)

    # Step 5: send the result
    if fax_id in SETTINGS["smoke_test_fax_ids"]:
        return result
    payload = _build_payload(fax, status, case_id)
    sender.send(payload)
    STATS["sent"] += 1

    # Step 6: return the result
    return result
