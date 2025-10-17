import re
import tiktoken
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class DocumentChunk:
    """Represents a chunk of document content."""
    content: str
    metadata: Dict[str, Any]
    chunk_id: str
    token_count: int
    embedding_vector: Optional[List[float]] = None


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """Count tokens in text using tiktoken."""
    try:
        encoding = tiktoken.get_encoding(encoding_name)
        return len(encoding.encode(text))
    except Exception:
        # Fallback to approximate counting
        return len(text.split()) * 1.3


def create_chunk_id(content: str, document_url: str, chunk_index: int) -> str:
    """Create unique chunk ID."""
    import hashlib
    content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
    return f"{document_url.split('/')[-1]}_{chunk_index}_{content_hash}"


def split_by_headers(content: str, headers: List[Dict[str, Any]]) -> List[Tuple[str, Dict[str, Any]]]:
    """Split content by document headers/sections."""
    if not headers:
        return [(content, {})]

    sections = []
    header_positions = []

    # Find header positions in content
    for header in headers:
        header_text = header['text']
        pattern = re.escape(header_text)
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            header_positions.append({
                'start': match.start(),
                'end': match.end(),
                'header': header,
                'text': header_text
            })

    # Sort by position
    header_positions.sort(key=lambda x: x['start'])

    # Split content by headers
    for i, header_pos in enumerate(header_positions):
        start_pos = header_pos['start']
        end_pos = header_positions[i + 1]['start'] if i + 1 < len(header_positions) else len(content)

        section_content = content[start_pos:end_pos].strip()
        if section_content:
            section_metadata = {
                'section_title': header_pos['text'],
                'section_level': header_pos['header']['level'],
                'section_id': header_pos['header'].get('id', ''),
                'is_section': True
            }
            sections.append((section_content, section_metadata))

    # If no headers found or no content was extracted, return full content
    if not sections:
        sections = [(content, {'is_section': False})]

    return sections


