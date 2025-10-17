from crewai import Agent, Task
from crewai.tools import tool
from typing import Dict, Any, List, Tuple, Optional
import chromadb
from retrieval.rag_pipeline import retrieve_context_for_query
import re
import json

# Global collection variable for tool access
_collection = None
_grep_tool = None

def set_collection(collection: chromadb.Collection):
    """Set the global collection for tool access."""
    global _collection
    _collection = collection

def set_grep_tool(grep_tool):
    """Set the global GREP tool for keyword search."""
    global _grep_tool
    _grep_tool = grep_tool


@tool("smart_search")
def smart_search_tool(search_query: str, max_chunks: int = 10) -> str:
    """
    Perform an intelligent search in the documentation.
    Use this to search for specific information with reformulated queries.
    Returns formatted documentation chunks ready to present to the user.
    """
    try:
        if _collection is None:
            return "Error: Vector database collection not initialized"

        # Perform search with lower threshold for researcher to evaluate
        context, metadata = retrieve_context_for_query(
            collection=_collection,
            query=search_query,
            max_chunks=max_chunks,
            similarity_threshold=0.4  # Lower threshold, let agent evaluate
        )

        if not context or context.strip() == "No relevant documentation found.":
            return f"No relevant documentation found for query: {search_query}\n\nTry a different search approach."

        # Return the formatted context along with evaluation metadata
        chunks_found = metadata['chunks_found']
        avg_similarity = sum(metadata['similarity_scores']) / len(metadata['similarity_scores']) if metadata['similarity_scores'] else 0
        max_similarity = max(metadata['similarity_scores']) if metadata['similarity_scores'] else 0

        result = f"""Search Results for: "{search_query}"
Found: {chunks_found} chunks | Avg Similarity: {avg_similarity:.2f} | Max Similarity: {max_similarity:.2f}

{context}
"""
        return result

    except Exception as e:
        return f"Error during search: {str(e)}"


@tool("evaluate_results")
def evaluate_results_tool(search_results: str) -> str:
    """
    Evaluate if search results adequately answer the query.

    IMPORTANT: Pass the EXACT output from smart_search_tool directly.

    Example usage:
        results = smart_search_tool("quantum circuit")
        evaluation = evaluate_results_tool(results)

    Returns an assessment with confidence score and recommendations.
    """
    try:
        # Extract similarity scores from the search results header
        # Format: "Found: X chunks | Avg Similarity: Y | Max Similarity: Z"
        if "No relevant documentation found" in search_results:
            return "EVALUATION: No results found. Try reformulating the query with different terms."

        # Parse similarity metrics from header
        avg_match = re.search(r'Avg Similarity: ([\d.]+)', search_results)
        max_match = re.search(r'Max Similarity: ([\d.]+)', search_results)
        chunks_match = re.search(r'Found: (\d+) chunks', search_results)

        if not (avg_match and max_match and chunks_match):
            return "EVALUATION: Could not parse search results. Results may still be useful - review the content."

        avg_score = float(avg_match.group(1))
        max_score = float(max_match.group(1))
        chunks_found = int(chunks_match.group(1))

        # Evaluate adequacy
        adequate = max_score > 0.6 and avg_score > 0.45
        confidence = min(1.0, (max_score + avg_score) / 2)

        if adequate:
            return f"EVALUATION: Good results! (Confidence: {confidence:.1%})\nThese {chunks_found} chunks show high relevance and should answer the query well."
        elif confidence > 0.3:
            return f"EVALUATION: Moderate results (Confidence: {confidence:.1%})\nThe {chunks_found} chunks may be helpful, but consider trying more specific search terms."
        else:
            return f"EVALUATION: Low relevance (Confidence: {confidence:.1%})\nThese {chunks_found} chunks don't seem very relevant. Try a completely different search approach."

    except Exception as e:
        return f"EVALUATION: Error evaluating results: {str(e)}\nResults may still be useful - review the content."


@tool("grep_search")
def grep_search_tool(keyword: str, doc_ids: Optional[str] = None, case_sensitive: bool = False) -> str:
    """
    Search for exact keyword matches in documents using GREP.
    Use this when you need precise keyword or term matching (e.g., function names, error codes, specific terms).

    Args:
        keyword: The exact keyword or phrase to search for
        doc_ids: Optional comma-separated list of doc_ids to search (e.g., "doc_0,doc_5,doc_10")
        case_sensitive: Whether search should be case-sensitive

    Returns:
        Matches with context showing where the keyword appears
    """
    if not _grep_tool:
        return "GREP tool not available. Use smart_search instead."

    try:
        # Parse doc_ids if provided
        doc_id_list = None
        if doc_ids:
            doc_id_list = [d.strip() for d in doc_ids.split(',')]

        # Perform GREP search
        matches = _grep_tool.grep_search(
            pattern=keyword,
            doc_ids=doc_id_list,
            case_sensitive=case_sensitive,
            context_chars=150,
            max_matches_per_doc=3,
            max_total_matches=15
        )

        if not matches:
            return f"No exact matches found for '{keyword}'"

        # Format results
        return _grep_tool.format_grep_results(matches, max_display=10)

    except Exception as e:
        return f"Error in GREP search: {str(e)}"


