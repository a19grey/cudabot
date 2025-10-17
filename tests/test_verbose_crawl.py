#!/usr/bin/env python3
"""Verbose test of CUDA-Q documentation crawling."""

import asyncio
import aiohttp
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def verbose_crawl_test():
    """Test crawling with verbose output."""
    print("🧪 Testing CUDA-Q Documentation Crawling with Verbose Output")
    print("=" * 60)

    start_time = time.time()

    # Test 1: Single page fetch
    print("\n1. 📡 Testing single page fetch...")
    try:
        async with aiohttp.ClientSession() as session:
            print("   - Creating session...")
            url = 'https://nvidia.github.io/cuda-quantum/latest/'
            print(f"   - Fetching: {url}")

            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                print(f"   - Response status: {response.status}")
                print(f"   - Content type: {response.headers.get('content-type')}")

                if response.status == 200:
                    content = await response.text()
                    print(f"   - Content length: {len(content)} characters")
                    print(f"   - Contains 'CUDA-Q': {'CUDA-Q' in content}")
                    print("   ✅ Single page fetch successful")
                else:
                    print(f"   ❌ Bad response status: {response.status}")
                    return False

    except Exception as e:
        print(f"   ❌ Error in single page fetch: {e}")
        return False

    # Test 2: Document processing
    print("\n2. 🔄 Testing document processing...")
    try:
        from crawlers.web_crawler import extract_text_from_html
        print("   - Importing extract_text_from_html...")

        print("   - Processing HTML content...")
        processed = extract_text_from_html(content)

        print(f"   - Title: {processed['title'][:50]}...")
        print(f"   - Content length: {len(processed['content'])} chars")
        print(f"   - Word count: {processed['word_count']}")
        print(f"   - Code blocks: {len(processed['code_blocks'])}")
        print(f"   - Headers: {len(processed['headers'])}")
        print("   ✅ Document processing successful")

    except Exception as e:
        print(f"   ❌ Error in document processing: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 3: URL discovery (limited)
    print("\n3. 🔍 Testing URL discovery...")
    try:
        from crawlers.web_crawler import discover_urls
        print("   - Importing discover_urls...")

        base_url = 'https://nvidia.github.io/cuda-quantum/latest/'
        patterns = ['https://nvidia.github.io/cuda-quantum/latest/**/*.html']
        exclude = ['*/genindex.html', '*/search.html']

        print(f"   - Base URL: {base_url}")
        print(f"   - Patterns: {patterns}")

        print("   - Discovering URLs...")
        urls = discover_urls(base_url, patterns, exclude)

        print(f"   - Found {len(urls)} URLs")
        if urls:
            print("   - First 5 URLs:")
            for i, url in enumerate(list(urls)[:5]):
                print(f"     {i+1}. {url}")
        print("   ✅ URL discovery successful")

    except Exception as e:
        print(f"   ❌ Error in URL discovery: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 4: Limited async crawl
    print("\n4. 🕷️ Testing limited async crawl (first 3 pages)...")
    try:
        limited_urls = list(urls)[:3] if urls else [url]
        print(f"   - Crawling {len(limited_urls)} pages...")

        documents = []

        async with aiohttp.ClientSession() as session:
            for i, page_url in enumerate(limited_urls, 1):
                print(f"   - [{i}/{len(limited_urls)}] Fetching: {page_url[:60]}...")

                try:
                    async with session.get(page_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status == 200:
                            content = await response.text()
                            processed = extract_text_from_html(content)

                            document = {
                                'url': page_url,
                                'title': processed['title'],
                                'content': processed['content'],
                                'code_blocks': processed['code_blocks'],
                                'headers': processed['headers'],
                                'word_count': processed['word_count'],
                                'content_hash': hashlib.md5(processed['content'].encode()).hexdigest(),
                                'crawled_at': time.time()
                            }
                            documents.append(document)
                            print(f"     ✅ Success: {processed['word_count']} words")
                        else:
                            print(f"     ⚠️ Status {response.status}")

                except Exception as e:
                    print(f"     ❌ Error: {e}")

        print(f"   ✅ Crawled {len(documents)} documents successfully")

        if documents:
            print("\n   📋 Document Summary:")
            for i, doc in enumerate(documents, 1):
                print(f"     {i}. {doc['title'][:40]}... ({doc['word_count']} words)")

    except Exception as e:
        print(f"   ❌ Error in async crawl: {e}")
        import traceback
        traceback.print_exc()
        return False

    elapsed = time.time() - start_time
    print(f"\n🎉 All tests completed successfully in {elapsed:.1f} seconds!")
    print(f"📊 Final results: {len(documents)} documents ready for processing")

    return True

if __name__ == "__main__":
    import hashlib
    success = asyncio.run(verbose_crawl_test())
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}")