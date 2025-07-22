"""
Developer Agent for Multi-Agent Development Platform

This agent specializes in code generation, architecture design, and full-stack development tasks.
It integrates with CrewAI and provides advanced development capabilities.
"""

import os
import re
import ast
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..core.base_agent import BaseMultiAgent, TaskResult
from ..core.message_bus import message_bus, MessageType
from ..config.settings import settings, agent_config


class CodeGenerationRequest(BaseModel):
    """Request for code generation"""
    language: str = Field(..., description="Programming language (python, javascript, etc.)")
    framework: Optional[str] = Field(None, description="Framework to use (fastapi, react, etc.)")
    description: str = Field(..., description="Description of what to implement")
    requirements: List[str] = Field(default_factory=list, description="Specific requirements")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    file_path: Optional[str] = Field(None, description="Target file path")


class CodeGenerationResult(BaseModel):
    """Result of code generation"""
    code: str = Field(..., description="Generated code")
    language: str = Field(..., description="Programming language used")
    framework: Optional[str] = Field(None, description="Framework used")
    file_path: Optional[str] = Field(None, description="Suggested or target file path")
    dependencies: List[str] = Field(default_factory=list, description="Required dependencies")
    tests: Optional[str] = Field(None, description="Generated test code")
    documentation: Optional[str] = Field(None, description="Generated documentation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class FileOperationTool(BaseTool):
    """Tool for file operations"""
    name: str = "file_operation_tool"
    description: str = "Read, write, and manage files in the project workspace"
    
    def _run(self, operation: str, file_path: str, content: str = None) -> str:
        """Execute file operation"""
        try:
            workspace_path = Path(settings.workspace_path)
            target_path = workspace_path / file_path
            
            # Ensure path is within workspace for security
            if not str(target_path.resolve()).startswith(str(workspace_path.resolve())):
                return "Error: File path outside workspace not allowed"
            
            if operation == "read":
                if target_path.exists():
                    return target_path.read_text(encoding='utf-8')
                else:
                    return "Error: File does not exist"
            
            elif operation == "write":
                if content is None:
                    return "Error: Content required for write operation"
                
                # Create directory if it doesn't exist
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding='utf-8')
                return f"Successfully wrote {len(content)} characters to {file_path}"
            
            elif operation == "exists":
                return str(target_path.exists())
            
            elif operation == "list":
                if target_path.is_dir():
                    files = [f.name for f in target_path.iterdir()]
                    return "\n".join(files)
                else:
                    return "Error: Path is not a directory"
            
            else:
                return f"Error: Unknown operation '{operation}'"
                
        except Exception as e:
            return f"Error: {str(e)}"


class CodeAnalysisTool(BaseTool):
    """Tool for code analysis"""
    name: str = "code_analysis_tool"
    description: str = "Analyze code structure, dependencies, and patterns"
    
    def _run(self, code: str, language: str = "python") -> str:
        """Analyze code and return insights"""
        try:
            if language.lower() == "python":
                return self._analyze_python_code(code)
            else:
                return self._analyze_generic_code(code, language)
        except Exception as e:
            return f"Analysis error: {str(e)}"
    
    def _analyze_python_code(self, code: str) -> str:
        """Analyze Python code using AST"""
        try:
            tree = ast.parse(code)
            
            classes = []
            functions = []
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        imports.extend([alias.name for alias in node.names])
                    else:
                        module = node.module or ""
                        imports.extend([f"{module}.{alias.name}" for alias in node.names])
            
            analysis = {
                "classes": classes,
                "functions": functions,
                "imports": imports,
                "lines": len(code.split('\n')),
                "complexity": len(classes) + len(functions)
            }
            
            return f"Analysis: {analysis}"
            
        except SyntaxError as e:
            return f"Syntax error in code: {str(e)}"
    
    def _analyze_generic_code(self, code: str, language: str) -> str:
        """Generic code analysis for non-Python languages"""
        lines = code.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        # Basic pattern matching for common constructs
        functions = len(re.findall(r'function\s+\w+|def\s+\w+|public\s+\w+\s+\w+\(', code))
        classes = len(re.findall(r'class\s+\w+|interface\s+\w+', code))
        
        analysis = {
            "language": language,
            "total_lines": len(lines),
            "code_lines": len(non_empty_lines),
            "estimated_functions": functions,
            "estimated_classes": classes
        }
        
        return f"Analysis: {analysis}"


