"""
Reviewer Agent for Multi-Agent Development Platform

This agent specializes in code review, quality analysis, security scanning, and best practices enforcement.
It provides comprehensive feedback on code quality and suggests improvements.
"""

import re
import ast
import json
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime
from enum import Enum

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from ..core.base_agent import BaseMultiAgent, TaskResult
from ..core.message_bus import message_bus, MessageType
from ..config.settings import settings, agent_config


class SeverityLevel(str, Enum):
    """Severity levels for code review issues"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategory(str, Enum):
    """Categories of code review issues"""
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    STYLE = "style"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    ARCHITECTURE = "architecture"
    BUG = "bug"


class CodeIssue(BaseModel):
    """Represents a code issue found during review"""
    id: str = Field(default_factory=lambda: f"issue_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
    category: IssueCategory
    severity: SeverityLevel
    title: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None
    references: List[str] = Field(default_factory=list)


class ReviewResult(BaseModel):
    """Result of code review"""
    overall_score: float = Field(..., ge=0, le=10, description="Overall code quality score (0-10)")
    total_issues: int
    issues_by_severity: Dict[SeverityLevel, int] = Field(default_factory=dict)
    issues_by_category: Dict[IssueCategory, int] = Field(default_factory=dict)
    issues: List[CodeIssue] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class SecurityScanTool(BaseTool):
    """Tool for security analysis"""
    name: str = "security_scan_tool"
    description: str = "Scan code for security vulnerabilities and unsafe practices"
    
    def _run(self, code: str, language: str = "python") -> str:
        """Scan code for security issues"""
        try:
            if language.lower() == "python":
                return self._scan_python_security(code)
            else:
                return self._scan_generic_security(code, language)
        except Exception as e:
            return f"Security scan error: {str(e)}"
    
    def _scan_python_security(self, code: str) -> str:
        """Scan Python code for security vulnerabilities"""
        issues = []
        lines = code.split('\n')
        
        # Security patterns to check
        security_patterns = {
            r'eval\s*\(': "Use of eval() is dangerous - arbitrary code execution",
            r'exec\s*\(': "Use of exec() is dangerous - arbitrary code execution", 
            r'import\s+pickle': "Pickle can execute arbitrary code during deserialization",
            r'\.system\s*\(': "os.system() can lead to command injection",
            r'subprocess\.call\s*\([^)]*shell\s*=\s*True': "subprocess with shell=True is vulnerable to injection",
            r'random\.random\(\)': "random module is not cryptographically secure",
            r'md5\s*\(': "MD5 is cryptographically broken",
            r'sha1\s*\(': "SHA1 is cryptographically weak",
            r'password\s*=\s*["\'][^"\']+["\']': "Hardcoded password detected",
            r'secret\s*=\s*["\'][^"\']+["\']': "Hardcoded secret detected",
            r'api_key\s*=\s*["\'][^"\']+["\']': "Hardcoded API key detected"
        }
        
        for i, line in enumerate(lines, 1):
            for pattern, message in security_patterns.items():
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(f"Line {i}: {message}")
        
        return json.dumps({
            "language": "python",
            "issues_found": len(issues),
            "issues": issues
        })
    
    def _scan_generic_security(self, code: str, language: str) -> str:
        """Generic security scan for non-Python languages"""
        issues = []
        lines = code.split('\n')
        
        # Generic security patterns
        generic_patterns = {
            r'password\s*[=:]\s*["\'][^"\']+["\']': "Hardcoded password detected",
            r'secret\s*[=:]\s*["\'][^"\']+["\']': "Hardcoded secret detected", 
            r'api[_-]?key\s*[=:]\s*["\'][^"\']+["\']': "Hardcoded API key detected",
            r'token\s*[=:]\s*["\'][^"\']+["\']': "Hardcoded token detected",
            r'SELECT\s+\*\s+FROM.*\$': "Possible SQL injection vulnerability",
            r'innerHTML\s*=': "Possible XSS vulnerability (JavaScript)",
            r'document\.write\s*\(': "Possible XSS vulnerability (JavaScript)"
        }
        
        for i, line in enumerate(lines, 1):
            for pattern, message in generic_patterns.items():
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(f"Line {i}: {message}")
        
        return json.dumps({
            "language": language,
            "issues_found": len(issues),
            "issues": issues
        })


class QualityAnalysisTool(BaseTool):
    """Tool for code quality analysis"""
    name: str = "quality_analysis_tool"
    description: str = "Analyze code quality metrics and identify improvement areas"
    
    def _run(self, code: str, language: str = "python") -> str:
        """Analyze code quality"""
        try:
            if language.lower() == "python":
                return self._analyze_python_quality(code)
            else:
                return self._analyze_generic_quality(code, language)
        except Exception as e:
            return f"Quality analysis error: {str(e)}"
    
    def _analyze_python_quality(self, code: str) -> str:
        """Analyze Python code quality"""
        try:
            tree = ast.parse(code)
            
            metrics = {
                "total_lines": len(code.split('\n')),
                "blank_lines": len([line for line in code.split('\n') if not line.strip()]),
                "comment_lines": len([line for line in code.split('\n') if line.strip().startswith('#')]),
                "functions": 0,
                "classes": 0,
                "complexity_score": 0,
                "docstring_coverage": 0,
                "long_functions": [],
                "naming_issues": [],
                "style_issues": []
            }
            
            functions_with_docstrings = 0
            total_functions = 0
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    metrics["classes"] += 1
                    # Check for docstring
                    if (node.body and isinstance(node.body[0], ast.Expr) and 
                        isinstance(node.body[0].value, ast.Str)):
                        functions_with_docstrings += 1
                    total_functions += 1
                    
                    # Check naming convention
                    if not node.name[0].isupper():
                        metrics["naming_issues"].append(f"Class {node.name} should start with uppercase")
                
                elif isinstance(node, ast.FunctionDef):
                    metrics["functions"] += 1
                    total_functions += 1
                    
                    # Check for docstring
                    if (node.body and isinstance(node.body[0], ast.Expr) and 
                        isinstance(node.body[0].value, ast.Str)):
                        functions_with_docstrings += 1
                    
                    # Check function length
                    if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
                        func_length = node.end_lineno - node.lineno
                        if func_length > 50:
                            metrics["long_functions"].append(f"Function {node.name} is {func_length} lines long")
                    
                    # Check naming convention
                    if not re.match(r'^[a-z_][a-z0-9_]*$', node.name):
                        metrics["naming_issues"].append(f"Function {node.name} should use snake_case")
            
            # Calculate docstring coverage
            if total_functions > 0:
                metrics["docstring_coverage"] = (functions_with_docstrings / total_functions) * 100
            
            # Style checks
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if len(line) > 88:  # PEP 8 line length
                    metrics["style_issues"].append(f"Line {i} exceeds 88 characters")
                if line.endswith(' ') or line.endswith('\t'):
                    metrics["style_issues"].append(f"Line {i} has trailing whitespace")
            
            return json.dumps(metrics)
            
        except SyntaxError as e:
            return json.dumps({"error": f"Syntax error: {str(e)}"})
    
    def _analyze_generic_quality(self, code: str, language: str) -> str:
        """Generic quality analysis"""
        lines = code.split('\n')
        
        metrics = {
            "language": language,
            "total_lines": len(lines),
            "blank_lines": len([line for line in lines if not line.strip()]),
            "long_lines": len([line for line in lines if len(line) > 120]),
            "trailing_whitespace": len([line for line in lines if line.endswith(' ') or line.endswith('\t')]),
            "estimated_complexity": "medium"
        }
        
        # Estimate complexity based on control structures
        complexity_keywords = ['if', 'else', 'elif', 'for', 'while', 'switch', 'case', 'catch', 'try']
        complexity_count = sum(len(re.findall(rf'\b{keyword}\b', code, re.IGNORECASE)) for keyword in complexity_keywords)
        
        if complexity_count < 5:
            metrics["estimated_complexity"] = "low"
        elif complexity_count > 15:
            metrics["estimated_complexity"] = "high"
        
        return json.dumps(metrics)


class StyleCheckerTool(BaseTool):
    """Tool for style and formatting analysis"""
    name: str = "style_checker_tool"
    description: str = "Check code style and formatting against best practices"
    
    def _run(self, code: str, language: str = "python", style_guide: str = "pep8") -> str:
        """Check code style"""
        try:
            if language.lower() == "python":
                return self._check_python_style(code)
            else:
                return self._check_generic_style(code, language)
        except Exception as e:
            return f"Style check error: {str(e)}"
    
    def _check_python_style(self, code: str) -> str:
        """Check Python code style against PEP 8"""
        issues = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Line length check
            if len(line) > 88:
                issues.append(f"Line {i}: Line too long ({len(line)} > 88 characters)")
            
            # Indentation check (basic)
            if line.strip() and not line.startswith(' ' * (len(line) - len(line.lstrip())) // 4 * 4):
                if line.lstrip() != line:  # Has indentation
                    issues.append(f"Line {i}: Use 4 spaces for indentation")
            
            # Trailing whitespace
            if line.endswith(' ') or line.endswith('\t'):
                issues.append(f"Line {i}: Trailing whitespace")
            
            # Import style
            if line.strip().startswith('import '):
                if ',' in line:
                    issues.append(f"Line {i}: Multiple imports on one line")
            
            # Spacing around operators
            if re.search(r'\w[+\-*/=<>!]=?\w', line):
                issues.append(f"Line {i}: Missing spaces around operator")
        
        return json.dumps({
            "style_guide": "PEP 8",
            "issues_found": len(issues),
            "issues": issues
        })
    
    def _check_generic_style(self, code: str, language: str) -> str:
        """Generic style checking"""
        issues = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Basic style checks
            if len(line) > 120:
                issues.append(f"Line {i}: Line too long ({len(line)} > 120 characters)")
            
            if line.endswith(' ') or line.endswith('\t'):
                issues.append(f"Line {i}: Trailing whitespace")
            
            # Mixed tabs and spaces
            if '\t' in line and ' ' in line.lstrip():
                issues.append(f"Line {i}: Mixed tabs and spaces")
        
        return json.dumps({
            "language": language,
            "issues_found": len(issues),
            "issues": issues
        })


class ReviewerAgent(BaseMultiAgent):
    """
    Reviewer Agent specializing in code review and quality assurance
    
    This agent can:
    - Perform comprehensive code reviews
    - Identify security vulnerabilities
    - Analyze code quality and metrics
    - Check style and formatting
    - Provide improvement recommendations
    - Generate review reports
    """
    
    def __init__(self, agent_id: Optional[str] = None):
        # Initialize tools
        tools = [
            SecurityScanTool(),
            QualityAnalysisTool(),
            StyleCheckerTool()
        ]
        
        # Get configuration
        config = agent_config.reviewer_agent_config
        
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
        
        # Reviewer-specific attributes
        self.review_standards = {
            "security": {"weight": 0.3, "min_score": 8.0},
            "quality": {"weight": 0.3, "min_score": 7.0},
            "style": {"weight": 0.2, "min_score": 8.0},
            "documentation": {"weight": 0.2, "min_score": 6.0}
        }
    
    async def process_task(self, task_description: str, context: Dict[str, Any] = None) -> TaskResult:
        """
        Process code review tasks
        
        Args:
            task_description: Description of the review task
            context: Additional context including code, files, requirements, etc.
            
        Returns:
            TaskResult: Result of the code review
        """
        context = context or {}
        
        try:
            # Determine review type
            review_type = self._determine_review_type(task_description, context)
            
            if review_type == "full_review":
                result = await self._handle_full_code_review(task_description, context)
            elif review_type == "security_review":
                result = await self._handle_security_review(task_description, context)
            elif review_type == "quality_review":
                result = await self._handle_quality_review(task_description, context)
            elif review_type == "style_review":
                result = await self._handle_style_review(task_description, context)
            else:
                result = await self._handle_general_review(task_description, context)
            
            return TaskResult(
                task_id=context.get('task_id', 'unknown'),
                agent_id=self.agent_id,
                status="completed",
                result=result
            )
            
        except Exception as e:
            self.logger.error(f"Error processing review task: {e}")
            raise
    
    def _determine_review_type(self, description: str, context: Dict[str, Any]) -> str:
        """Determine the type of review requested"""
        desc_lower = description.lower()
        
        if any(keyword in desc_lower for keyword in ["security", "vulnerability", "secure"]):
            return "security_review"
        elif any(keyword in desc_lower for keyword in ["quality", "metrics", "maintainability"]):
            return "quality_review"
        elif any(keyword in desc_lower for keyword in ["style", "format", "pep8", "lint"]):
            return "style_review"
        elif any(keyword in desc_lower for keyword in ["full", "comprehensive", "complete"]):
            return "full_review"
        else:
            return "general_review"
    
    async def _handle_full_code_review(self, description: str, context: Dict[str, Any]) -> ReviewResult:
        """Handle comprehensive code review"""
        self.logger.info(f"Performing full code review: {description}")
        
        code = self._extract_code(context)
        language = context.get('language', 'python')
        file_path = context.get('file_path')
        
        # Perform all types of analysis
        security_result = await self._perform_security_analysis(code, language)
        quality_result = await self._perform_quality_analysis(code, language)
        style_result = await self._perform_style_analysis(code, language)
        
        # Combine results
        all_issues = []
        all_issues.extend(security_result)
        all_issues.extend(quality_result)
        all_issues.extend(style_result)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(all_issues)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(all_issues)
        
        # Compile metrics
        metrics = self._compile_metrics(code, language, all_issues)
        
        # Count issues by severity and category
        issues_by_severity = {}
        issues_by_category = {}
        
        for issue in all_issues:
            issues_by_severity[issue.severity] = issues_by_severity.get(issue.severity, 0) + 1
            issues_by_category[issue.category] = issues_by_category.get(issue.category, 0) + 1
        
        return ReviewResult(
            overall_score=overall_score,
            total_issues=len(all_issues),
            issues_by_severity=issues_by_severity,
            issues_by_category=issues_by_category,
            issues=all_issues,
            recommendations=recommendations,
            metrics=metrics
        )
    
    async def _handle_security_review(self, description: str, context: Dict[str, Any]) -> ReviewResult:
        """Handle security-focused review"""
        self.logger.info(f"Performing security review: {description}")
        
        code = self._extract_code(context)
        language = context.get('language', 'python')
        
        security_issues = await self._perform_security_analysis(code, language)
        
        overall_score = 10.0 - (len([i for i in security_issues if i.severity == SeverityLevel.CRITICAL]) * 3.0) - \
                       (len([i for i in security_issues if i.severity == SeverityLevel.HIGH]) * 2.0) - \
                       (len([i for i in security_issues if i.severity == SeverityLevel.MEDIUM]) * 1.0)
        overall_score = max(0.0, overall_score)
        
        return ReviewResult(
            overall_score=overall_score,
            total_issues=len(security_issues),
            issues=security_issues,
            recommendations=self._generate_security_recommendations(security_issues),
            metrics={"security_focus": True, "vulnerabilities_found": len(security_issues)}
        )
    
    async def _handle_quality_review(self, description: str, context: Dict[str, Any]) -> ReviewResult:
        """Handle quality-focused review"""
        self.logger.info(f"Performing quality review: {description}")
        
        code = self._extract_code(context)
        language = context.get('language', 'python')
        
        quality_issues = await self._perform_quality_analysis(code, language)
        
        return ReviewResult(
            overall_score=self._calculate_quality_score(quality_issues),
            total_issues=len(quality_issues),
            issues=quality_issues,
            recommendations=self._generate_quality_recommendations(quality_issues),
            metrics={"quality_focus": True}
        )
    
    async def _handle_style_review(self, description: str, context: Dict[str, Any]) -> ReviewResult:
        """Handle style-focused review"""
        self.logger.info(f"Performing style review: {description}")
        
        code = self._extract_code(context)
        language = context.get('language', 'python')
        
        style_issues = await self._perform_style_analysis(code, language)
        
        return ReviewResult(
            overall_score=self._calculate_style_score(style_issues),
            total_issues=len(style_issues),
            issues=style_issues,
            recommendations=self._generate_style_recommendations(style_issues),
            metrics={"style_focus": True}
        )
    
    async def _handle_general_review(self, description: str, context: Dict[str, Any]) -> ReviewResult:
        """Handle general review tasks"""
        self.logger.info(f"Performing general review: {description}")
        
        # Fallback to full review for general requests
        return await self._handle_full_code_review(description, context)
    
    def _extract_code(self, context: Dict[str, Any]) -> str:
        """Extract code from context"""
        code = context.get('code')
        file_path = context.get('file_path')
        
        if not code and file_path:
            # Try to read from workspace
            try:
                from pathlib import Path
                workspace_path = Path(settings.workspace_path)
                target_path = workspace_path / file_path
                if target_path.exists():
                    code = target_path.read_text(encoding='utf-8')
            except Exception as e:
                self.logger.error(f"Could not read file {file_path}: {e}")
        
        if not code:
            raise ValueError("No code provided for review")
        
        return code
    
    async def _perform_security_analysis(self, code: str, language: str) -> List[CodeIssue]:
        """Perform security analysis and return issues"""
        security_tool = self.tools[0]  # SecurityScanTool
        result = security_tool._run(code, language)
        
        try:
            scan_data = json.loads(result)
            issues = []
            
            for i, issue_text in enumerate(scan_data.get('issues', [])):
                # Parse line number if present
                line_match = re.match(r'Line (\d+): (.+)', issue_text)
                if line_match:
                    line_num = int(line_match.group(1))
                    description = line_match.group(2)
                else:
                    line_num = None
                    description = issue_text
                
                # Determine severity based on keywords
                severity = SeverityLevel.MEDIUM
                if any(keyword in description.lower() for keyword in ['dangerous', 'arbitrary code', 'injection']):
                    severity = SeverityLevel.CRITICAL
                elif any(keyword in description.lower() for keyword in ['vulnerable', 'broken', 'weak']):
                    severity = SeverityLevel.HIGH
                
                issues.append(CodeIssue(
                    category=IssueCategory.SECURITY,
                    severity=severity,
                    title=f"Security Issue {i+1}",
                    description=description,
                    line_number=line_num
                ))
            
            return issues
        
        except json.JSONDecodeError:
            return [CodeIssue(
                category=IssueCategory.SECURITY,
                severity=SeverityLevel.LOW,
                title="Security Analysis Error",
                description=f"Could not parse security scan results: {result}"
            )]
    
    async def _perform_quality_analysis(self, code: str, language: str) -> List[CodeIssue]:
        """Perform quality analysis and return issues"""
        quality_tool = self.tools[1]  # QualityAnalysisTool
        result = quality_tool._run(code, language)
        
        try:
            quality_data = json.loads(result)
            issues = []
            
            # Check various quality metrics
            if quality_data.get('docstring_coverage', 100) < 50:
                issues.append(CodeIssue(
                    category=IssueCategory.DOCUMENTATION,
                    severity=SeverityLevel.MEDIUM,
                    title="Low Documentation Coverage",
                    description=f"Only {quality_data['docstring_coverage']:.1f}% of functions have docstrings"
                ))
            
            for func_issue in quality_data.get('long_functions', []):
                issues.append(CodeIssue(
                    category=IssueCategory.MAINTAINABILITY,
                    severity=SeverityLevel.MEDIUM,
                    title="Long Function",
                    description=func_issue
                ))
            
            for naming_issue in quality_data.get('naming_issues', []):
                issues.append(CodeIssue(
                    category=IssueCategory.STYLE,
                    severity=SeverityLevel.LOW,
                    title="Naming Convention",
                    description=naming_issue
                ))
            
            return issues
        
        except json.JSONDecodeError:
            return []
    
    async def _perform_style_analysis(self, code: str, language: str) -> List[CodeIssue]:
        """Perform style analysis and return issues"""
        style_tool = self.tools[2]  # StyleCheckerTool
        result = style_tool._run(code, language)
        
        try:
            style_data = json.loads(result)
            issues = []
            
            for issue_text in style_data.get('issues', []):
                line_match = re.match(r'Line (\d+): (.+)', issue_text)
                if line_match:
                    line_num = int(line_match.group(1))
                    description = line_match.group(2)
                else:
                    line_num = None
                    description = issue_text
                
                issues.append(CodeIssue(
                    category=IssueCategory.STYLE,
                    severity=SeverityLevel.LOW,
                    title="Style Issue",
                    description=description,
                    line_number=line_num
                ))
            
            return issues
        
        except json.JSONDecodeError:
            return []
    
    def _calculate_overall_score(self, issues: List[CodeIssue]) -> float:
        """Calculate overall code quality score"""
        base_score = 10.0
        
        # Deduct points based on severity
        for issue in issues:
            if issue.severity == SeverityLevel.CRITICAL:
                base_score -= 3.0
            elif issue.severity == SeverityLevel.HIGH:
                base_score -= 2.0
            elif issue.severity == SeverityLevel.MEDIUM:
                base_score -= 1.0
            elif issue.severity == SeverityLevel.LOW:
                base_score -= 0.5
        
        return max(0.0, base_score)
    
    def _calculate_quality_score(self, issues: List[CodeIssue]) -> float:
        """Calculate quality-specific score"""
        return self._calculate_overall_score(issues)
    
    def _calculate_style_score(self, issues: List[CodeIssue]) -> float:
        """Calculate style-specific score"""
        return max(0.0, 10.0 - (len(issues) * 0.5))
    
    def _generate_recommendations(self, issues: List[CodeIssue]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        critical_issues = [i for i in issues if i.severity == SeverityLevel.CRITICAL]
        if critical_issues:
            recommendations.append(f"Address {len(critical_issues)} critical security issues immediately")
        
        security_issues = [i for i in issues if i.category == IssueCategory.SECURITY]
        if security_issues:
            recommendations.append("Review and fix security vulnerabilities")
        
        doc_issues = [i for i in issues if i.category == IssueCategory.DOCUMENTATION]
        if len(doc_issues) > 3:
            recommendations.append("Improve code documentation and add missing docstrings")
        
        style_issues = [i for i in issues if i.category == IssueCategory.STYLE]
        if len(style_issues) > 5:
            recommendations.append("Run a code formatter to fix style issues")
        
        return recommendations or ["Code quality is good, no major issues found"]
    
    def _generate_security_recommendations(self, issues: List[CodeIssue]) -> List[str]:
        """Generate security-specific recommendations"""
        if not issues:
            return ["No security issues detected - good job!"]
        
        recommendations = [
            "Review and fix all security vulnerabilities",
            "Consider using security linting tools in your CI/CD pipeline",
            "Implement security code review process"
        ]
        
        return recommendations
    
    def _generate_quality_recommendations(self, issues: List[CodeIssue]) -> List[str]:
        """Generate quality-specific recommendations"""
        return [
            "Consider breaking down large functions into smaller ones",
            "Add more comprehensive documentation",
            "Implement unit tests for better code coverage"
        ]
    
    def _generate_style_recommendations(self, issues: List[CodeIssue]) -> List[str]:
        """Generate style-specific recommendations"""
        return [
            "Use a code formatter like Black (Python) or Prettier (JavaScript)",
            "Set up pre-commit hooks for automatic style checking",
            "Configure your editor to show style violations"
        ]
    
    def _compile_metrics(self, code: str, language: str, issues: List[CodeIssue]) -> Dict[str, Any]:
        """Compile comprehensive metrics"""
        lines = code.split('\n')
        
        return {
            "language": language,
            "total_lines": len(lines),
            "code_lines": len([line for line in lines if line.strip() and not line.strip().startswith('#')]),
            "comment_lines": len([line for line in lines if line.strip().startswith('#')]),
            "total_issues": len(issues),
            "critical_issues": len([i for i in issues if i.severity == SeverityLevel.CRITICAL]),
            "high_issues": len([i for i in issues if i.severity == SeverityLevel.HIGH]),
            "medium_issues": len([i for i in issues if i.severity == SeverityLevel.MEDIUM]),
            "low_issues": len([i for i in issues if i.severity == SeverityLevel.LOW]),
            "security_issues": len([i for i in issues if i.category == IssueCategory.SECURITY]),
            "quality_issues": len([i for i in issues if i.category in [IssueCategory.MAINTAINABILITY, IssueCategory.PERFORMANCE]]),
            "style_issues": len([i for i in issues if i.category == IssueCategory.STYLE]),
            "documentation_issues": len([i for i in issues if i.category == IssueCategory.DOCUMENTATION])
        }