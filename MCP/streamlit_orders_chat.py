# streamlit_orders_chat.py
"""
Streamlit chatbot that integrates with the Orders MCP server via langchain_mcp_adapters.

Run:
    pip install streamlit langchain langchain-mcp-adapters python-dotenv
    streamlit run streamlit_orders_chat.py
"""

import os
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv, find_dotenv

import streamlit as st
import httpx

# Attempt to import LangChain MCP adapter
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    LC_MCP_AVAILABLE = True
except ImportError:
    print("Warning: langchain-mcp-adapters not installed. HTTP mode will be used.")
    LC_MCP_AVAILABLE = False

# Required LangChain imports
try:
    from langchain.agents import AgentType, initialize_agent
    from langchain.chat_models import ChatOpenAI
except ImportError as e:
    print(f"Error: Required LangChain package not found: {e}")
    print("Please install the required packages:")
    print("pip install langchain openai")
    raise


class HttpMCPClient:
    """Simple HTTP-based MCP client that mimics MultiServerMCPClient interface."""
    def __init__(self, url: str):
        self.url = url
        self._client = httpx.AsyncClient()
        self._tools_cache = None

    async def close(self):
        await self._client.aclose()

    def _format_tool_for_langchain(self, tool_info: Dict[str, Any]) -> Dict[str, Any]:
        """Format MCP tool info into LangChain tool format."""
        name = tool_info["id"].replace("-", "_")  # Ensure valid function name
        params = tool_info.get("input_schema", {})
        param_properties = {
            k: {"type": "string" if v == "string" else "integer" if v == "int" else v}
            for k, v in params.items()
        }
        
        # Create a LangChain compatible tool schema
        return {
            "name": name,
            "description": tool_info.get("description", ""),
            "parameters": {
                "type": "object",
                "properties": param_properties,
                "required": list(params.keys())
            },
            "return_direct": False,  # Let LangChain handle response formatting
            "function": {
                "name": name,
                "description": tool_info.get("description", ""),
                "parameters": {
                    "type": "object",
                    "properties": param_properties,
                    "required": list(params.keys())
                }
            }
        }

    async def get_tools(self) -> List[Dict[str, Any]]:
        """Get tools from MCP server and format them for LangChain."""
        if self._tools_cache is not None:
            return self._tools_cache

        print("Discovering MCP tools...")
        # Try initialize first (newer protocol)
        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"}
        }
        r = await self._client.post(self.url, json=init_payload)
        r.raise_for_status()
        data = r.json()
        tools_list = []
        
        if "result" in data and "capabilities" in data["result"]:
            caps = data["result"]["capabilities"]
            if "tools" in caps and isinstance(caps["tools"], dict):
                tools_list = list(caps["tools"].values())
                print("Found tools via initialize:", [t.get("id") for t in tools_list])

        if not tools_list:
            # Fallback: discover_tools
            print("No tools in initialize response, trying discover_tools...")
            disc_payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "discover_tools"
            }
            r2 = await self._client.post(self.url, json=disc_payload)
            r2.raise_for_status()
            data = r2.json()
            if "result" in data:
                tools_list = data["result"].get("tools", [])
            else:
                tools_list = data.get("tools", [])
            print("Found tools via discover_tools:", [t.get("id") for t in tools_list])

        if not tools_list:
            print("Warning: No tools found from MCP server")
            return []

        # Format tools for LangChain
        langchain_tools = []
        for tool in tools_list:
            formatted_tool = self._format_tool_for_langchain(tool)
            # Create callable async tool function
            tool_name = formatted_tool["name"]
            
            async def tool_func(*args, _tool_name=tool_name, **kwargs):
                """Dynamic tool function that calls the MCP server."""
                merged_args = {**kwargs}
                if args:
                    print(f"Warning: Unexpected positional args for {_tool_name}:", args)
                return await self.call_tool(_tool_name, merged_args)
            
            # Add the callable to the tool definition
            formatted_tool["func"] = tool_func
            formatted_tool["coroutine"] = tool_func  # For async support
            langchain_tools.append(formatted_tool)

        print("Formatted tools for LangChain:", [t["name"] for t in langchain_tools])
        self._tools_cache = langchain_tools
        return langchain_tools

        # Format tools for OpenAI function calling
        formatted_tools = [self._format_tool_for_openai(tool) for tool in tools_list]
        self._tools_cache = formatted_tools
        return formatted_tools

    async def call_tool(self, tool_name: str, input_dict: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Call a tool on the MCP server using JSON-RPC 2.0."""
        print(f"Calling tool {tool_name} with inputs:", input_dict)
        
        # Convert tool name format
        mcp_tool_name = tool_name.replace("_", "-")
        
        payload = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "call_tool",
            "params": {
                "tool": mcp_tool_name,
                "input": input_dict
            }
        }
        
        print("Sending MCP request:", json.dumps(payload, indent=2))
        r = await self._client.post(self.url, json=payload)
        r.raise_for_status()
        data = r.json()
        print("MCP response:", json.dumps(data, indent=2))
        
        if "error" in data:
            error_info = data["error"]
            error_msg = error_info.get("message", str(error_info))
            raise RuntimeError(f"Tool call failed: {error_msg}")
        
        result = data.get("result", {})
        # Format the result in a way LangChain expects
        if isinstance(result, dict):
            if "orders" in result:  # list_recent_orders response
                return {"orders": json.dumps(result["orders"], indent=2)}
            elif "order" in result:  # get_order_status response
                return {"status": json.dumps(result["order"], indent=2)}
            else:
                return {"result": json.dumps(result, indent=2)}
        return {"result": str(result)}


# -----------------------------------------------------------------------------
# Load environment
# -----------------------------------------------------------------------------
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

# Defaults
DEFAULT_MCP_URL = os.getenv("MCP_URL", "http://127.0.0.1:8080/mcp")
DEFAULT_MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o")

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_KEY


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def run_async(coro):
    """Safely run async coroutines inside Streamlit."""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


def safe_rerun():
    """Call Streamlit's experimental_rerun if available (no-op otherwise)."""
    rerun = getattr(st, "experimental_rerun", None)
    if callable(rerun):
        try:
            rerun()
        except Exception:
            pass


async def async_load_agent(mcp_url: str, model_name: str) -> bool:
    """
    Load the LangChain agent and tools from MCP in async mode.
    Returns True if successful, False otherwise.
    """
    print(f"\n=== Starting Async Agent Loading ===")
    print(f"URL: {mcp_url}")
    print(f"Model: {model_name}")
    print(f"Client Mode: {st.session_state.get('client_mode', 'unset')}")
    
async def async_load_agent(mcp_url: str, model_name: str) -> bool:
    """
    Load the LangChain agent and tools from MCP in async mode.
    Returns True if successful, False otherwise.
    """
    try:
        print(f"\n=== Starting Async Agent Loading ===")
        print(f"URL: {mcp_url}")
        print(f"Model: {model_name}")
        print(f"Client Mode: {st.session_state.get('client_mode', 'unset')}")
        
        # Clear existing objects if we're reloading
        if "reloading" in st.session_state and st.session_state.reloading:
            print("Reloading requested - clearing existing objects")
            st.session_state.pop("mcp_client_obj", None)
            st.session_state.pop("agent_obj", None)
            st.session_state.reloading = False
        
        # Choose client based on mode (adapter or direct HTTP)
        use_adapter = (st.session_state.get("client_mode", "http") == "adapter" and LC_MCP_AVAILABLE)
        print(f"Using {'Adapter' if use_adapter else 'HTTP'} mode")
        
        client = None
        try:
            # Client setup
            if "mcp_client_obj" not in st.session_state:
                print("Creating new MCP client...")
                if use_adapter:
                    # Try adapter path first
                    servers = {
                        "orders_http": {"url": mcp_url, "transport": "streamable_http"}
                    }
                    st.session_state.mcp_client_obj = MultiServerMCPClient(servers)
                    print("Created MultiServerMCPClient")
                else:
                    # Use HTTP fallback
                    st.session_state.mcp_client_obj = HttpMCPClient(mcp_url)
                    print("Created HttpMCPClient")
                    
            client = st.session_state.mcp_client_obj
            print(f"Client type: {type(client)}")
            
        except Exception as e:
            error_msg = f"Error creating MCP client: {type(e).__name__}: {str(e)}"
            print(error_msg)
            st.session_state.pop("mcp_client_obj", None)
            raise RuntimeError(error_msg) from e

        # Agent setup
        try:
            if "agent_obj" not in st.session_state:
                print("Creating new agent...")
                print("Fetching tools...")
                tools = await client.get_tools()
                
                print(f"\nDiscovered {len(tools)} tools:")
                
                def extract_tool_info(tool, idx):
                    """Safely extract name and description from a tool object"""
                    try:
                        if isinstance(tool, dict):
                            name = tool.get('name', tool.get('function', {}).get('name', str(tool)))
                            desc = tool.get('description', 'N/A')
                        else:
                            name = getattr(tool, 'name', str(tool))
                            desc = getattr(tool, 'description', 'N/A')
                        return f"{idx}. {name}\n   Description: {desc}"
                    except Exception as e:
                        return f"{idx}. Error getting tool info: {e}"
                
                # Log each tool's details
                try:
                    tool_summaries = [extract_tool_info(t, i) for i, t in enumerate(tools, 1)]
                    print("\n".join(tool_summaries))
                except Exception as e:
                    print(f"Error logging tool details: {e}")
                
                # Create a clean list of tool names for the agent creation
                tool_names = []
                try:
                    for t in tools:
                        try:
                            name = t.get("name") if isinstance(t, dict) else getattr(t, "name", None)
                            if name:
                                tool_names.append(name)
                        except Exception as e:
                            print(f"Error extracting tool name: {e}")
                            continue
                except Exception as e:
                    print(f"Error processing tool names: {e}")
                
                print("\nCreating agent with tools:", tool_names)
                
                # Create the LLM
                llm = ChatOpenAI(
                    model_name=model_name,
                    temperature=0,  # Use deterministic responses
                    verbose=True    # Log interactions
                )
                
                # Create the agent with explicit configuration
                agent = initialize_agent(
                    tools,
                    llm,
                    agent=AgentType.OPENAI_FUNCTIONS,
                    handle_parsing_errors=True,
                    return_intermediate_steps=True,
                    verbose=True,
                    agent_kwargs={
                        "system_message": (
                            "You are an order management assistant with access to these tools:\n\n"
                            "1. list_recent_orders - List orders for a customer (requires customer_id like 'cust_1')\n"
                            "2. get_order_status - Get detailed status of an order (requires order_id like 'cust_1-ord-1')\n"
                            "3. cancel_order - Cancel an order (requires order_id and reason)\n\n"
                            "Important guidelines:\n"
                            "- Customer IDs must be in format 'cust_1', 'cust_2', etc.\n"
                            "- Order IDs must be in format '{customer_id}-ord-{number}' like 'cust_1-ord-1'\n"
                            "- Always use exact ID formats - they are case sensitive\n"
                            "- If user asks about orders without an ID, ask for their customer ID\n"
                            "- For cancellations, always confirm and require a reason\n\n"
                            "Example interactions:\n"
                            "User: Show me my orders\n"
                            "Assistant: I'll help you check your orders. Could you please provide your customer ID? It should be in the format 'cust_1' or similar.\n\n"
                            "User: Show orders for cust_1\n"
                            "Assistant: I'll use the list_recent_orders tool to check the orders for customer cust_1.\n\n"
                            "Remember to always process the tool responses to provide clear, user-friendly summaries."
                        )
                    }
                )
                
                print("Storing agent in session state")
                st.session_state.agent_obj = agent
                
                # Optional: Store some debug info about the agent
                st.session_state.agent_info = {
                    "tool_count": len(tools),
                    "tool_names": tool_names,
                    "client_type": type(client).__name__,
                    "model": model_name
                }
        
            print("=== Agent Loading Complete ===")
            print(f"Agent type: {type(st.session_state.agent_obj)}")
            print(f"Client type: {type(st.session_state.mcp_client_obj)}")
            print(f"Agent info: {st.session_state.agent_info}")
            
            return True
            
        except Exception as e:
            error_msg = f"Error creating agent: {type(e).__name__}: {str(e)}"
            print(error_msg)
            # Clean up any partial state
            st.session_state.pop("agent_obj", None)
            st.session_state.pop("agent_info", None)
            raise RuntimeError(error_msg) from e
            
    except Exception as e:
        error_msg = f"Agent loading failed: {type(e).__name__}: {str(e)}"
        print(error_msg)
        # Clean up all state on outer error
        st.session_state.pop("mcp_client_obj", None)
        st.session_state.pop("agent_obj", None)
        st.session_state.pop("agent_info", None)
        raise RuntimeError(error_msg) from e

    try:
        # Tool setup
        if "agent_obj" not in st.session_state:
            print("Creating new agent...")
            print("Fetching tools...")
            tools = await client.get_tools()
            
            print(f"\nDiscovered {len(tools)} tools:")
            
            def extract_tool_info(tool, idx):
                """Safely extract name and description from a tool object"""
                try:
                    if isinstance(tool, dict):
                        name = tool.get('name', tool.get('function', {}).get('name', str(tool)))
                        desc = tool.get('description', 'N/A')
                    else:
                        name = getattr(tool, 'name', str(tool))
                        desc = getattr(tool, 'description', 'N/A')
                    return f"{idx}. {name}\n   Description: {desc}"
                except Exception as e:
                    return f"{idx}. Error getting tool info: {e}"
            
            # Log each tool's details
            try:
                tool_summaries = [extract_tool_info(t, i) for i, t in enumerate(tools, 1)]
                print("\n".join(tool_summaries))
            except Exception as e:
                print(f"Error logging tool details: {e}")
            
            # Create a clean list of tool names for the agent creation
            tool_names = []
            try:
                for t in tools:
                    try:
                        name = t.get("name") if isinstance(t, dict) else getattr(t, "name", None)
                        if name:
                            tool_names.append(name)
                    except Exception as e:
                        print(f"Error extracting tool name: {e}")
                        continue
            except Exception as e:
                print(f"Error processing tool names: {e}")
            
            print("\nCreating agent with tools:", tool_names)

            # Create the agent with explicit configuration
            agent = create_agent(
                model=model_name,
                tools=tools,
                system_prompt=(
                    "You are an order management assistant with access to these tools:\n\n"
                    "1. list_recent_orders - List orders for a customer (requires customer_id like 'cust_1')\n"
                    "2. get_order_status - Get detailed status of an order (requires order_id like 'cust_1-ord-1')\n"
                    "3. cancel_order - Cancel an order (requires order_id and reason)\n\n"
                    "Important guidelines:\n"
                    "- Customer IDs must be in format 'cust_1', 'cust_2', etc.\n"
                    "- Order IDs must be in format '{customer_id}-ord-{number}' like 'cust_1-ord-1'\n"
                    "- Always use exact ID formats - they are case sensitive\n"
                    "- If user asks about orders without an ID, ask for their customer ID\n"
                    "- For cancellations, always confirm and require a reason\n\n"
                    "Example interactions:\n"
                    "User: Show me my orders\n"
                    "Assistant: I'll help you check your orders. Could you please provide your customer ID? It should be in the format 'cust_1' or similar.\n\n"
                    "User: Show orders for cust_1\n"
                    "Assistant: I'll use the list_recent_orders tool to check the orders for customer cust_1.\n\n"
                    "Remember to always process the tool responses to provide clear, user-friendly summaries."
                ),
            )
            
            print("Storing agent in session state")
            st.session_state.agent_obj = agent
            
            # Optional: Store some debug info about the agent
            st.session_state.agent_info = {
                "tool_count": len(tools),
                "tool_names": [t.get("name") if isinstance(t, dict) else getattr(t, "name", str(t)) for t in tools],
                "client_type": type(client).__name__,
                "model": model_name
            }
        
        print("=== Agent Loading Complete ===")
        print(f"Agent type: {type(st.session_state.agent_obj)}")
        print(f"Client type: {type(st.session_state.mcp_client_obj)}")
        print(f"Agent info: {st.session_state.agent_info}")
        
        return True
        
    except Exception as e:
        error_msg = f"Error in async_load_agent: {type(e).__name__}: {str(e)}"
        print(error_msg)
        # Clean up any partial state
        st.session_state.pop("mcp_client_obj", None)
        st.session_state.pop("agent_obj", None)
        st.session_state.pop("agent_info", None)
        # Re-raise to let the outer handler deal with user display
        raise        print("Agent created successfully")

        st.session_state.agent_obj = agent
        st.session_state.agent_info = {"tool_count": len(tools)}
        st.session_state.agent_ready = True
        return True
    except Exception as exc:
        print("MultiServerMCPClient path failed with exception:", exc)
        try:
            await client.close()
        except Exception:
            pass
        # Ensure session state reflects failure
        st.session_state.agent_obj = None
        st.session_state.mcp_client_obj = None
        st.session_state.agent_ready = False
        return False


def load_tools_and_agent(mcp_url, model_name):
    """Run async MCP loading in blocking mode for Streamlit."""
    print("\n=== Starting Tool and Agent Loading ===")
    print(f"URL: {mcp_url}")
    print(f"Model: {model_name}")
    print(f"LangChain MCP Available: {LC_MCP_AVAILABLE}")
    
    if not LC_MCP_AVAILABLE and st.session_state.get("client_mode") == "adapter":
        st.error(
            "LangChain adapter mode selected but langchain-mcp-adapters is not installed.\n"
            "Run: pip install langchain-mcp-adapters\n"
            "Switching to HTTP mode..."
        )
        st.session_state.client_mode = "http"
    
    try:
        print("Running async_load_agent...")
        success = run_async(async_load_agent(mcp_url, model_name))
        
        # Verify the setup
        agent_ready = (
            st.session_state.agent_obj is not None and
            st.session_state.mcp_client_obj is not None
        )
        
        if not agent_ready:
            print("Warning: Agent objects not properly stored in session state")
            return False
            
        print(f"Agent setup completed. Success: {success}")
        print(f"Agent type: {type(st.session_state.agent_obj)}")
        print(f"Client type: {type(st.session_state.mcp_client_obj)}")
        
        return success
        
    except Exception as e:
        print(f"Error during agent setup: {type(e).__name__}: {str(e)}")
        st.error(
            f"Failed to load MCP tools or create agent:\n"
            f"Error Type: {type(e).__name__}\n"
            f"Details: {str(e)}"
        )
        return False


# -----------------------------------------------------------------------------
# Initialize session
# -----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are an assistant that can query order management tools."},
        {"role": "assistant", "content": "Hello! I can help you with:\n"
         "- Checking order status (e.g., 'What's the status of order cust_1-ord-1?')\n"
         "- Listing recent orders (e.g., 'Show orders for customer cust_1')\n"
         "- Canceling orders (with a reason)\n\n"
         "Please provide your customer ID (like 'cust_1') when asking about orders."}
    ]

