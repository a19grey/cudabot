Improved Preprocessing for Agentic Document Search
Alex Krause - 2025-10-16

This guide outlines preprocessing steps to create a hierarchical document map and a summary lookup document for a "chat with docs" bot. These artifacts enable an agent to intelligently route queries to relevant document subsets before applying GREP (keyword search) or RAG (semantic retrieval), addressing the limitations of noisy RAG results.

This is meant as an improvement and evolution of the current structure. 


1. Build the Document Relationship Map

Create a hierarchical structure (like a folder tree or graph) to represent relationships between documents, mirroring their organization (e.g., folders, subfolders, files). This map helps the agent identify "where to look" based on query context.

Steps:

Load Documents: Recursively scan your docs folder (e.g., Markdown, PDFs) from a website crawl or local directory. Preserve file paths as metadata to track hierarchy (e.g., "docs/folder1/doc1.md").


Construct Tree: Build a nested dictionary or JSON where keys are folder/file paths, and values are nested subfolders or document metadata (e.g., file type, size, or optional semantic tags). For example: {"docs": {"folder1": {"doc1.md": {}, "doc2.md": {}}}}.

Optional Graph: For complex relationships (e.g., linked docs), extract entities/relations using an LLM and store as a graph (nodes: docs, edges: links/references) in a format like JSON or a graph DB.

Output: Save as a JSON file (e.g., doc_map.json) for quick loading into the agent’s context.

Purpose: The map gives the agent a high-level view of document organization, allowing it to narrow down relevant subsets (e.g., "search in folder1") before retrieval.

2. Create the Summary Lookup Document

Generate a single, compact document or JSON containing short summaries of each document (50-200 words). This fits within the agent’s context window for quick lookup, guiding it to relevant docs without loading full content.

then also create from the summar of each document a summary-summary which is a ~1,000 word summary of context for what this project even is. So that it can be fed into each LLM call at the start as part of the hidden system promp. So the system promp should append whatever is in this 'project overview' as context.

The entire improvement here is to make a much larger and hierarchical series of pre-processing elements to enable faster, smarter agentic tool use retrieval beyond what is possible with 'just rag'.

Steps:

Summarize Docs: For each document, prompt an LLM (e.g., Grok, GPT-4o-mini) with: "Summarize this document in 100 words or less, focusing on key topics and sections." Ensure summaries are concise and capture main ideas.



Compile Summaries: Create a flat JSON or list like [{"path": "docs/folder1/doc1.md", "summary": "Overview of topic X..."}]. Include paths for mapping back to the original doc.



Embed Summaries (Optional): Embed each summary with the same model as above for semantic search within the lookup.



Output: Save as a JSON file (e.g., summary_lookup.json) or a single text file, keeping total size small (e.g., under 10K entries or 4K-8K tokens) by grouping subfolders if needed.



Purpose: The lookup provides a lightweight, scannable overview of all docs, letting the agent quickly identify relevant ones based on query keywords or semantics.

3. Add GREP Tool (Keyword Search)

Create a custom tool for precise keyword or regex searches on document subsets, complementing RAG’s semantic retrieval. This tool is called by the agent when exact matches are needed (e.g., specific terms or IDs).





Steps:





Define Tool: Implement a function that takes a query pattern (e.g., regex or string) and a list of document contents (from the map’s selected subset). It searches for matches and returns snippets (e.g., 100 chars around each match).



Logic: Use regex/string matching (e.g., Python’s re module) for case-insensitive searches. For better ranking, consider BM25 (via libraries like rank_bm25) for weighted keyword matches.



Integration: Make the tool callable by the agent, passing in the query and subset of docs identified from the map/summaries.



Purpose: GREP ensures precision for queries needing exact terms, avoiding RAG’s tendency to pull vaguely similar docs.

4. Integrate into Agentic Workflow

Configure your agentic system to use the map and summaries as context for routing, then apply GREP or RAG on the selected document subset.





Steps:





Load Artifacts: Load doc_map.json and summary_lookup.json into the agent’s context or prompt at runtime.



Planner Logic: Prompt the agent with: "Using this document map {hierarchy} and summaries {lookup}, identify relevant paths for query {query}. Choose GREP for exact terms or RAG for concepts." The agent selects a subset of paths (e.g., "docs/folder1") based on folder names, summary content, or embeddings.



Retrieval: For the selected subset, load full document contents and apply either:





GREP: If the query has specific terms (e.g., "error code 404"), run the GREP tool for exact matches.



RAG: If the query is conceptual (e.g., "explain authentication"), use your existing semantic retriever (vector DB like Pinecone/Chroma) on the subset.



Synthesis: Combine results (GREP snippets or RAG chunks) into a coherent response, using the LLM to refine.



Conversational Memory: Store query history and selected paths to maintain context across turns, ensuring follow-up questions use prior routing.



Purpose: The agent uses the map and summaries to make informed decisions, reducing noise and improving retrieval accuracy.

Best Practices





Scale: For large doc sets, embed the map/summaries in a vector DB (e.g., Qdrant) for fast similarity searches. Dedupe summaries to save space.



Optimize Context: Keep summaries concise to fit in context (e.g., <8K tokens). Use cheaper LLMs for summarization to save costs.



Evaluate: Test with diverse queries; measure precision/recall on subsets vs. full RAG. Check for missed docs or false positives.



Edge Cases: If no relevant subset is found, fall back to full RAG. Update map/summaries when new docs are added.



Security: Ensure responses are grounded in the provided docs; avoid external data unless specified.

This preprocessing—hierarchical map, summary lookup, and GREP tool—slots into your agentic RAG system, guiding the bot to smarter retrieval. Your implementation model can adapt these steps, leveraging the map and summaries for routing and the GREP tool for precision.