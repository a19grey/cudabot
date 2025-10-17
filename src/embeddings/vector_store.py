import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional, Tuple
import uuid
from pathlib import Path
import json
import numpy as np


def initialize_chroma_client(persist_directory: str) -> chromadb.PersistentClient:
    """Initialize ChromaDB client with persistence."""
    persist_path = Path(persist_directory)
    persist_path.mkdir(parents=True, exist_ok=True)

    settings = Settings(
        persist_directory=str(persist_path),
        anonymized_telemetry=False
    )

    client = chromadb.PersistentClient(path=str(persist_path), settings=settings)
    return client


def create_collection(client: chromadb.PersistentClient, collection_name: str, embedding_dimension: int = 384) -> chromadb.Collection:
    """Create or get a ChromaDB collection."""
    try:
        # Try to get existing collection
        collection = client.get_collection(collection_name)
        print(f"Using existing collection: {collection_name}")
    except Exception:
        # Create new collection
        collection = client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine", "embedding_dimension": embedding_dimension}
        )
        print(f"Created new collection: {collection_name}")

    return collection


def add_chunks_to_collection(
    collection: chromadb.Collection,
    chunks: List[Any],
    batch_size: int = 100
) -> None:
    """Add document chunks to ChromaDB collection."""
    print(f"Adding {len(chunks)} chunks to collection...")

    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i + batch_size]

        # Prepare batch data
        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for chunk in batch_chunks:
            # Generate unique ID if not present
            chunk_id = chunk.chunk_id if hasattr(chunk, 'chunk_id') else str(uuid.uuid4())
            ids.append(chunk_id)

            # Get embedding
            if hasattr(chunk, 'embedding_vector') and chunk.embedding_vector:
                embeddings.append(chunk.embedding_vector)
            else:
                raise ValueError(f"Chunk {chunk_id} missing embedding vector")

            # Get content
            content = chunk.content if hasattr(chunk, 'content') else str(chunk)
            documents.append(content)

            # Get metadata
            metadata = chunk.metadata if hasattr(chunk, 'metadata') else {}

            # Ensure all metadata values are strings, numbers, or booleans
            clean_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    clean_metadata[key] = value
                elif isinstance(value, list):
                    clean_metadata[key] = json.dumps(value)  # Convert list to JSON string
                else:
                    clean_metadata[key] = str(value)

            # Add token count if available
            if hasattr(chunk, 'token_count'):
                clean_metadata['token_count'] = chunk.token_count

            metadatas.append(clean_metadata)

        try:
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
        except Exception as e:
            print(f"Error adding batch {i//batch_size}: {e}")
            # Try adding one by one
            for j, chunk in enumerate(batch_chunks):
                try:
                    collection.add(
                        ids=[ids[j]],
                        embeddings=[embeddings[j]],
                        documents=[documents[j]],
                        metadatas=[metadatas[j]]
                    )
                except Exception as inner_e:
                    print(f"Error adding individual chunk {ids[j]}: {inner_e}")

    print(f"Successfully added chunks to collection")


