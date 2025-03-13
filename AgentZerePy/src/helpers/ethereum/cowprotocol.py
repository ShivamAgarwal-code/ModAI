import requests


class CowSwapClient:
    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url.rstrip("/")

    def create_swap_order(
        self, amount: str, token_address: str, operation: str
    ) -> dict:
        url = f"{self.base_url}/cowswap/create"
        payload = {
            "amount": amount,
            "tokenAddress": token_address,
            "operation": operation,
        }
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(response.json())
            return response.json()
        raise Exception(
            f"Failed to create swap order: {response.status_code} {response.text}"
        )

    def sign_swap_order(self, order_id: str) -> dict:
        url = f"{self.base_url}/cowswap/sign_order"
        payload = {"orderId": order_id}
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json()
        raise Exception(
            f"Failed to sign swap order: {response.status_code} {response.text}"
        )

    def get_orders(self) -> dict:
        url = f"{self.base_url}/cowswap/orders"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        raise Exception(f"Failed to get orders: {response.status_code} {response.text}")
