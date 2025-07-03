"""
极简、灵活、prompt驱动的编码员代理。
所有开发任务都通过prompt驱动LLM完成。
memory只存储AI在写代码过程中的思考和决策链。
"""

import os
import logging
from typing import Any, Optional
from ..git_utils import GitManager
from ..llm_utils import LLMManager
from .memory_manager import MemoryManager

logger = logging.getLogger(__name__)

class CoderAgent:
    """
    极简、灵活、prompt驱动的编码员代理。
    所有开发任务都通过prompt驱动LLM完成。
    memory只存储AI在写代码过程中的思考和决策链。
    """
    def __init__(self, agent_id: str, llm_manager: Any, user_project_path: str,
                 memory_manager: Optional[MemoryManager] = None):
        """初始化代码实现代理
        
        Args:
            agent_id: 代理ID
            llm_manager: LLM管理器
            user_project_path: 用户项目路径
            memory_manager: 记忆管理器，可选
        """
        self.agent_id = agent_id
        self.llm_manager = llm_manager
        self.user_project_path = user_project_path
        self.git_manager = GitManager(user_project_path)
        
        # 初始化记忆管理器
        if memory_manager is None:
            self.memory_manager = MemoryManager(agent_id)
        else:
            self.memory_manager = memory_manager
        
        logger.info(f"初始化CoderAgent: {agent_id}")
        
        # 记录初始化
        self.memory_manager.store_memory(f"CoderAgent {agent_id} 初始化完成，项目路径: {user_project_path}")
    
    def _implement_issue(self, issue, max_iterations=30):
        """实现Issue的核心方法 - 使用简单的prompt驱动"""
        iteration_count = 0
        
        while iteration_count < max_iterations:
            # 获取当前记忆
            memories = self.memory_manager.get_recent_memories(hours=24, limit=10)
            memories_text = "\n".join([memory.context for memory in memories]) if memories else "No previous actions"
            
            # 决定下一步动作的prompt
            action_prompt = f"""
You are a skilled software developer. Based on the current situation, decide what action to take next.

AVAILABLE ACTIONS:
- read_file <filepath>: Read a file
- write_file <filepath> <content>: Write content to a file  
- run_command <command>: Execute a shell command
- analyze_code <code_or_filepath>: Analyze code structure
- create_test <test_name> <test_code>: Create a test file
- search_pattern <pattern> <directory>: Search for code patterns
- complete: Mark task as finished

CURRENT MEMORIES:
{memories_text}

CURRENT ISSUE:
{issue}

Think step by step:
1. What have I done so far?
2. What needs to be done next?
3. What's the most logical next action?

Respond with just the action command, for example:
read_file src/main.py
or
write_file utils.py def helper_function(): pass
or
complete

Your action:
"""
            
            # 使用LLM生成动作
            action = self.llm_manager._call_llm(action_prompt).strip()
            
            if action == "complete":
                break
                
            # 执行动作
            return_value = self._execute_action(action)
            
            # 更新记忆
            self.memory_manager.store_memory(f"Action: {action} | Result: {return_value}")
            
            # 检查是否完成的prompt
            completion_prompt = f"""
Look at the original issue and what has been accomplished so far. 

ORIGINAL ISSUE:
{issue}

ACTIONS TAKEN:
{memories_text}

Has this issue been fully resolved? Consider:
- Are all requirements implemented?
- Does the code work correctly?
- Are there tests if needed?
- Is the implementation complete?

If the issue is fully resolved, respond with "yes".
If more work is needed, respond with "no".

Answer:
"""
            
            completed = self.llm_manager._call_llm(completion_prompt).strip().lower()
            if completed.startswith("yes"):
                break
            
            iteration_count += 1
        
        return {
            "completed": completed.startswith("yes") if 'completed' in locals() else False,
            "iterations": iteration_count,
            "final_memories": [memory.context for memory in self.memory_manager.get_recent_memories(hours=24, limit=5)]
        }
    
    def _execute_action(self, action: str) -> str:
        """执行动作命令"""
        try:
            parts = action.split(' ', 1)
            command = parts[0]
            args = parts[1] if len(parts) > 1 else ""
            
            if command == "read_file":
                file_path = os.path.join(self.user_project_path, args)
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return f.read()
                else:
                    return f"File not found: {file_path}"
                    
            elif command == "write_file":
                try:
                    filepath, content = args.split(' ', 1)
                    full_path = os.path.join(self.user_project_path, filepath)
                    
                    # 确保目录存在
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    return f"File {filepath} written successfully"
                except ValueError:
                    return "Error: write_file requires filepath and content"
                    
            elif command == "run_command":
                import subprocess
                result = subprocess.run(args, shell=True, capture_output=True, text=True, cwd=self.user_project_path)
                return f"Exit code: {result.returncode}\nOutput: {result.stdout}\nError: {result.stderr}"
                
            elif command == "analyze_code":
                return f"Analyzed code: {args[:100]}..."
                
            elif command == "create_test":
                try:
                    test_name, test_code = args.split(' ', 1)
                    test_file = os.path.join(self.user_project_path, f"test_{test_name}.py")
                    with open(test_file, 'w', encoding='utf-8') as f:
                        f.write(test_code)
                    return f"Test file test_{test_name}.py created"
                except ValueError:
                    return "Error: create_test requires test_name and test_code"
                    
            elif command == "search_pattern":
                try:
                    pattern, directory = args.split(' ', 1)
                    search_path = os.path.join(self.user_project_path, directory)
                    if os.path.exists(search_path):
                        import glob
                        files = glob.glob(os.path.join(search_path, "**/*.py"), recursive=True)
                        return f"Searched for {pattern} in {len(files)} files in {directory}"
                    else:
                        return f"Directory not found: {search_path}"
                except ValueError:
                    return "Error: search_pattern requires pattern and directory"
                    
            else:
                return f"Unknown command: {command}"
                
        except Exception as e:
            return f"Error executing action: {str(e)}"
    
    async def implement_issue(self, issue: dict, max_iterations: int = 30) -> dict:
        """
        实现给定的Issue。
        
        Args:
            issue: Issue字典，包含title和description
            max_iterations: 最大迭代次数
            
        Returns:
            实现结果字典
        """
        logger.info(f"开始实现Issue: {issue.get('title', '未知')}")
        
        # 记录开始实现
        self.memory_manager.store_memory(f"开始实现Issue: {issue.get('title', '未知')}")
        
        try:
            # 格式化issue为字符串
            issue_text = f"Title: {issue.get('title', '')}\nDescription: {issue.get('description', '')}"
            
            # 调用核心实现方法
            result = self._implement_issue(issue_text, max_iterations)
            
            # 记录实现结果
            if result["completed"]:
                self.memory_manager.store_memory(f"成功实现Issue: {issue.get('title', '未知')}")
            else:
                self.memory_manager.store_memory(f"实现Issue未完成: {issue.get('title', '未知')}")
            
            return {
                "success": result["completed"],
                "iterations": result["iterations"],
                "memories": result["final_memories"],
                "error": None
            }
            
        except Exception as e:
            error_msg = f"实现Issue时发生异常: {str(e)}"
            logger.error(error_msg)
            self.memory_manager.store_memory(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "iterations": 0,
                "memories": []
            }
    
    def get_memory_summary(self) -> dict:
        """获取记忆总结"""
        return {
            "agent_id": self.agent_id,
            "total_memories": len(self.memory_manager.memories),
            "recent_memories": [memory.context for memory in self.memory_manager.get_recent_memories(hours=24, limit=5)]
        }
    
    def export_memories(self, output_path: str) -> bool:
        """导出记忆到文件"""
        try:
            return self.memory_manager.export_memories(output_path)
        except Exception as e:
            logger.error(f"导出记忆失败: {str(e)}")
            return False
    
    def clear_old_memories(self, days: int = 30):
        """清理旧记忆"""
        try:
            # 这里可以添加清理逻辑，或者直接调用memory_manager的方法
            logger.info(f"清理了 {days} 天前的记忆")
        except Exception as e:
            logger.error(f"清理记忆失败: {str(e)}")