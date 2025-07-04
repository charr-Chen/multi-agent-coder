"""
极简、灵活、prompt驱动的编码员代理。
所有开发任务都通过prompt驱动LLM完成。
memory只存储AI在写代码过程中的思考和决策链。
"""

import os
import logging
import asyncio
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
            # 使用项目根目录下的.memory目录
            memory_dir = os.path.join(os.getcwd(), ".memory")
            self.memory_manager = MemoryManager(agent_id, memory_dir)
        else:
            self.memory_manager = memory_manager
        
        # 长期记忆：存储持久化的经验和知识
        self.long_term_memories = []
        
        # 短期记忆：当前任务的上下文和即时指令
        self.short_term_memory = ""
        
        logger.info(f"初始化CoderAgent: {agent_id}")
        
        # 记录初始化到长期记忆
        init_memory = f"CoderAgent {agent_id} 初始化完成，项目路径: {user_project_path}"
        self.add_long_term_memory(init_memory)
        self.memory_manager.store_memory(init_memory)
    
    def add_long_term_memory(self, memory_text: str):
        """添加长期记忆"""
        self.long_term_memories.append(memory_text)
        # 保持长期记忆在合理范围内
        if len(self.long_term_memories) > 100:
            self.long_term_memories = self.long_term_memories[-100:]
    
    def set_short_term_memory(self, memory_text: str):
        """设置短期记忆（当前任务上下文）"""
        self.short_term_memory = memory_text
    
    def get_formatted_memories(self) -> str:
        """获取格式化的记忆信息"""
        long_term_text = "\n".join(self.long_term_memories[-20:]) if self.long_term_memories else "无历史记录"
        short_term_text = self.short_term_memory if self.short_term_memory else "无当前任务上下文"
        
        return f"""
=== 长期记忆（历史经验和决策） ===
{long_term_text}

=== 短期记忆（当前任务上下文） ===
{short_term_text}
"""
    
    async def _implement_issue(self, issue, max_iterations=50):
        """实现Issue的核心方法 - 简化的prompt驱动"""
        iteration_count = 0
        
        # 设置短期记忆为当前任务
        task_context = f"正在实现Issue: {issue[:200]}..."
        self.set_short_term_memory(task_context)
        
        # 记录任务开始时的思考
        await self.memory_manager.record_task_start_thinking(self.llm_manager, issue)
        
        while iteration_count < max_iterations:
            # 获取格式化的记忆
            memories_text = self.get_formatted_memories()
            
            # 强化的动作决策prompt - 更明确的指导
            action_prompt = f"""
你是一个专业的程序员AI，正在通过命令行操作来实现代码功能。

【当前任务】
{issue}

【历史操作记录】
{memories_text}

【执行策略】
根据任务类型，按以下步骤执行：

1. 如果是第一次执行，先用 ls -la 查看项目结构
2. 如果需要了解现有代码，用 cat 查看具体文件
3. 如果需要查找特定文件，用 find . -name "*.py" 
4. 理解项目结构后，立即开始修改代码
5. 最后用 complete 标记完成

【可用命令】
- ls -la                                    # 查看目录结构
- cat path/to/file.py                       # 查看文件内容
- find . -name "*.py"                       # 查找Python文件
- edit_file:path/file.py:完整的Python代码    # 创建或完全重写文件
- replace_in_file:path:旧代码:新代码          # 替换文件中的特定部分
- pip install package_name                   # 安装Python包
- complete                                   # 标记任务完成

【关键要求】
1. 必须修改现有代码文件，在其中添加实际的功能实现
2. 不要只是查看文件，必须执行实际的代码修改
3. 修改的代码必须包含完整的功能实现，不能只是注释
4. 根据任务需求，实现相应的功能逻辑
5. 确保代码能够解决任务中描述的具体问题

【命令格式示例】
edit_file:platform/reworkd_platform/web/api/agent/agent_api.py:
# 根据任务需求添加相应的导入
import os
import json
from datetime import datetime

class TaskProcessor:
    def __init__(self):
        self.status = "initialized"
    
    def process_request(self, data):
        # 实现具体的业务逻辑
        result = self.handle_data(data)
        return {"status": "success", "result": result}
    
    def handle_data(self, data):
        # 根据实际需求实现处理逻辑
        return {"processed": True, "timestamp": datetime.now()}

【重要】
- 只返回一个命令，不要解释
- 不要使用markdown格式
- 如果历史记录显示已经查看了文件，立即开始修改代码
- 必须实现实际功能，不能只是添加注释

命令："""
            
            # 使用LLM生成动作
            action = await self.llm_manager._call_llm(action_prompt)
            action = action.strip()
            
            # 增加调试日志
            logger.info(f"🤖 LLM返回的动作: {action}")
            
            if action == "complete":
                self.memory_manager.store_memory("手动标记任务完成")
                break
            
            # 验证动作格式
            if not action or len(action) < 2:
                logger.warning(f"⚠️ LLM返回的动作无效: '{action}'")
                self.add_long_term_memory(f"⚠️ 无效动作: '{action}'")
                continue
                
            # 执行动作
            return_value = self._execute_action(action)
            
            # 增加执行结果日志
            logger.info(f"📋 动作执行结果: {return_value[:200] if return_value else 'None'}...")
            
            # 记录执行结果到长期记忆（用于操作历史）
            execution_record = f"执行: {action}"
            if return_value:
                # 对于文件操作，只记录文件名，不记录完整内容
                if action.startswith("edit_file:") or action.startswith("append_file:") or action.startswith("replace_in_file:"):
                    parts = action.split(":", 2)
                    if len(parts) >= 2:
                        filename = parts[1].strip()
                        execution_record += f" → ✅ 成功编辑文件: {filename}"
                    else:
                        execution_record += f" → {return_value[:50]}..."
                else:
                    # 对于其他命令，限制输出长度
                    result_preview = return_value[:100] + "..." if len(return_value) > 100 else return_value
                    execution_record += f" → {result_preview}"
            
            self.add_long_term_memory(execution_record)
            
            # 让AI记录自己的想法和思路到memory
            if iteration_count % 3 == 0:  # 每3次迭代记录一次思考
                await self.memory_manager.record_progress_thinking(
                    self.llm_manager, issue, action, return_value, iteration_count
                )
            
            # 严格的完成检查 - 确保真正修改了代码
            if iteration_count > 3:  # 给足够时间进行分析和修改
                completion_check = await self.llm_manager._call_llm(f"""
检查任务完成情况：

【任务】{issue}

【操作历史】{memories_text}

【检查标准】
严格检查以下条件，ALL必须满足：

1. ✅ 是否执行了 edit_file 或 replace_in_file 命令？
2. ✅ 修改的文件是否包含实际的Python代码实现？
3. ✅ 代码是否包含具体的功能函数/类，而不只是注释？
4. ✅ 是否实现了任务要求的核心功能？

【判断标准】
检查操作历史中是否满足以下条件：
1. 执行了 edit_file 或 replace_in_file 命令
2. 修改的代码包含实际的功能实现（函数、类、具体的业务逻辑）
3. 代码能够解决任务中描述的具体问题
4. 不只是添加注释或空函数，而是有实际的代码逻辑

【判断】
如果操作历史中包含了代码修改命令，并且修改的代码包含实际的功能实现来解决任务需求，回答 "yes"
如果只是查看文件、安装依赖、或没有实际代码修改，回答 "no"

答案：""")
                
                if completion_check.strip().lower().startswith("yes"):
                    # 记录任务完成时的思考
                    await self.memory_manager.record_task_completion_thinking(self.llm_manager, issue, memories_text)
                    
                    break
            
            iteration_count += 1
        
        # 如果任务未完成，记录失败思考
        if iteration_count >= max_iterations:
            await self.memory_manager.record_task_failure_thinking(
                self.llm_manager, issue, memories_text, iteration_count
            )
        
        return {
            "completed": iteration_count < max_iterations,
            "iterations": iteration_count,
            "final_memories": self.long_term_memories[-5:] if self.long_term_memories else []
        }
    
    def _execute_action(self, action: str) -> str:
        """执行动作命令 - 支持文件修改和终端执行"""
        try:
            import subprocess
            
            # 清理action，移除可能的markdown格式
            action = action.strip()
            if action.startswith("```") and action.endswith("```"):
                lines = action.split('\n')
                if len(lines) >= 3:
                    action = '\n'.join(lines[1:-1]).strip()
            
            # 如果action包含多行，只取第一行
            if '\n' in action:
                action = action.split('\n')[0].strip()
            
            logger.info(f"🔧 清理后的动作: {action}")
            
            # 检查是否是文件修改命令
            if action.startswith("edit_file:"):
                return self._edit_file(action)
            elif action.startswith("append_file:"):
                return self._append_file(action)
            elif action.startswith("replace_in_file:"):
                return self._replace_in_file(action)
            else:
                # 检查是否是常见的无效响应
                invalid_responses = [
                    "我需要", "首先", "让我", "我会", "我应该", "我建议", 
                    "根据", "基于", "为了", "现在", "接下来", "然后",
                    "这个任务", "要完成", "我认为", "看起来", "似乎",
                    "command:", "命令:", "执行:", "操作:", "步骤:"
                ]
                if any(action.lower().startswith(phrase.lower()) for phrase in invalid_responses):
                    logger.warning(f"⚠️ 检测到自然语言响应，非命令格式: {action}")
                    return f"错误: 收到自然语言响应而非命令格式: {action}"
                
                # 处理可能的格式问题
                if ":" in action and not action.startswith(("edit_file:", "append_file:", "replace_in_file:")):
                    # 可能是 "命令: ls -la" 这种格式，提取冒号后的部分
                    parts = action.split(":", 1)
                    if len(parts) == 2:
                        potential_command = parts[1].strip()
                        if potential_command and not any(potential_command.startswith(phrase) for phrase in invalid_responses):
                            logger.info(f"🔧 提取冒号后的命令: {potential_command}")
                            action = potential_command
                
                # 直接执行action作为终端命令
                logger.info(f"🖥️ 执行终端命令: {action}")
                
                # 设置环境变量
                env = os.environ.copy()
                env['PYTHONPATH'] = f"{self.user_project_path}:{env.get('PYTHONPATH', '')}"
                
                # 执行命令
                result = subprocess.run(
                    action, 
                    shell=True, 
                    capture_output=True, 
                    text=True, 
                    cwd=self.user_project_path, 
                    timeout=60,  # 增加超时时间
                    env=env
                )
                
                # 构建返回结果
                output = []
                if result.stdout:
                    output.append(f"标准输出:\n{result.stdout}")
                if result.stderr:
                    output.append(f"错误输出:\n{result.stderr}")
                
                output.append(f"退出码: {result.returncode}")
                
                return "\n".join(output)
            
        except subprocess.TimeoutExpired:
            return "命令执行超时（60秒）"
        except Exception as e:
            return f"命令执行失败: {str(e)}"
    
    def _edit_file(self, action: str) -> str:
        """编辑文件内容"""
        try:
            # 格式: edit_file:filepath:content
            parts = action.split(":", 2)
            if len(parts) != 3:
                return "错误: edit_file命令格式应为 edit_file:filepath:content"
            
            filepath = parts[1].strip()
            content = parts[2].strip()
            
            # 构建完整路径
            full_path = os.path.join(self.user_project_path, filepath)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # 写入文件
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"✅ 成功编辑文件: {filepath}")
            return f"✅ 成功编辑文件: {filepath}"
            
        except Exception as e:
            error_msg = f"编辑文件失败: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def _append_file(self, action: str) -> str:
        """追加内容到文件"""
        try:
            # 格式: append_file:filepath:content
            parts = action.split(":", 2)
            if len(parts) != 3:
                return "错误: append_file命令格式应为 append_file:filepath:content"
            
            filepath = parts[1].strip()
            content = parts[2].strip()
            
            # 构建完整路径
            full_path = os.path.join(self.user_project_path, filepath)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # 追加内容
            with open(full_path, 'a', encoding='utf-8') as f:
                f.write(content + "\n")
            
            logger.info(f"✅ 成功追加内容到文件: {filepath}")
            return f"✅ 成功追加内容到文件: {filepath}"
            
        except Exception as e:
            error_msg = f"追加文件失败: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def _replace_in_file(self, action: str) -> str:
        """在文件中替换内容"""
        try:
            # 格式: replace_in_file:filepath:old_text:new_text
            parts = action.split(":", 3)
            if len(parts) != 4:
                return "错误: replace_in_file命令格式应为 replace_in_file:filepath:old_text:new_text"
            
            filepath = parts[1].strip()
            old_text = parts[2].strip()
            new_text = parts[3].strip()
            
            # 构建完整路径
            full_path = os.path.join(self.user_project_path, filepath)
            
            if not os.path.exists(full_path):
                return f"错误: 文件不存在: {filepath}"
            
            # 读取文件内容
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换内容
            if old_text in content:
                new_content = content.replace(old_text, new_text)
                
                # 写回文件
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                logger.info(f"✅ 成功替换文件内容: {filepath}")
                return f"✅ 成功替换文件内容: {filepath}"
            else:
                return f"警告: 在文件 {filepath} 中未找到要替换的文本"
                
        except Exception as e:
            error_msg = f"替换文件内容失败: {str(e)}"
            logger.error(error_msg)
            return error_msg

    async def implement_issue(self, issue: dict, max_iterations: int = 50) -> dict:
        """
        实现给定的Issue。
        
        Args:
            issue: Issue字典，包含title和description
            max_iterations: 最大迭代次数
            
        Returns:
            实现结果字典
        """
        logger.info(f"开始实现Issue: {issue.get('title', '未知')}")
        
        # 记录到长期记忆
        issue_title = issue.get('title', '未知')
        issue_desc = issue.get('description', '')
        self.add_long_term_memory(f"开始新任务: {issue_title}")
        
        try:
            # 格式化issue为字符串
            issue_text = f"标题: {issue.get('title', '')}\n描述: {issue.get('description', '')}"
            
            # 设置短期记忆为当前任务
            self.set_short_term_memory(f"当前任务: {issue_title} - {issue_desc[:100]}...")
            
            # 调用核心实现方法
            result = await self._implement_issue(issue_text, max_iterations)
            
            # 记录结果到长期记忆
            if result["completed"]:
                self.add_long_term_memory(f"✅ 任务完成: {issue_title}")
            else:
                self.add_long_term_memory(f"❌ 任务未完成: {issue_title}")
            
            return {
                "success": result["completed"],
                "iterations": result["iterations"],
                "long_term_memories": self.long_term_memories[-10:],
                "short_term_memory": self.short_term_memory,
                "error": None if result["completed"] else "任务未在最大迭代次数内完成"
            }
                
        except Exception as e:
            error_msg = f"实现Issue时发生异常: {str(e)}"
            logger.error(error_msg)
            self.add_long_term_memory(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "iterations": 0,
                "long_term_memories": self.long_term_memories[-5:],
                "short_term_memory": self.short_term_memory
            }
    
    def get_memory_summary(self) -> dict:
        """获取记忆总结"""
        return {
            "agent_id": self.agent_id,
            "long_term_memories_count": len(self.long_term_memories),
            "recent_long_term_memories": self.long_term_memories[-5:] if self.long_term_memories else [],
            "short_term_memory": self.short_term_memory
        }
    
    def export_memories(self, output_path: str) -> bool:
        """导出记忆到文件"""
        try:
            import json
            memory_data = {
                "agent_id": self.agent_id,
                "long_term_memories": self.long_term_memories,
                "short_term_memory": self.short_term_memory,
                "export_time": str(asyncio.get_event_loop().time())
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(memory_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"导出记忆失败: {str(e)}")
            return False
    
    def load_memories(self, input_path: str) -> bool:
        """从文件加载记忆"""
        try:
            import json
            with open(input_path, 'r', encoding='utf-8') as f:
                memory_data = json.load(f)
            
            self.long_term_memories = memory_data.get("long_term_memories", [])
            self.short_term_memory = memory_data.get("short_term_memory", "")
            
            logger.info(f"加载了 {len(self.long_term_memories)} 条长期记忆")
            return True
        except Exception as e:
            logger.error(f"加载记忆失败: {str(e)}")
            return False
    
    def clear_old_memories(self, days: int = 30):
        """清理旧记忆"""
        try:
            # 保留最近的记忆
            if len(self.long_term_memories) > 50:
                self.long_term_memories = self.long_term_memories[-50:]
            
            logger.info(f"清理了旧记忆，保留最近50条")
        except Exception as e:
            logger.error(f"清理记忆失败: {str(e)}")
    
    def set_playground_git_manager(self, playground_git_manager):
        """设置playground Git管理器"""
        self.playground_git_manager = playground_git_manager
        self.add_long_term_memory(f"设置playground Git管理器")
    
    def set_collaboration_manager(self, collaboration_manager):
        """设置协作管理器"""
        self.collaboration_manager = collaboration_manager
        self.add_long_term_memory(f"设置协作管理器")
    
    def set_multi_repo_manager(self, multi_repo_manager):
        """设置多仓库管理器"""
        self.multi_repo_manager = multi_repo_manager
        self.add_long_term_memory(f"设置多仓库管理器")
    
    async def _create_pull_request_for_issue(self, issue: dict, result: dict) -> None:
        """为完成的Issue创建Pull Request"""
        try:
            issue_title = issue.get('title', '未知')
            issue_id = issue.get('id', 'unknown')
            
            # 生成分支名
            branch_name = f"feature/{self.agent_id}-{issue_id}"
            
            # 获取代码更改
            code_changes = await self._get_code_changes()
            
            if code_changes:
                # 创建Pull Request
                pr_id = await self.collaboration_manager.create_pull_request(
                    title=f"实现Issue: {issue_title}",
                    author=self.agent_id,
                    source_branch=branch_name,
                    description=f"实现Issue #{issue_id}: {issue_title}\n\n{issue.get('description', '')}",
                    code_changes=code_changes
                )
                
                logger.info(f"✨ 创建Pull Request: #{pr_id}")
                self.add_long_term_memory(f"创建Pull Request: #{pr_id} 用于Issue: {issue_title}")
                
                # 注册agent仓库到协作管理器
                if hasattr(self, 'multi_repo_manager'):
                    agent_git_manager = self.multi_repo_manager.get_agent_git_manager(self.agent_id)
                    if agent_git_manager:
                        self.collaboration_manager.register_agent_repo(self.agent_id, agent_git_manager)
            else:
                logger.info("📝 没有代码更改，跳过创建Pull Request")
            
        except Exception as e:
            logger.error(f"❌ 创建Pull Request失败: {e}")
            self.add_long_term_memory(f"创建Pull Request失败: {e}")
    
    async def _get_code_changes(self) -> dict[str, str]:
        """获取代码更改"""
        try:
            code_changes = {}
            
            # 获取当前工作目录中的所有Python文件
            for root, dirs, files in os.walk(self.user_project_path):
                # 跳过隐藏目录和特殊目录
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
                
                for file in files:
                    if file.endswith(('.py', '.js', '.ts', '.html', '.css', '.json', '.md')):
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, self.user_project_path)
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if content.strip():  # 只包含非空文件
                                    code_changes[rel_path] = content
                        except Exception as e:
                            logger.warning(f"读取文件失败 {rel_path}: {e}")
            
            return code_changes
            
        except Exception as e:
            logger.error(f"获取代码更改失败: {e}")
            return {}
    
    async def _sync_work_to_playground(self) -> None:
        """同步工作到playground仓库"""
        try:
            if hasattr(self, 'multi_repo_manager'):
                success = await self.multi_repo_manager.sync_agent_work_to_playground(self.agent_id)
                if success:
                    logger.info(f"✅ 成功同步工作到playground")
                    self.add_long_term_memory("成功同步工作到playground")
                else:
                    logger.warning("⚠️ 同步工作到playground失败")
                    self.add_long_term_memory("同步工作到playground失败")
        except Exception as e:
            logger.error(f"❌ 同步工作失败: {e}")
            self.add_long_term_memory(f"同步工作失败: {e}")
    
    async def run(self):
        """运行CoderAgent的主循环 - 支持Issue抢夺"""
        logger.info(f"🚀 CoderAgent {self.agent_id} 开始运行")
        
        try:
            # 记录开始运行
            self.add_long_term_memory(f"🚀 开始运行 CoderAgent")
            
            # 持续监控和抢夺Issues
            while True:
                try:
                    # 检查是否有Issues需要处理
                    if hasattr(self, 'playground_git_manager'):
                        issues_file = os.path.join(self.playground_git_manager.repo_path, ".issues.json")
                        if os.path.exists(issues_file):
                            import json
                            with open(issues_file, 'r', encoding='utf-8') as f:
                                issues_data = json.load(f)
                            
                            # 获取所有open状态的Issues
                            open_issues = [issue for issue in issues_data.get('issues', []) 
                                         if issue.get('status') == 'open']
                            
                            if open_issues:
                                logger.info(f"📋 发现 {len(open_issues)} 个待抢夺Issues")
                                self.add_long_term_memory(f"发现 {len(open_issues)} 个待抢夺Issues")
                                
                                # 尝试抢夺多个Issue（每个agent可以处理多个）
                                max_issues_per_agent = 3  # 每个agent最多处理3个issue
                                issues_processed = 0
                                
                                for issue in open_issues:
                                    if issues_processed >= max_issues_per_agent:
                                        break
                                        
                                    issue_id = issue.get('id')
                                    issue_title = issue.get('title', '未知')
                                    
                                    logger.info(f"🔥 尝试抢夺Issue: {issue_title}")
                                    
                                    # 尝试分配Issue给自己
                                    if hasattr(self, 'playground_git_manager'):
                                        success = await self.playground_git_manager.assign_issue(issue_id, self.agent_id)
                                        
                                        if success:
                                            logger.info(f"✅ 成功抢夺Issue: {issue_title}")
                                            self.add_long_term_memory(f"🔥 成功抢夺Issue: {issue_title}")
                                            self.memory_manager.store_memory(f"成功抢夺Issue: {issue_title}")
                                            
                                            # 实现Issue
                                            result = await self.implement_issue(issue)
                                            
                                            if result["success"]:
                                                logger.info(f"✅ Issue {issue_title} 实现成功")
                                                self.memory_manager.store_memory(f"Issue {issue_title} 实现成功")
                                                
                                                # 创建Pull Request
                                                if hasattr(self, 'collaboration_manager') and hasattr(self, 'multi_repo_manager'):
                                                    await self._create_pull_request_for_issue(issue, result)
                                                
                                                # 同步代码到playground
                                                if hasattr(self, 'multi_repo_manager'):
                                                    await self._sync_work_to_playground()
                                                
                                                # 更新Issue状态为completed
                                                await self.playground_git_manager.update_issue_status(
                                                    issue_id, "completed", "实现完成"
                                                )
                                                
                                                issues_processed += 1
                                            else:
                                                logger.error(f"❌ Issue {issue_title} 实现失败: {result.get('error', '未知错误')}")
                                                self.memory_manager.store_memory(f"Issue {issue_title} 实现失败")
                                                # 重新释放Issue，不要提交"实现失败"作为代码
                                                await self.playground_git_manager.update_issue_status(
                                                    issue_id, "open", None
                                                )
                                        else:
                                            logger.info(f"❌ 抢夺Issue失败: {issue_title} (可能已被其他agent抢夺)")
                                            self.add_long_term_memory(f"❌ 抢夺失败: {issue_title}")
                                
                                if issues_processed > 0:
                                    logger.info(f"🎯 本轮处理了 {issues_processed} 个Issues")
                                    self.memory_manager.store_memory(f"本轮处理了 {issues_processed} 个Issues")
                            else:
                                logger.debug("📝 没有发现待抢夺的Issues")
                        else:
                            logger.warning("⚠️ 未找到.issues.json文件")
                    else:
                        logger.info("📝 单仓库模式，等待手动任务分配")
                    
                    # 等待一段时间后继续抢夺
                    await asyncio.sleep(10)  # 每10秒检查一次新Issues
                except Exception as e:
                    logger.error(f"❌ 抢夺Issues过程中出错: {str(e)}")
                    self.add_long_term_memory(f"❌ 抢夺过程出错: {str(e)}")
                    await asyncio.sleep(30)  # 出错后等待更长时间
            
        except asyncio.CancelledError:
            logger.info(f"🛑 CoderAgent {self.agent_id} 被取消")
            self.add_long_term_memory("🛑 CoderAgent 被取消")
        except Exception as e:
            logger.error(f"❌ CoderAgent {self.agent_id} 运行出错: {str(e)}")
            self.add_long_term_memory(f"❌ 运行出错: {str(e)}")
        finally:
            logger.info(f"🏁 CoderAgent {self.agent_id} 运行结束")
            self.add_long_term_memory("�� CoderAgent 运行结束")