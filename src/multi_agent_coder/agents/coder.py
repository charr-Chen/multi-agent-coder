"""
极简、灵活、prompt驱动的编码员代理。
所有开发任务都通过prompt驱动LLM完成。
memory只存储AI在写代码过程中的思考和决策链。
"""

import os
import json
import logging
import asyncio
import time
from typing import Any, Optional
from ..git_utils import GitManager
from ..llm_utils import LLMManager
from .memory_manager import MemoryManager

logger = logging.getLogger(__name__)

def _implement_issue(self, *args, **kwargs):
    while True:
        prompt = f"""blahblahblah

        current memories:
        {memories}

        current issue:
        {issue}
        """
        action = llm.generate('<decide-action-prompt-plus-memories-plus-issue>')
        return_value = tools_api.execute(action)
        update_memory(action, return_value)
        
        completed = llm.generate('<prompt-plus-memories>')

        if completed:
            break

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
            memory_manager: 记忆管理器
        """
        self.agent_id = agent_id
        self.llm_manager = llm_manager
        self.user_project_path = user_project_path
        self.memory_manager = memory_manager
        
        # 初始化记忆管理器
        if not self.memory_manager:
            self.memory_manager = MemoryManager(agent_id)
        
        # 初始化协作相关组件
        self.playground_git_manager = None
        self.collaboration_manager = None
        self.multi_repo_manager = None
        
        logger.info(f"初始化代码实现代理: {agent_id}")

    def set_playground_git_manager(self, playground_git_manager):
        """设置playground仓库管理器"""
        self.playground_git_manager = playground_git_manager
        logger.info(f"{self.agent_id} 设置playground仓库管理器")
    
    def set_collaboration_manager(self, collaboration_manager):
        """设置协作管理器"""
        self.collaboration_manager = collaboration_manager
        logger.info(f"{self.agent_id} 设置协作管理器")
    
    def set_multi_repo_manager(self, multi_repo_manager):
        """设置多仓库管理器"""
        self.multi_repo_manager = multi_repo_manager
        logger.info(f"{self.agent_id} 设置多仓库管理器")

    async def _analyze_context(self, issue: dict[str, Any]) -> str:
        """分析Issue上下文
        
        Args:
            issue: Issue信息
            
        Returns:
            上下文分析结果
        """
        try:
            # 构建分析prompt
            analysis_prompt = f"""
请分析以下Issue的上下文，包括：
1. 技术栈和架构要求
2. 功能复杂度评估
3. 与其他模块的依赖关系
4. 实现策略建议
5. 潜在风险和注意事项

Issue标题: {issue.get('title', '')}
Issue描述: {issue.get('description', '')}

