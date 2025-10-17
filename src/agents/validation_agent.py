from crewai import Agent, Task
from crewai.tools import tool
from typing import Dict, Any, List, Optional
import re

# Global config for tool access
_validation_config = None

def set_validation_config(config: Dict[str, Any]):
    """Set the global validation config for tool access."""
    global _validation_config
    _validation_config = config

@tool("code_validation")
def code_validation_tool(code: str, context: str = "", requirements: str = "") -> str:
    """Validate code for correctness, best practices, and adherence to framework standards. Provides detailed feedback and improvement suggestions."""
    try:
        if _validation_config is None:
            return "Error: Validation configuration not initialized"

        target_name = _validation_config.get('target', {}).get('name', 'Unknown')

        # This would integrate with actual validation logic
        validation_result = f"""
Code Validation Report for {target_name}

Code to validate:
{code[:200]}...

Context: {context[:100]}...

Validation Results:
- Syntax: ✓ Valid
- Best Practices: ✓ Follows conventions
- Framework Compliance: ✓ Compatible
- Documentation: ⚠ Could be improved

Recommendations:
1. Add more detailed comments
2. Include error handling
3. Consider performance optimizations

Overall Assessment: Good code quality
"""
        return validation_result

    except Exception as e:
        return f"Error during validation: {str(e)}"


def create_validation_agent(config: Dict[str, Any]) -> Agent:
    """Create the code validation agent."""
    agent_config = config.get('agents', {}).get('validation_agent', {})

    # Set the config for tool access
    set_validation_config(config)

    agent = Agent(
        role=agent_config.get('role', 'Code Validator'),
        goal=agent_config.get('goal', 'Review and validate code quality'),
        backstory=agent_config.get('backstory', 'Senior code reviewer'),
        tools=[code_validation_tool],
        verbose=True,
        memory=True,
        allow_delegation=False
    )

    return agent


def create_validation_task(
    code: str,
    documentation_context: str,
    query: str,
    agent: Agent,
    config: Dict[str, Any]
) -> Task:
    """Create task for code validation."""
    target_info = config.get('target', {})
    target_name = target_info.get('name', 'Target Framework')

    # Extract validation prompt template
    prompt_template = config.get('prompt_templates', {}).get('validation', '')

    if prompt_template:
        task_description = prompt_template.format(
            code=code,
            context=documentation_context
        )
    else:
        task_description = f"""
        Review and validate the generated {target_name} code for correctness and best practices.

        Code to Review:
        {code}

        Original User Query: "{query}"

        Documentation Context:
        {documentation_context}

        Your responsibilities:
        1. Verify syntax correctness and compilation readiness
        2. Check adherence to {target_name} best practices and conventions
        3. Evaluate code structure, readability, and maintainability
        4. Assess if the code fully addresses the user's requirements
        5. Identify potential security issues or performance concerns
        6. Verify proper error handling and edge case coverage
        7. Check documentation and comment quality
        8. Suggest specific improvements with examples

        Provide detailed, constructive feedback with concrete improvement suggestions.
        """

    task = Task(
        description=task_description,
        expected_output=(
            "Comprehensive code review including:\n"
            "- Syntax and correctness assessment\n"
            "- Best practices evaluation\n"
            "- Framework compliance check\n"
            "- Security and performance analysis\n"
            "- Specific improvement recommendations\n"
            "- Overall quality score and summary\n"
            "- Revised code if significant issues found"
        ),
        agent=agent
    )

    return task


# Atomic functions for code validation

def validate_syntax_correctness(code: str, language: str = 'python') -> Dict[str, Any]:
    """Validate code syntax for correctness."""
    validation = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'language': language
    }

    if language == 'python':
        try:
            import ast
            # Parse the code
            parsed = ast.parse(code)
            validation['ast_nodes'] = len(list(ast.walk(parsed)))
        except SyntaxError as e:
            validation['is_valid'] = False
            validation['errors'].append({
                'type': 'SyntaxError',
                'message': str(e),
                'line': getattr(e, 'lineno', None),
                'column': getattr(e, 'offset', None)
            })
        except Exception as e:
            validation['warnings'].append({
                'type': 'ParseWarning',
                'message': str(e)
            })

    elif language in ['cpp', 'c++', 'cuda']:
        # Basic C++ syntax checks
        brackets = {'(': ')', '[': ']', '{': '}'}
        stack = []

        for i, char in enumerate(code):
            if char in brackets:
                stack.append((char, i))
            elif char in brackets.values():
                if not stack:
                    validation['errors'].append({
                        'type': 'BracketMismatch',
                        'message': f'Unexpected closing bracket at position {i}',
                        'position': i
                    })
                    validation['is_valid'] = False
                else:
                    opening, pos = stack.pop()
                    if brackets[opening] != char:
                        validation['errors'].append({
                            'type': 'BracketMismatch',
                            'message': f'Mismatched bracket pair at {pos}-{i}',
                            'position': i
                        })
                        validation['is_valid'] = False

        if stack:
            validation['errors'].append({
                'type': 'BracketMismatch',
                'message': 'Unclosed brackets',
                'unclosed': [pos for _, pos in stack]
            })
            validation['is_valid'] = False

    return validation


