import json
import logging
import os
import httpx
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain.tools import Tool
from src.connections.safe_connection import SafeConnection
from src.connections.cowprotocol_connection import CowProtocolConnection
from src.connection_manager import ConnectionManager

load_dotenv()
logger = logging.getLogger("agent")


class ZerePyAgent:
    def __init__(self, agent_name: str):
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable must be set")

        agent_path = Path("agents") / f"{agent_name}.json"
        agent_dict = json.load(open(agent_path, "r"))

        self.name = agent_dict["name"]
        self.bio = agent_dict["bio"]

        # Create proper connection configs
        connections_config = [
            {
                "name": "safe",
                "base_url": os.getenv("SAFE_API_URL", "http://localhost:3000/api"),
            },
            {
                "name": "cowprotocol",
                "base_url": os.getenv("COW_API_URL", "http://localhost:3000/api"),
            },
            {"name": "openai", "api_key": os.getenv("OPENAI_API_KEY")},
        ]

        # Initialize connection manager with configs
        self.connection_manager = ConnectionManager(connections_config)

        self._setup_langchain_agent()
        logger.info("✅ Agent loaded successfully")

    def list_connections(self):
        return self.connection_manager.list_connections()

    def get_connection(self, name: str):
        return self.connection_manager.get_connection(name)

    def perform_action(self, connection_name: str, action_name: str, params: list):
        return self.connection_manager.perform_action(
            connection_name, action_name, params
        )

    def _setup_langchain_agent(self):
        tools = [
            Tool(
                name="Safe_Check_Status",
                func=lambda x: self.connection_manager.perform_action(
                    "safe", "check-status", [x]
                ),
                description='Check Safe transaction status. Input: {"safeTxHash": "string"} Returns: {"status": "pending", "transaction": {"safeTxHash": "string", "confirmations": int, "threshold": int, "isExecutable": bool}}',
                return_direct=False,
            ),
            Tool(
                name="Safe_Get_Balances",
                func=lambda x: self.connection_manager.perform_action(
                    "safe", "get-balances", []
                ),
                description='Get Safe balances including native token and ERC20 tokens \
                    Returns: {"balances": [{"token": "string", "balance": "string", "decimals": int, "symbol": "string", "address": "string"}]}',
                return_direct=False,
            ),
            Tool(
                name="Safe_Create_Transaction",
                func=lambda x: self.connection_manager.perform_action(
                    "safe",
                    "create-transaction",
                    (
                        [
                            json.loads(x)["to"],
                            json.loads(x)["value"],
                            json.loads(x)["data"],
                        ]
                        if isinstance(x, dict)
                        else [None, None, None]
                    ),
                ),
                description='Create Safe transaction. Input: dict with "to" (address), "value" (wei), "data" (hex) \
                    Returns: {"safeTxHash": "string", "safeTx": {"to": "string", "value": "string", "data": "string"}}',
                return_direct=False,
            ),
            Tool(
                name="Wait_Confirmation",
                func=lambda x: self._request_confirmation(x),
                description='Request human confirmation for signing a transaction. Input: {"safeTxHash": "string"} containing transaction details to be signed.',
                return_direct=False,
            ),
            Tool(
                name="Cow_Create_Swap",
                func=lambda x: self.connection_manager.perform_action(
                    "cowprotocol",
                    "create-swap-order",
                    (
                        [
                            json.loads(x)["amount"],
                            json.loads(x)["token_address"],
                            json.loads(x)["operation"],
                        ]
                    ),
                ),
                description='Create CoW swap order. Input: {"amount": "str", "token_address": "str", "operation": "str: buy/sell"} \
                    Return: {"order_id": "str"}',
                return_direct=False,
            ),
            Tool(
                name="Cow_Sign_Order",
                func=lambda x: self.connection_manager.perform_action(
                    "cowprotocol", "sign-swap-order", [json.loads(x)["order_id"]]
                ),
                description='Sign CoW swap order. Input: {"order_id": "str"}. Returns: {"safeTxHash": "string", "safeTx": {"to": "string", "value": "string", "data": "string"}}',
                return_direct=False,
            ),
            Tool(
                name="Cow_Get_Orders",
                func=lambda: self.connection_manager.perform_action(
                    "cowprotocol", "get-orders", []
                ),
                description='Get all CoW Protocol orders \
                    Returns: {"orders": [{"id": "string", "status": "string", "amount": "string", "token": "string", "operation": "string", "createdAt": "string", "updatedAt": "string"}]}',
                return_direct=False,
            ),
        ]

        llm = ChatOpenAI(
            temperature=0.3,
            model="gpt-4",
            api_key=os.getenv("OPENAI_API_KEY"),
        )

        template = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

        prompt = PromptTemplate(
            template=template,
            input_variables=["input", "agent_scratchpad"],
            partial_variables={
                "tools": "\n".join(
                    [f"{tool.name}: {tool.description}" for tool in tools]
                ),
                "tool_names": ", ".join([tool.name for tool in tools]),
            },
        )

        agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
        self.agent = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=6,
            handle_parsing_errors=True,
            early_stopping_method="force",
        )
        logger.info("✅ LangChain agent setup complete")

    def _request_confirmation(self, request_data: str) -> str:
        """
        Send confirmation request to the confirmation service

        Args:
            request_data (str): Transaction hash to be confirmed

        Returns:
            str: Response from confirmation service
        """
        try:
            tx_hash = (
                json.loads(request_data)["safeTxHash"]
                if isinstance(request_data, str)
                else request_data.get("safeTxHash")
            )
            callback_message = (
                json.loads(request_data)["callback_message"]
                if isinstance(request_data, str)
                else request_data.get("callback_message")
            )

            if not tx_hash:
                raise ValueError("No transaction hash provided")

            url = "http://localhost:16000/confirm-tx"
            headers = {"Content-Type": "application/json"}
            payload = {"tx_hash": tx_hash, "callback_message": callback_message}

            logger.info(f"Requesting confirmation for transaction: {tx_hash}")
            with httpx.Client() as client:
                response = client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                return f"Confirmation request sent for transaction: {tx_hash}"
            else:
                raise ValueError(
                    f"Confirmation request failed with status {response.status_code}: {response.text}"
                )

        except Exception as e:
            error_msg = f"Error requesting confirmation: {str(e)}"
            logger.error(error_msg)
            return error_msg

    def run_prompt(self, prompt: str) -> str:
        try:
            input_context = f"""You are {self.name}, {self.bio}

Tools usage chain:

Cow_Create_Swap -> Cow_Sign_Order -> Wait_Confirmation
Safe_Create_Transaction (Required tool that provide tx data) -> Wait_Confirmation

Constants and Guidelines:

Agent safe account:
SAFE_ADDRESS=0x4c76738fb40237ef05cE1F49BBADbc4B6b141a7d

Token addresses:
ETH_ADDRESS=0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee
COW_ADDRESS=0x0625aFB445C3B6B7B929342a04A22599fd5dBB59

IF SOME OF TOOLS RETURN NONE, STOP THE LOOP


User Query: {prompt}
"""
            response = self.agent.invoke(
                {
                    "input": input_context,
                    "name": self.name,
                    "bio": self.bio,
                }
            )
            return response.get("output", "Failed to process prompt")
        except Exception as e:
            logger.error(f"Error processing prompt: {str(e)}")
            return f"Error: {str(e)}"

    def loop(self):
        """Start interactive chat console with the agent"""
        logger.info(f"\n🤖 Starting chat with {self.name}...")
        logger.info("Type 'exit' or 'quit' to end the chat")
        logger.info("Type 'help' to see available commands")
        logger.info("Press Ctrl+C to stop\n")

        while True:
            try:
                # Get user input
                user_input = input(f"\n👤 You: ").strip()

                # Check for exit commands
                if user_input.lower() in ["exit", "quit"]:
                    logger.info(f"\n👋 Goodbye!")
                    break

                # Check for help command
                if user_input.lower() == "help":
                    logger.info("\n🔍 Available Commands:")
                    logger.info("- help: Show this help message")
                    logger.info("- exit/quit: End the chat")
                    logger.info("- connections: List all available connections")
                    logger.info("- clear: Clear the screen")
                    continue

                # Check for connections command
                if user_input.lower() == "connections":
                    self.list_connections()
                    continue

                # Check for clear command
                if user_input.lower() == "clear":
                    os.system("clear" if os.name == "posix" else "cls")
                    continue

                # Skip empty inputs
                if not user_input:
                    continue

                # Process the user input
                logger.info(f"\n🤖 {self.name}: Thinking...")
                response = self.run_prompt(user_input)
                logger.info(f"\n🤖 {self.name}: {response}")

            except KeyboardInterrupt:
                logger.info(f"\n\n👋 Chat ended by user")
                break
            except Exception as e:
                logger.error(f"\n❌ Error: {str(e)}")
                logger.info("Type 'exit' to quit or try another command")
