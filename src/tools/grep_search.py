"""
GREP-based keyword search tool for precise document retrieval.

Provides exact keyword matching and regex search capabilities,
complementing RAG's semantic retrieval for hybrid search.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from rank_bm25 import BM25Okapi


@dataclass
class GrepMatch:
    """Represents a single grep match result."""
    doc_id: str
    doc_title: str
    doc_url: str
    match_text: str
    context_before: str
    context_after: str
    line_number: Optional[int] = None
    score: float = 1.0


class GrepSearchTool:
    """GREP-based search tool for exact keyword/regex matching."""

    def __init__(self, doc_map: Dict[str, Any]):
        """
        Initialize GREP search tool.

        Args:
            doc_map: Document map from hierarchical processor
        """
        self.doc_map = doc_map
        self.documents = doc_map.get('documents', {})

        # Build BM25 index for ranked keyword search
        self._build_bm25_index()

    def _build_bm25_index(self):
        """Build BM25 index for ranking keyword matches."""
        corpus = []
        self.doc_id_list = []

        for doc_id, doc in self.documents.items():
            content = doc.get('content', '')
            corpus.append(content.lower().split())
            self.doc_id_list.append(doc_id)

        if corpus:
            self.bm25 = BM25Okapi(corpus)
        else:
            self.bm25 = None

    def grep_search(
        self,
        pattern: str,
        doc_ids: Optional[List[str]] = None,
        case_sensitive: bool = False,
        use_regex: bool = False,
        context_chars: int = 100,
        max_matches_per_doc: int = 5,
        max_total_matches: int = 20
    ) -> List[GrepMatch]:
        """
        Perform GREP search across documents.

        Args:
            pattern: Search pattern (string or regex)
            doc_ids: Optional list of doc_ids to search (if None, searches all)
            case_sensitive: Whether to use case-sensitive matching
            use_regex: Whether to treat pattern as regex
            context_chars: Number of characters to include before/after match
            max_matches_per_doc: Maximum matches to return per document
            max_total_matches: Maximum total matches to return

        Returns:
            List of GrepMatch objects
        """
        # Prepare pattern
        flags = 0 if case_sensitive else re.IGNORECASE
        if use_regex:
            try:
                compiled_pattern = re.compile(pattern, flags)
            except re.error as e:
                print(f"Invalid regex pattern: {e}")
                return []
        else:
            # Escape special regex characters for literal matching
            escaped_pattern = re.escape(pattern)
            compiled_pattern = re.compile(escaped_pattern, flags)

        # Determine which documents to search
        search_docs = doc_ids if doc_ids else list(self.documents.keys())

        matches = []
        for doc_id in search_docs:
            if doc_id not in self.documents:
                continue

            doc = self.documents[doc_id]
            content = doc.get('content', '')
            if not content:
                continue

            # Find all matches in this document
            doc_matches = []
            for match in compiled_pattern.finditer(content):
                start_pos = match.start()
                end_pos = match.end()

                # Extract context
                context_start = max(0, start_pos - context_chars)
                context_end = min(len(content), end_pos + context_chars)

                context_before = content[context_start:start_pos]
                match_text = content[start_pos:end_pos]
                context_after = content[end_pos:context_end]

                # Clean up context (remove excessive whitespace)
                context_before = ' '.join(context_before.split())
                context_after = ' '.join(context_after.split())

                grep_match = GrepMatch(
                    doc_id=doc_id,
                    doc_title=doc.get('title', 'Untitled'),
                    doc_url=doc.get('url', ''),
                    match_text=match_text,
                    context_before=context_before,
                    context_after=context_after
                )
                doc_matches.append(grep_match)

                if len(doc_matches) >= max_matches_per_doc:
                    break

            matches.extend(doc_matches)

            if len(matches) >= max_total_matches:
                break

        return matches[:max_total_matches]

    def keyword_search_ranked(
        self,
        query: str,
        doc_ids: Optional[List[str]] = None,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Perform BM25-ranked keyword search.

        Args:
            query: Search query
            doc_ids: Optional list of doc_ids to search
            top_k: Number of top results to return

        Returns:
            List of (doc_id, score) tuples, sorted by relevance
        """
        if not self.bm25:
            return []

        # Tokenize query
        query_tokens = query.lower().split()

        # Get BM25 scores for all documents
        scores = self.bm25.get_scores(query_tokens)

        # Filter by doc_ids if specified
        if doc_ids:
            doc_id_set = set(doc_ids)
            results = [
                (doc_id, score)
                for doc_id, score in zip(self.doc_id_list, scores)
                if doc_id in doc_id_set
            ]
        else:
            results = list(zip(self.doc_id_list, scores))

        # Sort by score and return top_k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def find_code_examples(
        self,
        keyword: str,
        doc_ids: Optional[List[str]] = None,
        max_examples: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find code examples containing a keyword.

        Args:
            keyword: Keyword to search for in code blocks
            doc_ids: Optional list of doc_ids to search
            max_examples: Maximum number of examples to return

        Returns:
            List of code example dictionaries
        """
        search_docs = doc_ids if doc_ids else list(self.documents.keys())

        examples = []
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)

        for doc_id in search_docs:
            if doc_id not in self.documents:
                continue

            doc = self.documents[doc_id]
            code_blocks = doc.get('code_blocks', [])

            for code in code_blocks:
                if pattern.search(code):
                    examples.append({
                        'doc_id': doc_id,
                        'doc_title': doc.get('title', 'Untitled'),
                        'doc_url': doc.get('url', ''),
                        'code': code,
                        'context': f"From {doc.get('title', 'document')}"
                    })

                    if len(examples) >= max_examples:
                        return examples

        return examples

    def search_headers(
        self,
        keyword: str,
        doc_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for keyword in document headers/sections.

        Args:
            keyword: Keyword to search for
            doc_ids: Optional list of doc_ids to search

        Returns:
            List of matching headers with document info
        """
        search_docs = doc_ids if doc_ids else list(self.documents.keys())

        results = []
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)

        for doc_id in search_docs:
            if doc_id not in self.documents:
                continue

            doc = self.documents[doc_id]
            headers = doc.get('headers', [])

            for header in headers:
                header_text = header.get('text', '') if isinstance(header, dict) else str(header)
                if pattern.search(header_text):
                    results.append({
                        'doc_id': doc_id,
                        'doc_title': doc.get('title', 'Untitled'),
                        'doc_url': doc.get('url', ''),
                        'header': header_text,
                        'level': header.get('level', 1) if isinstance(header, dict) else 1
                    })

        return results

    def format_grep_results(self, matches: List[GrepMatch], max_display: int = 10) -> str:
        """
        Format GREP matches for display.

        Args:
            matches: List of GrepMatch objects
            max_display: Maximum number of matches to display

        Returns:
            Formatted string for display
        """
        if not matches:
            return "No matches found."

        output = [f"Found {len(matches)} matches:\n"]

        for i, match in enumerate(matches[:max_display], 1):
            output.append(f"\n## Match {i}: {match.doc_title}")
            output.append(f"URL: {match.doc_url}")
            output.append(f"")
            output.append(f"...{match.context_before} **{match.match_text}** {match.context_after}...")
            output.append("")

        if len(matches) > max_display:
            output.append(f"\n... and {len(matches) - max_display} more matches")

        return "\n".join(output)


def format_bm25_results(
    results: List[Tuple[str, float]],
    documents: Dict[str, Any],
    max_display: int = 10
) -> str:
    """
    Format BM25 ranked search results.

    Args:
        results: List of (doc_id, score) tuples
        documents: Document map
        max_display: Maximum number of results to display

    Returns:
        Formatted string for display
    """
    if not results:
        return "No results found."

    output = [f"Found {len(results)} relevant documents:\n"]

    for i, (doc_id, score) in enumerate(results[:max_display], 1):
        if doc_id not in documents:
            continue

        doc = documents[doc_id]
        output.append(f"\n## Result {i}: {doc.get('title', 'Untitled')} (Score: {score:.2f})")
        output.append(f"URL: {doc.get('url', '')}")
        output.append(f"Path: {doc.get('path', '')}")
        output.append("")

    if len(results) > max_display:
        output.append(f"\n... and {len(results) - max_display} more results")

    return "\n".join(output)
