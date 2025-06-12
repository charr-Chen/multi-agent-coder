#!/usr/bin/env python3
"""
协作系统测试脚本

测试新的Pull Request协作机制
"""

import os
import json
import asyncio
import logging
from src.multi_agent_coder.git_utils import GitManager
from src.multi_agent_coder.llm_utils import LLMManager
from src.multi_agent_coder.collaboration import CollaborationManager
from src.multi_agent_coder.agents import CommenterAgent, CoderAgent
from git import Repo

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_collaboration_system():
    """测试协作系统"""
    try:
        logger.info("🚀 开始测试协作系统...")
        
        # 获取API密钥
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ 未设置 OPENAI_API_KEY 环境变量")
            return
        
        proxy_url = os.getenv("OPENAI_PROXY_URL")
        
        # 初始化LLM管理器
        llm_manager = LLMManager(api_key, proxy_url=proxy_url)
        
        # 设置测试仓库路径
        test_repo_path = "test_collaboration_repo"
        agent_repo_path = "test_agent_repo"
        
        # 清理旧的测试仓库
        import shutil
        for path in [test_repo_path, agent_repo_path]:
            if os.path.exists(path):
                shutil.rmtree(path)
        
        # 创建主仓库
        os.makedirs(test_repo_path)
        # 初始化Git仓库
        Repo.init(test_repo_path)
        main_git_manager = GitManager(test_repo_path)
        
        # 创建agent仓库
        os.makedirs(agent_repo_path)
        # 初始化Git仓库
        Repo.init(agent_repo_path)
        agent_git_manager = GitManager(agent_repo_path)
        
        # 创建协作管理器
        collaboration_manager = CollaborationManager(main_git_manager, llm_manager)
        collaboration_manager.register_agent_repo("test_coder", agent_git_manager)
        
        logger.info("✅ 协作管理器创建成功")
        
        # 创建测试Issue
        test_issue = await main_git_manager.create_issue(
            "创建简单计算器",
            "实现一个简单的计算器，支持加减乘除运算"
        )
        
        logger.info(f"✅ 创建测试Issue: {test_issue['id']}")
        
        # 模拟coder实现代码
        test_code = '''#!/usr/bin/env python3
"""
简单计算器
支持基本的四则运算
"""

class Calculator:
    """简单计算器类"""
    
    def add(self, a: float, b: float) -> float:
        """加法"""
        return a + b
    
    def subtract(self, a: float, b: float) -> float:
        """减法"""
        return a - b
    
    def multiply(self, a: float, b: float) -> float:
        """乘法"""
        return a * b
    
    def divide(self, a: float, b: float) -> float:
        """除法"""
        if b == 0:
            raise ValueError("除数不能为零")
        return a / b

def main():
    """主函数"""
    calc = Calculator()
    
    print("简单计算器")
    print("支持的操作: +, -, *, /")
    
    while True:
        try:
            expression = input("请输入表达式 (如: 1 + 2) 或 'quit' 退出: ")
            if expression.lower() == 'quit':
                break
            
            parts = expression.split()
            if len(parts) != 3:
                print("格式错误，请使用: 数字 操作符 数字")
                continue
            
            a, op, b = float(parts[0]), parts[1], float(parts[2])
            
            if op == '+':
                result = calc.add(a, b)
            elif op == '-':
                result = calc.subtract(a, b)
            elif op == '*':
                result = calc.multiply(a, b)
            elif op == '/':
                result = calc.divide(a, b)
            else:
                print("不支持的操作符")
                continue
            
            print(f"结果: {result}")
            
        except ValueError as e:
            print(f"错误: {e}")
        except Exception as e:
            print(f"未知错误: {e}")

if __name__ == "__main__":
    main()
'''
        
        # 创建Pull Request
        pr_id = await collaboration_manager.create_pull_request(
            issue_id=test_issue['id'],
            author="test_coder",
            title="实现简单计算器",
            description="实现了一个支持四则运算的简单计算器类",
            code_changes={f"src/{test_issue['id']}.py": test_code}
        )
        
        logger.info(f"✅ 创建Pull Request: {pr_id}")
        
        # 获取开放的PR
        open_prs = await collaboration_manager.get_open_pull_requests()
        logger.info(f"📋 发现 {len(open_prs)} 个开放的Pull Request")
        
        for pr in open_prs:
            logger.info(f"🔍 PR详情:")
            logger.info(f"  - ID: {pr.pr_id}")
            logger.info(f"  - 标题: {pr.title}")
            logger.info(f"  - 作者: {pr.author}")
            logger.info(f"  - 状态: {pr.status}")
            logger.info(f"  - 文件数: {len(pr.code_changes)}")
        
        # 模拟审核通过
        logger.info("🔍 开始审核Pull Request...")
        success = await collaboration_manager.review_pull_request(
            pr_id,
            "commenter",
            True,  # 审核通过
            "代码质量良好，功能完整，通过审核"
        )
        
        if success:
            logger.info("✅ Pull Request审核通过并已合并")
        else:
            logger.error("❌ Pull Request审核失败")
        
        # 检查主仓库中的文件
        merged_file_path = os.path.join(test_repo_path, f"src/{test_issue['id']}.py")
        if os.path.exists(merged_file_path):
            logger.info("✅ 代码已成功合并到主仓库")
            with open(merged_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.info(f"📄 合并的代码长度: {len(content)} 字符")
        else:
            logger.error("❌ 代码未能合并到主仓库")
        
        # 检查PR状态
        pr = await collaboration_manager.get_pr_by_id(pr_id)
        if pr:
            logger.info(f"📊 PR最终状态: {pr.status}")
            if pr.merge_commit:
                logger.info(f"🔗 合并提交: {pr.merge_commit}")
        
        logger.info("🎉 协作系统测试完成!")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        logger.error(f"🔍 错误详情:\n{traceback.format_exc()}")
    
    finally:
        # 清理测试文件
        logger.info("🧹 清理测试文件...")
        import shutil
        for path in [test_repo_path, agent_repo_path]:
            if os.path.exists(path):
                shutil.rmtree(path)
        logger.info("✅ 清理完成")

async def test_multi_agent_collaboration():
    """测试多agent协作"""
    logger.info("🤝 开始测试多agent协作...")
    
    try:
        # 获取API密钥
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ 未设置 OPENAI_API_KEY 环境变量")
            return
        
        proxy_url = os.getenv("OPENAI_PROXY_URL")
        llm_manager = LLMManager(api_key, proxy_url=proxy_url)
        
        # 设置测试仓库
        main_repo_path = "test_main_repo"
        agent1_repo_path = "test_agent1_repo"
        agent2_repo_path = "test_agent2_repo"
        
        # 清理旧仓库
        import shutil
        for path in [main_repo_path, agent1_repo_path, agent2_repo_path]:
            if os.path.exists(path):
                shutil.rmtree(path)
        
        # 创建仓库
        for path in [main_repo_path, agent1_repo_path, agent2_repo_path]:
            os.makedirs(path)
            # 初始化Git仓库
            Repo.init(path)
        
        main_git = GitManager(main_repo_path)
        agent1_git = GitManager(agent1_repo_path)
        agent2_git = GitManager(agent2_repo_path)
        
        # 创建协作管理器
        collaboration_manager = CollaborationManager(main_git, llm_manager)
        collaboration_manager.register_agent_repo("agent1", agent1_git)
        collaboration_manager.register_agent_repo("agent2", agent2_git)
        
        # 创建commenter和coders
        commenter = CommenterAgent(main_git, llm_manager)
        commenter.set_collaboration_manager(collaboration_manager)
        
        coder1 = CoderAgent(agent1_git, llm_manager, "agent1")
        coder1.set_collaboration_manager(collaboration_manager)
        coder1.set_playground_git_manager(main_git)
        
        coder2 = CoderAgent(agent2_git, llm_manager, "agent2")
        coder2.set_collaboration_manager(collaboration_manager)
        coder2.set_playground_git_manager(main_git)
        
        # 创建多个Issues
        issues = []
        issue_descriptions = [
            ("创建文件管理器", "实现一个简单的文件管理器，支持文件的创建、删除、重命名操作"),
            ("创建贪吃蛇游戏", "使用Python实现一个简单的贪吃蛇游戏"),
            ("创建待办事项管理器", "实现一个命令行的待办事项管理工具")
        ]
        
        for title, description in issue_descriptions:
            issue = await main_git.create_issue(title, description)
            issues.append(issue)
            logger.info(f"✅ 创建Issue: {title}")
        
        logger.info(f"📋 创建了 {len(issues)} 个Issues")
        
        # 模拟agent抢夺和实现Issues
        logger.info("🎯 模拟agent抢夺Issues...")
        
        # Agent1抢夺第一个Issue
        success1 = await main_git.assign_issue(issues[0]['id'], "agent1")
        if success1:
            logger.info(f"✅ Agent1抢夺Issue: {issues[0]['title']}")
        
        # Agent2抢夺第二个Issue
        success2 = await main_git.assign_issue(issues[1]['id'], "agent2")
        if success2:
            logger.info(f"✅ Agent2抢夺Issue: {issues[1]['title']}")
        
        # 模拟实现代码（简化版本，实际会调用LLM）
        simple_code1 = '''#!/usr/bin/env python3
"""简单文件管理器"""
import os

class FileManager:
    def create_file(self, filename, content=""):
        with open(filename, 'w') as f:
            f.write(content)
        print(f"文件 {filename} 创建成功")
    
    def delete_file(self, filename):
        if os.path.exists(filename):
            os.remove(filename)
            print(f"文件 {filename} 删除成功")
        else:
            print(f"文件 {filename} 不存在")

if __name__ == "__main__":
    fm = FileManager()
    print("简单文件管理器")
'''
        
        simple_code2 = '''#!/usr/bin/env python3
"""简单贪吃蛇游戏"""
import random

class SnakeGame:
    def __init__(self):
        self.snake = [(5, 5)]
        self.food = (10, 10)
        self.direction = (1, 0)
    
    def move(self):
        head = self.snake[0]
        new_head = (head[0] + self.direction[0], head[1] + self.direction[1])
        self.snake.insert(0, new_head)
        
        if new_head == self.food:
            self.food = (random.randint(0, 20), random.randint(0, 20))
        else:
            self.snake.pop()
    
    def play(self):
        print("贪吃蛇游戏开始!")

if __name__ == "__main__":
    game = SnakeGame()
    game.play()
'''
        
        # 创建Pull Requests
        pr1_id = await collaboration_manager.create_pull_request(
            issue_id=issues[0]['id'],
            author="agent1",
            title="实现文件管理器",
            description="实现了基本的文件创建和删除功能",
            code_changes={f"src/{issues[0]['id']}.py": simple_code1}
        )
        
        pr2_id = await collaboration_manager.create_pull_request(
            issue_id=issues[1]['id'],
            author="agent2",
            title="实现贪吃蛇游戏",
            description="实现了贪吃蛇游戏的基本框架",
            code_changes={f"src/{issues[1]['id']}.py": simple_code2}
        )
        
        logger.info(f"🔄 创建了2个Pull Requests: {pr1_id}, {pr2_id}")
        
        # 模拟审核
        logger.info("🔍 开始审核Pull Requests...")
        
        # 审核PR1 - 通过
        await collaboration_manager.review_pull_request(
            pr1_id, "commenter", True, "文件管理器实现良好"
        )
        
        # 审核PR2 - 通过
        await collaboration_manager.review_pull_request(
            pr2_id, "commenter", True, "贪吃蛇游戏框架完整"
        )
        
        # 检查合并结果
        merged_files = []
        for issue in issues[:2]:
            file_path = os.path.join(main_repo_path, f"src/{issue['id']}.py")
            if os.path.exists(file_path):
                merged_files.append(file_path)
        
        logger.info(f"✅ 成功合并 {len(merged_files)} 个文件到主仓库")
        
        # 模拟同步
        logger.info("🔄 测试代码同步...")
        await collaboration_manager.sync_all_agents()
        
        logger.info("🎉 多agent协作测试完成!")
        
    except Exception as e:
        logger.error(f"❌ 多agent协作测试失败: {e}")
        import traceback
        logger.error(f"🔍 错误详情:\n{traceback.format_exc()}")
    
    finally:
        # 清理
        logger.info("🧹 清理测试文件...")
        import shutil
        for path in [main_repo_path, agent1_repo_path, agent2_repo_path]:
            if os.path.exists(path):
                shutil.rmtree(path)

async def main():
    """主函数"""
    logger.info("🚀 开始协作系统测试套件...")
    
    # 测试基本协作功能
    await test_collaboration_system()
    
    logger.info("=" * 50)
    
    # 测试多agent协作
    await test_multi_agent_collaboration()
    
    logger.info("🎉 所有测试完成!")

if __name__ == "__main__":
    asyncio.run(main()) 