def split_by_sentences(text: str, max_chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """Split text by sentences with overlap."""
    # Split by sentences
    sentence_endings = r'[.!?]+\s+'
    sentences = re.split(sentence_endings, text)
    sentences = [s.strip() + '.' for s in sentences if s.strip()]

    if not sentences:
        return [text]

    chunks = []
    current_chunk = ""
    current_size = 0

    for sentence in sentences:
        sentence_tokens = count_tokens(sentence)

        # If adding this sentence exceeds chunk size, finalize current chunk
        if current_size + sentence_tokens > max_chunk_size and current_chunk:
            chunks.append(current_chunk.strip())

            # Start new chunk with overlap
            if overlap > 0:
                overlap_text = get_text_overlap(current_chunk, overlap)
                current_chunk = overlap_text + " " + sentence
                current_size = count_tokens(current_chunk)
            else:
                current_chunk = sentence
                current_size = sentence_tokens
        else:
            current_chunk += " " + sentence if current_chunk else sentence
            current_size += sentence_tokens

    # Add final chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def get_text_overlap(text: str, overlap_tokens: int) -> str:
    """Get the last N tokens of text for overlap."""
    words = text.split()
    if len(words) <= overlap_tokens * 0.75:  # Approximate token to word ratio
        return text

    overlap_words = int(overlap_tokens * 0.75)
    return " ".join(words[-overlap_words:])


def split_by_fixed_size(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """Split text by fixed token size with overlap."""
    if count_tokens(text) <= chunk_size:
        return [text]

    chunks = []
    words = text.split()
    current_chunk = []
    current_tokens = 0

    for word in words:
        word_tokens = count_tokens(word)

        if current_tokens + word_tokens > chunk_size and current_chunk:
            # Finalize current chunk
            chunk_text = " ".join(current_chunk)
            chunks.append(chunk_text)

            # Start new chunk with overlap
            if overlap > 0:
                overlap_words = int(overlap * 0.75)  # Approximate
                overlap_start = max(0, len(current_chunk) - overlap_words)
                current_chunk = current_chunk[overlap_start:] + [word]
                current_tokens = count_tokens(" ".join(current_chunk))
            else:
                current_chunk = [word]
                current_tokens = word_tokens
        else:
            current_chunk.append(word)
            current_tokens += word_tokens

    # Add final chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def extract_code_blocks_separately(content: str, code_blocks: List[str]) -> Tuple[str, List[str]]:
    """Extract code blocks to process separately."""
    text_content = content

    # Remove code blocks from main content
    for code_block in code_blocks:
        # Try to find and remove the code block
        code_pattern = re.escape(code_block)
        text_content = re.sub(code_pattern, "", text_content, flags=re.MULTILINE)

    # Clean up extra whitespace
    text_content = re.sub(r'\n\s*\n', '\n\n', text_content)

    return text_content.strip(), code_blocks


def create_document_chunks(
    document: Dict[str, Any],
    chunk_size: int = 512,
    overlap: int = 50,
    include_code_separately: bool = True
) -> List[DocumentChunk]:
    """Create chunks from a document."""
    chunks = []
    base_metadata = {
        'document_url': document['url'],
        'document_title': document['title'],
        'document_hash': document['content_hash']
    }

    # Extract code blocks if specified
    main_content = document['content']
    code_blocks = document.get('code_blocks', [])

    if include_code_separately and code_blocks:
        main_content, extracted_code = extract_code_blocks_separately(main_content, code_blocks)
    else:
        extracted_code = []

    # Split by sections if headers are available
    sections = split_by_headers(main_content, document.get('headers', []))

    chunk_index = 0

    # Process each section
    for section_content, section_metadata in sections:
        section_chunks = split_by_sentences(section_content, chunk_size, overlap)

        for chunk_text in section_chunks:
            if len(chunk_text.strip()) < 20:  # Skip very short chunks
                continue

            metadata = {**base_metadata, **section_metadata}
            chunk_id = create_chunk_id(chunk_text, document['url'], chunk_index)
            token_count = count_tokens(chunk_text)

            chunk = DocumentChunk(
                content=chunk_text.strip(),
                metadata=metadata,
                chunk_id=chunk_id,
                token_count=token_count
            )
            chunks.append(chunk)
            chunk_index += 1

    # Process code blocks separately
    for i, code_block in enumerate(extracted_code):
        if len(code_block.strip()) < 10:  # Skip very short code blocks
            continue

        # Split large code blocks
        if count_tokens(code_block) > chunk_size:
            code_chunks = split_by_fixed_size(code_block, chunk_size, overlap)
        else:
            code_chunks = [code_block]

        for code_chunk in code_chunks:
            metadata = {
                **base_metadata,
                'content_type': 'code',
                'code_block_index': i,
                'is_code': True
            }

            chunk_id = create_chunk_id(code_chunk, document['url'], chunk_index)
            token_count = count_tokens(code_chunk)

            chunk = DocumentChunk(
                content=code_chunk.strip(),
                metadata=metadata,
                chunk_id=chunk_id,
                token_count=token_count
            )
            chunks.append(chunk)
            chunk_index += 1

    return chunks


def chunk_documents(documents: List[Dict[str, Any]], chunk_config: Dict[str, Any]) -> List[DocumentChunk]:
    """Chunk multiple documents."""
    all_chunks = []

    chunk_size = chunk_config.get('chunk_size', 512)
    overlap = chunk_config.get('chunk_overlap', 50)
    include_code = chunk_config.get('include_code_separately', True)

    for document in documents:
        try:
            doc_chunks = create_document_chunks(
                document,
                chunk_size=chunk_size,
                overlap=overlap,
                include_code_separately=include_code
            )
            all_chunks.extend(doc_chunks)
        except Exception as e:
            print(f"Error chunking document {document.get('url', 'unknown')}: {e}")

    return all_chunks


def save_chunks_to_file(chunks: List[DocumentChunk], output_file: str) -> None:
    """Save chunks to JSON file."""
    import json
    from pathlib import Path

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert chunks to serializable format
    chunks_data = []
    for chunk in chunks:
        chunks_data.append({
            'content': chunk.content,
            'metadata': chunk.metadata,
            'chunk_id': chunk.chunk_id,
            'token_count': chunk.token_count
        })

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(chunks_data, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(chunks)} chunks to {output_file}")


def load_chunks_from_file(input_file: str) -> List[DocumentChunk]:
    """Load chunks from JSON file."""
    import json

    with open(input_file, 'r', encoding='utf-8') as f:
        chunks_data = json.load(f)

    chunks = []
    for chunk_data in chunks_data:
        chunk = DocumentChunk(
            content=chunk_data['content'],
            metadata=chunk_data['metadata'],
            chunk_id=chunk_data['chunk_id'],
            token_count=chunk_data['token_count']
        )
        chunks.append(chunk)

    return chunks