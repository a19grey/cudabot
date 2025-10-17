from crewai import Crew, Process
from crewai.flow import Flow, start, listen, router
from typing import Dict, Any, Optional, List
import asyncio
from datetime import datetime
import json
from pathlib import Path

from agents.query_agent import create_query_understanding_agent, create_query_understanding_task
from agents.researcher_agent import create_researcher_agent, create_research_task, parse_research_results
from agents.code_agent import create_code_generation_agent, create_code_generation_task
from agents.validation_agent import create_validation_agent, create_validation_task
from agents.response_agent import create_response_agent, create_response_task
from embeddings.vector_store import initialize_chroma_client, create_collection
from config_loader import get_merged_config, get_data_paths
from utils.output_manager import get_output_manager, debug_print, format_final_response


class DocumentationAssistantFlow(Flow):
    """Main flow for the documentation assistant using CrewAI."""

    def __init__(self, target_name: str):
        super().__init__()
        self.target_name = target_name
        self.config = get_merged_config(target_name)
        self.data_paths = get_data_paths(self.config)

        # Initialize vector store
        self.chroma_client = initialize_chroma_client(self.data_paths['embeddings_dir'])
        self.collection = create_collection(
            self.chroma_client,
            f"{target_name}_docs",
            embedding_dimension=384
        )

        # Create agents
        self.researcher_agent = create_researcher_agent(self.collection, self.config)
        self.query_agent = create_query_understanding_agent(self.collection, self.config)
        self.code_agent = create_code_generation_agent(self.config)
        self.validation_agent = create_validation_agent(self.config)

        # Initialize conversation state
        self.conversation_history: List[Dict[str, Any]] = []

    @start()
    def process_user_query(self) -> Dict[str, Any]:
        """Start the flow with user query processing."""
        # Extract query from flow inputs
        query = self.state.get('query', '')
        print(f"Processing query: {query}")

        # Create initial state
        state = {
            'original_query': query,
            'timestamp': datetime.utcnow().isoformat(),
            'target': self.target_name,
            'step': 'query_understanding',
            'documentation_context': '',
            'generated_code': '',
            'validation_result': '',
            'final_response': ''
        }

        return state

    @listen(process_user_query)
    def research_and_retrieve(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Use researcher agent to intelligently find relevant documentation."""
        print(f"🔬 Researcher agent analyzing query and searching documentation...")

        query = state['original_query']

        # Create and execute research task
        research_task = create_research_task(query, self.researcher_agent, self.config)

        # Create crew for intelligent research
        research_crew = Crew(
            agents=[self.researcher_agent],
            tasks=[research_task],
            process=Process.sequential,
            verbose=True
        )

        # Execute the crew
        result = research_crew.kickoff()
        research_output = str(result)

        # Parse research results
        parsed_results = parse_research_results(research_output)

        # Update state with research findings
        state['research_output'] = research_output
        state['research_parsed'] = parsed_results
        state['documentation_context'] = research_output  # Use full research output as context
        state['step'] = 'research_completed'

        print(f"✅ Research completed: {len(state['documentation_context'])} characters")
        if parsed_results.get('parsed'):
            print(f"   Confidence: {parsed_results.get('confidence_assessment', {}).get('confidence', 'N/A')}")
            print(f"   Chunks found: {parsed_results.get('selected_chunks', 0)}")

        return state

    @listen(research_and_retrieve)
    def finalize_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create final response, optionally generating and validating code if needed."""
        print("Finalizing response...")

        # Check if code generation is needed
        query = state['original_query'].lower()
        code_indicators = [
            'code', 'example', 'implement', 'write', 'create', 'build',
            'function', 'class', 'method', 'how to', 'generate'
        ]
        needs_code = any(indicator in query for indicator in code_indicators)

        # Generate code if needed
        if needs_code:
            print("💻 Generating code...")
            context = state['documentation_context']

            # Create and execute code generation task
            code_task = create_code_generation_task(state['original_query'], context, self.code_agent, self.config)
            code_crew = Crew(
                agents=[self.code_agent],
                tasks=[code_task],
                process=Process.sequential,
                verbose=True
            )
            result = code_crew.kickoff()
            state['generated_code'] = str(result)
            state['step'] = 'code_generated'
            print(f"✅ Code generated: {len(state['generated_code'])} characters")

            # Validate the code
            print("✔️  Validating generated code...")
            validation_task = create_validation_task(
                state['generated_code'], context, state['original_query'],
                self.validation_agent, self.config
            )
            validation_crew = Crew(
                agents=[self.validation_agent],
                tasks=[validation_task],
                process=Process.sequential,
                verbose=True
            )
            validation_result = validation_crew.kickoff()
            state['validation_result'] = str(validation_result)
            state['step'] = 'code_validated'
            print(f"✅ Code validated: {len(state['validation_result'])} characters")

        response_parts = []

        # Add documentation context
        if state['documentation_context']:
            response_parts.append("## Relevant Documentation\n")
            response_parts.append(state['documentation_context'])
            response_parts.append("\n")

        # Add generated code if present
        if state['generated_code']:
            response_parts.append("## Generated Code\n")
            response_parts.append(state['generated_code'])
            response_parts.append("\n")

        # Add validation results if present
        if state['validation_result']:
            response_parts.append("## Code Review\n")
            response_parts.append(state['validation_result'])
            response_parts.append("\n")

        # Compile final response
        final_response = "".join(response_parts)

        state['final_response'] = final_response
        state['step'] = 'completed'
        state['completed_at'] = datetime.utcnow().isoformat()

        # Save to conversation history
        self._save_to_history(state)

        print(f"Response finalized: {len(final_response)} characters")

        return state

    def _save_to_history(self, state: Dict[str, Any]) -> None:
        """Save interaction to conversation history."""
        history_entry = {
            'timestamp': state.get('timestamp'),
            'completed_at': state.get('completed_at'),
            'query': state.get('original_query'),
            'target': state.get('target'),
            'had_code': bool(state.get('generated_code')),
            'response_length': len(state.get('final_response', '')),
            'steps_completed': state.get('step')
        }

        self.conversation_history.append(history_entry)

        # Also save to disk
        try:
            history_file = Path(self.data_paths['processed_dir']) / f"{self.target_name}_conversation_history.json"
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversation_history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save conversation history: {e}")


def create_simple_crew_workflow(target_name: str, query: str, debug_mode: bool = False, status_callback=None) -> Dict[str, Any]:
    """
    Create a simple crew workflow without flows for basic queries.

    Args:
        target_name: Name of the target documentation set
        query: User's query
        debug_mode: If True, show verbose output. If False, capture to log file.
        status_callback: Optional callback function(status: str) to report progress

    Returns:
        Result dictionary with documentation, code, and validation
    """
    from utils.output_manager import initialize_output_manager
    from preprocessing.hierarchical_processor import load_doc_map, load_lookup_data
    from tools.grep_search import GrepSearchTool

    def report_status(status: str):
        """Helper to report status through callback."""
        if status_callback:
            status_callback(status)

    # Initialize output manager with the correct debug mode
    output_mgr = initialize_output_manager(debug_mode=debug_mode)

    config = get_merged_config(target_name)
    data_paths = get_data_paths(config)

    # Initialize vector store
    debug_print("🔧 Initializing vector store...")
    report_status("🔧 Initializing vector store...")
    chroma_client = initialize_chroma_client(data_paths['embeddings_dir'])
    collection = create_collection(chroma_client, f"{target_name}_docs")

    # Load hierarchical data and create GREP tool
    debug_print("🗺️  Loading hierarchical document structure...")
    report_status("🗺️  Loading document index...")
    doc_map = load_doc_map(target_name, data_paths['processed_dir'])
    lookup_data = load_lookup_data(target_name, data_paths['processed_dir'])

    grep_tool = None
    if doc_map:
        try:
            grep_tool = GrepSearchTool(doc_map)
            debug_print("✅ GREP search tool initialized")
            report_status("✅ Search tools ready")
        except Exception as e:
            debug_print(f"⚠️  GREP tool initialization failed: {e}")

    # Create agents (using researcher with GREP support)
    debug_print("🤖 Creating agents...")
    report_status("🤖 Agents initialized")
    researcher_agent = create_researcher_agent(collection, config, grep_tool=grep_tool)
    code_agent = create_code_generation_agent(config)
    validation_agent = create_validation_agent(config)
    response_agent = create_response_agent(config)

    # Create research task
    research_task = create_research_task(query, researcher_agent, config)

    # Execute intelligent research
    debug_print("\n🔬 Researcher agent searching for relevant documentation...")
    report_status("🔬 Search Agent analyzing query...")

    with output_mgr.capture_output():
        research_crew = Crew(
            agents=[researcher_agent],
            tasks=[research_task],
            process=Process.sequential,
            verbose=debug_mode  # Only verbose in debug mode
        )
        research_result = research_crew.kickoff()

    documentation_context = str(research_result)
    debug_print(f"✅ Research completed: {len(documentation_context)} characters")
    report_status(f"✅ Documentation retrieved")

    # Determine if code generation is needed
    needs_code = any(indicator in query.lower() for indicator in
                    ['code', 'example', 'implement', 'write', 'create', 'build'])

    result = {
        'query': query,
        'documentation_context': documentation_context,
        'generated_code': '',
        'validation_result': '',
        'timestamp': datetime.utcnow().isoformat()
    }

    if needs_code:
        # Generate code
        debug_print("\n💻 Generating code...")
        report_status("💻 Code Agent generating examples...")

        with output_mgr.capture_output():
            code_task = create_code_generation_task(query, documentation_context, code_agent, config)
            code_crew = Crew(
                agents=[code_agent],
                tasks=[code_task],
                process=Process.sequential,
                verbose=debug_mode
            )
            code_result = code_crew.kickoff()

        generated_code = str(code_result)
        result['generated_code'] = generated_code
        debug_print(f"✅ Code generated: {len(generated_code)} characters")
        report_status(f"✅ Code generated")

        # Validate code
        debug_print("\n✔️  Validating code...")
        report_status("✔️  Validation Agent reviewing code...")

        with output_mgr.capture_output():
            validation_task = create_validation_task(generated_code, documentation_context, query, validation_agent, config)
            validation_crew = Crew(
                agents=[validation_agent],
                tasks=[validation_task],
                process=Process.sequential,
                verbose=debug_mode
            )
            validation_result = validation_crew.kickoff()

        result['validation_result'] = str(validation_result)
        debug_print(f"✅ Validation completed: {len(str(validation_result))} characters")
        report_status("✅ Code validated")

    # Generate conversational response
    debug_print("\n💬 Creating conversational response...")
    report_status("💬 Response Agent crafting final answer...")

    with output_mgr.capture_output():
        response_task = create_response_task(
            user_query=query,
            research_findings=documentation_context,
            generated_code=result.get('generated_code', ''),
            validation_result=result.get('validation_result', ''),
            agent=response_agent,
            config=config
        )
        response_crew = Crew(
            agents=[response_agent],
            tasks=[response_task],
            process=Process.sequential,
            verbose=debug_mode
        )
        conversational_response = response_crew.kickoff()

    result['conversational_response'] = str(conversational_response)
    debug_print(f"✅ Conversational response generated: {len(str(conversational_response))} characters")
    report_status("✅ Response ready!")

    return result


async def run_documentation_assistant_async(target_name: str, query: str) -> Dict[str, Any]:
    """Run the documentation assistant asynchronously."""
    try:
        # Initialize flow
        flow = DocumentationAssistantFlow(target_name)

        # Execute flow
        result = await flow.kickoff_async(inputs={'query': query})

        return result
    except Exception as e:
        print(f"Error running async flow: {e}")
        # Fallback to simple crew workflow
        return create_simple_crew_workflow(target_name, query)


def run_documentation_assistant(target_name: str, query: str, use_flow: bool = False, debug_mode: bool = False, status_callback=None) -> Dict[str, Any]:
    """Run the documentation assistant synchronously.

    Args:
        target_name: Name of the target documentation set
        query: User's query
        use_flow: If True, use CrewAI flows (experimental). If False, use simple crew workflow.
        debug_mode: If True, show verbose output. If False, capture to log file.
        status_callback: Optional callback function(status: str) to report progress

    Returns:
        Result dictionary with documentation, code, and validation
    """
    try:
        if use_flow:
            # Try using CrewAI flows
            flow = DocumentationAssistantFlow(target_name)
            flow.kickoff(inputs={'query': query})
            # Extract the final state from the flow
            result = flow.state
            # Add query and target if not present
            if 'query' not in result:
                result['query'] = query
            if 'target' not in result:
                result['target'] = target_name
            return result
        else:
            # Use simple crew workflow with debug mode and status callback
            return create_simple_crew_workflow(target_name, query, debug_mode=debug_mode, status_callback=status_callback)

    except Exception as e:
        print(f"Error running flow: {e}")
        # Fallback to simple crew workflow
        return create_simple_crew_workflow(target_name, query, debug_mode=debug_mode, status_callback=status_callback)


def get_conversation_history(target_name: str) -> List[Dict[str, Any]]:
    """Get conversation history for a target."""
    try:
        config = get_merged_config(target_name)
        data_paths = get_data_paths(config)

        history_file = Path(data_paths['processed_dir']) / f"{target_name}_conversation_history.json"

        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading conversation history: {e}")

    return []


def format_assistant_response(result: Dict[str, Any]) -> str:
    """Format the assistant response for display.

    Prioritizes the conversational response if available, otherwise falls back to raw outputs.
    """
    # If we have a conversational response, use it as the primary output
    conversational_response = result.get('conversational_response', '')
    if conversational_response:
        return conversational_response

    # Fallback to structured output if no conversational response
    response_parts = []

    # Add header
    query = result.get('query') or result.get('original_query', 'Unknown query')
    target = result.get('target', 'Unknown target')
    timestamp = result.get('timestamp', 'Unknown time')

    response_parts.append(f"# {target} Assistant Response")
    response_parts.append(f"**Query:** {query}")
    response_parts.append(f"**Generated at:** {timestamp}")
    response_parts.append("")

    # Add documentation context
    documentation = result.get('documentation_context', '')
    if documentation:
        response_parts.append("## 📚 Relevant Documentation")
        response_parts.append(documentation)
        response_parts.append("")

    # Add generated code
    code = result.get('generated_code', '')
    if code:
        response_parts.append("## 💻 Generated Code")
        response_parts.append(code)
        response_parts.append("")

    # Add validation results
    validation = result.get('validation_result', '')
    if validation:
        response_parts.append("## ✅ Code Review")
        response_parts.append(validation)
        response_parts.append("")

    # Add final response if available
    final_response = result.get('final_response', '')
    if final_response and final_response not in [documentation, code, validation]:
        response_parts.append("## 🎯 Summary")
        response_parts.append(final_response)

    return "\n".join(response_parts)


# Utility functions for crew management

def check_crew_health(target_name: str) -> Dict[str, Any]:
    """Check the health of crew components."""
    try:
        config = get_merged_config(target_name)
        data_paths = get_data_paths(config)

        health = {
            'status': 'healthy',
            'components': {},
            'issues': []
        }

        # Check vector store
        try:
            chroma_client = initialize_chroma_client(data_paths['embeddings_dir'])
            collection = create_collection(chroma_client, f"{target_name}_docs")
            count = collection.count()
            health['components']['vector_store'] = {'status': 'healthy', 'document_count': count}
        except Exception as e:
            health['components']['vector_store'] = {'status': 'error', 'error': str(e)}
            health['issues'].append(f"Vector store error: {e}")

        # Check configuration
        try:
            agents_config = config.get('agents', {})
            health['components']['configuration'] = {
                'status': 'healthy',
                'agents_configured': len(agents_config)
            }
        except Exception as e:
            health['components']['configuration'] = {'status': 'error', 'error': str(e)}
            health['issues'].append(f"Configuration error: {e}")

        if health['issues']:
            health['status'] = 'degraded' if len(health['issues']) < 3 else 'unhealthy'

        return health

    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'components': {},
            'issues': [str(e)]
        }