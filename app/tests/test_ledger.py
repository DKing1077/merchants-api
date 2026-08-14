
def create_account(client, name, account_type, currency="usd"):
    response = client.post(
        "/v1/ledger/accounts",
        json={"name": name, "account_type": account_type, "currency": currency},
    )
    assert response.status_code == 200
    return response.json()


def create_entry(client, reference_id, postings, entry_type="payment"):
    return client.post(
        "/v1/ledger/entries",
        json={
            "entry_type": entry_type,
            "reference_id": reference_id,
            "postings": postings,
        },
    )


def test_get_account_balance_includes_metadata(client):
    cash = create_account(client, "Cash", "cash")
    payable = create_account(client, "Payable", "merchant_payable")
    create_entry(
        client,
        "entry-1",
        [
            {"account_id": cash["id"], "amount": 500, "currency": "usd"},
            {"account_id": payable["id"], "amount": -500, "currency": "usd"},
        ],
    )

    response = client.get(f"/v1/ledger/accounts/{cash['id']}/balance")
    assert response.status_code == 200
    body = response.json()
    assert body["account_id"] == cash["id"]
    assert body["name"] == "Cash"
    assert body["balance"] == 500


def test_account_entries_include_postings_and_pagination(client):
    cash = create_account(client, "Cash", "cash")
    payable = create_account(client, "Payable", "merchant_payable")
    first = create_entry(
        client,
        "entry-1",
        [
            {"account_id": cash["id"], "amount": 100, "currency": "usd"},
            {"account_id": payable["id"], "amount": -100, "currency": "usd"},
        ],
    ).json()
    second = create_entry(
        client,
        "entry-2",
        [
            {"account_id": cash["id"], "amount": 200, "currency": "usd"},
            {"account_id": payable["id"], "amount": -200, "currency": "usd"},
        ],
    ).json()

    response = client.get(f"/v1/ledger/accounts/{cash['id']}/entries?limit=1")
    assert response.status_code == 200
    body = response.json()
    assert body["has_more"] is True
    assert body["data"][0]["id"] == second["id"]
    assert len(body["data"][0]["postings"]) == 2

    next_page = client.get(
        f"/v1/ledger/accounts/{cash['id']}/entries?limit=1&starting_after={second['id']}"
    )
    assert next_page.status_code == 200
    assert next_page.json()["data"][0]["id"] == first["id"]


def test_balance_sheet_groups_accounts(client):
    cash = create_account(client, "Cash", "cash")
    payable = create_account(client, "Payable", "merchant_payable")
    create_entry(
        client,
        "entry-1",
        [
            {"account_id": cash["id"], "amount": 300, "currency": "usd"},
            {"account_id": payable["id"], "amount": -300, "currency": "usd"},
        ],
    )

    response = client.get("/v1/ledger/merchant/merchant_1/balance_sheet")
    assert response.status_code == 200
    body = response.json()
    assert {group["account_type"] for group in body} == {"cash", "merchant_payable"}


def test_prevent_duplicate_ledger_entries(client):
    cash = create_account(client, "Cash", "cash")
    payable = create_account(client, "Payable", "merchant_payable")
    postings = [
        {"account_id": cash["id"], "amount": 100, "currency": "usd"},
        {"account_id": payable["id"], "amount": -100, "currency": "usd"},
    ]
    first = create_entry(client, "duplicate-ref", postings)
    second = create_entry(client, "duplicate-ref", postings)
    assert first.status_code == 200
    assert second.status_code == 409
