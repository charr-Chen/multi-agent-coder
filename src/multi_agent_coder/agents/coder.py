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
        """主入口：处理一个issue"""
        logger.info(f"🚀 {self.agent_id} 开始处理Issue: {issue.get('title')}")
        
        try:
            # 1. 收集上下文
            context = await self.build_context(issue)
            
            # 2. 让AI决定怎么做（prompt驱动）
            result, thoughts = await self.run_llm_task("implement_issue", context)
            
            # 3. 检查LLM响应是否有效
            if not result:
                logger.error(f"❌ {self.agent_id} LLM返回空结果")
                return False
            
            # 4. 检查是否是错误响应或fallback响应
            if isinstance(result, dict):
                if "error" in result:
                    logger.error(f"❌ {self.agent_id} LLM返回错误: {result['error']}")
                    return False
                # 检查是否是fallback响应（包含"fallback_"前缀的文件名）
                if isinstance(result.get("file_path"), str) and result["file_path"].startswith("fallback_"):
                    logger.warning(f"⚠️ {self.agent_id} 收到fallback响应，LLM调用可能失败")
                    # 仍然创建fallback文件，让用户知道出了问题
            
            # 5. 应用结果（如写文件、提交等）
            modified_files = await self.apply_result(result, context)
            
            # 6. 🆕 只有真正创建了文件才算成功
            if not modified_files:
                logger.error(f"❌ {self.agent_id} 没有生成任何文件")
                return False
            
            logger.info(f"✅ {self.agent_id} 成功创建/修改了 {len(modified_files)} 个文件: {', '.join(modified_files)}")
            
            # 7. 🆕 如果有文件修改，创建PR
            if modified_files and self.collaboration_manager:
                pr_id = await self.create_pull_request_for_changes(
                    issue=issue,
                    modified_files=modified_files,
                    context=context
                )
                if pr_id:
                    logger.info(f"🎉 {self.agent_id} 成功创建PR: {pr_id}")
                else:
                    logger.warning(f"⚠️ {self.agent_id} PR创建失败")
            
            # 8. 存储AI思考链到Memory
            for thought in thoughts:
                self.memory_manager.store_thinking_process(
                    thought.get("thought", ""),
                    context=thought.get("context", {}),
                    conclusion=thought.get("conclusion", None),
                    confidence=thought.get("confidence", None)
                )
            
            # 9. 🆕 存储完成的Issue信息到Memory
            self.memory_manager.store_memory(
                memory_type=MemoryType.DECISION_LOG,
                content={
                    "action": "完成Issue",
                    "issue_title": issue.get('title', ''),
                    "issue_description": issue.get('description', ''),
                    "modified_files": modified_files,
                    "success": True,
                    "notes": f"成功实现Issue，创建了{len(modified_files)}个文件"
                },
                keywords=["issue", "完成", "实现"],
                priority=MemoryPriority.HIGH
            )
            
            # 10. 🆕 生成用户报告
            await self.generate_user_report(issue, modified_files, thoughts)
            
            logger.info(f"✅ {self.agent_id} 完成Issue: {issue.get('title')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ {self.agent_id} 处理Issue失败: {e}")
            import traceback
            logger.error(f"🔍 错误详情:\n{traceback.format_exc()}")
            
            # 🆕 存储失败信息到Memory
            try:
                self.memory_manager.store_memory(
                    memory_type=MemoryType.ERROR_PATTERN,
                    content={
                        "action": "处理Issue失败",
                        "issue_title": issue.get('title', ''),
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                        "success": False
                    },
                    keywords=["issue", "失败", "错误"],
                    priority=MemoryPriority.HIGH
                )
            except:
                logger.error("存储错误信息到Memory也失败了")
            
            return False

    async def build_context(self, issue: dict[str, Any]) -> dict[str, Any]:
        """收集上下文（相关memory、相关文件内容等）"""
        # 只取最近的思考过程
        recent_thoughts = self.memory_manager.get_recent_thinking_processes(limit=5)
        return {
            "issue": issue,
            "recent_thoughts": [t.content for t in recent_thoughts],
        }

    async def run_llm_task(self, task_type: str, context: dict[str, Any]) -> tuple[Any, list[dict]]:
        """通过prompt驱动LLM完成任务，返回结果和AI思考链"""
        prompt = self._get_prompt(task_type, context)
        llm_response = await self.llm_manager.execute_task(task_type, context, custom_prompt=prompt)
        if isinstance(llm_response, dict) and "result" in llm_response and "thoughts" in llm_response:
            return llm_response["result"], llm_response["thoughts"]
        return llm_response, []

    async def apply_result(self, result: Any, context: dict[str, Any]) -> list[str]:
        """应用LLM结果，如写文件、提交等，返回修改的文件列表"""
        modified_files = []
        
        if isinstance(result, dict) and "file_path" in result and "code" in result:
            file_path = result["file_path"]
            full_path = os.path.join(self.user_project_path, file_path)
            
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(result["code"])
            logger.info(f"📝 写入文件: {file_path}")
            
            await self.git_manager.commit_changes(
                f"实现: {context['issue'].get('title', '')}", 
                [file_path]
            )
            modified_files.append(file_path)
            
        elif isinstance(result, list):
            for file_result in result:
                if isinstance(file_result, dict) and "file_path" in file_result and "code" in file_result:
                    file_path = file_result["file_path"]
                    full_path = os.path.join(self.user_project_path, file_path)
                    
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(file_result["code"])
                    logger.info(f"📝 写入文件: {file_path}")
                    modified_files.append(file_path)
            
            if modified_files:
                await self.git_manager.commit_changes(
                    f"实现: {context['issue'].get('title', '')}", 
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

请严格按如下JSON格式输出：
{{
  "thoughts": [
    {{"thought": "你每一步的思考内容", "context": {{...}}, "conclusion": "本步结论", "confidence": 0.9}},
    ...
  ],
  "result": {{
    "file_path": "要写入的文件路径（相对项目根目录）",
    "code": "完整代码内容"
  }}
}}

如果需要修改多个文件，可以返回数组形式：
{{
  "thoughts": [...],
  "result": [
    {{"file_path": "file1.py", "code": "..."}},
    {{"file_path": "file2.py", "code": "..."}}
  ]
}}
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
     