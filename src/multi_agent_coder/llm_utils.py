"""LLM 工具模块

提供与 OpenAI API 的交互功能，支持灵活的prompt驱动任务执行。
"""

import os
import json
import logging
import asyncio
import re
from typing import Any, Optional, Dict, List, Union
from openai import AsyncOpenAI
import httpx
from .config import LLM_CONFIG

logger = logging.getLogger(__name__)

class LLMManager:
    """LLM 管理器 - 支持灵活的prompt驱动任务执行"""
    
    def __init__(self, api_key: str, proxy_url: str = None, max_retries: int = 3):
        """初始化 LLM 管理器
        
        Args:
            api_key: OpenAI API 密钥
            proxy_url: 代理URL，格式如 http://127.0.0.1:7890
            max_retries: 最大重试次数
        """
        # 配置HTTP客户端，支持代理和重试
        if proxy_url:
            http_client = httpx.AsyncClient(
                proxy=proxy_url,
                timeout=60.0
            )
            logger.info(f"使用代理: {proxy_url}")
        else:
            # 即使没有代理也要创建HTTP客户端，确保连接稳定性
            http_client = httpx.AsyncClient(
                timeout=60.0
            )
            logger.info("使用直接连接（无代理）")
        
        self.client = AsyncOpenAI(
            api_key=api_key,
            http_client=http_client,
            max_retries=max_retries
        )
        self.max_retries = max_retries
        logger.info("初始化 LLM 管理器")
    
    async def execute_task(self, task_type: str, context: Dict[str, Any], 
                          custom_prompt: str = None, **kwargs) -> Any:
        """执行通用任务
        
        Args:
            task_type: 任务类型 (analyze, generate, review, plan, etc.)
            context: 任务上下文
            custom_prompt: 自定义prompt
            **kwargs: 其他参数
            
        Returns:
            任务执行结果
        """
        try:
            # 根据任务类型选择prompt模板
            if custom_prompt:
                prompt = custom_prompt
            else:
                prompt = self._get_task_prompt(task_type, context, **kwargs)
            
            # 执行LLM调用
            response = await self._call_llm(prompt, context.get('temperature', 0.7))
            
            # 根据任务类型处理响应
            return self._process_response(task_type, response, context)
            
        except Exception as e:
            logger.error(f"执行任务 {task_type} 失败: {e}")
            return self._get_fallback_result(task_type, context)
    
    async def _call_llm(self, prompt: str, temperature: float = 0.7) -> str:
        """调用LLM API"""
        # 添加详细的prompt日志
        logger.info(f"🤖 LLM调用开始")
        logger.info(f"📊 参数: model={LLM_CONFIG['model']}, temperature={temperature}, max_tokens={LLM_CONFIG['max_tokens']}")
        logger.info(f"📝 Prompt长度: {len(prompt)}字符")
        logger.info(f"=" * 60)
        logger.info(f"📋 完整Prompt内容:")
        logger.info(prompt)
        logger.info(f"=" * 60)
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"🔄 LLM调用尝试 {attempt + 1}/{self.max_retries + 1}")
                response = await self.client.chat.completions.create(
                    model=LLM_CONFIG["model"],
                    messages=[
                        {"role": "system", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=LLM_CONFIG["max_tokens"]
                )
                
                content = response.choices[0].message.content.strip()
                logger.info(f"✅ LLM响应成功，内容长度: {len(content)}字符")
                logger.info(f"📋 LLM完整响应:")
                logger.info(f"=" * 60)
                logger.info(content)
                logger.info(f"=" * 60)
                return content
                
            except Exception as e:
                logger.error(f"LLM调用失败 (尝试 {attempt + 1}/{self.max_retries + 1}): {e}")
                if attempt < self.max_retries:
                    logger.info(f"等待 {2 ** attempt} 秒后重试...")
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                else:
                    logger.error(f"LLM调用最终失败，已重试 {self.max_retries} 次")
                    raise
    
    def _get_task_prompt(self, task_type: str, context: Dict[str, Any], **kwargs) -> str:
        """根据任务类型生成prompt"""
        prompts = {
            "analyze_requirements": self._get_requirements_analysis_prompt,
            "review_code": self._get_code_review_prompt,
            "implement_issue": self._get_implement_issue_prompt,
            "custom": lambda ctx, **kw: ctx.get('prompt', '请完成指定任务')
        }
        
        prompt_func = prompts.get(task_type, prompts["custom"])
        return prompt_func(context, **kwargs)
    
    def _get_requirements_analysis_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """需求分析prompt"""
        requirements = context.get('requirements', '')
        return f"""你是一个资深的需求分析师和系统架构师。

请深入分析以下用户需求，并将其分解为具体的开发任务：

用户需求：
{requirements}

请分析需求并创建具体的开发任务。每个任务应该包含：
1. 任务标题：简洁明了的任务名称
2. 任务描述：详细的功能描述和实现要求

请用自然语言回答，格式如下：

任务1：
标题：[任务标题]
描述：[详细描述]

任务2：
标题：[任务标题]
描述：[详细描述]

...

请确保任务分解合理、具体，便于开发人员理解和实现。"""
    
    def _get_code_review_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """代码审查prompt"""
        code = context.get('code', '')
        issue = context.get('issue', {})
        
        return f"""你是一个资深的代码审查员。

请审查以下代码：

Issue:
标题: {issue.get('title', '')}
描述: {issue.get('description', '')}

代码:
```python
{code}
```

请用自然语言回答，格式如下：

审查结果：[通过/不通过]

总体评分：[1-10分]

是否满足需求：[是/否]

代码质量评估：
- 可读性：[评分] - [评价]
- 可维护性：[评分] - [评价]
- 性能：[评分] - [评价]
- 安全性：[评分] - [评价]

优点：
- [优点1]
- [优点2]

问题：
- [问题1] - 严重程度：[高/中/低] - 建议：[改进建议]
- [问题2] - 严重程度：[高/中/低] - 建议：[改进建议]

建议：
- [建议1]
- [建议2]

总体意见：
[详细的审查意见和评论]

请确保审查全面、客观，重点关注代码质量、功能完整性和最佳实践。"""
    
    def _get_implement_issue_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """实现Issue的prompt"""
        issue = context.get('issue', {})
        recent_thoughts = context.get('recent_thoughts', [])
        
        # 格式化历史思考链（使用纯文本格式）
        thoughts_text = ""
        if recent_thoughts:
            thoughts_text = "\n".join([
                f"- {thought.context if hasattr(thought, 'context') else str(thought)}" 
                for thought in recent_thoughts[-5:]  # 只显示最近5条
            ])
        else:
            thoughts_text = "暂无历史思考记录"
        
        return f"""你是一个多能的AI编码员。请根据以下Issue和历史思考链，独立完成所有开发任务。

【Issue详情】:
标题: {issue.get('title', '')}
描述: {issue.get('description', '')}

【历史思考链】:
{thoughts_text}

【任务要求】:
1. 深入理解Issue需求
2. 设计合适的实现方案
3. 编写完整可运行的代码
4. 遵循最佳实践和代码规范

请用自然语言描述你的思考过程，然后直接提供代码实现。

格式如下：
**思考过程：**
[描述你的分析过程、设计方案等]

**代码实现：**
文件路径：[相对项目根目录的路径]
```
[完整的可运行代码内容]
```

如果需要修改多个文件，请分别提供每个文件的路径和代码。

注意：
- 代码必须是完整的、可运行的
- 包含所有必要的导入和依赖
- 遵循项目现有的代码风格
- 添加适当的注释和文档
"""
    
    def _process_response(self, task_type: str, response: str, context: Dict[str, Any]) -> Any:
        """处理LLM响应"""
        try:
            # 所有任务类型现在都使用自然语言格式
            if task_type == "implement_issue":
                return self._parse_natural_language_response(response)
            elif task_type == "analyze_requirements":
                return self._parse_requirements_response(response)
            elif task_type == "review_code":
                return self._parse_review_response(response)
            else:
                return response
        except Exception as e:
            logger.warning(f"处理响应失败: {e}")
            return response
    
    def _parse_requirements_response(self, response: str) -> list[dict[str, str]]:
        """解析需求分析的自然语言响应"""
        try:
            issues = []
            
            # 匹配任务格式：任务1：标题：[标题] 描述：[描述]
            task_pattern = r'任务\d+：\s*\n标题：\s*(.*?)\s*\n描述：\s*(.*?)(?=\n任务\d+：|\n*$)'
            matches = re.finditer(task_pattern, response, re.DOTALL)
            
            for match in matches:
                title = match.group(1).strip()
                description = match.group(2).strip()
                if title and description:
                    issues.append({
                        "title": title,
                        "description": description
                    })
            
            # 如果没有找到标准格式，尝试其他格式
            if not issues:
                # 尝试找到标题和描述的其他格式
                title_pattern = r'标题：\s*(.*?)(?=\n|$)'
                desc_pattern = r'描述：\s*(.*?)(?=\n|$)'
                
                titles = re.findall(title_pattern, response)
                descriptions = re.findall(desc_pattern, response)
                
                for i in range(min(len(titles), len(descriptions))):
                    issues.append({
                        "title": titles[i].strip(),
                        "description": descriptions[i].strip()
                    })
            
            # 如果还是没有找到，创建一个默认的issue
            if not issues:
                issues.append({
                    "title": "实现用户需求",
                    "description": response.strip()
                })
            
            return issues
            
        except Exception as e:
            logger.warning(f"解析需求分析响应失败: {e}")
            return [{"title": "实现用户需求", "description": response.strip()}]
    
    def _parse_review_response(self, response: str) -> dict[str, Any]:
        """解析代码审查的自然语言响应"""
        try:
            result = {
                "approved": False,
                "comments": "审查失败",
                "score": 0,
                "meets_requirements": False
            }
            
            # 提取审查结果
            approved_match = re.search(r'审查结果：\s*(通过|不通过)', response)
            if approved_match:
                result["approved"] = approved_match.group(1) == "通过"
            
            # 提取总体评分
            score_match = re.search(r'总体评分：\s*(\d+)', response)
            if score_match:
                result["score"] = int(score_match.group(1))
            
            # 提取是否满足需求
            meets_match = re.search(r'是否满足需求：\s*(是|否)', response)
            if meets_match:
                result["meets_requirements"] = meets_match.group(1) == "是"
            
            # 提取总体意见
            comments_match = re.search(r'总体意见：\s*(.*?)(?=\n*$)', response, re.DOTALL)
            if comments_match:
                result["comments"] = comments_match.group(1).strip()
            else:
                # 如果没有找到总体意见，使用整个响应作为评论
                result["comments"] = response.strip()
            
            return result
            
        except Exception as e:
            logger.warning(f"解析代码审查响应失败: {e}")
            return {
                "approved": False,
                "comments": response.strip(),
                "score": 0,
                "meets_requirements": False
            }
    
    def _parse_natural_language_response(self, response: str) -> Dict[str, Any]:
        """解析自然语言格式的响应"""
        try:
            # 提取思考过程
            thoughts_match = re.search(r'\*\*思考过程：\*\*\s*(.*?)(?=\*\*代码实现：\*\*)', response, re.DOTALL)
            thoughts_text = thoughts_match.group(1).strip() if thoughts_match else "无思考过程记录"
            
            # 提取代码实现
            code_sections = []
            
            # 匹配文件路径和代码块
            file_pattern = r'文件路径：\s*(.*?)\s*```(?:\w+)?\s*(.*?)```'
            matches = re.finditer(file_pattern, response, re.DOTALL)
            
            for match in matches:
                file_path = match.group(1).strip()
                code_content = match.group(2).strip()
                code_sections.append({
                    "file_path": file_path,
                    "code": code_content
                })
            
            # 如果没有找到标准格式，尝试其他格式
            if not code_sections:
                # 尝试找到代码块
                code_blocks = re.findall(r'```(?:\w+)?\s*(.*?)```', response, re.DOTALL)
                if code_blocks:
                    # 假设第一个代码块是主要实现
                    code_sections.append({
                        "file_path": "main.py",  # 默认文件名
                        "code": code_blocks[0].strip()
                    })
            
            # 构建结果
            result = {
                "thoughts": [
                    {
                        "thought": thoughts_text,
                        "context": {"step": "自然语言分析"},
                        "conclusion": "完成分析和实现",
                        "confidence": 0.8
                    }
                ]
            }
            
            # 根据代码数量决定result格式
            if len(code_sections) == 1:
                result["result"] = code_sections[0]
            elif len(code_sections) > 1:
                result["result"] = code_sections
            else:
                result["result"] = {
                    "file_path": "fallback.md",
                    "code": f"# 实现说明\n\n{thoughts_text}\n\n{response}"
                }
            
            return result
            
        except Exception as e:
            logger.warning(f"解析自然语言响应失败: {e}")
            return {
                "thoughts": [
                    {
                        "thought": "解析响应失败",
                        "context": {"step": "错误处理"},
                        "conclusion": "需要人工检查",
                        "confidence": 0.1
                    }
                ],
                "result": {
                    "file_path": "raw_response.md",
                    "code": f"# 原始响应\n\n{response}"
                }
            }
    
    def _get_fallback_result(self, task_type: str, context: Dict[str, Any]) -> Any:
        """获取fallback结果"""
        if task_type == "analyze_requirements":
            return [{"title": "实现基础功能", "description": "需求分析失败，实现基础功能"}]
        elif task_type == "review_code":
            return {"approved": False, "comments": "代码审查失败，需要重新检查", "score": 0, "meets_requirements": False}
        else:
            return {"error": f"任务 {task_type} 执行失败"}
    
    # 保持向后兼容的方法
    async def analyze_requirements(self, requirements: str) -> list[dict[str, str]]:
        """分析用户需求，生成 Issue 列表"""
        result = await self.execute_task("analyze_requirements", {
            "requirements": requirements
        })
        
        # 现在直接返回解析后的issue列表
        if isinstance(result, list):
            return result
        else:
            return [{"title": "实现用户需求", "description": requirements}]
    

    
    async def review_code(self, issue: dict[str, Any], code: str) -> dict[str, Any]:
        """审查代码提交"""
        result = await self.execute_task("review_code", {
            "issue": issue,
            "code": code
        })
        
        # 现在直接返回解析后的审查结果
        if isinstance(result, dict):
            return result
        else:
            return {"approved": False, "comments": str(result)}