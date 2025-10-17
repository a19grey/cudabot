from crewai import Agent, Task
from crewai.tools import tool
from typing import Dict, Any, List
import chromadb
from retrieval.rag_pipeline import retrieve_context_for_query
from embeddings.vector_store import get_relevant_context_chunks

# Global collection variable for tool access
_collection = None

def set_collection(collection: chromadb.Collection):
    """Set the global collection for tool access."""
    global _collection
    _collection = collection

@tool("document_retrieval")
def document_retrieval_tool(query: str, max_chunks: int = 5, similarity_threshold: float = 0.5) -> str:
    """Retrieve relevant documentation chunks based on a query. Use this tool to find information from the knowledge base."""
    try:
        if _collection is None:
            return "Error: Vector database collection not initialized"

        context, metadata = retrieve_context_for_query(
            collection=_collection,
            query=query,
            max_chunks=max_chunks,
            similarity_threshold=similarity_threshold
        )

        if not context or context.strip() == "No relevant documentation found.":
            return f"No relevant documentation found for query: '{query}'"

        # Add metadata information
        result = f"Retrieved {metadata['chunks_found']} relevant documentation chunks:\n\n"
        result += context

        return result

    except Exception as e:
        return f"Error retrieving documentation: {str(e)}"


def create_query_understanding_agent(collection: chromadb.Collection, config: Dict[str, Any]) -> Agent:
    """Create the query understanding and retrieval agent."""
    agent_config = config.get('agents', {}).get('query_agent', {})

    # Set the collection for tool access
    set_collection(collection)

    agent = Agent(
        role=agent_config.get('role', 'Documentation Specialist'),
        goal=agent_config.get('goal', 'Find and organize relevant documentation'),
        backstory=agent_config.get('backstory', 'Expert in finding relevant information'),
        tools=[document_retrieval_tool],
        verbose=True,
        memory=True,
        allow_delegation=False
    )

    return agent


def create_query_understanding_task(query: str, agent: Agent, config: Dict[str, Any]) -> Task:
    """Create task for query understanding and retrieval."""
    target_info = config.get('target', {})
    target_name = target_info.get('name', 'Documentation')

    task_description = f"""
    Analyze the user query and retrieve the most relevant {target_name} documentation.

    User Query: "{query}"

    Your responsibilities:
    1. Use the document_retrieval tool to find relevant documentation
    2. Analyze the retrieved content for relevance to the query
    3. Organize the information in a clear, structured way
    4. Identify key concepts, examples, and code snippets if present
    5. Note any gaps or areas where additional information might be needed

    Provide a comprehensive summary of the relevant documentation that directly addresses the user's query.
    Include specific quotes and code examples when available.
    """

    task = Task(
        description=task_description,
        expected_output=(
            "A structured summary of relevant documentation including:\n"
            "- Key concepts and explanations\n"
            "- Code examples if applicable\n"
            "- Step-by-step instructions if requested\n"
            "- Links to source documentation\n"
            "- Any important caveats or considerations"
        ),
        agent=agent
    )

    return task


# Atomic functions for query processing

def analyze_query_intent(query: str) -> Dict[str, Any]:
    """Analyze query to determine user intent."""
    from retrieval.rag_pipeline import preprocess_query
    return preprocess_query(query)


def validate_retrieval_results(results: str, query: str) -> Dict[str, Any]:
    """Validate that retrieval results are relevant to the query."""
    if not results or results.strip() == "No relevant documentation found.":
        return {
            'is_valid': False,
            'confidence': 0.0,
            'issues': ['No documentation found'],
            'suggestions': ['Try broader search terms', 'Check query spelling']
        }

    # Simple validation checks
    query_lower = query.lower()
    results_lower = results.lower()

    # Check if key query terms appear in results
    query_words = [word for word in query_lower.split() if len(word) > 3]
    found_words = [word for word in query_words if word in results_lower]

    relevance_score = len(found_words) / len(query_words) if query_words else 0.0

    validation = {
        'is_valid': relevance_score > 0.3,
        'confidence': min(1.0, relevance_score * 2),
        'found_terms': found_words,
        'missing_terms': [word for word in query_words if word not in found_words],
        'issues': [],
        'suggestions': []
    }

    if relevance_score < 0.5:
        validation['issues'].append('Low relevance to query terms')
        validation['suggestions'].append('Consider rephrasing the query')

    return validation


