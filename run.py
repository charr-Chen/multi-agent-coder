"""
运行脚本
用于启动多智能体编码系统
"""

import os
import logging
import asyncio
from src.multi_agent_coder.git_utils import GitManager
from src.multi_agent_coder.multi_repo_manager import MultiRepoManager
from src.multi_agent_coder.llm_utils import LLMManager
from src.multi_agent_coder.agents import CommenterAgent, CoderAgent
from src.multi_agent_coder.config import get_config

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """主函数"""
    try:
        # 获取配置
        config = get_config()
        
        # 获取 API 密钥
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("未设置 OPENAI_API_KEY 环境变量")
        
        # 获取代理配置（可选）
        proxy_url = os.getenv("OPENAI_PROXY_URL")
        if proxy_url:
            logger.info(f"使用代理: {proxy_url}")
        
        # 初始化 LLM 管理器
        llm_manager = LLMManager(api_key, proxy_url=proxy_url)
        
        # 检查是否使用多仓库模式
        if config["system"]["use_separate_repos"]:
            logger.info("使用多仓库模式")
            
            # 初始化多仓库管理器
            multi_repo_manager = MultiRepoManager(
                config["system"]["playground_repo"],
                config["system"]["agent_repos_dir"]
            )
            
            # 设置playground仓库
            playground_git_manager = await multi_repo_manager.setup_playground_repo()
            
            # 🆕 关键步骤：同步主项目的Issues到playground仓库
            logger.info("🔄 同步主项目Issues到playground仓库...")
            try:
                # 读取主项目的Issues
                main_issues_file = ".issues.json"
                if os.path.exists(main_issues_file):
                    import json
                    with open(main_issues_file, 'r', encoding='utf-8') as f:
                        main_issues_data = json.load(f)
                    
                    # 写入到playground仓库
                    playground_issues_file = os.path.join(playground_git_manager.repo_path, ".issues.json")
                    with open(playground_issues_file, 'w', encoding='utf-8') as f:
                        json.dump(main_issues_data, f, indent=2, ensure_ascii=False)
                    
                    # 提交到playground仓库
                    await playground_git_manager.commit_changes(
                        "同步主项目Issues到playground",
                        [".issues.json"]
                    )
                    
                    logger.info(f"✅ 成功同步 {len(main_issues_data.get('issues', []))} 个Issues到playground仓库")
                else:
                    logger.warning("❌ 主项目的.issues.json文件不存在")
            except Exception as e:
                logger.error(f"❌ 同步Issues到playground失败: {e}")
            
            # 创建评论员代理（使用playground仓库）
            commenter = CommenterAgent(playground_git_manager, llm_manager)
            
            # 创建编码员代理（每个使用独立仓库）
            coders = []
            for i in range(config["system"]["num_coders"]):
                agent_id = f"coder_{i}"
                # 为每个coder设置独立仓库
                agent_git_manager = await multi_repo_manager.setup_agent_repo(agent_id)
                coder = CoderAgent(agent_git_manager, llm_manager, agent_id)
                # 设置playground仓库管理器，用于访问Issues
                coder.set_playground_git_manager(playground_git_manager)
                # 将多仓库管理器传递给coder，用于同步工作
                coder.multi_repo_manager = multi_repo_manager
                coders.append(coder)
            
            logger.info(f"创建了 {len(coders)} 个编码员代理，每个都有独立仓库")
            
        else:
            logger.info("使用单仓库模式")
            
            # 获取仓库路径
            repo_path = config["system"]["repo_path"]
            logger.info(f"使用仓库路径: {repo_path}")
            
            # 初始化 Git 管理器
            git_manager = GitManager(repo_path)
            
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