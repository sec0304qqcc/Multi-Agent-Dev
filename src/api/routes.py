"""
API Routes for Multi-Agent Development Platform

This module defines all HTTP endpoints for agent interaction,
task management, and system monitoring.
"""

import asyncio
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field

from ..config.settings import settings
from ..agents.developer_agent import DeveloperAgent, CodeGenerationRequest, CodeGenerationResult
from ..agents.reviewer_agent import ReviewerAgent, ReviewResult
from ..core.base_agent import TaskResult, AgentMetrics


# Pydantic models for API requests/responses
class TaskRequest(BaseModel):
    """Request to submit a task to an agent"""
    agent_type: str = Field(..., description="Type of agent (developer, reviewer)")
    task_description: str = Field(..., description="Description of the task")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    priority: int = Field(default=5, ge=1, le=10, description="Task priority (1=highest)")


class TaskResponse(BaseModel):
    """Response after task submission"""
    task_id: str
    agent_id: str
    status: str
    message: str
    estimated_completion: Optional[str] = None


class AgentStatusResponse(BaseModel):
    """Agent status information"""
    agent_id: str
    role: str
    status: str
    current_tasks: int
    metrics: AgentMetrics
    uptime: str


class SystemStatusResponse(BaseModel):
    """Overall system status"""
    status: str
    timestamp: datetime
    agents: Dict[str, AgentStatusResponse]
    message_bus: str
    active_tasks: int


# Create router
router = APIRouter(
    tags=["Multi-Agent Platform"],
    responses={404: {"description": "Not found"}},
)

# Global storage for agents (in production, this would be managed differently)
agents: Dict[str, Any] = {}


def get_agent(agent_type: str):
    """Get agent instance by type"""
    if agent_type not in agents:
        if agent_type == "developer":
            agents[agent_type] = DeveloperAgent()
        elif agent_type == "reviewer":
            agents[agent_type] = ReviewerAgent()
        else:
            raise HTTPException(status_code=400, detail=f"Unknown agent type: {agent_type}")
    
    return agents[agent_type]