def query_collection(
    collection: chromadb.Collection,
    query_texts: List[str],
    n_results: int = 5,
    where_filter: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Query ChromaDB collection."""
    try:
        results = collection.query(
            query_texts=query_texts,
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        return results
    except Exception as e:
        print(f"Error querying collection: {e}")
        return {"ids": [], "documents": [], "metadatas": [], "distances": []}


def query_with_embedding(
    collection: chromadb.Collection,
    query_embedding: List[float],
    n_results: int = 5,
    where_filter: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Query ChromaDB collection with pre-computed embedding."""
    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        return results
    except Exception as e:
        print(f"Error querying collection with embedding: {e}")
        return {"ids": [], "documents": [], "metadatas": [], "distances": []}


def search_similar_chunks(
    collection: chromadb.Collection,
    query_text: str,
    filters: Optional[Dict[str, Any]] = None,
    top_k: int = 5,
    similarity_threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """Search for similar chunks with filtering and threshold."""
    # Request more results than needed to account for filtering by threshold
    # This ensures we can still return top_k results after threshold filtering
    n_results_to_fetch = min(top_k * 3, 50)  # Fetch 3x requested or max 50
    results = query_collection(collection, [query_text], n_results=n_results_to_fetch, where_filter=filters)

    # Convert ChromaDB results to our format
    similar_chunks = []

    if results.get("ids") and len(results["ids"]) > 0:
        for i in range(len(results["ids"][0])):
            # Convert distance to similarity (ChromaDB uses cosine distance)
            distance = results["distances"][0][i]
            similarity = 1.0 - distance  # Convert distance to similarity

            if similarity >= similarity_threshold:
                chunk_data = {
                    "chunk_id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "similarity_score": similarity,
                    "distance": distance
                }
                similar_chunks.append(chunk_data)

                # Stop once we have enough results above threshold
                if len(similar_chunks) >= top_k:
                    break

    return similar_chunks


def get_collection_stats(collection: chromadb.Collection) -> Dict[str, Any]:
    """Get statistics about the collection."""
    try:
        count = collection.count()

        # Get sample of metadata to analyze
        sample_results = collection.get(limit=min(100, count), include=["metadatas"])

        # Analyze metadata
        content_types = {}
        categories = {}
        has_code = 0

        for metadata in sample_results.get("metadatas", []):
            # Count content types
            content_type = metadata.get("content_type", "unknown")
            content_types[content_type] = content_types.get(content_type, 0) + 1

            # Count categories
            category = metadata.get("category", "unknown")
            categories[category] = categories.get(category, 0) + 1

            # Count code chunks
            if metadata.get("is_code", False):
                has_code += 1

        return {
            "total_chunks": count,
            "content_types": content_types,
            "categories": categories,
            "code_chunks": has_code,
            "sample_size": len(sample_results.get("metadatas", []))
        }

    except Exception as e:
        print(f"Error getting collection stats: {e}")
        return {"total_chunks": 0, "error": str(e)}


def delete_collection(client: chromadb.PersistentClient, collection_name: str) -> bool:
    """Delete a collection."""
    try:
        client.delete_collection(collection_name)
        print(f"Deleted collection: {collection_name}")
        return True
    except Exception as e:
        print(f"Error deleting collection {collection_name}: {e}")
        return False


def list_collections(client: chromadb.PersistentClient) -> List[str]:
    """List all collections."""
    try:
        collections = client.list_collections()
        return [col.name for col in collections]
    except Exception as e:
        print(f"Error listing collections: {e}")
        return []


def create_vector_store_for_target(
    chunks: List[Any],
    target_name: str,
    persist_directory: str,
    collection_name: Optional[str] = None
) -> Tuple[chromadb.PersistentClient, chromadb.Collection]:
    """Create vector store for a target's chunks."""
    if collection_name is None:
        collection_name = f"{target_name}_docs"

    # Initialize client
    client = initialize_chroma_client(persist_directory)

    # Determine embedding dimension
    embedding_dim = 384  # Default
    if chunks and hasattr(chunks[0], 'embedding_vector') and chunks[0].embedding_vector:
        embedding_dim = len(chunks[0].embedding_vector)

    # Create collection
    collection = create_collection(client, collection_name, embedding_dim)

    # Add chunks
    add_chunks_to_collection(collection, chunks)

    # Print stats
    stats = get_collection_stats(collection)
    print(f"Vector store created for {target_name}:")
    print(f"  Total chunks: {stats['total_chunks']}")
    print(f"  Content types: {stats.get('content_types', {})}")
    print(f"  Categories: {stats.get('categories', {})}")

    return client, collection


def hybrid_search(
    collection: chromadb.Collection,
    query_text: str,
    keyword_filters: Optional[List[str]] = None,
    metadata_filters: Optional[Dict[str, Any]] = None,
    top_k: int = 5,
    similarity_threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """Perform hybrid search combining semantic similarity and keyword/metadata filtering."""
    results = []

    # Base semantic search
    semantic_results = search_similar_chunks(
        collection, query_text, metadata_filters, top_k, similarity_threshold
    )

    # If keyword filters are provided, filter results
    if keyword_filters:
        filtered_results = []
        for result in semantic_results:
            content_lower = result["content"].lower()
            if any(keyword.lower() in content_lower for keyword in keyword_filters):
                result["matched_keywords"] = [kw for kw in keyword_filters if kw.lower() in content_lower]
                filtered_results.append(result)

        results = filtered_results
    else:
        results = semantic_results

    return results


def get_relevant_context_chunks(
    collection: chromadb.Collection,
    query_text: str,
    max_chunks: int = 5,
    max_tokens: int = 2000,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Get relevant chunks for context, respecting token limits."""
    # Search for relevant chunks
    chunks = search_similar_chunks(collection, query_text, filters, max_chunks * 2)  # Get more initially

    # Sort by relevance and select best chunks within token limit
    selected_chunks = []
    total_tokens = 0

    for chunk in chunks:
        chunk_tokens = chunk["metadata"].get("token_count", len(chunk["content"].split()) * 1.3)

        if total_tokens + chunk_tokens <= max_tokens and len(selected_chunks) < max_chunks:
            selected_chunks.append(chunk)
            total_tokens += chunk_tokens
        elif len(selected_chunks) == 0:
            # Include at least one chunk even if it exceeds limit
            selected_chunks.append(chunk)
            break

    return selected_chunks