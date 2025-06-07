from dotenv import load_dotenv
from openai import AsyncOpenAI
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from typing import List, Dict, TypedDict
from contextlib import AsyncExitStack, suppress
from dataclasses import dataclass, field
from datetime import datetime
import json
import asyncio
import signal
import sys
import os
import platform
import warnings

# Suppress ResourceWarning about unclosed pipes
warnings.filterwarnings("ignore", category=ResourceWarning)

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

class GracefulExit(SystemExit):
    pass

def handle_sigterm(signum, frame):
    print("\nReceived signal to terminate. Starting graceful shutdown...")
    raise GracefulExit()

# Set up signal handlers
signal.signal(signal.SIGINT, handle_sigterm)
signal.signal(signal.SIGTERM, handle_sigterm)

# Windows-specific event loop policy
if platform.system() == 'Windows':
    # Use the ProactorEventLoop by default on Windows
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

class ToolDefinition(TypedDict):
    name: str
    description: str
    input_schema: dict

@dataclass
class ConversationContext:
    messages: List[Dict] = field(default_factory=list)
    last_papers: List[Dict] = field(default_factory=list)
    last_query: str = ""
    
    def add_message(self, role: str, content: str, **kwargs):
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            **kwargs
        }
        self.messages.append(message)
        
    def set_last_papers(self, papers: List[Dict]):
        """Set the last papers list directly"""
        self.last_papers = papers if papers else []
            
    def get_last_papers(self) -> List[Dict]:
        return self.last_papers
    
    def get_recent_context(self, limit: int = 10) -> List[Dict]:
        return self.messages[-limit:]

