import requests
from typing import Dict, Optional, Any


class SafeClient:
    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Content-Type": "application/json"}

    def check_status(self, safe_tx_hash: str) -> Dict:
        """
        Check Safe transaction status

        Args:
            safe_tx_hash: Safe transaction hash to check

        Returns:
            Dict with status (pending/unknown) and transaction details
        """
        url = f"{self.base_url}/safe/status"
        params = {"safeTxHash": safe_tx_hash}

        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_balances(self) -> Dict:
        """
        Get Safe balances including native token and ERC20 tokens

        Returns:
            Dict containing Safe address and token balances
        """
        url = f"{self.base_url}/safe/balance"

        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def confirm_transaction(
        self, signer: str, safe_address: str, safe_tx_hash: str
    ) -> Dict:
        """
        Confirm a pending Safe transaction

        Args:
            signer: Private key or signer for the Safe owner
            safe_address: Address of the Safe contract
            safe_tx_hash: Hash of the Safe transaction to confirm

        Returns:
            Dict containing confirmation result
        """
        url = f"{self.base_url}/safe/confirm"
        payload = {
            "signer": signer,
            "safeAddress": safe_address,
            "safeTxHash": safe_tx_hash,
        }

        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def create_transaction(self, to: str, value: str, data: str) -> Dict:
        """
        Create and sign a Safe transaction

        Args:
            to: Destination address for the transaction
            value: ETH value in wei
            data: Transaction data (hex)

        Returns:
            Dict containing transaction details and signature
        """
        url = f"{self.base_url}/safe/create_tx"
        payload = {
            "to": to,
            "value": value,
            "data": data,
        }

        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()
        return response.json()
