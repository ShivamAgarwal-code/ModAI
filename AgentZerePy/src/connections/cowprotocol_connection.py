import logging
from typing import Any, Dict
from src.connections.base_connection import BaseConnection, Action, ActionParameter
from src.helpers.ethereum.cowprotocol import CowSwapClient

logger = logging.getLogger("connections.cowprotocol")


class CowProtocolConnection(BaseConnection):
    def __init__(self, config):
        self.client = CowSwapClient(config.get("base_url", "http://localhost:3000"))
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
            self.client = CowSwapClient(kwargs["base_url"])
        return True

    def is_configured(self, verbose=False) -> bool:
        return True

    def register_actions(self) -> None:
        self.actions = {
            "create-swap-order": Action(
                name="create-swap-order",
                parameters=[
                    ActionParameter("amount", True, str, "Amount to swap"),
                    ActionParameter(
                        "token_address", True, str, "Token address to swap"
                    ),
                    ActionParameter(
                        "operation", True, str, "Operation type (buy/sell)"
                    ),
                ],
                description="Create a new swap order",
            ),
            "sign-swap-order": Action(
                name="sign-swap-order",
                parameters=[
                    ActionParameter("order_id", True, str, "Order ID to sign"),
                ],
                description="Sign an existing swap order",
            ),
            "get-orders": Action(
                name="get-orders",
                parameters=[],
                description="Get all orders",
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

    def create_swap_order(
        self, amount: str, token_address: str, operation: str
    ) -> Dict:
        try:
            return self.client.create_swap_order(amount, token_address, operation)
        except Exception as e:
            logger.error(f"Failed to create swap order: {str(e)}")
            return None

    def sign_swap_order(self, order_id: str) -> Dict:
        try:
            return self.client.sign_swap_order(order_id)
        except Exception as e:
            logger.error(f"Failed to sign swap order: {str(e)}")
            return None

    def get_orders(self) -> Dict:
        try:
            return self.client.get_orders()
        except Exception as e:
            logger.error(f"Failed to get orders: {str(e)}")
            return None
