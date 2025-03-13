"""
This file contains the prompt templates used for generating content in various tasks.
These templates are formatted strings that will be populated with dynamic data at runtime.
"""

# Twitter prompts
POST_TWEET_PROMPT = (
    "Generate an engaging tweet. Don't include any hashtags, links or emojis. Keep it under 280 characters."
    "The tweets should be pure commentary, do not shill any coins or projects apart from {agent_name}. Do not repeat any of the"
    "tweets that were given as example. Avoid the words AI and crypto."
)

REPLY_TWEET_PROMPT = "Generate a friendly, engaging reply to this tweet: {tweet_text}. Keep it under 280 characters. Don't include any usernames, hashtags, links or emojis. "


# Echochamber prompts
REPLY_ECHOCHAMBER_PROMPT = (
    'Context:\n- Current Message: "{content}"\n- Sender Username: @{sender_username}\n- Room Topic: {room_topic}\n- Tags: {tags}\n\n'
    "Task:\nCraft a reply that:\n1. Addresses the message\n2. Aligns with topic/tags\n3. Engages participants\n4. Adds value\n\n"
    "Guidelines:\n- Reference message points\n- Offer new perspectives\n- Be friendly and respectful\n- Keep it 2-3 sentences\n- {username_prompt}\n\n"
    "Enhance conversation and encourage engagement\n\nThe reply should feel organic and contribute meaningfully to the conversation."
)


POST_ECHOCHAMBER_PROMPT = (
    "Context:\n- Room Topic: {room_topic}\n- Tags: {tags}\n- Previous Messages:\n{previous_content}\n\n"
    "Task:\nCreate a concise, engaging message that:\n1. Aligns with the room's topic and tags\n2. Builds upon Previous Messages without repeating them, or repeating greetings, introductions, or sentences.\n"
    "3. Offers fresh insights or perspectives\n4. Maintains a natural, conversational tone\n5. Keeps length between 2-4 sentences\n\nGuidelines:\n- Be specific and relevant\n- Add value to the ongoing discussion\n- Avoid generic statements\n- Use a friendly but professional tone\n- Include a question or discussion point when appropriate\n\n"
    "The message should feel organic and contribute meaningfully to the conversation."
)

CIP_38_INSIGHT_PROMPT = """**📜 Sure! Let me walk you through CIP-38, a proposal created by Haris Angelidakis, Andrea Canidio and Felix Henneke, that introduced Solver Computed Fees & Rank by Surplus.**

CIP-38 was essentially about revamping how fees work on the CoW Protocol.

**🔹 Before March 2024:**
When the proposed changes were implemented, users paid fees that went into a pot, and the protocol used those funds to reimburse solvers (the smart algorithms that crunch numbers and find the best trades) for their gas costs. But that system wasn't perfect: most of the time it failed to pass along the surplus from batching orders to the end users and required CoW to constantly monitor solvers.

**✨ What the authors proposed:**
Instead of the protocol handling all these fees, they suggested letting solvers collect their own "network fees" directly. This means they'd charge exactly what they need to cover their gas costs, no more, no less. And the best thing was that, according to the authors, competition among solvers ensured they didn't overcharge.

What's more, the authors suggested a change in the mechanism of "protocol fees" introduced in CIP-34 (ask me if you need context on that!). Authors suggested that Solvers would collect this fee on behalf of the CoW DAO (that's us!) and pay it out in COW tokens. According to the authors, it gives the token real utility and creates demand, which could boost its value.

**To sum up, the authors claim that their proposal:**
• Simplifies everything by cutting out middleman steps
• Encourages fair competition among solvers
• Boosts the value of COW tokens

**Analysis:**
On one hand, this proposal simplifies the fee structure dramatically, reduces overhead for the protocol, and introduces a new use case for the COW token. On the other hand, there are legitimate concerns about solver behavior — if left unchecked, they might exploit their power to set fees, potentially harming users or smaller solvers."""

CIP_38_COMMUNITY_PROMPT = """
💬 Here are some of the most valuable discussion points that were voiced by the community: 
**copiumnicus** 🧑‍💻 (X: @copiumnicus, known as Copium Capital, solver in CoW Swap) generally supported the proposal, but voiced some criticism: 
• **COW payments** 💰: @copiumnicus pointed out that requiring solvers to pay in COW could expose solvers to large losses due to the token's volatility. He suggested accepting fees in ETH instead. 
• **Data availability** 📊: in order to self-configure fees, solvers need higher data availability for the auctions that are happening. He proposes that the auctions are immediately available through API not 64 blocks later when they are finalized. 
**AndreaC** 👨‍🔬 (X: @AndreaCanidio, research economist in CoWSwap) replied to the criticism: 
• **COW payments** 💸: @AndreaCanidio pointed out that CoW DAO will also specify the currency in which fees are computed. It can be ETH or any other currency. However, independently of that currency, the payment should occur in COW. 
• **Data availability** 📈: @AndreaCanidio agreed that @copiumnicus has a good point. However, he mentioned that solvers should already have the auction ID as part of the instance, which can be used to look up auction data.
"""

COW_SWAP_SOLVER_PROMPT = """🔄 **Solver Competition on CoW Swap** 
💡 Solver competition is one of the most important features on CoW Swap. 
🔹 CoW Protocol groups user orders into batches and auctions them off to bonded third parties known as solvers to execute. 
Then, solvers simulate solutions to the batch and then bid against each other in a batch auction for the right to execute the transactions onchain. 
🏆 CoW Protocol currently has the largest solver network of any intents-based trading platform. To learn more about solvers, you can check out our docs 
(https://docs.cow.fi/cow-protocol/concepts/introduction/solvers) or Dune dashboard (https://dune.com/cowprotocol/solver-info) 
📜 **Recent Community Proposals** 
In the last 6 months, there have been several community proposals that changed the way solvers operate: 
•  **CIP-57**: Solver rewards on all chains 
•  **CIP-55**: Slashing of the GlueX Protocol solver and the CoW DAO bonding pool 
❓ Want me to elaborate on one of them?"""
