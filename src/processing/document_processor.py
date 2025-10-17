import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from .chunking import chunk_documents, DocumentChunk, save_chunks_to_file, load_chunks_from_file


def clean_document_content(content: str) -> str:
    """Clean and normalize document content."""
    import re

    # Remove excessive whitespace
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
    content = re.sub(r'[ \t]+', ' ', content)

    # Remove common navigation elements
    patterns_to_remove = [
        r'Table of Contents',
        r'Skip to main content',
        r'Previous\s*Next',
        r'Edit on GitHub',
        r'© \d{4}.*',
        r'All rights reserved',
    ]

    for pattern in patterns_to_remove:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE)

    return content.strip()


def filter_relevant_documents(documents: List[Dict[str, Any]], min_word_count: int = 50) -> List[Dict[str, Any]]:
    """Filter documents to keep only relevant content."""
    filtered_docs = []

    for doc in documents:
        # Skip documents that are too short
        if doc.get('word_count', 0) < min_word_count:
            continue

        # Skip common non-content pages
        title = doc.get('title', '').lower()
        url = doc.get('url', '').lower()

        skip_patterns = [
            'index', 'sitemap', 'search', '404', 'error',
            'genindex', 'modindex', 'py-modindex'
        ]

        if any(pattern in title or pattern in url for pattern in skip_patterns):
            continue

        # Clean content
        cleaned_content = clean_document_content(doc['content'])
        if len(cleaned_content) < min_word_count * 5:  # Rough character estimate
            continue

        # Update document with cleaned content
        doc['content'] = cleaned_content
        doc['word_count'] = len(cleaned_content.split())

        filtered_docs.append(doc)

    return filtered_docs


