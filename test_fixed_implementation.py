#!/usr/bin/env python3
"""
测试修复后的JSON解析问题
"""
import os
import sys
import asyncio
import logging

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.multi_agent_coder.llm_utils import LLMManager
from src.multi_agent_coder.agents.coder import CoderAgent
from src.multi_agent_coder.agents.memory_manager import MemoryManager

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_natural_language_parsing():
    """测试自然语言解析功能"""
    print("=== 测试自然语言解析功能 ===")
    
    # 创建测试实例
    test_api_key = "test_key"
    llm_manager = LLMManager(test_api_key)
    
    # 创建模拟的自然语言响应
    mock_response = """
**思考过程：**
我需要创建一个简单的Python函数来计算斐波那契数列。这个函数应该：
1. 接受一个整数n作为参数
2. 返回斐波那契数列的第n项
3. 使用递归或迭代方式实现

我选择使用迭代方式实现，因为它更高效。

**代码实现：**
文件路径：fibonacci.py
```python
def fibonacci(n):
    '''计算斐波那契数列的第n项'''
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b

# 测试函数
if __name__ == "__main__":
    for i in range(10):
        print(f"fibonacci({i}) = {fibonacci(i)}")
```
    """
    
    # 测试解析功能
    try:
        result = llm_manager._parse_natural_language_response(mock_response)
        print("✅ 自然语言解析成功")
        
        # 验证解析结果
        assert "thoughts" in result
        assert "result" in result
        assert result["result"]["file_path"] == "fibonacci.py"
        assert "def fibonacci(n):" in result["result"]["code"]
        
        print(f"📝 思考过程: {result['thoughts'][0]['thought'][:50]}...")
        print(f"📁 文件路径: {result['result']['file_path']}")
        print(f"💻 代码长度: {len(result['result']['code'])} 字符")
        
    except Exception as e:
        print(f"❌ 自然语言解析失败: {e}")
        return False
    
    return True

async def test_memory_manager():
    """测试记忆管理器"""
    print("\n=== 测试记忆管理器 ===")
    
    try:
        # 创建记忆管理器
        memory_manager = MemoryManager("test_agent")
        
        # 存储一些记忆
        memory_manager.store_memory("开始测试记忆管理器功能")
        memory_manager.store_memory("成功创建第一个记忆条目")
        memory_manager.store_memory("测试自然语言格式存储")
        
        # 检索记忆
        recent_memories = memory_manager.get_recent_memories(2)
        print(f"✅ 成功存储和检索 {len(recent_memories)} 条记忆")
        
        # 搜索记忆
        search_results = memory_manager.search_memories("测试", limit=3)
        print(f"✅ 搜索到 {len(search_results)} 条相关记忆")
        
        # 查看记忆文件
        if hasattr(memory_manager, 'view_memory_file'):
            memory_manager.view_memory_file()
        
    except Exception as e:
        print(f"❌ 记忆管理器测试失败: {e}")
        return False
    
    return True

async def test_coder_agent():
    """测试CoderAgent"""
    print("\n=== 测试CoderAgent ===")
    
    try:
        # 创建测试环境
        test_api_key = "test_key"
        llm_manager = LLMManager(test_api_key)
        user_project_path = "/tmp/test_project"
        
        # 确保测试目录存在
        os.makedirs(user_project_path, exist_ok=True)
        
        # 创建CoderAgent
        coder_agent = CoderAgent("test_coder", llm_manager, user_project_path)
        print("✅ 成功创建CoderAgent实例")
        
        # 获取记忆总结
        summary = coder_agent.get_memory_summary()
        print(f"✅ 记忆总结: {summary['agent_id']}, {summary['total_memories']} 条记忆")
        
    except Exception as e:
        print(f"❌ CoderAgent测试失败: {e}")
        return False
    
    return True

async def main():
    """主测试函数"""
    print("🚀 开始测试修复后的实现...")
    
    # 运行所有测试
    tests = [
        test_natural_language_parsing,
        test_memory_manager,
        test_coder_agent
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            results.append(False)
    
    # 总结结果
    print(f"\n=== 测试结果总结 ===")
    passed = sum(results)
    total = len(results)
    print(f"✅ 通过: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有测试都通过！JSON解析问题已修复。")
    else:
        print("⚠️  部分测试失败，需要进一步调试。")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main()) 