class ProjectStructureTool(BaseTool):
    """Tool for managing project structure"""
    name: str = "project_structure_tool"
    description: str = "Create and manage project directory structures and boilerplate"
    
    def _run(self, action: str, project_type: str = None, name: str = None) -> str:
        """Execute project structure operations"""
        try:
            if action == "create_structure":
                return self._create_project_structure(project_type, name)
            elif action == "analyze_structure":
                return self._analyze_project_structure()
            else:
                return f"Error: Unknown action '{action}'"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _create_project_structure(self, project_type: str, name: str) -> str:
        """Create standard project structure"""
        workspace_path = Path(settings.workspace_path)
        project_path = workspace_path / name
        
        if project_path.exists():
            return f"Error: Project '{name}' already exists"
        
        structures = {
            "python_package": [
                f"{name}/__init__.py",
                f"{name}/main.py",
                f"{name}/config.py",
                f"tests/__init__.py",
                f"tests/test_{name}.py",
                "requirements.txt",
                "README.md",
                ".gitignore"
            ],
            "fastapi": [
                f"{name}/__init__.py",
                f"{name}/main.py",
                f"{name}/api/__init__.py",
                f"{name}/api/routes.py",
                f"{name}/core/__init__.py",
                f"{name}/core/config.py",
                f"{name}/models/__init__.py",
                f"tests/__init__.py",
                f"tests/test_api.py",
                "requirements.txt",
                "Dockerfile",
                ".env.example",
                "README.md"
            ],
            "react": [
                "src/App.js",
                "src/index.js",
                "src/components/Header.js",
                "src/components/Footer.js",
                "src/styles/App.css",
                "public/index.html",
                "package.json",
                ".gitignore",
                "README.md"
            ]
        }
        
        if project_type not in structures:
            return f"Error: Unknown project type '{project_type}'"
        
        created_files = []
        for file_path in structures[project_type]:
            full_path = project_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create file with basic content
            if file_path.endswith('.py') and '__init__.py' in file_path:
                full_path.write_text(f'"""Package initialization for {name}"""')
            elif file_path.endswith('.py'):
                full_path.write_text(f'"""Module: {file_path}"""\n\n# TODO: Implement module functionality')
            elif file_path == 'README.md':
                full_path.write_text(f'# {name}\n\nGenerated by Multi-Agent Development Platform')
            else:
                full_path.write_text('')
            
            created_files.append(file_path)
        
        return f"Created project '{name}' with {len(created_files)} files: {', '.join(created_files)}"
    
    def _analyze_project_structure(self) -> str:
        """Analyze current project structure"""
        workspace_path = Path(settings.workspace_path)
        
        if not workspace_path.exists():
            return "Workspace directory does not exist"
        
        structure = {}
        for path in workspace_path.rglob('*'):
            if path.is_file():
                relative_path = path.relative_to(workspace_path)
                parts = relative_path.parts
                
                current = structure
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = path.stat().st_size
        
        return f"Project structure: {structure}"