请提供简洁但全面的分析：
"""
            
            # 调用LLM进行分析
            response = await self.llm_manager.execute_task(
                "analyze_code",
                {
                    "issue": issue,
                    "analysis_type": "context"
                }
            )
            
            if isinstance(response, dict):
                analysis = response.get("analysis", "无法分析上下文")
                confidence = response.get("confidence", 0.8)
                
                # 存储上下文理解
                self.memory_manager.store_issue_analysis(
                    issue_description=issue.get('title', ''),
                    analysis=analysis,
                    solution=f"信心度: {confidence}"
                )
                
                return analysis
            
            return "无法分析上下文"
                
        except Exception as e:
            logger.warning(f"上下文分析失败: {e}")
            return "上下文分析失败"

    async def work_on_issue(self, issue: dict[str, Any]) -> bool:
        """处理指定的Issue
        
        Args:
            issue: Issue信息
            
        Returns:
            是否成功处理
        """
        try:
            logger.info(f"🤖 {self.agent_id} 开始处理Issue: {issue.get('title', '未知任务')}")
            
            # 1. 分析上下文并存储思考过程
            context_analysis = await self._analyze_context(issue)
            self.memory_manager.store_thinking_process(
                thought=f"分析Issue上下文:\n{context_analysis}",
                context_info=f"Issue: {issue.get('title', '')}",
                conclusion="开始实现功能"
            )
            
            # 2. 构建实现计划
            implementation_plan = await self._create_implementation_plan(issue, context_analysis)
            self.memory_manager.store_implementation_plan(
                task=issue.get('title', ''),
                plan=implementation_plan,
                outcome="目标: 完成功能实现、确保代码质量、维护项目结构"
            )
            
            # 3. 执行实现
            result = await self._implement_solution(issue, implementation_plan)
            
            if not result:
                logger.error(f"❌ {self.agent_id} 实现失败")
                # 存储失败经验
                self.memory_manager.store_learning_experience(
                    lesson=f"实现{issue.get('title', '')}失败",
                    context_info=context_analysis,
                    improvement="需要改进实现策略"
                )
                return False
            
            # 4. 处理实现结果
            modified_files = []
            if isinstance(result, dict):
                if "file_path" in result and "code" in result:
                    modified_files = await self._handle_file_changes(result)
                elif "files" in result:
                    for file_info in result["files"]:
                        files = await self._handle_file_changes(file_info)
                        modified_files.extend(files)
            
            if not modified_files:
                logger.warning(f"⚠️ {self.agent_id} 没有产生任何文件修改")
                return False
            
            # 5. 提交更改
            if hasattr(self, 'playground_git_manager') and self.playground_git_manager:
                commit_message = f"feat: {issue.get('title', '实现功能')}\n\n{issue.get('description', '')}"
                await self.playground_git_manager.commit_changes(commit_message, modified_files)
            
            # 6. 更新Issue状态
            if hasattr(self, 'playground_git_manager') and self.playground_git_manager:
                await self.playground_git_manager.update_issue_status(
                    issue["id"],
                    "completed",
                    json.dumps({"modified_files": modified_files})
                )
            
            # 7. 存储成功经验
            self.memory_manager.store_learning_experience(
                lesson=f"成功实现Issue: {issue.get('title', '')}",
                context_info=context_analysis,
                improvement="继续优化代码质量和架构设计"
            )
            
            # 8. 存储创意想法（如果有）
            if isinstance(result, dict) and result.get("operation") == "enhance":
                self.memory_manager.store_memory(
                    f"创意想法: 增强了现有功能 {issue.get('title', '')}，类别: feature_enhancement，潜在影响: 提升用户体验和系统功能，实现说明: 修改了 {len(modified_files)} 个文件"
                )
            
            # 9. 存储TODO项目（如果需要后续工作）
            if len(modified_files) > 2:
                self.memory_manager.store_memory(
                    f"待办事项: 测试和验证 {issue.get('title', '')} 的实现，优先级: high，状态: pending"
                )
            
            logger.info(f"✅ {self.agent_id} 成功处理Issue")
            return True
            
        except Exception as e:
            logger.error(f"❌ {self.agent_id} 处理Issue失败: {e}")
            return False

    async def _create_implementation_plan(self, issue: dict[str, Any], context_analysis: str) -> str:
        """创建实现计划
        
        Args:
            issue: Issue信息
            context_analysis: 上下文分析结果
            
        Returns:
            实现计划
        """
        try:
            # 调用LLM创建实现计划
            response = await self.llm_manager.execute_task(
                "plan_implementation",
                {
                    "issue": issue,
                    "analysis": {"context_analysis": context_analysis}
                }
            )
            
            if isinstance(response, dict):
                plan = response.get("plan", "")
                
                # 存储决策日志
                self.memory_manager.store_decision_log(
                    decision=f"采用实现方案: {plan}",
                    reasoning=response.get("reasoning", ""),
                    outcome="待执行"
                )
                
                return plan
            
            return ""
                
        except Exception as e:
            logger.warning(f"创建实现计划失败: {e}")
            return ""

    async def _implement_solution(self, issue: dict[str, Any], implementation_plan: str) -> Any:
        """实现解决方案
        
        Args:
            issue: Issue信息
            implementation_plan: 实现计划
            
        Returns:
            实现结果
        """
        try:
            # 获取相关记忆
            relevant_memories = self.memory_manager.retrieve_memories(
                query=f"{issue.get('title', '')} {issue.get('type', '')}",
                limit=5
            )
            
            # 构建上下文
            context = {
                "issue": issue,
                "implementation_plan": implementation_plan,
                "relevant_memories": [
                    memory.context for memory in relevant_memories
                ],
                "recent_thoughts": [
                    {
                        "thought": f"分析Issue: {issue.get('title', '')}",
                        "context": {"step": "需求分析"},
                        "conclusion": "开始实现",
                        "confidence": 0.8
                    }
                ]
            }
            
            # 调用LLM实现功能
            result = await self.llm_manager.execute_task(
                "implement_issue",
                context
            )
            
            return result
                
        except Exception as e:
            logger.error(f"实现解决方案失败: {e}")
            return None

    async def _handle_file_changes(self, file_info: dict[str, Any]) -> list[str]:
        """处理文件变更
        
        Args:
            file_info: 文件信息
            
        Returns:
            修改的文件列表
        """
        modified_files = []
        try:
            file_path = file_info["file_path"]
            full_path = os.path.join(self.user_project_path, file_path)
            
            # 检查是否是现有文件
            is_existing_file = os.path.exists(full_path)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # 如果是现有文件，先读取原内容用于对比
            original_content = ""
            if is_existing_file:
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        original_content = f.read()
                except Exception as e:
                    logger.warning(f"读取现有文件失败 {file_path}: {e}")
            
            # 写入新内容
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(file_info["code"])
            
            modified_files.append(file_path)
            
            action = "modify" if is_existing_file else "create"
            logger.info(f"📝 {action}文件: {file_path}")
            
            # 记录文件变更
            if is_existing_file:
                self.memory_manager.store_file_change(
                    file_path=file_path,
                    action="modify",
                    details=f"修改了现有文件，原内容长度: {len(original_content) if original_content else 0}，新内容长度: {len(file_info['code'])}"
                )
            else:
                self.memory_manager.store_file_change(
                    file_path=file_path,
                    action="create",
                    details=f"创建了新文件，内容长度: {len(file_info['code'])}"
                )
            
        except Exception as e:
            logger.error(f"处理文件变更失败: {e}")
            
        return modified_files

    async def run(self):
        """Agent主运行循环（抢夺Issues并处理）"""
        logger.info(f"🚀 {self.agent_id} 开始运行...")
        
        while True:
            try:
                # 检查是否有可抢夺的Issues
                if self.playground_git_manager:
                    issues_file = os.path.join(self.playground_git_manager.repo_path, ".issues.json")
                    logger.debug(f"🔍 {self.agent_id} 检查Issues文件: {issues_file}")
                    
                    if os.path.exists(issues_file):
                        with open(issues_file, 'r', encoding='utf-8') as f:
                            issues_data = json.load(f)
                        
                        all_issues = issues_data.get('issues', [])
                        logger.info(f"📋 {self.agent_id} 发现 {len(all_issues)} 个总Issues")
                        
                        # 详细记录每个issue的状态
                        for i, issue in enumerate(all_issues):
                            status = issue.get('status', 'unknown')
                            assigned_to = issue.get('assigned_to', None)
                            title = issue.get('title', 'Unknown')
                            logger.debug(f"  Issue {i+1}: '{title}' - status: {status}, assigned_to: {assigned_to}")
                        
                        # 🆕 修复逻辑：同时处理未分配的Issues和已分配给自己的Issues
                        unassigned_issues = []
                        my_assigned_issues = []
                        
                        for issue in all_issues:
                            status = issue.get('status', 'unknown')
                            assigned_to = issue.get('assigned_to', None)
                            title = issue.get('title', 'Unknown')
                            
                            if not assigned_to:
                                # 未分配的Issues，可以抢夺
                                unassigned_issues.append(issue)
                                logger.debug(f"✅ 可抢夺Issue: '{title}' (status: {status})")
                            elif assigned_to == self.agent_id and status == 'assigned':
                                # 已分配给我但还未完成的Issues
                                my_assigned_issues.append(issue)
                                logger.debug(f"🎯 我的待处理Issue: '{title}' (status: {status})")
                            else:
                                logger.debug(f"❌ 其他Issue: '{title}' -> {assigned_to} (status: {status})")
                        
                        logger.info(f"📋 {self.agent_id} 状态: {len(unassigned_issues)}个可抢夺, {len(my_assigned_issues)}个待处理")
                        
                        # 优先处理已分配给自己的Issues
                        if my_assigned_issues:
                            target_issue = my_assigned_issues[0]
                            logger.info(f"🔄 {self.agent_id} 继续处理Issue: {target_issue.get('title')}")
                            
                            # 处理Issue
                            success = await self.work_on_issue(target_issue)
                            
                            if success:
                                # 标记为完成
                                target_issue['status'] = 'completed'
                                # 保存更新
                                with open(issues_file, 'w', encoding='utf-8') as f:
                                    json.dump(issues_data, f, indent=2, ensure_ascii=False)
                                logger.info(f"✅ {self.agent_id} 完成Issue: {target_issue.get('title')}")
                            else:
                                logger.error(f"❌ {self.agent_id} 处理Issue失败: {target_issue.get('title')}")
                        
                        # 如果没有待处理的，尝试抢夺新的Issues
                        elif unassigned_issues:
                            target_issue = unassigned_issues[0]
                            
                            # 标记为已分配
                            target_issue['assigned_to'] = self.agent_id
                            target_issue['status'] = 'assigned'
                            
                            # 保存更新
                            with open(issues_file, 'w', encoding='utf-8') as f:
                                json.dump(issues_data, f, indent=2, ensure_ascii=False)
                            
                            logger.info(f"🎯 {self.agent_id} 抢夺新Issue: {target_issue.get('title')}")
                            
                            # 处理Issue
                            success = await self.work_on_issue(target_issue)
                            
                            if success:
                                # 标记为完成
                                target_issue['status'] = 'completed'
                                # 保存更新
                                with open(issues_file, 'w', encoding='utf-8') as f:
                                    json.dump(issues_data, f, indent=2, ensure_ascii=False)
                                logger.info(f"✅ {self.agent_id} 完成Issue: {target_issue.get('title')}")
                            else:
                                logger.error(f"❌ {self.agent_id} 处理Issue失败: {target_issue.get('title')}")
                    
                    # 等待一段时间再检查
                    await asyncio.sleep(10)
                else:
                    logger.warning(f"⚠️ {self.agent_id} 未设置playground仓库管理器")
                    await asyncio.sleep(30)  # 等待更长时间
                    
            except Exception as e:
                logger.error(f"❌ {self.agent_id} 运行出错: {e}")
                import traceback
                logger.error(f"🔍 错误详情:\n{traceback.format_exc()}")
                await asyncio.sleep(30)  # 出错后等待更长时间

    async def create_pull_request_for_changes(self, issue: dict[str, Any], modified_files: list[str], context: dict[str, Any]):
        """为代码修改创建Pull Request"""
        if not self.collaboration_manager:
            logger.warning("未设置协作管理器，跳过PR创建")
            return
            
        try:
            pr_title = f"实现Issue: {issue.get('title', '未知任务')}"
            pr_description = f"""
