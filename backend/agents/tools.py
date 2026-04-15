"""
Tool registry for agent extensions.

Built-in tools that agents can use:
- Web search (DuckDuckGo via LangChain)
- Calculator
- etc.

Adding a new tool:
1. Create a new class inheriting from AgentTool
2. Add it to the TOOL_REGISTRY dict
3. Tools are available to all agents automatically
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun


class AgentTool(ABC):
    """Abstract base class for all agent tools."""

    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters."""
        pass

    def get_definition(self) -> Dict[str, Any]:
        """Return the tool definition for LLM consumption."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class WebSearchTool(AgentTool):
    """
    Web search tool using DuckDuckGo via LangChain.
    """
    name = "web_search"
    description = "Search the web for current information, job listings, news, or any factual data. Use this when you need up-to-date information from the internet."
    parameters = {
        "query": {
            "type": "string",
            "description": "The search query to look up",
            "required": True
        }
    }

    def __init__(self):
        self._langchain_tool = DuckDuckGoSearchRun()

    async def execute(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        try:
            # LangChain tool returns a string, we parse it into structured format
            result = self._langchain_tool.invoke({"query": query})
            # Truncate result if num_results suggests a shorter response
            content = result[:500] + "..." if len(result) > 500 else result
            return {
                "query": query,
                "results": [{"content": content}],
                "timestamp": datetime.utcnow().isoformat(),
                "source": "duckduckgo"
            }
        except Exception as e:
            return {"error": str(e), "results": []}


class CalculatorTool(AgentTool):
    """Simple calculator tool for computations using Python eval."""
    name = "calculator"
    description = "Perform mathematical calculations. Use for salary calculations, percentage computations, or any numeric operations."
    parameters = {
        "expression": {
            "type": "string",
            "description": "Mathematical expression to evaluate (e.g., '25 * 10000 * 12' for annual salary)",
            "required": True
        }
    }

    async def execute(self, expression: str) -> Dict[str, Any]:
        try:
            import re
            if not re.match(r'^[\d\s+\-*/().]+$', expression):
                return {"error": "Invalid expression", "result": None}

            result = eval(expression)  # Safe because we filtered input
            return {
                "expression": expression,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {"error": str(e), "result": None}


class TextSummaryTool(AgentTool):
    """Summarize text or articles using extractive method."""
    name = "text_summary"
    description = "Extract and summarize the main points from a block of text, article, or document. Useful for condensing job descriptions, articles, or reports."
    parameters = {
        "text": {
            "type": "string",
            "description": "Text to summarize",
            "required": True
        },
        "max_length": {
            "type": "integer",
            "description": "Maximum length of summary in words",
            "default": 100
        }
    }

    async def execute(self, text: str, max_length: int = 100) -> Dict[str, Any]:
        # Simple extractive summary - get first few sentences
        sentences = text.split('.')
        summary = '. '.join(sentences[:3]) + '.'

        if len(summary.split()) > max_length:
            words = summary.split()
            summary = ' '.join(words[:max_length]) + '...'

        return {
            "original_length": len(text.split()),
            "summary": summary,
            "timestamp": datetime.utcnow().isoformat()
        }


# ---------------------------------------------------------------------------
# Tool Registry - add new tools here
# ---------------------------------------------------------------------------
TOOL_REGISTRY: Dict[str, AgentTool] = {
    "web_search": WebSearchTool(),
    "calculator": CalculatorTool(),
    "text_summary": TextSummaryTool(),
}


def get_tool(name: str) -> Optional[AgentTool]:
    """Get a tool by name from the registry."""
    return TOOL_REGISTRY.get(name)


def get_all_tool_definitions() -> List[Dict[str, Any]]:
    """Get definitions of all available tools for LLM."""
    return [tool.get_definition() for tool in TOOL_REGISTRY.values()]


async def execute_tool(name: str, **kwargs) -> Dict[str, Any]:
    """Execute a tool by name with given arguments."""
    tool = get_tool(name)
    if not tool:
        return {"error": f"Tool '{name}' not found. Available tools: {list(TOOL_REGISTRY.keys())}"}

    try:
        return await tool.execute(**kwargs)
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}
