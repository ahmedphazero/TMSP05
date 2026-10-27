import io
from datetime import date, timedelta

import pytest

from app import create_app

GOOD_FILE = lambda name: (io.BytesIO(b"%PDF-1.4 test"), name)


@pytest.fixture()
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    return app.test_client()


def good_form(**over):
    data = {
        "extin": "EX12345", "category": "returned",
        "period_from": "2026-01-01", "period_to": "2026-01-31",
        "amount": "1500.500", "invoices": "INV-1, INV-2",
        "commercial_invoice": GOOD_FILE("invoice.pdf"),
        "payment_receipt": GOOD_FILE("receipt.pdf"),
    }
    data.update(over)
    return data


def post(client, **over):
    return client.post("/", data=good_form(**over), content_type="multipart/form-data")


def test_form_loads(client):
    assert client.get("/").status_code == 200


def test_valid_application_succeeds(client):
    r = post(client)
    assert r.status_code == 200
    assert b"Success" in r.data


def test_missing_document_reported(client):
    r = post(client, payment_receipt=(io.BytesIO(b""), ""))
    assert r.status_code == 422
    assert b"Missing required document: Excise payment receipt" in r.data


def test_all_problems_reported_together(client):
    r = post(client, extin="", amount="-5", invoices="")
    assert r.status_code == 422
    assert b"EXTIN" in r.data and b"greater than zero" in r.data and b"invoice reference" in r.data


def test_bad_period(client):
    r = post(client, period_from="2026-02-10", period_to="2026-02-01")
    assert b"on or after the start" in r.data


def test_future_period(client):
    future = (date.today() + timedelta(days=30)).isoformat()
    r = post(client, period_to=future)
    assert b"cannot be in the future" in r.data


def test_bad_file_type(client):
    r = post(client, payment_receipt=(io.BytesIO(b"x"), "receipt.exe"))
    assert b"not allowed" in r.data


def test_exact_duplicate_rejected(client):
    assert post(client).status_code == 200
    r = post(client)
    assert r.status_code == 422
    assert b"duplicate" in r.data


def test_reused_invoice_rejected(client):
    assert post(client).status_code == 200
    r = post(client, amount="99", invoices="INV-2, INV-9")
    assert r.status_code == 422
    assert b"already used" in r.data
