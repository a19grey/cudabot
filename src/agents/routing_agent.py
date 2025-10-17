"""
Document routing agent that uses hierarchical map and summaries
to intelligently select relevant document subsets before retrieval.
"""

from crewai import Agent, Task
from crewai.tools import tool
from typing import Dict, Any, List, Optional
import json


# Global state for routing
_lookup_data = None
_doc_map = None


def set_routing_data(lookup_data: Dict[str, Any], doc_map: Dict[str, Any]):
    """Set the global routing data for tool access."""
    global _lookup_data, _doc_map
    _lookup_data = lookup_data
    _doc_map = doc_map


@tool("explore_document_structure")
def explore_document_structure_tool(path_query: str = "") -> str:
    """
    Explore the hierarchical document structure.
    Use this to understand document organization and find relevant sections.

    Args:
        path_query: Optional path to explore (e.g., "latest/using" or empty for top-level)

    Returns:
        Formatted structure showing available paths and documents
    """
    if not _doc_map:
        return "Error: Document map not loaded"

    hierarchy = _doc_map.get('hierarchy', {})

    # Navigate to requested path
    current = hierarchy
    if path_query:
        parts = path_query.strip('/').split('/')
        for part in parts:
            if part in current:
                if '_subdirs' in current[part]:
                    current = current[part]['_subdirs']
                else:
                    current = current[part]
            else:
                return f"Path '{path_query}' not found in document structure"

    # Format current level
    output = [f"Document Structure at: /{path_query}" if path_query else "Document Structure (Top Level)"]
    output.append("=" * 60)
    output.append("")

    # List subdirectories
    if isinstance(current, dict):
        subdirs = [k for k in current.keys() if k not in ['_subdirs', '_documents']]
        if subdirs:
            output.append("📁 Subdirectories:")
            for subdir in sorted(subdirs)[:20]:  # Limit to 20
                output.append(f"  - {subdir}/")
            output.append("")

        # List documents
        if '_documents' in current:
            docs = current['_documents']
            if docs:
                output.append(f"📄 Documents ({len(docs)}):")
                for doc in docs[:10]:  # Show first 10
                    output.append(f"  - {doc.get('title', 'Untitled')}")
                    output.append(f"    ID: {doc.get('doc_id')}")
                    output.append(f"    File: {doc.get('filename')}")
                    if doc.get('headers'):
                        output.append(f"    Sections: {', '.join(doc['headers'][:3])}")
                    output.append("")
                if len(docs) > 10:
                    output.append(f"  ... and {len(docs) - 10} more documents")

    return "\n".join(output)


@tool("search_summaries")
def search_summaries_tool(keywords: str) -> str:
    """
    Search document summaries for keywords to find relevant documents.
    This is faster than full document search and helps identify which docs to look at.

    Args:
        keywords: Space-separated keywords to search for

    Returns:
        List of matching documents with their summaries
    """
    if not _lookup_data:
        return "Error: Lookup data not loaded"

    summaries = _lookup_data.get('summaries', {})
    keywords_lower = keywords.lower().split()

    matches = []
    for doc_id, doc_info in summaries.items():
        summary = doc_info.get('summary', '').lower()
        title = doc_info.get('title', '').lower()

        # Count keyword matches
        match_count = sum(1 for kw in keywords_lower if kw in summary or kw in title)

        if match_count > 0:
            matches.append((match_count, doc_id, doc_info))

    # Sort by relevance
    matches.sort(reverse=True)

    if not matches:
        return f"No summaries found matching keywords: {keywords}"

    output = [f"Found {len(matches)} documents matching '{keywords}':", ""]

    for i, (count, doc_id, doc_info) in enumerate(matches[:15], 1):  # Top 15
        output.append(f"## {i}. {doc_info.get('title', 'Untitled')} (Matches: {count})")
        output.append(f"ID: {doc_id}")
        output.append(f"Path: {doc_info.get('path', 'N/A')}")
        output.append(f"Summary: {doc_info.get('summary', 'No summary')}")
        output.append(f"Has Code: {'Yes' if doc_info.get('has_code') else 'No'}")
        output.append("")

    if len(matches) > 15:
        output.append(f"... and {len(matches) - 15} more matches")

    return "\n".join(output)


