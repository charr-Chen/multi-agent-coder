"""
记忆管理器
负责存储和检索代理的历史经验，使用自然语言处理，以纯文本格式存储
"""

import os
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict
from datetime import datetime, timezone
import logging
import re

logger = logging.getLogger(__name__)

@dataclass
class Memory:
    """简化的记忆数据结构"""
    create_at: datetime
    context: str
    
    def to_text_line(self) -> str:
        """转换为文本行格式"""
        timestamp = self.create_at.strftime('%Y-%m-%d %H:%M:%S')
        return f"[{timestamp}] {self.context}"
    
    @classmethod
    def from_text_line(cls, line: str) -> Optional['Memory']:
        """从文本行创建实例"""
        # 匹配格式: [2025-07-03 10:41:52] 记忆内容
        match = re.match(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] (.+)', line.strip())
        if match:
            try:
                timestamp_str = match.group(1)
                context = match.group(2)
                create_at = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
                return cls(create_at=create_at, context=context)
            except ValueError:
                logger.warning(f"无法解析时间戳: {line}")
                return None
        return None

class MemoryManager:
    """简化的记忆管理器 - 纯文本格式"""
    
    def __init__(self, agent_id: str, memory_dir: str = ".memory"):
        self.agent_id = agent_id
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        self.memory_file = self.memory_dir / f"{agent_id}_memory.txt"
        self.memories: List[Memory] = []
        self.max_memories = 500  # 最大记忆数量
        self.max_memory_age_days = 30  # 记忆最大保存天数
        
        # 加载现有记忆
        self._load_memories()
        
        logger.info(f"记忆管理器初始化完成: {agent_id}, 已加载 {len(self.memories)} 条记忆")
    
    def _load_memories(self):
        """从纯文本文件加载记忆"""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 解析文本内容
                lines = content.split('\n')
                memories_loaded = 0
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('[') and ']' in line:
                        memory = Memory.from_text_line(line)
                        if memory and not self._is_memory_expired(memory):
                            self.memories.append(memory)
                            memories_loaded += 1
                
                logger.info(f"成功加载 {memories_loaded} 条记忆")
            except Exception as e:
                logger.error(f"加载记忆文件失败: {e}")
    
    def _save_memories(self):
        """保存记忆到纯文本文件"""
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                # 写入文件头
                f.write(f"=== Agent: {self.agent_id} ===\n")
                f.write(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Memories: {len(self.memories)}\n")
                f.write("\n")
                
                # 按时间排序并写入记忆
                sorted_memories = sorted(self.memories, key=lambda m: m.create_at, reverse=True)
                for memory in sorted_memories:
                    f.write(memory.to_text_line() + "\n")
                
                # 写入文件尾
                f.write("\n---\n")
            
            logger.debug(f"成功保存 {len(self.memories)} 条记忆到纯文本文件")
        except Exception as e:
            logger.error(f"保存记忆文件失败: {e}")
    
    def _is_memory_expired(self, memory: Memory) -> bool:
        """检查记忆是否过期"""
        now = datetime.now(timezone.utc)
        age_days = (now - memory.create_at).days
        return age_days > self.max_memory_age_days
    
    def store_memory(self, context: str) -> None:
        """存储新记忆
        
        Args:
            context: 记忆内容（自然语言描述）
        """
        if not context or not context.strip():
            logger.warning("记忆内容为空，跳过存储")
            return
        
        memory = Memory(
            create_at=datetime.now(timezone.utc),
            context=context.strip()
        )
        
        self.memories.append(memory)
        
        # 清理过期和超量记忆
        self._cleanup_memories()
        
        # 保存到文件
        self._save_memories()
        
        logger.debug(f"存储新记忆: {context[:50]}...")
    
    def _cleanup_memories(self):
        """清理过期和超量记忆"""
        # 移除过期记忆
        self.memories = [memory for memory in self.memories if not self._is_memory_expired(memory)]
        
        # 如果记忆数量超过限制，保留最新的记忆
        if len(self.memories) > self.max_memories:
            self.memories.sort(key=lambda m: m.create_at, reverse=True)
            removed_count = len(self.memories) - self.max_memories
            self.memories = self.memories[:self.max_memories]
            logger.info(f"清理了 {removed_count} 条旧记忆")
    
    def retrieve_memories(self, query: str = None, limit: int = 10) -> List[Memory]:
        """检索记忆
        
        Args:
            query: 查询关键词（可选）
            limit: 返回数量限制
            
        Returns:
            匹配的记忆列表
        """
        if not query:
            # 如果没有查询条件，返回最新的记忆
            sorted_memories = sorted(self.memories, key=lambda m: m.create_at, reverse=True)
            return sorted_memories[:limit]
        
        # 使用简单的文本匹配进行搜索
        query_lower = query.lower()
        matched_memories = []
        
        for memory in self.memories:
            if self._matches_query(memory.context, query_lower):
                matched_memories.append(memory)
        
        # 按创建时间倒序排序
        matched_memories.sort(key=lambda m: m.create_at, reverse=True)
        
        return matched_memories[:limit]
    
    def search_memories(self, query: str, limit: int = 10) -> List[Memory]:
        """搜索记忆（别名方法，用于向后兼容）
        
        Args:
            query: 查询关键词
            limit: 返回数量限制
            
        Returns:
            匹配的记忆列表
        """
        return self.retrieve_memories(query, limit)
    
    def _matches_query(self, context: str, query_lower: str) -> bool:
        """检查记忆内容是否匹配查询"""
        context_lower = context.lower()
        
        # 简单的关键词匹配
        query_words = query_lower.split()
        for word in query_words:
            if word in context_lower:
                return True
        
        return False
    
    def get_recent_memories(self, hours: int = 24, limit: int = 20) -> List[Memory]:
        """获取最近的记忆
        
        Args:
            hours: 最近几小时
            limit: 返回数量限制
            
        Returns:
            最近的记忆列表
        """
        now = datetime.now(timezone.utc)
        
        # 修复时间计算逻辑
        if hours <= 24:
            from datetime import timedelta
            cutoff_time = now - timedelta(hours=hours)
        else:
            from datetime import timedelta
            cutoff_time = now - timedelta(hours=hours)
        
        recent_memories = [
            memory for memory in self.memories
            if memory.create_at >= cutoff_time
        ]
        
        # 按创建时间倒序排序
        recent_memories.sort(key=lambda m: m.create_at, reverse=True)
        
        return recent_memories[:limit]
    
    def get_memory_summary(self) -> str:
        """获取记忆摘要"""
        if not self.memories:
            return "暂无记忆"
        
        total_memories = len(self.memories)
        latest_memory = max(self.memories, key=lambda m: m.create_at)
        oldest_memory = min(self.memories, key=lambda m: m.create_at)
        
        return f"共有 {total_memories} 条记忆，最新记忆创建于 {latest_memory.create_at.strftime('%Y-%m-%d %H:%M:%S')}，最旧记忆创建于 {oldest_memory.create_at.strftime('%Y-%m-%d %H:%M:%S')}"
    
    def clear_all_memories(self):
        """清空所有记忆"""
        self.memories.clear()
        self._save_memories()
        logger.info("已清空所有记忆")
    
    def export_memories(self, file_path: str = None) -> str:
        """导出记忆到文件
        
        Args:
            file_path: 导出文件路径（可选）
            
        Returns:
            导出的文件路径
        """
        if file_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = f"memories_export_{self.agent_id}_{timestamp}.txt"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"=== Agent: {self.agent_id} Memory Export ===\n")
                f.write(f"Export Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Memories: {len(self.memories)}\n")
                f.write("="*50 + "\n\n")
                
                sorted_memories = sorted(self.memories, key=lambda m: m.create_at, reverse=True)
                for i, memory in enumerate(sorted_memories, 1):
                    f.write(f"Memory #{i}\n")
                    f.write(memory.to_text_line() + "\n")
                    f.write("-"*30 + "\n\n")
            
            logger.info(f"记忆导出成功: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"导出记忆失败: {e}")
            raise
    
    def view_memory_file(self) -> str:
        """查看记忆文件内容（用于调试）"""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logger.error(f"读取记忆文件失败: {e}")
                return f"读取失败: {e}"
        return "记忆文件不存在"
    
    # 便捷方法：存储不同类型的记忆（使用自然语言描述）
    def store_file_change(self, file_path: str, action: str, details: str = None):
        """存储文件变更记忆"""
        context = f"文件变更: {action} 文件 {file_path}"
        if details:
            context += f"。详情: {details}"
        self.store_memory(context)
    
    def store_issue_analysis(self, issue_description: str, analysis: str, solution: str = None):
        """存储问题分析记忆"""
        context = f"问题分析: {issue_description}。分析结果: {analysis}"
        if solution:
            context += f"。解决方案: {solution}"
        self.store_memory(context)
    
    def store_implementation_plan(self, task: str, plan: str, outcome: str = None):
        """存储实现计划记忆"""
        context = f"实现计划: 任务 '{task}'，计划 '{plan}'"
        if outcome:
            context += f"，结果: {outcome}"
        self.store_memory(context)
    
    def store_thinking_process(self, thought: str, context_info: str = None, conclusion: str = None):
        """存储思考过程记忆"""
        context = f"思考过程: {thought}"
        if context_info:
            context += f"，背景: {context_info}"
        if conclusion:
            context += f"，结论: {conclusion}"
        self.store_memory(context)
    
    def store_decision_log(self, decision: str, reasoning: str = None, outcome: str = None):
        """存储决策日志记忆"""
        context = f"决策记录: {decision}"
        if reasoning:
            context += f"，理由: {reasoning}"
        if outcome:
            context += f"，结果: {outcome}"
        self.store_memory(context)
    
    def store_learning_experience(self, lesson: str, context_info: str = None, improvement: str = None):
        """存储学习经验记忆"""
        context = f"学习经验: {lesson}"
        if context_info:
            context += f"，背景: {context_info}"
        if improvement:
            context += f"，改进建议: {improvement}"
        self.store_memory(context) 