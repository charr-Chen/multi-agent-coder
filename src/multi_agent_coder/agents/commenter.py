"""
评论员代理模块
负责创建任务、审查代码提交和管理 Issue。
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from ..git_utils import GitManager
from ..llm_utils import LLMManager
from ..config import AGENT_CONFIG

logger = logging.getLogger(__name__)

class CommenterAgent:
    """评论员代理类"""
    
    def __init__(self, git_manager: GitManager, llm_manager: LLMManager):
        """初始化评论员代理
        
        Args:
            git_manager: Git 仓库管理器
            llm_manager: LLM 管理器
        """
        self.git_manager = git_manager
        self.llm_manager = llm_manager
        self.config = AGENT_CONFIG["commenter"]
        logger.info("初始化评论员代理")
    
    async def create_issue(self, title: str, description: str) -> Dict[str, Any]:
        """创建新的 Issue
        
        Args:
            title: Issue 标题
            description: Issue 描述
            
        Returns:
            Issue 信息字典
        """
        issue = await self.git_manager.create_issue(title, description)
        logger.info(f"创建 Issue: {title}")
        return issue
    
    async def analyze_requirements(self, requirements: str) -> None:
        """分析用户需求，创建 Issue
        
        Args:
            requirements: 用户需求描述
        """
        issues = await self.llm_manager.analyze_requirements(requirements)
        for issue in issues:
            await self.create_issue(issue["title"], issue["description"])
    
    async def review_code(self, issue_id: str, code_changes: Dict[str, Any]) -> bool:
        """审查代码提交
        
        Args:
            issue_id: Issue ID
            code_changes: 代码更改信息
            
        Returns:
            是否通过审查
        """
        # 获取 Issue 信息
        issues = await self.git_manager.get_open_issues()
        issue = next((i for i in issues if i["id"] == issue_id), None)
        if not issue:
            logger.error(f"未找到 Issue: {issue_id}")
            return False
        
        # 审查代码
        review_result = await self.llm_manager.review_code(issue, code_changes["code"])
        
        if review_result["approved"]:
            # 更新 Issue 状态
            await self.git_manager.update_issue_status(
                issue_id,
                "completed",
                code_changes["code"]
            )
            logger.info(f"Issue {issue_id} 通过审查")
        else:
            # 更新 Issue 状态
            await self.git_manager.update_issue_status(
                issue_id,
                "open",
                code_changes["code"]
            )
            logger.info(f"Issue {issue_id} 未通过审查: {review_result['comments']}")
        
        return review_result["approved"]
    
    async def monitor_repo(self) -> None:
        """监控代码库状态
        
        持续监控代码库，检查是否需要创建新的 Issue。
        """
        while True:
            try:
                # 拉取最新代码
                await self.git_manager.pull_changes()
                
                # 分析代码库状态
                # TODO: 实现代码库状态分析
                
                await asyncio.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"监控代码库时出错: {e}")
                await asyncio.sleep(60)
    
    async def review_issues(self) -> None:
        """审查 Issue
        
        持续审查开放的 Issue，检查代码提交。
        """
        while True:
            try:
                # 获取开放的 Issue
                issues = await self.git_manager.get_open_issues()
                
                for issue in issues:
                    if issue.get("code_submission"):
                        # 审查代码提交
                        await self.review_code(
                            issue["id"],
                            {"code": issue["code_submission"]}
                        )
                
                await asyncio.sleep(30)  # 每30秒检查一次
            except Exception as e:
                logger.error(f"审查 Issue 时出错: {e}")
                await asyncio.sleep(30)
    
    async def run(self) -> None:
        """运行评论员代理
        
        启动所有监控和审查任务。
        """
        logger.info("启动评论员代理")
        
        # 创建监控和审查任务
        monitor_task = asyncio.create_task(self.monitor_repo())
        review_task = asyncio.create_task(self.review_issues())
        
        try:
            # 等待任务完成
            await asyncio.gather(monitor_task, review_task)
        except Exception as e:
            logger.error(f"评论员代理运行出错: {e}")
            # 取消所有任务
            monitor_task.cancel()
            review_task.cancel() 