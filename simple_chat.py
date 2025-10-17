#!/usr/bin/env python3
"""Simple chat interface with detailed RAG visibility."""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def load_env():
    """Load environment variables from .env file."""
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

def print_separator(char="=", length=80):
    """Print a separator line."""
    print(char * length)

def print_rag_results(chunks, query_analysis, retrieval_metadata):
    """Print detailed RAG retrieval information."""
    print_separator("=")
    print("📊 RAG RETRIEVAL DETAILS")
    print_separator("=")

    print(f"\n🔍 Query Analysis:")
    print(f"   Intent: {query_analysis.get('intent', 'unknown')}")
    print(f"   Keywords: {', '.join(query_analysis.get('keywords', []))}")
    print(f"   Is Code Query: {query_analysis.get('is_code_query', False)}")
    print(f"   Tech Terms: {', '.join(query_analysis.get('tech_terms', []))}")

    print(f"\n📦 Retrieval Results:")
    print(f"   Chunks Found: {retrieval_metadata.get('chunks_found', 0)}")
    print(f"   Total Tokens: {retrieval_metadata.get('total_tokens', 0):,}")
    print(f"   Similarity Threshold: 0.7")

    if chunks:
        print(f"\n📄 Retrieved Chunks:")
        print_separator("-")

        for i, chunk in enumerate(chunks, 1):
            metadata = chunk.get('metadata', {})
            similarity = chunk.get('similarity_score', 0.0)

            print(f"\n[Chunk {i}]")
            print(f"  📍 Source: {metadata.get('document_url', 'Unknown')}")
            print(f"  📝 Title: {metadata.get('document_title', 'Unknown')}")
            print(f"  📑 Section: {metadata.get('section_title', 'N/A')}")
            print(f"  🎯 Similarity: {similarity:.3f}")
            print(f"  📏 Tokens: {metadata.get('token_count', 0)}")
            print(f"  🔤 Content Preview:")

            # Show first 200 chars of content
            content_preview = chunk['content'][:200].replace('\n', ' ')
            print(f"     {content_preview}...")

            # Show if it has code
            if metadata.get('is_code', False):
                print(f"  💻 Contains Code: Yes")
    else:
        print("\n⚠️  No chunks retrieved!")

    print_separator("=")
    print()