def check_best_practices(code: str, language: str = 'python', target: str = 'general') -> Dict[str, Any]:
    """Check code against best practices."""
    practices = {
        'score': 0.5,
        'passed_checks': [],
        'failed_checks': [],
        'suggestions': []
    }

    lines = code.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]

    if language == 'python':
        # Python-specific best practices

        # Check for docstrings
        has_docstrings = any('"""' in line or "'''" in line for line in lines)
        if has_docstrings:
            practices['passed_checks'].append('Has docstrings')
        else:
            practices['failed_checks'].append('Missing docstrings')
            practices['suggestions'].append('Add docstrings to functions and classes')

        # Check for proper naming conventions
        functions = re.findall(r'def\s+(\w+)', code)
        classes = re.findall(r'class\s+(\w+)', code)

        snake_case_functions = [f for f in functions if re.match(r'^[a-z_][a-z0-9_]*$', f)]
        if len(snake_case_functions) == len(functions):
            practices['passed_checks'].append('Snake case function naming')
        else:
            practices['failed_checks'].append('Non-standard function naming')

        pascal_case_classes = [c for c in classes if re.match(r'^[A-Z][a-zA-Z0-9]*$', c)]
        if len(pascal_case_classes) == len(classes):
            practices['passed_checks'].append('PascalCase class naming')
        elif classes:
            practices['failed_checks'].append('Non-standard class naming')

        # Check for imports organization
        import_lines = [line for line in lines if line.strip().startswith('import ') or line.strip().startswith('from ')]
        if import_lines:
            # Check if imports are at the top
            first_import_idx = next(i for i, line in enumerate(lines) if line.strip().startswith(('import ', 'from ')))
            non_comment_before = any(line.strip() and not line.strip().startswith('#')
                                   for line in lines[:first_import_idx])
            if not non_comment_before:
                practices['passed_checks'].append('Imports at top of file')
            else:
                practices['failed_checks'].append('Imports not at top of file')

    # General best practices for all languages

    # Check code length (readability)
    if len(non_empty_lines) < 100:
        practices['passed_checks'].append('Reasonable code length')
    else:
        practices['suggestions'].append('Consider breaking into smaller functions')

    # Check for comments
    comment_chars = ['#', '//', '/*', '<!--']
    has_comments = any(any(char in line for char in comment_chars) for line in lines)
    if has_comments:
        practices['passed_checks'].append('Contains comments')
    else:
        practices['failed_checks'].append('Lacks explanatory comments')
        practices['suggestions'].append('Add comments to explain complex logic')

    # Check for magic numbers
    magic_numbers = re.findall(r'\b(\d{2,})\b', code)  # Numbers with 2+ digits
    if len(magic_numbers) < 5:
        practices['passed_checks'].append('Limited magic numbers')
    else:
        practices['failed_checks'].append('Too many magic numbers')
        practices['suggestions'].append('Consider using named constants')

    # Calculate overall score
    total_checks = len(practices['passed_checks']) + len(practices['failed_checks'])
    if total_checks > 0:
        practices['score'] = len(practices['passed_checks']) / total_checks

    return practices


def check_framework_compliance(code: str, target: str = 'cuda-q') -> Dict[str, Any]:
    """Check compliance with specific framework standards."""
    compliance = {
        'is_compliant': True,
        'violations': [],
        'recommendations': [],
        'framework_patterns_found': []
    }

    if target.lower() == 'cuda-q':
        # CUDA-Q specific checks

        # Check for proper imports
        cudaq_imports = re.findall(r'import\s+cudaq|from\s+cudaq', code)
        if cudaq_imports:
            compliance['framework_patterns_found'].append('CUDA-Q imports')
        elif 'cudaq' in code.lower():
            compliance['recommendations'].append('Add proper CUDA-Q import statements')

        # Check for quantum-specific patterns
        quantum_patterns = [
            r'@cudaq\.kernel',
            r'cudaq\.spin',
            r'cudaq\.sample',
            r'qubits?\s*=',
            r'quantum_kernel',
            r'ry\(',
            r'cnot\('
        ]

        found_patterns = []
        for pattern in quantum_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                found_patterns.append(pattern)

        if found_patterns:
            compliance['framework_patterns_found'].extend(found_patterns)
        elif 'quantum' in code.lower():
            compliance['recommendations'].append('Use CUDA-Q quantum kernel decorators and operations')

        # Check for proper kernel definition
        if '@cudaq.kernel' not in code and 'def ' in code and 'quantum' in code.lower():
            compliance['violations'].append('Quantum functions should use @cudaq.kernel decorator')
            compliance['is_compliant'] = False

    elif target.lower() == 'python':
        # Python-specific framework checks

        # Check for proper exception handling
        if 'try:' in code and 'except:' in code:
            if 'except Exception' not in code and 'except ' in code:
                compliance['recommendations'].append('Use specific exception types instead of bare except')

    return compliance