if "agent_ready" not in st.session_state:
    st.session_state.agent_ready = False
if "agent_info" not in st.session_state:
    st.session_state.agent_info = None
if "mcp_client_obj" not in st.session_state:
    st.session_state.mcp_client_obj = None
if "agent_obj" not in st.session_state:
    st.session_state.agent_obj = None
if "client_mode" not in st.session_state:
    st.session_state.client_mode = "http"  # or "adapter"


# -----------------------------------------------------------------------------
# Streamlit UI
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Orders Chatbot (MCP)", layout="wide")
st.title("Orders Chatbot — MCP + LangChain + OpenAI")

col1, col2 = st.columns([3, 1])

with col2:
    st.markdown("### Configuration")
    mcp_url = st.text_input("MCP URL", value=DEFAULT_MCP_URL, key="cfg_mcp_url")
    
    # Client mode selection
    st.markdown("#### Client Mode")
    adapter_disabled = not LC_MCP_AVAILABLE
    client_mode = st.radio(
        "Select client implementation:",
        ["Direct HTTP", "LangChain Adapter"],
        index=0 if st.session_state.client_mode == "http" else 1,
        help=("Choose between direct HTTP calls or LangChain's adapter. " +
              "Install langchain-mcp-adapters to enable the adapter mode." if adapter_disabled else ""),
        disabled=adapter_disabled and st.session_state.client_mode == "adapter"
    )
    
    if adapter_disabled and client_mode == "LangChain Adapter":
        st.error(
            "LangChain adapter mode requires langchain-mcp-adapters package.\n"
            "Run: pip install langchain-mcp-adapters"
        )
    
    # Update session state if mode changed
    new_mode = "http" if client_mode == "Direct HTTP" else "adapter"
    mode_changed = st.session_state.client_mode != new_mode
    
    if mode_changed:
        st.session_state.client_mode = new_mode
        st.session_state.reloading = True  # Trigger agent reload
        
        # Update status
        if new_mode == "adapter" and not LC_MCP_AVAILABLE:
            st.error("Cannot switch to adapter mode - package not installed")
        else:
            st.info(f"Switching to {client_mode} mode...")
            safe_rerun()
    st.text_input("Model name", value=DEFAULT_MODEL_NAME, key="cfg_model_name")
    st.radio(
        "Client mode",
        ["Direct HTTP", "LangChain Adapter"],
        key="cfg_client_mode",
        help="Direct HTTP is more reliable; LangChain Adapter has more features but may have compatibility issues.",
    )

    if st.button("Load tools & create agent"):
        mcp_url = st.session_state.cfg_mcp_url
        model_name = st.session_state.cfg_model_name
        # Update session state from radio button
        st.session_state.client_mode = "adapter" if st.session_state.cfg_client_mode == "LangChain Adapter" else "http"

        success = load_tools_and_agent(mcp_url, model_name)
        if success:
            st.success("Agent ready — try chatting.")
        else:
            st.error("Agent initialization failed.")

    st.markdown("---")
    st.markdown("### Agent status")
    if st.session_state.agent_ready:
        st.success(f"✅ Ready — tools: {st.session_state.agent_info.get('tool_count')}")
    else:
        st.info("⚙️ Not loaded yet.")

