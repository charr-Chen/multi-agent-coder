"""Git 操作工具模块

提供 Git 仓库操作、Issue 管理和冲突解决等功能。
"""

import os
import json
import uuid
import logging
import subprocess
import asyncio
import shutil
import tempfile
import time
import random

from pathlib import Path
from typing import Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class GitManager:
    """Git 仓库管理器"""
    
    def __init__(self, repo_path: str):
        """初始化 Git 管理器
        
        Args:
            repo_path: Git 仓库路径
        """
        self.repo_path = os.path.abspath(repo_path)
        self.issues_file = os.path.join(self.repo_path, '.issues.json')  # 修复：使用.issues.json保持一致性
        self.lock_file = os.path.join(self.repo_path, '.git_operations.lock')
        
        # 确保repo路径存在且是git仓库
        if not os.path.exists(self.repo_path):
            os.makedirs(self.repo_path, exist_ok=True)
        
        # 初始化git仓库（如果不存在）
        if not os.path.exists(os.path.join(self.repo_path, '.git')):
            self._run_git_command(['init'])
            
        # 设置git配置（如果需要）
        try:
            self._run_git_command(['config', 'user.name'], check_output=True)
        except subprocess.CalledProcessError:
            self._run_git_command(['config', 'user.name', 'Multi-Agent-Coder'])
            self._run_git_command(['config', 'user.email', 'agent@multi-agent-coder.com'])
        
        logger.info(f"初始化 Git 仓库: {self.repo_path}")
    
    def _run_git_command(self, args: list[str], check_output: bool = False, input_data: str = None) -> str:
        """运行Git命令
        
        Args:
            args: Git命令参数
            check_output: 是否返回输出
            input_data: 输入数据
            
        Returns:
            命令输出（如果check_output为True）
        """
        cmd = ['git'] + args
        try:
            if check_output:
                result = subprocess.run(
                    cmd, 
                    cwd=self.repo_path, 
                    capture_output=True, 
                    text=True, 
                    check=True,
                    input=input_data
                )
                return result.stdout.strip()
            else:
                subprocess.run(
                    cmd, 
                    cwd=self.repo_path, 
                    check=True,
                    input=input_data,
                    text=True if input_data else None
                )
                return ""
        except subprocess.CalledProcessError as e:
            logger.error(f"Git命令失败: {' '.join(cmd)}, 错误: {e}")
            raise
    
    async def _acquire_lock(self, timeout: float = 30.0):
        """获取文件锁，防止并发操作
        
        Args:
            timeout: 超时时间（秒）
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # 创建锁文件
                lock_fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(lock_fd, f"{os.getpid()}".encode())
                os.close(lock_fd)
                return True
            except OSError:
                # 锁文件已存在，等待
                await asyncio.sleep(0.1 + random.uniform(0, 0.1))
        
        # 超时，强制清理锁文件
        if os.path.exists(self.lock_file):
            try:
                os.remove(self.lock_file)
                logger.warning("强制清理Git操作锁文件")
            except OSError:
                pass
        
        raise TimeoutError("获取Git操作锁超时")
    
    def _release_lock(self):
        """释放文件锁"""
        try:
            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
        except OSError:
            pass
    
    async def _retry_with_backoff(self, func, max_retries=5, base_delay=0.1):
        """带指数退避的重试机制
        
        Args:
            func: 要重试的函数
            max_retries: 最大重试次数
            base_delay: 基础延迟时间（秒）
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                # 获取锁
                await self._acquire_lock()
                try:
                    return await func() if asyncio.iscoroutinefunction(func) else func()
                finally:
                    self._release_lock()
            except (subprocess.CalledProcessError, OSError, IOError, TimeoutError) as e:
                last_exception = e
                if "index.lock" in str(e) or "could not be obtained" in str(e) or "timeout" in str(e).lower():
                    # Git锁文件冲突或超时，等待后重试
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 0.1)
                    logger.warning(f"Git操作冲突，等待 {delay:.2f}s 后重试 (尝试 {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                    
                    # 尝试清理Git锁文件
                    git_lock_file = os.path.join(self.repo_path, '.git', 'index.lock')
                    if os.path.exists(git_lock_file):
                        try:
                            os.remove(git_lock_file)
                            logger.info("清理Git index锁文件")
                        except OSError:
                            pass
                else:
                    # 其他错误，直接抛出
                    self._release_lock()
                    raise
        
        # 所有重试都失败了
        self._release_lock()
        logger.error(f"Git操作失败，已重试 {max_retries} 次: {last_exception}")
        raise last_exception
    
    def _load_issues(self) -> dict[str, list[dict[str, Any]]]:
        """从文件加载issues"""
        if os.path.exists(self.issues_file):
            try:
                with open(self.issues_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        return {"issues": []}
                    return json.loads(content)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"加载Issues文件失败: {e}")
                return {"issues": []}
        return {"issues": []}
    
    def _save_issues(self, data: dict[str, list[dict[str, Any]]]) -> None:
        """保存issues到文件"""
        try:
            # 使用临时文件确保原子性写入
            temp_file = self.issues_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # 原子性重命名
            os.replace(temp_file, self.issues_file)
        except IOError as e:
            logger.error(f"保存Issues文件失败: {e}")
            raise
    
    async def create_issue(self, title: str, description: str) -> dict[str, Any]:
        """创建新的 Issue
        
        Args:
            title: Issue 标题
            description: Issue 描述
            
        Returns:
            Issue 信息字典
        """
        def _create():
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
            return issue
        
        # 创建Issue
        issue = await self._retry_with_backoff(_create)
        
        # 提交更改
        def _commit_create():
            # 添加文件到Git
            self._run_git_command(['add', '.issues.json'])
            # 提交
            self._run_git_command(['commit', '-m', f'创建 Issue: {title}'])
        
        try:
            await self._retry_with_backoff(_commit_create)
        except subprocess.CalledProcessError as e:
            if "nothing to commit" not in str(e):
                logger.warning(f"提交Issue创建失败: {e}")
        
        logger.info(f"创建 Issue: {title}")
        return issue
    
    async def get_open_issues(self) -> list[dict[str, Any]]:
        """获取所有open状态的issues"""
        def _get():
            data = self._load_issues()
            return [issue for issue in data.get("issues", []) if issue.get("status") == "open"]
        
        return await self._retry_with_backoff(_get)
    
    async def assign_issue(self, issue_id: str, assignee: str) -> bool:
        """分配 Issue 给指定代理
        
        Args:
            issue_id: Issue ID
            assignee: 被分配的代理
            
        Returns:
            是否分配成功
        """
        def _assign():
            data = self._load_issues()
            for issue in data["issues"]:
                if issue["id"] == issue_id and issue["status"] == "open":
                    issue["assigned_to"] = assignee
                    issue["status"] = "assigned"
                    self._save_issues(data)
                    return True
            return False
                
        # 使用重试机制分配issue
        try:
            success = await self._retry_with_backoff(_assign)
            if success:
                # 提交更改
                def _commit_assign():
                    self._run_git_command(['add', '.issues.json'])
                    self._run_git_command(['commit', '-m', f'分配 Issue {issue_id} 给 {assignee}'])
                
                try:
                    await self._retry_with_backoff(_commit_assign)
                except subprocess.CalledProcessError as e:
                    if "nothing to commit" not in str(e):
                        logger.warning(f"提交Issue分配失败: {e}")
                
                logger.info(f"分配 Issue {issue_id} 给 {assignee}")
                return True
        except Exception as e:
            logger.error(f"分配Issue失败: {e}")
        
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
        def _update():
            data = self._load_issues()
            for issue in data["issues"]:
                if issue["id"] == issue_id:
                    issue["status"] = status
                    if code_submission:
                        issue["code_submission"] = code_submission
                    self._save_issues(data)
                    return True
            return False
                
        try:
            success = await self._retry_with_backoff(_update)
            if success:
                # 提交更改
                def _commit_update():
                    self._run_git_command(['add', '.issues.json'])
                    self._run_git_command(['commit', '-m', f'更新 Issue {issue_id} 状态为 {status}'])
                
                try:
                    await self._retry_with_backoff(_commit_update)
                except subprocess.CalledProcessError as e:
                    if "nothing to commit" not in str(e):
                        logger.warning(f"提交Issue更新失败: {e}")
                
                logger.info(f"更新 Issue {issue_id} 状态为 {status}")
                return True
        except Exception as e:
            logger.error(f"更新Issue状态失败: {e}")
        
        return False
    
    async def commit_changes(self, message: str, files: list[str]) -> str:
        """提交代码更改
        
        Args:
            message: 提交信息
            files: 要提交的文件列表
            
        Returns:
            提交的hash值，失败时返回空字符串
        """
        def _commit():
            # 添加文件
            for file in files:
                if os.path.exists(os.path.join(self.repo_path, file)):
                    self._run_git_command(['add', file])
            
            # 检查是否有改动
            try:
                status = self._run_git_command(['status', '--porcelain'], check_output=True)
                if not status.strip():
                    logger.debug("没有改动需要提交")
                    return ""
            except subprocess.CalledProcessError:
                pass
            
            # 提交
            self._run_git_command(['commit', '-m', message])
            
            # 获取提交hash
            commit_hash = self._run_git_command(['rev-parse', 'HEAD'], check_output=True)
            logger.info(f"提交更改: {message}")
            return commit_hash
        
        try:
            return await self._retry_with_backoff(_commit)
        except subprocess.CalledProcessError as e:
            if "nothing to commit" in str(e):
                logger.debug("没有改动需要提交")
                return ""
            logger.error(f"提交失败: {e}")
            return ""
    
    async def push_changes(self) -> bool:
        """推送代码到远程仓库
        
        Returns:
            是否推送成功
        """
        def _push():
            # 检查是否有远程仓库
            try:
                remotes = self._run_git_command(['remote'], check_output=True)
                if not remotes.strip():
                    logger.debug("没有配置远程仓库，跳过推送操作")
                    return True
            except subprocess.CalledProcessError:
                logger.debug("没有配置远程仓库，跳过推送操作")
                return True
            
            # 推送到origin
            try:
                self._run_git_command(['push', 'origin', 'HEAD'])
                logger.info("推送更改到远程仓库")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"推送失败: {e}")
                return False
        
        try:
            return await self._retry_with_backoff(_push)
        except Exception as e:
            logger.error(f"推送操作失败: {e}")
            return False
    
    async def pull_changes(self) -> bool:
        """从远程仓库拉取代码
        
        Returns:
            是否拉取成功
        """
        def _pull():
            # 检查是否有远程仓库
            try:
                remotes = self._run_git_command(['remote'], check_output=True)
                if not remotes.strip():
                    logger.debug("没有配置远程仓库，跳过拉取操作")
                    return True
            except subprocess.CalledProcessError:
                logger.debug("没有配置远程仓库，跳过拉取操作")
                return True
            
            # 从origin拉取
            try:
                self._run_git_command(['pull', 'origin', 'HEAD'])
                logger.info("从远程仓库拉取更改")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"拉取失败: {e}")
                return False
        
        try:
            return await self._retry_with_backoff(_pull)
        except Exception as e:
            logger.error(f"拉取操作失败: {e}")
            return False
    
    async def resolve_conflicts(self) -> bool:
        """解决代码冲突
        
        Returns:
            是否解决成功
        """
        def _resolve():
            try:
                # 获取当前分支
                current_branch = self._run_git_command(['branch', '--show-current'], check_output=True)
                
                # 尝试拉取并使用rebase策略
                self._run_git_command(['pull', '--rebase', 'origin', current_branch])
                logger.info("使用 rebase 解决冲突")
                return True
            except subprocess.CalledProcessError as e:
                if "CONFLICT" in str(e):
                    # 取消rebase
                    try:
                        self._run_git_command(['rebase', '--abort'])
                    except subprocess.CalledProcessError:
                        pass
                    
                    # 重置到远程状态
                    try:
                        self._run_git_command(['reset', '--hard', f'origin/{current_branch}'])
                        logger.info("重置到远程状态解决冲突")
                        return True
                    except subprocess.CalledProcessError:
                        pass
                
                logger.error(f"解决冲突失败: {e}")
                return False
        
        try:
            return await self._retry_with_backoff(_resolve)
        except Exception as e:
            logger.error(f"冲突解决操作失败: {e}")
            return False
    
    async def create_branch(self, branch_name: str) -> bool:
        """创建并切换到新分支
        
        Args:
            branch_name: 分支名称
            
        Returns:
            是否创建成功
        """
        def _create_branch():
            # 检查分支是否已存在
            try:
                branches = self._run_git_command(['branch', '--list', branch_name], check_output=True)
                if branches.strip():
                    logger.info(f"分支 {branch_name} 已存在，切换到该分支")
                    self._run_git_command(['checkout', branch_name])
                    return True
            except subprocess.CalledProcessError:
                pass
            
            # 创建新分支
            self._run_git_command(['checkout', '-b', branch_name])
            logger.info(f"创建并切换到分支: {branch_name}")
            return True
        
        try:
            return await self._retry_with_backoff(_create_branch)
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
        def _checkout():
            # 检查分支是否存在
            try:
                branches = self._run_git_command(['branch', '--list', branch_name], check_output=True)
                if not branches.strip():
                    logger.error(f"分支 {branch_name} 不存在")
                    return False
            except subprocess.CalledProcessError:
                logger.error(f"分支 {branch_name} 不存在")
                return False
            
            # 切换分支
            self._run_git_command(['checkout', branch_name])
            logger.info(f"切换到分支: {branch_name}")
            return True
        
        try:
            return await self._retry_with_backoff(_checkout)
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
        def _delete():
            # 检查分支是否存在
            try:
                branches = self._run_git_command(['branch', '--list', branch_name], check_output=True)
                if not branches.strip():
                    logger.debug(f"分支 {branch_name} 不存在，无需删除")
                    return True
            except subprocess.CalledProcessError:
                logger.debug(f"分支 {branch_name} 不存在，无需删除")
                return True
            
            # 获取当前分支
            try:
                current_branch = self._run_git_command(['branch', '--show-current'], check_output=True)
                if current_branch == branch_name:
                    logger.warning(f"不能删除当前分支: {branch_name}")
                    return False
            except subprocess.CalledProcessError:
                pass
            
            # 删除分支
            self._run_git_command(['branch', '-D', branch_name])
            logger.info(f"删除分支: {branch_name}")
            return True
        
        try:
            return await self._retry_with_backoff(_delete)
        except Exception as e:
            logger.error(f"删除分支失败: {e}")
            return False
    
    async def get_current_branch(self) -> str:
        """获取当前分支名称
        
        Returns:
            当前分支名称
        """
        def _get_branch():
            try:
                return self._run_git_command(['branch', '--show-current'], check_output=True)
            except subprocess.CalledProcessError:
                return "main"
        
        try:
            return await self._retry_with_backoff(_get_branch)
        except Exception as e:
            logger.error(f"获取当前分支失败: {e}")
            return "main"
    
    async def list_branches(self) -> list[str]:
        """列出所有分支
        
        Returns:
            分支名称列表
        """
        def _list():
            try:
                output = self._run_git_command(['branch'], check_output=True)
                branches = []
                for line in output.split('\n'):
                    branch = line.strip().lstrip('* ')
                    if branch:
                        branches.append(branch)
                return branches
            except subprocess.CalledProcessError:
                return []
        
        try:
            return await self._retry_with_backoff(_list)
        except Exception as e:
            logger.error(f"列出分支失败: {e}")
            return []
    
    async def merge_branch(self, branch_name: str, message: str = None) -> bool:
        """合并分支
        
        Args:
            branch_name: 要合并的分支名称
            message: 合并提交信息
            
        Returns:
            是否合并成功
        """
        def _merge():
            # 检查分支是否存在
            try:
                branches = self._run_git_command(['branch', '--list', branch_name], check_output=True)
                if not branches.strip():
                    logger.error(f"分支 {branch_name} 不存在")
                    return False
            except subprocess.CalledProcessError:
                logger.error(f"分支 {branch_name} 不存在")
                return False
            
            # 合并分支
            merge_cmd = ['merge', branch_name]
            if message:
                merge_cmd.extend(['-m', message])
            
            self._run_git_command(merge_cmd)
            logger.info(f"合并分支: {branch_name}")
            return True
        
        try:
            return await self._retry_with_backoff(_merge)
        except Exception as e:
            logger.error(f"合并分支失败: {e}")
            return False 