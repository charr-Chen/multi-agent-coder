"""
需求分析器
深度分析用户需求，提取显式和隐式需求，识别技术约束和风险
"""

import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)

class RequirementType(Enum):
    """需求类型枚举"""
    FUNCTIONAL = "functional"       # 功能性需求
    NON_FUNCTIONAL = "non_functional"  # 非功能性需求
    TECHNICAL = "technical"         # 技术需求
    BUSINESS = "business"          # 业务需求
    USER_EXPERIENCE = "user_experience"  # 用户体验需求

class Priority(Enum):
    """优先级枚举"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class Requirement:
    """需求数据结构"""
    id: str
    type: RequirementType
    description: str
    priority: Priority
    source: str  # explicit(显式) 或 implicit(隐式)
    confidence: float  # 置信度 0-1
    dependencies: list[str] = None
    constraints: list[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.constraints is None:
            self.constraints = []

class RequirementAnalyzer:
    """需求分析器"""
    
    def __init__(self, llm_manager=None, memory_manager=None):
        self.llm_manager = llm_manager
        self.memory_manager = memory_manager
        
        # 预定义的模式和关键词
        self.functional_patterns = [
            r'implement|create|add|build|develop',
            r'should|must|need to|required to',
            r'function|feature|capability|ability'
        ]
        
        self.non_functional_patterns = [
            r'performance|speed|fast|slow|efficient',
            r'security|secure|safe|protect',
            r'scalable|scale|scalability',
            r'reliable|reliability|stable|robust',
            r'usable|user.friendly|intuitive'
        ]
        
        self.technical_patterns = [
            r'database|db|sql|nosql',
            r'api|rest|graphql|endpoint',
            r'framework|library|package',
            r'algorithm|data structure',
            r'integration|interface|connect'
        ]
        
        logger.info("需求分析器初始化完成")
    
    async def analyze_requirements(self, issue: dict[str, Any], context: dict[str, Any] = None) -> dict[str, Any]:
        """分析需求
        
        Args:
            issue: Issue信息
            context: 上下文信息
            
        Returns:
            需求分析结果
        """
        logger.info(f"开始分析需求: {issue.get('title', 'Unknown')}")
        
        # 提取显式需求
        explicit_requirements = self._extract_explicit_requirements(issue)
        
        # 推断隐式需求
        implicit_requirements = self._infer_implicit_requirements(issue, explicit_requirements)
        
        # 分析技术约束
        technical_constraints = self._analyze_technical_constraints(issue, context)
        
        # 识别风险和假设
        risks_and_assumptions = self._identify_risks_and_assumptions(issue, explicit_requirements + implicit_requirements)
        
        # 优先级排序
        prioritized_requirements = self._prioritize_requirements(explicit_requirements + implicit_requirements)
        
        # 需求验证
        validation_result = self._validate_requirements(prioritized_requirements)
        
        # 创建需求可追溯性矩阵
        traceability_matrix = self._create_traceability_matrix(prioritized_requirements, issue)
        
        analysis_result = {
            'issue_id': issue.get('id', 'unknown'),
            'explicit_requirements': [req.__dict__ for req in explicit_requirements],
            'implicit_requirements': [req.__dict__ for req in implicit_requirements],
            'all_requirements': [req.__dict__ for req in prioritized_requirements],
            'technical_constraints': technical_constraints,
            'risks_and_assumptions': risks_and_assumptions,
            'validation_result': validation_result,
            'traceability_matrix': traceability_matrix,
            'analysis_summary': self._create_analysis_summary(prioritized_requirements, technical_constraints)
        }
        
        # 存储到记忆中
        if self.memory_manager:
            from .memory_manager import MemoryType
            self.memory_manager.store_memory(
                MemoryType.SOLUTION_APPROACH,
                analysis_result,
                self._extract_analysis_keywords(issue, prioritized_requirements)
            )
        
        logger.info(f"需求分析完成: {len(prioritized_requirements)} 个需求")
        return analysis_result
    
    def _extract_explicit_requirements(self, issue: dict[str, Any]) -> list[Requirement]:
        """提取显式需求"""
        requirements = []
        req_counter = 1
        
        title = issue.get('title', '')
        description = issue.get('description', '')
        
        # 分析标题中的需求
        title_requirements = self._analyze_text_for_requirements(title, "title")
        for req_type, req_desc, priority in title_requirements:
            requirements.append(Requirement(
                id=f"req_{req_counter}",
                type=req_type,
                description=req_desc,
                priority=priority,
                source="explicit",
                confidence=0.9
            ))
            req_counter += 1
        
        # 分析描述中的需求
        desc_requirements = self._analyze_text_for_requirements(description, "description")
        for req_type, req_desc, priority in desc_requirements:
            requirements.append(Requirement(
                id=f"req_{req_counter}",
                type=req_type,
                description=req_desc,
                priority=priority,
                source="explicit",
                confidence=0.8
            ))
            req_counter += 1
        
        # 如果没有找到明确的需求，创建一个基本需求
        if not requirements:
            requirements.append(Requirement(
                id="req_1",
                type=RequirementType.FUNCTIONAL,
                description=f"实现: {title}",
                priority=Priority.HIGH,
                source="explicit",
                confidence=0.7
            ))
        
        return requirements
    
    def _infer_implicit_requirements(self, issue: dict[str, Any], explicit_requirements: list[Requirement]) -> list[Requirement]:
        """推断隐式需求"""
        implicit_requirements = []
        req_counter = len(explicit_requirements) + 1
        
        title = issue.get('title', '').lower()
        description = issue.get('description', '').lower()
        text = f"{title} {description}"
        
        # 基于显式需求推断隐式需求
        for explicit_req in explicit_requirements:
            if explicit_req.type == RequirementType.FUNCTIONAL:
                # 功能需求通常需要错误处理
                implicit_requirements.append(Requirement(
                    id=f"req_{req_counter}",
                    type=RequirementType.TECHNICAL,
                    description="实现适当的错误处理和异常管理",
                    priority=Priority.MEDIUM,
                    source="implicit",
                    confidence=0.8
                ))
                req_counter += 1
                
                # 功能需求通常需要测试
                implicit_requirements.append(Requirement(
                    id=f"req_{req_counter}",
                    type=RequirementType.TECHNICAL,
                    description="编写单元测试和集成测试",
                    priority=Priority.MEDIUM,
                    source="implicit",
                    confidence=0.7
                ))
                req_counter += 1
        
        # 基于关键词推断隐式需求
        
        # 数据相关的隐式需求
        if any(keyword in text for keyword in ['data', 'database', 'store', 'save', 'persist']):
            implicit_requirements.append(Requirement(
                id=f"req_{req_counter}",
                type=RequirementType.NON_FUNCTIONAL,
                description="确保数据一致性和完整性",
                priority=Priority.HIGH,
                source="implicit",
                confidence=0.8
            ))
            req_counter += 1
            
            implicit_requirements.append(Requirement(
                id=f"req_{req_counter}",
                type=RequirementType.TECHNICAL,
                description="实现数据验证和清理",
                priority=Priority.MEDIUM,
                source="implicit",
                confidence=0.7
            ))
            req_counter += 1
        
        # API相关的隐式需求
        if any(keyword in text for keyword in ['api', 'endpoint', 'service', 'interface']):
            implicit_requirements.append(Requirement(
                id=f"req_{req_counter}",
                type=RequirementType.NON_FUNCTIONAL,
                description="API应该具有适当的性能和响应时间",
                priority=Priority.MEDIUM,
                source="implicit",
                confidence=0.7
            ))
            req_counter += 1
            
            implicit_requirements.append(Requirement(
                id=f"req_{req_counter}",
                type=RequirementType.TECHNICAL,
                description="实现API文档和版本控制",
                priority=Priority.LOW,
                source="implicit",
                confidence=0.6
            ))
            req_counter += 1
        
        # 用户界面相关的隐式需求
        if any(keyword in text for keyword in ['ui', 'interface', 'user', 'display', 'show']):
            implicit_requirements.append(Requirement(
                id=f"req_{req_counter}",
                type=RequirementType.USER_EXPERIENCE,
                description="界面应该直观易用",
                priority=Priority.MEDIUM,
                source="implicit",
                confidence=0.6
            ))
            req_counter += 1
        
        # 安全相关的隐式需求
        if any(keyword in text for keyword in ['user', 'login', 'auth', 'access', 'permission']):
            implicit_requirements.append(Requirement(
                id=f"req_{req_counter}",
                type=RequirementType.NON_FUNCTIONAL,
                description="实现适当的安全措施和访问控制",
                priority=Priority.HIGH,
                source="implicit",
                confidence=0.8
            ))
            req_counter += 1
        
        return implicit_requirements
    
    def _analyze_technical_constraints(self, issue: dict[str, Any], context: dict[str, Any] = None) -> dict[str, Any]:
        """分析技术约束"""
        constraints = {
            'programming_language': [],
            'frameworks': [],
            'databases': [],
            'platforms': [],
            'performance': [],
            'compatibility': [],
            'other': []
        }
        
        text = f"{issue.get('title', '')} {issue.get('description', '')}".lower()
        
        # 编程语言约束
        languages = ['python', 'javascript', 'java', 'c++', 'c#', 'go', 'rust', 'php']
        for lang in languages:
            if lang in text:
                constraints['programming_language'].append(lang)
        
        # 框架约束
        frameworks = ['django', 'flask', 'react', 'vue', 'angular', 'spring', 'express']
        for framework in frameworks:
            if framework in text:
                constraints['frameworks'].append(framework)
        
        # 数据库约束
        databases = ['mysql', 'postgresql', 'mongodb', 'redis', 'sqlite']
        for db in databases:
            if db in text:
                constraints['databases'].append(db)
        
        # 性能约束
        performance_indicators = ['fast', 'slow', 'performance', 'speed', 'efficient', 'optimize']
        for indicator in performance_indicators:
            if indicator in text:
                constraints['performance'].append(f"性能要求: {indicator}")
        
        # 兼容性约束
        compatibility_indicators = ['compatible', 'support', 'work with', 'integrate with']
        for indicator in compatibility_indicators:
            if indicator in text:
                constraints['compatibility'].append(f"兼容性要求: {indicator}")
        
        # 从上下文中提取约束
        if context:
            project_context = context.get('project_context', {})
            if 'existing_tech_stack' in project_context:
                constraints['other'].append(f"现有技术栈约束: {project_context['existing_tech_stack']}")
        
        return constraints
    
    def _identify_risks_and_assumptions(self, issue: dict[str, Any], requirements: list[Requirement]) -> dict[str, Any]:
        """识别风险和假设"""
        risks = []
        assumptions = []
        
        text = f"{issue.get('title', '')} {issue.get('description', '')}".lower()
        
        # 识别风险
        risk_indicators = {
            'complexity': ['complex', 'complicated', 'difficult', 'challenging'],
            'integration': ['integrate', 'connect', 'combine', 'merge'],
            'performance': ['performance', 'speed', 'scale', 'load'],
            'data': ['data', 'database', 'migration', 'sync'],
            'security': ['security', 'auth', 'permission', 'access']
        }
        
        for risk_type, indicators in risk_indicators.items():
            if any(indicator in text for indicator in indicators):
                risks.append({
                    'type': risk_type,
                    'description': f"可能存在{risk_type}相关的风险",
                    'likelihood': 'medium',
                    'impact': 'medium'
                })
        
        # 识别假设
        assumption_patterns = [
            'assume', 'expect', 'should work', 'will be', 'probably', 'likely'
        ]
        
        for pattern in assumption_patterns:
            if pattern in text:
                assumptions.append({
                    'description': f"假设: 基于'{pattern}'的表述",
                    'validity': 'needs_verification'
                })
        
        # 基于需求数量识别风险
        if len(requirements) > 10:
            risks.append({
                'type': 'scope',
                'description': '需求数量较多，可能存在范围蔓延风险',
                'likelihood': 'high',
                'impact': 'medium'
            })
        
        # 基于隐式需求比例识别风险
        implicit_count = len([req for req in requirements if req.source == 'implicit'])
        total_count = len(requirements)
        if total_count > 0 and implicit_count / total_count > 0.5:
            risks.append({
                'type': 'requirements',
                'description': '隐式需求比例较高，可能存在需求理解偏差风险',
                'likelihood': 'medium',
                'impact': 'high'
            })
        
        return {
            'risks': risks,
            'assumptions': assumptions
        }
    
    def _prioritize_requirements(self, requirements: list[Requirement]) -> list[Requirement]:
        """优先级排序"""
        # 定义优先级权重
        priority_weights = {
            Priority.CRITICAL: 4,
            Priority.HIGH: 3,
            Priority.MEDIUM: 2,
            Priority.LOW: 1
        }
        
        # 定义类型权重
        type_weights = {
            RequirementType.FUNCTIONAL: 1.0,
            RequirementType.NON_FUNCTIONAL: 0.8,
            RequirementType.TECHNICAL: 0.6,
            RequirementType.BUSINESS: 0.9,
            RequirementType.USER_EXPERIENCE: 0.7
        }
        
        # 计算综合权重并排序
        def calculate_weight(req: Requirement) -> float:
            priority_weight = priority_weights.get(req.priority, 1)
            type_weight = type_weights.get(req.type, 0.5)
            confidence_weight = req.confidence
            source_weight = 1.0 if req.source == 'explicit' else 0.8
            
            return priority_weight * type_weight * confidence_weight * source_weight
        
        requirements.sort(key=calculate_weight, reverse=True)
        return requirements
    
    def _validate_requirements(self, requirements: list[Requirement]) -> dict[str, Any]:
        """验证需求"""
        validation_result = {
            'is_valid': True,
            'issues': [],
            'completeness_score': 0.0,
            'consistency_score': 0.0,
            'clarity_score': 0.0
        }
        
        # 检查需求完整性
        req_types = set(req.type for req in requirements)
        expected_types = {RequirementType.FUNCTIONAL}
        
        if not expected_types.issubset(req_types):
            validation_result['issues'].append("缺少基本的功能性需求")
            validation_result['is_valid'] = False
        
        # 检查需求一致性
        functional_reqs = [req for req in requirements if req.type == RequirementType.FUNCTIONAL]
        technical_reqs = [req for req in requirements if req.type == RequirementType.TECHNICAL]
        
        if len(functional_reqs) > 0 and len(technical_reqs) == 0:
            validation_result['issues'].append("功能需求缺少对应的技术需求支持")
        
        # 检查需求清晰度
        unclear_reqs = [req for req in requirements if len(req.description) < 10]
        if unclear_reqs:
            validation_result['issues'].append(f"发现 {len(unclear_reqs)} 个描述过于简单的需求")
        
        # 计算评分
        validation_result['completeness_score'] = min(1.0, len(req_types) / 3.0)
        validation_result['consistency_score'] = 1.0 - len(validation_result['issues']) * 0.2
        validation_result['clarity_score'] = 1.0 - len(unclear_reqs) / len(requirements) if requirements else 0.0
        
        return validation_result
    
    def _create_traceability_matrix(self, requirements: list[Requirement], issue: dict[str, Any]) -> dict[str, Any]:
        """创建需求可追溯性矩阵"""
        matrix = {
            'issue_to_requirements': {},
            'requirement_dependencies': {},
            'coverage_analysis': {}
        }
        
        issue_id = issue.get('id', 'unknown')
        
        # Issue到需求的映射
        matrix['issue_to_requirements'][issue_id] = [req.id for req in requirements]
        
        # 需求依赖关系
        for req in requirements:
            if req.dependencies:
                matrix['requirement_dependencies'][req.id] = req.dependencies
        
        # 覆盖度分析
        functional_coverage = len([req for req in requirements if req.type == RequirementType.FUNCTIONAL])
        technical_coverage = len([req for req in requirements if req.type == RequirementType.TECHNICAL])
        
        matrix['coverage_analysis'] = {
            'functional_requirements': functional_coverage,
            'technical_requirements': technical_coverage,
            'total_requirements': len(requirements),
            'explicit_ratio': len([req for req in requirements if req.source == 'explicit']) / len(requirements) if requirements else 0,
            'implicit_ratio': len([req for req in requirements if req.source == 'implicit']) / len(requirements) if requirements else 0
        }
        
        return matrix
    
    def _create_analysis_summary(self, requirements: list[Requirement], constraints: dict[str, Any]) -> dict[str, Any]:
        """创建分析摘要"""
        summary = {
            'total_requirements': len(requirements),
            'by_type': {},
            'by_priority': {},
            'by_source': {},
            'key_constraints': [],
            'recommendations': []
        }
        
        # 按类型统计
        for req_type in RequirementType:
            count = len([req for req in requirements if req.type == req_type])
            summary['by_type'][req_type.value] = count
        
        # 按优先级统计
        for priority in Priority:
            count = len([req for req in requirements if req.priority == priority])
            summary['by_priority'][priority.value] = count
        
        # 按来源统计
        explicit_count = len([req for req in requirements if req.source == 'explicit'])
        implicit_count = len([req for req in requirements if req.source == 'implicit'])
        summary['by_source'] = {
            'explicit': explicit_count,
            'implicit': implicit_count
        }
        
        # 关键约束
        for constraint_type, constraint_list in constraints.items():
            if constraint_list:
                summary['key_constraints'].append(f"{constraint_type}: {', '.join(constraint_list[:3])}")
        
        # 推荐
        if implicit_count > explicit_count:
            summary['recommendations'].append("建议与用户确认隐式需求的准确性")
        
        if summary['by_priority']['critical'] == 0 and summary['by_priority']['high'] == 0:
            summary['recommendations'].append("建议明确需求的优先级")
        
        if not summary['key_constraints']:
            summary['recommendations'].append("建议明确技术约束和限制")
        
        return summary
    
    def _analyze_text_for_requirements(self, text: str, source: str) -> list[tuple[RequirementType, str, Priority]]:
        """分析文本中的需求"""
        requirements = []
        
        if not text.strip():
            return requirements
        
        text_lower = text.lower()
        
        # 功能性需求识别
        for pattern in self.functional_patterns:
            if re.search(pattern, text_lower):
                priority = Priority.HIGH if 'must' in text_lower or 'critical' in text_lower else Priority.MEDIUM
                requirements.append((RequirementType.FUNCTIONAL, f"功能需求: {text}", priority))
                break
        
        # 非功能性需求识别
        for pattern in self.non_functional_patterns:
            if re.search(pattern, text_lower):
                priority = Priority.MEDIUM
                requirements.append((RequirementType.NON_FUNCTIONAL, f"非功能需求: {text}", priority))
                break
        
        # 技术需求识别
        for pattern in self.technical_patterns:
            if re.search(pattern, text_lower):
                priority = Priority.MEDIUM
                requirements.append((RequirementType.TECHNICAL, f"技术需求: {text}", priority))
                break
        
        return requirements
    
    def _extract_analysis_keywords(self, issue: dict[str, Any], requirements: list[Requirement]) -> list[str]:
        """提取分析关键词"""
        keywords = []
        
        # 从Issue中提取
        title_words = issue.get('title', '').lower().split()
        desc_words = issue.get('description', '').lower().split()
        keywords.extend([word for word in title_words + desc_words if len(word) > 3])
        
        # 从需求中提取
        for req in requirements:
            req_words = req.description.lower().split()
            keywords.extend([word for word in req_words if len(word) > 3])
        
        # 去重并限制数量
        unique_keywords = list(set(keywords))[:15]
        return unique_keywords 