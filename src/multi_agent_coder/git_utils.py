"""Git 操作工具模块

提供 Git 仓库操作、Issue 管理和冲突解决等功能。
"""

import os
import json
import uuid
import logging
from typing import List, Optional, Dict, Any
from git import Repo, GitCommandError
from git.exc import GitCommandError
from datetime import datetime

logger = logging.getLogger(__name__)

class GitManager:
    """Git 仓库管理器"""
    
    def __init__(self, repo_path: str):
        """初始化 Git 管理器
        
        Args:
            repo_path: Git 仓库路径
        """
        self.repo_path = repo_path
        self.repo = Repo(repo_path)
        self.issues_file = os.path.join(repo_path, ".issues.json")
        self._init_issues_file()
        logger.info(f"初始化 Git 仓库: {repo_path}")
    
    def _init_issues_file(self) -> None:
        """初始化 Issue 文件"""
        if not os.path.exists(self.issues_file):
            with open(self.issues_file, "w") as f:
                json.dump({"issues": []}, f)
            # 将 issues 文件添加到 Git
            self.repo.index.add([self.issues_file])
            self.repo.index.commit("初始化 Issue 跟踪系统")
    
    def _load_issues(self) -> Dict[str, List[Dict[str, Any]]]:
        """加载 Issue 数据"""
        try:
            with open(self.issues_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载 Issue 数据失败: {e}")
            return {"issues": []}
    
    def _save_issues(self, data: Dict[str, List[Dict[str, Any]]]) -> None:
        """保存 Issue 数据"""
        try:
            with open(self.issues_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"保存 Issue 数据失败: {e}")
    
    async def create_issue(self, title: str, description: str) -> Dict[str, Any]:
        """创建新的 Issue
        
        Args:
            title: Issue 标题
            description: Issue 描述
            
        Returns:
            Issue 信息字典
        """
        data = self._load_issues()
        issue = {
            "id": str(uuid.uuid4()),
            "title": title,
            "description": description,
            "status": "open",
            "assigned_to": None,
            "code_submission": None,
            "created_at": str(datetime.now())
        }
        data["issues"].append(issue)
        self._save_issues(data)
        
        # 提交更改
        await self.commit_changes(
            f"创建 Issue: {title}",
            [self.issues_file]
        )
        
        logger.info(f"创建 Issue: {title}")
        return issue
    
    async def get_open_issues(self) -> List[Dict[str, Any]]:
        """获取所有开放的 Issue
        
        Returns:
            Issue 列表
        """
        data = self._load_issues()
        return [issue for issue in data["issues"] if issue["status"] == "open"]
    
    async def assign_issue(self, issue_id: str, assignee: str) -> bool:
        """分配 Issue 给指定代理
        
        Args:
            issue_id: Issue ID
            assignee: 被分配的代理
            
        Returns:
            是否分配成功
        """
        data = self._load_issues()
        for issue in data["issues"]:
            if issue["id"] == issue_id and issue["status"] == "open":
                issue["assigned_to"] = assignee
                self._save_issues(data)
                
                # 提交更改
                await self.commit_changes(
                    f"分配 Issue {issue_id} 给 {assignee}",
                    [self.issues_file]
                )
                
                logger.info(f"分配 Issue {issue_id} 给 {assignee}")
                return True
        return False
    
    async def update_issue_status(self, issue_id: str, status: str, code_submission: Optional[str] = None) -> bool:
        """更新 Issue 状态
        
        Args:
            issue_id: Issue ID
            status: 新状态
            code_submission: 代码提交内容
            
        Returns:
            是否更新成功
        """
        data = self._load_issues()
        for issue in data["issues"]:
            if issue["id"] == issue_id:
                issue["status"] = status
                if code_submission:
                    issue["code_submission"] = code_submission
                self._save_issues(data)
                
                # 提交更改
                await self.commit_changes(
                    f"更新 Issue {issue_id} 状态为 {status}",
                    [self.issues_file]
                )
                
                logger.info(f"更新 Issue {issue_id} 状态为 {status}")
                return True
        return False
    
    async def commit_changes(self, message: str, files: List[str]) -> bool:
        """提交代码更改
        
        Args:
            message: 提交信息
            files: 要提交的文件列表
            
        Returns:
            是否提交成功
        """
        try:
            self.repo.index.add(files)
            self.repo.index.commit(message)
            logger.info(f"提交更改: {message}")
            return True
        except GitCommandError as e:
            logger.error(f"提交失败: {e}")
            return False
    
    async def push_changes(self) -> bool:
        """推送代码到远程仓库
        
        Returns:
            是否推送成功
        """
        try:
            self.repo.remotes.origin.push()
            logger.info("推送更改到远程仓库")
            return True
        except GitCommandError as e:
            logger.error(f"推送失败: {e}")
            return False
    
    async def pull_changes(self) -> bool:
        """从远程仓库拉取代码
        
        Returns:
            是否拉取成功
        """
        try:
            self.repo.remotes.origin.pull()
            logger.info("从远程仓库拉取更改")
            return True
        except GitCommandError as e:
            logger.error(f"拉取失败: {e}")
            return False
    
    async def resolve_conflicts(self) -> bool:
        """解决代码冲突
        
        Returns:
            是否解决成功
        """
        try:
            # 获取当前分支
            current = self.repo.active_branch
            
            # 获取远程分支
            remote = self.repo.remotes.origin
            
            # 获取远程分支的最新提交
            remote.fetch()
            
            # 尝试合并
            try:
                self.repo.git.merge(remote.refs[current.name])
                logger.info("成功合并远程更改")
                return True
            except GitCommandError as e:
                if "CONFLICT" in str(e):
                    # 解决冲突
                    self.repo.git.merge("--abort")  # 取消合并
                    self.repo.git.reset("--hard", "HEAD")  # 重置到当前状态
                    self.repo.git.pull("--rebase")  # 使用 rebase 策略
                    logger.info("使用 rebase 解决冲突")
                    return True
                else:
                    raise
        except Exception as e:
            logger.error(f"解决冲突失败: {e}")
            return False 