with col1:
    st.markdown("### Chat")
    chat_box = st.container()
    with chat_box:
        for msg in st.session_state.messages:
            role = msg["role"]
            content = msg["content"]
            meta = msg.get("meta")
            if role == "user":
                st.markdown(f"**You:** {content}")
            elif role == "assistant":
                st.markdown(f"**Assistant:** {content}")
            else:
                st.markdown(f"**System:** {content}")
            if meta:
                st.json(meta)

    user_input = st.text_area("Your message", key="user_input", height=100)
    col_a, col_b = st.columns([1, 1])
    with col_a:
        send_btn = st.button("Send")
    with col_b:
        clear_btn = st.button("Clear chat")

    if clear_btn:
        st.session_state.messages = [{"role": "system", "content": "You are an assistant that can query order management tools."}]
        safe_rerun()

    if send_btn and user_input.strip():
        user_msg = user_input.strip()
        st.session_state.messages.append({"role": "user", "content": user_msg})

        # Create a status container
        status_container = st.empty()
        debug_container = st.expander("Show request debug info", expanded=False)
        
        with status_container:
            status = st.info("🔄 Processing request...")

        with debug_container:
            st.write("📝 Request details:")
            st.write(f"- Input message: '{user_msg}'")
            st.write(f"- Client mode: {st.session_state.get('client_mode', 'http')}")
            st.write(f"- Agent ready: {st.session_state.agent_ready}")

        # Check agent status
        if not st.session_state.agent_ready:
            status.warning("⚙️ Agent not ready — loading tools automatically...")
            with debug_container:
                st.write("🔧 Initializing agent and loading tools...")
            
            if not load_tools_and_agent(st.session_state.cfg_mcp_url, st.session_state.cfg_model_name):
                status.error("❌ Failed to load agent.")
                with debug_container:
                    st.error("Agent initialization failed. Check server connection and settings.")
                st.stop()

        agent = st.session_state.agent_obj
        if agent is None:
            status.error("❌ Agent unavailable")
            with debug_container:
                st.error("Agent object is None. Try reloading tools.")
            st.stop()

        # Update status to show thinking
        status.info("🤔 Thinking and preparing tools...")
        
        # Prepare messages payload
        payload = {
            "messages": [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
                if m["role"] != "system"
            ]
        }
        
        with debug_container:
            st.write("📤 Sending request to agent:")
            st.json(payload)

            try:
                with debug_container:
                    st.write("🔄 Preparing to invoke agent...")
                    st.write("Agent configuration:")
                    st.json({
                        "model": st.session_state.cfg_model_name,
                        "client_mode": st.session_state.get("client_mode", "http"),
                        "message_count": len(payload["messages"])
                    })
                
                status.info("🤖 Agent is processing request...")
                
                # Debug the agent object
                with debug_container:
                    st.write("Agent state check:")
                    st.write(f"- Agent object exists: {agent is not None}")
                    st.write(f"- Agent type: {type(agent)}")
                    st.write(f"- Available tools: {len(agent.tools) if hasattr(agent, 'tools') else 'unknown'}")
                    st.write("\nInvoking agent with payload:")
                    st.json(payload)
                
                print("\n=== Agent Invocation ===")
                print(f"Payload: {json.dumps(payload, indent=2)}")
                result = run_async(agent.ainvoke(payload))
                print(f"Raw result: {result}")
                
                with debug_container:
                    st.write("✅ Agent response received:")
                    st.json({
                        "result_type": type(result).__name__,
                        "raw_result": str(result),
                        "has_messages": "messages" in result if isinstance(result, dict) else False
                    })
                
            except Exception as exc:
                status.error(f"❌ Agent call failed: {exc}")
                with debug_container:
                    st.error("Detailed error info:")
                    st.exception(exc)
                    st.write("Agent state at failure:")
                    st.write(f"- Agent ready: {st.session_state.agent_ready}")
                    st.write(f"- Agent object: {type(st.session_state.agent_obj)}")
                    st.write(f"- Client object: {type(st.session_state.mcp_client_obj)}")
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {exc}"})
                safe_rerun()
                st.stop()

            # Parse agent reply
            status.info("📝 Processing agent's response...")
            assistant_text = None
            try:
                if isinstance(result, dict) and "messages" in result:
                    # Handle dictionary-style response
                    last_msg = result["messages"][-1]
                    if isinstance(last_msg, dict):
                        assistant_text = last_msg.get("content", "")
                    else:
                        # Handle LangChain message objects
                        assistant_text = getattr(last_msg, "content", str(last_msg))
                elif isinstance(result, str):
                    assistant_text = result
                else:
                    # Fallback: convert to string
                    assistant_text = str(result)
            except Exception as e:
                print("Error parsing agent response:", e)
                print("Raw result:", result)
                assistant_text = "Sorry, I encountered an error processing the response."

            st.session_state.messages.append({"role": "assistant", "content": assistant_text})

            # Show any tool metadata if available
            try:
                status.info("🔍 Checking for tool usage details...")
                meta = None
                if isinstance(result, dict):
                    # Check for tool calls in different formats
                    if "tool_calls" in result:
                        meta = result["tool_calls"]
                    elif "tool_call" in result:
                        meta = result["tool_call"]
                    elif "additional_kwargs" in result:
                        # LangChain might nest tool calls here
                        kwargs = getattr(result, "additional_kwargs", {})
                        if isinstance(kwargs, dict):
                            for k in ("tool_calls", "tool_call"):
                                if k in kwargs:
                                    meta = kwargs[k]
                                    break
                
                if meta:
                    with debug_container:
                        st.write("🛠️ Tools used:")
                        st.json(meta)
                    
                    # Add to chat with formatted metadata
                    formatted_meta = meta if isinstance(meta, (dict, list)) else {"data": str(meta)}
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": "💡 Tool execution details",
                        "meta": formatted_meta
                    })
                
                status.success("✅ Response processed successfully!")
                
            except Exception as e:
                with debug_container:
                    st.error("Error handling tool metadata:")
                    st.exception(e)
                    st.write("Raw result:", result)
                print("Error handling tool metadata:", e)
                print("Raw result:", result)
            
            finally:
                # Clear the status container after we're done
                status_container.empty()

    # Do not auto-rerun at the end of the script unconditionally - Streamlit
    # will re-run automatically on user interactions. Removing this prevents
    # repeated reruns and avoids modifying widget session_state after creation.

# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    """
**Example Commands**
- "List recent orders for customer cust_1"
- "What's the status of order cust_1-ord-1?"
- "Show me the latest orders for cust_2"
- "Cancel order cust_1-ord-1" (will ask for reason)

**Tips**
- Always use customer IDs like 'cust_1', 'cust_2', etc.
- Order IDs are in format 'cust_1-ord-1'
- The assistant will ask for your customer ID if needed
- Cancellations require a valid reason and cannot be undone
"""
)
