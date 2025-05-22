"""配置文件

包含系统配置和 LLM 配置。
"""

import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载环境变量
env_path = os.path.join(os.getcwd(), '.env')
logger.info(f"尝试加载环境变量文件: {env_path}")
load_dotenv(env_path)

# 检查 API 密钥
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    logger.info("成功加载 OPENAI_API_KEY")
else:
    logger.error("未找到 OPENAI_API_KEY")

# LLM 配置
LLM_CONFIG = {
    "model": os.getenv("OPENAI_MODEL", "gpt-4"),
    "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
    "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "2000")),
}

# 系统配置
SYSTEM_CONFIG = {
    "repo_path": os.getenv("REPO_PATH", os.getcwd()),
    "num_coders": int(os.getenv("NUM_CODERS", "3")),
    "check_interval": int(os.getenv("CHECK_INTERVAL", "60")),  # 秒
    "review_interval": int(os.getenv("REVIEW_INTERVAL", "30")),  # 秒
    "work_interval": int(os.getenv("WORK_INTERVAL", "10")),  # 秒
}

# 代理配置
AGENT_CONFIG = {
    "commenter": {
        "name": "Commenter",
        "role": "负责创建任务、审查代码提交和管理 Issue",
        "system_prompt": """你是一个代码审查员，负责：
1. 分析用户需求并创建合适的 Issue
2. 审查代码提交，确保代码质量和功能完整性
3. 监控代码库状态，及时发现问题
4. 与评论员代理协作，确保项目顺利进行""",
    },
    "coder": {
        "name": "Coder",
        "role": "负责实现代码、提交更改和处理冲突",
        "system_prompt": """你是一个专业的程序员，负责：
1. 实现 Issue 中描述的功能
2. 编写高质量的代码
3. 处理代码冲突
4. 与评论员代理协作，确保代码符合要求""",
    },
}

def get_config() -> Dict[str, Any]:
    """获取完整配置
    
    Returns:
        配置字典
    """
    return {
        "llm": LLM_CONFIG,
        "system": SYSTEM_CONFIG,
        "agent": AGENT_CONFIG,
    } 