@tool("find_code_examples")
def find_code_examples_tool(keyword: str, doc_ids: Optional[str] = None) -> str:
    """
    Find code examples containing a specific keyword or function.
    Use this when the user asks for code examples or wants to see how something is used.

    Args:
        keyword: Keyword to search for in code blocks (e.g., "cudaq.sample", "qvector")
        doc_ids: Optional comma-separated list of doc_ids to search

    Returns:
        Code examples containing the keyword
    """
    if not _grep_tool:
        return "GREP tool not available. Use smart_search instead."

    try:
        # Parse doc_ids if provided
        doc_id_list = None
        if doc_ids:
            doc_id_list = [d.strip() for d in doc_ids.split(',')]

        # Find code examples
        examples = _grep_tool.find_code_examples(
            keyword=keyword,
            doc_ids=doc_id_list,
            max_examples=10
        )

        if not examples:
            return f"No code examples found containing '{keyword}'"

        # Format results
        output = [f"Found {len(examples)} code examples with '{keyword}':\n"]

        for i, example in enumerate(examples, 1):
            output.append(f"\n## Example {i}: {example['doc_title']}")
            output.append(f"URL: {example['doc_url']}")
            output.append(f"\n```\n{example['code']}\n```\n")

        return "\n".join(output)

    except Exception as e:
        return f"Error finding code examples: {str(e)}"


@tool("keyword_ranked_search")
def keyword_ranked_search_tool(query: str, doc_ids: Optional[str] = None, top_k: int = 10) -> str:
    """
    Perform BM25-ranked keyword search across documents.
    Use this for multi-term queries where you want documents ranked by keyword relevance.

    Args:
        query: Search query with multiple keywords
        doc_ids: Optional comma-separated list of doc_ids to search
        top_k: Number of top results to return

    Returns:
        Ranked list of documents with relevance scores
    """
    if not _grep_tool:
        return "GREP tool not available. Use smart_search instead."

    try:
        # Parse doc_ids if provided
        doc_id_list = None
        if doc_ids:
            doc_id_list = [d.strip() for d in doc_ids.split(',')]

        # Perform ranked search
        results = _grep_tool.keyword_search_ranked(
            query=query,
            doc_ids=doc_id_list,
            top_k=top_k
        )

        if not results:
            return f"No results found for query: {query}"

        # Format results
        from tools.grep_search import format_bm25_results
        return format_bm25_results(results, _grep_tool.documents, max_display=10)

    except Exception as e:
        return f"Error in keyword search: {str(e)}"


def create_researcher_agent(collection: chromadb.Collection, config: Dict[str, Any], grep_tool=None) -> Agent:
    """
    Create an intelligent researcher agent that:
    1. Analyzes user queries
    2. Reformulates them into effective search queries
    3. Uses GREP for exact matches and RAG for semantic search
    4. Evaluates search results
    5. Iteratively refines searches if needed
    6. Selects the most relevant chunks to pass on
    """
    set_collection(collection)

    # Set GREP tool if provided
    if grep_tool:
        set_grep_tool(grep_tool)

    agent_config = config.get('agents', {}).get('researcher_agent', {})
    target_name = config.get('target', {}).get('name', 'Documentation')

    # Build tools list
    tools = [smart_search_tool, evaluate_results_tool]

    # Add GREP tools if available
    if grep_tool:
        tools.extend([grep_search_tool, find_code_examples_tool, keyword_ranked_search_tool])

    agent = Agent(
        role=agent_config.get('role', 'Research Specialist'),
        goal=agent_config.get('goal',
            f'Find the most relevant {target_name} documentation through intelligent hybrid search (RAG + GREP)'),
        backstory=agent_config.get('backstory', f"""
You are an expert research specialist with deep knowledge of {target_name}.
You excel at:
- Understanding complex user queries and their underlying intent
- Choosing the right search strategy (semantic RAG vs exact GREP)
- Reformulating queries to match documentation structure and terminology
- Evaluating search results for relevance and quality
- Making intelligent decisions about which information is most valuable
- Iteratively refining searches when initial results are inadequate

Your search strategy:
- Use GREP tools (grep_search, find_code_examples) for:
  * Specific function/class names
  * Error codes or exact error messages
  * Code examples with specific APIs
  * Precise technical terms
- Use RAG tools (smart_search) for:
  * Conceptual questions
  * "How to" queries
  * General explanations
  * Topic overviews

You think strategically about search:
- Breaking complex queries into focused sub-queries
- Using domain-specific terminology
- Considering multiple angles and phrasings
- Evaluating both high-level concepts and specific technical details
- Combining GREP precision with RAG's semantic understanding
        """.strip()),
        tools=tools,
        verbose=True,
        memory=True,
        allow_delegation=False,
        max_iter=15  # Allow multiple iterations for refinement
    )

    return agent


