import logging
from typing import Any, Dict, List, Optional
from src.connections.base_connection import BaseConnection, Action, ActionParameter
from src.helpers.ethereum.snapshot import SnapshotClient

logger = logging.getLogger("connections.snapshot")


class SnapshotConnection(BaseConnection):
    def __init__(self, config):
        self.client = SnapshotClient()
        super().__init__(config)

    @property
    def is_llm_provider(self):
        return False

    def validate_config(self, config) -> Dict[str, Any]:
        return config

    def configure(self, **kwargs) -> bool:
        return True

    def is_configured(self, verbose=False) -> bool:
        return True

    def register_actions(self) -> None:
        self.actions = {
            "get-space": Action(
                name="get-space",
                parameters=[
                    ActionParameter("space_id", True, str, "ID of the space to fetch")
                ],
                description="Get information about a Snapshot space",
            ),
            "get-proposals": Action(
                name="get-proposals",
                parameters=[
                    ActionParameter("space_id", True, str, "ID of the space"),
                    ActionParameter("state", False, str, "State of proposals to fetch"),
                    ActionParameter(
                        "first", False, int, "Number of proposals to fetch"
                    ),
                ],
                description="Get proposals for a space",
            ),
            "get-votes": Action(
                name="get-votes",
                parameters=[
                    ActionParameter("proposal_id", True, str, "ID of the proposal"),
                    ActionParameter("first", False, int, "Number of votes to fetch"),
                ],
                description="Get votes for a proposal",
            ),
            "get-user-votes": Action(
                name="get-user-votes",
                parameters=[
                    ActionParameter("voter", True, str, "Address of the voter"),
                    ActionParameter("first", False, int, "Number of votes to fetch"),
                ],
                description="Get votes by a specific user",
            ),
            "get-proposal-messages": Action(
                name="get-proposal-messages",
                parameters=[
                    ActionParameter("proposal_id", True, str, "ID of the proposal"),
                    ActionParameter("first", False, int, "Number of messages to fetch"),
                ],
                description="Get messages for a proposal",
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

    def get_space(self, space_id: str) -> Optional[Dict]:
        try:
            # logger.info(f"Getting space {space_id}")
            space = self.client.get_space(space_id)
            logger.info(f"Retrieved space info for {space_id}")
            return space
        except Exception as e:
            logger.error(f"Failed to get space: {str(e)}")
            return None

    def get_proposals(
        self, space_id: str, state: str = "all", first: int = 20
    ) -> Optional[List]:
        try:
            proposals = self.client.get_proposals(space_id, state, first)
            logger.info(f"Retrieved {len(proposals)} proposals for space {space_id}")
            return proposals
        except Exception as e:
            logger.error(f"Failed to get proposals: {str(e)}")
            return None

    def get_votes(self, proposal_id: str, first: int = 1000) -> Optional[List]:
        try:
            votes = self.client.get_votes(proposal_id, first)
            logger.info(f"Retrieved {len(votes)} votes for proposal {proposal_id}")
            return votes
        except Exception as e:
            logger.error(f"Failed to get votes: {str(e)}")
            return None

    def get_user_votes(self, voter: str, first: int = 100) -> Optional[List]:
        try:
            votes = self.client.get_user_votes(voter, first)
            logger.info(f"Retrieved {len(votes)} votes for user {voter}")
            return votes
        except Exception as e:
            logger.error(f"Failed to get user votes: {str(e)}")
            return None

    def get_proposal_messages(
        self, proposal_id: str, first: int = 100
    ) -> Optional[List]:
        try:
            messages = self.client.get_proposal_messages(proposal_id, first)
            logger.info(
                f"Retrieved {len(messages)} messages for proposal {proposal_id}"
            )
            return messages
        except Exception as e:
            logger.error(f"Failed to get proposal messages: {str(e)}")
            return None
