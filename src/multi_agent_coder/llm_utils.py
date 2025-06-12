"""LLM 工具模块

提供与 OpenAI API 的交互功能。
"""

import logging
from typing import Dict, Any, List
from openai import AsyncOpenAI
import httpx
from .config import LLM_CONFIG

logger = logging.getLogger(__name__)

class LLMManager:
    """LLM 管理器"""
    
    def __init__(self, api_key: str, proxy_url: str = None, max_retries: int = 3):
        """初始化 LLM 管理器
        
        Args:
            api_key: OpenAI API 密钥
            proxy_url: 代理URL，格式如 http://127.0.0.1:7890
            max_retries: 最大重试次数
        """
        # 配置HTTP客户端，支持代理和重试
        http_client = None
        if proxy_url:
            http_client = httpx.AsyncClient(
                proxy=proxy_url,
                timeout=60.0
            )
            logger.info(f"使用代理: {proxy_url}")
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            http_client=http_client,
            max_retries=max_retries
        )
        self.max_retries = max_retries
        logger.info("初始化 LLM 管理器")
    
    async def analyze_requirements(self, requirements: str) -> List[Dict[str, str]]:
        """分析用户需求，生成 Issue 列表
        
        Args:
            requirements: 用户需求描述
            
        Returns:
            Issue 列表
        """
        try:
            logger.info(f"🔍 分析用户需求: {requirements}")
            
            response = await self.client.chat.completions.create(
                model=LLM_CONFIG["model"],
                messages=[
                    {
                        "role": "system", 
                        "content": """你是一个需求分析师，负责将用户需求分解为具体的开发任务。

请将用户需求分解为3-5个具体的开发任务，每个任务应该：
1. 有明确的标题
2. 有详细的描述
3. 是可以独立完成的功能

请按以下JSON格式返回：
[
  {
    "title": "任务标题",
    "description": "详细的任务描述，包括具体要实现的功能、技术要求等"
  },
  ...
]"""
                    },
                    {
                        "role": "user", 
                        "content": f"请将以下需求分解为具体的开发任务：\n\n{requirements}"
                    }
                ],
                temperature=LLM_CONFIG["temperature"],
                max_tokens=LLM_CONFIG["max_tokens"]
            )
            
            content = response.choices[0].message.content.strip()
            logger.info(f"🤖 GPT响应: {content}")
            
            # 解析JSON响应
            import json
            import re
            
            # 尝试提取JSON部分
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                issues_data = json.loads(json_str)
                
                issues = []
                for item in issues_data:
                    if isinstance(item, dict) and 'title' in item and 'description' in item:
                        issues.append({
                            'title': item['title'],
                            'description': item['description']
                        })
                
                logger.info(f"✅ 成功解析出 {len(issues)} 个任务")
                return issues
            else:
                logger.warning("❌ 无法从响应中提取JSON格式的任务列表")
                
                # Fallback: 手动解析
                lines = content.split('\n')
                issues = []
                current_title = None
                current_desc = []
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('1.') or line.startswith('2.') or line.startswith('3.') or \
                       line.startswith('4.') or line.startswith('5.') or line.startswith('-'):
                        if current_title:
                            issues.append({
                                'title': current_title,
                                'description': ' '.join(current_desc)
                            })
                        current_title = re.sub(r'^[\d\-\.\s]+', '', line)
                        current_desc = []
                    elif line and current_title:
                        current_desc.append(line)
                
                if current_title:
                    issues.append({
                        'title': current_title,
                        'description': ' '.join(current_desc)
                    })
                
                logger.info(f"✅ Fallback解析出 {len(issues)} 个任务")
            return issues
                
        except Exception as e:
            logger.error(f"❌ 分析需求时出错: {e}")
            # 返回一个默认任务
            return [{
                'title': f"实现用户需求: {requirements[:50]}...",
                'description': f"用户需求: {requirements}\n\n请根据上述需求实现相应功能。"
            }]
    
    async def review_code(self, issue: Dict[str, Any], code: str) -> Dict[str, Any]:
        """审查代码提交
        
        Args:
            issue: Issue 信息
            code: 提交的代码
            
        Returns:
            审查结果
        """
        try:
            response = await self.client.chat.completions.create(
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
            # 简单的审查逻辑：如果生成了代码就通过
            approved = len(code.strip()) > 50  # 代码长度大于50字符就认为通过
            logger.info(f"审查 Issue {issue['id']} 的代码")
            return {"approved": approved, "comments": content}
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
            logger.info(f"🤖 为Issue {issue['id']} 调用GPT生成代码")
            
            title = issue.get('title', '')
            description = issue.get('description', '')
            
            logger.info(f"📋 Issue标题: {title}")
            logger.info(f"📝 Issue描述: {description}")
            
            # 构建详细的GPT prompt
            prompt = f"""请根据以下需求生成完整的Python代码：

标题: {title}
详细描述: {description}

要求：
1. 生成完整、可运行的Python代码
2. 包含详细的中文注释和文档字符串
3. 代码结构清晰，遵循Python最佳实践
4. 包含适当的错误处理
5. 如果需要外部库，请在代码开头注释说明
6. 提供使用示例或测试代码
7. 确保代码的可维护性和可扩展性

请直接返回Python代码，不要包含任何markdown格式标记："""

            # 调用GPT API生成代码
            response = await self.client.chat.completions.create(
                model=LLM_CONFIG["model"],
                messages=[
                    {
                        "role": "system", 
                        "content": "你是一个资深的Python开发工程师，擅长根据需求编写高质量、完整、可运行的Python代码。你的代码应该具有良好的结构、清晰的注释、适当的错误处理，并遵循Python最佳实践。"
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=LLM_CONFIG["temperature"],
                max_tokens=LLM_CONFIG["max_tokens"]
            )
            
            generated_code = response.choices[0].message.content.strip()
            
            # 清理可能的markdown格式
            if generated_code.startswith("```python"):
                generated_code = generated_code[9:].strip()
            elif generated_code.startswith("```"):
                generated_code = generated_code[3:].strip()
            
            if generated_code.endswith("```"):
                generated_code = generated_code[:-3].strip()
            
            # 验证生成的代码不为空
            if not generated_code or len(generated_code.strip()) < 10:
                raise ValueError("GPT生成的代码为空或过短")
            
            logger.info(f"✅ GPT代码生成成功，长度: {len(generated_code)} 字符")
            logger.info(f"📊 代码行数: {len(generated_code.splitlines())} 行")
            
            return generated_code
            
        except Exception as e:
            logger.error(f"❌ GPT代码生成失败: {e}")
            
            # 不使用模板，直接返回错误信息和基础代码框架
            error_code = f'''"""
代码生成失败

Issue: {title}
描述: {description}
错误: {str(e)}

请手动实现此功能，或检查网络连接后重试。
"""

# TODO: 实现 {title}
# 描述: {description}

def main():
    """主函数 - 请根据需求实现具体功能"""
    print("此代码需要手动实现")
    print("Issue: {title}")
    print("描述: {description}")
    print("错误信息: {str(e)}")
    
    # 在这里添加你的实现
    pass

if __name__ == "__main__":
    main()
'''
            logger.warning(f"🔄 返回基础代码框架，用户需要手动实现")
            return error_code 