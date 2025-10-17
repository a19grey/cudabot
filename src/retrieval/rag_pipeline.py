from typing import List, Dict, Any, Optional, Tuple
import re
from embeddings.vector_store import search_similar_chunks, hybrid_search, get_relevant_context_chunks
from embeddings.embedding_generator import initialize_embedding_model, generate_text_embedding
import chromadb


def preprocess_query(query: str) -> Dict[str, Any]:
    """Preprocess user query to extract intent and keywords."""
    query_lower = query.lower().strip()

    # Identify query intent
    intent = classify_query_intent(query_lower)

    # Extract keywords
    keywords = extract_query_keywords(query)

    # Extract technical terms
    tech_terms = extract_technical_terms(query_lower)

    # Detect code-related queries
    is_code_query = detect_code_query(query_lower)

    return {
        'original_query': query,
        'processed_query': query_lower,
        'intent': intent,
        'keywords': keywords,
        'tech_terms': tech_terms,
        'is_code_query': is_code_query,
        'difficulty_preference': estimate_query_difficulty(query_lower)
    }


def classify_query_intent(query: str) -> str:
    """Classify the intent of the user query."""
    # Define intent patterns
    intent_patterns = {
        'how_to': [r'how to', r'how do i', r'how can i', r'steps to', r'tutorial'],
        'what_is': [r'what is', r'what are', r'define', r'explain', r'meaning of'],
        'example': [r'example', r'sample', r'demo', r'show me'],
        'troubleshoot': [r'error', r'problem', r'issue', r'not working', r'debug', r'fix'],
        'comparison': [r'vs', r'versus', r'compare', r'difference', r'better'],
        'api_reference': [r'function', r'method', r'class', r'parameter', r'api', r'reference'],
        'best_practice': [r'best practice', r'recommended', r'should i', r'better way'],
        'code_generation': [r'write code', r'generate', r'create', r'implement', r'build']
    }

    for intent, patterns in intent_patterns.items():
        if any(re.search(pattern, query) for pattern in patterns):
            return intent

    return 'general'


def extract_query_keywords(query: str) -> List[str]:
    """Extract meaningful keywords from query."""
    # Remove common words
    stop_words = {
        'how', 'to', 'do', 'i', 'can', 'what', 'is', 'are', 'the', 'a', 'an', 'and', 'or',
        'but', 'in', 'on', 'at', 'for', 'with', 'by', 'from', 'of', 'as', 'this', 'that'
    }

    # Extract words
    words = re.findall(r'\b[a-zA-Z]+\b', query.lower())
    keywords = [word for word in words if word not in stop_words and len(word) > 2]

    return keywords


def extract_technical_terms(query: str) -> List[str]:
    """Extract technical terms and concepts from query."""
    # Define technical term patterns
    tech_patterns = {
        'cuda_q': [r'cuda-q', r'cudaq'],
        'quantum': [r'quantum', r'qubit', r'gate', r'circuit', r'entanglement'],
        'programming': [r'function', r'class', r'method', r'variable', r'parameter'],
        'data_types': [r'array', r'matrix', r'vector', r'list', r'string'],
        'operations': [r'compile', r'execute', r'run', r'build', r'install'],
        'concepts': [r'algorithm', r'optimization', r'simulation', r'measurement']
    }

    tech_terms = []
    for category, patterns in tech_patterns.items():
        for pattern in patterns:
            if re.search(pattern, query):
                tech_terms.append(category)
                break

    return tech_terms


def detect_code_query(query: str) -> bool:
    """Detect if query is asking for code examples or implementation."""
    code_indicators = [
        r'code', r'example', r'implement', r'write', r'create', r'build',
        r'function', r'class', r'method', r'syntax', r'snippet'
    ]

    return any(re.search(pattern, query) for pattern in code_indicators)