def simple_rag_chat():
    """Simple RAG-based chat with detailed visibility."""
    print_separator("=")
    print("🤖 CUDA-Q Assistant with RAG Visibility")
    print_separator("=")

    # Load API key
    load_env()
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ No OpenAI API key found in .env file")
        return

    print(f"✅ API key loaded: ...{api_key[-4:]}")

    try:
        # Initialize vector store
        from config_loader import get_merged_config, get_data_paths
        from embeddings.vector_store import initialize_chroma_client, create_collection

        config = get_merged_config('cuda_q')
        data_paths = get_data_paths(config)

        client = initialize_chroma_client(data_paths['embeddings_dir'])
        collection = create_collection(client, "cuda_q_docs")

        # Check collection size
        try:
            count = collection.count()
            print(f"✅ Vector store connected: {count:,} chunks indexed")
        except:
            print("✅ Vector store connected")

        # Simple OpenAI client
        try:
            from openai import OpenAI
            openai_client = OpenAI(api_key=api_key)
            print("✅ OpenAI client initialized")
        except Exception as e:
            print(f"❌ OpenAI setup failed: {e}")
            return

        print("\n💬 Chat with CUDA-Q Assistant!")
        print("Commands:")
        print("  • 'quit' / 'exit' - Exit chat")
        print("  • 'verbose on/off' - Toggle detailed RAG output")
        print("  • 'history' - View conversation history")
        print("  • 'clear' - Clear conversation history")
        print("  • 'help' - Show commands")
        print_separator("-")
        print()

        # Conversation history
        conversation_history = []

        # Verbose mode toggle
        verbose = True  # Start with verbose on

        while True:
            try:
                user_input = input("You: ").strip()

                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("Goodbye! 👋")
                    break

                if user_input.lower() == 'verbose on':
                    verbose = True
                    print("✅ Verbose mode ON - will show RAG details")
                    continue

                if user_input.lower() == 'verbose off':
                    verbose = False
                    print("✅ Verbose mode OFF - will hide RAG details")
                    continue

                if user_input.lower() == 'history':
                    if conversation_history:
                        print(f"\n📜 Conversation History ({len(conversation_history)} turns):")
                        print_separator("-")
                        for i, entry in enumerate(conversation_history, 1):
                            print(f"\n[Turn {i}]")
                            print(f"You: {entry['user'][:80]}...")
                            print(f"Bot: {entry['assistant'][:80]}...")
                        print_separator("-")
                    else:
                        print("📜 No conversation history yet.")
                    continue

                if user_input.lower() == 'clear':
                    conversation_history = []
                    print("✅ Conversation history cleared")
                    continue

                if user_input.lower() == 'help':
                    print("""
Available commands:
- Ask about CUDA-Q: "What is CUDA-Q?"
- Request code examples: "Show me a quantum circuit example"
- Ask about releases: "What's in the latest release?"
- Ask about quantum concepts: "How do quantum gates work?"
- 'verbose on/off' - Toggle RAG visibility
- 'history' - View conversation history
- 'clear' - Clear conversation history
- 'quit' - Exit
""")
                    continue

                if not user_input:
                    continue

                print("\n🔍 Searching knowledge base...")

                # Real RAG retrieval
                from retrieval.rag_pipeline import retrieve_context_for_query

                # Retrieve context with aggressive settings
                formatted_context, retrieval_metadata = retrieve_context_for_query(
                    collection=collection,
                    query=user_input,
                    max_chunks=10,
                    max_tokens=30000,
                    similarity_threshold=0.6  # Lower threshold for more results
                )

                # Get the actual chunks for detailed display
                from retrieval.rag_pipeline import preprocess_query, retrieve_relevant_chunks
                query_analysis = preprocess_query(user_input)
                chunks = retrieve_relevant_chunks(
                    collection=collection,
                    query_analysis=query_analysis,
                    max_chunks=10,
                    max_tokens=30000,
                    similarity_threshold=0.6
                )

                # Show RAG details if verbose
                if verbose:
                    print_rag_results(chunks, query_analysis, retrieval_metadata)
                else:
                    print(f"   Found {len(chunks)} relevant chunks ({retrieval_metadata.get('total_tokens', 0):,} tokens)")

                print("🤖 Generating response...\n")

                # Build messages with conversation history
                messages = []

                # System prompt (always first)
                system_prompt = f"""You are a CUDA-Q expert assistant. Answer questions about CUDA-Q quantum computing based on the provided context from the official documentation.

Context from CUDA-Q documentation:
{formatted_context}

Instructions:
- Provide accurate, helpful answers based on the context above
- Maintain conversation context and refer back to previous questions when relevant
- Include code examples when appropriate
- Explain quantum computing concepts clearly
- Use the @cudaq.kernel decorator syntax
- If the context contains information about releases, changelog, or versions, USE IT
- Be specific and cite sources when possible
- If information is not in the context, say so clearly"""

                messages.append({"role": "system", "content": system_prompt})

                # Add conversation history
                for entry in conversation_history:
                    messages.append({"role": "user", "content": entry["user"]})
                    messages.append({"role": "assistant", "content": entry["assistant"]})

                # Add current question
                messages.append({"role": "user", "content": user_input})

                # Call OpenAI API
                try:
                    response = openai_client.chat.completions.create(
                        model="gpt-4-turbo-preview",  # Use GPT-4 Turbo for large context
                        messages=messages,
                        max_tokens=1000,
                        temperature=0.1
                    )

                    assistant_response = response.choices[0].message.content

                    # Save to conversation history
                    conversation_history.append({
                        "user": user_input,
                        "assistant": assistant_response
                    })

                    # Limit history to last 10 exchanges to avoid context overflow
                    if len(conversation_history) > 10:
                        conversation_history = conversation_history[-10:]

                    print(f"🤖 Assistant:\n{assistant_response}\n")
                    print_separator("-")
                    print(f"💬 Conversation turns: {len(conversation_history)}")
                    print_separator("-")

                except Exception as e:
                    print(f"❌ OpenAI API error: {e}")
                    print("Try again or type 'quit' to exit.")

            except KeyboardInterrupt:
                print("\nGoodbye! 👋")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
                continue

    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simple_rag_chat()
