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

def test_product_etag_conditional_get():
    client = APIClient()
    client.login()

    category_id = create_category(client)
    product_id = create_product(client, category_id)

    resp1 = client.get(f"/products/{product_id}/")
    assert resp1.status_code == 200, resp1.text

    etag = resp1.headers.get("ETag")
    assert etag is not None, "ETag header missing in response"

    resp2 = client.session.get(
        f"{BASE_URL}/products/{product_id}/",
        headers={
            "If-None-Match": etag,
        },
    )

    assert resp2.status_code == 304, resp2.text

    print(resp2.status_code)
    assert resp2.text == "" or resp2.content == b"", "304 response must not contain body"

    print("ETag conditional GET test passed")



if __name__ == "__main__":
    test_product_etag_conditional_get()
    print("etag test passed")