from crewai import Agent, Task
from crewai.tools import tool
from typing import Dict, Any, List, Optional
import re

# Global config for tool access
_target_config = None

def set_target_config(config: Dict[str, Any]):
    """Set the global target config for tool access."""
    global _target_config
    _target_config = config

@tool("code_generation")
def code_generation_tool(requirements: str, context: str = "", language: str = "python") -> str:
    """Generate code based on documentation context and user requirements. Specializes in creating working code examples with proper syntax and structure."""
    try:
        # Handle case where LLM passes dict instead of string
        if isinstance(requirements, dict):
            requirements = requirements.get('description', '') or str(requirements)
        if isinstance(context, dict):
            context = context.get('description', '') or str(context)
        if isinstance(language, dict):
            language = language.get('value', 'python')

        # Ensure all inputs are strings
        requirements = str(requirements)
        context = str(context)
        language = str(language)

        if _target_config is None:
            return "Error: Target configuration not initialized"

        # This would integrate with an LLM for actual code generation
        # For now, return structured template
        target_name = _target_config.get('target', {}).get('name', 'Unknown')

        template = f"""
# Generated {target_name} Code
# Requirements: {requirements}

# Based on documentation context:
# {context[:200]}...

# Code implementation would be generated here
# This is a placeholder for LLM-generated code

def example_function():
    '''
    Generated function based on requirements: {requirements}
    '''
    pass
"""
        return template

    except Exception as e:
        return f"Error generating code: {str(e)}"


def create_code_generation_agent(config: Dict[str, Any]) -> Agent:
    """Create the code generation agent."""
    agent_config = config.get('agents', {}).get('code_agent', {})

    # Set the config for tool access
    set_target_config(config)

    agent = Agent(
        role=agent_config.get('role', 'Code Generator'),
        goal=agent_config.get('goal', 'Generate working code examples'),
        backstory=agent_config.get('backstory', 'Expert software developer'),
        tools=[code_generation_tool],
        verbose=True,
        memory=True,
        allow_delegation=False
    )

    return agent


def create_code_generation_task(
    query: str,
    documentation_context: str,
    agent: Agent,
    config: Dict[str, Any]
) -> Task:
    """Create task for code generation."""
    target_info = config.get('target', {})
    target_name = target_info.get('name', 'Target Framework')

    # Extract code generation prompt template
    prompt_template = config.get('prompt_templates', {}).get('code_generation', '')

    if prompt_template:
        task_description = prompt_template.format(
            context=documentation_context,
            query=query
        )
    else:
        task_description = f"""
        Generate working {target_name} code based on the user's request and documentation context.

        User Request: "{query}"

        Documentation Context:
        {documentation_context}

        Your responsibilities:
        1. Analyze the user's requirements and the provided documentation
        2. Generate clean, working code that addresses the request
        3. Include necessary imports and setup code
        4. Add clear comments explaining key concepts
        5. Follow best practices and coding conventions
        6. Ensure the code is syntactically correct and executable
        7. Include example usage if applicable

        Generate code that is:
        - Functional and ready to run
        - Well-documented with comments
        - Following framework conventions
        - Including error handling where appropriate
        """

    task = Task(
        description=task_description,
        expected_output=(
            "Complete, working code that:\n"
            "- Addresses the user's specific request\n"
            "- Includes necessary imports and setup\n"
            "- Contains clear, explanatory comments\n"
            "- Follows best practices and conventions\n"
            "- Is syntactically correct and executable\n"
            "- Includes example usage if applicable"
        ),
        agent=agent
    )

    return task


# Atomic functions for code generation