def format_agent_output(raw_output: str, query: str) -> Dict[str, Any]:
    """Format agent output into structured response."""
    return {
        'query': query,
        'response': raw_output,
        'agent_type': 'query_agent',
        'timestamp': None,  # Will be set by caller
        'metadata': {
            'response_length': len(raw_output),
            'has_code': 'code' in raw_output.lower() or '```' in raw_output
        }
    }


def extract_key_concepts(documentation_text: str) -> List[str]:
    """Extract key concepts from documentation text."""
    import re

    # Look for headers, bold text, and code terms
    concepts = set()

    # Extract headers (markdown style)
    headers = re.findall(r'#+\s*([^#\n]+)', documentation_text)
    concepts.update([h.strip() for h in headers])

    # Extract bold/emphasized terms
    bold_terms = re.findall(r'\*\*([^*]+)\*\*', documentation_text)
    concepts.update([t.strip() for t in bold_terms])

    # Extract code-like terms (camelCase, snake_case)
    code_terms = re.findall(r'\b[a-z]+(?:[A-Z][a-z]*)+\b|\b[a-z]+(?:_[a-z]+)+\b', documentation_text)
    concepts.update(code_terms[:10])  # Limit to avoid noise

    # Filter out very short or common terms
    filtered_concepts = [c for c in concepts if len(c) > 3 and c.lower() not in
                        {'with', 'from', 'this', 'that', 'will', 'have', 'more', 'used'}]

    return sorted(list(filtered_concepts))[:15]  # Return top 15


def summarize_documentation_content(content: str, max_length: int = 500) -> str:
    """Create a brief summary of documentation content."""
    if len(content) <= max_length:
        return content

    # Try to find natural break points
    sentences = content.split('. ')
    summary = ""

    for sentence in sentences:
        if len(summary + sentence + '. ') <= max_length:
            summary += sentence + '. '
        else:
            break

    if not summary:
        # Fallback: truncate at word boundary
        words = content[:max_length].split()
        summary = ' '.join(words[:-1]) + '...'

    return summary.strip()


def identify_code_examples(documentation_text: str) -> List[Dict[str, str]]:
    """Identify and extract code examples from documentation."""
    import re

    code_examples = []

    # Find markdown code blocks
    code_blocks = re.findall(r'```(\w+)?\n(.*?)\n```', documentation_text, re.DOTALL)

    for i, (language, code) in enumerate(code_blocks):
        code_examples.append({
            'type': 'code_block',
            'language': language or 'unknown',
            'code': code.strip(),
            'index': i
        })

    # Find inline code
    inline_code = re.findall(r'`([^`]+)`', documentation_text)

    for i, code in enumerate(inline_code):
        if len(code) > 10:  # Only include substantial inline code
            code_examples.append({
                'type': 'inline_code',
                'language': 'unknown',
                'code': code.strip(),
                'index': i
            })

    return code_examples


def assess_documentation_completeness(query: str, documentation_text: str) -> Dict[str, Any]:
    """Assess if documentation adequately addresses the query."""
    query_analysis = analyze_query_intent(query)

    # Check coverage based on query intent
    completeness = {
        'overall_score': 0.5,  # Default neutral
        'coverage_areas': [],
        'missing_areas': [],
        'recommendations': []
    }

    intent = query_analysis['intent']

    if intent == 'how_to':
        # Look for step-by-step instructions
        has_steps = bool(re.search(r'\b(step|steps|first|next|then|finally)\b', documentation_text, re.IGNORECASE))
        completeness['coverage_areas'].append('instructions') if has_steps else completeness['missing_areas'].append('step_by_step')

    if intent == 'example' or query_analysis['is_code_query']:
        # Look for code examples
        code_examples = identify_code_examples(documentation_text)
        if code_examples:
            completeness['coverage_areas'].append('code_examples')
        else:
            completeness['missing_areas'].append('code_examples')
            completeness['recommendations'].append('Look for additional code examples')

    if intent == 'what_is':
        # Look for definitions and explanations
        has_definitions = bool(re.search(r'\b(is|are|means|refers to|definition)\b', documentation_text, re.IGNORECASE))
        completeness['coverage_areas'].append('definitions') if has_definitions else completeness['missing_areas'].append('definitions')

    # Calculate overall score
    total_areas = len(completeness['coverage_areas']) + len(completeness['missing_areas'])
    if total_areas > 0:
        completeness['overall_score'] = len(completeness['coverage_areas']) / total_areas

    return completeness