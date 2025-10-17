"""
Context manager for injecting project overview into agent prompts.

This ensures all agents have consistent context about the project/documentation
they're working with.
"""

from pathlib import Path
from typing import Optional, Dict, Any


class ProjectContextManager:
    """Manages project overview context for agents."""

    def __init__(self, target_name: str, processed_dir: Path):
        """
        Initialize context manager.

        Args:
            target_name: Name of target (e.g., 'cuda_q')
            processed_dir: Directory containing processed artifacts
        """
        self.target_name = target_name
        self.processed_dir = processed_dir
        self.overview = None
        self._load_overview()

    def _load_overview(self):
        """Load project overview from file."""
        overview_path = self.processed_dir / f"{self.target_name}_overview.txt"
        if overview_path.exists():
            with open(overview_path, 'r', encoding='utf-8') as f:
                self.overview = f.read()

    def get_overview(self) -> str:
        """Get project overview text."""
        if self.overview:
            return self.overview
        return f"Documentation for {self.target_name}."

    def get_context_prefix(self) -> str:
        """
        Get formatted context prefix for agent backstories.

        This should be prepended to agent backstories to provide project context.
        """
        if not self.overview:
            return ""

        return f"""
## PROJECT CONTEXT

{self.overview}

---

"""

    def enhance_agent_backstory(self, backstory: str) -> str:
        """
        Enhance an agent backstory with project context.

        Args:
            backstory: Original agent backstory

        Returns:
            Enhanced backstory with project context prepended
        """
        context_prefix = self.get_context_prefix()
        return context_prefix + backstory

    def get_system_context(self) -> Dict[str, str]:
        """
        Get system context as dictionary for inclusion in prompts.

        Returns:
            Dictionary with project context information
        """
        return {
            "project_name": self.target_name,
            "project_overview": self.get_overview(),
            "context_available": self.overview is not None
        }


def load_context_manager(target_name: str, processed_dir: Path) -> ProjectContextManager:
    """
    Load or create a project context manager.

    Args:
        target_name: Target name
        processed_dir: Processed data directory

    Returns:
        ProjectContextManager instance
    """
    return ProjectContextManager(target_name, processed_dir)


def inject_context_into_agents(
    agents_config: Dict[str, Dict[str, Any]],
    context_manager: ProjectContextManager
) -> Dict[str, Dict[str, Any]]:
    """
    Inject project context into agent configurations.

    Args:
        agents_config: Dictionary of agent configurations
        context_manager: Project context manager

    Returns:
        Enhanced agent configurations with context
    """
    enhanced_config = {}

    for agent_name, agent_cfg in agents_config.items():
        enhanced_cfg = agent_cfg.copy()

        # Enhance backstory if present
        if 'backstory' in enhanced_cfg:
            enhanced_cfg['backstory'] = context_manager.enhance_agent_backstory(
                enhanced_cfg['backstory']
            )

        enhanced_config[agent_name] = enhanced_cfg

    return enhanced_config
