# Multi-Source Documentation Crawling

The system supports crawling documentation from multiple sources with different crawl settings for each source.

## Configuration

Configure multiple documentation sources in your target YAML file (e.g., `config/targets/cuda_q.yaml`):

```yaml
documentation:
  sources:
    - name: "main_docs"
      base_url: "https://nvidia.github.io/cuda-quantum/latest/"
      follow_links: true      # Recursively follow links
      max_depth: 10           # Maximum link depth to follow
      max_pages: 1000         # Maximum pages to crawl
      crawl_patterns:
        - "https://nvidia.github.io/cuda-quantum/latest/**/*.html"
      exclude_patterns:
        - "**/genindex.html"
        - "**/search.html"
        - "**/404.html"

    - name: "github_releases"
      base_url: "https://github.com/NVIDIA/cuda-quantum/releases"
      follow_links: false     # Only crawl this single page
      max_depth: 0            # No depth - just the starting URL
      max_pages: 1            # Limit to 1 page
      extract_content: true   # Extract release notes and version info

    - name: "api_reference"
      base_url: "https://nvidia.github.io/cuda-quantum/latest/api/"
      follow_links: true
      max_depth: 5            # Shallower depth for API docs
      max_pages: 500
      exclude_patterns:
        - "**/genindex.html"
```

## Configuration Fields

### Required Fields

- **`name`**: Unique identifier for this source (used in logging)
- **`base_url`**: Starting URL for crawling

### Optional Fields

- **`follow_links`** (default: `true`): Whether to recursively follow links
  - `true`: Use Scrapy to crawl all linked pages
  - `false`: Only fetch the single page at `base_url`

- **`max_depth`** (default: `10`): Maximum depth to follow links
  - `0`: Only the starting page
  - `1`: Starting page + direct links
  - `10+`: Deep crawling

- **`max_pages`** (default: `1000`): Maximum total pages to crawl from this source
  - Prevents runaway crawling
  - Good for rate limiting

- **`crawl_patterns`**: List of glob patterns for URLs to include
  - Example: `"https://example.com/**/*.html"` matches all HTML files

- **`exclude_patterns`**: List of glob patterns for URLs to exclude
  - Example: `"**/genindex.html"` excludes all genindex.html files
  - Evaluated before `crawl_patterns`

## Usage

Once configured, simply run the setup command:

```bash
python src/main.py setup --target cuda_q --force-crawl
```

The crawler will automatically:
1. Process each source sequentially
2. Apply the crawl settings for each source
3. Combine all documents into a single dataset
4. Generate embeddings for the combined dataset

## Example Output

```
Found 2 documentation sources to crawl

============================================================
Crawling source: main_docs
  URL: https://nvidia.github.io/cuda-quantum/latest/
  Follow links: True
  Max depth: 10
  Max pages: 1000
  ✅ Crawled 308 documents from 'main_docs'

============================================================
Crawling source: github_releases
  URL: https://github.com/NVIDIA/cuda-quantum/releases
  Follow links: False
  Max depth: 0
  Max pages: 1
  Fetching single page: https://github.com/NVIDIA/cuda-quantum/releases
  ✅ Extracted 6772 words
  ✅ Crawled 1 documents from 'github_releases'

============================================================
Total documents crawled: 309
```

## Use Cases

### 1. Documentation + Release Notes

Combine official docs with GitHub releases for version-specific information:

```yaml
sources:
  - name: "docs"
    base_url: "https://example.com/docs/"
    follow_links: true
    max_pages: 1000

  - name: "releases"
    base_url: "https://github.com/org/repo/releases"
    follow_links: false  # Just the releases page
```

### 2. Multiple Documentation Versions

Crawl both stable and latest documentation:

```yaml
sources:
  - name: "stable_docs"
    base_url: "https://example.com/docs/stable/"
    follow_links: true

  - name: "latest_docs"
    base_url: "https://example.com/docs/latest/"
    follow_links: true
```

### 3. Documentation + Tutorials + API Reference

Separate sources with different crawl depths:

```yaml
sources:
  - name: "tutorials"
    base_url: "https://example.com/tutorials/"
    follow_links: true
    max_depth: 3    # Shallow crawl

  - name: "api"
    base_url: "https://example.com/api/"
    follow_links: true
    max_depth: 10   # Deep crawl for complete API coverage

  - name: "changelog"
    base_url: "https://example.com/changelog.html"
    follow_links: false  # Single page
```

## Backward Compatibility

The old single-source configuration is still supported:

```yaml
documentation:
  base_url: "https://nvidia.github.io/cuda-quantum/latest/"
  crawl_patterns:
    - "https://nvidia.github.io/cuda-quantum/latest/**/*.html"
  exclude_patterns:
    - "**/genindex.html"
```

This will be treated as a single source with `follow_links: true` and default settings.

## Tips

1. **Start with `follow_links: false`** to test single-page extraction before enabling full crawling

2. **Use `max_pages` limits** during development to avoid long crawl times

3. **Set appropriate `max_depth`** values:
   - 0-1: Single pages or landing pages only
   - 2-5: Documentation sections
   - 10+: Complete documentation trees

4. **Use `exclude_patterns`** to skip:
   - Search pages (`**/search.html`)
   - Index pages (`**/genindex.html`)
   - 404 pages (`**/404.html`)
   - Printer-friendly versions (`**/print/**`)

5. **Name sources descriptively** for easier debugging and log analysis
