"""
Conversational response agent for creating natural, user-friendly chat responses.

This agent takes research results and code from other agents and crafts
the final conversational response that users see in the chat interface.
"""

from crewai import Agent, Task
from typing import Dict, Any


def create_response_agent(config: Dict[str, Any]) -> Agent:
    """
    Create a conversational response agent.

    This agent is responsible for taking technical research results and code
    and formatting them into natural, helpful conversational responses.

    Args:
        config: Configuration dictionary

    Returns:
        Conversational response agent
    """
    agent_config = config.get('agents', {}).get('response_agent', {})

    backstory = agent_config.get('backstory', """You are a friendly and knowledgeable documentation assistant chatbot.
Your role is to take technical research findings and code examples and present them
in a clear, conversational way that feels natural in a chat interface.

You excel at:
- Summarizing technical documentation in plain language
- Explaining code examples step-by-step
- Providing context and reasoning for solutions
- Maintaining a helpful, encouraging tone
- Structuring responses for easy reading

You avoid:
- Dumping raw technical details without explanation
- Using overly formal or robotic language
- Including unnecessary metadata or internal processing details
- Overwhelming users with too much information at once

Remember: The user is having a conversation with you, not reading a technical report.
Make your responses feel personal, helpful, and conversational.""")

    response_agent = Agent(
        role=agent_config.get('role', 'Conversational Response Specialist'),
        goal=agent_config.get('goal',
             'Create natural, user-friendly responses from technical research and code'),
        backstory=backstory,
        verbose=agent_config.get('verbose', False),
        allow_delegation=False,
        memory=True
    )

    return response_agent


def create_response_task(
    user_query: str,
    research_findings: str,
    generated_code: str,
    validation_result: str,
    agent: Agent,
    config: Dict[str, Any]
) -> Task:
    """
    Create a task for generating a conversational response.

    Args:
        user_query: Original user question
        research_findings: Research results from researcher agent
        generated_code: Code from code generation agent (if any)
        validation_result: Validation from validation agent (if any)
        agent: The response agent
        config: Configuration dictionary

    Returns:
        Response generation task
    """

    # Build the context for the response agent
    context_parts = []

    context_parts.append(f"# User Question\n{user_query}\n")

    if research_findings:
        context_parts.append(f"# Research Findings\n{research_findings}\n")

    if generated_code:
        context_parts.append(f"# Generated Code\n{generated_code}\n")

    if validation_result:
        context_parts.append(f"# Code Review\n{validation_result}\n")

    full_context = "\n".join(context_parts)

    task_description = f"""Based on the information provided below, create a natural, conversational response
to the user's question.

{full_context}

**Your Task:**
Create a friendly, helpful response that:

1. **Directly answers the user's question** in clear, natural language
2. **Explains key concepts** from the documentation in plain terms
3. **If code was generated:**
   - Introduce it naturally (e.g., "Here's how you can do that:")
   - Explain what the code does step-by-step
   - Point out important details or best practices
4. **Provides additional context** that would be helpful (e.g., common pitfalls, alternatives, when to use this approach)
5. **Ends with a helpful closing** (e.g., "Let me know if you'd like me to explain any part in more detail!")

**Guidelines:**
- Use a warm, conversational tone (like you're helping a colleague)
- Structure your response with clear headings when appropriate
- Keep code blocks properly formatted with syntax highlighting
- Don't include metadata like timestamps, doc IDs, or internal processing info
- Don't just paste raw documentation - summarize and explain
- If the research didn't find good information, honestly say so and suggest alternatives

**Response Format:**
Write your response as if you're chatting directly with the user. No formal headers like
"ANSWER:" or "SUMMARY:" - just natural conversation.

Remember: This is what the user will see in the chat. Make it helpful and human!"""

    task = Task(
        description=task_description,
        agent=agent,
        expected_output="""A natural, conversational response that directly helps the user with their question.
The response should feel like it's from a knowledgeable friend, not a technical report generator.
It should be well-structured, easy to read, and focused on being genuinely helpful."""
    )

    return task
