"""
Scrapy-based web crawler for documentation.
Much simpler and more robust than custom implementation.
"""

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import List, Dict, Any
import hashlib
import json
from pathlib import Path


class DocumentationSpider(CrawlSpider):
    """Spider to crawl documentation websites."""

    name = 'documentation_spider'

    def __init__(self, start_urls, allowed_domains, exclude_patterns=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = start_urls if isinstance(start_urls, list) else [start_urls]
        self.allowed_domains = allowed_domains if isinstance(allowed_domains, list) else [allowed_domains]
        self.exclude_patterns = exclude_patterns or []
        self.documents = []

        # Setup link extractor with rules
        self.rules = (
            Rule(
                LinkExtractor(
                    allow=r'\.html$',  # Only follow HTML links
                    deny=self.exclude_patterns,
                    unique=True
                ),
                callback='parse_page',
                follow=True
            ),
        )
        super(DocumentationSpider, self)._compile_rules()

    def parse_page(self, response):
        """Parse a documentation page."""
        self.logger.info(f'Crawling: {response.url}')

        try:
            # Extract text from HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()

            # Extract title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else ""

            # Extract main content
            main_content = soup.find('main') or soup.find('div', class_='content') or soup.find('body')
            if not main_content:
                main_content = soup

            # Extract text content
            text_content = main_content.get_text()

            # Clean up text
            lines = [line.strip() for line in text_content.splitlines()]
            clean_text = '\n'.join(line for line in lines if line)

            # Extract code blocks
            code_blocks = []
            for code_elem in main_content.find_all(['pre', 'code']):
                code_text = code_elem.get_text().strip()
                if code_text and len(code_text) > 10:  # Filter very short snippets
                    code_blocks.append(code_text)

            # Extract headers for structure
            headers = []
            for i in range(1, 7):
                for header in main_content.find_all(f'h{i}'):
                    headers.append({
                        'level': i,
                        'text': header.get_text().strip(),
                        'id': header.get('id', '')
                    })

            word_count = len(clean_text.split())

            # Only keep pages with substantial content
            if word_count > 50:
                document = {
                    'url': response.url,
                    'title': title_text,
                    'content': clean_text,
                    'code_blocks': code_blocks,
                    'headers': headers,
                    'word_count': word_count,
                    'content_hash': hashlib.md5(clean_text.encode()).hexdigest(),
                    'content_type': response.headers.get('content-type', b'').decode('utf-8', errors='ignore')
                }

                self.documents.append(document)

        except Exception as e:
            self.logger.error(f"Error processing {response.url}: {e}")


def crawl_documentation(base_url: str, exclude_patterns: List[str] = None, max_pages: int = 1000) -> List[Dict[str, Any]]:
    """
    Crawl documentation using Scrapy.

    Args:
        base_url: Starting URL for crawling
        exclude_patterns: List of regex patterns to exclude (e.g., ['genindex', 'search'])
        max_pages: Maximum number of pages to crawl

    Returns:
        List of document dictionaries
    """
    # Parse domain from base URL
    parsed = urlparse(base_url)
    domain = parsed.netloc

    # Default exclude patterns
    if exclude_patterns is None:
        exclude_patterns = []

    # Convert simple patterns to regex
    exclude_regex = [pattern.replace('.html', r'\.html') for pattern in exclude_patterns]

    # Configure Scrapy process
    process = CrawlerProcess(settings={
        'USER_AGENT': 'Mozilla/5.0 (compatible; DocumentationBot/1.0)',
        'ROBOTSTXT_OBEY': True,
        'CONCURRENT_REQUESTS': 16,
        'DOWNLOAD_DELAY': 0.1,  # Be polite
        'DEPTH_LIMIT': 10,  # Maximum depth to crawl
        'CLOSESPIDER_PAGECOUNT': max_pages,  # Limit total pages
        'LOG_LEVEL': 'INFO',
        'HTTPCACHE_ENABLED': True,  # Enable caching for development
        'HTTPCACHE_EXPIRATION_SECS': 3600,  # Cache for 1 hour
    })

    # Store documents in a list we can access after crawling
    documents_collected = []

    # Custom spider class that stores documents
    class CustomDocSpider(DocumentationSpider):
        def closed(self, reason):
            documents_collected.extend(self.documents)

    # Run crawler with spider class and init kwargs
    process.crawl(
        CustomDocSpider,
        start_urls=[base_url],
        allowed_domains=[domain],
        exclude_patterns=exclude_regex
    )
    process.start()  # This blocks until crawling is done

    # Add timestamp
    import datetime
    for doc in documents_collected:
        doc['crawled_at'] = datetime.datetime.utcnow().isoformat()

    return documents_collected


def crawl_single_page(url: str, source_name: str = "single_page") -> List[Dict[str, Any]]:
    """
    Crawl a single page without following links.

    Args:
        url: URL to crawl
        source_name: Name identifier for this source

    Returns:
        List containing a single document dictionary
    """
    import requests
    import datetime

    try:
        print(f"  Fetching single page: {url}")
        response = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; DocumentationBot/1.0)'
        })

        if response.status_code != 200:
            print(f"  ❌ Failed to fetch: HTTP {response.status_code}")
            return []

        # Extract text from HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()

        # Extract title
        title = soup.find('title')
        title_text = title.get_text().strip() if title else ""

        # Extract main content
        main_content = soup.find('main') or soup.find('div', class_='content') or soup.find('body')
        if not main_content:
            main_content = soup

        # Extract text content
        text_content = main_content.get_text()

        # Clean up text
        lines = [line.strip() for line in text_content.splitlines()]
        clean_text = '\n'.join(line for line in lines if line)

        # Extract code blocks
        code_blocks = []
        for code_elem in main_content.find_all(['pre', 'code']):
            code_text = code_elem.get_text().strip()
            if code_text and len(code_text) > 10:
                code_blocks.append(code_text)

        # Extract headers
        headers = []
        for i in range(1, 7):
            for header in main_content.find_all(f'h{i}'):
                headers.append({
                    'level': i,
                    'text': header.get_text().strip(),
                    'id': header.get('id', '')
                })

        word_count = len(clean_text.split())

        document = {
            'url': url,
            'title': title_text,
            'content': clean_text,
            'code_blocks': code_blocks,
            'headers': headers,
            'word_count': word_count,
            'content_hash': hashlib.md5(clean_text.encode()).hexdigest(),
            'content_type': response.headers.get('content-type', ''),
            'crawled_at': datetime.datetime.utcnow().isoformat(),
            'source': source_name
        }

        print(f"  ✅ Extracted {word_count} words")
        return [document]

    except Exception as e:
        print(f"  ❌ Error crawling {url}: {e}")
        return []