def enhance_document_metadata(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Enhance document metadata for better retrieval."""
    for doc in documents:
        url = doc.get('url', '')
        title = doc.get('title', '')
        content = doc.get('content', '')

        # Extract category from URL structure
        path_parts = url.split('/')
        category = 'general'
        subcategory = 'overview'

        # Analyze URL structure for CUDA-Q docs
        for i, part in enumerate(path_parts):
            if part in ['api', 'examples', 'tutorials', 'guides', 'reference']:
                category = part
                if i + 1 < len(path_parts):
                    subcategory = path_parts[i + 1].replace('.html', '').replace('_', ' ')
                break

        # Identify content type
        content_type = 'documentation'
        if 'example' in title.lower() or 'example' in url.lower():
            content_type = 'example'
        elif 'api' in url.lower() or 'reference' in url.lower():
            content_type = 'api_reference'
        elif 'tutorial' in title.lower() or 'tutorial' in url.lower():
            content_type = 'tutorial'
        elif 'guide' in title.lower() or 'guide' in url.lower():
            content_type = 'guide'

        # Extract keywords from title and headers
        keywords = extract_keywords_from_document(doc)

        # Identify programming languages/technologies mentioned
        technologies = identify_technologies(content)

        # Add enhanced metadata
        doc['enhanced_metadata'] = {
            'category': category,
            'subcategory': subcategory,
            'content_type': content_type,
            'keywords': keywords,
            'technologies': technologies,
            'difficulty_level': estimate_difficulty_level(content, title),
            'has_code_examples': len(doc.get('code_blocks', [])) > 0
        }

    return documents


def extract_keywords_from_document(document: Dict[str, Any]) -> List[str]:
    """Extract relevant keywords from document title and headers."""
    keywords = set()

    # Extract from title
    title = document.get('title', '')
    title_words = [word.lower().strip('.,!?()[]') for word in title.split()]
    keywords.update([word for word in title_words if len(word) > 3])

    # Extract from headers
    headers = document.get('headers', [])
    for header in headers:
        header_text = header.get('text', '')
        header_words = [word.lower().strip('.,!?()[]') for word in header_text.split()]
        keywords.update([word for word in header_words if len(word) > 3])

    # Filter common stop words
    stop_words = {'with', 'from', 'this', 'that', 'they', 'them', 'their', 'there', 'where', 'when', 'what', 'which', 'will', 'would', 'could', 'should'}
    keywords = keywords - stop_words

    return list(keywords)[:20]  # Limit to top 20 keywords


def identify_technologies(content: str) -> List[str]:
    """Identify technologies and frameworks mentioned in content."""
    technologies = set()
    content_lower = content.lower()

    # Define technology patterns
    tech_patterns = {
        'cuda-q': ['cuda-q', 'cudaq'],
        'python': ['python', 'py'],
        'c++': ['c++', 'cpp', 'cxx'],
        'cuda': ['cuda', 'gpu'],
        'quantum': ['quantum', 'qubit', 'quantum computing'],
        'linear_algebra': ['matrix', 'vector', 'linear algebra'],
        'simulation': ['simulation', 'simulator'],
        'optimization': ['optimization', 'optimizer'],
        'machine_learning': ['machine learning', 'ml', 'neural network'],
        'docker': ['docker', 'container'],
        'cmake': ['cmake', 'makefile'],
        'git': ['git', 'github', 'version control']
    }

    for tech, patterns in tech_patterns.items():
        if any(pattern in content_lower for pattern in patterns):
            technologies.add(tech)

    return list(technologies)


def estimate_difficulty_level(content: str, title: str) -> str:
    """Estimate difficulty level based on content analysis."""
    title_lower = title.lower()
    content_lower = content.lower()

    # Beginner indicators
    beginner_terms = ['introduction', 'getting started', 'basics', 'overview', 'first', 'simple', 'basic']
    if any(term in title_lower for term in beginner_terms):
        return 'beginner'

    # Advanced indicators
    advanced_terms = ['advanced', 'optimization', 'performance', 'internals', 'architecture', 'deep dive']
    if any(term in title_lower or term in content_lower for term in advanced_terms):
        return 'advanced'

    # Code complexity indicators
    code_complexity_indicators = ['class', 'template', 'namespace', 'algorithm', 'complex']
    if sum(content_lower.count(indicator) for indicator in code_complexity_indicators) > 10:
        return 'intermediate_advanced'

    return 'intermediate'


def process_documents_pipeline(
    raw_documents: List[Dict[str, Any]],
    chunk_config: Dict[str, Any],
    output_dir: str,
    target_name: str
) -> tuple[List[Dict[str, Any]], List[DocumentChunk]]:
    """Complete document processing pipeline."""
    print(f"Processing {len(raw_documents)} raw documents...")

    # Step 1: Filter and clean documents
    print("Filtering and cleaning documents...")
    filtered_docs = filter_relevant_documents(raw_documents)
    print(f"Kept {len(filtered_docs)} relevant documents")

    # Step 2: Enhance metadata
    print("Enhancing document metadata...")
    enhanced_docs = enhance_document_metadata(filtered_docs)

    # Step 3: Create chunks
    print("Creating document chunks...")
    chunks = chunk_documents(enhanced_docs, chunk_config)
    print(f"Created {len(chunks)} chunks")

    # Step 4: Save processed data
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save enhanced documents
    docs_file = output_path / f"{target_name}_processed_docs.json"
    with open(docs_file, 'w', encoding='utf-8') as f:
        json.dump(enhanced_docs, f, indent=2, ensure_ascii=False)

    # Save chunks
    chunks_file = output_path / f"{target_name}_chunks.json"
    save_chunks_to_file(chunks, str(chunks_file))

    print(f"Saved processed documents to {docs_file}")
    print(f"Saved chunks to {chunks_file}")

    return enhanced_docs, chunks


def load_processed_documents(target_name: str, data_dir: str) -> tuple[List[Dict[str, Any]], List[DocumentChunk]]:
    """Load previously processed documents and chunks."""
    data_path = Path(data_dir)

    # Load documents
    docs_file = data_path / f"{target_name}_processed_docs.json"
    with open(docs_file, 'r', encoding='utf-8') as f:
        documents = json.load(f)

    # Load chunks
    chunks_file = data_path / f"{target_name}_chunks.json"
    chunks = load_chunks_from_file(str(chunks_file))

    return documents, chunks


def get_processing_stats(documents: List[Dict[str, Any]], chunks: List[DocumentChunk]) -> Dict[str, Any]:
    """Get statistics about processed documents and chunks."""
    total_words = sum(doc.get('word_count', 0) for doc in documents)
    total_tokens = sum(chunk.token_count for chunk in chunks)

    content_types = {}
    categories = {}
    technologies = set()

    for doc in documents:
        metadata = doc.get('enhanced_metadata', {})

        # Count content types
        content_type = metadata.get('content_type', 'unknown')
        content_types[content_type] = content_types.get(content_type, 0) + 1

        # Count categories
        category = metadata.get('category', 'unknown')
        categories[category] = categories.get(category, 0) + 1

        # Collect technologies
        doc_technologies = metadata.get('technologies', [])
        technologies.update(doc_technologies)

    chunk_types = {}
    for chunk in chunks:
        is_code = chunk.metadata.get('is_code', False)
        chunk_type = 'code' if is_code else 'text'
        chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1

    return {
        'document_count': len(documents),
        'chunk_count': len(chunks),
        'total_words': total_words,
        'total_tokens': total_tokens,
        'content_types': content_types,
        'categories': categories,
        'technologies': list(technologies),
        'chunk_types': chunk_types,
        'avg_chunk_tokens': total_tokens / len(chunks) if chunks else 0
    }