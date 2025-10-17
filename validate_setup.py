#!/usr/bin/env python3
"""
Simple validation script to check project structure and basic functionality.
"""

import os
import sys
from pathlib import Path
import yaml
import json

def check_project_structure():
    """Check that all required directories and files exist."""
    print("🔍 Checking project structure...")

    required_dirs = [
        "config/targets",
        "src/agents",
        "src/crawlers",
        "src/processing",
        "src/embeddings",
        "src/retrieval",
        "src/orchestration",
        "src/utils",
        "data/raw",
        "data/processed",
        "data/embeddings",
        "tests"
    ]

    required_files = [
        "requirements.txt",
        "README.md",
        "config/base_config.yaml",
        "config/targets/cuda_q.yaml",
        "src/main.py",
        "src/config_loader.py",
        "src/setup_pipeline.py"
    ]

    missing_dirs = []
    missing_files = []

    for directory in required_dirs:
        if not Path(directory).exists():
            missing_dirs.append(directory)

    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)

    if missing_dirs:
        print(f"❌ Missing directories: {missing_dirs}")
        return False

    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False

    print("✅ Project structure looks good!")
    return True

def check_configuration():
    """Check that configuration files are valid YAML."""
    print("🔧 Checking configuration files...")

    config_files = [
        "config/base_config.yaml",
        "config/targets/cuda_q.yaml"
    ]

    for config_file in config_files:
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
            print(f"  ✅ {config_file}")
        except Exception as e:
            print(f"  ❌ {config_file}: {e}")
            return False

    return True

def check_cuda_q_config():
    """Check specific CUDA-Q configuration."""
    print("⚛️ Checking CUDA-Q target configuration...")

    try:
        with open("config/targets/cuda_q.yaml", 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Check required sections
        required_sections = ['target', 'documentation', 'agents']
        for section in required_sections:
            if section not in config:
                print(f"  ❌ Missing section: {section}")
                return False

        # Check target info
        target = config['target']
        if target.get('name') != 'CUDA-Q':
            print(f"  ❌ Expected target name 'CUDA-Q', got '{target.get('name')}'")
            return False

        # Check documentation URL
        doc_config = config['documentation']
        base_url = doc_config.get('base_url')
        if not base_url or not base_url.startswith('http'):
            print(f"  ❌ Invalid base_url: {base_url}")
            return False

        # Check agents
        agents = config['agents']
        required_agents = ['query_agent', 'code_agent', 'validation_agent']
        for agent in required_agents:
            if agent not in agents:
                print(f"  ❌ Missing agent: {agent}")
                return False

        print("  ✅ CUDA-Q configuration is valid")
        return True

    except Exception as e:
        print(f"  ❌ Error checking CUDA-Q config: {e}")
        return False

def check_python_syntax():
    """Check Python syntax of main modules."""
    print("🐍 Checking Python syntax...")

    python_files = [
        "src/main.py",
        "src/config_loader.py",
        "src/setup_pipeline.py",
        "src/agents/query_agent.py",
        "src/agents/code_agent.py",
        "src/agents/validation_agent.py",
        "src/orchestration/crew_flow.py"
    ]

    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                compile(f.read(), file_path, 'exec')
            print(f"  ✅ {file_path}")
        except SyntaxError as e:
            print(f"  ❌ {file_path}: Syntax error at line {e.lineno}: {e.msg}")
            return False
        except Exception as e:
            print(f"  ❌ {file_path}: {e}")
            return False

    return True

def check_imports():
    """Check basic import functionality."""
    print("📦 Checking basic imports...")

    # Save current working directory
    original_cwd = os.getcwd()

    try:
        # Change to project root
        os.chdir(Path(__file__).parent)

        # Add src to path
        sys.path.insert(0, str(Path("src")))

        # Test basic imports
        try:
            import config_loader
            print("  ✅ config_loader")
        except Exception as e:
            print(f"  ❌ config_loader: {e}")
            return False

        try:
            from config_loader import load_target_config
            config = load_target_config('cuda_q')
            print("  ✅ CUDA-Q config loading")
        except Exception as e:
            print(f"  ❌ CUDA-Q config loading: {e}")
            return False

        return True

    finally:
        # Restore working directory
        os.chdir(original_cwd)

def main():
    """Run all validation checks."""
    print("🧪 Validating AI Documentation Assistant Setup")
    print("=" * 50)

    checks = [
        check_project_structure,
        check_configuration,
        check_cuda_q_config,
        check_python_syntax,
        check_imports
    ]

    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"❌ {check.__name__}: FAILED - {e}")
            results.append(False)
        print()

    # Summary
    passed = sum(results)
    total = len(results)

    print("=" * 50)
    print(f"Validation Results: {passed}/{total} checks passed")

    if passed == total:
        print("🎉 All validation checks passed!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Setup CUDA-Q: python src/main.py setup --target cuda_q")
        print("3. Start chatting: python src/main.py chat --target cuda_q")
        return True
    else:
        print(f"❌ {total - passed} validation checks failed")
        print("Please fix the issues above before proceeding.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)