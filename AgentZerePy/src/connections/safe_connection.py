import logging
from typing import Any, Dict
from src.connections.base_connection import BaseConnection, Action, ActionParameter
from src.helpers.ethereum.safe import SafeClient

logger = logging.getLogger("connections.safe")


class SafeConnection(BaseConnection):
    def __init__(self, config):
        self.client = SafeClient(config.get("base_url", "http://localhost:3000"))
        super().__init__(config)

    @property
    def is_llm_provider(self):
        return False

    def validate_config(self, config) -> Dict[str, Any]:
        if "base_url" in config and not isinstance(config["base_url"], str):
            raise ValueError("base_url must be a string")
        return config

    def configure(self, **kwargs) -> bool:
        if "base_url" in kwargs:
            self.client = SafeClient(kwargs["base_url"])
        return True

    def is_configured(self, verbose=False) -> bool:
        return True

    def register_actions(self) -> None:
        self.actions = {
            "check-status": Action(
                name="check-status",
                parameters=[
                    ActionParameter(
                        "safe_tx_hash", True, str, "Safe transaction hash to check"
                    )
                ],
                description="Check Safe transaction status",
            ),
            "get-balances": Action(
                name="get-balances",
                parameters=[],
                description="Get Safe balances including native token and ERC20 tokens",
            ),
            "confirm-transaction": Action(
                name="confirm-transaction",
                parameters=[
                    ActionParameter(
                        "signer", True, str, "Private key or signer for the Safe owner"
                    ),
                    ActionParameter(
                        "safe_address", True, str, "Address of the Safe contract"
                    ),
                    ActionParameter(
                        "safe_tx_hash",
                        True,
                        str,
                        "Hash of the Safe transaction to confirm",
                    ),
                ],
                description="Confirm a pending Safe transaction",
            ),
            "create-transaction": Action(
                name="create-transaction",
                parameters=[
                    ActionParameter(
                        "to", True, str, "Destination address for the transaction"
                    ),
                    ActionParameter("value", True, str, "ETH value in wei"),
                    ActionParameter("data", True, str, "Transaction data (hex)"),
                ],
                description="Create and sign a Safe transaction",
            ),
        }

    def perform_action(self, action_name: str, kwargs) -> Any:
        if action_name not in self.actions:
            raise KeyError(f"Unknown action: {action_name}")

        action = self.actions[action_name]
        errors = action.validate_params(kwargs)
        if errors:
            raise ValueError(f"Invalid parameters: {', '.join(errors)}")

        method_name = action_name.replace("-", "_")
        method = getattr(self, method_name)
        return method(**kwargs)

    def check_status(self, safe_tx_hash: str) -> Dict:
        try:
            return self.client.check_status(safe_tx_hash)
        except Exception as e:
            logger.error(f"Failed to check status: {str(e)}")
            return None

    def get_balances(self) -> Dict:
        try:
            return self.client.get_balances()
        except Exception as e:
            logger.error(f"Failed to get balances: {str(e)}")
            return None

    def confirm_transaction(
        self, signer: str, safe_address: str, safe_tx_hash: str
    ) -> Dict:
        try:
            return self.client.confirm_transaction(signer, safe_address, safe_tx_hash)
        except Exception as e:
            logger.error(f"Failed to confirm transaction: {str(e)}")
            return None

    def create_transaction(self, to: str, value: str, data: str) -> Dict:
        try:
            return self.client.create_transaction(to, value, data)
        except Exception as e:
            logger.error(f"Failed to create transaction: {str(e)}")
            return None