def crawl_target_documentation_scrapy(target_name: str) -> List[Dict[str, Any]]:
    """Crawl documentation for a target using Scrapy."""
    import sys
    from pathlib import Path

    # Add src to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from config_loader import get_merged_config, get_crawl_config, get_data_paths

    # Load configuration
    config = get_merged_config(target_name)
    crawl_config = get_crawl_config(config)
    data_paths = get_data_paths(config)

    all_documents = []

    # Check if we have multiple sources configured
    sources = crawl_config.get('sources', [])

    if sources:
        # New multi-source configuration
        print(f"Found {len(sources)} documentation sources to crawl")

        for source in sources:
            source_name = source.get('name', 'unnamed')
            base_url = source.get('base_url')
            follow_links = source.get('follow_links', True)
            max_depth = source.get('max_depth', 10)
            max_pages = source.get('max_pages', 1000)

            if not base_url:
                print(f"  ⚠️  Skipping source '{source_name}': no base_url")
                continue

            print(f"\n{'='*60}")
            print(f"Crawling source: {source_name}")
            print(f"  URL: {base_url}")
            print(f"  Follow links: {follow_links}")
            print(f"  Max depth: {max_depth}")
            print(f"  Max pages: {max_pages}")

            # Extract exclude patterns
            exclude_patterns = []
            for pattern in source.get('exclude_patterns', []):
                if '/' in pattern:
                    filename = pattern.split('/')[-1]
                else:
                    filename = pattern
                filename = filename.replace('*', '').replace('.html', '')
                if filename:
                    exclude_patterns.append(filename)

            if exclude_patterns:
                print(f"  Exclude patterns: {exclude_patterns}")

            # If follow_links is False, just fetch the single page
            if not follow_links:
                documents = crawl_single_page(base_url, source_name)
            else:
                documents = crawl_documentation(
                    base_url=base_url,
                    exclude_patterns=exclude_patterns,
                    max_pages=max_pages
                )

            print(f"  ✅ Crawled {len(documents)} documents from '{source_name}'")
            all_documents.extend(documents)

    else:
        # Legacy single-source configuration
        if not crawl_config['base_url']:
            raise ValueError(f"No base_url configured for target: {target_name}")

        base_url = crawl_config['base_url']

        # Extract simple exclude patterns (just the filenames)
        exclude_patterns = []
        for pattern in crawl_config.get('exclude_patterns', []):
            if '/' in pattern:
                filename = pattern.split('/')[-1]
            else:
                filename = pattern
            filename = filename.replace('*', '').replace('.html', '')
            if filename:
                exclude_patterns.append(filename)

        print(f"Crawling {base_url}")
        print(f"Exclude patterns: {exclude_patterns}")

        # Crawl documents
        all_documents = crawl_documentation(
            base_url=base_url,
            exclude_patterns=exclude_patterns,
            max_pages=1000
        )

    print(f"\n{'='*60}")
    print(f"Total documents crawled: {len(all_documents)}")

    # Save to file
    output_file = Path(data_paths['raw_dir']) / f"{target_name}_docs.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_documents, f, indent=2, ensure_ascii=False)

    print(f"Saved to {output_file}")

    return all_documents


if __name__ == "__main__":
    # Test crawling
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else 'cuda_q'
    docs = crawl_target_documentation_scrapy(target)
    print(f"\nSuccessfully crawled {len(docs)} documents for {target}")
