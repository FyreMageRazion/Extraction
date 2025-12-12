from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

from dotenv import load_dotenv, find_dotenv
from pathlib import Path
import os

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

async def main():
    client=MultiServerMCPClient(
        {
            "math":{
                "command":"python",
                "args":[str(Path(__file__).resolve().parent / "mathserver.py")],  # Using absolute path
                "transport":"stdio",
            
            },
            "weather": {
                "url": "http://localhost:8080/mcp",  # Using FastMCP default port
                "transport": "streamable_http",
            }

        }
    )

    # Ensure OPENAI_API_KEY is available (from environment or .env)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY not set. Create a .env file with OPENAI_API_KEY or set the environment variable."
        )
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

    tools=await client.get_tools()
    agent = create_agent(
    model="gpt-3.5-turbo",
    tools=tools,
    system_prompt="You are a helpful assistant",
)
    math_response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "what's (3 + 5) x 12?"}]}
    )

    print("Math response:", math_response['messages'][-1].content)

    weather_response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "what is the weather in California?"}]}
    )
    print("Weather response:", weather_response['messages'][-1].content)

asyncio.run(main())