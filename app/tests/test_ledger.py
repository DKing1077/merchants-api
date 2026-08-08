import pytest


BALANCED_POSTINGS = [
    {"account_id": "acc_revenue", "amount": -1000, "currency": "usd"},
    {"account_id": "acc_receivable", "amount": 1000, "currency": "usd"},
]


def create_entry(client, entry_type="payment", postings=None, **kwargs):
    payload = {
        "entry_type": entry_type,
        "postings": postings or BALANCED_POSTINGS,
        **kwargs,
    }
    return client.post("/v1/ledger/entries", json=payload)


# ---------------------------------------------------------------------------
# Create ledger entry
# ---------------------------------------------------------------------------


def test_create_ledger_entry(client):
    response = create_entry(client)
    assert response.status_code == 200
    body = response.json()
    assert body["entry_type"] == "payment"
    assert "id" in body
    assert "created_at" in body


def test_create_ledger_entry_with_metadata(client):
    response = create_entry(
        client,
        entry_type="fee",
        reference_id="ref_123",
        description="processing fee",
        entry_metadata={"source": "stripe"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["reference_id"] == "ref_123"
    assert body["description"] == "processing fee"
    assert body["entry_metadata"] == {"source": "stripe"}


def test_create_ledger_entry_unbalanced_postings(client):
    unbalanced = [
        {"account_id": "acc_a", "amount": 500, "currency": "usd"},
        {"account_id": "acc_b", "amount": 200, "currency": "usd"},
    ]
    response = create_entry(client, postings=unbalanced)
    assert response.status_code == 400


def test_create_ledger_entry_single_posting(client):
    single = [{"account_id": "acc_a", "amount": 500, "currency": "usd"}]
    response = create_entry(client, postings=single)
    assert response.status_code == 400


def test_create_ledger_entry_missing_postings(client):
    response = client.post("/v1/ledger/entries", json={"entry_type": "payment"})
    assert response.status_code == 422


def test_create_ledger_entry_invalid_currency(client):
    bad_postings = [
        {"account_id": "acc_a", "amount": -100, "currency": "us"},
        {"account_id": "acc_b", "amount": 100, "currency": "us"},
    ]
    response = create_entry(client, postings=bad_postings)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Account balance
# ---------------------------------------------------------------------------


def test_get_account_balance_zero_for_unknown_account(client):
    response = client.get("/v1/ledger/accounts/acc_unknown/balance")
    assert response.status_code == 200
    body = response.json()
    assert body["account_id"] == "acc_unknown"
    assert body["balance"] == 0


def test_get_account_balance_after_postings(client):
    postings = [
        {"account_id": "acc_test", "amount": -500, "currency": "usd"},
        {"account_id": "acc_other", "amount": 500, "currency": "usd"},
    ]
    create_entry(client, postings=postings)
    response = client.get("/v1/ledger/accounts/acc_test/balance")
    assert response.status_code == 200
    assert response.json()["balance"] == -500


def test_get_account_balance_multiple_entries(client):
    postings_a = [
        {"account_id": "acc_x", "amount": 300, "currency": "usd"},
        {"account_id": "acc_y", "amount": -300, "currency": "usd"},
    ]
    postings_b = [
        {"account_id": "acc_x", "amount": 200, "currency": "usd"},
        {"account_id": "acc_y", "amount": -200, "currency": "usd"},
    ]
    create_entry(client, postings=postings_a)
    create_entry(client, postings=postings_b)
    response = client.get("/v1/ledger/accounts/acc_x/balance")
    assert response.status_code == 200
    assert response.json()["balance"] == 500