def create_research_task(user_query: str, agent: Agent, config: Dict[str, Any]) -> Task:
    """Create an intelligent research task."""
    target_name = config.get('target', {}).get('name', 'Documentation')

    task_description = f"""
Research and find the most relevant {target_name} documentation for this user query:

"{user_query}"

Your research process should be:

1. ANALYZE THE QUERY
   - Identify the core intent and information need
   - Extract key concepts and technical terms
   - Determine what type of information would best answer this (conceptual, API docs, examples, troubleshooting, etc.)

2. PLAN YOUR SEARCH STRATEGY
   - Consider multiple search angles
   - Identify domain-specific terminology that might appear in docs
   - Think about how documentation is typically structured

3. EXECUTE SEARCHES
   - Start with your best reformulated query using smart_search_tool
   - The tool returns formatted documentation chunks ready to use
   - Optionally use evaluate_results_tool to check if you need more searches
   - Example:
     search_output = smart_search_tool("cudaq boson operators")
     # search_output now contains formatted documentation chunks
   - If results are inadequate, try alternative approaches:
     * Different terminology or phrasing
     * Breaking complex queries into smaller sub-queries
     * Searching for related concepts
     * Broadening or narrowing scope

4. ITERATE INTELLIGENTLY
   - Try up to 3-4 different search approaches if needed
   - Learn from what worked and what didn't
   - Combine insights from multiple searches if helpful

5. COMPILE FINAL ANSWER
   - Take the best documentation chunks from your searches
   - Present them in a clear, user-friendly format
   - Remove search metadata and evaluation notes
   - Focus on providing the actual documentation content

IMPORTANT:
- Be strategic, not mechanical
- Quality over quantity
- If no good results after multiple attempts, explain what you tried and why it didn't work
- Always use the tools to search and evaluate - don't make up information
"""

    task = Task(
        description=task_description,
        expected_output=f"""
Provide the complete documentation content that answers the user's query.

Your output should be structured as follows:

1. ANSWER SUMMARY (2-3 sentences)
   - A brief, direct answer to the user's query

2. RELEVANT DOCUMENTATION
   - The full content of the most relevant documentation chunks (3-5 chunks with similarity > 0.5)
   - Include complete code examples, API descriptions, and explanations
   - Present the actual documentation text, not just metadata

3. ADDITIONAL CONTEXT (if helpful)
   - Any supplementary information that enhances understanding
   - Related concepts or alternative approaches

DO NOT include:
- Search strategy details (save those for internal logging)
- Similarity scores or technical metadata
- JSON formatting - use clear markdown sections instead

Focus on providing a complete, helpful answer that the user can directly use.
        """.strip(),
        agent=agent
    )

    return task


def parse_research_results(research_output: str) -> Dict[str, Any]:
    """Parse the researcher agent's output into a structured format."""
    try:
        # Try to parse as JSON first
        if '{' in research_output and '}' in research_output:
            # Extract JSON from the output
            json_match = re.search(r'\{.*\}', research_output, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))

        # Fallback: create structure from text
        return {
            "raw_output": research_output,
            "parsed": False,
            "message": "Could not parse as JSON, returning raw output"
        }
    except Exception as e:
        return {
            "raw_output": research_output,
            "parsed": False,
            "error": str(e)
        }


def extract_relevant_chunks(research_output: str) -> List[Dict[str, Any]]:
    """Extract the relevant documentation chunks from research output."""
    try:
        parsed = parse_research_results(research_output)

        if parsed.get("parsed") and "selected_chunks" in parsed:
            return parsed["selected_chunks"]

        # Fallback: extract from text
        chunks = []
        # Look for chunk markers in output
        chunk_pattern = r'## Context \d+:(.*?)(?=## Context \d+:|$)'
        matches = re.findall(chunk_pattern, research_output, re.DOTALL)

        for i, match in enumerate(matches):
            chunks.append({
                "index": i,
                "content": match.strip()
            })

        return chunks
    except Exception as e:
        print(f"Error extracting chunks: {e}")
        return []
