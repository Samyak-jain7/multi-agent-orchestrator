"""
Tool registry for agent extensions.

Built-in tools that agents can use:
- Web search (DuckDuckGo/SerpAPI)
- HTTP requests
- Calculator
- etc.

Adding a new tool:
1. Create a new class inheriting from AgentTool
2. Add it to the TOOL_REGISTRY dict
3. Tools are available to all agents automatically
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
import json
import asyncio
import aiohttp
from datetime import datetime


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
    Web search tool using DuckDuckGo HTML parsing (no API key required).
    For production, replace with SerpAPI or similar.
    """
    name = "web_search"
    description = "Search the web for current information, job listings, news, or any factual data. Use this when you need up-to-date information from the internet."
    parameters = {
        "query": {
            "type": "string",
            "description": "The search query to look up",
            "required": True
        },
        "num_results": {
            "type": "integer",
            "description": "Number of results to return (default: 5)",
            "default": 5
        }
    }

    async def execute(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        try:
            search_url = f"https://duckduckgo.com/html/?q={query}&kl=en-in"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, headers=headers, timeout=10) as response:
                    if response.status != 200:
                        return {"error": f"Search failed with status {response.status}", "results": []}

                    html = await response.text()

            # Simple HTML parsing to extract search results
            results = self._parse_html_results(html, num_results)

            return {
                "query": query,
                "results": results,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "duckduckgo"
            }
        except asyncio.TimeoutError:
            return {"error": "Search timed out", "results": []}
        except Exception as e:
            return {"error": str(e), "results": []}

    def _parse_html_results(self, html: str, num_results: int) -> List[Dict[str, str]]:
        """Parse DuckDuckGo HTML results."""
        results = []
        import re
        from urllib.parse import unquote, parse_qs, urlparse

        # Each result is in a div with class 'result results_links...'
        # Split by result block start
        result_divs = re.split(r'<div class="result results_links', html)

        for div in result_divs[1:num_results + 1]:  # Skip first split (before any results)
            # Find title - it's in <a class="result__a" href="...">TITLE</a>
            title_match = re.search(r'class="result__a"[^>]*>([^<]+)</a>', div)
            # Find URL from the href
            url_match = re.search(r'href="([^"]+)"', div)
            # Find snippet - it's in <a class="result__snippet">SNIPPET</a>
            snippet_match = re.search(r'class="result__snippet"[^>]*>([^<]+)</a>', div)

            if title_match:
                title = title_match.group(1).strip()
                # Extract actual URL from duckduckgo redirect
                raw_url = url_match.group(1) if url_match else ""
                if "uddg=" in raw_url:
                    # Extract the actual destination URL using urlparse
                    parsed = urlparse('https:' + raw_url)
                    params = parse_qs(parsed.query)
                    url = unquote(params.get('uddg', [raw_url])[0])
                else:
                    url = unquote(raw_url.replace("//", ""))

                snippet = snippet_match.group(1).strip() if snippet_match else ""
                # Clean HTML entities
                snippet = re.sub(r'<[^>]+>', '', snippet).strip()

                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet[:200] + "..." if len(snippet) > 200 else snippet
                })

        return results


class JobSiteSearchTool(AgentTool):
    """
    Tool to search job sites (LinkedIn, Naukri, Instahire, etc.)
    Simulates job search by using web search with job-specific queries.
    """
    name = "job_site_search"
    description = "Search for job listings on LinkedIn, Naukri, Instahire, or other job sites. Enter role, location, and experience level to find relevant SDE positions."
    parameters = {
        "site": {
            "type": "string",
            "description": "Job site to search: 'linkedin', 'naukri', 'instahire', or 'all'",
            "required": True,
            "enum": ["linkedin", "naukri", "instahire", "all"]
        },
        "role": {
            "type": "string",
            "description": "Job title or role to search for",
            "required": True
        },
        "location": {
            "type": "string",
            "description": "City or location to search in",
            "required": True
        },
        "experience": {
            "type": "string",
            "description": "Experience level (e.g., 'SDE2', '3-5 years', 'senior')"
        }
    }

    async def execute(self, site: str, role: str, location: str, experience: str = None) -> Dict[str, Any]:
        # Build search query based on inputs
        exp_suffix = f" {experience}" if experience else ""
        query = f"{role} jobs {location} site:{self._get_site_domain(site)}{exp_suffix}"

        search_tool = WebSearchTool()
        search_results = await search_tool.execute(query=query, num_results=10)

        if "error" in search_results:
            return search_results

        # Structure the results as job listings
        jobs = []
        for r in search_results.get("results", []):
            jobs.append({
                "title": r["title"],
                "url": r["url"],
                "source": site,
                "location": location,
                "snippet": r["snippet"]
            })

        return {
            "site": site,
            "role": role,
            "location": location,
            "experience": experience,
            "jobs_found": len(jobs),
            "jobs": jobs,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _get_site_domain(self, site: str) -> str:
        domains = {
            "linkedin": "linkedin.com/jobs",
            "naukri": "naukri.com",
            "instahire": "instahire.com",
            "all": ""
        }
        return domains.get(site, "")


class CalculatorTool(AgentTool):
    """Simple calculator tool for computations."""
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
            # Safe eval - only allow numbers and basic operators
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
    """Summarize text or articles."""
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
    "job_site_search": JobSiteSearchTool(),
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