"""
自我审查器
实现代码审查、质量检查和自我改进功能
"""

import ast
import re
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)

class ReviewType(Enum):
    """审查类型枚举"""
    SYNTAX = "syntax"              # 语法审查
    LOGIC = "logic"               # 逻辑审查
    STYLE = "style"               # 代码风格审查
    SECURITY = "security"         # 安全审查
    PERFORMANCE = "performance"   # 性能审查
    MAINTAINABILITY = "maintainability"  # 可维护性审查

class Severity(Enum):
    """问题严重程度枚举"""
    CRITICAL = "critical"         # 严重问题
    HIGH = "high"                # 高优先级
    MEDIUM = "medium"            # 中等优先级
    LOW = "low"                  # 低优先级
    INFO = "info"                # 信息提示

@dataclass
class ReviewIssue:
    """审查问题数据结构"""
    id: str
    type: ReviewType
    severity: Severity
    description: str
    line_number: Optional[int] = None
    column: Optional[int] = None
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'type': self.type.value,
            'severity': self.severity.value,
            'description': self.description,
            'line_number': self.line_number,
            'column': self.column,
            'suggestion': self.suggestion,
            'code_snippet': self.code_snippet
        }

@dataclass
class ReviewResult:
    """审查结果数据结构"""
    overall_score: float  # 总体评分 0-100
    issues: list[ReviewIssue]
    suggestions: list[str]
    metrics: dict[str, Any]
    
    def to_dict(self) -> dict[str, Any]:
        return {
            'overall_score': self.overall_score,
            'issues': [issue.to_dict() for issue in self.issues],
            'suggestions': self.suggestions,
            'metrics': self.metrics
        }