@tool("get_document_list_by_path")
def get_document_list_by_path_tool(path_pattern: str) -> str:
    """
    Get list of document IDs for a specific path or pattern.
    Use this after exploring structure to get doc IDs for focused search.

    Args:
        path_pattern: Path pattern (e.g., "latest/using/" or "api/")

    Returns:
        List of document IDs matching the path
    """
    if not _doc_map:
        return "Error: Document map not loaded"

    documents = _doc_map.get('documents', {})
    pattern_lower = path_pattern.lower().strip('/')

    matching_docs = []
    for doc_id, doc in documents.items():
        doc_path = doc.get('path', '').lower()
        if pattern_lower in doc_path:
            matching_docs.append({
                'doc_id': doc_id,
                'title': doc.get('title', 'Untitled'),
                'path': doc.get('path', ''),
                'url': doc.get('url', '')
            })

    if not matching_docs:
        return f"No documents found matching path pattern: {path_pattern}"

    output = [f"Found {len(matching_docs)} documents in path '{path_pattern}':", ""]

    for doc in matching_docs[:20]:  # Limit to 20
        output.append(f"- {doc['doc_id']}: {doc['title']}")
        output.append(f"  Path: {doc['path']}")
        output.append("")

    if len(matching_docs) > 20:
        output.append(f"... and {len(matching_docs) - 20} more documents")

    output.append("\nUse these doc_ids for focused GREP or RAG searches.")

    return "\n".join(output)


def create_routing_agent(lookup_data: Dict[str, Any], doc_map: Dict[str, Any],
                        config: Dict[str, Any]) -> Agent:
    """
    Create a routing agent that uses document structure and summaries
    to identify relevant document subsets.

    Args:
        lookup_data: Combined lookup data with summaries
        doc_map: Hierarchical document map
        config: Target configuration

    Returns:
        CrewAI Agent configured for document routing
    """
    # Set global data for tools
    set_routing_data(lookup_data, doc_map)

    target_name = config.get('target', {}).get('name', 'Documentation')

    agent = Agent(
        role="Document Navigator",
        goal=f"Intelligently route queries to relevant {target_name} documentation subsets",
        backstory=f"""You are an expert at navigating {target_name} documentation structure.
You understand how documentation is organized and can quickly identify which sections
and documents are most relevant for any query.

Your strengths:
- Understanding document hierarchy and organization
- Identifying relevant paths based on query intent
- Using summaries to quickly assess document relevance
- Recommending targeted document subsets for detailed search

You use the document structure and summaries to narrow down searches,
making retrieval faster and more accurate.""",
        tools=[
            explore_document_structure_tool,
            search_summaries_tool,
            get_document_list_by_path_tool
        ],
        verbose=True,
        memory=True,
        allow_delegation=False
    )

    return agent


def create_routing_task(user_query: str, agent: Agent, config: Dict[str, Any]) -> Task:
    """
    Create a routing task to identify relevant document subsets.

    Args:
        user_query: User's query
        agent: Routing agent
        config: Target configuration

    Returns:
        CrewAI Task for routing
    """
    target_name = config.get('target', {}).get('name', 'Documentation')

    task_description = f"""
Analyze this query and identify the most relevant {target_name} documentation subset:

"{user_query}"

Your process:

1. UNDERSTAND THE QUERY
   - What is the user asking about?
   - What type of information do they need (tutorial, API, examples, troubleshooting)?
   - What technical terms or concepts are mentioned?

2. EXPLORE DOCUMENT STRUCTURE
   - Use explore_document_structure_tool to understand organization
   - Identify relevant paths or sections (e.g., "api/", "examples/", "guides/")

3. SEARCH SUMMARIES
   - Use search_summaries_tool with key terms from the query
   - Identify which specific documents are most relevant

4. GET DOCUMENT IDS
   - Use get_document_list_by_path_tool for promising paths
   - Compile a targeted list of doc_ids to search

Your goal is to narrow down from potentially hundreds of documents to a focused
subset (ideally 5-20 documents) that are most likely to answer the query.
"""

    task = Task(
        description=task_description,
        expected_output=f"""
A routing recommendation with:

1. RECOMMENDED DOCUMENT SUBSET
   - List of specific doc_ids to search (5-20 docs)
   - Why these documents are relevant

2. RECOMMENDED SEARCH STRATEGY
   - Should we use GREP (for exact keywords/code) or RAG (for concepts)?
   - What search terms or patterns to use?

3. RELEVANT PATHS
   - Which sections/paths of the documentation are most relevant?

Format as clear, actionable guidance for the search phase.
""",
        agent=agent
    )

    return task