def extract_code_requirements(query: str) -> Dict[str, Any]:
    """Extract code requirements from user query."""
    requirements = {
        'primary_action': '',
        'components': [],
        'constraints': [],
        'language_hints': [],
        'complexity_level': 'intermediate',
        'examples_requested': False
    }

    query_lower = query.lower()

    # Extract primary action
    action_patterns = {
        'create': r'\b(create|build|make|generate|implement)\b',
        'modify': r'\b(modify|change|update|alter|edit)\b',
        'fix': r'\b(fix|debug|correct|resolve)\b',
        'optimize': r'\b(optimize|improve|enhance|speed up)\b',
        'explain': r'\b(explain|show|demonstrate)\b'
    }

    for action, pattern in action_patterns.items():
        if re.search(pattern, query_lower):
            requirements['primary_action'] = action
            break

    if not requirements['primary_action']:
        requirements['primary_action'] = 'create'  # Default

    # Extract components/objects to work with
    component_patterns = [
        r'\b(function|method|class|module|script)\s+(\w+)',
        r'\b(\w+)\s+(function|method|class)',
        r'\bfor\s+(\w+)',
        r'\bwith\s+(\w+)'
    ]

    for pattern in component_patterns:
        matches = re.findall(pattern, query_lower)
        for match in matches:
            if isinstance(match, tuple):
                requirements['components'].extend([m for m in match if len(m) > 2])
            else:
                requirements['components'].append(match)

    # Extract constraints and requirements
    constraint_patterns = {
        'performance': r'\b(fast|quick|efficient|optimized|performance)\b',
        'simple': r'\b(simple|basic|easy|straightforward)\b',
        'complex': r'\b(advanced|complex|sophisticated|detailed)\b',
        'secure': r'\b(secure|safe|protected)\b',
        'error_handling': r'\b(error|exception|handling|robust)\b'
    }

    for constraint, pattern in constraint_patterns.items():
        if re.search(pattern, query_lower):
            requirements['constraints'].append(constraint)

    # Detect if examples are requested
    example_patterns = [
        r'\bexample', r'\bsample', r'\bdemo', r'\bshow me',
        r'\bhow to use', r'\busage'
    ]

    requirements['examples_requested'] = any(
        re.search(pattern, query_lower) for pattern in example_patterns
    )

    # Estimate complexity
    if 'simple' in requirements['constraints']:
        requirements['complexity_level'] = 'beginner'
    elif 'complex' in requirements['constraints'] or 'advanced' in query_lower:
        requirements['complexity_level'] = 'advanced'

    return requirements


def identify_programming_language(query: str, context: str = "") -> str:
    """Identify the programming language for code generation."""
    combined_text = (query + " " + context).lower()

    # Language indicators in order of priority
    language_patterns = {
        'python': [r'\bpython\b', r'\.py\b', r'\bpip\b', r'\bdef\b', r'\bimport\b'],
        'javascript': [r'\bjavascript\b', r'\bjs\b', r'\.js\b', r'\bnode\b', r'\bnpm\b'],
        'cpp': [r'\bc\+\+\b', r'\.cpp\b', r'\.h\b', r'\bstd::\b', r'#include'],
        'java': [r'\bjava\b', r'\.java\b', r'\bclass\b.*\bpublic\b'],
        'cuda': [r'\bcuda\b', r'\.cu\b', r'__global__', r'__device__'],
        'cuda-q': [r'\bcuda-q\b', r'\bcudaq\b', r'quantum', r'qubit']
    }

    for language, patterns in language_patterns.items():
        if any(re.search(pattern, combined_text) for pattern in patterns):
            return language

    return 'python'  # Default fallback


def validate_code_syntax(code: str, language: str = 'python') -> Dict[str, Any]:
    """Basic syntax validation for generated code."""
    validation = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'suggestions': []
    }

    if language == 'python':
        # Basic Python syntax checks
        try:
            import ast
            ast.parse(code)
        except SyntaxError as e:
            validation['is_valid'] = False
            validation['errors'].append(f"Syntax error: {str(e)}")
        except Exception as e:
            validation['warnings'].append(f"Parse warning: {str(e)}")

        # Check for common issues
        if 'def ' in code and 'return' not in code:
            validation['warnings'].append('Function might be missing return statement')

        if 'import' not in code and any(lib in code for lib in ['numpy', 'pandas', 'matplotlib']):
            validation['suggestions'].append('Consider adding necessary imports')

    # General checks for all languages
    lines = code.split('\n')
    if len(lines) < 3:
        validation['warnings'].append('Code seems very short')

    if not any(line.strip().startswith('#') or line.strip().startswith('//') for line in lines):
        validation['suggestions'].append('Consider adding comments for clarity')

    return validation


def extract_code_from_text(text: str) -> List[Dict[str, str]]:
    """Extract code blocks from text."""
    code_blocks = []

    # Find markdown code blocks
    import re
    code_pattern = r'```(\w+)?\n(.*?)\n```'
    matches = re.findall(code_pattern, text, re.DOTALL)

    for i, (language, code) in enumerate(matches):
        code_blocks.append({
            'type': 'code_block',
            'language': language or 'unknown',
            'code': code.strip(),
            'index': i
        })

    # Find inline code (longer snippets)
    inline_pattern = r'`([^`\n]+)`'
    inline_matches = re.findall(inline_pattern, text)

    for i, code in enumerate(inline_matches):
        if len(code) > 20:  # Only substantial inline code
            code_blocks.append({
                'type': 'inline_code',
                'language': 'unknown',
                'code': code.strip(),
                'index': len(code_blocks)
            })

    return code_blocks