## Issue 详情
- **标题**: {issue.get('title', '未知任务')}
- **描述**: {issue.get('description', '无描述')}
- **负责Agent**: {self.agent_id}

## 修改文件
{chr(10).join([f"- {file}" for file in modified_files])}

---
*此PR由AI Agent自动创建*
"""
            
            # 准备代码更改字典
            code_changes = {}
            for file_path in modified_files:
                full_path = os.path.join(self.user_project_path, file_path)
                if os.path.exists(full_path):
                    with open(full_path, 'r', encoding='utf-8') as f:
                        code_changes[file_path] = f.read()
            
            # 创建分支名
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            source_branch = f"feature/{self.agent_id}-{timestamp}"
            
            # 创建PR
            pr_id = await self.collaboration_manager.create_pull_request(
                title=pr_title,
                author=self.agent_id,
                source_branch=source_branch,
                description=pr_description,
                code_changes=code_changes
            )
            
            logger.info(f"🎉 {self.agent_id} 成功创建PR: {pr_id}")
            logger.info(f"📋 PR标题: {pr_title}")
            logger.info(f"🌿 分支: {source_branch}")
            logger.info(f"📁 修改文件: {', '.join(modified_files)}")
            
            return pr_id
            
        except Exception as e:
            logger.error(f"❌ {self.agent_id} 创建PR失败: {e}")
            return None
    
    async def generate_user_report(self, issue: dict[str, Any], modified_files: list[str], thoughts: list[dict]):
        """生成用户可读的工作报告"""
        try:
            # 获取当前时间
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 生成报告内容
            report_content = f"""# 🤖 AI Agent工作报告

