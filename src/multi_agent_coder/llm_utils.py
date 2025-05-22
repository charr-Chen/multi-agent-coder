"""LLM 工具模块

提供与 OpenAI API 的交互功能。
"""

import logging
from typing import Dict, Any, List
import openai
from .config import LLM_CONFIG

logger = logging.getLogger(__name__)

class LLMManager:
    """LLM 管理器"""
    
    def __init__(self, api_key: str):
        """初始化 LLM 管理器
        
        Args:
            api_key: OpenAI API 密钥
        """
        # 设置 API 密钥
        openai.api_key = api_key
        logger.info("初始化 LLM 管理器")
    
    async def analyze_requirements(self, requirements: str) -> List[Dict[str, str]]:
        """分析用户需求，生成 Issue 列表
        
        Args:
            requirements: 用户需求描述
            
        Returns:
            Issue 列表
        """
        try:
            response = await openai.ChatCompletion.acreate(
                model=LLM_CONFIG["model"],
                messages=[
                    {"role": "system", "content": "你是一个需求分析师，负责将用户需求分解为具体的开发任务。"},
                    {"role": "user", "content": f"请将以下需求分解为具体的开发任务，每个任务包含标题和描述：\n\n{requirements}"}
                ],
                temperature=LLM_CONFIG["temperature"],
                max_tokens=LLM_CONFIG["max_tokens"]
            )
            
            # 解析响应，生成 Issue 列表
            issues = []
            content = response.choices[0].message.content
            # TODO: 解析响应内容，生成 Issue 列表
            logger.info("分析用户需求")
            return issues
        except Exception as e:
            logger.error(f"分析需求时出错: {e}")
            return []
    
    async def review_code(self, issue: Dict[str, Any], code: str) -> Dict[str, Any]:
        """审查代码提交
        
        Args:
            issue: Issue 信息
            code: 提交的代码
            
        Returns:
            审查结果
        """
        try:
            response = await openai.ChatCompletion.acreate(
                model=LLM_CONFIG["model"],
                messages=[
                    {"role": "system", "content": "你是一个代码审查员，负责审查代码质量和功能完整性。"},
                    {"role": "user", "content": f"""请审查以下代码：

Issue: {issue['title']}
描述: {issue['description']}

代码:
```python
{code}
```

请提供以下信息：
1. 代码是否满足 Issue 要求
2. 代码质量评估
3. 改进建议
4. 是否通过审查"""}
                ],
                temperature=LLM_CONFIG["temperature"],
                max_tokens=LLM_CONFIG["max_tokens"]
            )
            
            # 解析响应
            content = response.choices[0].message.content
            # TODO: 解析响应内容，生成审查结果
            logger.info(f"审查 Issue {issue['id']} 的代码")
            return {"approved": True, "comments": content}
        except Exception as e:
            logger.error(f"审查代码时出错: {e}")
            return {"approved": False, "comments": str(e)}
    
    async def generate_code(self, issue: Dict[str, Any]) -> str:
        """生成代码实现
        
        Args:
            issue: Issue 信息
            
        Returns:
            生成的代码
        """
        try:
            response = await openai.ChatCompletion.acreate(
                model=LLM_CONFIG["model"],
                messages=[
                    {"role": "system", "content": "你是一个专业的程序员，负责实现代码功能。"},
                    {"role": "user", "content": f"""请实现以下功能：

Issue: {issue['title']}
描述: {issue['description']}

请生成完整的代码实现，包括必要的注释和文档。"""}
                ],
                temperature=LLM_CONFIG["temperature"],
                max_tokens=LLM_CONFIG["max_tokens"]
            )
            
            # 获取生成的代码
            code = response.choices[0].message.content
            logger.info(f"为 Issue {issue['id']} 生成代码")
            return code
        except Exception as e:
            logger.error(f"生成代码时出错: {e}")
            return "" 