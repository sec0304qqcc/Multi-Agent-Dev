"""
Configuration management for Multi-Agent Development Platform
"""
import os
from typing import Optional, List, Dict, Any
try:
    from pydantic_settings import BaseSettings
    from pydantic import validator
except ImportError:
    from pydantic import BaseSettings, validator
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # =============================================================================
    # Application Settings
    # =============================================================================
    app_name: str = "Multi-Agent Development Platform"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    
    # =============================================================================
    # Security Settings
    # =============================================================================
    secret_key: str = "your-super-secret-key-change-in-production"
    jwt_secret: str = "your-jwt-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 3600
    
    # =============================================================================
    # Database Configuration
    # =============================================================================
    postgres_db: str = "multi_agent_dev"
    postgres_user: str = "agent_user"
    postgres_password: str = "secure_password_change_me"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: Optional[str] = None
    
    @validator('database_url', pre=True, always=True)
    def assemble_database_url(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if isinstance(v, str):
            return v
        return f"postgresql://{values.get('postgres_user')}:{values.get('postgres_password')}@{values.get('postgres_host')}:{values.get('postgres_port')}/{values.get('postgres_db')}"
    
    # =============================================================================
    # Redis Configuration
    # =============================================================================
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0
    redis_url: Optional[str] = None
    
    @validator('redis_url', pre=True, always=True)
    def assemble_redis_url(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if isinstance(v, str):
            return v
        password = values.get('redis_password')
        if password:
            return f"redis://:{password}@{values.get('redis_host')}:{values.get('redis_port')}/{values.get('redis_db')}"
        return f"redis://{values.get('redis_host')}:{values.get('redis_port')}/{values.get('redis_db')}"
    
    # =============================================================================
    # LLM API Configuration
    # =============================================================================
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    
    # Default LLM Models
    default_llm_model: str = "claude-3-sonnet-20240229"
    fallback_llm_model: str = "gpt-3.5-turbo"
    local_llm_model: str = "codellama:7b"
    
    # =============================================================================
    # Agent Configuration
    # =============================================================================
    agent_timeout: int = 300
    max_concurrent_agents: int = 5
    agent_retry_attempts: int = 3
    
    # Cost Control
    monthly_budget_usd: float = 140.0
    cost_alert_threshold: float = 0.8
    enable_cost_control: bool = True
    
    # =============================================================================
    # Development Settings
    # =============================================================================
    dev_mode: bool = True
    hot_reload: bool = True
    mock_llm_responses: bool = False
    
    # Testing Settings
    test_database_url: str = "sqlite:///test.db"
    run_integration_tests: bool = False
    
    # =============================================================================
    # VS Code Integration
    # =============================================================================
    vscode_integration: bool = True
    claude_code_webhook_port: int = 8001
    claude_code_api_url: str = "http://localhost:8001/api"
    
    # =============================================================================
    # Monitoring and Metrics
    # =============================================================================
    prometheus_port: int = 9090
    enable_metrics: bool = True
    grafana_port: int = 3000
    grafana_password: str = "admin"
    
    # =============================================================================
    # External Services
    # =============================================================================
    # n8n Workflow Automation
    n8n_port: int = 5678
    n8n_user: str = "admin" 
    n8n_password: str = "admin"
    
    # Webhook Settings
    webhook_url: str = "http://localhost:8000/webhooks"
    webhook_secret: str = "your-webhook-secret"
    
    # =============================================================================
    # File Storage and Paths
    # =============================================================================
    storage_backend: str = "local"
    storage_path: str = "./storage"
    workspace_path: str = "./workspace"
    logs_path: str = "./logs"
    
    # =============================================================================
    # Feature Flags
    # =============================================================================
    enable_advanced_features: bool = False
    enable_experimental_agents: bool = False
    enable_telemetry: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Environment variable prefixes
        env_prefix = ""
        
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment.lower() in ("development", "dev")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.environment.lower() in ("production", "prod")
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode"""
        return self.environment.lower() in ("testing", "test")


class AgentConfig:
    """Agent-specific configuration"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        
    @property
    def developer_agent_config(self) -> Dict[str, Any]:
        """Configuration for Developer Agent"""
        return {
            "role": "Senior Full-Stack Developer",
            "goal": "Write high-quality, maintainable code following best practices",
            "backstory": """
            You are an expert software developer with 10+ years of experience in full-stack development.
            You specialize in clean code, architecture design, and modern development practices.
            You always consider security, performance, and maintainability in your solutions.
            """,
            "verbose": self.settings.debug,
            "allow_delegation": True,
            "max_iter": 3,
            "memory": True
        }
    
    @property
    def reviewer_agent_config(self) -> Dict[str, Any]:
        """Configuration for Reviewer Agent"""
        return {
            "role": "Code Quality Specialist",
            "goal": "Ensure code quality, security, and adherence to best practices",
            "backstory": """
            You are a senior code reviewer with expertise in security analysis, performance optimization,
            and clean architecture principles. You have a keen eye for potential bugs, security vulnerabilities,
            and code smells. You provide constructive feedback to improve code quality.
            """,
            "verbose": self.settings.debug,
            "allow_delegation": False,
            "max_iter": 2,
            "memory": True
        }


class DatabaseConfig:
    """Database connection configuration"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
    
    @property
    def database_config(self) -> Dict[str, Any]:
        """SQLAlchemy database configuration"""
        return {
            "url": self.settings.database_url,
            "echo": self.settings.debug,
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 3600
        }


class RedisConfig:
    """Redis connection configuration"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
    
    @property
    def redis_config(self) -> Dict[str, Any]:
        """Redis client configuration"""
        return {
            "host": self.settings.redis_host,
            "port": self.settings.redis_port,
            "password": self.settings.redis_password if self.settings.redis_password else None,
            "db": self.settings.redis_db,
            "decode_responses": True,
            "socket_timeout": 5,
            "socket_connect_timeout": 5,
            "health_check_interval": 30
        }


# Global settings instance
settings = Settings()

# Configuration helpers
agent_config = AgentConfig(settings)
database_config = DatabaseConfig(settings)
redis_config = RedisConfig(settings)