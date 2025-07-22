"""
CrewAI-based Task Coordination System

This module provides the main coordination logic for multi-agent collaboration
using CrewAI's Crew functionality to orchestrate complex development workflows.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum

from crewai import Crew, Task, Process
from pydantic import BaseModel, Field

from ..config.settings import settings
from ..agents.developer_agent import DeveloperAgent
from ..agents.reviewer_agent import ReviewerAgent
from ..core.base_agent import TaskResult
from ..core.message_bus import message_bus, MessageType


class WorkflowType(str, Enum):
    """Types of development workflows"""
    SIMPLE_DEVELOPMENT = "simple_development"
    CODE_REVIEW_WORKFLOW = "code_review_workflow"
    FULL_DEVELOPMENT_CYCLE = "full_development_cycle"
    ARCHITECTURE_DESIGN = "architecture_design"
    BUG_FIX_WORKFLOW = "bug_fix_workflow"
    REFACTORING_WORKFLOW = "refactoring_workflow"


class WorkflowStatus(str, Enum):
    """Status of workflow execution"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowRequest(BaseModel):
    """Request for workflow execution"""
    workflow_type: WorkflowType
    description: str = Field(..., description="Description of what to accomplish")
    requirements: List[str] = Field(default_factory=list, description="Specific requirements")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    priority: int = Field(default=5, ge=1, le=10, description="Workflow priority")
    timeout: Optional[int] = Field(default=300, description="Timeout in seconds")