## 📋 基本信息
- **Agent ID**: {self.agent_id}
- **完成时间**: {timestamp}
- **Issue标题**: {issue.get('title', '未知')}

## 📖 Issue描述
{issue.get('description', '无描述')}

## 🧠 AI思考过程
"""
            
            # 添加思考过程
            for i, thought in enumerate(thoughts, 1):
                confidence = thought.get('confidence', 0.5)
                confidence_emoji = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.5 else "🔴"
                
                report_content += f"""
### 步骤 {i} {confidence_emoji}
- **思考**: {thought.get('thought', '无记录')}
- **结论**: {thought.get('conclusion', '无结论')}
- **信心度**: {confidence:.1%}
"""

            # 添加文件修改信息
            report_content += f"""

## 📁 创建/修改的文件 ({len(modified_files)}个)
"""
            
            for file_path in modified_files:
                report_content += f"""
### `{file_path}`
"""
                # 尝试读取文件内容的前几行作为预览
                try:
                    full_path = os.path.join(self.user_project_path, file_path)
                    if os.path.exists(full_path):
                        with open(full_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                            preview_lines = lines[:10]  # 显示前10行
                            if len(lines) > 10:
                                preview_lines.append("... (还有更多内容)")
                            
                            # 确定文件类型来选择代码块语法
                            if file_path.endswith(('.py', '.pyx')):
                                lang = 'python'
                            elif file_path.endswith(('.js', '.jsx')):
                                lang = 'javascript'
                            elif file_path.endswith(('.ts', '.tsx')):
                                lang = 'typescript'
                            elif file_path.endswith(('.html', '.htm')):
                                lang = 'html'
                            elif file_path.endswith('.css'):
                                lang = 'css'
                            elif file_path.endswith('.md'):
                                lang = 'markdown'
                            else:
                                lang = 'text'
                            
                            report_content += f"""