@router.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Detailed health check endpoint"""
    try:
        system_health = {
            "status": "healthy",
            "timestamp": datetime.now(),
            "version": settings.app_version,
            "environment": settings.environment,
            "components": {}
        }
        
        # Check each agent
        for agent_type in ["developer", "reviewer"]:
            try:
                agent = get_agent(agent_type)
                health = await agent.health_check()
                system_health["components"][agent_type] = health["status"]
            except Exception as e:
                system_health["components"][agent_type] = f"unhealthy: {str(e)}"
                system_health["status"] = "degraded"
        
        return system_health
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@router.get("/agents/status", response_model=SystemStatusResponse)
async def get_agents_status():
    """Get status of all agents"""
    try:
        agent_statuses = {}
        total_active_tasks = 0
        
        for agent_type in ["developer", "reviewer"]:
            try:
                agent = get_agent(agent_type)
                status = agent.get_status()
                
                agent_statuses[agent_type] = AgentStatusResponse(
                    agent_id=status["agent_id"],
                    role=agent.role,
                    status=status["status"],
                    current_tasks=status["current_tasks"],
                    metrics=agent.metrics,
                    uptime=status["uptime"]
                )
                
                total_active_tasks += status["current_tasks"]
                
            except Exception as e:
                # Create error status
                agent_statuses[agent_type] = AgentStatusResponse(
                    agent_id=f"{agent_type}_error",
                    role="Unknown",
                    status="error",
                    current_tasks=0,
                    metrics=AgentMetrics(agent_id=f"{agent_type}_error"),
                    uptime=datetime.now().isoformat()
                )
        
        return SystemStatusResponse(
            status="healthy" if all(a.status != "error" for a in agent_statuses.values()) else "degraded",
            timestamp=datetime.now(),
            agents=agent_statuses,
            message_bus="connected",  # TODO: Check actual message bus status
            active_tasks=total_active_tasks
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent status: {str(e)}")


@router.get("/agents/{agent_type}/status", response_model=AgentStatusResponse)
async def get_agent_status(agent_type: str):
    """Get status of a specific agent"""
    try:
        agent = get_agent(agent_type)
        status = agent.get_status()
        
        return AgentStatusResponse(
            agent_id=status["agent_id"],
            role=agent.role,
            status=status["status"],
            current_tasks=status["current_tasks"],
            metrics=agent.metrics,
            uptime=status["uptime"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent status: {str(e)}")


@router.get("/agents/{agent_type}/history", response_model=List[TaskResult])
async def get_agent_history(agent_type: str, limit: int = 10):
    """Get task history for a specific agent"""
    try:
        agent = get_agent(agent_type)
        history = agent.get_task_history(limit)
        return history
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent history: {str(e)}")


@router.post("/tasks/submit", response_model=TaskResponse)
async def submit_task(task_request: TaskRequest, background_tasks: BackgroundTasks):
    """Submit a task to an agent"""
    try:
        # Generate unique task ID
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        # Get the appropriate agent
        agent = get_agent(task_request.agent_type)
        
        # Add task ID to context
        context = task_request.context.copy()
        context["task_id"] = task_id
        
        # Submit task in background
        background_tasks.add_task(
            execute_task_background,
            agent,
            task_id,
            task_request.task_description,
            context
        )
        
        return TaskResponse(
            task_id=task_id,
            agent_id=agent.agent_id,
            status="submitted",
            message="Task submitted successfully and is being processed",
            estimated_completion=None  # TODO: Add estimation logic
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit task: {str(e)}")


@router.get("/tasks/{task_id}/status", response_model=TaskResult)
async def get_task_status(task_id: str):
    """Get status of a specific task"""
    # TODO: Implement task tracking across agents
    # For now, search through all agents
    
    for agent_type in ["developer", "reviewer"]:
        try:
            agent = get_agent(agent_type)
            
            # Check current tasks
            if task_id in agent.current_tasks:
                return agent.current_tasks[task_id]
            
            # Check completed tasks
            for completed_task in agent.completed_tasks:
                if completed_task.task_id == task_id:
                    return completed_task
                    
        except Exception:
            continue
    
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@router.post("/code/generate", response_model=CodeGenerationResult)
async def generate_code(request: CodeGenerationRequest):
    """Generate code using the Developer Agent"""
    try:
        agent = get_agent("developer")
        
        # Convert request to context
        context = {
            "language": request.language,
            "framework": request.framework,
            "requirements": request.requirements,
            "context": request.context,
            "file_path": request.file_path,
            "task_id": f"codegen_{uuid.uuid4().hex[:8]}"
        }
        
        # Execute code generation
        result = await agent.execute_task(
            task_id=context["task_id"],
            task_description=request.description,
            context=context
        )
        
        if result.status == "completed" and isinstance(result.result, CodeGenerationResult):
            return result.result
        else:
            raise HTTPException(status_code=500, detail="Code generation failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code generation failed: {str(e)}")


@router.post("/code/review", response_model=ReviewResult)
async def review_code(
    code: Optional[str] = None,
    file_path: Optional[str] = None,
    language: str = "python",
    review_type: str = "full_review"
):
    """Review code using the Reviewer Agent"""
    try:
        if not code and not file_path:
            raise HTTPException(status_code=400, detail="Either code or file_path must be provided")
        
        agent = get_agent("reviewer")
        
        # Prepare context
        context = {
            "code": code,
            "file_path": file_path,
            "language": language,
            "review_type": review_type,
            "task_id": f"review_{uuid.uuid4().hex[:8]}"
        }
        
        # Execute code review
        result = await agent.execute_task(
            task_id=context["task_id"],
            task_description=f"Perform {review_type} on provided code",
            context=context
        )
        
        if result.status == "completed" and isinstance(result.result, ReviewResult):
            return result.result
        else:
            raise HTTPException(status_code=500, detail="Code review failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Code review failed: {str(e)}")


@router.post("/workflow/develop-and-review")
async def develop_and_review_workflow(
    description: str,
    language: str = "python",
    framework: Optional[str] = None,
    requirements: List[str] = None
):
    """Complete development workflow: generate code then review it"""
    try:
        requirements = requirements or []
        
        # Step 1: Generate code
        developer = get_agent("developer")
        code_context = {
            "language": language,
            "framework": framework,
            "requirements": requirements,
            "task_id": f"workflow_dev_{uuid.uuid4().hex[:8]}"
        }
        
        dev_result = await developer.execute_task(
            task_id=code_context["task_id"],
            task_description=description,
            context=code_context
        )
        
        if dev_result.status != "completed":
            raise HTTPException(status_code=500, detail="Code generation failed")
        
        # Step 2: Review generated code
        reviewer = get_agent("reviewer")
        review_context = {
            "code": dev_result.result.code if hasattr(dev_result.result, 'code') else str(dev_result.result),
            "language": language,
            "task_id": f"workflow_review_{uuid.uuid4().hex[:8]}"
        }
        
        review_result = await reviewer.execute_task(
            task_id=review_context["task_id"],
            task_description="Review generated code for quality and security",
            context=review_context
        )
        
        return {
            "development_result": dev_result,
            "review_result": review_result,
            "workflow_status": "completed",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")


async def execute_task_background(agent, task_id: str, task_description: str, context: Dict[str, Any]):
    """Execute task in background"""
    try:
        result = await agent.execute_task(task_id, task_description, context)
        # TODO: Store result in database or cache for later retrieval
        # TODO: Send notification via WebSocket
        print(f"Background task {task_id} completed: {result.status}")
    except Exception as e:
        print(f"Background task {task_id} failed: {e}")


# Additional utility endpoints
@router.get("/system/info")
async def get_system_info():
    """Get system information"""
    return {
        "platform": "Multi-Agent Development Platform",
        "version": settings.app_version,
        "environment": settings.environment,
        "agent_types": ["developer", "reviewer"],
        "supported_languages": ["python", "javascript", "typescript", "java", "go"],
        "features": [
            "Code generation",
            "Code review",
            "Security analysis",
            "Quality assessment",
            "Style checking",
            "Multi-language support"
        ]
    }