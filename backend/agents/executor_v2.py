"""
SupervisorExecutor — Proper multi-agent orchestrator using LangGraph.

This is a refactored version that replaces the simple LLM.invoke() pattern
with proper Model + Tools + Memory + Reasoning Loop architecture.

Graph structure:
    START -> SUPERVISOR -> [AGENTS] -> SUPERVISOR -> (END or loop)
"""

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from agents.composio_manager import ComposioToolManager
from agents.memory import WorkflowMemory
from agents.providers import load_provider_from_agent
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from models.execution import AgentModel, WorkflowModel
from models.execution import WorkflowStatus as DBWorkflowStatus
from schemas import ExecutionEvent
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class WorkflowState(dict):
    """
    LangGraph workflow state — passed between nodes.
    """

    workflow_id: str
    input_data: Dict[str, Any]
    current_node: str
    iteration: int
    max_iterations: int
    messages: List[Dict[str, str]]  # {"agent": str, "role": str, "content": str}
    agent_outputs: Dict[str, Dict[str, Any]]  # agent_id -> output
    supervisor_decision: Dict[str, Any]  # routing decision
    needs_refinement: bool
    final_output: Dict[str, Any]


class SupervisorExecutor:
    """
    Proper multi-agent orchestrator using LangGraph.

    Key improvements over executor_v1:
    - Model + Tools + Memory + Reasoning Loop per agent
    - Supervisor-based routing (LLM decides next agent)
    - Shared WorkflowMemory across all agents
    - Tool execution via Composio
    """

    def __init__(
        self,
        db: AsyncSession,
        event_callback: Optional[Callable[[ExecutionEvent], Awaitable[None]]] = None,
        env_vars: Optional[Dict[str, str]] = None,
    ):
        self.db = db
        self.event_callback = event_callback
        self.env_vars = env_vars or {}
        self._provider_cache: Dict[str, Any] = {}
        self._composio = ComposioToolManager()

    # -------------------------------------------------------------------------
    # LLM Provider helpers
    # -------------------------------------------------------------------------

    def _get_llm_for_agent(self, agent: AgentModel):
        """Get the LLM provider for a specific agent."""
        cache_key = f"{agent.id}"
        if cache_key in self._provider_cache:
            return self._provider_cache[cache_key]

        provider = load_provider_from_agent(
            agent_model_name=agent.model_name or "MiniMax-M2.7",
            agent_provider=agent.model_provider or "minimax",
            agent_config=agent.config or {},
            env_vars=self.env_vars,
        )
        self._provider_cache[cache_key] = provider
        return provider

    async def _get_agent_config(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Fetch agent config from DB."""
        stmt = select(AgentModel).where(AgentModel.id == agent_id)
        result = await self.db.execute(stmt)
        agent = result.scalar_one_or_none()
        if not agent:
            return None
        return {
            "id": agent.id,
            "name": agent.name,
            "system_prompt": agent.system_prompt,
            "tool_ids": agent.tool_ids or [],
            "memory_enabled": agent.memory_enabled,
            "max_iterations": agent.max_iterations or 5,
            "temperature": agent.temperature or 0.7,
            "model_provider": agent.model_provider,
            "model_name": agent.model_name,
        }

    async def _get_workflow_def(self, workflow_id: str) -> Dict[str, Any]:
        """Fetch workflow definition from DB."""
        stmt = select(WorkflowModel).where(WorkflowModel.id == workflow_id)
        result = await self.db.execute(stmt)
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        # If workflow_definition is set, use it; otherwise build from agent_ids
        if workflow.workflow_definition:
            return workflow.workflow_definition

        # Legacy: build DAG from agent_ids
        nodes = []
        edges = []
        for i, agent_id in enumerate(workflow.agent_ids or []):
            node_id = f"agent_{i}"
            nodes.append(
                {
                    "id": node_id,
                    "type": "agent",
                    "agent_id": agent_id,
                    "tools": [],
                }
            )
            if i == 0:
                edges.append({"from": "supervisor", "to": node_id})
            edges.append({"from": node_id, "to": "supervisor"})

        return {
            "nodes": [{"id": "supervisor", "type": "supervisor", "config": {}}] + nodes,
            "edges": edges,
            "max_iterations": workflow.max_iterations or 10,
        }

    # -------------------------------------------------------------------------
    # Supervisor Node
    # -------------------------------------------------------------------------

    def _get_supervisor_node(self, workflow_def: dict):
        """Returns a LangGraph node that acts as supervisor."""

        def supervisor_node(state: WorkflowState) -> WorkflowState:
            import asyncio

            messages = state.get("messages", [])
            iteration = state.get("iteration", 0)

            # Build context from shared memory
            memory_context = self._build_memory_context(state["workflow_id"])

            # Get agent nodes for routing
            agent_nodes = [n for n in workflow_def.get("nodes", []) if n.get("type") == "agent"]

            supervisor_prompt = f"""You are a workflow supervisor managing a multi-agent pipeline.

## Current State
- Workflow ID: {state['workflow_id']}
- Iteration: {iteration}/{state.get('max_iterations', 10)}
- Input: {json.dumps(state.get('input_data', {}), indent=2)[:500]}

## Available Agents
{json.dumps(agent_nodes, indent=2)}

## Conversation History
{memory_context}

## Your Decision
Based on the conversation history and current state, decide EXACTLY ONE action:

1. **Route to an agent** (if workflow just started OR needs more specialized work):
   Return: {{"next_agent": "agent_<index>", "reasoning": "why this agent"}}

2. **Finish successfully** (if task is complete):
   Return: {{"action": "finish", "reasoning": "why complete"}}

3. **Force finish** (if max iterations reached):
   Return: {{"action": "finish", "reasoning": "max iterations reached"}}

Output JSON only — no markdown, no explanation."""

            response_text = self._call_llm_sync(supervisor_prompt, model="supervisor")

            try:
                # Try to extract JSON from response
                decision = self._extract_json(response_text)
            except Exception:
                decision = {"action": "finish", "reasoning": "parse error"}

            logger.info(f"Supervisor decision: {decision}")

            return {
                **state,
                "supervisor_decision": decision,
                "current_node": "supervisor",
            }

        return supervisor_node

    def _call_llm_sync(self, prompt: str, model: str = "supervisor") -> str:
        """
        Synchronous LLM call for use in sync graph nodes.
        For async nodes, use _call_llm_async.
        """
        import asyncio

        # Create a simple sync wrapper for the async LLM call
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, we need to use a different approach
                # For sync nodes, we use a simple approach with minimax
                from agents.providers import get_provider

                provider = get_provider("minimax", self.env_vars)

                # Use sync invoke for supervisor decisions
                messages = [HumanMessage(content=prompt)]
                response = provider.ainvoke(messages)

                if hasattr(response, "content"):
                    return response.content
                return str(response)
            else:
                return asyncio.run(self._call_llm_async(prompt, model))
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self._call_llm_async(prompt, model))

    async def _call_llm_async(self, prompt: str, model: str = "supervisor") -> str:
        """Async LLM call."""
        from agents.providers import get_provider

        provider = get_provider("minimax", self.env_vars)
        messages = [HumanMessage(content=prompt)]
        response = await provider.ainvoke(messages)
        return response.content if hasattr(response, "content") else str(response)

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from a text response."""
        # Find JSON object in text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start : end + 1])
        return json.loads(text)

    def _build_memory_context(self, workflow_id: str) -> str:
        """Build context string from shared workflow memory."""
        try:
            memory = WorkflowMemory(workflow_id)
            return memory.get_summary()
        except Exception:
            return "(Memory unavailable)"

    def _format_context(self, prior_context: List[Dict[str, Any]]) -> str:
        """Format prior context for an agent prompt."""
        if not prior_context:
            return "(No prior context)"
        parts = []
        for msg in prior_context[-5:]:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")[:300]
            parts.append(f"[{role}] {content}")
        return "\n".join(parts)

    # -------------------------------------------------------------------------
    # Agent Node Factory
    # -------------------------------------------------------------------------

    def _get_agent_node(self, agent_id: str, tool_names: List[str]):
        """Factory: creates a LangGraph node for a specific agent."""

        async def agent_node(state: WorkflowState) -> WorkflowState:
            memory = WorkflowMemory(state["workflow_id"])

            # Get agent config from DB
            agent_config = await self._get_agent_config(agent_id)
            if not agent_config:
                logger.warning(f"Agent {agent_id} not found, skipping")
                return {**state, "current_node": f"agent_{agent_id}"}

            # Get tools from Composio
            tools = self._composio.get_tools_for_agent(tool_names + agent_config.get("tool_ids", []))

            # Read prior context
            prior_context = memory.read(limit=10)

            # Build agent prompt
            agent_prompt = f"""{agent_config['system_prompt']}

## Prior context from workflow:
{self._format_context(prior_context)}

## Your task:
{json.dumps(state.get('input_data', {}), indent=2)}

## Instructions:
- Use available tools to complete your task
- Write your final response clearly
- If you need more information, use search or fetch tools
"""

            # Reasoning loop: think -> act -> observe (up to max_iterations per agent)
            result = await self._agent_reasoning_loop(
                agent_config=agent_config,
                prompt=agent_prompt,
                tools=tools,
                max_iterations=agent_config.get("max_iterations", 3),
            )

            # Write to shared memory
            memory.write(agent_id, "agent", result["output"], {"tool_calls": result.get("tool_calls", [])})

            # Update state
            agent_outputs = {**state.get("agent_outputs", {}), agent_id: result}

            return {
                **state,
                "agent_outputs": agent_outputs,
                "messages": state.get("messages", []) + [{"agent": agent_id, "content": result["output"]}],
                "iteration": state.get("iteration", 0) + 1,
            }

        return agent_node

    async def _agent_reasoning_loop(
        self, agent_config: Dict[str, Any], prompt: str, tools: List[Any], max_iterations: int = 3
    ) -> dict:
        """
        Agent reasoning loop: think -> use tool -> observe -> decide.
        This is the key difference from simple LLM.invoke().
        """
        # Get the LLM for this agent
        stmt = select(AgentModel).where(AgentModel.id == agent_config["id"])
        result = await self.db.execute(stmt)
        agent_model = result.scalar_one_or_none()

        if not agent_model:
            return {"output": f"Agent {agent_config['id']} not found", "tool_calls": []}

        llm = self._get_llm_for_agent(agent_model)

        # Bind tools if available
        if tools:
            try:
                llm = llm.bind_tools(tools)
            except Exception as e:
                logger.warning(f"Failed to bind tools to LLM: {e}")

        messages = [HumanMessage(content=prompt)]
        tool_calls_made = []

        for i in range(max_iterations):
            try:
                response = await llm.ainvoke(messages)
            except Exception as e:
                logger.error(f"LLM invocation failed: {e}")
                return {"output": f"LLM error: {str(e)}", "tool_calls": tool_calls_made}

            if not hasattr(response, "tool_calls") or not response.tool_calls:
                # No tool call = done thinking
                return {
                    "output": response.content if hasattr(response, "content") else str(response),
                    "tool_calls": tool_calls_made,
                }

            # Execute each tool call
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name") or (tool_call.get("function", {}) or {}).get("name", "unknown")
                tool_args = tool_call.get("args") or tool_call.get("arguments") or {}

                try:
                    tool_result = await self._execute_tool(tool_name, tool_args)
                    messages.append(ToolMessage(content=str(tool_result), tool_call_id=tool_call.get("id", "unknown")))
                    tool_calls_made.append({"tool": tool_name, "args": tool_args, "result": str(tool_result)[:500]})
                except Exception as e:
                    error_msg = f"Tool error: {str(e)}"
                    messages.append(ToolMessage(content=error_msg, tool_call_id=tool_call.get("id", "unknown")))
                    tool_calls_made.append({"tool": tool_name, "args": tool_args, "error": str(e)})

        # Max iterations reached
        return {
            "output": response.content if hasattr(response, "content") else str(response),
            "tool_calls": tool_calls_made,
        }

    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Execute a tool and return the result."""
        # Map Composio tools to actual implementations
        tool_map = {
            "bash_execute": self._tool_bash,
            "python_execute": self._tool_python,
            "web_fetch": self._tool_web_fetch,
            "google_search": self._tool_google_search,
            "ddg_search": self._tool_ddg_search,
            "file_read": self._tool_file_read,
            "file_write": self._tool_file_write,
        }

        if tool_name in tool_map:
            return await tool_map[tool_name](args)

        # Default: return a message that tool is not implemented
        return f"Tool '{tool_name}' executed with args: {args}"

    async def _tool_bash(self, args: Dict[str, Any]) -> str:
        """Execute a bash command."""
        import subprocess

        cmd = args.get("command") or args.get("cmd", "")
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return result.stdout[:1000] if result.stdout else result.stderr[:1000] or "Command executed"
        except Exception as e:
            return f"Bash error: {str(e)}"

    async def _tool_python(self, args: Dict[str, Any]) -> str:
        """Execute Python code."""
        code = args.get("code", "")
        try:
            import contextlib
            import io

            f = io.StringIO()
            exec(code, {"__builtins__": __builtins__})
            return f.getvalue() or "Code executed"
        except Exception as e:
            return f"Python error: {str(e)}"

    async def _tool_web_fetch(self, args: Dict[str, Any]) -> str:
        """Fetch a URL."""
        url = args.get("url", "")
        try:
            import httpx

            response = httpx.get(url, timeout=10)
            return response.text[:2000]
        except Exception as e:
            return f"Fetch error: {str(e)}"

    async def _tool_google_search(self, args: Dict[str, Any]) -> str:
        """Google search."""
        query = args.get("query", "")
        try:
            import httpx

            # Simple search simulation (real implementation would use Google API)
            response = httpx.get(f"https://www.google.com/search?q={query}", timeout=10)
            return f"Search results for '{query}': {response.text[:500]}"
        except Exception as e:
            return f"Search error: {str(e)}"

    async def _tool_ddg_search(self, args: Dict[str, Any]) -> str:
        """DuckDuckGo search."""
        query = args.get("query", "")
        try:
            import httpx

            response = httpx.get(f"https://duckduckgo.com/?q={query}", timeout=10)
            return f"DDG results for '{query}': {response.text[:500]}"
        except Exception as e:
            return f"Search error: {str(e)}"

    async def _tool_file_read(self, args: Dict[str, Any]) -> str:
        """Read a file."""
        path = args.get("path", "")
        try:
            with open(path, "r") as f:
                return f.read()[:2000]
        except Exception as e:
            return f"Read error: {str(e)}"

    async def _tool_file_write(self, args: Dict[str, Any]) -> str:
        """Write to a file."""
        path = args.get("path", "")
        content = args.get("content", "")
        try:
            with open(path, "w") as f:
                f.write(content)
            return f"Written to {path}"
        except Exception as e:
            return f"Write error: {str(e)}"

    # -------------------------------------------------------------------------
    # Graph Building
    # -------------------------------------------------------------------------

    def _build_graph(self, workflow_def: dict) -> Any:  # Returns compiled LangGraph
        """Build the full LangGraph from workflow definition."""

        workflow = StateGraph(WorkflowState)

        # Add supervisor node
        workflow.add_node("supervisor", self._get_supervisor_node(workflow_def))

        # Add agent nodes
        agent_node_map = {}
        for node in workflow_def.get("nodes", []):
            if node.get("type") == "agent":
                agent_id = node.get("agent_id")
                tools = node.get("tools", [])
                node_name = f"agent_{agent_id}"
                workflow.add_node(node_name, self._get_agent_node(agent_id, tools))
                agent_node_map[node["id"]] = node_name

        # Add edges from workflow definition
        for edge in workflow_def.get("edges", []):
            from_node = edge["from"]
            to_node = edge["to"]
            condition = edge.get("condition")

            if condition:
                # Conditional edge
                workflow.add_conditional_edges(
                    from_node,
                    lambda state, cond=condition: self._evaluate_condition(state, cond),
                    {to_node: to_node, "supervisor": "supervisor"},
                )
            else:
                # Direct edge
                if from_node == "supervisor":
                    workflow.add_edge(from_node, agent_node_map.get(to_node, to_node))
                elif to_node == "supervisor":
                    workflow.add_edge(agent_node_map.get(from_node, from_node), to_node)
                else:
                    workflow.add_edge(agent_node_map.get(from_node, from_node), agent_node_map.get(to_node, to_node))

        # Entry point
        workflow.set_entry_point("supervisor")

        # Define conditional routing from supervisor
        # The supervisor returns {"next_agent": "agent_<id>"} or {"action": "finish"}
        workflow.add_conditional_edges(
            "supervisor",
            self._supervisor_router,
            {
                **{
                    agent_node_map.get(n["id"], n["id"]): agent_node_map.get(n["id"], n["id"])
                    for n in workflow_def.get("nodes", [])
                    if n.get("type") == "agent"
                },
                "finish": END,
            },
        )

        return workflow.compile(checkpointer=MemorySaver())

    def _supervisor_router(self, state: WorkflowState) -> str:
        """Route based on supervisor decision."""
        decision = state.get("supervisor_decision", {})
        if "next_agent" in decision:
            agent_ref = decision["next_agent"]
            # agent_ref format: "agent_<index>" or just the node id
            return agent_ref
        return "finish"

    def _evaluate_condition(self, state: WorkflowState, condition: str) -> str:
        """Evaluate a condition to decide routing."""
        # Simple condition evaluation
        # Could be extended to support more complex conditions
        if condition == "needs_research":
            # Check if any agent has research-related output
            for output in state.get("agent_outputs", {}).values():
                content = str(output.get("output", "")).lower()
                if any(kw in content for kw in ["research", "search", "find", "lookup"]):
                    return "supervisor"
        return "supervisor"

    # -------------------------------------------------------------------------
    # Workflow Execution
    # -------------------------------------------------------------------------

    async def execute_workflow(self, workflow_id: str, input_data: dict) -> dict:
        """Execute a workflow with proper LangGraph + shared memory."""

        # Load workflow definition from DB
        workflow_def = await self._get_workflow_def(workflow_id)

        # Update workflow status
        await self._update_workflow_status(workflow_id, DBWorkflowStatus.RUNNING)
        await self._emit_event(
            event_type="workflow_started",
            workflow_id=workflow_id,
            message=f"Workflow {workflow_id} started with SupervisorExecutor",
        )

        # Build graph
        graph = self._build_graph(workflow_def)

        # Initial state
        initial_state = WorkflowState(
            workflow_id=workflow_id,
            input_data=input_data,
            current_node="supervisor",
            iteration=0,
            max_iterations=workflow_def.get("max_iterations", 10),
            messages=[],
            agent_outputs={},
            supervisor_decision={},
            needs_refinement=True,
            final_output={},
        )

        # Execute
        try:
            result = await graph.ainvoke(
                initial_state, config={"configurable": {"thread_id": f"workflow_{workflow_id}"}}
            )

            # Mark workflow complete
            await self._update_workflow_status(workflow_id, DBWorkflowStatus.COMPLETED)
            await self._emit_event(
                event_type="workflow_completed", workflow_id=workflow_id, message=f"Workflow {workflow_id} completed"
            )

            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "output": result.get("final_output") or result.get("agent_outputs", {}),
                "iterations": result.get("iteration", 0),
            }
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            await self._update_workflow_status(workflow_id, DBWorkflowStatus.FAILED)
            await self._emit_event(
                event_type="workflow_failed",
                workflow_id=workflow_id,
                message=f"Workflow {workflow_id} failed: {str(e)}",
                meta_data={"error": str(e)},
            )
            return {"workflow_id": workflow_id, "status": "failed", "error": str(e)}

    async def _update_workflow_status(self, workflow_id: str, status: DBWorkflowStatus):
        """Update workflow status in DB."""
        from datetime import datetime

        update_data = {"status": status.value}
        if status == DBWorkflowStatus.RUNNING:
            update_data["started_at"] = datetime.utcnow()
        elif status in (DBWorkflowStatus.COMPLETED, DBWorkflowStatus.FAILED):
            update_data["completed_at"] = datetime.utcnow()

        stmt = update(WorkflowModel).where(WorkflowModel.id == workflow_id).values(**update_data)
        await self.db.execute(stmt)
        await self.db.commit()

    async def _emit_event(
        self,
        event_type: str,
        workflow_id: str = None,
        task_id: str = None,
        agent_id: str = None,
        message: str = "",
        meta_data: Optional[Dict[str, Any]] = None,
    ):
        """Emit an execution event."""
        if self.event_callback:
            event = ExecutionEvent(
                event_type=event_type,
                workflow_id=workflow_id,
                task_id=task_id,
                agent_id=agent_id,
                message=message,
                meta_data=meta_data,
            )
            await self.event_callback(event)
