"""
运行脚本
用于启动多智能体编码系统
"""

import os
import logging
import asyncio
from src.multi_agent_coder.git_utils import GitManager
from src.multi_agent_coder.llm_utils import LLMManager
from src.multi_agent_coder.agents import CommenterAgent, CoderAgent
from src.multi_agent_coder.config import get_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """主函数"""
    try:
        # 获取配置
        config = get_config()
        
        # 获取仓库路径
        repo_path = config["system"]["repo_path"]
        logger.info(f"使用仓库路径: {repo_path}")
        
        # 初始化 Git 管理器
        git_manager = GitManager(repo_path)
        
        # 获取 API 密钥
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("未设置 OPENAI_API_KEY 环境变量")
        
        # 初始化 LLM 管理器
        llm_manager = LLMManager(api_key)
        
        # 创建评论员代理
        commenter = CommenterAgent(git_manager, llm_manager)
        
        # 创建编码员代理
        coders = [
            CoderAgent(git_manager, llm_manager, f"coder_{i}")
            for i in range(config["system"]["num_coders"])
        ]
        
        # 启动所有代理
        tasks = [
            commenter.run(),
            *[coder.run() for coder in coders]
        ]
        
        # 等待所有任务完成
        await asyncio.gather(*tasks)
        
    except Exception as e:
        logger.error(f"运行出错: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 