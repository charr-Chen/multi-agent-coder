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
from typing import Any, Optional
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

class MemoryContent(TypedDict):
    """记忆内容类型"""
    file_analysis: dict[str, Any]
    code_pattern: dict[str, Any]
    project_structure: dict[str, Any]
    solution_approach: dict[str, Any]
    error_pattern: dict[str, Any]
    decision_reason: dict[str, Any]

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
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "keywords": self.keywords
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
            keywords=data.get("keywords", [])
        )

class MemoryManager:
    """记忆管理器"""
    
    def __init__(self, agent_id: str, memory_dir: str = ".memory"):
        self.agent_id = agent_id
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        self.memory_file = self.memory_dir / f"{agent_id}_memory.json"
        self.memories: dict[str, Memory] = {}
        self.max_memories = 1000  # 最大记忆数量
        
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
    
    def store_memory(self, memory_type: MemoryType, content: dict[str, Any],
                    keywords: list[str] = None) -> str:
        """存储新记忆
        
        Args:
            memory_type: 记忆类型
            content: 记忆内容
            keywords: 关键词列表
            
        Returns:
            记忆ID
        """
        memory_id = f"{memory_type.value}_{int(time.time() * 1000)}"
        current_time = time.time()
        
        # 提取关键词
        if keywords is None:
            keywords = self._extract_keywords(content)
        
        memory = Memory(
            id=memory_id,
            memory_type=memory_type,
            content=content,
            created_at=current_time,
            last_accessed=current_time,
            keywords=keywords
        )
        
        self.memories[memory_id] = memory
        
        # 如果记忆数量超过限制，删除最旧的记忆
        if len(self.memories) > self.max_memories:
            self._cleanup_old_memories()
        
        self._save_memories()
        logger.debug(f"存储新记忆: {memory_id} ({memory_type.value})")
        
        return memory_id
    
    def retrieve_memories(self, query_keywords: list[str],
                         memory_type: MemoryType = None,
                         limit: int = 10) -> list[Memory]:
        """检索相关记忆
        
        Args:
            query_keywords: 查询关键词
            memory_type: 记忆类型过滤
            limit: 返回数量限制
            
        Returns:
            相关记忆列表
        """
        relevant_memories = []
        
        for memory in self.memories.values():
            # 类型过滤
            if memory_type and memory.memory_type != memory_type:
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
            # 保存更新的访问信息
            self._save_memories()
            logger.info(f"检索到 {len(result)} 条相关记忆")
        
        return result
    
    def get_memory_by_id(self, memory_id: str) -> Optional[Memory]:
        """根据ID获取记忆"""
        memory = self.memories.get(memory_id)
        if memory:
            memory.access_count += 1
            self._save_memories()
        return memory
    
    def update_memory(self, memory_id: str, content: dict[str, Any] = None,
                     keywords: list[str] = None) -> bool:
        """更新记忆
        
        Args:
            memory_id: 记忆ID
            content: 新内容
            keywords: 新关键词
            
        Returns:
            是否更新成功
        """
        if memory_id not in self.memories:
            logger.warning(f"记忆ID不存在: {memory_id}")
            return False
        
        memory = self.memories[memory_id]
        
        if content:
            memory.content.update(content)
        
        if keywords:
            memory.keywords = keywords
        elif content:
            # 重新提取关键词
            memory.keywords = self._extract_keywords(memory.content)
        
        memory.last_accessed = time.time()
        self._save_memories()
        
        logger.info(f"更新记忆: {memory_id}")
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
        type_counts = {}
        total_accesses = 0
        
        for memory in self.memories.values():
            type_name = memory.memory_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
            total_accesses += memory.access_count
        
        return {
            "total_memories": len(self.memories),
            "type_distribution": type_counts,
            "total_accesses": total_accesses,
            "average_accesses": total_accesses / len(self.memories) if self.memories else 0
        }
    
    def _extract_keywords(self, content: dict[str, Any]) -> list[str]:
        """从内容中提取关键词"""
        keywords = []
        
        def extract_from_value(value):
            if isinstance(value, str):
                # 简单的关键词提取
                words = value.lower().split()
                keywords.extend([word.strip('.,!?;:"()[]{}') for word in words 
                               if len(word) > 3 and word.isalpha()])
            elif isinstance(value, dict):
                for v in value.values():
                    extract_from_value(v)
            elif isinstance(value, list):
                for item in value:
                    extract_from_value(item)
        
        extract_from_value(content)
        
        # 去重并限制数量
        return list(set(keywords))[:20]
    
    def _calculate_relevance(self, memory: Memory, query_keywords: list[str]) -> float:
        """计算记忆与查询关键词的相关性"""
        if not query_keywords:
            return 0.0
        
        memory_keywords = set(memory.keywords)
        query_keywords_set = set(query_keywords)
        
        # 计算交集比例
        intersection = memory_keywords.intersection(query_keywords_set)
        union = memory_keywords.union(query_keywords_set)
        
        if not union:
            return 0.0
        
        # Jaccard相似度
        jaccard_similarity = len(intersection) / len(union)
        
        # 考虑访问频率（热度）
        access_weight = min(memory.access_count / 10.0, 1.0)
        
        # 考虑时间衰减（新记忆权重更高）
        time_weight = 1.0 / (1.0 + (time.time() - memory.created_at) / (24 * 3600))
        
        return jaccard_similarity * (1 + access_weight * 0.2 + time_weight * 0.1)
    
    def _cleanup_old_memories(self):
        """清理旧记忆"""
        # 按时间戳排序，删除最旧的记忆
        sorted_memories = sorted(self.memories.values(), key=lambda x: x.created_at)
        
        # 删除最旧的10%记忆
        delete_count = max(1, len(sorted_memories) // 10)
        
        for memory in sorted_memories[:delete_count]:
            del self.memories[memory.id]
        
        logger.info(f"清理了 {delete_count} 条旧记忆")
    
    def clear_all_memories(self):
        """清空所有记忆"""
        self.memories.clear()
        self._save_memories()
        logger.info("已清空所有记忆") 