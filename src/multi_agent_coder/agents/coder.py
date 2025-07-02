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
from .thinking import MemoryManager
from .thinking.memory_manager import MemoryType, MemoryPriority

logger = logging.getLogger(__name__)

class CoderAgent:
    """
    极简、灵活、prompt驱动的编码员代理。
    所有开发任务都通过prompt驱动LLM完成。
    memory只存储AI在写代码过程中的思考和决策链。
    """
    def __init__(self, git_manager: GitManager, llm_manager: LLMManager, agent_id: str):
        self.git_manager = git_manager
        self.llm_manager = llm_manager
        self.agent_id = agent_id
        self.memory_manager = MemoryManager(agent_id)
        self.user_project_path = self.git_manager.repo_path if self.git_manager else None
        
        # 🆕 协作相关组件
        self.playground_git_manager = None
        self.collaboration_manager = None
        self.multi_repo_manager = None
        
        logger.info(f"编码员代理初始化完成: {agent_id}")

    async def work_on_issue(self, issue: dict[str, Any]) -> bool:
        """处理指定的Issue
        
        Args:
            issue: Issue信息
            
        Returns:
            是否成功处理
        """
        try:
            logger.info(f"🤖 {self.agent_id} 开始处理Issue: {issue.get('title', '未知任务')}")
            
            # 构建上下文
            context = await self.build_context(issue)
            
            # 运行LLM任务
            result, thoughts = await self.run_llm_task("coding", context)
            
            # 应用结果
            modified_files = await self.apply_result(result, context)
            
            if modified_files:
                logger.info(f"✅ {self.agent_id} 成功修改 {len(modified_files)} 个文件")
                
                # 🆕 智能存储记忆
                await self._store_intelligent_memory(issue, result, modified_files, thoughts)
                
                # 创建Pull Request（如果启用了协作模式）
                if hasattr(self, 'collaboration_manager') and self.collaboration_manager:
                    await self.create_pull_request_for_changes(issue, modified_files, context)
                
                # 生成工作报告
                await self.generate_user_report(issue, modified_files, thoughts)
                
                # 🆕 自动同步工作到playground仓库
                if hasattr(self, 'multi_repo_manager') and self.multi_repo_manager:
                    try:
                        logger.info(f"🔄 {self.agent_id} 开始同步工作到playground...")
                        sync_success = await self.multi_repo_manager.sync_agent_work_to_playground(self.agent_id)
                        if sync_success:
                            logger.info(f"✅ {self.agent_id} 成功同步工作到playground")
                        else:
                            logger.warning(f"⚠️ {self.agent_id} 同步工作到playground失败")
                    except Exception as e:
                        logger.error(f"❌ {self.agent_id} 同步工作异常: {e}")
                
                # 更新Issue状态
                if hasattr(self, 'playground_git_manager') and self.playground_git_manager:
                    await self.playground_git_manager.update_issue_status(
                        issue['id'], 
                        'completed',
                        f"由 {self.agent_id} 完成，修改了 {len(modified_files)} 个文件"
                    )
                
                return True
            else:
                logger.warning(f"⚠️ {self.agent_id} 没有产生任何文件修改")
                # 🆕 即使没有修改文件，也存储失败经验
                await self._store_intelligent_memory(issue, result, [], thoughts)
                return False
                
        except Exception as e:
            logger.error(f"❌ {self.agent_id} 处理Issue失败: {e}")
            import traceback
            logger.debug(f"🔍 错误详情:\n{traceback.format_exc()}")
            return False

    async def build_context(self, issue: dict[str, Any]) -> dict[str, Any]:
        """构建工作上下文
        
        Args:
            issue: Issue信息
            
        Returns:
            上下文字典
        """
        # 获取最近的思考过程
        recent_thoughts = []
        if hasattr(self, 'memory_manager'):
            recent_memories = self.memory_manager.get_recent_thinking_processes(5)
            for memory in recent_memories:
                recent_thoughts.append(memory.content)
        
        # 🆕 智能上下文分析
        context_analysis = await self._analyze_context(issue)
        
        # 🆕 存储上下文理解
        if hasattr(self, 'memory_manager'):
            self.memory_manager.store_context_understanding(
                context_type="issue_analysis",
                understanding=context_analysis,
                confidence=0.8,
                related_contexts=[issue.get('title', ''), issue.get('description', '')]
            )
        
        return {
            "issue": issue,
            "recent_thoughts": recent_thoughts,
            "context_analysis": context_analysis,
            "agent_id": self.agent_id
        }
    
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
            response = await self.llm_manager.chat_completion(
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.3
            )
            
            if response and isinstance(response, str):
                return response
            else:
                return "无法分析上下文"
                
        except Exception as e:
            logger.warning(f"上下文分析失败: {e}")
            return "上下文分析失败"
    
    async def _store_intelligent_memory(self, issue: dict[str, Any], result: Any, 
                                      modified_files: list[str], thoughts: list[dict]):
        """智能存储记忆
        
        Args:
            issue: Issue信息
            result: LLM结果
            modified_files: 修改的文件
            thoughts: 思考过程
        """
        if not hasattr(self, 'memory_manager'):
            return
        
        try:
            # 1. 存储AI决策
            decision_summary = f"处理Issue: {issue.get('title', '')}"
            reasoning = f"修改了 {len(modified_files)} 个文件: {', '.join(modified_files)}"
            
            self.memory_manager.store_ai_decision(
                context=issue.get('description', ''),
                decision=decision_summary,
                reasoning=reasoning,
                confidence=0.9 if modified_files else 0.5,
                impact=f"创建/修改了 {len(modified_files)} 个文件"
            )
            
            # 2. 存储工作流程洞察
            workflow_insight = f"成功处理Issue，使用了 {len(thoughts)} 个思考步骤"
            improvement_suggestions = []
            
            if len(modified_files) == 0:
                improvement_suggestions.append("需要改进代码生成策略")
            elif len(modified_files) > 3:
                improvement_suggestions.append("考虑将复杂任务分解为更小的单元")
            
            self.memory_manager.store_workflow_insight(
                workflow_type="issue_processing",
                insight=workflow_insight,
                efficiency_score=0.8 if modified_files else 0.3,
                improvement_suggestions=improvement_suggestions
            )
            
            # 3. 存储学习经验
            if modified_files:
                lesson = f"成功实现Issue，关键文件: {modified_files[0] if modified_files else '无'}"
                self.memory_manager.store_learning_experience(
                    lesson=lesson,
                    context=issue.get('description', ''),
                    success=True,
                    improvement="继续优化代码质量和架构设计"
                )
            
            # 4. 存储创意想法（如果有）
            if isinstance(result, dict) and result.get("operation") == "enhance":
                self.memory_manager.store_creative_idea(
                    idea=f"增强了现有功能: {issue.get('title', '')}",
                    category="feature_enhancement",
                    potential_impact="提升用户体验和系统功能",
                    implementation_notes=f"修改了 {len(modified_files)} 个文件"
                )
            
            # 5. 存储TODO项目（如果需要后续工作）
            if len(modified_files) > 2:
                self.memory_manager.store_todo_item(
                    task=f"测试和验证 {issue.get('title', '')} 的实现",
                    priority="high",
                    status="pending"
                )
            
        except Exception as e:
            logger.warning(f"智能记忆存储失败: {e}")

    async def run_llm_task(self, task_type: str, context: dict[str, Any]) -> tuple[Any, list[dict]]:
        """通过prompt驱动LLM完成任务，返回结果和AI思考链"""
        prompt = self._get_prompt(task_type, context)
        llm_response = await self.llm_manager.execute_task(task_type, context, custom_prompt=prompt)
        if isinstance(llm_response, dict) and "result" in llm_response and "thoughts" in llm_response:
            return llm_response["result"], llm_response["thoughts"]
        return llm_response, []

    async def apply_result(self, result: Any, context: dict[str, Any]) -> list[str]:
        """应用LLM返回的结果到文件系统
        
        Args:
            result: LLM返回的结果
            context: 上下文信息
            
        Returns:
            修改的文件列表
        """
        modified_files = []
        
        if isinstance(result, dict) and "file_path" in result and "code" in result:
            file_path = result["file_path"]
            full_path = os.path.join(self.user_project_path, file_path)
            
            # 检查是否需要修改现有文件
            is_existing_file = os.path.exists(full_path)
            
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
                f.write(result["code"])
            
            action = "修改" if is_existing_file else "创建"
            logger.info(f"📝 {action}文件: {file_path}")
            
            # 记录文件变更到memory
            if hasattr(self, 'memory_manager'):
                self.memory_manager.store_memory(
                    MemoryType.FILE_ANALYSIS,
                    {
                        "action": action,
                        "file_path": file_path,
                        "original_content_length": len(original_content),
                        "new_content_length": len(result["code"]),
                        "has_changes": original_content != result["code"]
                    },
                    keywords=[file_path.split('/')[-1], action],
                    tags=["file_operation"]
                )
            
            await self.git_manager.commit_changes(
                f"{action}: {context['issue'].get('title', '')}", 
                [file_path]
            )
            modified_files.append(file_path)
            
        elif isinstance(result, list):
            for file_result in result:
                if isinstance(file_result, dict) and "file_path" in file_result and "code" in file_result:
                    file_path = file_result["file_path"]
                    full_path = os.path.join(self.user_project_path, file_path)
                    
                    # 检查是否需要修改现有文件
                    is_existing_file = os.path.exists(full_path)
                    
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
                        f.write(file_result["code"])
                    
                    action = "修改" if is_existing_file else "创建"
                    logger.info(f"📝 {action}文件: {file_path}")
                    
                    # 记录文件变更到memory
                    if hasattr(self, 'memory_manager'):
                        self.memory_manager.store_memory(
                            MemoryType.FILE_ANALYSIS,
                            {
                                "action": action,
                                "file_path": file_path,
                                "original_content_length": len(original_content),
                                "new_content_length": len(file_result["code"]),
                                "has_changes": original_content != file_result["code"]
                            },
                            keywords=[file_path.split('/')[-1], action],
                            tags=["file_operation"]
                        )
                    
                    modified_files.append(file_path)
            
            if modified_files:
                await self.git_manager.commit_changes(
                    f"批量修改: {context['issue'].get('title', '')}", 
                    modified_files
                )
                
        elif isinstance(result, str):
            logger.info(f"LLM返回: {result[:200]}")
        else:
            logger.info(f"LLM返回未知类型: {type(result)}")
            
        return modified_files

    def _get_prompt(self, task_type: str, context: dict[str, Any]) -> str:
        """返回不同任务类型的prompt模板"""
        issue = context.get("issue", {})
        recent_thoughts = context.get("recent_thoughts", [])
        return f"""
你是一个多能的AI编码员。请根据以下Issue和历史思考链，独立完成所有开发任务。

【Issue】:
标题: {issue.get('title', '')}
描述: {issue.get('description', '')}

【历史思考链】:
{recent_thoughts}

【重要指导】:
1. 优先修改现有文件而不是创建新文件，除非确实需要新文件
2. 如果修改现有文件，请保持原有的代码结构和风格
3. 在修改前先分析现有代码的逻辑和结构
4. 确保修改后的代码与现有代码兼容
5. 如果创建新文件，请考虑是否应该放在合适的目录结构中

请严格按如下JSON格式输出：
{{
  "thoughts": [
    {{"thought": "你每一步的思考内容", "context": {{...}}, "conclusion": "本步结论", "confidence": 0.9}},
    ...
  ],
  "result": {{
    "file_path": "要写入的文件路径（相对项目根目录）",
    "code": "完整代码内容",
    "operation": "create|modify|enhance"
  }}
}}

如果需要修改多个文件，可以返回数组形式：
{{
  "thoughts": [...],
  "result": [
    {{"file_path": "file1.py", "code": "...", "operation": "modify"}},
    {{"file_path": "file2.py", "code": "...", "operation": "create"}}
  ]
}}

operation字段说明：
- create: 创建新文件
- modify: 修改现有文件
- enhance: 增强现有文件功能
"""

    def set_playground_git_manager(self, playground_git_manager):
        """设置playground仓库管理器"""
        self.playground_git_manager = playground_git_manager
        logger.info(f"{self.agent_id} 设置playground仓库管理器")

    def set_collaboration_manager(self, collaboration_manager):
        """设置协作管理器"""
        self.collaboration_manager = collaboration_manager
        logger.info(f"{self.agent_id} 设置协作管理器")

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
                        import json
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
                                logger.info(f"✅ {self.agent_id} 完成新Issue: {target_issue.get('title')}")
                            else:
                                logger.error(f"❌ {self.agent_id} 处理新Issue失败: {target_issue.get('title')}")
                            
                        else:
                            logger.debug(f"📭 {self.agent_id} 没有找到可用Issues，等待中...")
                    else:
                        logger.warning(f"⚠️ {self.agent_id} Issues文件不存在: {issues_file}")
                else:
                    logger.warning(f"⚠️ {self.agent_id} 未设置playground_git_manager")
                            
                await asyncio.sleep(10)  # 等待10秒后再检查
                
            except Exception as e:
                logger.error(f"❌ {self.agent_id} 运行出错: {e}")
                import traceback
                logger.error(f"🔍 错误详情:\n{traceback.format_exc()}")
                await asyncio.sleep(30)  # 出错后等待更长时间
     