"""
记忆管理器
负责存储和检索代理的历史经验、文件分析、解决方案等信息
"""

import json
import os
import time
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict
from typing import TypedDict
import logging

class EnumEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理枚举类型"""
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)

logger = logging.getLogger(__name__)

class MemoryType(Enum):
    """记忆类型枚举"""
    FILE_ANALYSIS = "file_analysis"      # 文件分析结果
    CODE_PATTERN = "code_pattern"        # 代码模式
    PROJECT_STRUCTURE = "project_structure"  # 项目结构
    SOLUTION_APPROACH = "solution_approach"  # 解决方案
    ERROR_PATTERN = "error_pattern"      # 错误模式
    DECISION_REASON = "decision_reason"  # 决策理由
    
    # 新增的记忆类型
    THINKING_PROCESS = "thinking_process"    # AI思考过程
    TODO_LIST = "todo_list"                  # 待办事项列表
    DECISION_LOG = "decision_log"            # 决策日志
    LEARNING_EXPERIENCE = "learning_experience"  # 学习经验
    PROBLEM_SOLVING = "problem_solving"      # 问题解决过程
    CREATIVE_IDEA = "creative_idea"          # 创意想法
    WORKFLOW_PATTERN = "workflow_pattern"    # 工作流程模式
    COLLABORATION_NOTE = "collaboration_note"  # 协作笔记
    CONTEXT_UNDERSTANDING = "context_understanding"  # 上下文理解
    STRATEGY_PLAN = "strategy_plan"          # 策略计划

class MemoryPriority(Enum):
    """记忆优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class MemoryStatus(Enum):
    """记忆状态"""
    ACTIVE = "active"           # 活跃状态
    ARCHIVED = "archived"       # 归档状态
    EXPIRED = "expired"         # 过期状态
    PENDING = "pending"         # 待处理状态

@dataclass
class Memory:
    """记忆数据结构"""
    id: str
    memory_type: MemoryType
    content: dict[str, Any]
    created_at: float
    last_accessed: float
    access_count: int = 0
    keywords: list[str] = field(default_factory=list)
    priority: MemoryPriority = MemoryPriority.MEDIUM
    status: MemoryStatus = MemoryStatus.ACTIVE
    tags: list[str] = field(default_factory=list)
    related_memories: list[str] = field(default_factory=list)  # 相关记忆ID列表
    expiration_time: Optional[float] = None  # 过期时间
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "keywords": self.keywords,
            "priority": self.priority.value,
            "status": self.status.value,
            "tags": self.tags,
            "related_memories": self.related_memories,
            "expiration_time": self.expiration_time
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'Memory':
        """从字典创建实例"""
        return cls(
            id=data["id"],
            memory_type=MemoryType(data["memory_type"]),
            content=data["content"],
            created_at=data["created_at"],
            last_accessed=data["last_accessed"],
            access_count=data.get("access_count", 0),
            keywords=data.get("keywords", []),
            priority=MemoryPriority(data.get("priority", "medium")),
            status=MemoryStatus(data.get("status", "active")),
            tags=data.get("tags", []),
            related_memories=data.get("related_memories", []),
            expiration_time=data.get("expiration_time")
        )

