import json
import random
import time
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from src.connection_manager import ConnectionManager
from src.helpers import print_h_bar
from datetime import datetime
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import MessagesPlaceholder, PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.tools import Tool
from langchain.callbacks import get_openai_callback
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage, AIMessage
from typing import Any

REQUIRED_FIELDS = ["name", "bio", "traits", "examples", "loop_delay", "config", "tasks"]

logger = logging.getLogger("agent")


class ZerePyAgent:
    def __init__(self, agent_name: str):
        try:
            # Check for OpenAI API key first
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError(
                    "OPENAI_API_KEY environment variable must be set. Please add it to your .env file"
                )

            agent_path = Path("agents") / f"{agent_name}.json"
            agent_dict = json.load(open(agent_path, "r"))

            missing_fields = [
                field for field in REQUIRED_FIELDS if field not in agent_dict
            ]
            if missing_fields:
                raise KeyError(f"Missing required fields: {', '.join(missing_fields)}")

            self.name = agent_dict["name"]
            self.bio = agent_dict["bio"]
            self.traits = agent_dict["traits"]
            self.examples = agent_dict["examples"]
            self.example_accounts = agent_dict.get("example_accounts", [])
            self.loop_delay = agent_dict["loop_delay"]

            # Log the full config for debugging
            logger.info("Loading agent configuration:")
            logger.info(json.dumps(agent_dict["config"], indent=2))

            self.connection_manager = ConnectionManager(agent_dict["config"])
            self.use_time_based_weights = agent_dict.get(
                "use_time_based_weights", False
            )
            self.time_based_multipliers = agent_dict.get("time_based_multipliers", {})
            logger.info(agent_dict["config"])
            # Extract Discord config with better validation
            discord_config = next(
                (
                    config
                    for config in agent_dict["config"]
                    if config["name"] == "discord"
                ),
                None,
            )
            if discord_config:
                logger.info("Found Discord configuration:")
                logger.info(json.dumps(discord_config, indent=2))

                self.discord_server_id = discord_config.get("server_id")
                if not self.discord_server_id:
                    logger.error("Discord server_id is missing or empty in config")
                else:
                    logger.info(f"Using Discord server ID: {self.discord_server_id}")

                self.discord_message_limit = discord_config.get("message_limit", 50)
                self.discord_trigger_words = discord_config.get("trigger_words", [])
                self.discord_ignore_bots = discord_config.get("ignore_bots", True)

                logger.info(
                    f"Discord config loaded: message_limit={self.discord_message_limit}, "
                    f"trigger_words={self.discord_trigger_words}, "
                    f"ignore_bots={self.discord_ignore_bots}"
                )
            else:
                logger.warning("No Discord configuration found in agent config")

            # Extract Snapshot config
            snapshot_config = next(
                (
                    config
                    for config in agent_dict["config"]
                    if config["name"] == "snapshot"
                ),
                None,
            )
            if snapshot_config:
                self.snapshot_space_id = snapshot_config.get("space_id")
                self.snapshot_proposal_limit = snapshot_config.get("proposal_limit", 10)

            # Extract Safe config
            safe_config = next(
                (config for config in agent_dict["config"] if config["name"] == "safe"),
                None,
            )
            if safe_config:
                self.safe_address = safe_config.get("safe_address")

            # Extract Forum config
            forum_config = next(
                (
                    config
                    for config in agent_dict["config"]
                    if config["name"] == "cowforum"
                ),
                None,
            )
            if forum_config:
                self.forum_update_interval = forum_config.get("update_interval", 300)
                self.forum_category = forum_config.get("category")

            self.is_llm_set = False
            self._system_prompt = None
            self.tasks = agent_dict.get("tasks", [])
            self.task_weights = [task.get("weight", 0) for task in self.tasks]
            self.logger = logging.getLogger("agent")

            # Initialize state with empty collections
            self.state = {
                "discord_messages": [],
                "snapshot_proposals": [],
                "safe_transactions": [],
                "forum_updates": [],
                "last_message_timestamps": {
                    "discord": None,
                    "snapshot": None,
                    "forum": None,
                },
                "processed_message_ids": set(),  # Track processed Discord messages
            }

            # Initialize LangChain components
            self._setup_langchain_agent()

            # Service check intervals
            self.discord_check_interval = 20  # 20 seconds
            self.other_services_check_interval = 60  # 1 minute
            self.last_discord_check = 0
            self.last_services_check = 0

        except Exception as e:
            logger.error("Could not load ZerePy agent")
            raise e

    def _setup_langchain_agent(self):
        """Setup LangChain agent with tools"""
        try:
            tools = [
                Tool(
                    name="Discord_Send",
                    func=lambda x: self.connection_manager.perform_action(
                        connection_name="discord",
                        action_name="post-message",
                        params=[self.discord_server_id, x],
                    ),
                    description="Send a message to Discord channel. Action Input: message (str) - The text message you want to send to Discord.",
                    return_direct=True,
                ),
                Tool(
                    name="Safe_Check",
                    func=lambda x: self.perform_action(
                        connection_name="safe",
                        action_name="check-status",
                        params=[x],
                    ),
                    description="Check Safe transaction status. Action Input: safe_tx_hash (str) - The transaction hash to check status for.",
                ),
                Tool(
                    name="Forum_Get",
                    func=lambda x: self.perform_action(
                        connection_name="cowforum",
                        action_name="get-forum-article",
                        params=[x],
                    ),
                    description="Get forum article content. Action Input: url (str) - The full URL of the forum article to fetch.",
                ),
            ]

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is not set")

            llm = ChatOpenAI(
                temperature=0.3,
                api_key=api_key,
                model="gpt-4o",  # Specify model explicitly
            )

            template = """Assistant is a helpful AI named {name}. {bio}

{instructions}

TOOLS:
------

You have access to the following tools:

{tools}

IMPORTANT: You must ALWAYS follow this process:

1. First, think about whether you need to use a tool to complete instructions
2. If you need a tool, use this format:
```
Thought: Do I need to use a tool? Yes
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
```
3. After each observation, start the process again with a new thought
4. Only when you have all needed information and don't need any more tools, use this format:
```
Thought: Do I need to use a tool? No
Final Answer: [your response here]
```

RULES:
- NEVER respond directly to the Human without going through the thought process
- ALWAYS start with "Thought: Do I need to use a tool?"
- ALWAYS use a tool at least once before giving a Final Answer
- After using a tool, ALWAYS start with a new thought about the observation
- If you're unsure, use more tools to gather information

Begin!

Previous conversation history:
{chat_history}

New input: {input}
{agent_scratchpad}"""

            prompt = PromptTemplate(
                template=template,
                input_variables=[
                    "input",
                    "agent_scratchpad",
                    "name",
                    "bio",
                    "instructions",
                    "chat_history",
                ],
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
                max_iterations=3,
                handle_parsing_errors=True,
            )

        except Exception as e:
            logger.error("Error setting up LangChain agent")
            raise e

    def _construct_system_prompt(self) -> str:
        if self._system_prompt is None:
            prompt_parts = []
            prompt_parts.extend(self.bio)

            if self.traits:
                prompt_parts.append("\nYour key traits are:")
                prompt_parts.extend(f"- {trait}" for trait in self.traits)

            if self.examples:
                prompt_parts.append("\nHere are some examples of your style:")
                prompt_parts.extend(f"- {example}" for example in self.examples)

            self._system_prompt = "\n".join(prompt_parts)

        return self._system_prompt

    def _should_process_discord_message(self, message):
        # Skip if message already processed
        if message["id"] in self.state["processed_message_ids"]:
            return False

        # Skip bot messages if configured
        if self.discord_ignore_bots and message.get("is_bot", False):
            return False

        # Check for trigger words if configured
        if self.discord_trigger_words:
            content = message["content"].lower()
            if not any(word.lower() in content for word in self.discord_trigger_words):
                return False

        return True

    def _process_discord_message(self, message):
        try:
            discord_personality = """You are chAIrman 🪑, the CoW Protocol community bot.
- Use emojis for engagement (🐮 for CoW, 📊 for trading)
- Be helpful and clear
- Sign messages with "- chAIrman 🪑\""""

            # Format message context
            input_text = f"""Message from {message.get('author', 'Unknown')}:
{message.get('message', '')}

{discord_personality}

If the message needs a response, use Discord_Send with a helpful reply.
If not, briefly explain why."""

            response = self.agent.invoke(
                {
                    "input": input_text,
                    "name": "chAIrman",
                    "bio": "I am the chAIrman of CoW Protocol's community.",
                    "instructions": "You are chAIrman, CoW Protocol's community bot. Keep responses helpful and engaging.",
                    "chat_history": "",
                }
            )

            if response and "output" in response:
                # Mark message as processed regardless of whether we responded
                self.state["processed_message_ids"].add(message["id"])
                logger.info(
                    f"Processed Discord message {message['id']}: {response['output'][:100]}..."
                )
            return response.get("output")

        except Exception as e:
            logger.error(f"Error processing Discord message: {str(e)}")
            return None

    def _update_discord_messages(self):
        """Fetch and update latest Discord messages"""
        try:
            if self.discord_server_id:
                messages = self.perform_action(
                    connection_name="discord",
                    action_name="read-messages",
                    params=[self.discord_server_id, 10],  # Get last 10 messages
                )
                logger.info(f"Retrieved {len(messages)} Discord messages")

                if messages:
                    # Sort messages by timestamp if available
                    messages.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

                    # Get unprocessed messages from the latest batch
                    unprocessed_messages = [
                        msg
                        for msg in messages
                        if msg["id"] not in self.state["processed_message_ids"]
                        and msg.get("message")  # Only messages with content
                        and not (self.discord_ignore_bots and msg.get("is_bot", False))
                    ]

                    # Update state with all messages for context
                    self.state["discord_messages"] = messages
                    self.state["last_message_timestamps"]["discord"] = datetime.now()

                    if unprocessed_messages:
                        # Get context from older messages
                        processed_messages = [
                            msg
                            for msg in messages
                            if msg["id"] in self.state["processed_message_ids"]
                            and msg.get("message")
                        ][
                            :5
                        ]  # Get up to 5 recent processed messages for context

                        # Combine messages for processing
                        batch = processed_messages + unprocessed_messages
                        batch.sort(key=lambda x: x.get("timestamp", ""))  # Sort by time

                        logger.info(
                            f"\n📨 Processing {len(unprocessed_messages)} new messages with {len(processed_messages)} context messages"
                        )
                        self._process_discord_messages_batch(
                            batch,
                            new_message_ids=[msg["id"] for msg in unprocessed_messages],
                        )

        except Exception as e:
            logger.error(f"Failed to update Discord messages: {str(e)}")

    def _process_discord_messages_batch(self, messages, new_message_ids):
        """Process a batch of Discord messages with context
        Args:
            messages: List of all messages including context
            new_message_ids: List of IDs of new messages that need responses
        """
        try:
            # Format all messages for context
            messages_context = "\n".join(
                [
                    f"Message {i+1}:\n"
                    f"Author: {msg.get('author', 'Unknown')}\n"
                    f"Content: {msg.get('message', '')}\n"
                    f"Is New: {'Yes' if msg['id'] in new_message_ids else 'No (Context)'}\n"
                    for i, msg in enumerate(messages)
                ]
            )

            discord_personality = """You are chAIrman 🪑, the CoW Protocol community bot.
- Use emojis for engagement (🐮 for CoW, 📊 for trading)
- Be helpful and clear
- Sign messages with "- chAIrman 🪑\""""

            input_text = f"""Here are Discord messages (older to newer):

{messages_context}

{discord_personality}

Analyze the messages marked as "Is New: Yes" and decide if they need responses.
Use the context from older messages to understand the conversation flow.

For each new message that needs a response:
1. Use Discord_Send to send an appropriate reply
2. Keep responses relevant to the conversation context
3. Always sign your messages with "- chAIrman 🪑"

You can respond to multiple messages if needed. Focus on continuing the conversation naturally."""

            response = self.agent.invoke(
                {
                    "input": input_text,
                    "name": "chAIrman",
                    "bio": "I am the chAIrman of CoW Protocol's community.",
                    "instructions": "You are chAIrman, CoW Protocol's community bot. Keep responses helpful and engaging.",
                    "chat_history": "",
                }
            )

            if response and "output" in response:
                # Mark only new messages as processed
                for msg_id in new_message_ids:
                    self.state["processed_message_ids"].add(msg_id)
                logger.info(f"Batch processed {len(new_message_ids)} new messages")
                logger.info(f"Agent response: {response['output'][:200]}...")

        except Exception as e:
            logger.error(f"Error processing Discord message batch: {str(e)}")

    def _update_snapshot_proposals(self):
        """Fetch and update latest Snapshot proposals"""
        try:
            if self.snapshot_space_id:
                proposals = self.perform_action(
                    connection_name="snapshot",
                    action_name="get-proposals",
                    params=[
                        self.snapshot_space_id,
                        "active",
                        self.snapshot_proposal_limit,
                    ],
                )
                if proposals:
                    self.state["snapshot_proposals"] = proposals
                    self.state["last_message_timestamps"]["snapshot"] = datetime.now()
                    logger.info(f"Retrieved {len(proposals)} Snapshot proposals")
        except Exception as e:
            logger.error(f"Failed to update Snapshot proposals: {str(e)}")

    def _update_forum_updates(self):
        """Fetch and update latest forum updates"""
        try:
            updates = self.perform_action(
                connection_name="cowforum",
                action_name="get-forum-updates",
                params=[self.forum_category] if self.forum_category else [],
            )
            if updates:
                self.state["forum_updates"] = updates
                self.state["last_message_timestamps"]["forum"] = datetime.now()
                logger.info(f"Retrieved {len(updates)} forum updates")
        except Exception as e:
            logger.error(f"Failed to update forum updates: {str(e)}")

    def _process_messages(self):
        """Process messages using LangChain agent"""
        try:
            # Process Discord messages - now handled in batch
            if self.state["discord_messages"]:
                messages = self.state["discord_messages"]
                unprocessed = [
                    msg
                    for msg in messages
                    if msg["id"] not in self.state["processed_message_ids"]
                    and msg.get("message")
                    and not (self.discord_ignore_bots and msg.get("is_bot", False))
                ]
                if unprocessed:
                    self._process_discord_messages_batch(
                        unprocessed[:3]
                    )  # Process up to 3 messages

            # Process Snapshot proposals
            if self.state["snapshot_proposals"]:
                for proposal in self.state["snapshot_proposals"]:
                    try:
                        input_text = f"""Review this Snapshot proposal:
Title: {proposal.get('title', 'Unknown')}
Body: {proposal.get('body', 'No body')}

Should we take any action on this proposal?"""

                        response = self.agent.invoke(
                            {
                                "input": input_text,
                                "name": self.name,
                                "bio": (
                                    self.bio[0] if self.bio else "I am an AI assistant."
                                ),
                                "instructions": "You are a governance assistant. Review proposals and suggest actions if needed.",
                                "chat_history": "",
                            }
                        )
                        if response and "output" in response:
                            logger.info(
                                f"Agent analysis for proposal [{proposal.get('title', 'Unknown')}]: {response['output']}"
                            )
                    except Exception as e:
                        logger.error(f"Error processing Snapshot proposal: {str(e)}")

            # Process forum updates
            if self.state["forum_updates"]:
                for update in self.state["forum_updates"]:
                    try:
                        input_text = f"""Review this forum update:
Title: {update.get('title', 'Unknown')}
Category: {update.get('category', 'Unknown')}
Author: {update.get('author', 'Unknown')}

Should we get more details about this update using Forum_Get?"""

                        response = self.agent.invoke(
                            {
                                "input": input_text,
                                "name": self.name,
                                "bio": (
                                    self.bio[0] if self.bio else "I am an AI assistant."
                                ),
                                "instructions": "You are a forum moderator. Review updates and fetch details if interesting.",
                                "chat_history": "",
                            }
                        )
                        if response and "output" in response:
                            logger.info(
                                f"Agent review for forum update [{update.get('title', 'Unknown')}]: {response['output']}"
                            )
                    except Exception as e:
                        logger.error(f"Error processing forum update: {str(e)}")

        except Exception as e:
            logger.error(f"Error in _process_messages: {str(e)}")

    def _should_check_discord(self) -> bool:
        current_time = time.time()
        if current_time - self.last_discord_check >= self.discord_check_interval:
            self.last_discord_check = current_time
            return True
        return False

    def _should_check_services(self) -> bool:
        current_time = time.time()
        if (
            current_time - self.last_services_check
            >= self.other_services_check_interval
        ):
            self.last_services_check = current_time
            return True
        return False

    def perform_action(self, connection_name: str, action_name: str, **kwargs) -> Any:
        """Perform an action using the connection manager"""
        logger.info(f"Performing action {action_name} on {connection_name}: {kwargs}")
        try:
            params = kwargs.get("params", [])
            logger.info(f"Params: {params}")
            if isinstance(params, (list, tuple, dict)):
                return self.connection_manager.perform_action(
                    connection_name=connection_name,
                    action_name=action_name,
                    params=params,
                )
            else:
                return self.connection_manager.perform_action(
                    connection_name=connection_name,
                    action_name=action_name,
                    params=[params] if params else [],
                )
        except Exception as e:
            logger.error(
                f"Error performing action {action_name} on {connection_name}: {str(e)}"
            )
            return None

    def loop(self):
        """Main agent loop for autonomous behavior"""
        logger.info("\n🚀 Starting agent loop...")
        logger.info("Press Ctrl+C at any time to stop the loop.")
        print_h_bar()

        time.sleep(1)

        try:
            while True:
                try:
                    # Update Discord messages every 20 seconds
                    if self._should_check_discord():
                        logger.info("\n👀 Checking Discord messages...")
                        self._update_discord_messages()
                        logger.info("Discord messages updated")

                    # Update other services every minute
                    if self._should_check_services():
                        logger.info("\n👀 Checking other services...")
                        self._update_snapshot_proposals()
                        self._update_forum_updates()

                    # Process all messages using LangChain agent
                    self._process_messages()

                    # Short sleep to prevent CPU overuse
                    time.sleep(1)

                except Exception as e:
                    logger.error(f"\n❌ Error in agent loop iteration: {e}")
                    logger.info("⏳ Waiting 5 seconds before retrying...")
                    time.sleep(5)

        except KeyboardInterrupt:
            logger.info("\n👋 Agent loop stopped by user.")
            return
