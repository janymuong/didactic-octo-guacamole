from dotenv import load_dotenv
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from typing import List, Dict
import asyncio
import nest_asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime

nest_asyncio.apply()

# Load environment variables from .env file
load_dotenv()

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

class Rastuc_Corp:

    def __init__(self):
        # Initialize session and client objects
        self.session: ClientSession = None
        # Initialize OpenAI client - API key will be loaded from OPENAI_API_KEY env var
        self.openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.available_tools: List[dict] = []
        self.context = ConversationContext()

    async def process_query(self, query):
        # Add user query to context
        self.context.add_message('user', query)
        self.context.last_query = query
        
        # Get recent conversation context
        messages = self.context.get_recent_context()
        
        # If this is a follow-up about papers, add the last papers to the context
        if any(word in query.lower() for word in ['last', 'previous', 'those', 'these', 'paper', 'number']):
            # Get last papers
            try:
                result = await self.session.call_tool('get_last_papers')
                # Convert TextContent to native Python type
                papers = json.loads(str(result.content)) if result.content else []
                self.context.set_last_papers(papers)
                if self.context.last_papers:
                    # Add papers context
                    messages.append({
                        'role': 'system',
                        'content': f"Last searched papers: {json.dumps(self.context.last_papers, indent=2)}"
                    })
            except Exception as e:
                print(f"Error getting last papers: {e}")
        
        response = self.openai.chat.completions.create(
            model='gpt-4o',  # OpenAI GPT-4o model
            messages=messages,
            tools=self.available_tools,
            max_tokens=2024
        )
        
        process_query = True
        while process_query:
            message = response.choices[0].message
            
            if message.content:
                print(message.content)
                self.context.add_message('assistant', message.content)
                
            if message.tool_calls:
                # Add assistant message with tool calls
                self.context.add_message(
                    'assistant',
                    message.content,
                    tool_calls=message.tool_calls
                )
                
                # Process each tool call
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    tool_id = tool_call.id
                    
                    print(f"Calling tool {tool_name} with args {tool_args}")
                    
                    # Call the MCP tool
                    result = await self.session.call_tool(tool_name, arguments=tool_args)
                    
                    # Convert TextContent to string for context
                    result_content = str(result.content)
                    
                    # Add tool result to context
                    self.context.add_message(
                        'tool',
                        result_content,
                        tool_call_id=tool_id
                    )
                    
                    # Update last papers if search was performed
                    if tool_name == 'search_papers':
                        try:
                            papers_result = await self.session.call_tool('get_last_papers')
                            # Convert TextContent to native Python type
                            papers = json.loads(str(papers_result.content)) if papers_result.content else []
                            self.context.set_last_papers(papers)
                        except Exception as e:
                            print(f"Error updating last papers: {e}")
                
                # Get next response from OpenAI
                response = self.openai.chat.completions.create(
                    model='gpt-4o',
                    messages=self.context.get_recent_context(),
                    tools=self.available_tools,
                    max_tokens=2024
                )
            else:
                # No tool calls, conversation is complete
                process_query = False

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nRastuc Corp started in MCP! \n An AI agent to get you scientfic papers from arXiv.org, and extract the information you need")
        print("Type your research topic or 'quit' to exit.")
        
        while True:
            try:
                query = input("\nRastuc Corp:) ").strip()
        
                if query.lower() == 'quit':
                    break
                    
                await self.process_query(query)
                print("\n")
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    async def connect_to_server_and_run(self):
        # Create server parameters for stdio connection
        server_params = StdioServerParameters(
            command="uv",  # Executable
            args=["run", "research_server.py"],  # Optional command line arguments
            env=None,  # Optional environment variables
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                self.session = session
                # Initialize the connection
                await session.initialize()
    
                # List available tools
                response = await session.list_tools()
                
                tools = response.tools
                print("\nConnected to server with tools:", [tool.name for tool in tools])
                
                # Convert MCP tools to OpenAI format
                self.available_tools = [{
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema
                    }
                } for tool in response.tools]
    
                await self.chat_loop()


async def main():
    chatbot = Rastuc_Corp()
    await chatbot.connect_to_server_and_run()
  

if __name__ == "__main__":
    asyncio.run(main())