def estimate_query_difficulty(query: str) -> str:
    """Estimate the difficulty level the user is looking for."""
    beginner_terms = ['basic', 'simple', 'introduction', 'getting started', 'beginner']
    advanced_terms = ['advanced', 'complex', 'optimization', 'performance', 'internals']

    if any(term in query for term in beginner_terms):
        return 'beginner'
    elif any(term in query for term in advanced_terms):
        return 'advanced'
    else:
        return 'intermediate'


def create_retrieval_filters(query_analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Create filters for vector store based on query analysis."""
    filters = None  # Start with no filters to avoid complex ChromaDB syntax

    # For now, disable complex filtering to avoid ChromaDB issues
    # Future: implement single-field filtering if needed

    return filters


def retrieve_relevant_chunks(
    collection: chromadb.Collection,
    query_analysis: Dict[str, Any],
    max_chunks: int = 10,          # Allow up to 10 chunks
    max_tokens: int = 30000,       # 30K token budget for aggressive context
    similarity_threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """Retrieve relevant chunks based on query analysis."""
    query = query_analysis['original_query']

    # Create filters
    filters = create_retrieval_filters(query_analysis)

    # Perform hybrid search
    chunks = hybrid_search(
        collection=collection,
        query_text=query,
        keyword_filters=query_analysis['keywords'],
        metadata_filters=filters if filters else None,
        top_k=max_chunks * 3,  # Get more initially for aggressive context (30 candidates)
        similarity_threshold=similarity_threshold
    )

    # If no results with filters, try without filters
    if not chunks and filters:
        chunks = search_similar_chunks(
            collection=collection,
            query_text=query,
            top_k=max_chunks,
            similarity_threshold=similarity_threshold
        )

    # Rank and select best chunks
    selected_chunks = rank_and_select_chunks(chunks, query_analysis, max_chunks, max_tokens)

    return selected_chunks


def rank_and_select_chunks(
    chunks: List[Dict[str, Any]],
    query_analysis: Dict[str, Any],
    max_chunks: int,
    max_tokens: int
) -> List[Dict[str, Any]]:
    """Rank chunks by relevance and select the best ones."""
    if not chunks:
        return []

    # Calculate relevance scores
    for chunk in chunks:
        chunk['relevance_score'] = calculate_chunk_relevance(chunk, query_analysis)

    # Sort by relevance
    chunks.sort(key=lambda x: x['relevance_score'], reverse=True)

    # Select chunks within token limit
    selected_chunks = []
    total_tokens = 0

    for chunk in chunks:
        chunk_tokens = chunk['metadata'].get('token_count', len(chunk['content'].split()) * 1.3)

        if (len(selected_chunks) < max_chunks and
            total_tokens + chunk_tokens <= max_tokens):
            selected_chunks.append(chunk)
            total_tokens += chunk_tokens
        elif len(selected_chunks) == 0:
            # Always include at least one chunk
            selected_chunks.append(chunk)
            break

    return selected_chunks


def calculate_chunk_relevance(chunk: Dict[str, Any], query_analysis: Dict[str, Any]) -> float:
    """Calculate relevance score for a chunk based on query analysis."""
    base_score = chunk.get('similarity_score', 0.0)

    # Boost score based on query intent match
    metadata = chunk.get('metadata', {})
    content_type = metadata.get('content_type', '')

    intent_boosts = {
        'example': 0.2 if content_type == 'example' else 0.0,
        'api_reference': 0.2 if content_type == 'api_reference' else 0.0,
        'how_to': 0.15 if content_type in ['tutorial', 'guide'] else 0.0,
        'code_generation': 0.1 if metadata.get('has_code_examples', False) else 0.0
    }

    intent = query_analysis['intent']
    intent_boost = intent_boosts.get(intent, 0.0)

    # Boost for code queries
    code_boost = 0.1 if (query_analysis['is_code_query'] and
                        metadata.get('is_code', False)) else 0.0

    # Boost for matched keywords
    keyword_boost = 0.0
    matched_keywords = chunk.get('matched_keywords', [])
    if matched_keywords:
        keyword_boost = min(0.15, len(matched_keywords) * 0.05)

    # Difficulty level match
    difficulty_boost = 0.0
    query_difficulty = query_analysis['difficulty_preference']
    chunk_difficulty = metadata.get('difficulty_level', 'intermediate')
    if query_difficulty == chunk_difficulty:
        difficulty_boost = 0.1

    # Penalize very short chunks
    content_length_penalty = 0.0
    if len(chunk['content']) < 100:
        content_length_penalty = -0.1

    final_score = (base_score + intent_boost + code_boost +
                  keyword_boost + difficulty_boost + content_length_penalty)

    return min(1.0, max(0.0, final_score))


def format_context_for_llm(chunks: List[Dict[str, Any]]) -> str:
    """Format retrieved chunks as context for LLM."""
    if not chunks:
        return "No relevant documentation found."

    context_parts = []

    for i, chunk in enumerate(chunks, 1):
        metadata = chunk.get('metadata', {})

        # Create context section
        section_title = metadata.get('section_title', metadata.get('document_title', 'Documentation'))
        content_type = metadata.get('content_type', 'documentation')

        context_part = f"## Context {i}: {section_title}"

        if content_type != 'documentation':
            context_part += f" ({content_type})"

        context_part += f"\n\n{chunk['content']}\n"

        # Add source information
        doc_url = metadata.get('document_url', '')
        if doc_url:
            context_part += f"\n*Source: {doc_url}*\n"

        context_parts.append(context_part)

    return "\n" + "="*50 + "\n".join(context_parts) + "\n" + "="*50


def retrieve_context_for_query(
    collection: chromadb.Collection,
    query: str,
    max_chunks: int = 10,          # Allow up to 10 chunks
    max_tokens: int = 30000,       # 30K token budget for aggressive context
    similarity_threshold: float = 0.5
) -> Tuple[str, Dict[str, Any]]:
    """Main function to retrieve and format context for a query."""
    # Analyze query
    query_analysis = preprocess_query(query)

    # Retrieve relevant chunks
    chunks = retrieve_relevant_chunks(
        collection=collection,
        query_analysis=query_analysis,
        max_chunks=max_chunks,
        max_tokens=max_tokens,
        similarity_threshold=similarity_threshold
    )

    # Format context
    formatted_context = format_context_for_llm(chunks)

    # Return context and metadata
    retrieval_metadata = {
        'query_analysis': query_analysis,
        'chunks_found': len(chunks),
        'total_tokens': sum(chunk['metadata'].get('token_count', 0) for chunk in chunks),
        'similarity_scores': [chunk.get('similarity_score', 0.0) for chunk in chunks],
        'content_types': [chunk['metadata'].get('content_type', 'unknown') for chunk in chunks]
    }

    return formatted_context, retrieval_metadata


def rerank_results_for_diversity(chunks: List[Dict[str, Any]], max_similar: int = 2) -> List[Dict[str, Any]]:
    """Rerank results to ensure diversity and avoid redundancy."""
    if len(chunks) <= max_similar:
        return chunks

    selected = [chunks[0]]  # Always include top result

    for chunk in chunks[1:]:
        # Check similarity with already selected chunks
        is_too_similar = False

        for selected_chunk in selected:
            # Simple text similarity check
            similarity_ratio = calculate_text_similarity(
                chunk['content'],
                selected_chunk['content']
            )

            if similarity_ratio > 0.8:  # Too similar
                is_too_similar = True
                break

        if not is_too_similar:
            selected.append(chunk)

        if len(selected) >= len(chunks) or len(selected) >= max_similar * 2:
            break

    return selected


def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate simple text similarity ratio."""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    if not words1 or not words2:
        return 0.0

    intersection = words1.intersection(words2)
    union = words1.union(words2)

    return len(intersection) / len(union) if union else 0.0