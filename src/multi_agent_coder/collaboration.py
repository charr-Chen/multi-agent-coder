"""
协作管理器模块

实现类似GitHub的多智能体协作机制，包括：
1. Pull Request 机制
2. 代码审核流程
3. 主仓库协作
4. 代码同步
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from .git_utils import GitManager
from .llm_utils import LLMManager

logger = logging.getLogger(__name__)

class PullRequest:
    """Pull Request 类"""
    
    def __init__(self, pr_id: str, issue_id: str, author: str, title: str, 
                 description: str, code_changes: Dict[str, str], branch_name: str):
        self.pr_id = pr_id
        self.issue_id = issue_id
        self.author = author
        self.title = title
        self.description = description
        self.code_changes = code_changes  # {file_path: code_content}
        self.branch_name = branch_name
        self.status = "open"  # open, approved, rejected, merged
        self.created_at = datetime.now().isoformat()
        self.reviewed_at = None
        self.reviewer = None
        self.review_comments = []
        self.merge_commit = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "pr_id": self.pr_id,
            "issue_id": self.issue_id,
            "author": self.author,
            "title": self.title,
            "description": self.description,
            "code_changes": self.code_changes,
            "branch_name": self.branch_name,
            "status": self.status,
            "created_at": self.created_at,
            "reviewed_at": self.reviewed_at,
            "reviewer": self.reviewer,
            "review_comments": self.review_comments,
            "merge_commit": self.merge_commit
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PullRequest':
        """从字典创建"""
        pr = cls(
            data["pr_id"],
            data["issue_id"],
            data["author"],
            data["title"],
            data["description"],
            data["code_changes"],
            data["branch_name"]
        )
        pr.status = data.get("status", "open")
        pr.created_at = data.get("created_at", datetime.now().isoformat())
        pr.reviewed_at = data.get("reviewed_at")
        pr.reviewer = data.get("reviewer")
        pr.review_comments = data.get("review_comments", [])
        pr.merge_commit = data.get("merge_commit")
        return pr

class CollaborationManager:
    """协作管理器"""
    
    def __init__(self, main_repo_git_manager: GitManager, llm_manager: LLMManager):
        """初始化协作管理器
        
        Args:
            main_repo_git_manager: 主仓库的Git管理器
            llm_manager: LLM管理器
        """
        self.main_repo_git_manager = main_repo_git_manager
        self.llm_manager = llm_manager
        self.pr_file_path = os.path.join(main_repo_git_manager.repo_path, ".pull_requests.json")
        self.agent_repos: Dict[str, GitManager] = {}
        
        # 确保PR文件存在
        self._ensure_pr_file()
        logger.info("初始化协作管理器")
    
    def _ensure_pr_file(self):
        """确保PR文件存在"""
        if not os.path.exists(self.pr_file_path):
            with open(self.pr_file_path, "w", encoding="utf-8") as f:
                json.dump({"pull_requests": []}, f, indent=2, ensure_ascii=False)
            logger.info("创建Pull Request文件")
    
    def register_agent_repo(self, agent_id: str, git_manager: GitManager):
        """注册agent仓库
        
        Args:
            agent_id: agent ID
            git_manager: agent的Git管理器
        """
        self.agent_repos[agent_id] = git_manager
        logger.info(f"注册agent仓库: {agent_id}")
    
    async def create_pull_request(self, issue_id: str, author: str, title: str, 
                                description: str, code_changes: Dict[str, str]) -> str:
        """创建Pull Request
        
        Args:
            issue_id: 关联的Issue ID
            author: 作者（agent ID）
            title: PR标题
            description: PR描述
            code_changes: 代码更改 {file_path: code_content}
            
        Returns:
            PR ID
        """
        # 生成PR ID
        pr_id = f"pr_{issue_id}_{author}_{int(datetime.now().timestamp())}"
        branch_name = f"feature/{issue_id}-{author}"
        
        # 创建PR对象
        pr = PullRequest(
            pr_id=pr_id,
            issue_id=issue_id,
            author=author,
            title=title,
            description=description,
            code_changes=code_changes,
            branch_name=branch_name
        )
        
        # 在author的仓库中创建分支
        if author in self.agent_repos:
            agent_git = self.agent_repos[author]
            try:
                # 创建并切换到新分支
                await agent_git.create_branch(branch_name)
                logger.info(f"为{author}创建分支: {branch_name}")
                
                # 在分支中提交代码更改
                for file_path, code_content in code_changes.items():
                    full_path = os.path.join(agent_git.repo_path, file_path)
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(code_content)
                
                # 提交更改
                commit_message = f"feat: {title}\n\nImplements #{issue_id}\n\nPR: #{pr_id}"
                await agent_git.commit_changes(commit_message, list(code_changes.keys()))
                logger.info(f"{author}在分支{branch_name}中提交代码")
                
            except Exception as e:
                logger.error(f"在agent仓库中创建分支失败: {e}")
        
        # 保存PR到文件
        await self._save_pull_request(pr)
        
        logger.info(f"🔄 创建Pull Request: {pr_id} by {author}")
        logger.info(f"📋 PR标题: {title}")
        logger.info(f"🌿 分支: {branch_name}")
        logger.info(f"📁 文件数量: {len(code_changes)}")
        
        return pr_id
    
    async def _save_pull_request(self, pr: PullRequest):
        """保存PR到文件"""
        try:
            # 读取现有PR
            with open(self.pr_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 更新或添加PR
            prs = data.get("pull_requests", [])
            existing_pr_index = None
            for i, existing_pr in enumerate(prs):
                if existing_pr["pr_id"] == pr.pr_id:
                    existing_pr_index = i
                    break
            
            if existing_pr_index is not None:
                prs[existing_pr_index] = pr.to_dict()
            else:
                prs.append(pr.to_dict())
            
            data["pull_requests"] = prs
            
            # 写回文件
            with open(self.pr_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 提交PR文件更改到主仓库
            await self.main_repo_git_manager.commit_changes(
                f"Update PR: {pr.pr_id}",
                [".pull_requests.json"]
            )
            
        except Exception as e:
            logger.error(f"保存PR失败: {e}")
    
    async def get_open_pull_requests(self) -> List[PullRequest]:
        """获取开放的Pull Request"""
        try:
            with open(self.pr_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            prs = []
            for pr_data in data.get("pull_requests", []):
                if pr_data.get("status") == "open":
                    prs.append(PullRequest.from_dict(pr_data))
            
            return prs
        except Exception as e:
            logger.error(f"获取开放PR失败: {e}")
            return []
    
    async def review_pull_request(self, pr_id: str, reviewer: str, 
                                approved: bool, comments: str = "") -> bool:
        """审核Pull Request
        
        Args:
            pr_id: PR ID
            reviewer: 审核者
            approved: 是否通过
            comments: 审核评论
            
        Returns:
            是否审核成功
        """
        try:
            # 读取PR
            with open(self.pr_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 找到对应的PR
            prs = data.get("pull_requests", [])
            pr_data = None
            pr_index = None
            
            for i, pr in enumerate(prs):
                if pr["pr_id"] == pr_id:
                    pr_data = pr
                    pr_index = i
                    break
            
            if not pr_data:
                logger.error(f"未找到PR: {pr_id}")
                return False
            
            # 更新PR状态
            pr_data["status"] = "approved" if approved else "rejected"
            pr_data["reviewed_at"] = datetime.now().isoformat()
            pr_data["reviewer"] = reviewer
            pr_data["review_comments"].append({
                "reviewer": reviewer,
                "approved": approved,
                "comments": comments,
                "timestamp": datetime.now().isoformat()
            })
            
            prs[pr_index] = pr_data
            data["pull_requests"] = prs
            
            # 保存更改
            with open(self.pr_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 提交更改
            await self.main_repo_git_manager.commit_changes(
                f"Review PR {pr_id}: {'approved' if approved else 'rejected'}",
                [".pull_requests.json"]
            )
            
            logger.info(f"{'✅' if approved else '❌'} PR {pr_id} 审核{'通过' if approved else '未通过'}")
            logger.info(f"👤 审核者: {reviewer}")
            if comments:
                logger.info(f"💬 评论: {comments}")
            
            # 如果通过审核，自动合并
            if approved:
                await self.merge_pull_request(pr_id)
            
            return True
            
        except Exception as e:
            logger.error(f"审核PR失败: {e}")
            return False
    
    async def merge_pull_request(self, pr_id: str) -> bool:
        """合并Pull Request到主仓库
        
        Args:
            pr_id: PR ID
            
        Returns:
            是否合并成功
        """
        try:
            # 读取PR
            with open(self.pr_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 找到对应的PR
            pr_data = None
            pr_index = None
            
            for i, pr in enumerate(data.get("pull_requests", [])):
                if pr["pr_id"] == pr_id:
                    pr_data = pr
                    pr_index = i
                    break
            
            if not pr_data or pr_data["status"] != "approved":
                logger.error(f"PR {pr_id} 未找到或未通过审核")
                return False
            
            # 将代码更改应用到主仓库
            logger.info(f"🔀 开始合并PR {pr_id} 到主仓库")
            
            for file_path, code_content in pr_data["code_changes"].items():
                full_path = os.path.join(self.main_repo_git_manager.repo_path, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(code_content)
                
                logger.info(f"📁 合并文件: {file_path}")
            
            # 提交合并
            merge_message = f"Merge PR #{pr_id}: {pr_data['title']}\n\nCloses #{pr_data['issue_id']}"
            commit_hash = await self.main_repo_git_manager.commit_changes(
                merge_message,
                list(pr_data["code_changes"].keys())
            )
            
            # 更新PR状态
            pr_data["status"] = "merged"
            pr_data["merge_commit"] = commit_hash
            data["pull_requests"][pr_index] = pr_data
            
            # 保存PR更改
            with open(self.pr_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            await self.main_repo_git_manager.commit_changes(
                f"Update PR {pr_id} status to merged",
                [".pull_requests.json"]
            )
            
            logger.info(f"🎉 PR {pr_id} 成功合并到主仓库")
            logger.info(f"📝 合并提交: {commit_hash}")
            
            # 通知所有agent同步代码
            await self.sync_all_agents()
            
            return True
            
        except Exception as e:
            logger.error(f"合并PR失败: {e}")
            return False
    
    async def sync_all_agents(self):
        """同步所有agent的代码"""
        logger.info("🔄 开始同步所有agent的代码...")
        
        for agent_id, agent_git in self.agent_repos.items():
            try:
                logger.info(f"📥 同步agent {agent_id} 的代码")
                
                # 检查当前分支和工作目录状态
                current_branch = await agent_git.get_current_branch()
                logger.debug(f"🌿 agent {agent_id} 当前分支: {current_branch}")
                
                # 确保main分支存在
                branches = await agent_git.list_branches()
                if "main" not in branches:
                    logger.info(f"🆕 为agent {agent_id} 创建main分支")
                    # 如果没有main分支，创建一个
                    try:
                        # 先确保有初始提交
                        readme_path = os.path.join(agent_git.repo_path, "README.md")
                        if not os.path.exists(readme_path):
                            with open(readme_path, "w", encoding="utf-8") as f:
                                f.write(f"# Agent {agent_id} Repository\n\nThis is the working repository for agent {agent_id}.\n")
                            await agent_git.commit_changes("Initial commit", ["README.md"])
                        
                        # 创建main分支
                        await agent_git.create_branch("main")
                    except Exception as e:
                        logger.warning(f"⚠️ 创建main分支失败: {e}")
                
                # 如果不在main分支，需要安全地切换
                if current_branch != "main":
                    # 检查是否有未提交的更改
                    try:
                        # 先暂存所有更改
                        agent_git.repo.git.stash("push", "--include-untracked", "-m", f"Auto stash before sync")
                        logger.debug(f"💾 为agent {agent_id} 暂存未提交的更改")
                    except Exception as e:
                        logger.debug(f"暂存更改失败或无更改需要暂存: {e}")
                    
                    # 切换到main分支
                    success = await agent_git.checkout_branch("main")
                    if not success:
                        logger.warning(f"⚠️ agent {agent_id} 切换到main分支失败，跳过同步")
                        continue
                
                # 从主仓库拉取最新代码
                await self._sync_from_main_repo(agent_git)
                
                logger.info(f"✅ agent {agent_id} 同步完成")
                
            except Exception as e:
                logger.error(f"❌ 同步agent {agent_id} 失败: {e}")
                import traceback
                logger.debug(f"🔍 同步错误详情:\n{traceback.format_exc()}")
    
    async def _sync_from_main_repo(self, agent_git: GitManager):
        """从主仓库同步代码到agent仓库"""
        try:
            # 获取主仓库中的所有非Git文件
            import shutil
            import fnmatch
            
            # 定义要忽略的文件和目录模式
            ignore_patterns = [
                '.git*',
                '__pycache__',
                '*.pyc',
                '*.pyo',
                '.DS_Store',
                'Thumbs.db'
            ]
            
            def should_ignore(path):
                """检查是否应该忽略某个路径"""
                basename = os.path.basename(path)
                for pattern in ignore_patterns:
                    if fnmatch.fnmatch(basename, pattern):
                        return True
                return False
            
            # 同步文件
            synced_files = []
            
            for root, dirs, files in os.walk(self.main_repo_git_manager.repo_path):
                # 过滤要忽略的目录
                dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d))]
                
                for file in files:
                    src_file = os.path.join(root, file)
                    
                    # 跳过要忽略的文件
                    if should_ignore(src_file):
                        continue
                    
                    # 计算相对路径
                    rel_path = os.path.relpath(src_file, self.main_repo_git_manager.repo_path)
                    dst_file = os.path.join(agent_git.repo_path, rel_path)
                    
                    # 确保目标目录存在
                    dst_dir = os.path.dirname(dst_file)
                    if dst_dir:
                        os.makedirs(dst_dir, exist_ok=True)
                    
                    try:
                        # 复制文件
                        shutil.copy2(src_file, dst_file)
                        synced_files.append(rel_path)
                        logger.debug(f"📄 同步文件: {rel_path}")
                    except Exception as e:
                        logger.warning(f"⚠️ 跳过文件 {rel_path}: {e}")
            
            if synced_files:
                logger.info(f"📦 同步了 {len(synced_files)} 个文件")
                
                # 提交同步的更改
                commit_hash = await agent_git.commit_changes(
                    "Sync from main repository",
                    ["."]  # 添加所有更改
                )
                
                if commit_hash:
                    logger.debug(f"✅ 同步提交: {commit_hash[:8]}")
                else:
                    logger.debug("📝 没有需要提交的更改")
            else:
                logger.debug("📭 没有文件需要同步")
            
        except Exception as e:
            logger.error(f"从主仓库同步失败: {e}")
            import traceback
            logger.debug(f"🔍 同步错误详情:\n{traceback.format_exc()}")
    
    async def get_pr_by_id(self, pr_id: str) -> Optional[PullRequest]:
        """根据ID获取PR"""
        try:
            with open(self.pr_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for pr_data in data.get("pull_requests", []):
                if pr_data["pr_id"] == pr_id:
                    return PullRequest.from_dict(pr_data)
            
            return None
        except Exception as e:
            logger.error(f"获取PR失败: {e}")
            return None
    
    async def cleanup_merged_branches(self):
        """清理已合并的分支"""
        logger.info("🧹 开始清理已合并的分支...")
        
        try:
            with open(self.pr_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for pr_data in data.get("pull_requests", []):
                if pr_data["status"] == "merged":
                    author = pr_data["author"]
                    branch_name = pr_data["branch_name"]
                    
                    if author in self.agent_repos:
                        try:
                            agent_git = self.agent_repos[author]
                            await agent_git.delete_branch(branch_name)
                            logger.info(f"🗑️ 删除已合并分支: {branch_name}")
                        except Exception as e:
                            logger.debug(f"删除分支失败: {e}")
            
        except Exception as e:
            logger.error(f"清理分支失败: {e}") 