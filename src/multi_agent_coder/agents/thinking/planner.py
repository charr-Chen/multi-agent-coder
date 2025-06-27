"""
规划器模块
实现思考链（Chain of Thought），将复杂任务分解为多个可执行的步骤
"""

import logging
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

class TaskType(Enum):
    """任务类型枚举"""
    ANALYSIS = "analysis"           # 分析任务
    DESIGN = "design"              # 设计任务
    IMPLEMENTATION = "implementation"  # 实现任务
    TESTING = "testing"            # 测试任务
    DEBUGGING = "debugging"        # 调试任务
    OPTIMIZATION = "optimization"  # 优化任务
    DOCUMENTATION = "documentation"

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"

class Priority(Enum):
    """优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class Task:
    """任务数据结构"""
    id: str
    task_type: TaskType
    title: str
    description: str
    priority: Priority
    estimated_duration: int  # 预计耗时（分钟）
    dependencies: list[str] = field(default_factory=list)  # 依赖的任务ID
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "task_type": self.task_type.value,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "estimated_duration": self.estimated_duration,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "assigned_agent": self.assigned_agent,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error_message": self.error_message
        }

@dataclass
class ExecutionPlan:
    """执行计划数据结构"""
    id: str
    issue_id: str
    title: str
    description: str
    created_at: float
    tasks: list[Task]
    estimated_total_duration: int  # 总预计耗时（分钟）
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "issue_id": self.issue_id,
            "title": self.title,
            "description": self.description,
            "created_at": self.created_at,
            "tasks": [task.to_dict() for task in self.tasks],
            "estimated_total_duration": self.estimated_total_duration
        }

class Planner:
    """规划器 - 实现思考链功能"""
    
    def __init__(self, llm_manager=None):
        self.llm_manager = llm_manager
        self.current_plan: Optional[ExecutionPlan] = None
        self.task_queue: list[Task] = []
        self.completed_tasks: list[Task] = []
        self.failed_tasks: list[Task] = []
        
        logger.info("规划器初始化完成")
    
    async def create_execution_plan(self, issue: dict[str, Any], context: dict[str, Any] = None) -> ExecutionPlan:
        """创建执行计划
        
        Args:
            issue: Issue信息
            context: 上下文信息
            
        Returns:
            执行计划
        """
        logger.info(f"开始创建执行计划: {issue.get('title', 'Unknown')}")
        
        # 思考链的5个步骤
        thinking_steps = [
            "理解问题和需求",
            "分析问题复杂度",
            "选择解决方法",
            "分解具体任务",
            "优化执行顺序"
        ]
        
        plan_id = f"plan_{int(time.time() * 1000)}"
        tasks = []
        
        # 第1步：理解问题和需求
        logger.info("🤔 步骤1: 理解问题和需求")
        understanding = await self._understand_requirements(issue, context)
        
        # 第2步：分析问题复杂度
        logger.info("🔍 步骤2: 分析问题复杂度")
        complexity_analysis = self._analyze_complexity(issue, understanding)
        
        # 第3步：选择解决方法
        logger.info("💡 步骤3: 选择解决方法")
        solution_approach = self._choose_solution_approach(complexity_analysis)
        
        # 第4步：分解具体任务
        logger.info("📋 步骤4: 分解具体任务")
        tasks = self._decompose_tasks(issue, solution_approach, context)
        
        # 第5步：优化执行顺序
        logger.info("⚡ 步骤5: 优化执行顺序")
        optimized_tasks = self._optimize_task_order(tasks)
        
        # 创建执行计划
        total_time = sum(task.estimated_duration for task in optimized_tasks)
        
        execution_plan = ExecutionPlan(
            id=plan_id,
            issue_id=issue.get('id', 'unknown'),
            title=f"执行计划: {issue.get('title', 'Unknown')}",
            description=f"基于{solution_approach['strategy']}方法的{len(optimized_tasks)}个任务执行计划",
            created_at=time.time(),
            tasks=optimized_tasks,
            estimated_total_duration=total_time
        )
        
        self.current_plan = execution_plan
        self.task_queue = optimized_tasks.copy()
        
        logger.info(f"✅ 执行计划创建完成: {len(optimized_tasks)} 个任务, 预计 {total_time} 分钟")
        
        return execution_plan
    
    async def _understand_requirements(self, issue: dict[str, Any], context: dict[str, Any] = None) -> dict[str, Any]:
        """理解需求"""
        understanding = {
            'title': issue.get('title', ''),
            'description': issue.get('description', ''),
            'keywords': self._extract_keywords(issue),
            'requirements_type': self._classify_requirement_type(issue),
            'complexity_indicators': self._identify_complexity_indicators(issue),
            'context_info': context or {}
        }
        
        logger.debug(f"需求理解完成: {understanding['requirements_type']}")
        return understanding
    
    def _analyze_complexity(self, issue: dict[str, Any], understanding: dict[str, Any]) -> dict[str, Any]:
        """分析复杂度"""
        complexity_score = 0
        factors = []
        
        # 基于关键词判断复杂度
        complex_keywords = ['integrate', 'system', 'architecture', 'framework', 'multiple', 'complex']
        simple_keywords = ['fix', 'update', 'add', 'simple', 'basic']
        
        title_lower = issue.get('title', '').lower()
        desc_lower = issue.get('description', '').lower()
        
        for keyword in complex_keywords:
            if keyword in title_lower or keyword in desc_lower:
                complexity_score += 2
                factors.append(f"包含复杂关键词: {keyword}")
        
        for keyword in simple_keywords:
            if keyword in title_lower or keyword in desc_lower:
                complexity_score -= 1
                factors.append(f"包含简单关键词: {keyword}")
        
        # 基于描述长度判断
        desc_length = len(issue.get('description', ''))
        if desc_length > 500:
            complexity_score += 2
            factors.append("描述详细，可能涉及多个方面")
        elif desc_length < 100:
            complexity_score -= 1
            factors.append("描述简短，可能是简单任务")
        
        # 规范化复杂度分数 (1-10)
        complexity_level = max(1, min(10, complexity_score + 5))
        
        return {
            'complexity_level': complexity_level,
            'factors': factors,
            'estimated_difficulty': 'high' if complexity_level >= 7 else 'medium' if complexity_level >= 4 else 'low'
        }
    
    def _choose_solution_approach(self, complexity_analysis: dict[str, Any]) -> dict[str, Any]:
        """选择解决方法"""
        complexity_level = complexity_analysis['complexity_level']
        
        if complexity_level >= 7:
            # 高复杂度：分阶段实现
            approach = {
                'strategy': 'phased_implementation',
                'phases': ['analysis', 'design', 'core_implementation', 'testing', 'optimization'],
                'parallel_tasks': False,
                'review_points': ['design_review', 'implementation_review']
            }
        elif complexity_level >= 4:
            # 中等复杂度：标准流程
            approach = {
                'strategy': 'standard_implementation',
                'phases': ['analysis', 'implementation', 'testing'],
                'parallel_tasks': True,
                'review_points': ['implementation_review']
            }
        else:
            # 低复杂度：快速实现
            approach = {
                'strategy': 'rapid_implementation',
                'phases': ['quick_analysis', 'direct_implementation'],
                'parallel_tasks': True,
                'review_points': []
            }
        
        logger.debug(f"选择解决方法: {approach['strategy']}")
        return approach
    
    def _decompose_tasks(self, issue: dict[str, Any], solution_approach: dict[str, Any], 
                        context: dict[str, Any] = None) -> list[Task]:
        """分解任务"""
        tasks = []
        task_counter = 1
        
        strategy = solution_approach['strategy']
        phases = solution_approach['phases']
        
        for phase in phases:
            if phase == 'analysis' or phase == 'quick_analysis':
                tasks.extend(self._create_analysis_tasks(issue, task_counter))
                task_counter += len(tasks)
                
            elif phase == 'design':
                tasks.extend(self._create_design_tasks(issue, task_counter))
                task_counter += len(tasks)
                
            elif phase == 'implementation' or phase == 'core_implementation' or phase == 'direct_implementation':
                tasks.extend(self._create_implementation_tasks(issue, task_counter))
                task_counter += len(tasks)
                
            elif phase == 'testing':
                tasks.extend(self._create_testing_tasks(issue, task_counter))
                task_counter += len(tasks)
                
            elif phase == 'optimization':
                tasks.extend(self._create_optimization_tasks(issue, task_counter))
                task_counter += len(tasks)
        
        return tasks
    
    def _create_analysis_tasks(self, issue: dict[str, Any], start_id: int) -> list[Task]:
        """创建分析任务"""
        tasks = []
        
        # 需求分析任务
        tasks.append(Task(
            id=f"task_{start_id}",
            task_type=TaskType.ANALYSIS,
            title="深度需求分析",
            description="详细分析需求、识别边界条件和潜在风险",
            priority=Priority.HIGH,
            estimated_duration=45
        ))
        
        # 代码结构分析任务
        tasks.append(Task(
            id=f"task_{start_id + 1}",
            task_type=TaskType.ANALYSIS,
            title="技术调研",
            description="调研相关技术、框架和最佳实践",
            priority=Priority.HIGH,
            estimated_duration=60
        ))
        
        tasks.append(Task(
            id=f"task_{start_id + 2}",
            task_type=TaskType.ANALYSIS,
            title="依赖关系分析",
            description="分析与现有代码的依赖关系和影响范围",
            priority=Priority.MEDIUM,
            estimated_duration=30,
            dependencies=[f"task_{start_id}"]
        ))
        
        return tasks
    
    def _create_design_tasks(self, issue: dict[str, Any], start_id: int) -> list[Task]:
        """创建设计任务"""
        tasks = []
        
        tasks.append(Task(
            id=f"task_{start_id}",
            task_type=TaskType.DESIGN,
            title="架构设计",
            description="设计整体架构和模块结构",
            priority=Priority.HIGH,
            estimated_duration=60
        ))
        
        tasks.append(Task(
            id=f"task_{start_id + 1}",
            task_type=TaskType.DESIGN,
            title="接口设计",
            description="设计API接口和数据结构",
            priority=Priority.HIGH,
            estimated_duration=45,
            dependencies=[f"task_{start_id}"]
        ))
        
        tasks.append(Task(
            id=f"task_{start_id + 2}",
            task_type=TaskType.DESIGN,
            title="数据模型设计",
            description="设计数据模型和存储方案",
            priority=Priority.MEDIUM,
            estimated_duration=30,
            dependencies=[f"task_{start_id}"]
        ))
        
        return tasks
    
    def _create_implementation_tasks(self, issue: dict[str, Any], start_id: int) -> list[Task]:
        """创建实现任务"""
        tasks = []
        
        # 核心实现任务
        tasks.append(Task(
            id=f"task_{start_id}",
            task_type=TaskType.IMPLEMENTATION,
            title="核心模块实现",
            description="实现核心业务逻辑模块",
            priority=Priority.HIGH,
            estimated_duration=120
        ))
        
        # 错误处理任务
        tasks.append(Task(
            id=f"task_{start_id + 1}",
            task_type=TaskType.IMPLEMENTATION,
            title="辅助功能实现",
            description="实现辅助功能和工具类",
            priority=Priority.MEDIUM,
            estimated_duration=60,
            dependencies=[f"task_{start_id}"]
        ))
        
        # 接口集成任务
        tasks.append(Task(
            id=f"task_{start_id + 2}",
            task_type=TaskType.IMPLEMENTATION,
            title="接口集成",
            description="集成各模块接口，确保数据流通",
            priority=Priority.HIGH,
            estimated_duration=45,
            dependencies=[f"task_{start_id}", f"task_{start_id + 1}"]
        ))
        
        return tasks
    
    def _create_testing_tasks(self, issue: dict[str, Any], start_id: int) -> list[Task]:
        """创建测试任务"""
        tasks = []
        
        tasks.append(Task(
            id=f"task_{start_id}",
            task_type=TaskType.TESTING,
            title="单元测试",
            description="编写和执行单元测试",
            priority=Priority.HIGH,
            estimated_duration=60
        ))
        
        tasks.append(Task(
            id=f"task_{start_id + 1}",
            task_type=TaskType.TESTING,
            title="集成测试",
            description="测试模块间集成和接口",
            priority=Priority.HIGH,
            estimated_duration=45,
            dependencies=[f"task_{start_id}"]
        ))
        
        tasks.append(Task(
            id=f"task_{start_id + 2}",
            task_type=TaskType.TESTING,
            title="端到端测试",
            description="完整流程的端到端测试",
            priority=Priority.MEDIUM,
            estimated_duration=45,
            dependencies=[f"task_{start_id + 1}"]
        ))
        
        return tasks
    
    def _create_optimization_tasks(self, issue: dict[str, Any], start_id: int) -> list[Task]:
        """创建优化任务"""
        tasks = []
        
        tasks.append(Task(
            id=f"task_{start_id}",
            task_type=TaskType.OPTIMIZATION,
            title="性能优化",
            description="分析和优化性能瓶颈",
            priority=Priority.MEDIUM,
            estimated_duration=60
        ))
        
        tasks.append(Task(
            id=f"task_{start_id + 1}",
            task_type=TaskType.OPTIMIZATION,
            title="代码重构",
            description="重构代码提高可维护性",
            priority=Priority.LOW,
            estimated_duration=45
        ))
        
        tasks.append(Task(
            id=f"task_{start_id + 2}",
            task_type=TaskType.DOCUMENTATION,
            title="文档编写",
            description="编写技术文档和使用说明",
            priority=Priority.MEDIUM,
            estimated_duration=30
        ))
        
        return tasks
    
    def _optimize_task_order(self, tasks: list[Task]) -> list[Task]:
        """优化任务执行顺序"""
        # 拓扑排序，确保依赖关系正确
        sorted_tasks = []
        remaining_tasks = tasks.copy()
        
        while remaining_tasks:
            # 找到没有未满足依赖的任务
            ready_tasks = []
            for task in remaining_tasks:
                if all(dep_id in [t.id for t in sorted_tasks] for dep_id in task.dependencies):
                    ready_tasks.append(task)
            
            if not ready_tasks:
                # 如果没有ready的任务，说明有循环依赖，强制添加第一个
                ready_tasks = [remaining_tasks[0]]
                logger.warning("检测到可能的循环依赖，强制添加任务")
            
            # 按优先级排序ready的任务
            ready_tasks.sort(key=lambda x: x.priority.value, reverse=True)
            
            # 添加优先级最高的任务
            selected_task = ready_tasks[0]
            sorted_tasks.append(selected_task)
            remaining_tasks.remove(selected_task)
        
        return sorted_tasks
    
    def get_next_task(self) -> Optional[Task]:
        """获取下一个要执行的任务"""
        if not self.task_queue:
            return None
        
        # 找到第一个状态为PENDING且依赖已满足的任务
        for task in self.task_queue:
            if task.status == TaskStatus.PENDING:
                # 检查依赖是否已完成
                if all(dep_id in [t.id for t in self.completed_tasks] for dep_id in task.dependencies):
                    return task
        
        return None
    
    def update_task_status(self, task_id: str, status: TaskStatus, result: dict[str, Any] = None):
        """更新任务状态"""
        task = self._find_task_by_id(task_id)
        if not task:
            logger.warning(f"未找到任务: {task_id}")
            return
        
        task.status = status
        
        if status == TaskStatus.IN_PROGRESS:
            task.started_at = time.time()
        elif status == TaskStatus.COMPLETED:
            task.completed_at = time.time()
            task.result = result
            if task in self.task_queue:
                self.task_queue.remove(task)
            self.completed_tasks.append(task)
        elif status == TaskStatus.FAILED:
            task.completed_at = time.time()
            if task in self.task_queue:
                self.task_queue.remove(task)
            self.failed_tasks.append(task)
        
        logger.debug(f"任务状态更新: {task_id} -> {status.value}")
    
    def get_plan_progress(self) -> dict[str, Any]:
        """获取计划执行进度"""
        if not self.current_plan:
            return {'error': '没有活动的执行计划'}
        
        total_tasks = len(self.current_plan.tasks)
        completed_count = len(self.completed_tasks)
        failed_count = len(self.failed_tasks)
        in_progress_count = len([t for t in self.task_queue if t.status == TaskStatus.IN_PROGRESS])
        pending_count = len([t for t in self.task_queue if t.status == TaskStatus.PENDING])
        
        return {
            'plan_id': self.current_plan.id,
            'total_tasks': total_tasks,
            'completed': completed_count,
            'failed': failed_count,
            'in_progress': in_progress_count,
            'pending': pending_count,
            'progress_percentage': (completed_count / total_tasks * 100) if total_tasks > 0 else 0,
            'estimated_remaining_time': sum(t.estimated_duration for t in self.task_queue)
        }
    
    def _find_task_by_id(self, task_id: str) -> Optional[Task]:
        """根据ID查找任务"""
        all_tasks = self.task_queue + self.completed_tasks + self.failed_tasks
        for task in all_tasks:
            if task.id == task_id:
                return task
        return None
    
    def _extract_keywords(self, issue: dict[str, Any]) -> list[str]:
        """提取关键词"""
        text = f"{issue.get('title', '')} {issue.get('description', '')}"
        words = text.lower().split()
        # 简单的关键词提取，过滤常见词汇
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]
        return list(set(keywords))[:10]  # 限制数量
    
    def _classify_requirement_type(self, issue: dict[str, Any]) -> str:
        """分类需求类型"""
        title_lower = issue.get('title', '').lower()
        
        if any(word in title_lower for word in ['fix', 'bug', 'error', 'issue']):
            return 'bug_fix'
        elif any(word in title_lower for word in ['add', 'new', 'create', 'implement']):
            return 'new_feature'
        elif any(word in title_lower for word in ['update', 'modify', 'change', 'improve']):
            return 'enhancement'
        elif any(word in title_lower for word in ['test', 'testing']):
            return 'testing'
        else:
            return 'general'
    
    def _identify_complexity_indicators(self, issue: dict[str, Any]) -> list[str]:
        """识别复杂度指标"""
        indicators = []
        text = f"{issue.get('title', '')} {issue.get('description', '')}".lower()
        
        complexity_patterns = {
            'multiple_components': ['multiple', 'several', 'various', 'different'],
            'integration': ['integrate', 'connect', 'combine', 'merge'],
            'system_level': ['system', 'architecture', 'framework', 'platform'],
            'data_processing': ['database', 'data', 'processing', 'algorithm'],
            'ui_complexity': ['interface', 'ui', 'frontend', 'user experience']
        }
        
        for indicator, keywords in complexity_patterns.items():
            if any(keyword in text for keyword in keywords):
                indicators.append(indicator)
        
        return indicators 