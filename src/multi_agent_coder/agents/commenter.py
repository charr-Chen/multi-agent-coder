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
        
        logger.info(f"📊 审查结果: {'通过' if review_result['approved'] else '未通过'}")
        logger.info(f"💬 审查评论: {review_result.get('comments', 'No comments')}")
        
        if review_result["approved"]:
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
        
        return review_result["approved"]
    
    async def monitor_repo(self) -> None:
        """监控代码库状态
        
        持续监控代码库，检查是否需要创建新的 Issue。
        同时提供用户交互界面，让用户可以输入新需求。
        """
        logger.info("🔍 开始监控代码库...")
        logger.info("💬 欢迎使用多代理编码系统!")
        logger.info("📝 你可以随时输入需求，我会分析并创建对应的Issues")
        logger.info("✨ 输入格式：直接描述你想要实现的功能")
        logger.info("🚪 输入 'quit' 或 'exit' 退出系统")
        logger.info("=" * 50)
        
        # 创建异步任务处理用户输入
        async def handle_user_input():
            """处理用户输入的异步任务"""
            import aioconsole
            while True:
                try:
                    logger.info("💭 请输入你的需求 (输入 'quit' 退出):")
                    user_input = await aioconsole.ainput("👤 需求: ")
                    
                    if user_input.lower().strip() in ['quit', 'exit', 'q']:
                        logger.info("👋 感谢使用，再见!")
                        return
                    
                    if user_input.strip():
                        logger.info(f"🎯 收到用户需求: {user_input}")
                        await self.analyze_requirements(user_input)
                    else:
                        logger.info("⚠️ 请输入有效的需求描述")
                        
                except KeyboardInterrupt:
                    logger.info("👋 接收到中断信号，退出...")
                    return
                except Exception as e:
                    logger.error(f"❌ 处理用户输入时出错: {e}")
        
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
    
    async def run(self) -> None:
        """运行评论员代理
        
        启动所有监控和审查任务。
        """
        logger.info("🚀 启动评论员代理")
        
        # 创建监控和审查任务
        logger.info("📡 创建监控任务...")
        monitor_task = asyncio.create_task(self.monitor_repo())
        logger.info("👀 创建审查任务...")
        review_task = asyncio.create_task(self.review_issues())
        
        try:
            logger.info("⚡ 评论员代理开始工作...")
            # 等待任务完成
            await asyncio.gather(monitor_task, review_task)
        except Exception as e:
            logger.error(f"❌ 评论员代理运行出错: {e}")
            # 取消所有任务
            monitor_task.cancel()
            review_task.cancel() 