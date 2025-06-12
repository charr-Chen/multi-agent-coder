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
            self.repo.index.add([".issues.json"])  # 使用相对路径
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
            [".issues.json"]  # 使用相对路径
        )
        
        logger.info(f"创建 Issue: {title}")
        return issue
    
    async def get_open_issues(self) -> List[Dict[str, Any]]:
        """获取所有开放的 Issue（包括open和assigned状态）
        
        Returns:
            Issue 列表
        """
        data = self._load_issues()
        return [issue for issue in data["issues"] if issue["status"] in ["open", "assigned"]]
    
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
                issue["status"] = "assigned"
                self._save_issues(data)
                
                # 提交更改
                await self.commit_changes(
                    f"分配 Issue {issue_id} 给 {assignee}",
                    [".issues.json"]  # 使用相对路径
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
                    [".issues.json"]  # 使用相对路径
                )
                
                logger.info(f"更新 Issue {issue_id} 状态为 {status}")
                return True
        return False
    
    async def commit_changes(self, message: str, files: List[str]) -> str:
        """提交代码更改
        
        Args:
            message: 提交信息
            files: 要提交的文件列表
            
        Returns:
            提交的hash值，失败时返回空字符串
        """
        try:
            self.repo.index.add(files)
            commit = self.repo.index.commit(message)
            logger.info(f"提交更改: {message}")
            return commit.hexsha
        except GitCommandError as e:
            logger.error(f"提交失败: {e}")
            return ""
    
    async def push_changes(self) -> bool:
        """推送代码到远程仓库
        
        Returns:
            是否推送成功
        """
        try:
            # 检查是否有远程仓库
            if not self.repo.remotes:
                logger.debug("没有配置远程仓库，跳过推送操作")
                return True
            
            # 检查是否有origin远程仓库
            if 'origin' not in [remote.name for remote in self.repo.remotes]:
                logger.debug("没有配置origin远程仓库，跳过推送操作")
                return True
            
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
            # 检查是否有远程仓库
            if not self.repo.remotes:
                logger.debug("没有配置远程仓库，跳过拉取操作")
                return True
            
            # 检查是否有origin远程仓库
            if 'origin' not in [remote.name for remote in self.repo.remotes]:
                logger.debug("没有配置origin远程仓库，跳过拉取操作")
                return True
            
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
    
    async def create_branch(self, branch_name: str) -> bool:
        """创建并切换到新分支
        
        Args:
            branch_name: 分支名称
            
        Returns:
            是否创建成功
        """
        try:
            # 检查分支是否已存在
            if branch_name in [branch.name for branch in self.repo.branches]:
                logger.info(f"分支 {branch_name} 已存在，切换到该分支")
                await self.checkout_branch(branch_name)
                return True
            
            # 创建新分支
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()
            logger.info(f"创建并切换到分支: {branch_name}")
            return True
        except Exception as e:
            logger.error(f"创建分支失败: {e}")
            return False
    
    async def checkout_branch(self, branch_name: str) -> bool:
        """切换到指定分支
        
        Args:
            branch_name: 分支名称
            
        Returns:
            是否切换成功
        """
        try:
            # 检查分支是否存在
            if branch_name not in [branch.name for branch in self.repo.branches]:
                logger.error(f"分支 {branch_name} 不存在")
                return False
            
            # 切换分支
            self.repo.heads[branch_name].checkout()
            logger.info(f"切换到分支: {branch_name}")
            return True
        except Exception as e:
            logger.error(f"切换分支失败: {e}")
            return False
    
    async def delete_branch(self, branch_name: str) -> bool:
        """删除分支
        
        Args:
            branch_name: 分支名称
            
        Returns:
            是否删除成功
        """
        try:
            # 检查分支是否存在
            if branch_name not in [branch.name for branch in self.repo.branches]:
                logger.debug(f"分支 {branch_name} 不存在，无需删除")
                return True
            
            # 不能删除当前分支
            if self.repo.active_branch.name == branch_name:
                logger.warning(f"不能删除当前分支: {branch_name}")
                return False
            
            # 删除分支
            self.repo.delete_head(branch_name, force=True)
            logger.info(f"删除分支: {branch_name}")
            return True
        except Exception as e:
            logger.error(f"删除分支失败: {e}")
            return False
    
    async def get_current_branch(self) -> str:
        """获取当前分支名称
        
        Returns:
            当前分支名称
        """
        try:
            return self.repo.active_branch.name
        except Exception as e:
            logger.error(f"获取当前分支失败: {e}")
            return "main"
    
    async def list_branches(self) -> List[str]:
        """列出所有分支
        
        Returns:
            分支名称列表
        """
        try:
            return [branch.name for branch in self.repo.branches]
        except Exception as e:
            logger.error(f"列出分支失败: {e}")
            return []
    
    async def merge_branch(self, branch_name: str, message: str = None) -> bool:
        """合并分支到当前分支
        
        Args:
            branch_name: 要合并的分支名称
            message: 合并提交信息
            
        Returns:
            是否合并成功
        """
        try:
            # 检查分支是否存在
            if branch_name not in [branch.name for branch in self.repo.branches]:
                logger.error(f"分支 {branch_name} 不存在")
                return False
            
            # 获取要合并的分支
            branch_to_merge = self.repo.heads[branch_name]
            
            # 执行合并
            if message is None:
                message = f"Merge branch '{branch_name}'"
            
            self.repo.git.merge(branch_to_merge, m=message)
            logger.info(f"合并分支 {branch_name} 到 {self.repo.active_branch.name}")
            return True
        except Exception as e:
            logger.error(f"合并分支失败: {e}")
            return False 