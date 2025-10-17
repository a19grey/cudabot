"""
Hierarchical document preprocessing for improved agent-based retrieval.

This module creates:
1. Document relationship map (hierarchical structure)
2. Document summaries for quick lookup
3. Project overview summary for context

Based on the architecture described in docs/improved_rag_grep_arch.md
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse
from collections import defaultdict
import anthropic
import os


class HierarchicalDocumentProcessor:
    """Process documents into hierarchical structure with summaries."""

    def __init__(self, target_name: str, data_paths: Dict[str, Path]):
        """
        Initialize the hierarchical processor.

        Args:
            target_name: Name of the target (e.g., 'cuda_q')
            data_paths: Dictionary of data paths from config
        """
        self.target_name = target_name
        self.data_paths = data_paths
        self.client = None

        # Initialize Anthropic client if API key available
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if api_key:
            self.client = anthropic.Anthropic(api_key=api_key)

    def build_document_map(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build hierarchical document relationship map from URLs.

        Args:
            documents: List of document dictionaries with 'url', 'title', etc.

        Returns:
            Hierarchical dictionary representing document structure
        """
        print("🗺️  Building document relationship map...")

        doc_map = {
            "metadata": {
                "target": self.target_name,
                "total_documents": len(documents),
                "structure_type": "url_hierarchy"
            },
            "hierarchy": {},
            "documents": {}  # Flat lookup by doc_id
        }

        for idx, doc in enumerate(documents):
            url = doc.get('url', '')
            if not url:
                continue

            # Parse URL to extract hierarchy
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.split('/') if p]

            # Build nested structure
            current_level = doc_map["hierarchy"]
            for part in path_parts[:-1]:  # All but the last part (filename)
                if part not in current_level:
                    current_level[part] = {"_subdirs": {}, "_documents": []}
                current_level = current_level[part]["_subdirs"]

            # Add document reference
            doc_id = f"doc_{idx}"
            filename = path_parts[-1] if path_parts else parsed.netloc
            if "_documents" not in current_level:
                current_level["_documents"] = []

            current_level["_documents"].append({
                "doc_id": doc_id,
                "title": doc.get('title', filename),
                "url": url,
                "filename": filename,
                "word_count": doc.get('word_count', 0),
                "headers": [h.get('text', '') for h in doc.get('headers', [])][:5]  # Top 5 headers
            })

            # Store full document info for flat lookup
            doc_map["documents"][doc_id] = {
                "url": url,
                "title": doc.get('title', ''),
                "content": doc.get('content', ''),
                "code_blocks": doc.get('code_blocks', []),
                "headers": doc.get('headers', []),
                "word_count": doc.get('word_count', 0),
                "path": '/'.join(path_parts)
            }

        print(f"✅ Document map built: {len(doc_map['documents'])} documents organized")
        return doc_map

    def generate_document_summary(self, doc: Dict[str, Any], max_words: int = 100) -> str:
        """
        Generate a concise summary of a document.

        Args:
            doc: Document dictionary with 'content', 'title', etc.
            max_words: Maximum words for summary

        Returns:
            Summary string
        """
        content = doc.get('content', '')
        title = doc.get('title', 'Untitled')

        if not content:
            return f"{title}: No content available."

        # If we have Anthropic client, use Claude for better summaries
        if self.client:
            try:
                # Use a shorter context for efficiency
                content_preview = content[:4000]  # ~1000 tokens

                message = self.client.messages.create(
                    model="claude-3-5-haiku-20241022",  # Fast and cheap
                    max_tokens=150,
                    temperature=0.3,
                    messages=[{
                        "role": "user",
                        "content": f"""Summarize this documentation page in exactly {max_words} words or less. Focus on key topics, features, and purpose.

Title: {title}

Content:
{content_preview}

Provide only the summary, no preamble."""
                    }]
                )

                summary = message.content[0].text.strip()
                return summary

            except Exception as e:
                print(f"  ⚠️  Claude summarization failed ({e}), using fallback")

        # Fallback: Extract first few sentences
        sentences = re.split(r'[.!?]\s+', content)
        summary_parts = []
        word_count = 0

        for sentence in sentences:
            sentence_words = len(sentence.split())
            if word_count + sentence_words > max_words:
                break
            summary_parts.append(sentence)
            word_count += sentence_words

        summary = '. '.join(summary_parts)
        if summary and not summary.endswith('.'):
            summary += '.'

        return f"{title}: {summary}" if summary else f"{title}: Documentation page."

    def generate_all_summaries(self, doc_map: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        """
        Generate summaries for all documents.

        Args:
            doc_map: Document map from build_document_map()

        Returns:
            Dictionary mapping doc_id to summary info
        """
        print("📝 Generating document summaries...")

        summaries = {}
        documents = doc_map.get("documents", {})
        total = len(documents)

        for idx, (doc_id, doc) in enumerate(documents.items(), 1):
            if idx % 10 == 0:
                print(f"  Progress: {idx}/{total} documents summarized")

            summary = self.generate_document_summary(doc, max_words=100)

            summaries[doc_id] = {
                "path": doc.get('path', ''),
                "url": doc.get('url', ''),
                "title": doc.get('title', ''),
                "summary": summary,
                "word_count": doc.get('word_count', 0),
                "has_code": len(doc.get('code_blocks', [])) > 0
            }

        print(f"✅ Generated {len(summaries)} document summaries")
        return summaries

    def generate_project_overview(self, summaries: Dict[str, Dict[str, str]]) -> str:
        """
        Generate a ~1000 word project overview from all document summaries.

        This overview can be included in system prompts for context.

        Args:
            summaries: Dictionary of document summaries

        Returns:
            Project overview text (~1000 words)
        """
        print("📚 Generating project overview summary...")

        # Collect all summaries
        all_summaries = [s['summary'] for s in summaries.values()]
        combined = '\n\n'.join(all_summaries[:20])  # Use first 20 for overview

        if self.client:
            try:
                message = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",  # Better for synthesis
                    max_tokens=1500,
                    temperature=0.3,
                    messages=[{
                        "role": "user",
                        "content": f"""Based on these documentation summaries, create a comprehensive project overview of approximately 1000 words.

The overview should cover:
1. What the project/technology is
2. Key features and capabilities
3. Main use cases and applications
4. Important concepts and terminology
5. Getting started information

Documentation summaries:
{combined}

Provide a well-structured overview that gives an AI assistant enough context to understand what this documentation is about."""
                    }]
                )

                overview = message.content[0].text.strip()
                print(f"✅ Project overview generated ({len(overview.split())} words)")
                return overview

            except Exception as e:
                print(f"  ⚠️  Claude overview generation failed ({e}), using fallback")

        # Fallback: Create basic overview from summaries
        overview = f"""{self.target_name.upper()} Documentation Overview

This documentation covers {len(summaries)} pages describing the {self.target_name} project.

Key Topics:
{combined[:2000]}

This is an automatically generated overview. The full documentation provides detailed information on installation, usage, APIs, and examples."""

        print(f"✅ Project overview generated (fallback, {len(overview.split())} words)")
        return overview

    def save_artifacts(self, doc_map: Dict[str, Any], summaries: Dict[str, Dict[str, str]],
                      overview: str) -> Dict[str, Path]:
        """
        Save all hierarchical preprocessing artifacts.

        Args:
            doc_map: Document relationship map
            summaries: Document summaries
            overview: Project overview

        Returns:
            Dictionary of saved file paths
        """
        print("💾 Saving hierarchical preprocessing artifacts...")

        processed_dir = Path(self.data_paths['processed_dir'])
        saved_paths = {}

        # Save document map
        map_path = processed_dir / f"{self.target_name}_doc_map.json"
        with open(map_path, 'w', encoding='utf-8') as f:
            json.dump(doc_map, f, indent=2, ensure_ascii=False)
        saved_paths['doc_map'] = map_path
        print(f"  ✓ Document map: {map_path}")

        # Save summaries
        summaries_path = processed_dir / f"{self.target_name}_summaries.json"
        with open(summaries_path, 'w', encoding='utf-8') as f:
            json.dump(summaries, f, indent=2, ensure_ascii=False)
        saved_paths['summaries'] = summaries_path
        print(f"  ✓ Summaries: {summaries_path}")

        # Save project overview
        overview_path = processed_dir / f"{self.target_name}_overview.txt"
        with open(overview_path, 'w', encoding='utf-8') as f:
            f.write(overview)
        saved_paths['overview'] = overview_path
        print(f"  ✓ Overview: {overview_path}")

        # Save a combined lookup file for easy agent access
        lookup_path = processed_dir / f"{self.target_name}_lookup.json"
        lookup_data = {
            "target": self.target_name,
            "overview": overview,
            "document_count": len(summaries),
            "summaries": summaries,
            "hierarchy_path": str(map_path.name)
        }
        with open(lookup_path, 'w', encoding='utf-8') as f:
            json.dump(lookup_data, f, indent=2, ensure_ascii=False)
        saved_paths['lookup'] = lookup_path
        print(f"  ✓ Combined lookup: {lookup_path}")

        print(f"✅ All artifacts saved to {processed_dir}")
        return saved_paths

    def process_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Path]:
        """
        Main processing function: builds map, generates summaries, creates overview.

        Args:
            documents: List of document dictionaries from crawler

        Returns:
            Dictionary of saved file paths
        """
        print(f"\n{'='*60}")
        print(f"Hierarchical Document Processing for {self.target_name}")
        print(f"{'='*60}\n")

        # Step 1: Build document map
        doc_map = self.build_document_map(documents)

        # Step 2: Generate summaries
        summaries = self.generate_all_summaries(doc_map)

        # Step 3: Generate project overview
        overview = self.generate_project_overview(summaries)

        # Step 4: Save all artifacts
        saved_paths = self.save_artifacts(doc_map, summaries, overview)

        print(f"\n{'='*60}")
        print(f"✅ Hierarchical processing complete!")
        print(f"{'='*60}\n")

        return saved_paths


def load_doc_map(target_name: str, processed_dir) -> Optional[Dict[str, Any]]:
    """Load document map from file."""
    processed_dir = Path(processed_dir)
    map_path = processed_dir / f"{target_name}_doc_map.json"
    if map_path.exists():
        with open(map_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def load_summaries(target_name: str, processed_dir) -> Optional[Dict[str, Dict[str, str]]]:
    """Load document summaries from file."""
    processed_dir = Path(processed_dir)
    summaries_path = processed_dir / f"{target_name}_summaries.json"
    if summaries_path.exists():
        with open(summaries_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def load_project_overview(target_name: str, processed_dir) -> Optional[str]:
    """Load project overview from file."""
    processed_dir = Path(processed_dir)
    overview_path = processed_dir / f"{target_name}_overview.txt"
    if overview_path.exists():
        with open(overview_path, 'r', encoding='utf-8') as f:
            return f.read()
    return None


def load_lookup_data(target_name: str, processed_dir) -> Optional[Dict[str, Any]]:
    """Load combined lookup data from file."""
    processed_dir = Path(processed_dir)
    lookup_path = processed_dir / f"{target_name}_lookup.json"
    if lookup_path.exists():
        with open(lookup_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None
