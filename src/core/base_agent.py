"""
Base Agent class for Multi-Agent Development Platform

This module provides the foundational Agent class that all specialized agents inherit from.
It integrates with CrewAI and provides common functionality for all agents.
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from abc import ABC, abstractmethod

from crewai import Agent
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..config.settings import settings


class TaskResult(BaseModel):
    """Standardized task result format"""
    task_id: str
    agent_id: str
    status: str = Field(..., description="Task status: pending, running, completed, failed")
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    execution_time: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentMetrics(BaseModel):
    """Agent performance metrics"""
    agent_id: str
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    success_rate: float = 0.0
    last_activity: Optional[datetime] = None


class BaseMultiAgent(ABC):
    """
    Base class for all Multi-Agent Development Platform agents
    
    This class provides common functionality and integrates with CrewAI
    while adding our custom features like metrics, logging, and task management.
    """
    
    def __init__(
        self,
        role: str,
        goal: str,
        backstory: str,
        agent_id: Optional[str] = None,
        verbose: bool = None,
        allow_delegation: bool = True,
        max_iter: int = 3,
        memory: bool = True,
        tools: Optional[List[BaseTool]] = None
    ):
        self.agent_id = agent_id or f"{self.__class__.__name__}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.verbose = verbose if verbose is not None else settings.debug
        self.allow_delegation = allow_delegation
        self.max_iter = max_iter
        self.memory = memory
        self.tools = tools or []
        
        # Initialize logging
        self.logger = self._setup_logger()
        
        # Initialize metrics
        self.metrics = AgentMetrics(agent_id=self.agent_id)
        
        # Initialize CrewAI agent
        self.crew_agent = self._create_crew_agent()
        
        # Task tracking
        self.current_tasks: Dict[str, TaskResult] = {}
        self.completed_tasks: List[TaskResult] = []
        
        self.logger.info(f"Agent {self.agent_id} initialized successfully")
    
    def _setup_logger(self) -> logging.Logger:
        """Setup structured logging for the agent"""
        logger = logging.getLogger(f"agent.{self.agent_id}")
        logger.setLevel(getattr(logging, settings.log_level.upper()))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'%(asctime)s - {self.agent_id} - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _create_crew_agent(self) -> Agent:
        """Create and configure the underlying CrewAI agent"""
        try:
            agent = Agent(
                role=self.role,
                goal=self.goal,
                backstory=self.backstory,
                verbose=self.verbose,
                allow_delegation=self.allow_delegation,
                max_iter=self.max_iter,
                memory=self.memory,
                tools=self.tools
            )
            return agent
        except Exception as e:
            self.logger.error(f"Failed to create CrewAI agent: {e}")
            raise
    
    @abstractmethod
    async def process_task(self, task_description: str, context: Dict[str, Any] = None) -> TaskResult:
        """
        Process a task assigned to this agent
        
        Args:
            task_description: Description of the task to perform
            context: Additional context and parameters for the task
            
        Returns:
            TaskResult: The result of task processing
        """
        pass
    
    async def execute_task(self, task_id: str, task_description: str, context: Dict[str, Any] = None) -> TaskResult:
        """
        Execute a task with full lifecycle management
        
        Args:
            task_id: Unique identifier for the task
            task_description: Description of the task to perform
            context: Additional context and parameters for the task
            
        Returns:
            TaskResult: The result of task execution
        """
        start_time = datetime.now()
        context = context or {}
        
        # Initialize task result
        task_result = TaskResult(
            task_id=task_id,
            agent_id=self.agent_id,
            status="running",
            started_at=start_time
        )
        
        # Track current task
        self.current_tasks[task_id] = task_result
        
        self.logger.info(f"Starting task {task_id}: {task_description}")
        
        try:
            # Process the task
            result = await self.process_task(task_description, context)
            
            # Update task result
            completed_at = datetime.now()
            execution_time = (completed_at - start_time).total_seconds()
            
            task_result.status = "completed"
            task_result.result = result.result if isinstance(result, TaskResult) else result
            task_result.completed_at = completed_at
            task_result.execution_time = execution_time
            
            # Update metrics
            self.metrics.tasks_completed += 1
            self.metrics.total_execution_time += execution_time
            self.metrics.average_execution_time = self.metrics.total_execution_time / self.metrics.tasks_completed
            self.metrics.success_rate = self.metrics.tasks_completed / (self.metrics.tasks_completed + self.metrics.tasks_failed)
            self.metrics.last_activity = completed_at
            
            self.logger.info(f"Task {task_id} completed successfully in {execution_time:.2f}s")
            
        except Exception as e:
            # Handle task failure
            completed_at = datetime.now()
            execution_time = (completed_at - start_time).total_seconds()
            
            task_result.status = "failed"
            task_result.error = str(e)
            task_result.completed_at = completed_at
            task_result.execution_time = execution_time
            
            # Update metrics
            self.metrics.tasks_failed += 1
            self.metrics.success_rate = self.metrics.tasks_completed / (self.metrics.tasks_completed + self.metrics.tasks_failed) if (self.metrics.tasks_completed + self.metrics.tasks_failed) > 0 else 0
            self.metrics.last_activity = completed_at
            
            self.logger.error(f"Task {task_id} failed after {execution_time:.2f}s: {e}")
        
        finally:
            # Move to completed tasks
            self.current_tasks.pop(task_id, None)
            self.completed_tasks.append(task_result)
            
            # Limit completed tasks history
            if len(self.completed_tasks) > 100:
                self.completed_tasks = self.completed_tasks[-50:]
        
        return task_result
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status and metrics"""
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "status": "busy" if self.current_tasks else "idle",
            "current_tasks": len(self.current_tasks),
            "metrics": self.metrics.dict(),
            "uptime": datetime.now().isoformat()
        }
    
    def get_task_history(self, limit: int = 10) -> List[TaskResult]:
        """Get recent task history"""
        return self.completed_tasks[-limit:] if self.completed_tasks else []
    
    def add_tool(self, tool: BaseTool) -> None:
        """Add a new tool to the agent's toolkit"""
        self.tools.append(tool)
        # Note: CrewAI agents need to be recreated to add tools
        # In production, this might need a more sophisticated approach
        self.logger.info(f"Added tool {tool.name} to agent {self.agent_id}")
    
    def remove_tool(self, tool_name: str) -> bool:
        """Remove a tool from the agent's toolkit"""
        initial_count = len(self.tools)
        self.tools = [tool for tool in self.tools if tool.name != tool_name]
        removed = len(self.tools) < initial_count
        
        if removed:
            self.logger.info(f"Removed tool {tool_name} from agent {self.agent_id}")
        else:
            self.logger.warning(f"Tool {tool_name} not found in agent {self.agent_id}")
        
        return removed
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the agent"""
        try:
            # Basic health check - can be extended by subclasses
            health_status = {
                "agent_id": self.agent_id,
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "tools_count": len(self.tools),
                "current_tasks": len(self.current_tasks),
                "metrics": self.metrics.dict()
            }
            
            # Check if agent has been inactive for too long
            if self.metrics.last_activity:
                inactive_time = datetime.now() - self.metrics.last_activity
                if inactive_time.total_seconds() > 3600:  # 1 hour
                    health_status["warnings"] = ["Agent has been inactive for over 1 hour"]
            
            return health_status
            
        except Exception as e:
            return {
                "agent_id": self.agent_id,
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.agent_id}, role={self.role})>"