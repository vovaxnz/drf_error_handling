import requests
import uuid

BASE_URL = "http://localhost:8000/api/v1"
USERNAME = "admin"
EMAIL = "admin@example.com"
PASSWORD = "admin"


class APIClient:
    def __init__(self):
        self.session = requests.Session()

    def login(self):
        resp = self.session.post(
            f"{BASE_URL}/auth/login/",
            json={
                "username": USERNAME,
                "email": EMAIL,
                "password": PASSWORD,
            },
            # headers={"X-Forwarded-Proto": "https"}
            # headers={"Idempotency-Key": str(uuid.uuid4())}
        )
        assert resp.status_code == 200, resp.text
        token = resp.json()["access"]
        self.session.headers.update({
            "Authorization": f"Bearer {token}"
        })

    def post(self, path, json=None, idempotency_key=None):
        headers = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
            # headers["X-Forwarded-Proto"] = "https" # Witout https idempotency not working, this patch allows use http
        return self.session.post(f"{BASE_URL}{path}", json=json, headers=headers)

    def get(self, path):
        return self.session.get(f"{BASE_URL}{path}")


def create_category(client):
    resp = client.post("/product-categories/", json={
        "name": f"Category-{uuid.uuid4()}",
        "parent": None,
    })
    assert resp.status_code == 201
    return resp.json()["id"]


def create_product(client, category_id):
    resp = client.post("/products/", json={
        "category": category_id,
        "title": "Idempotent Product",
        "description": "",
        "sku": f"SKU-{uuid.uuid4()}",
        "product_url": "",
        "image_url": "",
        "price_amount": "50.00",
        "attributes": {},
        "embedding_ref": "",
        "is_active": True,
    })
    assert resp.status_code == 201
    return resp.json()["id"]


def test_idempotent_payment_creation():
    client = APIClient()
    client.login()

    user_id = client.get("/auth/user/").json()["pk"]

    # створюємо quote -> order
    category_id = create_category(client)
    product_id = create_product(client, category_id)

    quote_resp = client.post("/quotes/", json={
        "client": user_id,
        "status": "draft",
    })
    quote_id = quote_resp.json()["id"]

    # якщо у вас є endpoint quote-items
    client.post("/quote-items/", json={
        "quote": quote_id,
        "product": product_id,
        "quantity": 1,
        "unit_price": "50.00",
        "currency": "USD",
    })

    client.post(f"/quotes/{quote_id}/send/")
    accept_resp = client.post(f"/quotes/{quote_id}/accept/")
    order_id = accept_resp.json()["order_id"]

    idempotency_key = str(uuid.uuid4())

    payload = {
        "order": order_id,
        "amount": "50.00",
        "currency": "USD",
        "provider": "dummy",
    }

    # перший виклик
    resp1 = client.post(
        "/payments/",
        json=payload,
        idempotency_key=idempotency_key,
    )
    assert resp1.status_code == 201, resp1.text
    payment_id_1 = resp1.json()["id"]

    # другий виклик з тим самим ключем
    resp2 = client.post(
        "/payments/",
        json=payload,
        idempotency_key=idempotency_key,
    )

    # очікувана поведінка:
    # або 200 з тим самим payment id
    # або 409 conflict
    assert resp2.status_code in (200, 201, 409), resp2.text

    if resp2.status_code in (200, 201):
        payment_id_2 = resp2.json()["id"]
        assert payment_id_1 == payment_id_2, "Idempotency failed: different resource created"



if __name__ == "__main__":
    test_idempotent_payment_creation()
    print("Idempotency test passed")