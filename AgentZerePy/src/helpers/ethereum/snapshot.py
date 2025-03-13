import requests
import json
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger("snapshot")


class SnapshotClient:
    """
    Client for interacting with Snapshot GraphQL API.

    Base URL: https://hub.snapshot.org/graphql
    """

    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://hub.snapshot.org/graphql"
        self.headers = {"Content-Type": "application/json"}
        # if api_key:
        #     self.headers["x-api-key"] = api_key

    def _execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        payload = {"query": query, "variables": variables or {}}

        response = requests.post(self.base_url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def get_space(self, space_id: str) -> Dict:
        """
        Get a single space by ID.

        Arguments:
            space_id (str): Space identifier (e.g. "yam.eth")

        Example:
            >>> client.get_space("yam.eth")
            {
                "data": {
                    "space": {
                        "id": "yam.eth",
                        "name": "Yam Finance",
                        "about": "",
                        "network": "1",
                        "symbol": "YAM",
                        "members": [
                            "0x683A78bA1f6b25E29fbBC9Cd1BFA29A51520De84",
                            "0x9Ebc8AD4011C7f559743Eb25705CCF5A9B58D0bc"
                        ]
                    }
                }
            }
        """
        query = """
        query Space($id: String!) {
            space(id: $id) {
                id
                name
                about
                network
                symbol
                members
                admins
                moderators
                strategies {
                    name
                    network
                    params
                }
                voting {
                    delay
                    period
                    type
                    quorum
                }
            }
        }
        """
        result = self._execute_query(query, {"id": space_id})
        logger.info(f"Result: {result}")
        return result.get("data", {}).get("space")

    def get_proposals(
        self, space_id: str, state: str = "all", first: int = 20
    ) -> List[Dict]:
        query = """
        query Proposals($space: String!, $state: String!, $first: Int!) {
            proposals(
                where: {
                    space: $space,
                    state: $state
                }
                first: $first
                skip: 0
            ) {
                id
                title
                body
                choices
                start
                end
                snapshot
                state
                author
                space {
                    id
                    name
                }
                votes
            }
        }
        """
        result = self._execute_query(
            query, {"space": space_id, "state": state, "first": first}
        )
        # print(result)
        return result.get("data", {}).get("proposals", [])

    def get_votes(self, proposal_id: str, first: int = 1000) -> List[Dict]:
        query = """
        query Votes($proposal: String!, $first: Int!) {
            votes(
                where: {
                    proposal: $proposal
                }
                first: $first
            ) {
                id
                voter
                choice
                vp
                reason
                created
            }
        }
        """
        result = self._execute_query(query, {"proposal": proposal_id, "first": first})
        return result.get("data", {}).get("votes", [])

    def get_user_votes(self, voter: str, first: int = 100) -> List[Dict]:
        query = """
        query Votes($voter: String!, $first: Int!) {
            votes(
                where: {
                    voter: $voter
                }
                first: $first
            ) {
                id
                voter
                proposal {
                    id
                    title
                    space {
                        id
                        name
                    }
                }
                choice
                vp
                created
            }
        }
        """
        result = self._execute_query(query, {"voter": voter, "first": first})
        return result.get("data", {}).get("votes", [])

    def get_voting_power(self, voter: str, space_id: str, proposal_id: str) -> Dict:
        query = """
        query VotingPower($voter: String!, $space: String!, $proposal: String!) {
            vp(
                voter: $voter
                space: $space
                proposal: $proposal
            ) {
                vp
                vp_by_strategy
                vp_state
            }
        }
        """
        result = self._execute_query(
            query, {"voter": voter, "space": space_id, "proposal": proposal_id}
        )
        return result.get("data", {}).get("vp", {})

    def get_follows(self, space_id: str, first: int = 100) -> List[Dict]:
        """Get followers of a space"""
        query = """
        query Follows($space: String!, $first: Int!) {
            follows(
                where: {
                    space: $space
                }
                first: $first
            ) {
                id
                follower
                created
            }
        }
        """
        result = self._execute_query(query, {"space": space_id, "first": first})
        return result.get("data", {}).get("follows", [])

    def get_proposal_messages(self, proposal_id: str, first: int = 100) -> List[Dict]:
        """Get messages/comments on a proposal"""
        query = """
        query Messages($proposal: String!, $first: Int!) {
            messages(
                where: {
                    proposal: $proposal
                }
                first: $first
                orderBy: "created",
                orderDirection: desc
            ) {
                id
                content
                author
                created
                proposal {
                    id
                    title
                }
            }
        }
        """
        result = self._execute_query(query, {"proposal": proposal_id, "first": first})
        return result.get("data", {}).get("messages", [])

    def get_user_activities(self, address: str, first: int = 100) -> List[Dict]:
        """Get user's activities (proposals, votes, follows)"""
        query = """
        query Activities($address: String!, $first: Int!) {
            proposals(
                where: {
                    author: $address
                }
                first: $first
                orderBy: "created",
                orderDirection: desc
            ) {
                id
                title
                created
                space {
                    id
                    name
                }
            }
            votes(
                where: {
                    voter: $address
                }
                first: $first
                orderBy: "created",
                orderDirection: desc
            ) {
                id
                created
                proposal {
                    id
                    title
                }
                choice
            }
            follows(
                where: {
                    follower: $address
                }
                first: $first
                orderBy: "created",
                orderDirection: desc
            ) {
                id
                space {
                    id
                    name
                }
                created
            }
        }
        """
        result = self._execute_query(query, {"address": address, "first": first})
        return result.get("data", {})

    # def get_space_stats(self, space_id: str) -> Dict:
    #     """Get detailed statistics for a space"""
    #     query = """
    #     query SpaceStats($id: String!) {
    #         space(id: $id) {
    #             id
    #             name
    #             about
    #             network
    #             symbol
    #             followersCount
    #             proposalsCount
    #             votesCount
    #             activeProposals: proposals(
    #                 where: {
    #                     space: $id,
    #                     state: "active"
    #                 }
    #             ) {
    #                 id
    #             }
    #             topVoters: votes(
    #                 first: 10,
    #                 orderBy: "vp",
    #                 orderDirection: desc,
    #                 where: {
    #                     space: $id
    #                 }
    #             ) {
    #                 voter
    #                 vp
    #             }
    #         }
    #     }
    #     """
    #     result = self._execute_query(query, {"id": space_id})
    #     return result.get("data", {}).get("space", {})

    def get_proposal_results(self, proposal_id: str) -> Dict:
        """Get detailed results for a proposal"""
        query = """
        query ProposalResults($id: String!) {
            proposal(id: $id) {
                id
                title
                state
                choices
                scores
                scores_total
                votes
                quorum
                votes_by_strategy
            }
        }
        """
        result = self._execute_query(query, {"id": proposal_id})
        return result.get("data", {}).get("proposal", {})
