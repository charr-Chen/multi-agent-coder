"""
评论员代理模块
负责创建任务、审查代码提交和管理 Issue。
"""

import logging
import re
import time
import asyncio
from pathlib import Path
from typing import Any, Optional
from ..git_utils import GitManager
from ..llm_utils import LLMManager
from ..config import AGENT_CONFIG

logger = logging.getLogger(__name__)

class CommenterAgent:
    """评论员代理类"""
    
    def __init__(self, agent_id: str, git_manager: GitManager, llm_manager: LLMManager):
        """初始化评论员代理
        
        Args:
            agent_id: 代理ID
            git_manager: Git 仓库管理器
            llm_manager: LLM 管理器
        """
        self.agent_id = agent_id
        self.git_manager = git_manager
        self.llm_manager = llm_manager
        self.config = AGENT_CONFIG["commenter"]
        self.collaboration_manager = None  # 协作管理器
        
        # 注释模板和规范
        self.comment_templates = {
            "function": '''"""
{description}

Args:
{args}

Returns:
{returns}

Raises:
{raises}
"""''',
            "class": '''"""
{description}

Attributes:
{attributes}

Example:
{example}
"""''',
            "module": '''"""
{description}

This module contains:
{contents}

Author: {author}
Created: {created}
"""'''
        }
        
        logger.info(f"📝 注释员代理 {agent_id} 初始化完成")
    
    def set_collaboration_manager(self, collaboration_manager):
        """设置协作管理器
        
        Args:
            collaboration_manager: 协作管理器实例
        """
        self.collaboration_manager = collaboration_manager
        logger.info("评论员设置协作管理器")
    
    async def create_issue(self, title: str, description: str) -> dict[str, Any]:
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
    
    async def review_code(self, issue_id: str, code_changes: dict[str, Any]) -> bool:
        """审查代码提交
        
        Args:
            issue_id: Issue ID
            code_changes: 代码更改信息
            
        Returns:
            是否通过审查
        """
        logger.info(f"👀 开始审查Issue: {issue_id}")
        
        # 获取 Issue 信息
        issues = await self.git_manager.get_open_issues()
        issue = next((i for i in issues if i["id"] == issue_id), None)
        if not issue:
            logger.error(f"❌ 未找到Issue: {issue_id}")
            return False
        
        logger.info(f"📋 审查Issue详情: {issue.get('title', 'Unknown')}")
        logger.info(f"📝 代码长度: {len(code_changes['code'])} 字符")
        
        # 显示代码预览
        code_lines = code_changes['code'].split('\n')
        logger.info(f"🔍 代码预览 (前5行):")
        for i, line in enumerate(code_lines[:5], 1):
            logger.info(f"  {i}: {line}")
        if len(code_lines) > 5:
            logger.info(f"  ... (还有 {len(code_lines) - 5} 行)")
        
        # 审查代码
        logger.info(f"🤖 开始LLM代码审查...")
        review_result = await self.llm_manager.review_code(issue, code_changes["code"])
        
        logger.info(f"📊 审查结果: {'通过' if review_result.get('approved', False) else '未通过'}")
        logger.info(f"💬 审查评论: {review_result.get('comments', 'No comments')}")
        
        if review_result.get("approved", False):
            # 更新 Issue 状态
            logger.info(f"✅ 更新Issue状态为completed...")
            await self.git_manager.update_issue_status(
                issue_id,
                "completed",
                code_changes["code"]
            )
            logger.info(f"🎉 Issue {issue_id} 通过审查并完成")
        else:
            # 更新 Issue 状态
            logger.info(f"❌ 更新Issue状态为open (需要重新实现)...")
            await self.git_manager.update_issue_status(
                issue_id,
                "open",
                code_changes["code"]
            )
            logger.info(f"🔄 Issue {issue_id} 未通过审查，需要重新实现")
            logger.info(f"📝 审查意见: {review_result['comments']}")
        
        return review_result.get("approved", False)
    
    async def monitor_repo(self) -> None:
        """监控代码库状态
        
        持续监控代码库，检查是否需要创建新的 Issue。
        同时提供用户交互界面，让用户可以输入新需求。
        """
        logger.info("🔍 开始监控代码库...")
        
        # 等待一下让系统完全启动
        await asyncio.sleep(2)
        
        # 显示醒目的用户交互提示
        print("\n" + "=" * 80)
        print("🎉 系统已启动完成！")
        print("💬 欢迎使用多代理编程系统!")
        print("📝 请描述你想要实现的功能，我会分析并创建对应的Issues")
        print("✨ 然后CoderAgent们会竞争抢夺这些Issues并实现代码")
        print("🚪 输入 'quit' 或 'exit' 退出系统")
        print("=" * 80)
        print()
        
        # 创建异步任务处理用户输入
        async def handle_user_input():
            """处理用户输入的异步任务"""
            import sys
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            def get_user_input_sync(prompt):
                """同步获取用户输入"""
                try:
                    return input(prompt)
                except (EOFError, KeyboardInterrupt):
                    return "quit"
            
            # 使用线程池执行器来处理同步输入
            executor = ThreadPoolExecutor(max_workers=1)
            
            while True:
                try:
                    # 使用更醒目的提示
                    print("\n" + "🔥" * 50)
                    print("💭 请输入你的需求描述:")
                    print("   例如: '添加用户登录功能'")
                    print("   例如: '实现文件上传接口'")
                    print("   例如: '创建数据库连接模块'")
                    print("🔥" * 50)
                    
                    # 在单独的线程中获取用户输入，避免阻塞异步事件循环
                    loop = asyncio.get_event_loop()
                    user_input = await loop.run_in_executor(
                        executor, 
                        get_user_input_sync, 
                        "👤 你的需求: "
                    )
                    
                    if user_input.lower().strip() in ['quit', 'exit', 'q']:
                        print("\n🎉 感谢使用多代理编程系统！")
                        print("👋 再见!")
                        executor.shutdown(wait=False)
                        return
                    
                    if user_input.strip():
                        print(f"\n🎯 收到用户需求: {user_input}")
                        print("🤖 正在分析需求并创建Issues...")
                        await self.analyze_requirements(user_input)
                        print("✅ 需求分析完成，已创建对应的Issues")
                        print("🔄 CoderAgent们将开始抢夺和实现这些Issues...")
                        print("⏳ 请稍等，查看实现进度...")
                    else:
                        print("⚠️ 请输入有效的需求描述")
                        
                except KeyboardInterrupt:
                    print("\n👋 接收到中断信号，退出...")
                    executor.shutdown(wait=False)
                    return
                except Exception as e:
                    logger.error(f"❌ 处理用户输入时出错: {e}")
                    # 等待一段时间避免无限循环
                    await asyncio.sleep(1)
        
        # 创建监控任务
        async def repo_monitoring():
            """仓库监控任务"""
            while True:
                try:
                    logger.debug("📡 检查代码库状态...")
                    # 检查是否有远程仓库，有的话才拉取最新代码
                    try:
                        if self.git_manager.repo.remotes:
                            logger.debug("🔄 拉取远程更改...")
                            await self.git_manager.pull_changes()
                        else:
                            logger.debug("💻 本地仓库模式，跳过拉取远程更改")
                    except Exception as e:
                        logger.debug(f"⚠️ 跳过拉取操作: {e}")
                
                    # 分析代码库状态
                    # TODO: 实现代码库状态分析
                    logger.debug("😴 监控休眠60秒...")
                    await asyncio.sleep(60)  # 每分钟检查一次
                except Exception as e:
                    logger.error(f"❌ 监控代码库时出错: {e}")
                    await asyncio.sleep(60)
        
        # 同时运行用户输入处理和仓库监控
        try:
            await asyncio.gather(
                handle_user_input(),
                repo_monitoring()
            )
        except Exception as e:
            logger.error(f"❌ 监控系统出错: {e}")
    
    async def review_pull_requests(self) -> None:
        """审查Pull Request
        
        持续审查开放的Pull Request。
        """
        if not self.collaboration_manager:
            logger.warning("⚠️ 未设置协作管理器，无法审查Pull Request")
            return
        
        logger.info("👀 开始审查Pull Requests...")
        while True:
            try:
                logger.debug("📋 获取开放的Pull Requests...")
                # 获取开放的Pull Request
                prs = await self.collaboration_manager.get_open_pull_requests()
                
                if prs:
                    logger.info(f"📝 发现 {len(prs)} 个开放的Pull Requests")
                
                for pr in prs:
                    logger.info(f"🔍 审查Pull Request: {pr.pr_id}")
                    logger.info(f"📋 PR标题: {pr.title}")
                    logger.info(f"👤 作者: {pr.author}")
                    logger.info(f"🌿 分支: {pr.branch_name}")
                    
                    # 审查代码
                    approved = True
                    comments = ""
                    
                    try:
                        # 使用LLM审查代码
                        for file_path, code_content in pr.code_changes.items():
                            logger.info(f"📁 审查文件: {file_path}")
                            
                            # 构造Issue信息用于审查
                            issue_info = {
                                "id": pr.issue_id,
                                "title": pr.title,
                                "description": pr.description
                            }
                            
                            review_result = await self.llm_manager.review_code(issue_info, code_content)
                            
                            if not review_result["approved"]:
                                approved = False
                                comments += f"文件 {file_path}: {review_result.get('comments', 'Code quality issues')}\n"
                            else:
                                logger.info(f"✅ 文件 {file_path} 审查通过")
                    
                    except Exception as e:
                        logger.error(f"❌ 审查PR {pr.pr_id} 时出错: {e}")
                        approved = False
                        comments = f"审查过程中出现错误: {str(e)}"
                    
                    # 提交审查结果
                    await self.collaboration_manager.review_pull_request(
                        pr.pr_id,
                        "commenter",
                        approved,
                        comments
                    )
                    
                    if approved:
                        logger.info(f"🎉 Pull Request {pr.pr_id} 审查通过并已合并")
                    else:
                        logger.info(f"❌ Pull Request {pr.pr_id} 审查未通过")
                        logger.info(f"💬 审查意见: {comments}")
                
                # 休眠一段时间再检查
                logger.debug("😴 PR审查休眠30秒...")
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ 审查Pull Requests时出错: {e}")
                await asyncio.sleep(30)
    
    async def review_issues(self) -> None:
        """审查 Issue
        
        持续审查开放的 Issue，检查代码提交。
        """
        logger.info("👀 开始审查Issues...")
        while True:
            try:
                logger.debug("📋 获取开放的Issues...")
                # 获取开放的 Issue
                issues = await self.git_manager.get_open_issues()
                
                if issues:
                    logger.info(f"📝 发现 {len(issues)} 个开放的Issues")
                
                for issue in issues:
                    logger.debug(f"🔍 检查Issue: {issue.get('title', 'Unknown')}")
                    if issue.get("code_submission"):
                        logger.info(f"💻 发现代码提交，开始审查Issue: {issue['id']}")
                        # 审查代码提交
                        await self.review_code(
                            issue["id"],
                            {"code": issue["code_submission"]}
                        )
                    else:
                        logger.debug(f"⏳ Issue {issue['id']} 还没有代码提交")
                else:
                    logger.debug("📭 没有发现开放的Issues")
                
                logger.debug("😴 审查休眠30秒...")
                await asyncio.sleep(30)  # 每30秒检查一次
            except Exception as e:
                logger.error(f"❌ 审查 Issue 时出错: {e}")
                await asyncio.sleep(30)
    
    async def sync_playground_code(self) -> None:
        """同步playground代码到所有agent仓库"""
        logger.info("🔄 开始代码同步任务...")
        while True:
            try:
                logger.debug("📡 检查playground更新...")
                
                # 检查playground是否有新提交
                try:
                    if self.git_manager.repo.remotes:
                        await self.git_manager.pull_changes()
                        logger.debug("✅ 已拉取playground最新更新")
                    else:
                        logger.debug("💻 本地仓库模式，跳过拉取")
                except Exception as e:
                    logger.debug(f"⚠️ 拉取playground更新失败: {e}")
                
                # 如果有协作管理器，同步到所有agent
                if self.collaboration_manager:
                    try:
                        await self.collaboration_manager.sync_all_agents()
                        logger.info("✅ 成功同步playground代码到所有agent")
                    except Exception as e:
                        logger.error(f"❌ 同步代码到agent失败: {e}")
                
                # 休眠一段时间再检查
                logger.debug("😴 代码同步休眠60秒...")
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ 代码同步任务出错: {e}")
                await asyncio.sleep(60)
    
    async def run(self) -> None:
        """运行评论员代理
        
        启动所有监控和审查任务。
        """
        logger.info("🚀 启动评论员代理")
        
        # 创建监控和审查任务
        logger.info("📡 创建监控任务...")
        monitor_task = asyncio.create_task(self.monitor_repo())
        logger.info("👀 创建Issue审查任务...")
        review_task = asyncio.create_task(self.review_issues())
        
        tasks = [monitor_task, review_task]
        
        # 如果有协作管理器，添加PR审查任务
        if self.collaboration_manager:
            logger.info("🔄 创建Pull Request审查任务...")
            pr_review_task = asyncio.create_task(self.review_pull_requests())
            tasks.append(pr_review_task)
            logger.info("✅ 启用Pull Request审查功能")
            
            # 添加代码同步任务
            logger.info("🔄 创建代码同步任务...")
            sync_task = asyncio.create_task(self.sync_playground_code())
            tasks.append(sync_task)
            logger.info("✅ 启用代码同步功能")
        else:
            logger.info("⚠️ 未启用Pull Request审查功能")
        
        try:
            logger.info("⚡ 评论员代理开始工作...")
            # 等待所有任务完成
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"❌ 评论员代理运行出错: {e}")
            # 取消所有任务
            for task in tasks:
                task.cancel() 