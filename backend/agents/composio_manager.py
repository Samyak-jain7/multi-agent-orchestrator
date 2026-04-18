"""
Composio Tool Manager — manages Composio tools for agents.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Filtered list of commonly useful tools that don't require complex auth
USEFUL_TOOLS = [
    # Search
    "google_search",
    "wikipedia_search",
    "ddg_search",
    # Code
    "bash_execute",
    "python_execute",
    "code_search",
    # File
    "file_read",
    "file_write",
    "file_search",
    # Web
    "web_fetch",
    "browser_navigate",
    "take_screenshot",
    # Data
    "json_parse",
    "csv_read",
    "api_request",
    # Communication
    "send_email",
    "slack_send",
    "notion_create",
]


class ComposioToolManager:
    """
    Manages Composio tools for agents.

    Provides a filtered, safe subset of Composio tools that can be
    attached to agents in the orchestrator.
    """

    TOOL_CATEGORIES = {
        "search": ["google_search", "wikipedia_search", "ddg_search"],
        "code": ["bash_execute", "python_execute", "code_search"],
        "file": ["file_read", "file_write", "file_search"],
        "web": ["web_fetch", "browser_navigate", "take_screenshot"],
        "data": ["json_parse", "csv_read", "api_request"],
        "communication": ["send_email", "slack_send", "notion_create"],
    }

    def __init__(self):
        self._client = None
        self._tool_cache: Dict[str, Any] = {}

    @property
    def client(self):
        """Lazy Composio client initialization."""
        if self._client is None:
            try:
                from composio import Composio

                self._client = Composio()
            except Exception as e:
                logger.warning(f"Composio client init failed: {e}")
                self._client = None
        return self._client

    def list_available_tools(self) -> List[Dict[str, str]]:
        """
        Return all available Composio tools with descriptions.
        Returns a filtered list of safe, commonly useful tools.
        """
        if not self.client:
            # Return static list if Composio not configured
            return [
                {"name": name, "description": f"Tool: {name}", "category": cat}
                for cat, names in self.TOOL_CATEGORIES.items()
                for name in names
            ]

        try:
            # Try to get real tools from Composio
            tools = self.client.tools.list()
            available = []
            seen = set()

            for tool in tools:
                name = getattr(tool, "name", None) or getattr(tool, "id", None)
                if name and name in USEFUL_TOOLS and name not in seen:
                    seen.add(name)
                    available.append(
                        {
                            "name": name,
                            "description": getattr(tool, "description", f"Tool: {name}"),
                            "category": self._get_category(name),
                        }
                    )

            # Fill in any missing from our static list
            for cat, names in self.TOOL_CATEGORIES.items():
                for name in names:
                    if name not in seen:
                        available.append(
                            {
                                "name": name,
                                "description": f"Tool: {name}",
                                "category": cat,
                            }
                        )

            return available
        except Exception as e:
            logger.warning(f"Failed to list Composio tools: {e}")
            # Fallback to static list
            return [
                {"name": name, "description": f"Tool: {name}", "category": cat}
                for cat, names in self.TOOL_CATEGORIES.items()
                for name in names
            ]

    def _get_category(self, tool_name: str) -> str:
        """Get the category for a tool name."""
        for cat, names in self.TOOL_CATEGORIES.items():
            if tool_name in names:
                return cat
        return "other"

    def get_tools_for_agent(self, tool_ids: List[str]) -> List[Any]:
        """
        Get configured Composio tools for an agent.
        Returns a list of Composio tool objects.
        """
        if not self.client:
            logger.warning("Composio client not available, returning empty tool list")
            return []

        tools = []
        for tool_id in tool_ids:
            if tool_id in self._tool_cache:
                tools.append(self._tool_cache[tool_id])
                continue

            try:
                tool = self.client.tools.get(name=tool_id)
                self._tool_cache[tool_id] = tool
                tools.append(tool)
            except Exception as e:
                logger.warning(f"Failed to get tool {tool_id}: {e}")

        return tools

    def validate_tools(self, tool_ids: List[str]) -> Dict[str, bool]:
        """
        Check which tools are available.
        Returns {tool_id: available}.
        """
        available = self.list_available_tools()
        available_names = {t["name"] for t in available}

        return {tool_id: tool_id in available_names for tool_id in tool_ids}

    def get_tools_by_category(self, category: str) -> List[Dict[str, str]]:
        """Get all tools in a specific category."""
        all_tools = self.list_available_tools()
        return [t for t in all_tools if t.get("category") == category]

    def search_tools(self, query: str) -> List[Dict[str, str]]:
        """Search tools by name or description."""
        all_tools = self.list_available_tools()
        query_lower = query.lower()
        return [
            t for t in all_tools if query_lower in t["name"].lower() or query_lower in t.get("description", "").lower()
        ]
