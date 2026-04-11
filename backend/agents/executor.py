import asyncio
import json
import re
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from models.execution import AgentModel, TaskModel, WorkflowModel, ExecutionLogModel
from schemas import TaskStatus, WorkflowStatus, ExecutionEvent


class AgentState(dict):
    workflow_id: str
    task_id: str
    agent_id: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    error: Optional[str]
    messages: List[Any]
    step: int


class AgentExecutor:
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

    def _get_llm(self, agent: AgentModel) -> Any:
        cache_key = f"{agent.id}"
        if cache_key in self._provider_cache:
            return self._provider_cache[cache_key]

        from agents.providers import load_provider_from_agent
        provider = load_provider_from_agent(
            agent_model_name=agent.model_name or "MiniMax-M2.7",
            agent_provider=agent.model_provider or "minimax",
            agent_config=agent.config or {},
            env_vars=self.env_vars,
        )
        self._provider_cache[cache_key] = provider
        return provider

    async def _execute_agent_task(self, state: AgentState) -> AgentState:
        task_id = state["task_id"]
        agent_id = state["agent_id"]

        await self._update_task_status(task_id, TaskStatus.RUNNING)
        await self._emit_event(
            event_type="task_started",
            task_id=task_id,
            agent_id=agent_id,
            message=f"Task {task_id} started execution"
        )

        try:
            result = await self._run_agent(agent_id, state["input_data"])

            state["output_data"] = result
            state["error"] = None

            await self._update_task_status(task_id, TaskStatus.COMPLETED, output=result)
            await self._emit_event(
                event_type="task_completed",
                task_id=task_id,
                agent_id=agent_id,
                message=f"Task {task_id} completed successfully"
            )
        except Exception as e:
            state["error"] = str(e)
            state["output_data"] = {}

            await self._update_task_status(task_id, TaskStatus.FAILED, error=str(e))
            await self._emit_event(
                event_type="task_failed",
                task_id=task_id,
                agent_id=agent_id,
                message=f"Task {task_id} failed: {str(e)}",
                meta_data={"error": str(e)}
            )

        return state

    async def _run_agent(self, agent_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        stmt = select(AgentModel).where(AgentModel.id == agent_id)
        result = await self.db.execute(stmt)
        agent = result.scalar_one_or_none()

        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        provider = self._get_llm(agent)

        # Simple input sanitization
        sanitized_prompt = agent.system_prompt.replace("{", "{{").replace("}", "}}")
        system_msg = SystemMessage(content=sanitized_prompt)

        user_content = self._format_input(input_data)

        response = await provider.ainvoke([system_msg, HumanMessage(content=user_content)])

        output_text = response.content if hasattr(response, 'content') else str(response)

        return self._parse_output(output_text)

    def _format_input(self, input_data: Dict[str, Any]) -> str:
        if isinstance(input_data, dict):
            parts = []
            for key, value in input_data.items():
                parts.append(f"{key}: {json.dumps(value, indent=2)}")
            return "\n\n".join(parts)
        return str(input_data)

    def _parse_output(self, output: str) -> Dict[str, Any]:
        try:
            # Find the first '{' and last '}' to handle nested objects
            start_idx = output.find('{')
            end_idx = output.rfind('}')
            if start_idx != -1 and end_idx != -1:
                return json.loads(output[start_idx:end_idx + 1])
        except json.JSONDecodeError:
            pass

        return {
            "result": output,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        output: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        update_data = {"status": status.value}
        if status == TaskStatus.RUNNING:
            update_data["started_at"] = datetime.utcnow()
        elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            update_data["completed_at"] = datetime.utcnow()
        if output is not None:
            update_data["output"] = output
        if error is not None:
            update_data["error"] = error

        stmt = update(TaskModel).where(TaskModel.id == task_id).values(**update_data)
        await self.db.execute(stmt)
        await self.db.commit()

    async def _emit_event(
        self,
        event_type: str,
        workflow_id: str = None,
        task_id: str = None,
        agent_id: str = None,
        message: str = "",
        meta_data: Optional[Dict[str, Any]] = None
    ):
        if self.event_callback:
            event = ExecutionEvent(
                event_type=event_type,
                workflow_id=workflow_id,
                task_id=task_id,
                agent_id=agent_id,
                message=message,
                meta_data=meta_data
            )
            await self.event_callback(event)

    def build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("execute_task", self._execute_agent_task)
        workflow.set_entry_point("execute_task")
        workflow.add_edge("execute_task", END)

        return workflow.compile(checkpointer=MemorySaver())

    async def execute_workflow(
        self,
        workflow_id: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        stmt = select(WorkflowModel).where(WorkflowModel.id == workflow_id)
        result = await self.db.execute(stmt)
        workflow = result.scalar_one_or_none()

        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        await self._update_workflow_status(workflow_id, WorkflowStatus.RUNNING)
        await self._emit_event(
            event_type="workflow_started",
            workflow_id=workflow_id,
            message=f"Workflow {workflow_id} started"
        )

        stmt_tasks = select(TaskModel).where(
            TaskModel.workflow_id == workflow_id
        ).order_by(TaskModel.priority.desc())

        result_tasks = await self.db.execute(stmt_tasks)
        tasks = result_tasks.scalars().all()

        # Auto-create tasks from workflow's agent_ids if none exist
        if not tasks and workflow.agent_ids:
            for agent_id in workflow.agent_ids:
                task_model = TaskModel(
                    workflow_id=workflow_id,
                    agent_id=agent_id,
                    title=f"Task for agent {agent_id}",
                    input_data={},
                    status="pending",
                )
                self.db.add(task_model)
            await self.db.commit()
            result_tasks = await self.db.execute(stmt_tasks)
            tasks = result_tasks.scalars().all()

        results = {}
        task_outputs = {}

        for task in tasks:
            if task.dependencies:
                deps_met = all(
                    task_outputs.get(dep_id, {}).get("completed")
                    for dep_id in task.dependencies
                )
                if not deps_met:
                    await self._update_task_status(task.id, TaskStatus.CANCELLED)
                    continue

            task_input = {**task.input_data, **input_data}

            graph = self.build_graph()

            initial_state = AgentState(
                workflow_id=workflow_id,
                task_id=task.id,
                agent_id=task.agent_id,
                input_data=task_input,
                output_data={},
                error=None,
                messages=[],
                step=0
            )

            try:
                final_state = await graph.ainvoke(
                    initial_state,
                    config={"configurable": {"thread_id": f"{workflow_id}_{task.id}"}}
                )

                task_outputs[task.id] = {
                    "completed": True,
                    "output": final_state.get("output_data", {})
                }
                results[task.id] = final_state.get("output_data", {})

            except Exception as e:
                task_outputs[task.id] = {"completed": False, "error": str(e)}
                results[task.id] = {"error": str(e)}

        await self._update_workflow_status(workflow_id, WorkflowStatus.COMPLETED)

        # Persist aggregated task_results to the workflow so frontend can show them
        workflow_update = update(WorkflowModel).where(
            WorkflowModel.id == workflow_id
        ).values(output={"task_results": results})
        await self.db.execute(workflow_update)
        await self.db.commit()

        await self._emit_event(
            event_type="workflow_completed",
            workflow_id=workflow_id,
            message=f"Workflow {workflow_id} completed"
        )

        return {
            "workflow_id": workflow_id,
            "status": "completed",
            "task_results": results
        }

    async def _update_workflow_status(self, workflow_id: str, status: WorkflowStatus):
        update_data = {"status": status.value}
        if status == WorkflowStatus.RUNNING:
            update_data["started_at"] = datetime.utcnow()
        elif status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED):
            update_data["completed_at"] = datetime.utcnow()

        stmt = update(WorkflowModel).where(WorkflowModel.id == workflow_id).values(**update_data)
        await self.db.execute(stmt)
        await self.db.commit()
