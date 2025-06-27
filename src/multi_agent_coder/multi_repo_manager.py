"""多仓库管理器模块

管理每个agent的独立仓库和主playground仓库的同步。
"""

import os
import asyncio
import logging
import shutil
import time
import traceback
from pathlib import Path
from typing import Optional
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
        self.agent_git_managers: dict[str, GitManager] = {}
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
        
        # 使用绝对路径，避免相对路径问题
        agent_repo_path = os.path.abspath(os.path.join(self.agent_repos_dir, f"agent_{agent_id}"))
        
        try:
            if os.path.exists(agent_repo_path):
                # 如果目录已存在，使用现有仓库
                logger.info(f"使用现有agent仓库: {agent_repo_path}")
            else:
                # 创建新的agent仓库目录
                os.makedirs(agent_repo_path)
                
                # 初始化Git仓库
                repo = Repo.init(agent_repo_path)
                logger.info(f"初始化agent仓库: {agent_repo_path}")
                
                # 从playground仓库复制内容（包括参考项目代码）
                if self.playground_git_manager and os.path.exists(self.playground_path):
                    await self._copy_repo_content(self.playground_path, agent_repo_path)
                    logger.info(f"从playground复制参考项目内容到agent仓库: {agent_repo_path}")
                
                # 创建src目录（如果不存在）
                src_dir = os.path.join(agent_repo_path, "src")
                os.makedirs(src_dir, exist_ok=True)
                
                # 创建初始README文件
                readme_path = os.path.join(agent_repo_path, "README.md")
                if not os.path.exists(readme_path):
                    with open(readme_path, "w", encoding="utf-8") as f:
                        f.write(f"# Agent {agent_id} Repository\n\n")
                        f.write(f"This is the working repository for agent {agent_id}.\n")
                        f.write("This repository is automatically managed by the multi-agent coder system.\n")
                        f.write("\n## Reference Project\n")
                        f.write("This repository contains the reference project code for learning and inspiration.\n")
            
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
    
    async def _copy_repo_content(self, src_path: str, dst_path: str):
        """安全地复制仓库内容，排除Git元数据和冲突文件
        
        Args:
            src_path: 源路径
            dst_path: 目标路径
        """
        import fnmatch
        
        # 定义要忽略的文件和目录模式 - 只忽略必要的系统文件
        ignore_patterns = [
            '.git',
            '.git/*',
            '__pycache__',
            '*.pyc',
            '*.pyo',
            '.DS_Store',
            'Thumbs.db',
            '.env',
            '.env.*',
            # 🆕 避免循环复制agent_repos目录
            'agent_repos',
            'agent_repos/*',
            # 只忽略可能导致冲突的特定文件
            'node_modules',  # npm依赖
            '.pytest_cache',  # pytest缓存
            '*.log',  # 日志文件
            '.coverage',  # 覆盖率文件
            '.venv',  # 虚拟环境
            'venv',   # 虚拟环境
        ]
        
        def should_ignore(path, name):
            """检查是否应该忽略某个路径"""
            # 检查完整路径
            full_path = os.path.join(path, name)
            rel_path = os.path.relpath(full_path, src_path)
            
            for pattern in ignore_patterns:
                if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel_path, pattern):
                    return True
            return False
        
        logger.info(f"📁 开始复制参考项目内容: {src_path} -> {dst_path}")
        copied_files = 0
        
        # 递归复制文件，但排除指定的模式
        for root, dirs, files in os.walk(src_path):
            # 过滤要忽略的目录
            original_dirs = dirs[:]
            dirs[:] = [d for d in dirs if not should_ignore(root, d)]
            
            # 记录被忽略的目录
            ignored_dirs = set(original_dirs) - set(dirs)
            if ignored_dirs:
                logger.debug(f"🚫 忽略目录: {ignored_dirs}")
            
            for file in files:
                if should_ignore(root, file):
                    logger.debug(f"🚫 忽略文件: {file}")
                    continue
                
                src_file = os.path.join(root, file)
                rel_path = os.path.relpath(src_file, src_path)
                dst_file = os.path.join(dst_path, rel_path)
                
                # 确保目标目录存在
                dst_dir = os.path.dirname(dst_file)
                if dst_dir:
                    os.makedirs(dst_dir, exist_ok=True)
                
                try:
                    # 复制文件
                    shutil.copy2(src_file, dst_file)
                    copied_files += 1
                    logger.debug(f"📄 复制文件: {rel_path}")
                except Exception as e:
                    logger.warning(f"⚠️ 跳过文件 {rel_path}: {e}")
        
        logger.info(f"✅ 完成复制，共复制了 {copied_files} 个文件")
    
    async def sync_agent_to_playground(self, agent_id: str) -> bool:
        """将agent的工作同步到playground仓库
        
        Args:
            agent_id: agent ID
            
        Returns:
            是否同步成功
        """
        try:
            if not self.playground_git_manager:
                logger.error("Playground仓库未初始化")
                return False

            # 使用绝对路径，避免相对路径问题
            agent_repo_path = os.path.abspath(os.path.join(self.agent_repos_dir, f"agent_{agent_id}"))
            
            # 检查agent仓库是否存在
            if not os.path.exists(agent_repo_path):
                logger.error(f"Agent仓库不存在: {agent_repo_path}")
                return False
            
            logger.info(f"🔄 开始同步 {agent_id} 的工作到playground...")
            synced_files = 0
            
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
                    dst_dir = os.path.dirname(dst_file)
                    if dst_dir:
                        os.makedirs(dst_dir, exist_ok=True)
                    
                    try:
                        # 复制文件
                        shutil.copy2(src_file, dst_file)
                        synced_files += 1
                        logger.debug(f"📄 同步文件: {rel_path}")
                    except Exception as e:
                        logger.warning(f"⚠️ 跳过文件 {rel_path}: {e}")
            
            logger.info(f"📦 同步了 {synced_files} 个文件")
            
            # 提交到playground仓库
            commit_hash = await self.playground_git_manager.commit_changes(
                f"同步来自 {agent_id} 的工作",
                ["."]
            )
            
            if commit_hash:
                logger.info(f"✅ 同步提交成功: {commit_hash[:8]}")
            else:
                logger.info("📝 没有新的更改需要提交")
            
            # 只有在有远程仓库时才推送
            if self.playground_repo_url and self.playground_repo_url.strip():
                await self.playground_git_manager.push_changes()
                logger.info("📤 已推送到远程仓库")
            else:
                logger.debug("本地仓库模式，跳过推送到远程")
            
            logger.info(f"✅ 成功同步 {agent_id} 的工作到playground")
            return True
            
        except Exception as e:
            logger.error(f"❌ 同步agent工作到playground失败: {e}")
            import traceback
            logger.debug(f"🔍 同步错误详情:\n{traceback.format_exc()}")
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
            # 使用绝对路径，避免相对路径问题
            agent_repo_path = os.path.abspath(os.path.join(self.agent_repos_dir, f"agent_{agent_id}"))
            
            if os.path.exists(agent_repo_path):
                shutil.rmtree(agent_repo_path)
                logger.info(f"清理agent仓库: {agent_repo_path}")
            
            # 从管理器中移除
            if agent_id in self.agent_git_managers:
                del self.agent_git_managers[agent_id]
            
            return True
        except Exception as e:
            logger.error(f"清理agent仓库失败: {e}")
            return False
