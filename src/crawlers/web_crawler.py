import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from pathlib import Path
import json
import hashlib
from typing import List, Set, Dict, Any, Optional
import re
from tqdm import tqdm


async def fetch_url_async(session: aiohttp.ClientSession, url: str) -> Optional[Dict[str, Any]]:
    """Fetch single URL asynchronously."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                content = await response.text()
                return {
                    'url': url,
                    'content': content,
                    'status': response.status,
                    'content_type': response.headers.get('content-type', '')
                }
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None


def extract_text_from_html(html_content: str) -> Dict[str, Any]:
    """Extract clean text and metadata from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')

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
        if code_text:
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

    return {
        'title': title_text,
        'content': clean_text,
        'code_blocks': code_blocks,
        'headers': headers,
        'word_count': len(clean_text.split())
    }


def discover_urls(base_url: str, crawl_patterns: List[str], exclude_patterns: List[str] = None) -> Set[str]:
    """Discover URLs to crawl from sitemap or by following links."""
    discovered_urls = set()
    exclude_patterns = exclude_patterns or []

    try:
        # Try to get sitemap first
        sitemap_urls = [
            urljoin(base_url, '/sitemap.xml'),
            urljoin(base_url, '/sitemap_index.xml')
        ]

        for sitemap_url in sitemap_urls:
            try:
                response = requests.get(sitemap_url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'xml')
                    for loc in soup.find_all('loc'):
                        url = loc.get_text().strip()
                        if should_crawl_url(url, crawl_patterns, exclude_patterns):
                            discovered_urls.add(url)
                    break
            except:
                continue

        # If no sitemap, crawl by following links
        if not discovered_urls:
            discovered_urls = crawl_by_following_links(base_url, crawl_patterns, exclude_patterns)

    except Exception as e:
        print(f"Error discovering URLs: {e}")

    return discovered_urls


def crawl_by_following_links(base_url: str, crawl_patterns: List[str], exclude_patterns: List[str], max_depth: int = 3) -> Set[str]:
    """Crawl by following links from base URL."""
    discovered_urls = set()
    visited_urls = set()
    urls_to_visit = [(base_url, 0)]

    while urls_to_visit:
        current_url, depth = urls_to_visit.pop(0)

        if current_url in visited_urls or depth > max_depth:
            continue

        visited_urls.add(current_url)

        try:
            response = requests.get(current_url, timeout=10)
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.content, 'html.parser')

            # Add current URL if it matches patterns
            if should_crawl_url(current_url, crawl_patterns, exclude_patterns):
                discovered_urls.add(current_url)

            # Find all links
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(current_url, href)

                # Only follow links within the same domain
                if urlparse(absolute_url).netloc == urlparse(base_url).netloc:
                    urls_to_visit.append((absolute_url, depth + 1))

        except Exception as e:
            print(f"Error crawling {current_url}: {e}")

    return discovered_urls


def should_crawl_url(url: str, crawl_patterns: List[str], exclude_patterns: List[str] = None) -> bool:
    """Check if URL should be crawled based on patterns."""
    exclude_patterns = exclude_patterns or []

    def glob_to_regex(pattern: str) -> str:
        """Convert glob pattern to regex pattern."""
        # Escape special regex characters except * and **
        import re as regex_module
        pattern = regex_module.escape(pattern)

        # Replace escaped wildcards back and convert to regex
        # **/ matches zero or more path segments (including empty)
        pattern = pattern.replace(r'\*\*/', '(?:.*/)?')
        # ** alone matches everything
        pattern = pattern.replace(r'\*\*', '.*')
        # * matches any characters except /
        pattern = pattern.replace(r'\*', r'[^/]*')

        return '^' + pattern + '$'

    # Check exclude patterns first
    for pattern in exclude_patterns:
        regex_pattern = glob_to_regex(pattern)
        if re.match(regex_pattern, url):
            return False

    # Check include patterns
    for pattern in crawl_patterns:
        regex_pattern = glob_to_regex(pattern)
        if re.match(regex_pattern, url):
            return True

    return False


async def crawl_documentation_async(config: Dict[str, Any], max_concurrent: int = 10) -> List[Dict[str, Any]]:
    """Crawl documentation asynchronously."""
    base_url = config['base_url']
    crawl_patterns = config['crawl_patterns']
    exclude_patterns = config.get('exclude_patterns', [])

    print(f"Discovering URLs from {base_url}")
    urls_to_crawl = discover_urls(base_url, crawl_patterns, exclude_patterns)
    print(f"Found {len(urls_to_crawl)} URLs to crawl")

    if not urls_to_crawl:
        print("No URLs found to crawl")
        return []

    documents = []
    semaphore = asyncio.Semaphore(max_concurrent)

    async def crawl_with_semaphore(session: aiohttp.ClientSession, url: str):
        async with semaphore:
            return await fetch_url_async(session, url)

    async with aiohttp.ClientSession() as session:
        tasks = [crawl_with_semaphore(session, url) for url in urls_to_crawl]

        print("Crawling documents...")
        results = []
        for task in tqdm(asyncio.as_completed(tasks), total=len(tasks)):
            result = await task
            if result:
                results.append(result)

        # Process HTML content
        for result in tqdm(results, desc="Processing HTML"):
            try:
                extracted = extract_text_from_html(result['content'])

                document = {
                    'url': result['url'],
                    'title': extracted['title'],
                    'content': extracted['content'],
                    'code_blocks': extracted['code_blocks'],
                    'headers': extracted['headers'],
                    'word_count': extracted['word_count'],
                    'content_hash': hashlib.md5(extracted['content'].encode()).hexdigest(),
                    'content_type': result.get('content_type', ''),
                    'crawled_at': None  # Will be set by caller
                }

                if document['word_count'] > 50:  # Filter out very short pages
                    documents.append(document)

            except Exception as e:
                print(f"Error processing {result['url']}: {e}")

    print(f"Successfully crawled {len(documents)} documents")
    return documents


def save_crawled_documents(documents: List[Dict[str, Any]], output_file: str) -> None:
    """Save crawled documents to JSON file."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Add timestamp
    import datetime
    for doc in documents:
        doc['crawled_at'] = datetime.datetime.utcnow().isoformat()

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(documents, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(documents)} documents to {output_file}")


def load_crawled_documents(input_file: str) -> List[Dict[str, Any]]:
    """Load crawled documents from JSON file."""
    with open(input_file, 'r', encoding='utf-8') as f:
        return json.load(f)


async def crawl_target_documentation(target_name: str) -> List[Dict[str, Any]]:
    """Main function to crawl documentation for a target."""
    from config_loader import get_merged_config, get_crawl_config, get_data_paths

    # Load configuration
    config = get_merged_config(target_name)
    crawl_config = get_crawl_config(config)
    data_paths = get_data_paths(config)

    if not crawl_config['base_url']:
        raise ValueError(f"No base_url configured for target: {target_name}")

    # Crawl documents
    documents = await crawl_documentation_async(crawl_config)

    # Save to file
    output_file = Path(data_paths['raw_dir']) / f"{target_name}_docs.json"
    save_crawled_documents(documents, str(output_file))

    return documents