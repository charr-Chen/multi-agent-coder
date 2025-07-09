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
        # 注意：Issues管理通过playground_git_manager完成，不在用户项目目录中创建GitManager
        
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
            diff_examples = (
                """--- a/foo.py
+++ b/foo.py
@@ -1,3 +1,4 @@
 def foo():
     print(\"hello\")
+    print(\"world\")
"""
                """--- a/bar.txt
+++ b/bar.txt
@@ -2,7 +2,8 @@
line1
-line2
+line2 changed
line3
+new line4
line5
"""
                """--- a/test.js
+++ b/test.js
@@ -10,6 +10,8 @@
 function test() {
     doSomething();
+    log(\"added\");
 }
"""
            )
            action_prompt = f"""
你是一个专业的顶级全栈程序员AI，正在通过命令行操作实现代码功能。

【当前任务】
{issue}

【历史操作记录】
{memories_text}

【常用命令提示，实际上你可以使用任何有效的终端命令】
- ls -la                                    # 查看项目结构
- tree                                      # 查看目录树结构(如果可用)
- find . -name "*.py" -type f              # 查找Python文件
- find . -name "*.js" -type f              # 查找JavaScript文件  
- find . -name "*.json" -type f            # 查找配置文件
- cat <file>                               # 查看文件内容
- find . -name "*.py"                      # 查找Python文件
- grep -r "keyword" .                      # 搜索关键词
- cat > tmp.patch <<EOF
  <这里替换为多行 diff patch 内容>
  EOF                                      # 创建patch文件
- patch <目标文件路径> < tmp.patch           # 应用patch修改原始文件
- complete                                 # 标记完成

```bash
cat > tmp.patch <<EOF
--- main.py	2025-07-07 11:00:00.000000000 +0800
+++ main.py	2025-07-07 11:01:00.000000000 +0800
@@ -1,2 +1,2 @@
-print("Hello")
+print("Hi")
EOF

patch main.py < tmp.patch
```

【重要规则】
- 系统性地探索项目的结构，目录树结构，不要猜测文件位置，而是通过命令全面了解项目
- 系统性地探索文件内容，绝对不要猜测内容，充分理解现有代码内容后再修改
- **严禁假设和幻觉**：绝对不要说"假设找到了xxx文件"、"查看了该文件"、"确认了调用逻辑"等没有实际执行命令的描述
- **只能基于命令输出描述**：你只能基于实际执行命令的真实输出来描述文件内容，禁止凭空想象文件内容或结构
- 不能假设找到了某个符合要求的文件，必须是查看后确认实际存在且对应用户需求的文件
- 不要通过搜索关键词的方式查找需求修改的文件，而是通过实实在在地查看每个文件的内容确定哪里需要修改
- 修改文件前必须确认用户传入的项目里实际存在这个文件
- patch文件中的"原始代码"与实际文件内容必须是匹配的，与实际修改的目标文件一致
- 修改的不能是自己新创建的文件，也不能是.memory里假设的文件，必须是在用户传入项目里实际存在的文件
- 修改文件必须分两步：先用cat > <patch_file>创建patch文件，再用patch命令应用
- 不要使用其他方式修改文件，这是唯一的方式
- patch文件内容必须是**严格的unified diff格式**，不能有多余空行，不能有多余的空白字符，必须能被patch工具直接应用
- patch内容必须包含完整的文件头（--- 和 +++ 行）、@@行（显示行号信息），每行修改前必须有+、-或空格前缀
- **避免重复创建patch文件**：如果已经创建了一个patch文件来实现任务要求，不要再创建类似的patch文件进行"优化"
- **任务完成标准**：一旦创建了有效的patch文件并应用成功，通常任务就已经完成，除非有明确的错误需要修复

【patch文件创建格式说明】
```bash
cat > filename.patch <<EOF
--- a/file.py
+++ b/file.py
@@ -1,3 +1,4 @@
 def hello():
     print("Hello")
+    print("World")
EOF
patch main.py < fix.patch
```
- patch文件名：patch文件的名称，如changes.patch
- patch内容：标准的unified diff格式，包含文件头和@@行
- 使用EOF作为分隔符来包含多行patch内容

你可以输出多行命令，每行一个命令。先探索项目结构，找到需要修改的文件，理解代码后再进行修改。"""
            
            # 使用LLM生成动作
            logger.info(f"📤 发送prompt给LLM，长度: {len(action_prompt)}字符")
            action = await self.llm_manager._call_llm(action_prompt)
            action = action.strip()
            
            # 增加调试日志
            logger.info(f"🤖 LLM返回的原始响应 ({len(action)}字符): {action}")
            
            # 处理多行命令
            if '\n' in action:
                # 分割成多个命令
                commands = [cmd.strip() for cmd in action.split('\n') if cmd.strip()]
                logger.info(f"📝 LLM返回了{len(commands)}个命令:")
                for i, cmd in enumerate(commands, 1):
                    logger.info(f"   命令{i}: {cmd}")
                
                # 执行每个命令
                all_results = []
                for i, cmd in enumerate(commands, 1):
                    if cmd == "complete":
                        self.memory_manager.store_memory("手动标记任务完成")
                        break
                    
                    logger.info(f"🔧 执行命令 {i}/{len(commands)}: {cmd}")
                    cmd_result = self._execute_action(cmd)
                    all_results.append(f"命令{i} ({cmd}):\n{cmd_result}")
                    
                    # 如果是patch命令且失败了，停止后续命令
                    if cmd.startswith("patch ") and "失败" in cmd_result:
                        logger.warning(f"⚠️ patch命令失败，停止执行后续命令")
                        break
                
                return_value = "\n\n".join(all_results)
            else:
                # 单行命令，按原逻辑处理
                if action == "complete":
                    self.memory_manager.store_memory("手动标记任务完成")
                    break
                
                # 验证动作格式
                if not action or len(action) < 2:
                    logger.warning(f"⚠️ LLM返回的动作无效: '{action}'")
                    self.add_long_term_memory(f"⚠️ 无效动作: '{action}'")
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
                if action.startswith("cat > ") and "<<EOF" in action:
                    # 提取patch文件名
                    first_line = action.split('\n')[0].strip()
                    patch_filename = first_line.replace("cat > ", "").replace(" <<EOF", "").strip()
                    # 简单验证：检查文件是否真的存在
                    if os.path.exists(os.path.join(self.user_project_path, patch_filename)):
                        execution_record += f" → ✅ 成功创建patch文件: {patch_filename}"
                    else:
                        execution_record += f" → ❌ 失败：patch文件未创建"
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
            if iteration_count > 8:  # 给足够时间进行探索、分析和修改
                # 检查是否有实际的文件修改操作（创建patch文件或应用patch）
                has_file_operations = any("成功创建patch文件" in memory or "patch" in memory for memory in self.long_term_memories[-10:])
                
                if has_file_operations:
                    # 检查最近是否创建了patch文件
                    recent_patch_creations = [memory for memory in self.long_term_memories[-5:] if "成功创建patch文件" in memory]
                    
                    # 如果最近创建了patch文件，更严格地检查任务完成情况
                    if recent_patch_creations:
                        completion_check = await self.llm_manager._call_llm(f"""
检查任务完成情况：

任务: {issue}
操作历史: {memories_text}

重要提醒：
- 如果已经创建了patch文件来修改配置或代码，通常任务就已经完成了
- 不要为了"优化"而重复创建类似的patch文件
- 简单的配置更新通常一个patch文件就足够了

判断标准:
1. 是否执行了文件修改操作？
2. 修改的代码是否实现了任务要求的功能？
3. 代码是否完整且可运行？

如果任务已完成且代码实现正确，回答 "yes"
如果还有未完成的部分，回答 "no"

答案:""")
                    else:
                        # 普通的完成检查
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
            
            logger.info(f"🔧 清理后的动作: {action}")
            
            # 检查是否是创建patch文件命令
            if action.startswith("cat > ") and "<<EOF" in action:
                return self._create_patch_file(action)
            # 检查是否是patch命令
            elif action.startswith("patch "):
                # 直接执行patch命令
                pass  # 下面会走到通用命令执行逻辑
            # 其他命令直接尝试执行，失败了再反馈
            # 直接执行action作为终端命令
            logger.info(f"🖥️ 准备执行终端命令: {action}")
            logger.info(f"📂 执行目录: {self.user_project_path}")
            
            # 设置环境变量
            env = os.environ.copy()
            env['PYTHONPATH'] = f"{self.user_project_path}:{env.get('PYTHONPATH', '')}"
            
            # 执行命令
            logger.info(f"⏳ 开始执行命令...")
            import subprocess
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
    

    
    def _create_patch_file(self, action: str) -> str:
        """创建patch文件"""
        try:
            # 解析 cat > filename <<EOF ... EOF 格式
            lines = action.split('\n')
            if len(lines) < 3:
                return "错误: cat命令格式错误，需要至少3行"
            
            # 第一行应该是: cat > filename <<EOF
            first_line = lines[0].strip()
            if not first_line.startswith("cat > "):
                return "错误: cat命令格式错误"
            
            # 提取文件名
            filename_part = first_line.replace("cat > ", "").replace(" <<EOF", "").strip()
            patch_filename = filename_part
            
            # 查找EOF结束标记
            eof_found = False
            content_lines = []
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == "EOF":
                    eof_found = True
                    break
                content_lines.append(line)
            
            if not eof_found:
                return "错误: 未找到EOF结束标记"
            
            patch_content = '\n'.join(content_lines)
            
            # 验证patch内容不为空
            if not patch_content:
                return f"错误: patch内容为空，拒绝创建空patch文件: {patch_filename}"
            
            # 构建patch文件的完整路径
            patch_path = os.path.join(self.user_project_path, patch_filename)
            
            logger.info(f"📝 准备创建patch文件: {patch_filename}")
            logger.info(f"📄 patch内容长度: {len(patch_content)}字符")
            
            # 显示patch内容预览
            patch_preview = patch_content[:200] + "..." if len(patch_content) > 200 else patch_content
            logger.info(f"📖 patch内容预览: {patch_preview}")
            
            # 确保目录存在
            os.makedirs(os.path.dirname(patch_path), exist_ok=True)
            
            # 写入patch文件
            with open(patch_path, 'w', encoding='utf-8') as f:
                f.write(patch_content)
            
            logger.info(f"✅ 成功创建patch文件: {patch_filename}")
            return f"✅ 成功创建patch文件: {patch_filename} (内容长度: {len(patch_content)}字符)"
                
        except Exception as e:
            error_msg = f"创建patch文件失败: {str(e)}"
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