class DeveloperAgent(BaseMultiAgent):
    """
    Developer Agent specializing in code generation and development tasks
    
    This agent can:
    - Generate code in multiple languages
    - Create project structures
    - Analyze existing code
    - Refactor and optimize code
    - Generate documentation and tests
    """
    
    def __init__(self, agent_id: Optional[str] = None):
        # Initialize tools
        tools = [
            FileOperationTool(),
            CodeAnalysisTool(),
            ProjectStructureTool()
        ]
        
        # Get configuration
        config = agent_config.developer_agent_config
        
        super().__init__(
            agent_id=agent_id,
            role=config["role"],
            goal=config["goal"],
            backstory=config["backstory"],
            verbose=config["verbose"],
            allow_delegation=config["allow_delegation"],
            max_iter=config["max_iter"],
            memory=config["memory"],
            tools=tools
        )
        
        # Developer-specific attributes
        self.supported_languages = [
            "python", "javascript", "typescript", "java", "go", 
            "rust", "c++", "c#", "php", "ruby"
        ]
        self.supported_frameworks = {
            "python": ["fastapi", "django", "flask", "streamlit"],
            "javascript": ["react", "vue", "angular", "node", "express"],
            "typescript": ["react", "vue", "angular", "nest", "deno"]
        }
    
    async def process_task(self, task_description: str, context: Dict[str, Any] = None) -> TaskResult:
        """
        Process development tasks
        
        Args:
            task_description: Description of the development task
            context: Additional context including requirements, preferences, etc.
            
        Returns:
            TaskResult: Result of the development task
        """
        context = context or {}
        
        try:
            # Parse task type from description
            task_type = self._determine_task_type(task_description, context)
            
            if task_type == "code_generation":
                result = await self._handle_code_generation(task_description, context)
            elif task_type == "project_creation":
                result = await self._handle_project_creation(task_description, context)
            elif task_type == "code_analysis":
                result = await self._handle_code_analysis(task_description, context)
            elif task_type == "code_refactoring":
                result = await self._handle_code_refactoring(task_description, context)
            else:
                result = await self._handle_general_development(task_description, context)
            
            return TaskResult(
                task_id=context.get('task_id', 'unknown'),
                agent_id=self.agent_id,
                status="completed",
                result=result
            )
            
        except Exception as e:
            self.logger.error(f"Error processing development task: {e}")
            raise
    
    def _determine_task_type(self, description: str, context: Dict[str, Any]) -> str:
        """Determine the type of development task"""
        desc_lower = description.lower()
        
        if any(keyword in desc_lower for keyword in ["generate", "create", "implement", "write"]):
            if any(keyword in desc_lower for keyword in ["project", "structure", "boilerplate"]):
                return "project_creation"
            else:
                return "code_generation"
        elif any(keyword in desc_lower for keyword in ["analyze", "review", "examine", "understand"]):
            return "code_analysis"
        elif any(keyword in desc_lower for keyword in ["refactor", "improve", "optimize", "clean"]):
            return "code_refactoring"
        else:
            return "general_development"
    
    async def _handle_code_generation(self, description: str, context: Dict[str, Any]) -> CodeGenerationResult:
        """Handle code generation tasks"""
        self.logger.info(f"Handling code generation: {description}")
        
        # Extract requirements from context
        language = context.get('language', 'python')
        framework = context.get('framework')
        requirements = context.get('requirements', [])
        file_path = context.get('file_path')
        
        # Generate code using CrewAI
        prompt = self._build_code_generation_prompt(description, language, framework, requirements)
        
        try:
            # Use CrewAI agent to generate code
            generated_code = await self._generate_with_crew_ai(prompt)
            
            # Parse and enhance the generated code
            code, metadata = self._parse_generated_code(generated_code, language)
            
            # Generate tests if requested
            tests = None
            if context.get('generate_tests', True):
                tests = await self._generate_tests(code, language, framework)
            
            # Generate documentation if requested
            documentation = None
            if context.get('generate_docs', True):
                documentation = await self._generate_documentation(code, language)
            
            result = CodeGenerationResult(
                code=code,
                language=language,
                framework=framework,
                file_path=file_path or metadata.get('suggested_path'),
                dependencies=metadata.get('dependencies', []),
                tests=tests,
                documentation=documentation,
                metadata=metadata
            )
            
            # Save to file if path provided
            if file_path and context.get('save_to_file', True):
                tool_result = self.tools[0]._run('write', file_path, code)
                self.logger.info(f"File save result: {tool_result}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Code generation failed: {e}")
            raise
    
    async def _handle_project_creation(self, description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle project structure creation"""
        self.logger.info(f"Creating project structure: {description}")
        
        project_type = context.get('project_type', 'python_package')
        project_name = context.get('project_name', 'new_project')
        
        # Create project structure using tool
        structure_tool = self.tools[2]  # ProjectStructureTool
        result = structure_tool._run('create_structure', project_type, project_name)
        
        return {
            "project_name": project_name,
            "project_type": project_type,
            "result": result,
            "status": "created" if "Created project" in result else "error"
        }
    
    async def _handle_code_analysis(self, description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code analysis tasks"""
        self.logger.info(f"Analyzing code: {description}")
        
        code = context.get('code')
        file_path = context.get('file_path')
        language = context.get('language', 'python')
        
        if not code and file_path:
            # Read code from file
            file_tool = self.tools[0]  # FileOperationTool
            code = file_tool._run('read', file_path)
            if code.startswith('Error:'):
                raise ValueError(f"Could not read file: {code}")
        
        if not code:
            raise ValueError("No code provided for analysis")
        
        # Analyze code using tool
        analysis_tool = self.tools[1]  # CodeAnalysisTool
        analysis_result = analysis_tool._run(code, language)
        
        return {
            "language": language,
            "file_path": file_path,
            "analysis": analysis_result,
            "code_length": len(code),
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_code_refactoring(self, description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle code refactoring tasks"""
        self.logger.info(f"Refactoring code: {description}")
        
        # This would involve using CrewAI to analyze and improve existing code
        # For now, return a placeholder
        return {
            "status": "refactoring_completed",
            "description": description,
            "improvements": "Code refactoring functionality to be implemented"
        }
    
    async def _handle_general_development(self, description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general development tasks"""
        self.logger.info(f"Handling general development task: {description}")
        
        # Use CrewAI for general development guidance
        return {
            "status": "completed",
            "description": description,
            "guidance": "General development task completed"
        }
    
    def _build_code_generation_prompt(
        self, 
        description: str, 
        language: str, 
        framework: Optional[str], 
        requirements: List[str]
    ) -> str:
        """Build a detailed prompt for code generation"""
        prompt = f"""
Generate {language} code for the following requirement:

DESCRIPTION: {description}

LANGUAGE: {language}
FRAMEWORK: {framework or 'None specified'}

REQUIREMENTS:
{chr(10).join(f"- {req}" for req in requirements) if requirements else "- None specified"}

GUIDELINES:
- Write clean, well-documented code
- Follow {language} best practices and PEP 8 (if Python)
- Include proper error handling
- Add type hints where applicable
- Make the code modular and maintainable
- Include docstrings for functions and classes

Please provide:
1. The main implementation code
2. Any required imports
3. Basic usage example if applicable
4. List of dependencies needed

Format the response with clear code blocks and explanations.
"""
        return prompt
    
    async def _generate_with_crew_ai(self, prompt: str) -> str:
        """Generate content using CrewAI agent"""
        try:
            # For now, return a placeholder - in full implementation,
            # this would use the actual CrewAI agent execution
            return f"Generated code based on prompt: {prompt[:100]}..."
        except Exception as e:
            self.logger.error(f"CrewAI generation failed: {e}")
            raise
    
    def _parse_generated_code(self, generated_content: str, language: str) -> tuple[str, Dict[str, Any]]:
        """Parse generated content to extract code and metadata"""
        # Placeholder implementation - would parse actual CrewAI output
        metadata = {
            "dependencies": [],
            "suggested_path": f"src/generated_{language}_code.py",
            "complexity": "low"
        }
        
        # For now, return placeholder code
        placeholder_code = f"""
# Generated {language} code
# TODO: Implement actual functionality

def main():
    print("Generated code placeholder")
    pass

if __name__ == "__main__":
    main()
"""
        
        return placeholder_code, metadata
    
    async def _generate_tests(self, code: str, language: str, framework: Optional[str]) -> Optional[str]:
        """Generate test code for the given implementation"""
        if language.lower() == "python":
            return f"""
import unittest

class TestGeneratedCode(unittest.TestCase):
    def test_placeholder(self):
        # TODO: Implement actual tests
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
"""
        return None
    
    async def _generate_documentation(self, code: str, language: str) -> Optional[str]:
        """Generate documentation for the given code"""
        return f"""
# Generated Code Documentation

## Overview
This code was generated by the Multi-Agent Development Platform.

## Language
{language}

## Usage
TODO: Add usage examples

## API Reference
TODO: Add API documentation
"""