class MemoryManager:
    """记忆管理器"""
    
    def __init__(self, agent_id: str, memory_dir: str = ".memory"):
        self.agent_id = agent_id
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        self.memory_file = self.memory_dir / f"{agent_id}_memory.json"
        self.memories: dict[str, Memory] = {}
        self.max_memories = 2000  # 增加最大记忆数量
        self.max_memory_age_days = 30  # 记忆最大保存天数
        
        # 加载现有记忆
        self._load_memories()
        
        logger.info(f"记忆管理器初始化完成: {agent_id}, 已加载 {len(self.memories)} 条记忆")
    
    def _load_memories(self):
        """加载记忆文件"""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for memory_data in data.get('memories', []):
                        memory = Memory.from_dict(memory_data)
                        # 检查记忆是否过期
                        if self._is_memory_expired(memory):
                            memory.status = MemoryStatus.EXPIRED
                        self.memories[memory.id] = memory
                logger.info(f"成功加载 {len(self.memories)} 条记忆")
            except Exception as e:
                logger.error(f"加载记忆文件失败: {e}")
    
    def _save_memories(self):
        """保存记忆到文件"""
        try:
            data = {
                'agent_id': self.agent_id,
                'timestamp': time.time(),
                'memories': [memory.to_dict() for memory in self.memories.values()]
            }
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, cls=EnumEncoder)
            logger.debug(f"成功保存 {len(self.memories)} 条记忆")
        except Exception as e:
            logger.error(f"保存记忆文件失败: {e}")
    
    def _is_memory_expired(self, memory: Memory) -> bool:
        """检查记忆是否过期"""
        if memory.expiration_time and time.time() > memory.expiration_time:
            return True
        if time.time() - memory.created_at > self.max_memory_age_days * 24 * 3600:
            return True
        return False
    
    def store_memory(self, memory_type: MemoryType, content: dict[str, Any],
                    keywords: list[str] = None, priority: MemoryPriority = MemoryPriority.MEDIUM,
                    tags: list[str] = None, expiration_days: int = None) -> str:
        """存储新记忆
        
        Args:
            memory_type: 记忆类型
            content: 记忆内容
            keywords: 关键词列表
            priority: 优先级
            tags: 标签列表
            expiration_days: 过期天数
            
        Returns:
            记忆ID
        """
        memory_id = f"{memory_type.value}_{int(time.time() * 1000)}"
        current_time = time.time()
        
        # 提取关键词
        if keywords is None:
            keywords = self._extract_keywords(content)
        
        # 设置过期时间
        expiration_time = None
        if expiration_days:
            expiration_time = current_time + expiration_days * 24 * 3600
        
        memory = Memory(
            id=memory_id,
            memory_type=memory_type,
            content=content,
            created_at=current_time,
            last_accessed=current_time,
            keywords=keywords,
            priority=priority,
            tags=tags or [],
            expiration_time=expiration_time
        )
        
        self.memories[memory_id] = memory
        
        # 如果记忆数量超过限制，删除最旧的记忆
        if len(self.memories) > self.max_memories:
            self._cleanup_old_memories()
        
        self._save_memories()
        logger.debug(f"存储新记忆: {memory_id} ({memory_type.value}) - 优先级: {priority.value}")
        
        return memory_id
    
    # 新增：存储思考过程
    def store_thinking_process(self, thought: str, context: dict[str, Any] = None, 
                              conclusion: str = None, confidence: float = None) -> str:
        """存储AI的思考过程"""
        content = {
            "thought": thought,
            "context": context or {},
            "conclusion": conclusion,
            "confidence": confidence,
            "timestamp": time.time()
        }
        
        keywords = self._extract_keywords_from_text(thought)
        if conclusion:
            keywords.extend(self._extract_keywords_from_text(conclusion))
        
        return self.store_memory(
            MemoryType.THINKING_PROCESS,
            content,
            keywords,
            priority=MemoryPriority.HIGH
        )
    
    # 新增：存储待办事项
    def store_todo_item(self, task: str, priority: str = "medium", 
                       due_date: float = None, status: str = "pending") -> str:
        """存储待办事项"""
        content = {
            "task": task,
            "priority": priority,
            "due_date": due_date,
            "status": status,
            "created_at": time.time()
        }
        
        keywords = self._extract_keywords_from_text(task)
        
        return self.store_memory(
            MemoryType.TODO_LIST,
            content,
            keywords,
            priority=MemoryPriority.HIGH if priority == "high" else MemoryPriority.MEDIUM
        )
    
    # 新增：存储决策日志
    def store_decision_log(self, decision: str, alternatives: list[str] = None,
                          reasoning: str = None, outcome: str = None) -> str:
        """存储决策日志"""
        content = {
            "decision": decision,
            "alternatives": alternatives or [],
            "reasoning": reasoning,
            "outcome": outcome,
            "timestamp": time.time()
        }
        
        keywords = self._extract_keywords_from_text(decision)
        if reasoning:
            keywords.extend(self._extract_keywords_from_text(reasoning))
        
        return self.store_memory(
            MemoryType.DECISION_LOG,
            content,
            keywords,
            priority=MemoryPriority.HIGH
        )
    
    # 新增：存储学习经验
    def store_learning_experience(self, lesson: str, context: str = None,
                                 success: bool = None, improvement: str = None) -> str:
        """存储学习经验"""
        content = {
            "lesson": lesson,
            "context": context,
            "success": success,
            "improvement": improvement,
            "timestamp": time.time()
        }
        
        keywords = self._extract_keywords_from_text(lesson)
        
        return self.store_memory(
            MemoryType.LEARNING_EXPERIENCE,
            content,
            keywords,
            priority=MemoryPriority.HIGH
        )
    
    # 新增：存储创意想法
    def store_creative_idea(self, idea: str, category: str = None,
                           potential_impact: str = None, implementation_notes: str = None) -> str:
        """存储创意想法"""
        content = {
            "idea": idea,
            "category": category,
            "potential_impact": potential_impact,
            "implementation_notes": implementation_notes,
            "timestamp": time.time()
        }
        
        keywords = self._extract_keywords_from_text(idea)
        
        return self.store_memory(
            MemoryType.CREATIVE_IDEA,
            content,
            keywords,
            priority=MemoryPriority.MEDIUM
        )
    
    # 新增：获取待办事项
    def get_todo_items(self, status: str = "pending") -> list[Memory]:
        """获取待办事项"""
        todo_memories = []
        for memory in self.memories.values():
            if (memory.memory_type == MemoryType.TODO_LIST and 
                memory.status == MemoryStatus.ACTIVE and
                memory.content.get("status") == status):
                todo_memories.append(memory)
        
        # 按优先级和创建时间排序
        todo_memories.sort(key=lambda x: (
            x.priority.value != "high",  # high优先级在前
            x.created_at  # 创建时间早的在前
        ))
        
        return todo_memories
    
    # 新增：更新待办事项状态
    def update_todo_status(self, memory_id: str, new_status: str) -> bool:
        """更新待办事项状态"""
        if memory_id in self.memories:
            memory = self.memories[memory_id]
            if memory.memory_type == MemoryType.TODO_LIST:
                memory.content["status"] = new_status
                memory.last_accessed = time.time()
                self._save_memories()
                return True
        return False
    
    # 新增：获取最近的思考过程
    def get_recent_thinking_processes(self, limit: int = 10) -> list[Memory]:
        """获取最近的思考过程"""
        thinking_memories = []
        for memory in self.memories.values():
            if (memory.memory_type == MemoryType.THINKING_PROCESS and 
                memory.status == MemoryStatus.ACTIVE):
                thinking_memories.append(memory)
        
        # 按创建时间排序，最新的在前
        thinking_memories.sort(key=lambda x: x.created_at, reverse=True)
        
        return thinking_memories[:limit]
    
    # 新增：获取相关记忆链
    def get_related_memories(self, memory_id: str, limit: int = 5) -> list[Memory]:
        """获取相关记忆链"""
        if memory_id not in self.memories:
            return []
        
        memory = self.memories[memory_id]
        related_memories = []
        
        # 获取直接相关的记忆
        for related_id in memory.related_memories:
            if related_id in self.memories:
                related_memories.append(self.memories[related_id])
        
        # 获取关键词相关的记忆
        for other_memory in self.memories.values():
            if (other_memory.id != memory_id and 
                other_memory.status == MemoryStatus.ACTIVE):
                # 计算关键词重叠度
                overlap = len(set(memory.keywords) & set(other_memory.keywords))
                if overlap > 0:
                    other_memory.content["relevance_score"] = overlap
                    related_memories.append(other_memory)
        
        # 按相关性排序
        related_memories.sort(key=lambda x: x.content.get("relevance_score", 0), reverse=True)
        
        return related_memories[:limit]
    
    # 新增：添加记忆关联
    def link_memories(self, memory_id1: str, memory_id2: str) -> bool:
        """关联两个记忆"""
        if memory_id1 in self.memories and memory_id2 in self.memories:
            self.memories[memory_id1].related_memories.append(memory_id2)
            self.memories[memory_id2].related_memories.append(memory_id1)
            self._save_memories()
            return True
        return False
    
    def retrieve_memories(self, query_keywords: list[str],
                         memory_type: MemoryType = None,
                         limit: int = 10,
                         priority_filter: MemoryPriority = None) -> list[Memory]:
        """检索相关记忆
        
        Args:
            query_keywords: 查询关键词
            memory_type: 记忆类型过滤
            limit: 返回数量限制
            priority_filter: 优先级过滤
            
        Returns:
            相关记忆列表
        """
        relevant_memories = []
        
        for memory in self.memories.values():
            # 状态过滤
            if memory.status != MemoryStatus.ACTIVE:
                continue
            
            # 类型过滤
            if memory_type and memory.memory_type != memory_type:
                continue
            
            # 优先级过滤
            if priority_filter and memory.priority != priority_filter:
                continue
            
            # 计算相关性
            relevance = self._calculate_relevance(memory, query_keywords)
            if relevance > 0:
                # 更新访问信息
                memory.last_accessed = time.time()
                memory.access_count += 1
                relevant_memories.append((memory, relevance))
        
        # 按相关性排序
        relevant_memories.sort(key=lambda x: x[1], reverse=True)
        
        # 返回前limit个
        result = [memory for memory, _ in relevant_memories[:limit]]
        
        if result:
            self._save_memories()
            logger.info(f"检索到 {len(result)} 条相关记忆")
        
        return result

    def get_memory_by_id(self, memory_id: str) -> Optional[Memory]:
        """根据ID获取记忆"""
        return self.memories.get(memory_id)
    
    def update_memory(self, memory_id: str, content: dict[str, Any] = None,
                     keywords: list[str] = None, priority: MemoryPriority = None,
                     tags: list[str] = None) -> bool:
        """更新记忆"""
        if memory_id not in self.memories:
            return False
        
        memory = self.memories[memory_id]
        
        if content is not None:
            memory.content.update(content)
        
        if keywords is not None:
            memory.keywords = keywords
        
        if priority is not None:
            memory.priority = priority
        
        if tags is not None:
            memory.tags = tags
        
        memory.last_accessed = time.time()
        self._save_memories()
        
        logger.debug(f"更新记忆: {memory_id}")
        return True
    
    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        if memory_id in self.memories:
            del self.memories[memory_id]
            self._save_memories()
            logger.debug(f"删除记忆: {memory_id}")
            return True
        return False
    
    def get_statistics(self) -> dict[str, Any]:
        """获取记忆统计信息"""
        stats = {
            "total_memories": len(self.memories),
            "active_memories": 0,
            "archived_memories": 0,
            "expired_memories": 0,
            "by_type": {},
            "by_priority": {},
            "most_accessed": [],
            "recent_memories": []
        }
        
        for memory in self.memories.values():
            # 按状态统计
            if memory.status == MemoryStatus.ACTIVE:
                stats["active_memories"] += 1
            elif memory.status == MemoryStatus.ARCHIVED:
                stats["archived_memories"] += 1
            elif memory.status == MemoryStatus.EXPIRED:
                stats["expired_memories"] += 1
            
            # 按类型统计
            type_name = memory.memory_type.value
            stats["by_type"][type_name] = stats["by_type"].get(type_name, 0) + 1
            
            # 按优先级统计
            priority_name = memory.priority.value
            stats["by_priority"][priority_name] = stats["by_priority"].get(priority_name, 0) + 1
        
        # 获取访问次数最多的记忆
        sorted_by_access = sorted(self.memories.values(), key=lambda x: x.access_count, reverse=True)
        stats["most_accessed"] = [m.id for m in sorted_by_access[:5]]
        
        # 获取最近的记忆
        sorted_by_time = sorted(self.memories.values(), key=lambda x: x.created_at, reverse=True)
        stats["recent_memories"] = [m.id for m in sorted_by_time[:5]]
        
        return stats
    
    def _extract_keywords(self, content: dict[str, Any]) -> list[str]:
        """从内容中提取关键词"""
        keywords = []
        
        def extract_from_value(value):
            if isinstance(value, str):
                # 简单的关键词提取
                words = value.lower().split()
                # 过滤掉常见的无意义词汇
                stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their', 'mine', 'yours', 'his', 'hers', 'ours', 'theirs'}
                keywords.extend([word for word in words if len(word) > 2 and word not in stop_words])
            elif isinstance(value, dict):
                for v in value.values():
                    extract_from_value(v)
            elif isinstance(value, list):
                for item in value:
                    extract_from_value(item)
        
        extract_from_value(content)
        return list(set(keywords))  # 去重
    
    def _extract_keywords_from_text(self, text: str) -> list[str]:
        """从文本中提取关键词"""
        if not text:
            return []
        
        words = text.lower().split()
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their', 'mine', 'yours', 'his', 'hers', 'ours', 'theirs'}
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        return list(set(keywords))
    
    def _calculate_relevance(self, memory: Memory, query_keywords: list[str]) -> float:
        """计算记忆与查询的相关性"""
        if not query_keywords:
            return 0.0
        
        # 关键词匹配度
        keyword_matches = len(set(memory.keywords) & set(query_keywords))
        keyword_score = keyword_matches / len(query_keywords)
        
        # 优先级权重
        priority_weights = {
            MemoryPriority.LOW: 0.5,
            MemoryPriority.MEDIUM: 1.0,
            MemoryPriority.HIGH: 1.5,
            MemoryPriority.CRITICAL: 2.0
        }
        priority_score = priority_weights.get(memory.priority, 1.0)
        
        # 时间衰减（越新的记忆权重越高）
        time_decay = 1.0 / (1.0 + (time.time() - memory.created_at) / (24 * 3600))  # 按天衰减
        
        # 访问频率权重
        access_score = min(memory.access_count / 10.0, 1.0)  # 最多1.0
        
        # 综合评分
        relevance = keyword_score * priority_score * time_decay * (1.0 + access_score * 0.5)
        
        return relevance
    
    def _cleanup_old_memories(self):
        """清理旧记忆"""
        # 按访问时间和访问次数排序
        sorted_memories = sorted(
            self.memories.values(),
            key=lambda x: (x.last_accessed, x.access_count)
        )
        
        # 删除最旧的20%的记忆
        delete_count = len(self.memories) // 5
        for memory in sorted_memories[:delete_count]:
            del self.memories[memory.id]
        
        logger.info(f"清理了 {delete_count} 条旧记忆")
    
    def clear_all_memories(self):
        """清空所有记忆"""
        self.memories.clear()
        self._save_memories()
        logger.info("已清空所有记忆")
    
    def export_memories(self, file_path: str = None) -> str:
        """导出记忆到文件"""
        if file_path is None:
            file_path = f"{self.agent_id}_memories_export_{int(time.time())}.json"
        
        export_data = {
            "agent_id": self.agent_id,
            "export_time": time.time(),
            "memories": [memory.to_dict() for memory in self.memories.values()]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, cls=EnumEncoder)
        
        logger.info(f"记忆已导出到: {file_path}")
        return file_path
    
    def import_memories(self, file_path: str) -> bool:
        """从文件导入记忆"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            imported_count = 0
            for memory_data in data.get('memories', []):
                memory = Memory.from_dict(memory_data)
                # 避免ID冲突
                if memory.id not in self.memories:
                    self.memories[memory.id] = memory
                    imported_count += 1
            
            self._save_memories()
            logger.info(f"成功导入 {imported_count} 条记忆")
            return True
            
        except Exception as e:
            logger.error(f"导入记忆失败: {e}")
            return False
    
    def store_ai_decision(self, context: str, decision: str, reasoning: str = None, 
                         alternatives: list[str] = None, confidence: float = None,
                         impact: str = None) -> str:
        """存储AI的自主决策
        
        Args:
            context: 决策上下文
            decision: 决策内容
            reasoning: 决策理由
            alternatives: 其他可选方案
            confidence: 信心度
            impact: 预期影响
            
        Returns:
            记忆ID
        """
        content = {
            "context": context,
            "decision": decision,
            "reasoning": reasoning,
            "alternatives": alternatives or [],
            "confidence": confidence,
            "impact": impact,
            "timestamp": time.time()
        }
        
        return self.store_memory(
            MemoryType.DECISION_LOG,
            content,
            keywords=self._extract_keywords_from_text(f"{context} {decision}"),
            priority=MemoryPriority.HIGH if confidence and confidence > 0.8 else MemoryPriority.MEDIUM,
            tags=["ai_decision", "autonomous"]
        )
    
    def store_workflow_insight(self, workflow_type: str, insight: str, 
                             efficiency_score: float = None, 
                             improvement_suggestions: list[str] = None) -> str:
        """存储工作流程洞察
        
        Args:
            workflow_type: 工作流程类型
            insight: 洞察内容
            efficiency_score: 效率评分
            improvement_suggestions: 改进建议
            
        Returns:
            记忆ID
        """
        content = {
            "workflow_type": workflow_type,
            "insight": insight,
            "efficiency_score": efficiency_score,
            "improvement_suggestions": improvement_suggestions or [],
            "timestamp": time.time()
        }
        
        return self.store_memory(
            MemoryType.WORKFLOW_PATTERN,
            content,
            keywords=[workflow_type, "workflow", "insight"],
            priority=MemoryPriority.MEDIUM,
            tags=["workflow", "optimization"]
        )
    
    def store_collaboration_note(self, partner_id: str, interaction_type: str,
                               note: str, outcome: str = None, 
                               next_actions: list[str] = None) -> str:
        """存储协作笔记
        
        Args:
            partner_id: 协作伙伴ID
            interaction_type: 交互类型
            note: 笔记内容
            outcome: 结果
            next_actions: 后续行动
            
        Returns:
            记忆ID
        """
        content = {
            "partner_id": partner_id,
            "interaction_type": interaction_type,
            "note": note,
            "outcome": outcome,
            "next_actions": next_actions or [],
            "timestamp": time.time()
        }
        
        return self.store_memory(
            MemoryType.COLLABORATION_NOTE,
            content,
            keywords=[partner_id, interaction_type, "collaboration"],
            priority=MemoryPriority.MEDIUM,
            tags=["collaboration", "interaction"]
        )
    
    def store_context_understanding(self, context_type: str, understanding: str,
                                  confidence: float = None, 
                                  related_contexts: list[str] = None) -> str:
        """存储上下文理解
        
        Args:
            context_type: 上下文类型
            understanding: 理解内容
            confidence: 理解信心度
            related_contexts: 相关上下文
            
        Returns:
            记忆ID
        """
        content = {
            "context_type": context_type,
            "understanding": understanding,
            "confidence": confidence,
            "related_contexts": related_contexts or [],
            "timestamp": time.time()
        }
        
        return self.store_memory(
            MemoryType.CONTEXT_UNDERSTANDING,
            content,
            keywords=[context_type, "context", "understanding"],
            priority=MemoryPriority.HIGH if confidence and confidence > 0.8 else MemoryPriority.MEDIUM,
            tags=["context", "understanding"]
        )
    
    def store_strategy_plan(self, strategy_name: str, plan: str, 
                          objectives: list[str] = None, timeline: str = None,
                          success_metrics: list[str] = None) -> str:
        """存储策略计划
        
        Args:
            strategy_name: 策略名称
            plan: 计划内容
            objectives: 目标列表
            timeline: 时间线
            success_metrics: 成功指标
            
        Returns:
            记忆ID
        """
        content = {
            "strategy_name": strategy_name,
            "plan": plan,
            "objectives": objectives or [],
            "timeline": timeline,
            "success_metrics": success_metrics or [],
            "timestamp": time.time()
        }
        
        return self.store_memory(
            MemoryType.STRATEGY_PLAN,
            content,
            keywords=[strategy_name, "strategy", "plan"],
            priority=MemoryPriority.HIGH,
            tags=["strategy", "planning"]
        )
    
    def get_ai_decisions(self, context_keywords: list[str] = None, 
                        limit: int = 10) -> list[Memory]:
        """获取AI决策记录
        
        Args:
            context_keywords: 上下文关键词
            limit: 返回数量限制
            
        Returns:
            AI决策记忆列表
        """
        return self.retrieve_memories(
            query_keywords=context_keywords or [],
            memory_type=MemoryType.DECISION_LOG,
            limit=limit
        )
    
    def get_workflow_insights(self, workflow_type: str = None, 
                            limit: int = 10) -> list[Memory]:
        """获取工作流程洞察
        
        Args:
            workflow_type: 工作流程类型
            limit: 返回数量限制
            
        Returns:
            工作流程洞察列表
        """
        memories = self.retrieve_memories(
            query_keywords=[workflow_type] if workflow_type else [],
            memory_type=MemoryType.WORKFLOW_PATTERN,
            limit=limit
        )
        return memories
    
    def get_collaboration_history(self, partner_id: str = None, 
                                limit: int = 10) -> list[Memory]:
        """获取协作历史
        
        Args:
            partner_id: 伙伴ID
            limit: 返回数量限制
            
        Returns:
            协作历史列表
        """
        return self.retrieve_memories(
            query_keywords=[partner_id] if partner_id else ["collaboration"],
            memory_type=MemoryType.COLLABORATION_NOTE,
            limit=limit
        )
    
    def get_context_understandings(self, context_type: str = None, 
                                 limit: int = 10) -> list[Memory]:
        """获取上下文理解记录
        
        Args:
            context_type: 上下文类型
            limit: 返回数量限制
            
        Returns:
            上下文理解列表
        """
        return self.retrieve_memories(
            query_keywords=[context_type] if context_type else ["context"],
            memory_type=MemoryType.CONTEXT_UNDERSTANDING,
            limit=limit
        )
    
    def get_strategy_plans(self, strategy_name: str = None, 
                         limit: int = 10) -> list[Memory]:
        """获取策略计划
        
        Args:
            strategy_name: 策略名称
            limit: 返回数量限制
            
        Returns:
            策略计划列表
        """
        return self.retrieve_memories(
            query_keywords=[strategy_name] if strategy_name else ["strategy"],
            memory_type=MemoryType.STRATEGY_PLAN,
            limit=limit
        ) 