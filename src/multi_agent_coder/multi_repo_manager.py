"""多仓库管理器模块

管理每个agent的独立仓库和主playground仓库的同步。
"""

import os
import shutil
import logging
from typing import Dict, List, Optional
from git import Repo, GitCommandError
from .git_utils import GitManager

logger = logging.getLogger(__name__)

class MultiRepoManager:
    """多仓库管理器"""
    
    def __init__(self, playground_repo_url: str, agent_repos_dir: str):
        """初始化多仓库管理器
        
        Args:
            playground_repo_url: 主playground仓库URL
            agent_repos_dir: agent仓库存储目录
        """
        self.playground_repo_url = playground_repo_url
        self.agent_repos_dir = agent_repos_dir
        self.playground_path = os.path.join(agent_repos_dir, "playground")
        self.agent_git_managers: Dict[str, GitManager] = {}
        self.playground_git_manager: Optional[GitManager] = None
        
        # 确保目录存在
        os.makedirs(agent_repos_dir, exist_ok=True)
        
        logger.info(f"初始化多仓库管理器: {agent_repos_dir}")
    
    async def setup_playground_repo(self) -> GitManager:
        """设置主playground仓库
        
        Returns:
            playground仓库的GitManager
        """
        try:
            # 如果没有指定远程仓库URL，直接创建本地仓库
            if not self.playground_repo_url or self.playground_repo_url.strip() == "":
                logger.info("未指定远程仓库，创建本地playground仓库")
                if not os.path.exists(self.playground_path):
                    os.makedirs(self.playground_path)
                    repo = Repo.init(self.playground_path)
                    logger.info(f"创建本地playground仓库: {self.playground_path}")
            else:
                # 有远程仓库URL，尝试克隆或拉取
                if os.path.exists(self.playground_path):
                    # 如果目录已存在，尝试拉取最新代码
                    repo = Repo(self.playground_path)
                    if repo.remotes:
                        try:
                            repo.remotes.origin.pull()
                            logger.info("拉取playground仓库最新代码")
                        except Exception as e:
                            logger.warning(f"拉取playground仓库失败，使用现有本地仓库: {e}")
                    else:
                        logger.info("使用现有本地playground仓库")
                else:
                    # 克隆playground仓库
                    try:
                        Repo.clone_from(self.playground_repo_url, self.playground_path)
                        logger.info(f"克隆playground仓库: {self.playground_repo_url}")
                    except Exception as e:
                        logger.warning(f"克隆playground仓库失败，创建本地仓库: {e}")
                        os.makedirs(self.playground_path)
                        Repo.init(self.playground_path)
            
            # 确保.issues.json文件存在
            issues_file = os.path.join(self.playground_path, ".issues.json")
            if not os.path.exists(issues_file):
                import json
                with open(issues_file, "w") as f:
                    json.dump({"issues": []}, f)
                logger.info("创建.issues.json文件")
            
            self.playground_git_manager = GitManager(self.playground_path)
            return self.playground_git_manager
            
        except Exception as e:
            logger.error(f"设置playground仓库失败: {e}")
            # 如果克隆失败，创建本地仓库
            if not os.path.exists(self.playground_path):
                os.makedirs(self.playground_path)
                repo = Repo.init(self.playground_path)
                # 尝试添加远程仓库（如果URL有效的话）
                if self.playground_repo_url and self.playground_repo_url.strip():
                    try:
                        repo.create_remote("origin", self.playground_repo_url)
                        logger.info(f"添加远程仓库: {self.playground_repo_url}")
                    except Exception:
                        logger.warning(f"无法添加远程仓库: {self.playground_repo_url}")
                logger.info(f"创建本地playground仓库: {self.playground_path}")
            
            # 确保.issues.json文件存在
            issues_file = os.path.join(self.playground_path, ".issues.json")
            if not os.path.exists(issues_file):
                import json
                with open(issues_file, "w") as f:
                    json.dump({"issues": []}, f)
                logger.info("创建.issues.json文件")
            
            self.playground_git_manager = GitManager(self.playground_path)
            return self.playground_git_manager
    
    async def setup_agent_repo(self, agent_id: str) -> GitManager:
        """为agent设置独立仓库
        
        Args:
            agent_id: agent ID
            
        Returns:
            agent仓库的GitManager
        """
        agent_repo_path = os.path.join(self.agent_repos_dir, f"agent_{agent_id}")
        
        try:
            if os.path.exists(agent_repo_path):
                # 如果目录已存在，使用现有仓库
                logger.info(f"使用现有agent仓库: {agent_repo_path}")
            else:
                # 从playground仓库复制初始内容
                if self.playground_git_manager and os.path.exists(self.playground_path):
                    shutil.copytree(self.playground_path, agent_repo_path)
                    logger.info(f"从playground复制创建agent仓库: {agent_repo_path}")
                else:
                    # 创建新的空仓库
                    os.makedirs(agent_repo_path)
                    Repo.init(agent_repo_path)
                    # 创建.issues.json文件
                    import json
                    issues_file = os.path.join(agent_repo_path, ".issues.json")
                    with open(issues_file, "w") as f:
                        json.dump({"issues": []}, f)
                    logger.info(f"创建新的agent仓库: {agent_repo_path}")
            
            # 确保.issues.json文件存在
            issues_file = os.path.join(agent_repo_path, ".issues.json")
            if not os.path.exists(issues_file):
                import json
                with open(issues_file, "w") as f:
                    json.dump({"issues": []}, f)
                logger.info(f"为agent {agent_id} 创建.issues.json文件")
            
            # 创建GitManager
            git_manager = GitManager(agent_repo_path)
            self.agent_git_managers[agent_id] = git_manager
            
            return git_manager
            
        except Exception as e:
            logger.error(f"设置agent仓库失败: {e}")
            raise
    
    async def sync_agent_to_playground(self, agent_id: str) -> bool:
        """将agent的工作同步到playground仓库
        
        Args:
            agent_id: agent ID
            
        Returns:
            是否同步成功
        """
        try:
            if agent_id not in self.agent_git_managers:
                logger.error(f"Agent {agent_id} 仓库不存在")
                return False
            
            if not self.playground_git_manager:
                logger.error("Playground仓库未初始化")
                return False
            
            agent_repo_path = os.path.join(self.agent_repos_dir, f"agent_{agent_id}")
            
            # 复制agent的工作到playground
            # 这里可以实现更智能的合并策略
            for root, dirs, files in os.walk(agent_repo_path):
                # 跳过.git目录
                if '.git' in dirs:
                    dirs.remove('.git')
                
                for file in files:
                    if file.startswith('.'):
                        continue
                    
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file, agent_repo_path)
                    dst_file = os.path.join(self.playground_path, rel_path)
                    
                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    
                    # 复制文件
                    shutil.copy2(src_file, dst_file)
            
            # 提交到playground仓库
            await self.playground_git_manager.commit_changes(
                f"同步来自 {agent_id} 的工作",
                ["."]
            )
            
            # 只有在有远程仓库时才推送
            if self.playground_repo_url and self.playground_repo_url.strip():
                await self.playground_git_manager.push_changes()
            else:
                logger.info("本地仓库模式，跳过推送到远程")
            
            logger.info(f"成功同步 {agent_id} 的工作到playground")
            return True
            
        except Exception as e:
            logger.error(f"同步agent工作到playground失败: {e}")
            return False
    
    async def sync_playground_to_agents(self) -> bool:
        """将playground的更新同步到所有agent仓库
        
        Returns:
            是否同步成功
        """
        try:
            if not self.playground_git_manager:
                logger.error("Playground仓库未初始化")
                return False
            
            # 只有在有远程仓库时才拉取playground的最新更新
            try:
                if self.playground_repo_url and self.playground_repo_url.strip():
                    if self.playground_git_manager.repo.remotes:
                        await self.playground_git_manager.pull_changes()
                    else:
                        logger.debug("Playground仓库没有远程配置，跳过拉取")
                else:
                    logger.debug("本地仓库模式，跳过拉取playground更新")
            except Exception as e:
                logger.debug(f"跳过拉取playground更新: {e}")
            
            # 同步到所有agent仓库
            for agent_id, git_manager in self.agent_git_managers.items():
                agent_repo_path = os.path.join(self.agent_repos_dir, f"agent_{agent_id}")
                
                # 复制playground的更新到agent仓库
                # 这里可以实现更智能的合并策略，避免覆盖agent的工作
                for root, dirs, files in os.walk(self.playground_path):
                    if '.git' in dirs:
                        dirs.remove('.git')
                    
                    for file in files:
                        if file.startswith('.'):
                            continue
                        
                        src_file = os.path.join(root, file)
                        rel_path = os.path.relpath(src_file, self.playground_path)
                        dst_file = os.path.join(agent_repo_path, rel_path)
                        
                        # 只复制不存在的文件，避免覆盖agent的工作
                        if not os.path.exists(dst_file):
                            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                            shutil.copy2(src_file, dst_file)
                
                # 提交更新
                await git_manager.commit_changes(
                    "同步playground更新",
                    ["."]
                )
            
            logger.info("成功同步playground更新到所有agent仓库")
            return True
            
        except Exception as e:
            logger.error(f"同步playground到agent仓库失败: {e}")
            return False
    
    def get_agent_git_manager(self, agent_id: str) -> Optional[GitManager]:
        """获取agent的GitManager
        
        Args:
            agent_id: agent ID
            
        Returns:
            GitManager实例或None
        """
        return self.agent_git_managers.get(agent_id)
    
    def get_playground_git_manager(self) -> Optional[GitManager]:
        """获取playground的GitManager
        
        Returns:
            GitManager实例或None
        """
        return self.playground_git_manager
    
    async def cleanup_agent_repo(self, agent_id: str) -> bool:
        """清理agent仓库
        
        Args:
            agent_id: agent ID
            
        Returns:
            是否清理成功
        """
        try:
            agent_repo_path = os.path.join(self.agent_repos_dir, f"agent_{agent_id}")
            if os.path.exists(agent_repo_path):
                shutil.rmtree(agent_repo_path)
                logger.info(f"清理agent仓库: {agent_repo_path}")
            
            if agent_id in self.agent_git_managers:
                del self.agent_git_managers[agent_id]
            
            return True
            
        except Exception as e:
            logger.error(f"清理agent仓库失败: {e}")
            return False 