class WorkflowResult(BaseModel):
    """Result of workflow execution"""
    workflow_id: str
    workflow_type: WorkflowType
    status: WorkflowStatus
    results: Dict[str, Any] = Field(default_factory=dict)
    agent_results: Dict[str, TaskResult] = Field(default_factory=dict)
    execution_time: Optional[float] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CrewCoordinator:
    """
    Main coordinator for multi-agent workflows using CrewAI
    
    This class manages the creation and execution of CrewAI crews,
    coordinates agent interactions, and handles complex development workflows.
    """
    
    def __init__(self):
        self.logger = logging.getLogger("crew_coordinator")
        self.active_workflows: Dict[str, WorkflowResult] = {}
        self.agents: Dict[str, Any] = {}
        self.crews: Dict[str, Crew] = {}
        
        # Initialize agents
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize all available agents"""
        try:
            self.agents["developer"] = DeveloperAgent(agent_id="crew_developer_001")
            self.agents["reviewer"] = ReviewerAgent(agent_id="crew_reviewer_001")
            self.logger.info("Agents initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize agents: {e}")
            raise
    
    async def execute_workflow(self, request: WorkflowRequest) -> WorkflowResult:
        """
        Execute a multi-agent workflow
        
        Args:
            request: Workflow request with type and parameters
            
        Returns:
            WorkflowResult: Result of workflow execution
        """
        workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Initialize workflow result
        workflow_result = WorkflowResult(
            workflow_id=workflow_id,
            workflow_type=request.workflow_type,
            status=WorkflowStatus.PENDING,
            started_at=datetime.now()
        )
        
        self.active_workflows[workflow_id] = workflow_result
        
        try:
            self.logger.info(f"Starting workflow {workflow_id}: {request.workflow_type}")
            
            # Route to appropriate workflow handler
            if request.workflow_type == WorkflowType.SIMPLE_DEVELOPMENT:
                result = await self._execute_simple_development(workflow_id, request)
            elif request.workflow_type == WorkflowType.CODE_REVIEW_WORKFLOW:
                result = await self._execute_code_review_workflow(workflow_id, request)
            elif request.workflow_type == WorkflowType.FULL_DEVELOPMENT_CYCLE:
                result = await self._execute_full_development_cycle(workflow_id, request)
            elif request.workflow_type == WorkflowType.ARCHITECTURE_DESIGN:
                result = await self._execute_architecture_design(workflow_id, request)
            elif request.workflow_type == WorkflowType.BUG_FIX_WORKFLOW:
                result = await self._execute_bug_fix_workflow(workflow_id, request)
            elif request.workflow_type == WorkflowType.REFACTORING_WORKFLOW:
                result = await self._execute_refactoring_workflow(workflow_id, request)
            else:
                raise ValueError(f"Unknown workflow type: {request.workflow_type}")
            
            # Update workflow result
            workflow_result.status = WorkflowStatus.COMPLETED
            workflow_result.results = result
            workflow_result.completed_at = datetime.now()
            workflow_result.execution_time = (workflow_result.completed_at - workflow_result.started_at).total_seconds()
            
            self.logger.info(f"Workflow {workflow_id} completed successfully")
            
        except Exception as e:
            workflow_result.status = WorkflowStatus.FAILED
            workflow_result.error_message = str(e)
            workflow_result.completed_at = datetime.now()
            workflow_result.execution_time = (workflow_result.completed_at - workflow_result.started_at).total_seconds()
            
            self.logger.error(f"Workflow {workflow_id} failed: {e}")
        
        return workflow_result
    
    async def _execute_simple_development(self, workflow_id: str, request: WorkflowRequest) -> Dict[str, Any]:
        """Execute simple development workflow (single agent)"""
        self.logger.info(f"Executing simple development workflow: {workflow_id}")
        
        # Create CrewAI task
        development_task = Task(
            description=request.description,
            agent=self.agents["developer"].crew_agent,
            expected_output="Complete implementation with code and documentation"
        )
        
        # Create and execute crew
        crew = Crew(
            agents=[self.agents["developer"].crew_agent],
            tasks=[development_task],
            process=Process.sequential,
            verbose=settings.debug
        )
        
        # Execute crew
        crew_result = crew.kickoff()
        
        return {
            "workflow_type": "simple_development",
            "development_result": str(crew_result),
            "agent_used": "developer",
            "status": "completed"
        }
    
    async def _execute_code_review_workflow(self, workflow_id: str, request: WorkflowRequest) -> Dict[str, Any]:
        """Execute code review workflow"""
        self.logger.info(f"Executing code review workflow: {workflow_id}")
        
        # Extract code from context
        code = request.context.get("code")
        if not code:
            raise ValueError("Code must be provided in context for code review workflow")
        
        # Create review task
        review_task = Task(
            description=f"Review the following code for quality, security, and best practices:\n\n{code}",
            agent=self.agents["reviewer"].crew_agent,
            expected_output="Comprehensive code review with issues and recommendations"
        )
        
        # Create and execute crew
        crew = Crew(
            agents=[self.agents["reviewer"].crew_agent],
            tasks=[review_task],
            process=Process.sequential,
            verbose=settings.debug
        )
        
        crew_result = crew.kickoff()
        
        return {
            "workflow_type": "code_review",
            "review_result": str(crew_result),
            "agent_used": "reviewer",
            "status": "completed"
        }
    
    async def _execute_full_development_cycle(self, workflow_id: str, request: WorkflowRequest) -> Dict[str, Any]:
        """Execute full development cycle (develop → review → iterate)"""
        self.logger.info(f"Executing full development cycle: {workflow_id}")
        
        # Task 1: Development
        development_task = Task(
            description=request.description,
            agent=self.agents["developer"].crew_agent,
            expected_output="Complete implementation with code, tests, and documentation"
        )
        
        # Task 2: Code Review (depends on development)
        review_task = Task(
            description="Review the developed code for quality, security, and best practices. Provide detailed feedback and suggestions for improvement.",
            agent=self.agents["reviewer"].crew_agent,
            expected_output="Comprehensive code review with quality score and recommendations",
            context=[development_task]
        )
        
        # Create crew with both agents
        crew = Crew(
            agents=[
                self.agents["developer"].crew_agent,
                self.agents["reviewer"].crew_agent
            ],
            tasks=[development_task, review_task],
            process=Process.sequential,
            verbose=settings.debug
        )
        
        # Execute crew
        crew_result = crew.kickoff()
        
        return {
            "workflow_type": "full_development_cycle",
            "development_phase": "completed",
            "review_phase": "completed",
            "final_result": str(crew_result),
            "agents_used": ["developer", "reviewer"],
            "status": "completed"
        }
    
    async def _execute_architecture_design(self, workflow_id: str, request: WorkflowRequest) -> Dict[str, Any]:
        """Execute architecture design workflow"""
        self.logger.info(f"Executing architecture design workflow: {workflow_id}")
        
        # Architecture design task
        architecture_task = Task(
            description=f"Design a comprehensive software architecture for: {request.description}. "
                       f"Consider scalability, maintainability, security, and performance. "
                       f"Include component diagrams, API design, and technology recommendations.",
            agent=self.agents["developer"].crew_agent,
            expected_output="Detailed architecture document with diagrams, component specifications, and implementation guide"
        )
        
        # Architecture review task
        review_task = Task(
            description="Review the proposed architecture for potential issues, scalability concerns, "
                       "security vulnerabilities, and adherence to best practices. Provide recommendations.",
            agent=self.agents["reviewer"].crew_agent,
            expected_output="Architecture review with assessment and improvement recommendations",
            context=[architecture_task]
        )
        
        # Create crew
        crew = Crew(
            agents=[
                self.agents["developer"].crew_agent,
                self.agents["reviewer"].crew_agent
            ],
            tasks=[architecture_task, review_task],
            process=Process.sequential,
            verbose=settings.debug
        )
        
        crew_result = crew.kickoff()
        
        return {
            "workflow_type": "architecture_design",
            "architecture_result": str(crew_result),
            "status": "completed"
        }
    
    async def _execute_bug_fix_workflow(self, workflow_id: str, request: WorkflowRequest) -> Dict[str, Any]:
        """Execute bug fix workflow"""
        self.logger.info(f"Executing bug fix workflow: {workflow_id}")
        
        bug_description = request.context.get("bug_description", request.description)
        code_with_bug = request.context.get("code", "")
        
        # Bug analysis and fix task
        fix_task = Task(
            description=f"Analyze and fix the following bug: {bug_description}\n\n"
                       f"Code context: {code_with_bug}\n\n"
                       f"Provide a detailed analysis of the bug, root cause, and implement a fix. "
                       f"Include test cases to prevent regression.",
            agent=self.agents["developer"].crew_agent,
            expected_output="Bug analysis, fix implementation, and test cases"
        )
        
        # Fix verification task
        verification_task = Task(
            description="Review the bug fix to ensure it properly addresses the issue without "
                       "introducing new problems. Verify the test cases are comprehensive.",
            agent=self.agents["reviewer"].crew_agent,
            expected_output="Bug fix verification with quality assessment",
            context=[fix_task]
        )
        
        # Create crew
        crew = Crew(
            agents=[
                self.agents["developer"].crew_agent,
                self.agents["reviewer"].crew_agent
            ],
            tasks=[fix_task, verification_task],
            process=Process.sequential,
            verbose=settings.debug
        )
        
        crew_result = crew.kickoff()
        
        return {
            "workflow_type": "bug_fix",
            "bug_fix_result": str(crew_result),
            "status": "completed"
        }
    
    async def _execute_refactoring_workflow(self, workflow_id: str, request: WorkflowRequest) -> Dict[str, Any]:
        """Execute code refactoring workflow"""
        self.logger.info(f"Executing refactoring workflow: {workflow_id}")
        
        original_code = request.context.get("code", "")
        refactor_goals = request.context.get("refactor_goals", [])
        
        # Refactoring task
        refactor_task = Task(
            description=f"Refactor the following code to improve: {', '.join(refactor_goals)}.\n\n"
                       f"Original code:\n{original_code}\n\n"
                       f"Goals: {request.description}\n\n"
                       f"Maintain functionality while improving code quality, readability, and maintainability.",
            agent=self.agents["developer"].crew_agent,
            expected_output="Refactored code with explanations of changes and improvements"
        )
        
        # Refactoring review task
        review_task = Task(
            description="Review the refactored code to ensure improvements were made without "
                       "breaking functionality. Verify that refactoring goals were achieved.",
            agent=self.agents["reviewer"].crew_agent,
            expected_output="Refactoring quality assessment with recommendations",
            context=[refactor_task]
        )
        
        # Create crew
        crew = Crew(
            agents=[
                self.agents["developer"].crew_agent,
                self.agents["reviewer"].crew_agent
            ],
            tasks=[refactor_task, review_task],
            process=Process.sequential,
            verbose=settings.debug
        )
        
        crew_result = crew.kickoff()
        
        return {
            "workflow_type": "refactoring",
            "refactoring_result": str(crew_result),
            "status": "completed"
        }
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowResult]:
        """Get status of a specific workflow"""
        return self.active_workflows.get(workflow_id)
    
    async def list_active_workflows(self) -> List[WorkflowResult]:
        """List all active workflows"""
        return [w for w in self.active_workflows.values() if w.status == WorkflowStatus.RUNNING]
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow"""
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            if workflow.status == WorkflowStatus.RUNNING:
                workflow.status = WorkflowStatus.CANCELLED
                workflow.completed_at = datetime.now()
                self.logger.info(f"Workflow {workflow_id} cancelled")
                return True
        return False
    
    async def cleanup_completed_workflows(self, max_history: int = 100):
        """Clean up old completed workflows"""
        completed_workflows = [
            (wid, w) for wid, w in self.active_workflows.items() 
            if w.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED]
        ]
        
        if len(completed_workflows) > max_history:
            # Keep only the most recent workflows
            sorted_workflows = sorted(completed_workflows, key=lambda x: x[1].completed_at or x[1].started_at, reverse=True)
            to_remove = sorted_workflows[max_history:]
            
            for workflow_id, _ in to_remove:
                del self.active_workflows[workflow_id]
            
            self.logger.info(f"Cleaned up {len(to_remove)} old workflows")


# Global coordinator instance
crew_coordinator = CrewCoordinator()