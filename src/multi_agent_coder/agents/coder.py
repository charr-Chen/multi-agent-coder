"""
编码员代理模块
负责获取任务、实现代码和处理 Git 操作。
"""

import os
import logging
import asyncio
from typing import List, Dict, Any, Optional
from ..git_utils import GitManager
from ..llm_utils import LLMManager
from ..config import AGENT_CONFIG

logger = logging.getLogger(__name__)

class CoderAgent:
    """编码员代理类"""
    
    def __init__(self, git_manager: GitManager, llm_manager: LLMManager, agent_id: str):
        """初始化编码员代理
        
        Args:
            git_manager: Git 仓库管理器 (agent自己的仓库)
            llm_manager: LLM 管理器
            agent_id: 代理 ID
        """
        self.git_manager = git_manager  # agent自己的仓库
        self.llm_manager = llm_manager
        self.agent_id = agent_id
        self.config = AGENT_CONFIG["coder"]
        self.current_issue = None
        self.playground_git_manager = None  # playground仓库管理器，用于访问Issues
        self.collaboration_manager = None  # 协作管理器
        logger.info(f"初始化编码员代理: {agent_id}")
    
    def set_playground_git_manager(self, playground_git_manager: GitManager):
        """设置playground仓库管理器
        
        Args:
            playground_git_manager: playground仓库的Git管理器
        """
        self.playground_git_manager = playground_git_manager
        logger.info(f"{self.agent_id} 设置playground仓库管理器")
    
    def set_collaboration_manager(self, collaboration_manager):
        """设置协作管理器
        
        Args:
            collaboration_manager: 协作管理器实例
        """
        self.collaboration_manager = collaboration_manager
        logger.info(f"{self.agent_id} 设置协作管理器")
    
    def get_issues_git_manager(self) -> GitManager:
        """获取用于访问Issues的Git管理器
        
        Returns:
            用于访问Issues的Git管理器
        """
        # 如果有playground管理器，使用它来访问Issues
        if self.playground_git_manager:
            return self.playground_git_manager
        # 否则使用自己的管理器（单仓库模式）
        return self.git_manager
    
    async def grab_issue(self) -> Optional[Dict[str, Any]]:
        """获取一个未分配的 Issue
        
        Returns:
            Issue 信息字典，如果没有可用的 Issue 则返回 None
        """
        issues = await self.get_issues_git_manager().get_open_issues()
        
        for issue in issues:
            if not issue.get("assigned_to"):
                # 尝试分配 Issue
                if await self.get_issues_git_manager().assign_issue(issue["id"], self.agent_id):
                    self.current_issue = issue
                    logger.info(f"获取 Issue: {issue['id']}")
                    return issue
        
        return None
    
    async def implement_issue(self, issue: Dict[str, Any]) -> bool:
        """实现 Issue 的代码
        
        Args:
            issue: Issue 信息字典
            
        Returns:
            是否实现成功
        """
        try:
            logger.info(f"🔧 {self.agent_id} 开始实现Issue: {issue.get('title', 'Unknown')}")
            logger.info(f"📋 Issue详情: {issue.get('description', 'No description')}")
            
            # 生成代码
            logger.info(f"🤖 {self.agent_id} 正在生成代码...")
            code = await self.llm_manager.generate_code(issue)
            if not code:
                logger.error(f"❌ {self.agent_id} 生成代码失败: {issue['id']}")
                return False
            
            logger.info(f"✅ {self.agent_id} 代码生成成功，长度: {len(code)} 字符")
            logger.info(f"📝 生成的代码预览:\n{'-'*50}")
            # 显示代码的前10行
            code_lines = code.split('\n')
            preview_lines = code_lines[:10]
            for i, line in enumerate(preview_lines, 1):
                logger.info(f"{i:2d}: {line}")
            if len(code_lines) > 10:
                logger.info(f"... (还有 {len(code_lines) - 10} 行)")
            logger.info(f"{'-'*50}")
            
            # 生成智能文件名
            try:
                smart_filename = await self.llm_manager.generate_filename(
                    issue['title'], 
                    issue['description'], 
                    code
                )
                file_path = f"src/{smart_filename}.py"
                logger.info(f"✅ {self.agent_id} 生成智能文件名: {file_path}")
            except Exception as e:
                logger.warning(f"⚠️ {self.agent_id} 智能文件名生成失败: {e}")
                # Fallback: 使用Issue ID
                file_path = f"src/{issue['id']}.py"
                logger.info(f"🔄 {self.agent_id} 使用fallback文件名: {file_path}")
            
            # 如果有协作管理器，使用Pull Request流程
            if self.collaboration_manager:
                logger.info(f"🔄 {self.agent_id} 使用Pull Request流程提交代码")
                
                # 创建Pull Request
                pr_title = f"实现 {issue['title']}"
                pr_description = f"实现Issue #{issue['id']}: {issue['description']}"
                code_changes = {file_path: code}
                
                pr_id = await self.collaboration_manager.create_pull_request(
                    issue_id=issue['id'],
                    author=self.agent_id,
                    title=pr_title,
                    description=pr_description,
                    code_changes=code_changes
                )
                
                logger.info(f"🎉 {self.agent_id} 创建Pull Request: {pr_id}")
                logger.info(f"⏳ 等待代码审核...")
                
                # 更新Issue状态为review
                issues_git_manager = self.get_issues_git_manager()
                await issues_git_manager.update_issue_status(
                    issue["id"],
                    "review",
                    f"Pull Request: {pr_id}"
                )
                
                return True
            else:
                # 传统流程：直接提交代码
                logger.info(f"📤 {self.agent_id} 使用传统流程直接提交代码")
                
                full_file_path = os.path.join(self.git_manager.repo_path, file_path)
                logger.info(f"📁 {self.agent_id} 准备写入文件: {full_file_path}")
                
                # 确保目录存在
                os.makedirs(os.path.dirname(full_file_path), exist_ok=True)
                logger.debug(f"📂 {self.agent_id} 目录已创建: {os.path.dirname(full_file_path)}")
                
                # 写入文件
                with open(full_file_path, "w", encoding='utf-8') as f:
                    f.write(code)
                logger.info(f"💾 {self.agent_id} 文件写入成功: {file_path}")
                
                # 提交代码到agent自己的仓库
                commit_message = f"实现 Issue {issue['id']}: {issue['title']}"
                logger.info(f"📤 {self.agent_id} 准备提交代码: {commit_message}")
                
                commit_hash = await self.git_manager.commit_changes(commit_message, [file_path])
                if commit_hash:
                    logger.info(f"✅ {self.agent_id} Git提交成功")
                    
                    # 如果使用多仓库模式，同步到playground
                    if hasattr(self, 'multi_repo_manager') and self.multi_repo_manager:
                        logger.info(f"🔄 {self.agent_id} 开始同步到playground...")
                        await self.multi_repo_manager.sync_agent_to_playground(self.agent_id)
                        logger.info(f"✅ {self.agent_id} 已同步工作到playground")
                    else:
                        # 单仓库模式，推送到远程
                        logger.info(f"📤 {self.agent_id} 推送到远程仓库...")
                        await self.git_manager.push_changes()
                        logger.info(f"✅ {self.agent_id} 推送成功")
                    
                    # 更新 Issue 状态 (总是在playground仓库中更新)
                    logger.info(f"📝 {self.agent_id} 更新Issue状态为review...")
                    issues_git_manager = self.get_issues_git_manager()
                    await issues_git_manager.update_issue_status(
                        issue["id"],
                        "review",
                        code
                    )
                    logger.info(f"🎉 {self.agent_id} 完成Issue {issue['id']} 的实现")
                    return True
                else:
                    logger.error(f"❌ {self.agent_id} Git提交失败")
                
                return False
        except Exception as e:
            logger.error(f"❌ {self.agent_id} 实现Issue时出错: {e}")
            import traceback
            logger.error(f"🔍 错误详情:\n{traceback.format_exc()}")
            return False
    
    async def handle_conflicts(self) -> bool:
        """处理代码冲突
        
        Returns:
            是否解决成功
        """
        try:
            # 检查是否有远程仓库，有的话才拉取最新代码
            try:
                if self.get_issues_git_manager().repo.remotes:
                    await self.get_issues_git_manager().pull_changes()
                else:
                    logger.debug("本地仓库模式，跳过拉取远程更改")
            except Exception as e:
                logger.debug(f"跳过拉取操作: {e}")
            
            # 解决冲突
            if await self.get_issues_git_manager().resolve_conflicts():
                # 提交解决后的代码
                commit_hash = await self.get_issues_git_manager().commit_changes(
                    "解决代码冲突",
                    ["src/*.py"]
                )
                if commit_hash:
                    # 推送代码（如果有远程仓库的话）
                    try:
                        if self.get_issues_git_manager().repo.remotes:
                            await self.get_issues_git_manager().push_changes()
                        else:
                            logger.debug("本地仓库模式，跳过推送到远程")
                    except Exception as e:
                        logger.debug(f"跳过推送操作: {e}")
                    
                    logger.info("成功解决代码冲突")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"处理代码冲突时出错: {e}")
            return False
    
    async def work_on_issues(self) -> None:
        """处理 Issue
        
        持续检查并处理分配给自己的 Issue。
        """
        logger.info(f"🔨 {self.agent_id} 开始处理Issues...")
        while True:
            try:
                logger.debug(f"📋 {self.agent_id} 检查分配的Issues...")
                # 获取分配给自己的 Issue
                issues = await self.get_issues_git_manager().get_open_issues()
                assigned_issues = [
                    issue for issue in issues
                    if issue.get("assigned_to") == self.agent_id and issue.get("status") == "assigned"
                ]
                
                if assigned_issues:
                    logger.info(f"📝 {self.agent_id} 发现 {len(assigned_issues)} 个分配的Issues")
                    
                    for issue in assigned_issues:
                        logger.info(f"🚀 {self.agent_id} 开始处理Issue: {issue.get('title', 'Unknown')}")
                        await self.implement_issue(issue)
                else:
                    logger.debug(f"📭 {self.agent_id} 没有分配的Issues")
                
                logger.debug(f"😴 {self.agent_id} 工作休眠30秒...")
                await asyncio.sleep(30)  # 每30秒检查一次
            except Exception as e:
                logger.error(f"❌ {self.agent_id} 处理 Issue 时出错: {e}")
                await asyncio.sleep(30)
    
    async def grab_issues(self) -> None:
        """抢夺 Issue
        
        持续检查开放的 Issue，并尝试分配给自己。
        """
        logger.info(f"🎯 {self.agent_id} 开始抢夺Issues...")
        while True:
            try:
                logger.debug(f"🔍 {self.agent_id} 寻找可抢夺的Issues...")
                # 获取开放的 Issue
                issues = await self.get_issues_git_manager().get_open_issues()
                open_issues = [
                    issue for issue in issues
                    if issue.get("status") == "open" and not issue.get("assigned_to")
                ]
                
                if open_issues:
                    logger.info(f"🎯 {self.agent_id} 发现 {len(open_issues)} 个可抢夺的Issues")
                    
                    for issue in open_issues:
                        logger.info(f"🏃 {self.agent_id} 尝试抢夺Issue: {issue.get('title', 'Unknown')}")
                        # 尝试分配 Issue 给自己
                        success = await self.get_issues_git_manager().assign_issue(issue["id"], self.agent_id)
                        if success:
                            logger.info(f"✅ {self.agent_id} 成功抢夺Issue: {issue['id']}")
                            break  # 一次只抢一个
                        else:
                            logger.debug(f"❌ {self.agent_id} 抢夺失败，Issue可能已被其他代理抢夺")
                    else:
                        logger.debug(f"�� {self.agent_id} 没有发现可抢夺的Issues")
                
                logger.debug(f"😴 {self.agent_id} 抢夺休眠20秒...")
                await asyncio.sleep(20)  # 每20秒检查一次
            except Exception as e:
                logger.error(f"❌ {self.agent_id} 抢夺 Issue 时出错: {e}")
                await asyncio.sleep(20)
    
    async def run(self) -> None:
        """运行编码员代理
        
        启动所有工作任务。
        """
        logger.info(f"🚀 启动编码员代理: {self.agent_id}")
        
        # 创建工作任务
        logger.info(f"🎯 {self.agent_id} 创建抢夺任务...")
        grab_task = asyncio.create_task(self.grab_issues())
        logger.info(f"🔨 {self.agent_id} 创建工作任务...")
        work_task = asyncio.create_task(self.work_on_issues())
        
        try:
            logger.info(f"⚡ {self.agent_id} 开始工作...")
            # 等待任务完成
            await asyncio.gather(grab_task, work_task)
        except Exception as e:
            logger.error(f"❌ {self.agent_id} 运行出错: {e}")
            # 取消所有任务
            grab_task.cancel()
            work_task.cancel() 