```{lang}
{''.join(preview_lines)}
```
"""
                    else:
                        report_content += "\n*文件不存在或无法读取*\n"
                except Exception as e:
                    report_content += f"\n*读取文件时出错: {e}*\n"

            # 添加总结
            report_content += f"""

## 📊 工作总结
- ✅ 成功完成Issue: **{issue.get('title', '未知')}**
- 📝 创建/修改了 **{len(modified_files)}** 个文件
- 🧠 进行了 **{len(thoughts)}** 步AI思考分析
- 🎯 任务状态: **已完成**

## 💡 备注
此报告由AI Agent `{self.agent_id}` 自动生成。如有问题请查看详细日志或联系开发者。

---
*报告生成时间: {timestamp}*
"""

            # 保存报告到主项目目录
            report_filename = f"agent_report_{self.agent_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            
            # 尝试保存到主项目的reports目录
            if self.playground_git_manager:
                main_repo_path = self.playground_git_manager.repo_path
            else:
                main_repo_path = self.user_project_path
                
            reports_dir = os.path.join(main_repo_path, "reports")
            os.makedirs(reports_dir, exist_ok=True)
            
            report_path = os.path.join(reports_dir, report_filename)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            logger.info(f"📊 {self.agent_id} 生成用户报告: {report_path}")
            
            # 提交报告到Git（如果可能）
            try:
                if self.playground_git_manager:
                    await self.playground_git_manager.commit_changes(
                        f"添加{self.agent_id}工作报告: {issue.get('title', '未知')}",
                        [f"reports/{report_filename}"]
                    )
                    logger.info(f"📊 {self.agent_id} 报告已提交到Git")
            except Exception as e:
                logger.warning(f"⚠️ {self.agent_id} 提交报告失败: {e}")
            
        except Exception as e:
            logger.error(f"❌ {self.agent_id} 生成用户报告失败: {e}")
     