"""
编码员代理模块
负责获取任务、实现代码和处理 Git 操作。
"""

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
            git_manager: Git 仓库管理器
            llm_manager: LLM 管理器
            agent_id: 代理 ID
        """
        self.git_manager = git_manager
        self.llm_manager = llm_manager
        self.agent_id = agent_id
        self.config = AGENT_CONFIG["coder"]
        self.current_issue = None
        logger.info(f"初始化编码员代理: {agent_id}")
    
    async def grab_issue(self) -> Optional[Dict[str, Any]]:
        """获取一个未分配的 Issue
        
        Returns:
            Issue 信息字典，如果没有可用的 Issue 则返回 None
        """
        issues = await self.git_manager.get_open_issues()
        
        for issue in issues:
            if not issue.get("assigned_to"):
                # 尝试分配 Issue
                if await self.git_manager.assign_issue(issue["id"], self.agent_id):
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
            # 生成代码
            code = await self.llm_manager.generate_code(issue)
            if not code:
                logger.error(f"生成代码失败: {issue['id']}")
                return False
            
            # 创建或更新文件
            file_path = f"src/{issue['id']}.py"
            with open(file_path, "w") as f:
                f.write(code)
            
            # 提交代码
            if await self.git_manager.commit_changes(
                f"实现 Issue {issue['id']}: {issue['title']}",
                [file_path]
            ):
                # 推送代码
                if await self.git_manager.push_changes():
                    # 更新 Issue 状态
                    await self.git_manager.update_issue_status(
                        issue["id"],
                        "review",
                        code
                    )
                    logger.info(f"完成 Issue {issue['id']} 的实现")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"实现 Issue 时出错: {e}")
            return False
    
    async def handle_conflicts(self) -> bool:
        """处理代码冲突
        
        Returns:
            是否解决成功
        """
        try:
            # 拉取最新代码
            await self.git_manager.pull_changes()
            
            # 解决冲突
            if await self.git_manager.resolve_conflicts():
                # 提交解决后的代码
                if await self.git_manager.commit_changes(
                    "解决代码冲突",
                    ["src/*.py"]
                ):
                    # 推送代码
                    if await self.git_manager.push_changes():
                        logger.info("成功解决代码冲突")
                        return True
            
            return False
        except Exception as e:
            logger.error(f"处理代码冲突时出错: {e}")
            return False
    
    async def work_on_issues(self) -> None:
        """处理 Issue
        
        持续获取和处理 Issue。
        """
        while True:
            try:
                if not self.current_issue:
                    # 尝试获取新的 Issue
                    issue = await self.grab_issue()
                    if issue:
                        self.current_issue = issue
                
                if self.current_issue:
                    # 实现 Issue
                    if await self.implement_issue(self.current_issue):
                        self.current_issue = None
                    else:
                        # 处理可能的冲突
                        await self.handle_conflicts()
                
                await asyncio.sleep(10)  # 每10秒检查一次
            except Exception as e:
                logger.error(f"处理 Issue 时出错: {e}")
                await asyncio.sleep(10)
    
    async def run(self) -> None:
        """运行编码员代理
        
        启动 Issue 处理任务。
        """
        logger.info(f"启动编码员代理: {self.agent_id}")
        
        try:
            await self.work_on_issues()
        except Exception as e:
            logger.error(f"编码员代理运行出错: {e}") 