import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional


def load_yaml_config(file_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML file {file_path}: {e}")


def load_base_config() -> Dict[str, Any]:
    """Load base platform configuration."""
    config_path = Path(__file__).parent.parent / "config" / "base_config.yaml"
    return load_yaml_config(str(config_path))


def load_target_config(target_name: str) -> Dict[str, Any]:
    """Load target-specific configuration."""
    config_path = Path(__file__).parent.parent / "config" / "targets" / f"{target_name}.yaml"
    return load_yaml_config(str(config_path))


def get_merged_config(target_name: str) -> Dict[str, Any]:
    """Get merged configuration combining base and target configs."""
    base_config = load_base_config()
    target_config = load_target_config(target_name)

    # Deep merge configurations
    merged = base_config.copy()
    merged.update(target_config)

    return merged


def get_data_paths(config: Dict[str, Any]) -> Dict[str, str]:
    """Extract and validate data paths from configuration."""
    storage = config.get('storage', {})
    base_dir = Path(storage.get('data_dir', './data'))

    paths = {
        'data_dir': str(base_dir),
        'embeddings_dir': str(base_dir / 'embeddings'),
        'raw_dir': str(base_dir / 'raw'),
        'processed_dir': str(base_dir / 'processed')
    }

    # Create directories if they don't exist
    for path in paths.values():
        os.makedirs(path, exist_ok=True)

    return paths


def get_embedding_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract embedding configuration."""
    return config.get('embedding', {
        'model': 'sentence-transformers/all-MiniLM-L6-v2',
        'chunk_size': 512,
        'chunk_overlap': 50,
        'similarity_threshold': 0.7,
        'max_results': 5
    })


def get_crawl_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract crawling configuration."""
    doc_config = config.get('documentation', {})
    return {
        'base_url': doc_config.get('base_url'),
        'crawl_patterns': doc_config.get('crawl_patterns', []),
        'exclude_patterns': doc_config.get('exclude_patterns', []),
        'sources': doc_config.get('sources', [])  # Support multi-source configuration
    }


def get_agent_config(config: Dict[str, Any], agent_name: str) -> Optional[Dict[str, Any]]:
    """Get configuration for specific agent."""
    agents = config.get('agents', {})
    return agents.get(agent_name)


def get_prompt_template(config: Dict[str, Any], template_name: str) -> Optional[str]:
    """Get prompt template from configuration."""
    templates = config.get('prompt_templates', {})
    return templates.get(template_name)