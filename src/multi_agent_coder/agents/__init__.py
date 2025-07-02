"""
Agent 模块
包含评论员和编码员代理，现已集成思考链、记忆、反思等智能化功能
所有代理都支持异步操作
"""

from .commenter import CommenterAgent
from .coder import CoderAgent
from .thinking import MemoryManager

__all__ = [
    'CommenterAgent', 
    'CoderAgent',
    'MemoryManager'
] 