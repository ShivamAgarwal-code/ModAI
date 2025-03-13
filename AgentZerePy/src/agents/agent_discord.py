import json
import time
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain.tools import Tool
from typing import Any
from src.connection_manager import ConnectionManager
from langchain_openai import OpenAI

# Load environment variables
load_dotenv()

logger = logging.getLogger("agent")


class ZerePyAgent:
    def __init__(self, agent_name: str):
        try:
            # Check for OpenAI API key
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError(
                    "OPENAI_API_KEY environment variable must be set. Please add it to your .env file"
                )

            agent_path = Path("agents") / f"{agent_name}.json"
            agent_dict = json.load(open(agent_path, "r"))

            self.name = agent_dict["name"]
            self.bio = agent_dict["bio"]

            # Extract Discord config
            discord_config = next(
                (
                    config
                    for config in agent_dict["config"]
                    if config["name"] == "discord"
                ),
                None,
            )
            if not discord_config:
                raise ValueError("Discord configuration is required")

            self.discord_server_id = discord_config.get("server_id")
            if not self.discord_server_id:
                raise ValueError("Discord server_id is required")

            self.discord_ignore_bots = discord_config.get("ignore_bots", True)
            self.connection_manager = ConnectionManager(agent_dict["config"])

            # Initialize state
            self.state = {
                "discord_messages": [],
                "processed_message_ids": set(),
                "last_check": 0,
                "last_proposals_check": 0,
            }

            self.proposals_file = Path("data") / f"{agent_name}_proposals.json"
            self.proposals_file.parent.mkdir(exist_ok=True)
            if not self.proposals_file.exists():
                self._save_proposals([])

            # Initialize LangChain agent
            self._setup_langchain_agent()
            logger.info("✅ Agent loaded successfully")

        except Exception as e:
            logger.error(f"Could not load agent: {str(e)}")
            raise e

    def _setup_langchain_agent(self):
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
                    return_direct=False,
                ),
                Tool(
                    name="Get_Analysis",
                    func=lambda x: self._get_analysis(x),
                    description="Get analysis about CoW DAO proposals (CIPs). Action Input: proposal_number (str) - CIP number (e.g., '61' for CIP-61).",
                    return_direct=False,
                ),
                Tool(
                    name="Get_Insight",
                    func=lambda x: self._get_insight(x),
                    description='Get insights about CIP-38 and CoW Swap. Input should be one of:\n1. "tell me about CIP-38" - returns CIP-38 detailed explanation\n2. "what did the community think about this proposal?" - returns community feedback\n3. "what do solvers do on CoWSwap?" - returns solver role explanation',
                    return_direct=False,
                ),
            ]

            llm = ChatOpenAI(
                temperature=0.3,
                model="gpt-4o",
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

For CIP-related queries, you must:
1. First get the insight/analysis using appropriate tool
2. Then use Discord_Send to share the information
3. Only then provide the final answer

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

            prompt = PromptTemplate(
                template=template,
                input_variables=[
                    "input",
                    "agent_scratchpad",
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
                max_iterations=6,
                handle_parsing_errors=True,
                early_stopping_method="force",
            )
            logger.info("✅ LangChain agent setup complete")

        except Exception as e:
            logger.error(f"Failed to setup LangChain agent: {str(e)}")
            raise e

    def _process_messages_batch(self, messages, new_message_ids):
        try:
            # Format current messages context
            messages_context = "\n".join(
                [
                    f"Message {i+1}:\n"
                    f"Author: {msg.get('author', 'Unknown')}\n"
                    f"Content: {msg.get('message', '')}\n"
                    f"Is New: {'Yes' if msg['id'] in new_message_ids else 'No (Context)'}\n"
                    f"Timestamp: {msg.get('timestamp', 'Unknown')}\n"
                    for i, msg in enumerate(messages)
                ]
            )
            logger.info(f"Processing messages:\n{messages_context}")

            # Create chat history from previous messages
            chat_history = []
            for msg in messages:
                if msg.get("is_bot", False) or msg.get("author", "").lower() in [
                    "chaiman",
                    "chairman",
                ]:
                    chat_history.append(f"Assistant: {msg.get('message', '')}")
                else:
                    chat_history.append(f"Human: {msg.get('message', '')}")

            chat_history_str = "\n".join(chat_history[-5:])

            input_text = f"""
You are chAIrman 🪑, the CoW Protocol community bot.
- Use emojis for engagement (🐮 for CoW, 📊 for trading)
- Sign messages with "- chAIrman 🪑"
- IGNORE STUPID MESSAGES
- WHEN USE GET_INSIGHT, SEND THE ANSWER TO DISCORD_SEND (WITHOUT PROCESSING IT, ADD ONLY `\n FOR NEW LINES)

Analyze messages and reponse to LAST IMPORTANT MESSAGE.
IF THERE IS NO IMPORTANT MESSAGE, IGNORE THE MESSAGES.

if it needs a response, use Discord_Send to send a message (ONLY IF IT IS IMPORTANT)

IMPORTANT:
- DO NOT respond to your own messages
- DO NOT respond to other bot messages
- DO NOT respond to messages marked as "Is New: No"

Here are Discord messages (older to newer):

{messages_context}
"""
            response = self.agent.invoke(
                {
                    "input": input_text,
                    "name": "chAIrman",
                    "bio": "I am the chAIrman of CoW Protocol's community.",
                    "instructions": "You are chAIrman, CoW Protocol's community bot. Keep responses helpful and engaging.",
                    "chat_history": chat_history_str,
                }
            )

            if response and "output" in response:
                for msg_id in new_message_ids:
                    self.state["processed_message_ids"].add(msg_id)
                logger.info(f"Processed {len(new_message_ids)} new messages")
                logger.info(f"Chat history used: {chat_history_str}")

        except Exception as e:
            logger.error(f"Error processing message batch: {str(e)}")
            logger.error(f"Messages context: {messages_context}")

    def _update_messages(self):
        try:
            messages = self.connection_manager.perform_action(
                connection_name="discord",
                action_name="read-messages",
                params=[self.discord_server_id, 4],
            )

            if not messages:
                logger.info("No messages received from Discord")
                return

            # Log raw messages for debugging
            logger.info(f"Raw messages from Discord: {messages}")

            # Sort messages by timestamp, oldest first
            messages.sort(key=lambda x: x.get("timestamp", ""))

            # Filter only messages with required fields
            valid_messages = [
                msg
                for msg in messages
                if msg.get("id") and msg.get("message") and msg.get("author")
            ]

            if not valid_messages:
                logger.info("No valid messages found")
                return

            # Get all new messages chronologically
            new_messages = [
                msg
                for msg in valid_messages
                if msg["id"] not in self.state["processed_message_ids"]
            ]

            if new_messages:
                logger.info(f"Found {len(new_messages)} new messages")
                # Get context messages (already processed ones)
                context_messages = [
                    msg
                    for msg in valid_messages
                    if msg["id"] in self.state["processed_message_ids"]
                ][-5:]

                # Messages to actually process (non-bot messages)
                messages_to_process = [
                    msg
                    for msg in new_messages
                    if not msg.get("is_bot", False)
                    and msg.get("author", "").lower() not in ["chaiman", "chairman"]
                ]

                # Create batch with proper chronological order
                batch = context_messages + new_messages

                # Mark all new messages as processed
                for msg in new_messages:
                    self.state["processed_message_ids"].add(msg["id"])

                if messages_to_process:
                    logger.info(
                        f"Processing batch of {len(batch)} messages ({len(context_messages)} context, {len(new_messages)} new, {len(messages_to_process)} to process)"
                    )
                    self._process_messages_batch(
                        batch,
                        new_message_ids=[
                            msg["id"] for msg in new_messages
                        ],  # All new messages marked as new
                    )
                else:
                    logger.info("No messages to process (only bot messages)")
            else:
                logger.info("No new messages")

            self.state["discord_messages"] = valid_messages
            self.state["last_check"] = time.time()

        except Exception as e:
            logger.error(f"Failed to update messages: {str(e)}")
            raise e

    def _save_proposals(self, analyzed_proposals):
        with open(self.proposals_file, "w") as f:
            json.dump(analyzed_proposals, f)

    def _get_formatted_analyses(self):
        try:
            proposals = self._load_proposals()
            if not proposals:
                return "No stored proposals found."

            formatted_analyses = []
            for p in proposals:
                if isinstance(p, dict) and "analysis" in p:
                    formatted_analyses.append(p["analysis"])

            if not formatted_analyses:
                return "No valid analyses found in stored proposals."

            return "\n\n---\n\n".join(formatted_analyses)
        except Exception as e:
            logger.error(f"Error formatting analyses: {str(e)}")
            return "Error retrieving stored proposals."

    def _get_space_proposals(self, space_id: str, state: str):
        try:
            proposals = self.connection_manager.perform_action(
                connection_name="snapshot",
                action_name="get-proposals",
                params=[space_id, state, 3],
            )

            if not proposals:
                return "No proposals found for the specified space and state."

            analyses = []
            for proposal in proposals:
                analysis = self._analyze_proposal(proposal)
                if analysis and "analysis" in analysis:
                    analyses.append(analysis["analysis"])

            if not analyses:
                return "Could not analyze any proposals."

            return "\n\n---\n\n".join(analyses)
        except Exception as e:
            logger.error(f"Error getting space proposals: {str(e)}")
            return f"Error retrieving proposals: {str(e)}"

    def _analyze_proposal(self, proposal, custom_prompt=""):
        try:
            if not proposal:
                return None

            base_prompt = """Analyze this Snapshot proposal and provide a structured analysis in the following format:

Title: [Proposal Title]
ID: [Proposal ID]
Status: [Current Status]
Deadline: [Voting Deadline]

Summary:
[2-3 sentences about main objectives]

Key Points:
- [Point 1]
- [Point 2]
- [Point 3]

Impact on CoW Protocol:
[1-2 sentences about impact]

Voting Recommendation:
[Clear recommendation with brief justification]

Priority Level: [High/Medium/Low]"""

            final_prompt = (
                f"{base_prompt}\n{custom_prompt}" if custom_prompt else base_prompt
            )

            response = self.agent.invoke(
                {
                    "input": f"Analyze this proposal:\n{json.dumps(proposal, indent=2)}\n\nInstructions: {final_prompt}",
                    "name": self.name,
                    "bio": self.bio,
                    "instructions": final_prompt,
                    "chat_history": "",
                }
            )

            analysis_text = response.get("output", "Failed to analyze proposal")
            if analysis_text == "Failed to analyze proposal":
                logger.error("Failed to get analysis from LLM")
                return None

            return {
                "id": proposal.get("id", "unknown"),
                "analysis": analysis_text,
                "processed_at": int(time.time()),
                "space": proposal.get("space", {}).get("id", "unknown"),
                "state": proposal.get("state", "unknown"),
            }

        except Exception as e:
            logger.error(f"Failed to analyze proposal: {str(e)}")
            return None

    def _load_proposals(self):
        if self.proposals_file.exists():
            with open(self.proposals_file, "r") as f:
                return json.load(f)
        return []

    def _update_proposals(self, space_id: str):
        try:
            current_time = time.time()
            if (
                current_time - self.state["last_proposals_check"] < 300
            ):  # Check every 5 minutes
                return

            raw_proposals = self.connection_manager.perform_action(
                connection_name="snapshot",
                action_name="get-proposals",
                params=[space_id, "passed", 3],
            )

            if raw_proposals:
                # Load existing analyzed proposals
                existing_analyses = self._load_proposals()
                existing_ids = {p["id"] for p in existing_analyses}

                # Analyze new proposals
                new_analyses = []
                for proposal in raw_proposals:
                    if proposal.get("id") not in existing_ids:
                        analysis = self._analyze_proposal(proposal)
                        if analysis:
                            new_analyses.append(analysis)
                            logger.info(f"Analyzed new proposal: {proposal.get('id')}")

                # Update storage with new analyses
                if new_analyses:
                    all_analyses = existing_analyses + new_analyses
                    self._save_proposals(all_analyses)
                    logger.info(f"Added {len(new_analyses)} new proposal analyses")

                self.state["last_proposals_check"] = current_time

        except Exception as e:
            logger.error(f"Failed to update proposals: {str(e)}")

    def loop(self):
        logger.info("\n🚀 Starting agent loop...")
        logger.info("Press Ctrl+C to stop")

        try:
            while True:
                try:
                    current_time = time.time()
                    if current_time - self.state["last_check"] >= 15:
                        self.state["last_check"] = current_time
                        self._update_messages()
                        self._update_proposals("cow.eth")
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Error in loop: {e}")
                    time.sleep(5)
        except KeyboardInterrupt:
            logger.info("\n👋 Agent stopped")

    def _get_insight(self, query: str) -> str:
        try:
            from src.prompts import (
                CIP_38_COMMUNITY_PROMPT,
                CIP_38_INSIGHT_PROMPT,
                COW_SWAP_SOLVER_PROMPT,
            )

            query = query.lower()

            if "community" in query or "think" in query:
                return CIP_38_COMMUNITY_PROMPT
            elif "cip-38" in query or "cip 38" in query:
                return CIP_38_INSIGHT_PROMPT
            elif "solver" in query or "cowswap" in query:
                return COW_SWAP_SOLVER_PROMPT
            else:
                return CIP_38_INSIGHT_PROMPT

        except Exception as e:
            logger.error(f"Error getting insight: {str(e)}")
            return "Error retrieving insight"

    def _get_analysis(self, cip_number: str) -> str:
        try:
            proposals = self._load_proposals()
            cip_id = f"CIP-{cip_number}"

            for proposal in proposals:
                if cip_id.lower() in proposal.get("analysis", "").lower():
                    return proposal["analysis"]

            return f"No analysis found for {cip_id}. Please check if this proposal exists and has been analyzed."
        except Exception as e:
            logger.error(f"Error getting CIP insight: {str(e)}")
            return f"Error retrieving insight for {cip_id}"
