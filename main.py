"""
Main FastAPI application for Multi-Agent Development Platform

This is the main entry point for the API server that coordinates
agent interactions and provides HTTP endpoints for the web interface.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

from src.config.settings import settings
from src.core.message_bus import message_bus
from src.agents.developer_agent import DeveloperAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.api.routes import router
from src.api.websocket import websocket_router


# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("multi_agent_platform")


# Global agent instances
agents: Dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Multi-Agent Development Platform")
    
    try:
        # Initialize message bus
        await message_bus.connect()
        logger.info("Message bus connected")
        
        # Initialize agents
        developer_agent = DeveloperAgent()
        reviewer_agent = ReviewerAgent()
        
        # Store agents globally
        agents["developer"] = developer_agent
        agents["reviewer"] = reviewer_agent
        
        logger.info("Agents initialized successfully")
        
        # Register agents with message bus
        # This would be implemented when we add the message handling
        
        logger.info("Multi-Agent Development Platform started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down Multi-Agent Development Platform")
        
        try:
            await message_bus.disconnect()
            logger.info("Message bus disconnected")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="Multi-Agent Development Platform",
    description="AI-powered collaborative development platform using specialized agents",
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1")
app.include_router(websocket_router, prefix="/ws")

# Serve static files (for web interface)
try:
    app.mount("/static", StaticFiles(directory="web/static"), name="static")
except RuntimeError:
    # Static directory doesn't exist yet
    pass


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint - serves basic dashboard"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Multi-Agent Development Platform</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; text-align: center; }
            .status { background: #e8f5e8; padding: 15px; border-radius: 5px; margin: 20px 0; }
            .agents { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }
            .agent { background: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #007bff; }
            .endpoints { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }
            a { color: #007bff; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Multi-Agent Development Platform</h1>
            
            <div class="status">
                <h3>✅ System Status: Online</h3>
                <p>The Multi-Agent Development Platform is running successfully!</p>
            </div>
            
            <div class="agents">
                <div class="agent">
                    <h4>👨‍💻 Developer Agent</h4>
                    <p>Specialized in code generation, architecture design, and full-stack development.</p>
                </div>
                <div class="agent">
                    <h4>🔍 Reviewer Agent</h4>
                    <p>Focuses on code review, security analysis, and quality assurance.</p>
                </div>
            </div>
            
            <div class="endpoints">
                <h3>🔗 Available Endpoints</h3>
                <ul>
                    <li><a href="/docs">📚 API Documentation (Swagger UI)</a></li>
                    <li><a href="/redoc">📖 API Documentation (ReDoc)</a></li>
                    <li><a href="/api/v1/health">❤️ Health Check</a></li>
                    <li><a href="/api/v1/agents/status">📊 Agent Status</a></li>
                </ul>
            </div>
            
            <div class="endpoints">
                <h3>🚀 Getting Started</h3>
                <ol>
                    <li>Visit the <a href="/docs">API Documentation</a> to explore available endpoints</li>
                    <li>Use the <code>/api/v1/tasks/submit</code> endpoint to submit development tasks</li>
                    <li>Check <code>/api/v1/agents/status</code> to monitor agent performance</li>
                    <li>Access WebSocket endpoint at <code>/ws</code> for real-time updates</li>
                </ol>
            </div>
        </div>
    </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check message bus connection
        if message_bus.redis_client:
            await message_bus.redis_client.ping()
            message_bus_status = "healthy"
        else:
            message_bus_status = "disconnected"
        
        # Check agents status
        agent_statuses = {}
        for name, agent in agents.items():
            try:
                status = await agent.health_check()
                agent_statuses[name] = status["status"]
            except Exception as e:
                agent_statuses[name] = f"unhealthy: {str(e)}"
        
        return {
            "status": "healthy",
            "timestamp": "2025-07-22T00:00:00Z",
            "version": settings.app_version,
            "environment": settings.environment,
            "components": {
                "message_bus": message_bus_status,
                "agents": agent_statuses
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )