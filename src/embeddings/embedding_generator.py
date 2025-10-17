import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional, Union
import os
import pickle
from pathlib import Path
import hashlib
import json
from tqdm import tqdm


def initialize_embedding_model(model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> SentenceTransformer:
    """Initialize the embedding model."""
    try:
        print(f"Loading embedding model: {model_name}")
        model = SentenceTransformer(model_name)
        return model
    except Exception as e:
        print(f"Error loading model {model_name}: {e}")
        print("Falling back to default model...")
        return SentenceTransformer('all-MiniLM-L6-v2')


def generate_text_embedding(text: str, model: SentenceTransformer) -> List[float]:
    """Generate embedding for a single text."""
    try:
        embedding = model.encode(text, convert_to_tensor=False)
        return embedding.tolist()
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return [0.0] * model.get_sentence_embedding_dimension()


def generate_batch_embeddings(texts: List[str], model: SentenceTransformer, batch_size: int = 32) -> List[List[float]]:
    """Generate embeddings for multiple texts in batches."""
    embeddings = []

    print(f"Generating embeddings for {len(texts)} texts...")

    for i in tqdm(range(0, len(texts), batch_size), desc="Generating embeddings"):
        batch_texts = texts[i:i + batch_size]
        try:
            batch_embeddings = model.encode(batch_texts, convert_to_tensor=False, show_progress_bar=False)
            embeddings.extend([emb.tolist() for emb in batch_embeddings])
        except Exception as e:
            print(f"Error processing batch {i//batch_size}: {e}")
            # Fallback: process individually
            for text in batch_texts:
                embedding = generate_text_embedding(text, model)
                embeddings.append(embedding)

    return embeddings


def create_embedding_cache_key(text: str, model_name: str) -> str:
    """Create cache key for embedding."""
    content_hash = hashlib.md5(f"{model_name}:{text}".encode()).hexdigest()
    return content_hash


def load_embedding_cache(cache_file: str) -> Dict[str, List[float]]:
    """Load embedding cache from disk."""
    cache_path = Path(cache_file)
    if cache_path.exists():
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Error loading embedding cache: {e}")
    return {}


def save_embedding_cache(cache: Dict[str, List[float]], cache_file: str) -> None:
    """Save embedding cache to disk."""
    cache_path = Path(cache_file)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(cache_path, 'wb') as f:
            pickle.dump(cache, f)
    except Exception as e:
        print(f"Error saving embedding cache: {e}")


def generate_embeddings_with_cache(
    texts: List[str],
    model: SentenceTransformer,
    cache_file: str,
    batch_size: int = 32
) -> List[List[float]]:
    """Generate embeddings with caching support."""
    model_name = model._model_card_data.model_name if hasattr(model, '_model_card_data') else "unknown"

    # Load cache
    cache = load_embedding_cache(cache_file)

    embeddings = []
    texts_to_embed = []
    cache_keys = []
    indices_to_embed = []

    # Check cache for existing embeddings
    for i, text in enumerate(texts):
        cache_key = create_embedding_cache_key(text, model_name)
        cache_keys.append(cache_key)

        if cache_key in cache:
            embeddings.append(cache[cache_key])
        else:
            embeddings.append(None)  # Placeholder
            texts_to_embed.append(text)
            indices_to_embed.append(i)

    # Generate missing embeddings
    if texts_to_embed:
        print(f"Generating {len(texts_to_embed)} new embeddings (found {len(texts) - len(texts_to_embed)} in cache)")
        new_embeddings = generate_batch_embeddings(texts_to_embed, model, batch_size)

        # Update cache and results
        for idx, embedding in zip(indices_to_embed, new_embeddings):
            embeddings[idx] = embedding
            cache_key = cache_keys[idx]
            cache[cache_key] = embedding

        # Save updated cache
        save_embedding_cache(cache, cache_file)
    else:
        print("All embeddings found in cache")

    return embeddings


def compute_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """Compute cosine similarity between two embeddings."""
    try:
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Normalize vectors
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        # Compute cosine similarity
        similarity = np.dot(vec1, vec2) / (norm1 * norm2)
        return float(similarity)

    except Exception as e:
        print(f"Error computing similarity: {e}")
        return 0.0


def find_most_similar_embeddings(
    query_embedding: List[float],
    candidate_embeddings: List[List[float]],
    top_k: int = 5,
    threshold: float = 0.0
) -> List[tuple[int, float]]:
    """Find most similar embeddings to query."""
    similarities = []

    for i, candidate_embedding in enumerate(candidate_embeddings):
        similarity = compute_similarity(query_embedding, candidate_embedding)
        if similarity >= threshold:
            similarities.append((i, similarity))

    # Sort by similarity (descending)
    similarities.sort(key=lambda x: x[1], reverse=True)

    return similarities[:top_k]


def embed_document_chunks(
    chunks: List[Any],
    model: SentenceTransformer,
    cache_file: str,
    batch_size: int = 32
) -> List[Any]:
    """Add embeddings to document chunks."""
    # Extract texts from chunks
    texts = [chunk.content for chunk in chunks]

    # Generate embeddings
    embeddings = generate_embeddings_with_cache(texts, model, cache_file, batch_size)

    # Add embeddings to chunks
    for chunk, embedding in zip(chunks, embeddings):
        chunk.embedding_vector = embedding

    return chunks


def create_embedding_index(
    chunks: List[Any],
    model_name: str,
    index_file: str
) -> Dict[str, Any]:
    """Create and save embedding index."""
    index_data = {
        'model_name': model_name,
        'dimension': len(chunks[0].embedding_vector) if chunks else 0,
        'chunk_count': len(chunks),
        'chunks': []
    }

    for chunk in chunks:
        chunk_data = {
            'chunk_id': chunk.chunk_id,
            'content': chunk.content,
            'metadata': chunk.metadata,
            'token_count': chunk.token_count,
            'embedding_vector': chunk.embedding_vector
        }
        index_data['chunks'].append(chunk_data)

    # Save index
    index_path = Path(index_file)
    index_path.parent.mkdir(parents=True, exist_ok=True)

    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)

    print(f"Saved embedding index with {len(chunks)} chunks to {index_file}")

    return index_data