class SelfReviewer:
    """自我审查器"""
    
    def __init__(self, llm_manager=None, memory_manager=None):
        self.llm_manager = llm_manager
        self.memory_manager = memory_manager
        self.review_history: list[ReviewResult] = []
        
        # 初始化审查规则
        self._init_review_rules()
        
        logger.info("自我审查器初始化完成")
    
    def _init_review_rules(self):
        """初始化审查规则"""
        # 语法规则
        self.syntax_rules = [
            {'pattern': r'^\s*def\s+\w+\(.*\):\s*$', 'message': '函数定义后应有文档字符串'},
            {'pattern': r'^\s*class\s+\w+.*:\s*$', 'message': '类定义后应有文档字符串'},
        ]
        
        # 风格规则
        self.style_rules = [
            {'pattern': r'^.{120,}', 'message': '行长度超过120字符'},
            {'pattern': r'\t', 'message': '使用tab缩进，建议使用4个空格'},
            {'pattern': r'[a-z]+[A-Z]', 'message': '变量名使用驼峰命名，建议使用下划线'},
        ]
        
        # 安全规则
        self.security_rules = [
            {'pattern': r'eval\(', 'message': '使用eval()函数存在安全风险'},
            {'pattern': r'exec\(', 'message': '使用exec()函数存在安全风险'},
            {'pattern': r'input\(.*\)', 'message': '直接使用input()可能存在注入风险'},
        ]
        
        # 性能规则
        self.performance_rules = [
            {'pattern': r'for.*in.*range\(len\(', 'message': '可以使用enumerate()替代range(len())'},
            {'pattern': r'\+.*\+.*\+', 'message': '多个字符串连接建议使用join()或f-string'},
        ]
    
    async def review_code(self, code: str, context: dict[str, Any] = None) -> ReviewResult:
        """审查代码
        
        Args:
            code: 要审查的代码
            context: 上下文信息
            
        Returns:
            审查结果
        """
        logger.info("开始代码审查")
        
        issues = []
        issue_counter = 1
        
        # 语法审查
        syntax_issues = self._review_syntax(code, issue_counter)
        issues.extend(syntax_issues)
        issue_counter += len(syntax_issues)
        
        # 逻辑审查
        logic_issues = self._review_logic(code, issue_counter)
        issues.extend(logic_issues)
        issue_counter += len(logic_issues)
        
        # 风格审查
        style_issues = self._review_style(code, issue_counter)
        issues.extend(style_issues)
        issue_counter += len(style_issues)
        
        # 安全审查
        security_issues = self._review_security(code, issue_counter)
        issues.extend(security_issues)
        issue_counter += len(security_issues)
        
        # 性能审查
        performance_issues = self._review_performance(code, issue_counter)
        issues.extend(performance_issues)
        issue_counter += len(performance_issues)
        
        # 可维护性审查
        maintainability_issues = self._review_maintainability(code, issue_counter)
        issues.extend(maintainability_issues)
        
        # 计算评分和指标
        overall_score = self._calculate_overall_score(issues, code)
        metrics = self._calculate_metrics(code, issues)
        suggestions = self._generate_suggestions(issues, code)
        
        review_result = ReviewResult(
            overall_score=overall_score,
            issues=issues,
            suggestions=suggestions,
            metrics=metrics
        )
        
        # 存储审查历史
        self.review_history.append(review_result)
        
        # 存储到记忆中
        if self.memory_manager:
            from .memory_manager import MemoryType
            self.memory_manager.store_memory(
                MemoryType.CODE_PATTERN,
                {
                    'review_result': review_result.to_dict(),
                    'code_length': len(code),
                    'issues_count': len(issues)
                },
                ['code_review', 'quality', 'issues']
            )
        
        logger.info(f"代码审查完成: 评分 {overall_score:.1f}, 发现 {len(issues)} 个问题")
        return review_result
    
    def _review_syntax(self, code: str, start_id: int) -> list[ReviewIssue]:
        """语法审查"""
        issues = []
        
        try:
            # 尝试解析AST
            tree = ast.parse(code)
            
            # 检查函数和类是否有文档字符串
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if not ast.get_docstring(node):
                        issues.append(ReviewIssue(
                            id=f"syntax_{start_id + len(issues)}",
                            type=ReviewType.SYNTAX,
                            severity=Severity.MEDIUM,
                            description=f"{node.__class__.__name__} '{node.name}' 缺少文档字符串",
                            line_number=node.lineno,
                            suggestion=f"为 {node.name} 添加文档字符串说明其功能"
                        ))
            
        except SyntaxError as e:
            issues.append(ReviewIssue(
                id=f"syntax_{start_id}",
                type=ReviewType.SYNTAX,
                severity=Severity.CRITICAL,
                description=f"语法错误: {e.msg}",
                line_number=e.lineno,
                column=e.offset,
                suggestion="修复语法错误"
            ))
        
        return issues
    
    def _review_logic(self, code: str, start_id: int) -> list[ReviewIssue]:
        """逻辑审查"""
        issues = []
        lines = code.split('\n')
        
        try:
            tree = ast.parse(code)
            
            # 检查未使用的变量
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # 简单的未使用变量检查
                    assigned_vars = set()
                    used_vars = set()
                    
                    for child in ast.walk(node):
                        if isinstance(child, ast.Assign):
                            for target in child.targets:
                                if isinstance(target, ast.Name):
                                    assigned_vars.add(target.id)
                        elif isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                            used_vars.add(child.id)
                    
                    unused_vars = assigned_vars - used_vars
                    for var in unused_vars:
                        if not var.startswith('_'):  # 忽略以_开头的变量
                            issues.append(ReviewIssue(
                                id=f"logic_{start_id + len(issues)}",
                                type=ReviewType.LOGIC,
                                severity=Severity.LOW,
                                description=f"变量 '{var}' 被赋值但未使用",
                                suggestion=f"删除未使用的变量 '{var}' 或使用下划线前缀"
                            ))
            
            # 检查可能的逻辑错误
            for i, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                # 检查空的except块
                if line_stripped == 'except:' and i < len(lines):
                    next_line = lines[i].strip() if i < len(lines) else ''
                    if next_line == 'pass':
                        issues.append(ReviewIssue(
                            id=f"logic_{start_id + len(issues)}",
                            type=ReviewType.LOGIC,
                            severity=Severity.MEDIUM,
                            description="空的except块可能隐藏错误",
                            line_number=i,
                            suggestion="添加适当的错误处理或至少记录异常"
                        ))
                
                # 检查比较链
                if '==' in line_stripped and 'or' in line_stripped:
                    if re.search(r'\w+\s*==\s*\w+\s+or\s+\w+', line_stripped):
                        issues.append(ReviewIssue(
                            id=f"logic_{start_id + len(issues)}",
                            type=ReviewType.LOGIC,
                            severity=Severity.MEDIUM,
                            description="可能的逻辑错误：比较操作符优先级",
                            line_number=i,
                            suggestion="使用括号明确操作符优先级"
                        ))
        
        except SyntaxError:
            # 如果有语法错误，跳过逻辑检查
            pass
        
        return issues
    
    def _review_style(self, code: str, start_id: int) -> list[ReviewIssue]:
        """风格审查"""
        issues = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            # 检查行长度
            if len(line) > 120:
                issues.append(ReviewIssue(
                    id=f"style_{start_id + len(issues)}",
                    type=ReviewType.STYLE,
                    severity=Severity.LOW,
                    description=f"行长度 {len(line)} 超过建议的120字符",
                    line_number=i,
                    suggestion="将长行分解为多行"
                ))
            
            # 检查tab字符
            if '\t' in line:
                issues.append(ReviewIssue(
                    id=f"style_{start_id + len(issues)}",
                    type=ReviewType.STYLE,
                    severity=Severity.LOW,
                    description="使用tab缩进",
                    line_number=i,
                    suggestion="使用4个空格替代tab"
                ))
            
            # 检查尾随空格
            if line.endswith(' ') or line.endswith('\t'):
                issues.append(ReviewIssue(
                    id=f"style_{start_id + len(issues)}",
                    type=ReviewType.STYLE,
                    severity=Severity.INFO,
                    description="行末有尾随空格",
                    line_number=i,
                    suggestion="删除行末的空格"
                ))
        
        # 检查命名约定
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not re.match(r'^[a-z_][a-z0-9_]*$', node.name):
                        issues.append(ReviewIssue(
                            id=f"style_{start_id + len(issues)}",
                            type=ReviewType.STYLE,
                            severity=Severity.LOW,
                            description=f"函数名 '{node.name}' 不符合snake_case约定",
                            line_number=node.lineno,
                            suggestion="使用小写字母和下划线命名函数"
                        ))
                
                elif isinstance(node, ast.ClassDef):
                    if not re.match(r'^[A-Z][a-zA-Z0-9]*$', node.name):
                        issues.append(ReviewIssue(
                            id=f"style_{start_id + len(issues)}",
                            type=ReviewType.STYLE,
                            severity=Severity.LOW,
                            description=f"类名 '{node.name}' 不符合PascalCase约定",
                            line_number=node.lineno,
                            suggestion="使用首字母大写的驼峰命名法命名类"
                        ))
        
        except SyntaxError:
            pass
        
        return issues
    
    def _review_security(self, code: str, start_id: int) -> list[ReviewIssue]:
        """安全审查"""
        issues = []
        lines = code.split('\n')
        
        security_patterns = [
            (r'eval\s*\(', "使用eval()函数存在代码注入风险", Severity.CRITICAL),
            (r'exec\s*\(', "使用exec()函数存在代码注入风险", Severity.CRITICAL),
            (r'os\.system\s*\(', "使用os.system()可能存在命令注入风险", Severity.HIGH),
            (r'subprocess\.call.*shell=True', "subprocess使用shell=True存在安全风险", Severity.HIGH),
            (r'pickle\.loads?\s*\(', "使用pickle反序列化不可信数据存在风险", Severity.MEDIUM),
            (r'input\s*\([^)]*\)', "直接使用input()可能存在注入风险", Severity.MEDIUM),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, message, severity in security_patterns:
                if re.search(pattern, line):
                    issues.append(ReviewIssue(
                        id=f"security_{start_id + len(issues)}",
                        type=ReviewType.SECURITY,
                        severity=severity,
                        description=message,
                        line_number=i,
                        code_snippet=line.strip(),
                        suggestion="使用更安全的替代方法"
                    ))
        
        return issues
    
    def _review_performance(self, code: str, start_id: int) -> list[ReviewIssue]:
        """性能审查"""
        issues = []
        lines = code.split('\n')
        
        performance_patterns = [
            (r'for\s+\w+\s+in\s+range\s*\(\s*len\s*\(', "使用range(len())可以用enumerate()替代", Severity.LOW),
            (r'\w+\s*\+=?\s*\w+\s*\+\s*\w+', "字符串连接建议使用join()或f-string", Severity.LOW),
            (r'\.append\s*\(.*\)\s*$', "在循环中使用append可能影响性能", Severity.INFO),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, message, severity in performance_patterns:
                if re.search(pattern, line):
                    issues.append(ReviewIssue(
                        id=f"performance_{start_id + len(issues)}",
                        type=ReviewType.PERFORMANCE,
                        severity=severity,
                        description=message,
                        line_number=i,
                        code_snippet=line.strip(),
                        suggestion="考虑使用更高效的实现方式"
                    ))
        
        return issues
    
    def _review_maintainability(self, code: str, start_id: int) -> list[ReviewIssue]:
        """可维护性审查"""
        issues = []
        
        try:
            tree = ast.parse(code)
            
            # 检查函数复杂度
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    complexity = self._calculate_cyclomatic_complexity(node)
                    if complexity > 10:
                        issues.append(ReviewIssue(
                            id=f"maintainability_{start_id + len(issues)}",
                            type=ReviewType.MAINTAINABILITY,
                            severity=Severity.MEDIUM,
                            description=f"函数 '{node.name}' 复杂度过高 (复杂度: {complexity})",
                            line_number=node.lineno,
                            suggestion="考虑将复杂函数分解为更小的函数"
                        ))
                    
                    # 检查函数长度
                    func_lines = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                    if func_lines > 50:
                        issues.append(ReviewIssue(
                            id=f"maintainability_{start_id + len(issues)}",
                            type=ReviewType.MAINTAINABILITY,
                            severity=Severity.LOW,
                            description=f"函数 '{node.name}' 过长 ({func_lines} 行)",
                            line_number=node.lineno,
                            suggestion="考虑将长函数分解为更小的函数"
                        ))
        
        except SyntaxError:
            pass
        
        return issues
    
    def _calculate_cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        """计算圈复杂度"""
        complexity = 1  # 基础复杂度
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def _calculate_overall_score(self, issues: list[ReviewIssue], code: str) -> float:
        """计算总体评分"""
        base_score = 100.0
        
        # 根据问题严重程度扣分
        severity_penalties = {
            Severity.CRITICAL: 20,
            Severity.HIGH: 10,
            Severity.MEDIUM: 5,
            Severity.LOW: 2,
            Severity.INFO: 1
        }
        
        total_penalty = 0
        for issue in issues:
            total_penalty += severity_penalties.get(issue.severity, 0)
        
        # 限制最低分数
        final_score = max(0, base_score - total_penalty)
        return final_score
    
    def _calculate_metrics(self, code: str, issues: list[ReviewIssue]) -> dict[str, Any]:
        """计算代码指标"""
        lines = code.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        metrics = {
            'total_lines': len(lines),
            'code_lines': len(non_empty_lines),
            'comment_lines': len([line for line in lines if line.strip().startswith('#')]),
            'blank_lines': len(lines) - len(non_empty_lines),
            'total_issues': len(issues),
            'issues_by_severity': {},
            'issues_by_type': {}
        }
        
        # 按严重程度统计
        for severity in Severity:
            count = len([issue for issue in issues if issue.severity == severity])
            metrics['issues_by_severity'][severity.value] = count
        
        # 按类型统计
        for review_type in ReviewType:
            count = len([issue for issue in issues if issue.type == review_type])
            metrics['issues_by_type'][review_type.value] = count
        
        return metrics
    
    def _generate_suggestions(self, issues: list[ReviewIssue], code: str) -> list[str]:
        """生成改进建议"""
        suggestions = []
        
        # 基于问题类型生成建议
        critical_issues = [issue for issue in issues if issue.severity == Severity.CRITICAL]
        if critical_issues:
            suggestions.append("🚨 发现严重问题，建议优先修复语法错误和安全问题")
        
        security_issues = [issue for issue in issues if issue.type == ReviewType.SECURITY]
        if security_issues:
            suggestions.append("🔒 发现安全问题，建议审查代码安全性")
        
        style_issues = [issue for issue in issues if issue.type == ReviewType.STYLE]
        if len(style_issues) > 5:
            suggestions.append("📝 代码风格问题较多，建议使用代码格式化工具")
        
        performance_issues = [issue for issue in issues if issue.type == ReviewType.PERFORMANCE]
        if performance_issues:
            suggestions.append("⚡ 发现性能问题，建议优化代码效率")
        
        maintainability_issues = [issue for issue in issues if issue.type == ReviewType.MAINTAINABILITY]
        if maintainability_issues:
            suggestions.append("🔧 代码可维护性有待改进，建议重构复杂函数")
        
        # 基于代码特征生成建议
        lines = code.split('\n')
        if len(lines) > 200:
            suggestions.append("📄 代码文件较大，建议考虑模块化")
        
        if not any('#' in line for line in lines):
            suggestions.append("📖 缺少注释，建议添加必要的代码注释")
        
        return suggestions
    
    async def suggest_improvements(self, code: str, issues: list[ReviewIssue]) -> dict[str, Any]:
        """建议具体的改进方案"""
        improvements = {
            'priority_fixes': [],
            'suggested_refactoring': [],
            'best_practices': [],
            'automated_fixes': []
        }
        
        # 优先修复项
        critical_and_high = [issue for issue in issues if issue.severity in [Severity.CRITICAL, Severity.HIGH]]
        for issue in critical_and_high:
            improvements['priority_fixes'].append({
                'issue_id': issue.id,
                'description': issue.description,
                'suggestion': issue.suggestion,
                'line_number': issue.line_number
            })
        
        # 重构建议
        maintainability_issues = [issue for issue in issues if issue.type == ReviewType.MAINTAINABILITY]
        for issue in maintainability_issues:
            improvements['suggested_refactoring'].append({
                'description': issue.description,
                'suggestion': issue.suggestion
            })
        
        # 最佳实践建议
        if any(issue.type == ReviewType.SECURITY for issue in issues):
            improvements['best_practices'].append("实施安全编码实践")
        
        if any(issue.type == ReviewType.PERFORMANCE for issue in issues):
            improvements['best_practices'].append("遵循性能优化最佳实践")
        
        # 自动修复建议
        style_issues = [issue for issue in issues if issue.type == ReviewType.STYLE]
        if style_issues:
            improvements['automated_fixes'].append("使用black或autopep8进行代码格式化")
        
        return improvements
    
    def get_review_trends(self) -> dict[str, Any]:
        """获取审查趋势分析"""
        if not self.review_history:
            return {'message': '暂无审查历史'}
        
        recent_reviews = self.review_history[-10:]  # 最近10次审查
        
        scores = [review.overall_score for review in recent_reviews]
        issue_counts = [len(review.issues) for review in recent_reviews]
        
        return {
            'average_score': sum(scores) / len(scores),
            'score_trend': 'improving' if len(scores) >= 2 and scores[-1] > scores[0] else 'declining',
            'average_issues': sum(issue_counts) / len(issue_counts),
            'total_reviews': len(self.review_history),
            'recent_reviews': len(recent_reviews)
        } 