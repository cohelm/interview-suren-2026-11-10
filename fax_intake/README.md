# Fax intake exercise

You will review a small Python service, make one of its operations safe to
retry, and then discuss the limits of your change.

## What we look for

We care about how you reason as much as about the final patch.

- **Code review:** you find the problems that matter, share your opinions on
  design and style, and explain which findings would block the pull request.
- **Retry safety:** you can make an operation with side effects safe to retry,
  and say what happens if it fails at any step.
- **Testing:** your tests fail when the code is wrong, and you spot existing
  tests that would not.
- **Judgment:** you choose what to fix now and what to leave for later, you
  check what your tools tell you before you rely on it, and you can explain
  why.

## Task

The session is 60 minutes: about 15 to review, 30 to make the change, and 15 to
discuss. Think out loud as you go.

Use any editor, docs, or LLM you like. Share your screen throughout the session.
If you use an LLM, include your prompts and its responses so we can see how you
guide it and check what it tells you.

1. **Review.** Open the exercise pull request, `exercise/fax-intake` into
   `master`. Review its implementation, tests, and description as an
   LLM-generated contribution from a teammate, checking them against the spec
   below. Talk us through what you would flag, most important first. You do not
   need to write it down.
2. **Make retries safe.** Assume calls are sequential and a fax ID always has
   the same content. Change `process_fax` so that:
   - repeating a fax ID returns the same result, creates at most one case, and
     delivers at most one result, whatever the status
   - if sending raises before or after delivery, the error reaches the caller.
     A later retry returns the recorded outcome, creates no new case, and
     leaves exactly one delivered result
   - the sender gets the fax ID as its idempotency key.

   Add tests for this, including the failure cases, and fix any existing tests
   you don't trust. You do not need to fix everything you flagged in the
   review. Create your own branch from `exercise/fax-intake`, push your changes,
   and open a pull request targeting `exercise/fax-intake` (see below).
3. **Discuss.** What does your change guarantee, and what doesn't it? How would
   it hold up with concurrent workers, process restarts, or a fax ID reused with
   different content?

## Spec

A fax is a dictionary like this:

```python
{
    "fax_id": "fax-1",
    "documents": [
        {"kind": "request_form", "patient_id": "person-1", "readable": True},
        {"kind": "clinical_note", "patient_id": "person-1"},
        {"kind": "other"},
    ],
}
```

Every document has a `kind`: `request_form`, `clinical_note`, or `other`.
`patient_id` is optional. `readable` is also optional: an omitted field means
the document is readable, as with the second and third documents above. Set
`"readable": False` for a document that could not be read; any such document
makes the fax `rejected`.

`classify_fax` returns a status and, for a ready fax, its patient ID:

- `ready`: the fax has a request form, a clinical note, and exactly one distinct
  patient ID across its documents (documents without one are fine)
- `manual_review`: a person must resolve missing or conflicting information
- `rejected`: the fax is empty, has an unreadable document, or has more than
  `max_documents` documents (set in `SETTINGS`).

`rejected` takes priority over `manual_review`.

`process_fax` creates a case for a ready fax, sends a result for every fax, and
returns the same result it sent. A result has a `fax_id`, a `status`, and a
`case_id`, which is `None` when no case was created.

`IntakeStore` and `ResultSender` in `fakes.py` stand in for a database and a
downstream service. Rely on them as written. You do not need to review or
change them.

- The store keeps cases and outcomes across calls. Its writes never fail.
- The sender records deliveries. It ignores a send whose `idempotency_key` it
  has already delivered.
- `send` can raise `OSError` before delivery, or after the receiver has stored
  the result but before its acknowledgment arrives. In the second case the
  caller cannot tell that delivery happened. `fail_before_delivery_once` and
  `fail_after_delivery_once` simulate these two cases.

## Run the tests

Use Python 3.9 or newer. There is nothing to install.

```sh
cd fax_intake
python3 -m unittest -v
```

## Submit your changes

The default branch is `exercise/fax-intake`, so a fresh clone already contains
the code to review. From the repository root, create your own branch:

```sh
git switch -c candidate/fixes
```

After making and committing your changes:

```sh
git push -u origin candidate/fixes
gh pr create --base exercise/fax-intake
```

You can also open the pull request in GitHub: choose `exercise/fax-intake` as
the base and `candidate/fixes` as the compare branch. Your pull request should
show only your changes. The exercise pull request stays open for review.
