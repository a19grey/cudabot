"""
Setup pipeline for initializing targets with documentation crawling,
processing, and embedding generation.
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, List
import json

from config_loader import get_merged_config, get_data_paths, get_embedding_config
from crawlers.scrapy_crawler import crawl_target_documentation_scrapy
from processing.document_processor import process_documents_pipeline, load_processed_documents
from embeddings.embedding_generator import create_embeddings_for_target
from embeddings.vector_store import create_vector_store_for_target
from processing.chunking import load_chunks_from_file
from preprocessing.hierarchical_processor import HierarchicalDocumentProcessor


def check_target_setup(target_name: str) -> Dict[str, Any]:
    """Check if a target is properly set up."""
    try:
        config = get_merged_config(target_name)
        data_paths = get_data_paths(config)

        components = {
            'config': False,
            'raw_docs': False,
            'processed_docs': False,
            'chunks': False,
            'hierarchical_map': False,
            'summaries': False,
            'overview': False,
            'embeddings': False,
            'vector_store': False
        }

        # Check configuration
        try:
            components['config'] = bool(config.get('target', {}).get('name'))
        except:
            pass

        # Check raw documentation
        raw_docs_file = Path(data_paths['raw_dir']) / f"{target_name}_docs.json"
        components['raw_docs'] = raw_docs_file.exists()

        # Check processed documents
        processed_docs_file = Path(data_paths['processed_dir']) / f"{target_name}_processed_docs.json"
        components['processed_docs'] = processed_docs_file.exists()

        # Check chunks
        chunks_file = Path(data_paths['processed_dir']) / f"{target_name}_chunks.json"
        components['chunks'] = chunks_file.exists()

        # Check hierarchical preprocessing artifacts
        doc_map_file = Path(data_paths['processed_dir']) / f"{target_name}_doc_map.json"
        components['hierarchical_map'] = doc_map_file.exists()

        summaries_file = Path(data_paths['processed_dir']) / f"{target_name}_summaries.json"
        components['summaries'] = summaries_file.exists()

        overview_file = Path(data_paths['processed_dir']) / f"{target_name}_overview.txt"
        components['overview'] = overview_file.exists()

        # Check embeddings
        embeddings_file = Path(data_paths['embeddings_dir']) / f"{target_name}_embedding_index.json"
        components['embeddings'] = embeddings_file.exists()

        # Check vector store
        vector_store_dir = Path(data_paths['embeddings_dir'])
        components['vector_store'] = any(vector_store_dir.glob(f"*{target_name}*"))

        # Overall readiness
        is_ready = all(components.values())

        return {
            'is_ready': is_ready,
            'components': components,
            'missing_components': [k for k, v in components.items() if not v]
        }

    except Exception as e:
        return {
            'is_ready': False,
            'components': {},
            'missing_components': ['all'],
            'error': str(e)
        }


def setup_target_pipeline_impl(
    target_name: str,
    crawl_docs: bool = True,
    force_recrawl: bool = False,
    max_concurrent: int = 10
) -> Dict[str, Any]:
    """Complete setup pipeline for a target."""
    print(f"Starting setup pipeline for target: {target_name}")

    try:
        # Load configuration
        config = get_merged_config(target_name)
        data_paths = get_data_paths(config)
        embedding_config = get_embedding_config(config)

        # Add data paths to config for downstream functions
        config['data_paths'] = data_paths

        setup_result = {
            'target': target_name,
            'documents_crawled': 0,
            'chunks_created': 0,
            'embeddings_created': 0,
            'steps_completed': []
        }

        # Step 1: Crawl documentation
        raw_docs_file = Path(data_paths['raw_dir']) / f"{target_name}_docs.json"

        if crawl_docs and (force_recrawl or not raw_docs_file.exists()):
            print("Step 1: Crawling documentation...")
            # Scrapy crawler runs synchronously, not async
            documents = crawl_target_documentation_scrapy(target_name)
            setup_result['documents_crawled'] = len(documents)
            setup_result['steps_completed'].append('crawl_docs')
            print(f"✅ Crawled {len(documents)} documents")
        else:
            if raw_docs_file.exists():
                print("Step 1: Loading existing documentation...")
                with open(raw_docs_file, 'r', encoding='utf-8') as f:
                    documents = json.load(f)
                setup_result['documents_crawled'] = len(documents)
                print(f"✅ Loaded {len(documents)} documents from cache")
            else:
                raise ValueError("No documentation found and crawling is disabled")

        # Step 2: Process documents and create chunks
        processed_docs_file = Path(data_paths['processed_dir']) / f"{target_name}_processed_docs.json"
        chunks_file = Path(data_paths['processed_dir']) / f"{target_name}_chunks.json"

        if force_recrawl or not (processed_docs_file.exists() and chunks_file.exists()):
            print("Step 2: Processing documents and creating chunks...")
            processed_docs, chunks = process_documents_pipeline(
                documents,
                embedding_config,
                data_paths['processed_dir'],
                target_name
            )
            setup_result['chunks_created'] = len(chunks)
            setup_result['steps_completed'].append('process_docs')
            print(f"✅ Created {len(chunks)} chunks from {len(processed_docs)} documents")
        else:
            print("Step 2: Loading existing processed documents and chunks...")
            processed_docs, chunks = load_processed_documents(target_name, data_paths['processed_dir'])
            setup_result['chunks_created'] = len(chunks)
            print(f"✅ Loaded {len(chunks)} chunks from cache")

        # Step 2.5: Hierarchical preprocessing (document map, summaries, overview)
        doc_map_file = Path(data_paths['processed_dir']) / f"{target_name}_doc_map.json"

        if force_recrawl or not doc_map_file.exists():
            print("Step 2.5: Building hierarchical document structure...")
            hierarchical_processor = HierarchicalDocumentProcessor(target_name, data_paths)
            saved_paths = hierarchical_processor.process_documents(documents)
            setup_result['hierarchical_artifacts'] = {
                'doc_map': str(saved_paths.get('doc_map')),
                'summaries': str(saved_paths.get('summaries')),
                'overview': str(saved_paths.get('overview')),
                'lookup': str(saved_paths.get('lookup'))
            }
            setup_result['steps_completed'].append('hierarchical_processing')
            print("✅ Hierarchical preprocessing completed")
        else:
            print("Step 2.5: Hierarchical preprocessing already completed...")
            setup_result['hierarchical_artifacts'] = {
                'doc_map': str(doc_map_file),
                'cached': True
            }

        # Step 3: Generate embeddings
        embeddings_index_file = Path(data_paths['embeddings_dir']) / f"{target_name}_embedding_index.json"

        if force_recrawl or not embeddings_index_file.exists():
            print("Step 3: Generating embeddings...")
            embedded_chunks = create_embeddings_for_target(chunks, target_name, config)
            setup_result['embeddings_created'] = len(embedded_chunks)
            setup_result['steps_completed'].append('create_embeddings')
            print(f"✅ Generated embeddings for {len(embedded_chunks)} chunks")
        else:
            print("Step 3: Embeddings already exist...")
            embedded_chunks = chunks  # Assume embeddings are already attached
            setup_result['embeddings_created'] = len(chunks)

        # Step 4: Create vector store
        print("Step 4: Setting up vector store...")
        try:
            client, collection = create_vector_store_for_target(
                embedded_chunks,
                target_name,
                data_paths['embeddings_dir']
            )
            setup_result['steps_completed'].append('create_vector_store')
            print("✅ Vector store created successfully")
        except Exception as e:
            print(f"⚠️ Vector store setup had issues: {e}")

        # Step 5: Validate setup
        print("Step 5: Validating setup...")
        validation = check_target_setup(target_name)
        if validation['is_ready']:
            print("✅ Setup validation passed")
            setup_result['steps_completed'].append('validation_passed')
        else:
            print("⚠️ Setup validation found issues:")
            for component in validation['missing_components']:
                print(f"  - Missing: {component}")

        setup_result['validation_result'] = validation
        print(f"\n🎉 Setup pipeline completed for {target_name}")
        print(f"   Steps completed: {len(setup_result['steps_completed'])}")

        return setup_result

    except Exception as e:
        print(f"❌ Setup pipeline failed: {e}")
        raise


def setup_target_pipeline_sync(
    target_name: str,
    crawl_docs: bool = True,
    force_recrawl: bool = False,
    max_concurrent: int = 10
) -> Dict[str, Any]:
    """Synchronous wrapper for setup pipeline."""
    return setup_target_pipeline_impl(
        target_name,
        crawl_docs,
        force_recrawl,
        max_concurrent
    )


def get_setup_status_report(target_name: str) -> Dict[str, Any]:
    """Get detailed setup status report for a target."""
    try:
        setup_status = check_target_setup(target_name)
        config = get_merged_config(target_name)
        data_paths = get_data_paths(config)

        report = {
            'target': target_name,
            'overall_status': 'ready' if setup_status['is_ready'] else 'incomplete',
            'components': setup_status['components'],
            'file_details': {}
        }

        # Check file sizes and details
        files_to_check = [
            ('raw_docs', Path(data_paths['raw_dir']) / f"{target_name}_docs.json"),
            ('processed_docs', Path(data_paths['processed_dir']) / f"{target_name}_processed_docs.json"),
            ('chunks', Path(data_paths['processed_dir']) / f"{target_name}_chunks.json"),
            ('embeddings', Path(data_paths['embeddings_dir']) / f"{target_name}_embedding_index.json")
        ]

        for component, file_path in files_to_check:
            if file_path.exists():
                file_size = file_path.stat().st_size
                report['file_details'][component] = {
                    'exists': True,
                    'size_mb': round(file_size / 1024 / 1024, 2),
                    'path': str(file_path)
                }

                # Load and check content for some files
                if component == 'raw_docs':
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            docs = json.load(f)
                        report['file_details'][component]['document_count'] = len(docs)
                    except:
                        report['file_details'][component]['document_count'] = 'unknown'

                elif component == 'chunks':
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            chunks = json.load(f)
                        report['file_details'][component]['chunk_count'] = len(chunks)
                    except:
                        report['file_details'][component]['chunk_count'] = 'unknown'

                elif component == 'embeddings':
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            index_data = json.load(f)
                        report['file_details'][component]['embedding_count'] = len(index_data.get('chunks', []))
                        report['file_details'][component]['model'] = index_data.get('model_name', 'unknown')
                    except:
                        report['file_details'][component]['embedding_count'] = 'unknown'

            else:
                report['file_details'][component] = {
                    'exists': False,
                    'path': str(file_path)
                }

        return report

    except Exception as e:
        return {
            'target': target_name,
            'overall_status': 'error',
            'error': str(e),
            'components': {},
            'file_details': {}
        }


def cleanup_target_data(target_name: str, confirm: bool = False) -> Dict[str, Any]:
    """Clean up all data for a target (for reset/reinstall)."""
    if not confirm:
        raise ValueError("Cleanup requires explicit confirmation (set confirm=True)")

    try:
        config = get_merged_config(target_name)
        data_paths = get_data_paths(config)

        cleanup_result = {
            'target': target_name,
            'files_removed': [],
            'directories_cleaned': []
        }

        # Files to remove
        files_to_remove = [
            Path(data_paths['raw_dir']) / f"{target_name}_docs.json",
            Path(data_paths['processed_dir']) / f"{target_name}_processed_docs.json",
            Path(data_paths['processed_dir']) / f"{target_name}_chunks.json",
            Path(data_paths['processed_dir']) / f"{target_name}_conversation_history.json",
            Path(data_paths['embeddings_dir']) / f"{target_name}_embedding_index.json",
            Path(data_paths['embeddings_dir']) / f"{target_name}_embedding_cache.pkl"
        ]

        for file_path in files_to_remove:
            if file_path.exists():
                file_path.unlink()
                cleanup_result['files_removed'].append(str(file_path))

        # Clean up vector store directories (ChromaDB)
        embeddings_dir = Path(data_paths['embeddings_dir'])
        for item in embeddings_dir.glob(f"*{target_name}*"):
            if item.is_dir():
                import shutil
                shutil.rmtree(item)
                cleanup_result['directories_cleaned'].append(str(item))

        print(f"✅ Cleaned up data for {target_name}")
        print(f"   Files removed: {len(cleanup_result['files_removed'])}")
        print(f"   Directories cleaned: {len(cleanup_result['directories_cleaned'])}")

        return cleanup_result

    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        raise


def repair_target_setup(target_name: str) -> Dict[str, Any]:
    """Attempt to repair a target setup by identifying and fixing issues."""
    print(f"Attempting to repair setup for {target_name}...")

    try:
        # Check current status
        status = check_target_setup(target_name)
        missing = status['missing_components']

        repair_result = {
            'target': target_name,
            'repairs_attempted': [],
            'repairs_successful': [],
            'repairs_failed': []
        }

        if 'raw_docs' in missing:
            # Need to crawl docs
            repair_result['repairs_attempted'].append('crawl_documentation')
            try:
                crawl_target_documentation_scrapy(target_name)
                repair_result['repairs_successful'].append('crawl_documentation')
            except Exception as e:
                repair_result['repairs_failed'].append(f'crawl_documentation: {e}')

        if 'processed_docs' in missing or 'chunks' in missing:
            # Need to process docs
            repair_result['repairs_attempted'].append('process_documents')
            try:
                config = get_merged_config(target_name)
                data_paths = get_data_paths(config)

                # Load raw docs
                raw_docs_file = Path(data_paths['raw_dir']) / f"{target_name}_docs.json"
                with open(raw_docs_file, 'r', encoding='utf-8') as f:
                    documents = json.load(f)

                # Process
                embedding_config = get_embedding_config(config)
                process_documents_pipeline(
                    documents,
                    embedding_config,
                    data_paths['processed_dir'],
                    target_name
                )
                repair_result['repairs_successful'].append('process_documents')
            except Exception as e:
                repair_result['repairs_failed'].append(f'process_documents: {e}')

        if 'embeddings' in missing or 'vector_store' in missing:
            # Need to create embeddings and vector store
            repair_result['repairs_attempted'].append('create_embeddings_and_vector_store')
            try:
                config = get_merged_config(target_name)
                data_paths = get_data_paths(config)
                config['data_paths'] = data_paths

                # Load chunks
                chunks = load_chunks_from_file(
                    str(Path(data_paths['processed_dir']) / f"{target_name}_chunks.json")
                )

                # Create embeddings and vector store
                embedded_chunks = create_embeddings_for_target(chunks, target_name, config)
                create_vector_store_for_target(
                    embedded_chunks,
                    target_name,
                    data_paths['embeddings_dir']
                )
                repair_result['repairs_successful'].append('create_embeddings_and_vector_store')
            except Exception as e:
                repair_result['repairs_failed'].append(f'create_embeddings_and_vector_store: {e}')

        # Check final status
        final_status = check_target_setup(target_name)
        repair_result['final_status'] = final_status

        success_rate = len(repair_result['repairs_successful']) / len(repair_result['repairs_attempted']) if repair_result['repairs_attempted'] else 1.0

        if success_rate == 1.0 and final_status['is_ready']:
            print(f"✅ Repair completed successfully for {target_name}")
        else:
            print(f"⚠️ Repair partially successful for {target_name} ({int(success_rate * 100)}%)")

        return repair_result

    except Exception as e:
        print(f"❌ Repair failed: {e}")
        raise