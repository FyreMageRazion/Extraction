from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

from dotenv import load_dotenv, find_dotenv
from pathlib import Path
import os
import json
# Attempt to locate a .env file in common locations:
# 1. standard .env in project root
# 2. .venv/.env (some setups place environment there)
env_path = find_dotenv()
if not env_path:
    root_env = Path(__file__).resolve().parent / ".env"
    venv_env = Path(__file__).resolve().parent / ".venv" / ".env"
    if root_env.exists():
        env_path = str(root_env)
    elif venv_env.exists():
        env_path = str(venv_env)

if env_path:
    load_dotenv(env_path)

import asyncio


async def run_chat(
    mcp_config: dict,
    system_prompt: str,
    history_path: str = "history.json",
    persist_history: bool = True,
    model: str = "gpt-3.5-turbo",
):
    # Ensure OPENAI API KEY available
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY not set. Export it in the environment or create a .env file and load it."
        )

    # --- Build MCP client and fetch tools ---
    client = MultiServerMCPClient(mcp_config)
    tools = await client.get_tools()

    # --- Create agent ---
    if create_agent is None:
        raise RuntimeError(
            "create_agent helper not found. Provide a create_agent utility that accepts "
            "model, tools, system_prompt (or adapt the script to construct a LangGraph agent)."
        )

    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
    )

    # --- Load / initialize conversation history ---
    history_file = Path(history_path)
    conv_history = []
    if persist_history and history_file.exists():
        try:
            conv_history = json.loads(history_file.read_text(encoding="utf-8"))
        except Exception:
            conv_history = []

    # Ensure the system message is first
    if not conv_history or conv_history[0].get("role") != "system":
        conv_history.insert(0, {"role": "system", "content": system_prompt})

    print("LangGraph MCP chat started. Type messages. Type 'exit' or 'quit' to end.")

    # Multi-turn loop; agent called with entire history each turn
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting conversation (keyboard interrupt).")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Exiting conversation (user requested).")
            break

        # Append user turn
        conv_history.append({"role": "user", "content": user_input})

        # Call agent. Common pattern: agent.ainvoke({"messages": conv_history})
        try:
            response = await agent.ainvoke({"messages": conv_history})
        except Exception as e:
            print("Agent invocation failed:", repr(e))
            # Optionally continue loop so user can try again
            continue

        # Extract assistant message robustly
        assistant_text = None
        if isinstance(response, dict):
            # many implementations return {'messages': [ ... ]}
            msgs = response.get("messages")
            if isinstance(msgs, list) and msgs:
                last = msgs[-1]
                # last may be a dict-like or object with .content
                assistant_text = (
                    (last.get("content") if isinstance(last, dict) else None)
                    or getattr(last, "content", None)
                    or response.get("content")
                    or response.get("text")
                )
        elif isinstance(response, str):
            assistant_text = response

        if not assistant_text:
            assistant_text = "<no content returned by agent>"

        # Print and append assistant reply
        print("\nAgent:", assistant_text)
        conv_history.append({"role": "assistant", "content": assistant_text})

        # Persist history
        if persist_history:
            try:
                history_file.write_text(json.dumps(conv_history, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception as e:
                print("Warning: failed to persist history:", e)

    # End of conversation
    print("Conversation closed. History saved to", history_path if persist_history else "not persisted.")


if __name__ == "__main__":
    # Example MCP config matching your earlier snippet
    mcp_config = {
        "orders": {
            "url": "http://localhost:8000/mcp",   # FastMCP default if you run a local MCP server
            "transport": "streamable_http",
        }
    }

    system_prompt = (
        "You are an orders management customer support agent. "
        "Give detailed responses — include all the details you have about the customer's order(s). "
        "If the customer wants to cancel the order, ask for a specific order_id to cancel. You can cencel only if only if the order is in the ORDERED status. You should polietely prevent cancellation for other statuses like DISPATCHED, CANCELLED, DELIVERED, or IN_TRANSIT."
        "Answer follow-ups. This conversation persists across turns and only exits when the user types 'exit' or 'quit'."
    )

    asyncio.run(run_chat(mcp_config=mcp_config, system_prompt=system_prompt))

'''
Example questions:
What is the order status of cust_1?
What is the order status of cust_1? I actually have 3 orders which one is cancelled
'''