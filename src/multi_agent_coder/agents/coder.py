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
            
            # 平衡的prompt - 有思考能力但输出命令
            action_prompt = f"""
你是一个专业的顶级全栈程序员AI，正在通过命令行操作实现代码功能。

【当前任务】
{issue}

【历史操作记录】
{memories_text}

【思考过程】
1. 分析任务需求，确定需要实现的功能
2. 查看项目结构，了解现有代码
3. 设计实现方案，考虑代码架构
4. 编写具体的代码实现

【常用命令提示，实际上你可以使用任何有效的终端命令】
- ls -la                                    # 查看项目结构
- cat <file>                               # 查看文件内容
- find . -name "*.py"                      # 查找Python文件
- grep -r "keyword" .                      # 搜索关键词
- diff_file:<file>:<diff>                  # 修改文件（唯一方式）
- complete                                 # 标记完成

【重要规则】
- 你可以思考和分析，但最终必须输出一个具体的命令
- 不要输出思考过程，只输出命令
- 修改文件必须使用diff_file命令
- 确保代码实现完整且功能正确

只输出终端命令，不要其他内容。"""
            
            # 使用LLM生成动作
            logger.info(f"📤 发送prompt给LLM，长度: {len(action_prompt)}字符")
            action = await self.llm_manager._call_llm(action_prompt)
            action = action.strip()
            
            # 增加调试日志
            logger.info(f"🤖 LLM返回的原始响应 ({len(action)}字符): {action}")
            
            # 检查是否包含多行响应
            if '\n' in action:
                lines = action.split('\n')
                logger.info(f"📝 LLM返回了多行响应，共{len(lines)}行:")
                for i, line in enumerate(lines[:5], 1):  # 只显示前5行
                    logger.info(f"   行{i}: {line}")
                if len(lines) > 5:
                    logger.info(f"   ... 还有{len(lines)-5}行")
            
            if action == "complete":
                self.memory_manager.store_memory("手动标记任务完成")
                break
            
            # 验证动作格式
            if not action or len(action) < 2:
                logger.warning(f"⚠️ LLM返回的动作无效: '{action}'")
                self.add_long_term_memory(f"⚠️ 无效动作: '{action}'")
                continue
            
            # 验证文件编辑命令格式
            if action.startswith("diff_file:"):
                if not self._validate_file_command(action):
                    logger.warning(f"⚠️ diff_file命令格式无效: '{action}'")
                    self.add_long_term_memory(f"⚠️ diff_file命令格式无效: '{action}'")
                    
                    # 给LLM一次重新生成的机会
                    retry_prompt = f"""
上次命令格式错误: {action}

请重新生成一个正确的diff_file命令。格式要求:
- diff_file:文件路径:diff内容

确保每个部分都不为空。

命令:"""
                    
                    retry_action = await self.llm_manager._call_llm(retry_prompt)
                    retry_action = retry_action.strip()
                    
                    if retry_action and self._validate_file_command(retry_action):
                        logger.info(f"🔄 重试成功，使用新命令: {retry_action}")
                        action = retry_action
                    else:
                        logger.warning(f"⚠️ 重试后命令仍然无效: '{retry_action}'")
                        continue
                
            # 执行动作
            logger.info(f"🔧 开始执行动作: {action}")
            return_value = self._execute_action(action)
            
            # 增加执行结果日志
            if return_value:
                logger.info(f"📋 动作执行结果 ({len(return_value)}字符):")
                # 显示前300字符
                result_preview = return_value[:300] + "..." if len(return_value) > 300 else return_value
                logger.info(f"   {result_preview}")
            else:
                logger.warning(f"⚠️ 动作执行返回空结果")
            
            # 记录执行结果到长期记忆（用于操作历史）
            execution_record = f"执行: {action}"
            if return_value:
                # 对于文件操作，只记录文件名，不记录完整内容
                if action.startswith("diff_file:"):
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
            
            # 适度的思考记录，保持思考能力
            if iteration_count % 3 == 0:  # 每3次迭代记录一次思考
                await self.memory_manager.record_progress_thinking(
                    self.llm_manager, issue, action, return_value, iteration_count
                )
            
            # 智能完成检查 - 结合思考能力和实际文件操作
            if iteration_count > 3:  # 给足够时间进行分析和修改
                # 检查是否有实际的文件修改操作
                has_file_operations = any("成功编辑文件" in memory for memory in self.long_term_memories[-10:])
                
                if has_file_operations:
                    # 让AI判断任务是否真正完成
                    completion_check = await self.llm_manager._call_llm(f"""
检查任务完成情况：

任务: {issue}
操作历史: {memories_text}

判断标准:
1. 是否执行了文件修改操作？
2. 修改的代码是否实现了任务要求的功能？
3. 代码是否完整且可运行？

如果任务已完成且代码实现正确，回答 "yes"
如果还有未完成的部分，回答 "no"

答案:""")
                    
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
    
    def _validate_file_command(self, action: str) -> bool:
        """验证diff_file命令格式"""
        try:
            if action.startswith("diff_file:"):
                parts = action.split(":", 2)
                if len(parts) != 3:
                    return False
                filepath, diff_content = parts[1].strip(), parts[2].strip()
                if not filepath or not diff_content:
                    logger.warning(f"diff_file命令缺少文件路径或diff内容")
                    return False
                return True
                
            return True
            
        except Exception as e:
            logger.error(f"验证文件命令时出错: {e}")
            return False
    
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
            if action.startswith("diff_file:"):
                return self._apply_diff(action)
            else:
                # 检查是否是常见的无效响应
                invalid_responses = [
                    "我需要", "首先", "让我", "我会", "我应该", "我建议", 
                    "根据", "基于", "为了", "现在", "接下来", "然后",
                    "这个任务", "要完成", "我认为", "看起来", "似乎",
                    "command:", "命令:", "执行:", "操作:", "步骤:",
                    "分析", "思考", "理解", "设计", "计划", "总结",
                    "本任务", "这个功能", "我们需要", "应该实现"
                ]
                if any(action.lower().startswith(phrase.lower()) for phrase in invalid_responses):
                    logger.warning(f"⚠️ 检测到自然语言响应，非命令格式: {action}")
                    self.add_long_term_memory(f"⚠️ 收到自然语言响应而非命令: {action[:50]}...")
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
                logger.info(f"🖥️ 准备执行终端命令: {action}")
                logger.info(f"📂 执行目录: {self.user_project_path}")
                
                # 设置环境变量
                env = os.environ.copy()
                env['PYTHONPATH'] = f"{self.user_project_path}:{env.get('PYTHONPATH', '')}"
                
                # 执行命令
                logger.info(f"⏳ 开始执行命令...")
                result = subprocess.run(
                    action, 
                    shell=True, 
                    capture_output=True, 
                    text=True, 
                    cwd=self.user_project_path, 
                    timeout=60,  # 增加超时时间
                    env=env
                )
                
                # 详细记录执行结果
                logger.info(f"✅ 命令执行完成，退出码: {result.returncode}")
                
                if result.stdout:
                    logger.info(f"📤 标准输出 ({len(result.stdout)}字符):")
                    # 显示前500字符，避免日志过长
                    stdout_preview = result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout
                    logger.info(f"   {stdout_preview}")
                else:
                    logger.info(f"📤 标准输出: 无")
                
                if result.stderr:
                    logger.warning(f"📤 错误输出 ({len(result.stderr)}字符):")
                    # 显示前500字符，避免日志过长
                    stderr_preview = result.stderr[:500] + "..." if len(result.stderr) > 500 else result.stderr
                    logger.warning(f"   {stderr_preview}")
                else:
                    logger.info(f"📤 错误输出: 无")
                
                # 构建返回结果
                output = []
                if result.stdout:
                    output.append(f"标准输出:\n{result.stdout}")
                if result.stderr:
                    output.append(f"错误输出:\n{result.stderr}")
                
                output.append(f"退出码: {result.returncode}")
                
                result_text = "\n".join(output)
                logger.info(f"📋 返回给LLM的结果长度: {len(result_text)}字符")
                
                return result_text
            
        except subprocess.TimeoutExpired:
            return "命令执行超时（60秒）"
        except Exception as e:
            return f"命令执行失败: {str(e)}"
    

    
    def _apply_diff(self, action: str) -> str:
        """应用diff到文件"""
        try:
            # 格式: diff_file:filepath:diff_content
            parts = action.split(":", 2)
            if len(parts) != 3:
                return "错误: diff_file命令格式应为 diff_file:filepath:diff_content"
            
            filepath = parts[1].strip()
            diff_content = parts[2].strip()
            
            # 验证diff内容不为空
            if not diff_content:
                return f"错误: diff内容为空，拒绝应用空diff: {filepath}"
            
            # 构建完整路径
            full_path = os.path.join(self.user_project_path, filepath)
            
            logger.info(f"📝 准备应用diff到文件: {filepath}")
            logger.info(f"📄 diff内容长度: {len(diff_content)}字符")
            
            # 显示diff内容预览
            diff_preview = diff_content[:200] + "..." if len(diff_content) > 200 else diff_content
            logger.info(f"📖 diff内容预览: {diff_preview}")
            
            # 如果文件不存在，尝试创建它
            if not os.path.exists(full_path):
                logger.info(f"📁 文件不存在，将创建新文件: {filepath}")
                # 确保目录存在
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                # 创建空文件
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write("")
            
            # 读取原文件内容
            original_content = self._read_file_with_encoding(full_path)
            
            # 使用Python的difflib来应用diff
            result = self._apply_unified_diff(original_content, diff_content)
            
            if result["success"]:
                # 写回文件
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(result["new_content"])
                
                logger.info(f"✅ 成功应用diff到文件: {filepath}")
                return f"✅ 成功应用diff到文件: {filepath} (修改后内容长度: {len(result['new_content'])}字符)"
            else:
                return f"错误: 应用diff失败: {result['error']}"
                
        except Exception as e:
            error_msg = f"应用diff失败: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def _apply_unified_diff(self, original_content: str, diff_content: str) -> dict:
        """应用unified diff到文件内容"""
        try:
            import difflib
            import re
            
            logger.info(f"🔍 开始解析diff内容，原文件内容长度: {len(original_content)}字符")
            logger.info(f"🔍 diff内容长度: {len(diff_content)}字符")
            
            # 分割原文件内容为行
            original_lines = original_content.splitlines(keepends=True)
            logger.info(f"🔍 原文件行数: {len(original_lines)}")
            
            # 解析diff内容
            diff_lines = diff_content.splitlines()
            logger.info(f"🔍 diff行数: {len(diff_lines)}")
            
            # 显示diff内容的前几行用于调试
            for i, line in enumerate(diff_lines[:10]):
                logger.info(f"🔍 diff行{i+1}: {repr(line)}")
            
            # 找到@@行，解析行号信息
            hunk_pattern = r'@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@'
            
            new_lines = original_lines[:]
            found_hunks = 0
            
            i = 0
            while i < len(diff_lines):
                line = diff_lines[i]
                
                # 跳过文件头
                if line.startswith('---') or line.startswith('+++'):
                    logger.info(f"🔍 跳过文件头: {repr(line)}")
                    i += 1
                    continue
                
                # 处理hunk
                if line.startswith('@@'):
                    logger.info(f"🔍 发现hunk: {repr(line)}")
                    match = re.match(hunk_pattern, line)
                    if not match:
                        logger.warning(f"⚠️ hunk格式不匹配: {repr(line)}")
                        i += 1
                        continue
                    
                    found_hunks += 1
                    old_start = int(match.group(1)) - 1  # 转换为0-based索引
                    old_count = int(match.group(2)) if match.group(2) else 1
                    new_start = int(match.group(3)) - 1  # 转换为0-based索引
                    new_count = int(match.group(4)) if match.group(4) else 1
                    
                    logger.info(f"🔍 hunk参数: old_start={old_start}, old_count={old_count}, new_start={new_start}, new_count={new_count}")
                    
                    # 处理这个hunk
                    hunk_result = self._process_hunk(
                        new_lines, diff_lines, i + 1, old_start, old_count
                    )
                    
                    if not hunk_result["success"]:
                        logger.error(f"❌ hunk处理失败: {hunk_result['error']}")
                        return {"success": False, "error": hunk_result["error"]}
                    
                    new_lines = hunk_result["new_lines"]
                    i = hunk_result["next_index"]
                    logger.info(f"🔍 hunk处理成功，新文件行数: {len(new_lines)}")
                else:
                    i += 1
            
            logger.info(f"🔍 总共处理了 {found_hunks} 个hunk")
            
            if found_hunks == 0:
                logger.warning("⚠️ 没有找到任何有效的hunk，可能是diff格式问题")
                # 如果没有找到hunk，但有添加行，尝试简单处理
                additions = []
                for line in diff_lines:
                    if line.startswith('+') and not line.startswith('+++'):
                        additions.append(line[1:])  # 去掉前缀
                
                if additions:
                    logger.info(f"🔍 尝试简单处理，发现 {len(additions)} 个添加行")
                    for add_line in additions:
                        if not add_line.endswith('\n'):
                            add_line += '\n'
                        new_lines.append(add_line)
                    logger.info(f"🔍 简单处理后文件行数: {len(new_lines)}")
                else:
                    logger.warning("⚠️ 也没有找到简单的添加行")
            
            new_content = ''.join(new_lines)
            logger.info(f"🔍 最终文件内容长度: {len(new_content)}字符")
            
            # 显示最终内容的前几行用于调试
            final_lines = new_content.splitlines()
            for i, line in enumerate(final_lines[:5]):
                logger.info(f"🔍 最终内容行{i+1}: {repr(line)}")
            
            return {"success": True, "new_content": new_content}
            
        except Exception as e:
            logger.error(f"❌ 解析diff异常: {str(e)}")
            return {"success": False, "error": f"解析diff失败: {str(e)}"}
    
    def _process_hunk(self, lines: list, diff_lines: list, start_index: int, 
                     old_start: int, old_count: int) -> dict:
        """处理一个diff hunk"""
        try:
            logger.info(f"🔍 开始处理hunk，起始索引: {start_index}, old_start: {old_start}, old_count: {old_count}")
            logger.info(f"🔍 当前文件行数: {len(lines)}")
            
            deletions = []
            additions = []
            context_lines = []
            
            i = start_index
            while i < len(diff_lines):
                line = diff_lines[i]
                logger.info(f"🔍 处理diff行{i+1}: {repr(line)}")
                
                # 如果遇到新的@@行，停止处理当前hunk
                if line.startswith('@@'):
                    logger.info(f"🔍 遇到新hunk，停止处理当前hunk")
                    break
                
                if line.startswith('-'):
                    # 删除行
                    del_content = line[1:]  # 去掉前缀
                    deletions.append(del_content)
                    logger.info(f"🔍 删除行: {repr(del_content)}")
                elif line.startswith('+'):
                    # 添加行
                    add_content = line[1:]  # 去掉前缀
                    additions.append(add_content)
                    logger.info(f"🔍 添加行: {repr(add_content)}")
                elif line.startswith(' '):
                    # 上下文行
                    context_content = line[1:]  # 去掉前缀
                    context_lines.append(context_content)
                    logger.info(f"🔍 上下文行: {repr(context_content)}")
                else:
                    # 空行或其他，可能是hunk结束
                    logger.info(f"🔍 遇到空行或其他，可能是hunk结束: {repr(line)}")
                    break
                
                i += 1
            
            logger.info(f"🔍 hunk解析完成 - 删除: {len(deletions)}行, 添加: {len(additions)}行, 上下文: {len(context_lines)}行")
            
            # 应用修改
            # 简单的处理：删除旧行，添加新行
            if deletions:
                logger.info(f"🔍 开始删除 {len(deletions)} 行")
                # 找到要删除的行
                for del_line in deletions:
                    found = False
                    for j in range(len(lines)):
                        if lines[j].rstrip('\n') == del_line.rstrip('\n'):
                            logger.info(f"🔍 找到并删除行{j+1}: {repr(lines[j])}")
                            lines.pop(j)
                            found = True
                            break
                    if not found:
                        logger.warning(f"⚠️ 未找到要删除的行: {repr(del_line)}")
            
            # 添加新行
            if additions:
                logger.info(f"🔍 开始添加 {len(additions)} 行")
                # 在适当位置插入新行
                insert_pos = min(old_start, len(lines))
                logger.info(f"🔍 插入位置: {insert_pos}")
                
                for add_line in additions:
                    if not add_line.endswith('\n'):
                        add_line += '\n'
                    lines.insert(insert_pos, add_line)
                    logger.info(f"🔍 在位置{insert_pos}插入: {repr(add_line)}")
                    insert_pos += 1
            
            logger.info(f"🔍 hunk处理完成，新文件行数: {len(lines)}")
            
            return {
                "success": True, 
                "new_lines": lines, 
                "next_index": i
            }
            
        except Exception as e:
            logger.error(f"❌ 处理hunk异常: {str(e)}")
            return {"success": False, "error": f"处理hunk失败: {str(e)}"}
    

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
            
            # 安全地访问result字典
            if isinstance(result, dict):
                success = result.get("completed", False)
                iterations = result.get("iterations", 0)
                error = None if success else "任务未在最大迭代次数内完成"
            else:
                success = False
                iterations = 0
                error = f"返回结果格式错误: {type(result)}"
            
            return {
                "success": success,
                "iterations": iterations,
                "long_term_memories": self.long_term_memories[-10:],
                "short_term_memory": self.short_term_memory,
                "error": error
            }
                
        except Exception as e:
            # 安全地处理异常信息，避免格式化错误
            try:
                error_msg = f"实现Issue时发生异常: {str(e)}"
            except:
                error_msg = "实现Issue时发生未知异常"
            
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
            content = self._read_file_with_encoding(input_path)
            memory_data = json.loads(content)
            
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
    
    def _read_file_with_encoding(self, file_path: str) -> str:
        """尝试用多种编码读取文件"""
        encodings = ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1', 'gbk', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    # 检查内容是否合理（不包含太多控制字符）
                    if self._is_text_content(content):
                        return content
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                logger.debug(f"尝试编码 {encoding} 读取文件 {file_path} 失败: {e}")
                continue
        
        # 如果所有编码都失败，尝试以二进制方式读取并忽略错误
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                logger.warning(f"文件 {file_path} 使用UTF-8编码读取时忽略了一些字符")
                return content
        except Exception as e:
            logger.error(f"无法读取文件 {file_path}: {e}")
            return ""
    
    def _is_text_content(self, content: str) -> bool:
        """检查内容是否是合理的文本内容"""
        if not content:
            return True
        
        # 计算控制字符的比例
        control_chars = sum(1 for c in content if ord(c) < 32 and c not in '\t\n\r')
        total_chars = len(content)
        
        # 如果控制字符超过5%，认为不是文本文件
        if total_chars > 0 and control_chars / total_chars > 0.05:
            return False
        
        return True

    async def _get_code_changes(self) -> dict[str, str]:
        """获取代码更改"""
        try:
            code_changes = {}
            
            # 获取当前工作目录中的所有相关文件
            for root, dirs, files in os.walk(self.user_project_path):
                # 跳过隐藏目录和特殊目录
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', '.memory']]
                
                for file in files:
                    # 过滤掉agent工作文件和临时文件
                    if (file.endswith(('.py', '.js', '.ts', '.html', '.css', '.json', '.md')) and 
                        not file.startswith('agent_') and 
                        not file.startswith('.') and
                        file not in ['.issues.json', '.pull_requests.json']):
                        
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, self.user_project_path)
                        
                        try:
                            # 尝试多种编码方式读取文件
                            content = self._read_file_with_encoding(file_path)
                            if content and content.strip():  # 只包含非空文件
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
                            content = self._read_file_with_encoding(issues_file)
                            issues_data = json.loads(content)
                            
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
                                            
                                            # 安全地检查result格式
                                            if isinstance(result, dict) and result.get("success", False):
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
                                                error_msg = result.get('error', '未知错误') if isinstance(result, dict) else str(result)
                                                logger.error(f"❌ Issue {issue_title} 实现失败: {error_msg}")
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