class MCP_ChatBot:

    def __init__(self):
        # Initialize session and client objects
        self.sessions: List[ClientSession] = []
        self.exit_stack = AsyncExitStack()
        self.client = AsyncOpenAI()
        self.available_tools: List[ToolDefinition] = []
        self.tool_to_session: Dict[str, ClientSession] = {}
        self.context = ConversationContext()
        self.shutdown_event = asyncio.Event()
        self._closing = False

    async def connect_to_server(self, server_name: str, server_config: dict) -> None:
        """Connect to a single MCP server."""
        try:
            server_params = StdioServerParameters(**server_config)
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            self.sessions.append(session)
            
            # List available tools for this session
            response = await session.list_tools()
            tools = response.tools
            print(f"\nConnected to {server_name} with tools:", [t.name for t in tools])
            
            for tool in tools:
                self.tool_to_session[tool.name] = session
                self.available_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                })
        except Exception as e:
            print(f"Failed to connect to {server_name}: {e}")

    async def connect_to_servers(self):
        """Connect to all configured MCP servers."""
        try:
            with open("server_config.json", "r") as file:
                data = json.load(file)
            
            servers = data.get("mcpServers", {})
            
            for server_name, server_config in servers.items():
                await self.connect_to_server(server_name, server_config)
        except Exception as e:
            print(f"Error loading server configuration: {e}")
            raise
    
    async def process_query(self, query):
        # Add user query to context
        self.context.add_message('user', query)
        self.context.last_query = query
        
        # Get recent conversation context - filter out tool messages that don't have corresponding tool calls
        messages = []
        for msg in self.context.get_recent_context():
            if msg['role'] != 'tool' or ('tool_call_id' in msg and any(
                m for m in self.context.messages if m.get('tool_calls') and 
                any(call.get('id') == msg['tool_call_id'] for call in m['tool_calls'])
            )):
                messages.append(msg)
        
        # If this is a paper-related query, check for last papers
        if any(word in query.lower() for word in ['paper', 'research', 'article', 'publication']):
            for session in self.sessions:
                try:
                    if 'get_last_papers' in [t.name for t in (await session.list_tools()).tools]:
                        result = await session.call_tool('get_last_papers')
                        try:
                            papers = json.loads(str(result.content)) if result.content else []
                            self.context.set_last_papers(papers)
                            if self.context.last_papers:
                                messages.append({
                                    'role': 'system',
                                    'content': f"Last searched papers: {json.dumps(self.context.last_papers, indent=2)}"
                                })
                        except json.JSONDecodeError:
                            print("Warning: Could not parse last papers JSON")
                        break
                except Exception as e:
                    print(f"Warning: Error getting last papers: {e}")
        
        process_query = True
        while process_query:
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    tools=[{
                        "type": "function",
                        "function": {
                            "name": tool["name"],
                            "description": tool["description"],
                            "parameters": tool["input_schema"]
                        }
                    } for tool in self.available_tools],
                    tool_choice="auto"
                )
                
                assistant_message = response.choices[0].message
                
                # If the assistant wants to use a tool
                if assistant_message.tool_calls:
                    # Convert tool calls to dict format for storage
                    tool_calls_dict = [{
                        'id': tc.id,
                        'type': tc.type,
                        'function': {
                            'name': tc.function.name,
                            'arguments': tc.function.arguments
                        }
                    } for tc in assistant_message.tool_calls]
                    
                    # Add assistant message with tool calls
                    self.context.add_message(
                        'assistant',
                        assistant_message.content if assistant_message.content else "",
                        tool_calls=tool_calls_dict
                    )
                    
                    for tool_call in assistant_message.tool_calls:
                        try:
                            # Call the tool
                            tool_name = tool_call.function.name
                            tool_args = json.loads(tool_call.function.arguments)
                            
                            print(f"Calling tool {tool_name} with args {tool_args}")
                            
                            session = self.tool_to_session[tool_name]
                            result = await session.call_tool(tool_name, arguments=tool_args)
                            
                            # Add tool result to context
                            self.context.add_message(
                                'tool',
                                str(result.content),
                                tool_call_id=tool_call.id
                            )
                            
                            # Update last papers if search was performed
                            if tool_name == 'search_papers':
                                try:
                                    papers_result = await session.call_tool('get_last_papers')
                                    papers = json.loads(str(papers_result.content)) if papers_result.content else []
                                    self.context.set_last_papers(papers)
                                except Exception as e:
                                    print(f"Warning: Error updating last papers: {e}")
                        except Exception as e:
                            print(f"Warning: Error calling tool {tool_name}: {e}")
                            self.context.add_message(
                                'tool',
                                f"Error calling tool {tool_name}: {str(e)}",
                                tool_call_id=tool_call.id
                            )
                    
                    # Update messages for next iteration
                    messages = []
                    for msg in self.context.get_recent_context():
                        if msg['role'] != 'tool' or ('tool_call_id' in msg and any(
                            m for m in self.context.messages if m.get('tool_calls') and 
                            any(call.get('id') == msg['tool_call_id'] for call in m['tool_calls'])
                        )):
                            messages.append(msg)
                else:
                    # If no tool use, just print and store the response
                    print(assistant_message.content if assistant_message.content else "")
                    self.context.add_message(
                        'assistant',
                        assistant_message.content if assistant_message.content else ""
                    )
                    process_query = False
                    
            except Exception as e:
                print(f"Error during query processing: {e}")
                process_query = False

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nOmniMind Nexus - The Multi-Server Intelligence Hub")
        print("✧══════════════════════════════════════════✧")
        print("Connected to multiple servers, ready to orchestrate knowledge and tools.")
        print("Type your queries or 'quit' to exit.")
        print("✧══════════════════════════════════════════✧")
        
        while not self.shutdown_event.is_set():
            try:
                query = input("\nNexus:) ").strip()
        
                if query.lower() == 'quit':
                    break
                    
                await self.process_query(query)
                print("\n")
                    
            except (EOFError, KeyboardInterrupt, GracefulExit):
                print("\nReceived signal to terminate...")
                break
            except Exception as e:
                print(f"\nError: {e}")
                if not self.shutdown_event.is_set():
                    continue
                break

    async def cleanup(self):
        """Cleanly close all resources using AsyncExitStack."""
        if self._closing:
            return
        self._closing = True
        
        print("\nCleaning up resources...")
        try:
            # Set shutdown event
            self.shutdown_event.set()
            
            # Close all sessions
            await self.exit_stack.aclose()
            
            # Cancel all pending tasks except the current one
            current_task = asyncio.current_task()
            tasks = [t for t in asyncio.all_tasks() if t is not current_task]
            
            # Cancel all other tasks
            for task in tasks:
                task.cancel()
            
            # Wait for tasks to complete with a timeout
            if tasks:
                with suppress(asyncio.TimeoutError):
                    await asyncio.wait(tasks, timeout=2)
            
            # Close any remaining transports
            for session in self.sessions:
                if hasattr(session, '_transport'):
                    with suppress(Exception):
                        session._transport.close()
                        
        except Exception as e:
            print(f"Error during cleanup: {e}")


async def main():
    chatbot = None
    try:
        chatbot = MCP_ChatBot()
        await chatbot.connect_to_servers()
        await chatbot.chat_loop()
    except (GracefulExit, KeyboardInterrupt):
        print("\nStarting graceful shutdown...")
    except Exception as e:
        print(f"\nError in main loop: {e}")
    finally:
        if chatbot:
            await chatbot.cleanup()

def run():
    """Wrapper function to handle the event loop"""
    try:
        if platform.system() == 'Windows':
            # Windows-specific handling
            asyncio.run(main())
        else:
            # Unix-like systems
            asyncio.run(main())
    except (KeyboardInterrupt, GracefulExit):
        print("\nShutdown complete.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    finally:
        # Cleanup any remaining asyncio resources
        if platform.system() == 'Windows':
            with suppress(Exception):
                loop = asyncio.get_event_loop()
                if not loop.is_closed():
                    loop.close()

if __name__ == "__main__":
    run()
