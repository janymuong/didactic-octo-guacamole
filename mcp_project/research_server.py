import arxiv
import json
import os
from typing import List, Dict
from mcp.server.fastmcp import FastMCP
from dataclasses import dataclass, field
from datetime import datetime

PAPER_DIR = "papers"

@dataclass
class ConversationHistory:
    """Class to maintain conversation state and history"""
    messages: List[Dict] = field(default_factory=list)
    last_papers: List[Dict] = field(default_factory=list)
    
    def add_user_message(self, message: str):
        self.messages.append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat()
        })
    
    def add_system_message(self, message: str):
        self.messages.append({
            'role': 'system',
            'content': message,
            'timestamp': datetime.now().isoformat()
        })
    
    def set_last_papers(self, papers: List[Dict]):
        self.last_papers = papers
    
    def get_last_papers(self) -> List[Dict]:
        return self.last_papers
    
    def get_recent_messages(self, limit: int = 5) -> List[Dict]:
        return self.messages[-limit:]

# Initialize FastMCP server
mcp = FastMCP("research")
conversation = ConversationHistory()

@mcp.tool()
def search_papers(topic: str, max_results: int = 5) -> List[str]:
    """
    Search for papers on arXiv based on a topic and store their information.
    
    Args:
        topic: The topic to search for
        max_results: Maximum number of results to retrieve (default: 5)
        
    Returns:
        List of paper IDs found in the search
    """
    
    # Use arxiv to find the papers 
    client = arxiv.Client()

    # Search for the most relevant articles matching the queried topic
    search = arxiv.Search(
        query = topic,
        max_results = max_results,
        sort_by = arxiv.SortCriterion.Relevance
    )

    papers = client.results(search)
    
    # Create directory for this topic
    path = os.path.join(PAPER_DIR, topic.lower().replace(" ", "_"))
    os.makedirs(path, exist_ok=True)
    
    file_path = os.path.join(path, "papers_info.json")

    # Try to load existing papers info
    try:
        with open(file_path, "r") as json_file:
            papers_info = json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError):
        papers_info = {}

    # Process each paper and add to papers_info  
    paper_ids = []
    found_papers = []
    for paper in papers:
        paper_id = paper.get_short_id()
        paper_ids.append(paper_id)
        paper_info = {
            'id': paper_id,
            'title': paper.title,
            'authors': [author.name for author in paper.authors],
            'summary': paper.summary,
            'pdf_url': paper.pdf_url,
            'published': str(paper.published.date())
        }
        papers_info[paper_id] = paper_info
        found_papers.append(paper_info)
    
    # Save updated papers_info to json file
    with open(file_path, "w") as json_file:
        json.dump(papers_info, json_file, indent=2)
    
    # Update conversation history with found papers
    conversation.set_last_papers(found_papers)
    
    print(f"Results are saved in: {file_path}")
    return paper_ids

@mcp.tool()
def extract_info(paper_id: str) -> str:
    """
    Search for information about a specific paper across all topic directories.
    
    Args:
        paper_id: The ID of the paper to look for
        
    Returns:
        JSON string with paper information if found, error message if not found
    """
    # First check in conversation history
    for paper in conversation.get_last_papers():
        if paper['id'] == paper_id:
            return json.dumps(paper, indent=2)
 
    # If not found in history, search in files
    for item in os.listdir(PAPER_DIR):
        item_path = os.path.join(PAPER_DIR, item)
        if os.path.isdir(item_path):
            file_path = os.path.join(item_path, "papers_info.json")
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r") as json_file:
                        papers_info = json.load(json_file)
                        if paper_id in papers_info:
                            return json.dumps(papers_info[paper_id], indent=2)
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    print(f"Error reading {file_path}: {str(e)}")
                    continue
    
    return f"There's no saved information related to paper {paper_id}."

@mcp.tool()
def get_last_papers() -> str:
    """
    Get information about the papers from the last search.
    
    Returns:
        JSON string containing paper information
    """
    papers = conversation.get_last_papers()
    return json.dumps(papers if papers else [])

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')