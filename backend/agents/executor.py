"""
Backward compatibility shim.
The original executor.py was renamed to executor_v1.py.
This module re-exports the v1 executor for existing code.
"""
from agents.executor_v1 import AgentExecutor, AgentState

__all__ = ["AgentExecutor", "AgentState"]