def load_embedding_index(index_file: str) -> Dict[str, Any]:
    """Load embedding index from file."""
    with open(index_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_embeddings_for_target(
    chunks: List[Any],
    target_name: str,
    config: Dict[str, Any]
) -> List[Any]:
    """Create embeddings for a target's document chunks."""
    embedding_config = config.get('embedding', {})
    data_paths = config.get('data_paths', {})

    model_name = embedding_config.get('model', 'sentence-transformers/all-MiniLM-L6-v2')
    batch_size = embedding_config.get('batch_size', 32)

    # Initialize model
    model = initialize_embedding_model(model_name)

    # Set up cache file
    cache_file = Path(data_paths.get('embeddings_dir', './data/embeddings')) / f"{target_name}_embedding_cache.pkl"

    # Generate embeddings
    embedded_chunks = embed_document_chunks(chunks, model, str(cache_file), batch_size)

    # Create and save index
    index_file = Path(data_paths.get('embeddings_dir', './data/embeddings')) / f"{target_name}_embedding_index.json"
    create_embedding_index(embedded_chunks, model_name, str(index_file))

    print(f"Created embeddings for {len(embedded_chunks)} chunks")

    return embedded_chunks


def query_embeddings(
    query_text: str,
    index_file: str,
    model: Optional[SentenceTransformer] = None,
    top_k: int = 5,
    threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """Query embeddings and return most similar chunks."""
    # Load index
    index_data = load_embedding_index(index_file)

    # Initialize model if not provided
    if model is None:
        model_name = index_data.get('model_name', 'sentence-transformers/all-MiniLM-L6-v2')
        model = initialize_embedding_model(model_name)

    # Generate query embedding
    query_embedding = generate_text_embedding(query_text, model)

    # Extract candidate embeddings
    candidate_embeddings = [chunk['embedding_vector'] for chunk in index_data['chunks']]

    # Find most similar
    similar_indices = find_most_similar_embeddings(query_embedding, candidate_embeddings, top_k, threshold)

    # Return results
    results = []
    for idx, similarity in similar_indices:
        chunk_data = index_data['chunks'][idx].copy()
        chunk_data['similarity_score'] = similarity
        results.append(chunk_data)

    return results