def enhance_code_with_comments(code: str, context: str = "", language: str = 'python') -> str:
    """Add helpful comments to code based on context."""
    if not code.strip():
        return code

    lines = code.split('\n')
    enhanced_lines = []

    comment_prefix = '#' if language in ['python', 'bash'] else '//'

    # Add header comment
    enhanced_lines.append(f"{comment_prefix} Generated code based on documentation context")
    enhanced_lines.append(f"{comment_prefix} Context: {context[:100]}..." if context else "")
    enhanced_lines.append("")

    in_function = False
    for line in lines:
        stripped = line.strip()

        # Add function documentation
        if language == 'python' and stripped.startswith('def '):
            in_function = True
            enhanced_lines.append(line)
            # Add docstring placeholder if not present
            if not any('"""' in l or "'''" in l for l in lines):
                indent = len(line) - len(line.lstrip())
                enhanced_lines.append(' ' * (indent + 4) + '"""')
                enhanced_lines.append(' ' * (indent + 4) + 'Generated function - add description here')
                enhanced_lines.append(' ' * (indent + 4) + '"""')
        else:
            enhanced_lines.append(line)

    return '\n'.join(enhanced_lines)


def generate_usage_example(code: str, language: str = 'python') -> str:
    """Generate a usage example for the provided code."""
    if not code.strip():
        return ""

    # Extract function/class names
    import re

    if language == 'python':
        # Find function definitions
        func_matches = re.findall(r'def\s+(\w+)\s*\(([^)]*)\)', code)
        class_matches = re.findall(r'class\s+(\w+)', code)

        example_lines = ["# Usage Example:", ""]

        for func_name, params in func_matches:
            if params.strip():
                # Simple parameter example
                param_list = [p.split(':')[0].strip() for p in params.split(',')]
                param_examples = []
                for param in param_list:
                    if 'self' not in param:
                        param_examples.append(f"{param}=None")  # Placeholder

                example_lines.append(f"# Call {func_name}")
                if param_examples:
                    example_lines.append(f"result = {func_name}({', '.join(param_examples)})")
                else:
                    example_lines.append(f"result = {func_name}()")
            else:
                example_lines.append(f"result = {func_name}()")

        for class_name in class_matches:
            example_lines.append(f"# Create instance of {class_name}")
            example_lines.append(f"instance = {class_name}()")

        return '\n'.join(example_lines)

    return "# Add usage example here"


def assess_code_quality(code: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
    """Assess the quality of generated code."""
    assessment = {
        'overall_score': 0.5,
        'strengths': [],
        'weaknesses': [],
        'suggestions': [],
        'completeness': 0.5
    }

    if not code or not code.strip():
        assessment['overall_score'] = 0.0
        assessment['weaknesses'].append('No code generated')
        return assessment

    lines = [l for l in code.split('\n') if l.strip()]

    # Check for basic quality indicators
    has_comments = any('#' in line or '//' in line for line in lines)
    has_functions = any('def ' in line or 'function ' in line for line in lines)
    has_error_handling = any('try' in line or 'except' in line or 'catch' in line for line in lines)

    if has_comments:
        assessment['strengths'].append('Well-commented code')
    else:
        assessment['suggestions'].append('Add more comments for clarity')

    if has_functions:
        assessment['strengths'].append('Modular structure with functions')

    if has_error_handling:
        assessment['strengths'].append('Includes error handling')
    else:
        if requirements.get('constraints') and 'error_handling' in requirements['constraints']:
            assessment['weaknesses'].append('Missing requested error handling')

    # Check completeness based on requirements
    primary_action = requirements.get('primary_action', '')
    if primary_action == 'create' and len(lines) > 5:
        assessment['completeness'] = 0.8
    elif primary_action == 'explain' and has_comments:
        assessment['completeness'] = 0.9

    # Calculate overall score
    score = 0.5  # Base score
    score += len(assessment['strengths']) * 0.1
    score -= len(assessment['weaknesses']) * 0.15
    score = max(0.0, min(1.0, score))

    assessment['overall_score'] = score

    return assessment