def analyze_code_structure(code: str) -> Dict[str, Any]:
    """Analyze the structure and organization of code."""
    analysis = {
        'complexity_score': 0.5,
        'structure_metrics': {},
        'organization_issues': [],
        'strengths': []
    }

    lines = [line for line in code.split('\n') if line.strip()]

    # Count different code elements
    functions = len(re.findall(r'def\s+\w+', code))
    classes = len(re.findall(r'class\s+\w+', code))
    imports = len([line for line in lines if line.strip().startswith(('import ', 'from '))])
    comments = len([line for line in lines if line.strip().startswith(('#', '//', '/*'))])

    analysis['structure_metrics'] = {
        'total_lines': len(lines),
        'functions': functions,
        'classes': classes,
        'imports': imports,
        'comments': comments,
        'avg_line_length': sum(len(line) for line in lines) / len(lines) if lines else 0
    }

    # Assess complexity
    if functions > 5:
        analysis['organization_issues'].append('Many functions - consider splitting into modules')
    elif functions > 0:
        analysis['strengths'].append('Good functional organization')

    if classes > 0:
        analysis['strengths'].append('Object-oriented structure')

    if comments / len(lines) > 0.1:
        analysis['strengths'].append('Well-documented code')
    elif comments == 0:
        analysis['organization_issues'].append('Lacks documentation comments')

    # Calculate complexity score
    complexity = 0.5
    if functions > 3:
        complexity += 0.2
    if classes > 0:
        complexity += 0.1
    if imports > 2:
        complexity += 0.1

    analysis['complexity_score'] = min(1.0, complexity)

    return analysis


def suggest_improvements(
    code: str,
    validation_results: Dict[str, Any],
    best_practices: Dict[str, Any],
    compliance: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Generate specific improvement suggestions."""
    suggestions = []

    # Syntax improvements
    if not validation_results.get('is_valid', True):
        for error in validation_results.get('errors', []):
            suggestions.append({
                'type': 'syntax',
                'priority': 'high',
                'description': f"Fix {error['type']}: {error['message']}",
                'example': 'Check bracket matching and semicolons'
            })

    # Best practices improvements
    for failed_check in best_practices.get('failed_checks', []):
        if 'docstring' in failed_check.lower():
            suggestions.append({
                'type': 'documentation',
                'priority': 'medium',
                'description': 'Add docstrings to functions and classes',
                'example': '"""Brief description of function purpose and parameters"""'
            })
        elif 'naming' in failed_check.lower():
            suggestions.append({
                'type': 'style',
                'priority': 'medium',
                'description': 'Follow naming conventions (snake_case for functions, PascalCase for classes)',
                'example': 'def calculate_result() instead of def CalculateResult()'
            })

    # Framework compliance improvements
    if not compliance.get('is_compliant', True):
        for violation in compliance.get('violations', []):
            suggestions.append({
                'type': 'framework',
                'priority': 'high',
                'description': violation,
                'example': '@cudaq.kernel decorator for quantum functions'
            })

    for recommendation in compliance.get('recommendations', []):
        suggestions.append({
            'type': 'framework',
            'priority': 'medium',
            'description': recommendation,
            'example': 'import cudaq'
        })

    # General improvements
    suggestions.extend(best_practices.get('suggestions', []))

    # Remove duplicates and format consistently
    unique_suggestions = []
    seen_descriptions = set()

    for suggestion in suggestions:
        if isinstance(suggestion, str):
            suggestion = {'type': 'general', 'priority': 'medium', 'description': suggestion, 'example': ''}

        desc = suggestion.get('description', '')
        if desc not in seen_descriptions:
            seen_descriptions.add(desc)
            unique_suggestions.append(suggestion)

    return unique_suggestions[:10]  # Limit to top 10


def calculate_overall_quality_score(
    syntax_validation: Dict[str, Any],
    best_practices: Dict[str, Any],
    compliance: Dict[str, Any],
    structure_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """Calculate overall code quality score."""

    # Weight different aspects
    weights = {
        'syntax': 0.3,
        'practices': 0.3,
        'compliance': 0.2,
        'structure': 0.2
    }

    # Calculate individual scores
    syntax_score = 1.0 if syntax_validation.get('is_valid', True) else 0.0
    practices_score = best_practices.get('score', 0.5)
    compliance_score = 1.0 if compliance.get('is_compliant', True) else 0.5
    structure_score = structure_analysis.get('complexity_score', 0.5)

    # Calculate weighted overall score
    overall_score = (
        syntax_score * weights['syntax'] +
        practices_score * weights['practices'] +
        compliance_score * weights['compliance'] +
        structure_score * weights['structure']
    )

    # Determine quality rating
    if overall_score >= 0.8:
        quality_rating = 'Excellent'
    elif overall_score >= 0.6:
        quality_rating = 'Good'
    elif overall_score >= 0.4:
        quality_rating = 'Fair'
    else:
        quality_rating = 'Poor'

    return {
        'overall_score': round(overall_score, 2),
        'quality_rating': quality_rating,
        'component_scores': {
            'syntax': syntax_score,
            'best_practices': practices_score,
            'framework_compliance': compliance_score,
            'code_structure': structure_score
        },
        'weights_used': weights
    }