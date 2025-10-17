"""
Target management utilities for handling multiple documentation targets.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml
import json
from datetime import datetime
import shutil

from config_loader import load_base_config, load_target_config, get_merged_config


class TargetManager:
    """Manager for handling multiple documentation targets."""

    def __init__(self):
        self.base_config_path = Path(__file__).parent.parent.parent / "config" / "base_config.yaml"
        self.targets_dir = Path(__file__).parent.parent.parent / "config" / "targets"

    def list_targets(self) -> List[Dict[str, Any]]:
        """List all available targets with their metadata."""
        targets = []

        if not self.targets_dir.exists():
            return targets

        for config_file in self.targets_dir.glob("*.yaml"):
            try:
                target_name = config_file.stem
                config = load_target_config(target_name)
                target_info = config.get('target', {})

                targets.append({
                    'name': target_name,
                    'display_name': target_info.get('name', target_name),
                    'description': target_info.get('description', ''),
                    'domain': target_info.get('domain', ''),
                    'config_file': str(config_file)
                })

            except Exception as e:
                targets.append({
                    'name': config_file.stem,
                    'display_name': config_file.stem,
                    'description': f'Error loading config: {e}',
                    'domain': 'unknown',
                    'config_file': str(config_file),
                    'error': str(e)
                })

        return sorted(targets, key=lambda x: x['name'])

    def create_target(self, target_name: str, target_config: Dict[str, Any]) -> bool:
        """Create a new target configuration."""
        try:
            config_file = self.targets_dir / f"{target_name}.yaml"

            if config_file.exists():
                raise ValueError(f"Target '{target_name}' already exists")

            # Ensure targets directory exists
            self.targets_dir.mkdir(parents=True, exist_ok=True)

            # Validate required fields
            required_fields = ['target', 'documentation']
            for field in required_fields:
                if field not in target_config:
                    raise ValueError(f"Missing required field: {field}")

            # Write configuration
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(target_config, f, indent=2, default_flow_style=False)

            return True

        except Exception as e:
            print(f"Error creating target '{target_name}': {e}")
            return False

    def delete_target(self, target_name: str, confirm: bool = False) -> bool:
        """Delete a target configuration and optionally its data."""
        if not confirm:
            raise ValueError("Target deletion requires confirmation (set confirm=True)")

        try:
            config_file = self.targets_dir / f"{target_name}.yaml"

            if not config_file.exists():
                raise ValueError(f"Target '{target_name}' does not exist")

            # Remove configuration file
            config_file.unlink()

            # Also clean up data files
            try:
                from setup_pipeline import cleanup_target_data
                cleanup_target_data(target_name, confirm=True)
            except Exception as e:
                print(f"Warning: Could not clean up data for {target_name}: {e}")

            return True

        except Exception as e:
            print(f"Error deleting target '{target_name}': {e}")
            return False

    def clone_target(self, source_target: str, new_target: str, modifications: Optional[Dict[str, Any]] = None) -> bool:
        """Clone an existing target with optional modifications."""
        try:
            source_config = load_target_config(source_target)
            new_config = source_config.copy()

            # Apply modifications
            if modifications:
                self._deep_update(new_config, modifications)

            # Update target name in the config
            if 'target' not in new_config:
                new_config['target'] = {}
            new_config['target']['name'] = new_target

            return self.create_target(new_target, new_config)

        except Exception as e:
            print(f"Error cloning target '{source_target}' to '{new_target}': {e}")
            return False

    def validate_target(self, target_name: str) -> Dict[str, Any]:
        """Validate a target configuration."""
        validation_result = {
            'is_valid': False,
            'errors': [],
            'warnings': [],
            'suggestions': []
        }

        try:
            config = load_target_config(target_name)

            # Check required sections
            required_sections = ['target', 'documentation']
            for section in required_sections:
                if section not in config:
                    validation_result['errors'].append(f"Missing required section: {section}")

            # Validate target section
            target_info = config.get('target', {})
            if not target_info.get('name'):
                validation_result['errors'].append("Target name is required")

            # Validate documentation section
            doc_config = config.get('documentation', {})
            if not doc_config.get('base_url'):
                validation_result['errors'].append("Documentation base_url is required")

            base_url = doc_config.get('base_url', '')
            if base_url and not (base_url.startswith('http://') or base_url.startswith('https://')):
                validation_result['warnings'].append("Documentation base_url should start with http:// or https://")

            # Check crawl patterns
            crawl_patterns = doc_config.get('crawl_patterns', [])
            if not crawl_patterns:
                validation_result['warnings'].append("No crawl patterns defined - this may limit documentation discovery")

            # Check agents configuration
            agents_config = config.get('agents', {})
            expected_agents = ['query_agent', 'code_agent', 'validation_agent']

            for agent in expected_agents:
                if agent not in agents_config:
                    validation_result['warnings'].append(f"Agent '{agent}' not configured - using defaults")

            # Check prompt templates
            prompt_templates = config.get('prompt_templates', {})
            if not prompt_templates:
                validation_result['suggestions'].append("Consider adding custom prompt templates for better responses")

            # Overall validation
            validation_result['is_valid'] = len(validation_result['errors']) == 0

            if validation_result['is_valid']:
                validation_result['message'] = "Target configuration is valid"
            else:
                validation_result['message'] = f"Target configuration has {len(validation_result['errors'])} errors"

        except Exception as e:
            validation_result['errors'].append(f"Configuration loading error: {e}")
            validation_result['message'] = "Failed to load target configuration"

        return validation_result

    def get_target_template(self, template_type: str = 'basic') -> Dict[str, Any]:
        """Get a template for creating new targets."""
        if template_type == 'basic':
            return {
                'target': {
                    'name': '',
                    'description': '',
                    'domain': ''
                },
                'documentation': {
                    'base_url': '',
                    'crawl_patterns': [
                        '**/*.html'
                    ],
                    'exclude_patterns': [
                        '*/genindex.html',
                        '*/search.html'
                    ]
                },
                'agents': {
                    'query_agent': {
                        'role': 'Documentation Specialist',
                        'goal': 'Find relevant documentation and code examples',
                        'backstory': 'Expert in documentation and framework knowledge'
                    },
                    'code_agent': {
                        'role': 'Code Generator',
                        'goal': 'Generate working code examples',
                        'backstory': 'Senior software engineer with framework expertise'
                    },
                    'validation_agent': {
                        'role': 'Code Validator',
                        'goal': 'Review and validate code for best practices',
                        'backstory': 'Code review expert with deep framework knowledge'
                    }
                }
            }

        elif template_type == 'advanced':
            return {
                'target': {
                    'name': '',
                    'description': '',
                    'domain': ''
                },
                'documentation': {
                    'base_url': '',
                    'crawl_patterns': [
                        '**/*.html'
                    ],
                    'exclude_patterns': [
                        '*/genindex.html',
                        '*/search.html',
                        '*/404.html'
                    ]
                },
                'agents': {
                    'query_agent': {
                        'role': 'Documentation Specialist',
                        'goal': 'Find relevant documentation and code examples',
                        'backstory': 'Expert in documentation and framework knowledge'
                    },
                    'code_agent': {
                        'role': 'Code Generator',
                        'goal': 'Generate working code examples',
                        'backstory': 'Senior software engineer with framework expertise'
                    },
                    'validation_agent': {
                        'role': 'Code Validator',
                        'goal': 'Review and validate code for best practices',
                        'backstory': 'Code review expert with deep framework knowledge'
                    }
                },
                'prompt_templates': {
                    'code_generation': '''
Based on the following documentation context:
{context}

Generate code for: {query}

Requirements:
- Use proper syntax and patterns
- Include necessary imports
- Add explanatory comments
- Follow best practices
                    ''',
                    'validation': '''
Review this code for correctness:
{code}

Context: {context}

Check for:
- Syntax correctness
- Best practices
- Framework compliance
- Performance considerations
                    '''
                }
            }

        else:
            raise ValueError(f"Unknown template type: {template_type}")

    def export_target(self, target_name: str, export_path: str, include_data: bool = False) -> bool:
        """Export a target configuration and optionally its data."""
        try:
            export_dir = Path(export_path)
            export_dir.mkdir(parents=True, exist_ok=True)

            # Export configuration
            config = load_target_config(target_name)
            config_file = export_dir / f"{target_name}_config.yaml"

            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.safe_dump(config, f, indent=2, default_flow_style=False)

            export_manifest = {
                'target_name': target_name,
                'export_timestamp': datetime.utcnow().isoformat(),
                'includes_data': include_data,
                'files': [str(config_file.name)]
            }

            if include_data:
                # Export data files if they exist
                merged_config = get_merged_config(target_name)
                from config_loader import get_data_paths
                data_paths = get_data_paths(merged_config)

                data_files = [
                    ('raw_docs', Path(data_paths['raw_dir']) / f"{target_name}_docs.json"),
                    ('processed_docs', Path(data_paths['processed_dir']) / f"{target_name}_processed_docs.json"),
                    ('chunks', Path(data_paths['processed_dir']) / f"{target_name}_chunks.json"),
                    ('embeddings', Path(data_paths['embeddings_dir']) / f"{target_name}_embedding_index.json")
                ]

                for data_type, source_file in data_files:
                    if source_file.exists():
                        dest_file = export_dir / f"{target_name}_{data_type}.json"
                        shutil.copy2(source_file, dest_file)
                        export_manifest['files'].append(str(dest_file.name))

            # Create manifest
            manifest_file = export_dir / f"{target_name}_manifest.json"
            with open(manifest_file, 'w', encoding='utf-8') as f:
                json.dump(export_manifest, f, indent=2)

            print(f"Exported target '{target_name}' to {export_dir}")
            return True

        except Exception as e:
            print(f"Error exporting target '{target_name}': {e}")
            return False

    def import_target(self, import_path: str, new_name: Optional[str] = None) -> bool:
        """Import a target from exported files."""
        try:
            import_dir = Path(import_path)

            if not import_dir.exists():
                raise ValueError(f"Import path does not exist: {import_path}")

            # Look for manifest file
            manifest_files = list(import_dir.glob("*_manifest.json"))
            if not manifest_files:
                raise ValueError("No manifest file found in import directory")

            manifest_file = manifest_files[0]
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            original_name = manifest['target_name']
            target_name = new_name if new_name else original_name

            # Import configuration
            config_file = import_dir / f"{original_name}_config.yaml"
            if not config_file.exists():
                raise ValueError(f"Configuration file not found: {config_file}")

            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Update target name if different
            if new_name:
                if 'target' not in config:
                    config['target'] = {}
                config['target']['name'] = new_name

            # Create target
            if not self.create_target(target_name, config):
                raise ValueError(f"Failed to create target '{target_name}'")

            # Import data files if available
            if manifest.get('includes_data', False):
                merged_config = get_merged_config(target_name)
                from config_loader import get_data_paths
                data_paths = get_data_paths(merged_config)

                data_mappings = [
                    (f"{original_name}_raw_docs.json", Path(data_paths['raw_dir']) / f"{target_name}_docs.json"),
                    (f"{original_name}_processed_docs.json", Path(data_paths['processed_dir']) / f"{target_name}_processed_docs.json"),
                    (f"{original_name}_chunks.json", Path(data_paths['processed_dir']) / f"{target_name}_chunks.json"),
                    (f"{original_name}_embeddings.json", Path(data_paths['embeddings_dir']) / f"{target_name}_embedding_index.json")
                ]

                for source_name, dest_path in data_mappings:
                    source_file = import_dir / source_name
                    if source_file.exists():
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_file, dest_path)

            print(f"Imported target '{target_name}' successfully")
            return True

        except Exception as e:
            print(f"Error importing target: {e}")
            return False

    def _deep_update(self, base_dict: Dict, update_dict: Dict) -> None:
        """Deep update a dictionary with another dictionary."""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

    def get_target_stats(self, target_name: str) -> Dict[str, Any]:
        """Get statistics about a target."""
        try:
            from setup_pipeline import get_setup_status_report

            stats = get_setup_status_report(target_name)
            config = load_target_config(target_name)

            # Add configuration stats
            stats['config_stats'] = {
                'agents_configured': len(config.get('agents', {})),
                'prompt_templates': len(config.get('prompt_templates', {})),
                'crawl_patterns': len(config.get('documentation', {}).get('crawl_patterns', [])),
                'exclude_patterns': len(config.get('documentation', {}).get('exclude_patterns', []))
            }

            return stats

        except Exception as e:
            return {
                'target': target_name,
                'error': str(e),
                'overall_status': 'error'
            }