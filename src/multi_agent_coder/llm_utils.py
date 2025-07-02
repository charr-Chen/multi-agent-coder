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
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"LLM调用尝试 {attempt + 1}/{self.max_retries + 1}")
                response = await self.client.chat.completions.create(
                    model=LLM_CONFIG["model"],
                    messages=[
                        {"role": "system", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=LLM_CONFIG["max_tokens"]
                )
                
                content = response.choices[0].message.content.strip()
                logger.debug(f"LLM响应: {content[:200]}...")
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
            "analyze_code": self._get_code_analysis_prompt,
            "generate_code": self._get_code_generation_prompt,
            "review_code": self._get_code_review_prompt,
            "plan_implementation": self._get_implementation_plan_prompt,
            "select_files": self._get_file_selection_prompt,
            "generate_filename": self._get_filename_generation_prompt,
            "analyze_project": self._get_project_analysis_prompt,
            "debug_code": self._get_debug_prompt,
            "optimize_code": self._get_optimization_prompt,
            "create_tests": self._get_test_creation_prompt,
            "document_code": self._get_documentation_prompt,
            "refactor_code": self._get_refactoring_prompt,
            "security_audit": self._get_security_audit_prompt,
            "performance_analysis": self._get_performance_analysis_prompt,
            "architecture_design": self._get_architecture_design_prompt,
            "api_design": self._get_api_design_prompt,
            "database_design": self._get_database_design_prompt,
            "deployment_plan": self._get_deployment_plan_prompt,
            "implement_issue": self._get_implement_issue_prompt,
            "custom": lambda ctx, **kw: ctx.get('prompt', '请完成指定任务')
        }
        
        prompt_func = prompts.get(task_type, prompts["custom"])
        return prompt_func(context, **kwargs)
    
    def _get_requirements_analysis_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """需求分析prompt"""
        requirements = context.get('requirements', '')
        return f"""你是一个资深的需求分析师和系统架构师。

请深入分析以下用户需求，并提供详细的技术分析：

用户需求：
{requirements}

请提供JSON格式的分析结果：
{{
    "summary": "需求概述",
    "technical_requirements": ["具体技术需求1", "具体技术需求2"],
    "implementation_approach": "实现方法",
    "key_components": ["需要开发的组件1", "需要开发的组件2"],
    "expected_changes": ["预期的代码变更1", "预期的代码变更2"],
    "complexity": "简单/中等/复杂",
    "estimated_effort": "工作量估算",
    "dependencies": ["依赖项1", "依赖项2"],
    "risks": ["潜在风险1", "潜在风险2"],
    "suggestions": ["建议1", "建议2"]
}}

请确保分析准确、详细，并考虑技术可行性和最佳实践。"""
    
    def _get_code_analysis_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """代码分析prompt"""
        code = context.get('code', '')
        file_path = context.get('file_path', 'unknown')
        analysis_type = context.get('analysis_type', 'structure')
        
        if analysis_type == 'structure':
            return f"""你是一个资深的代码分析专家。

请深入分析以下代码的结构和功能：

文件路径: {file_path}
代码:
```python
{code}
```

请提供JSON格式的分析结果：
{{
    "file_type": "文件类型(如: service, model, utils, controller等)",
    "main_purpose": "文件主要用途",
    "architecture_pattern": "使用的架构模式",
    "classes": [
        {{
            "name": "类名",
            "purpose": "类的具体作用和职责",
            "key_methods": ["重要方法1", "重要方法2"],
            "dependencies": ["依赖的类或模块"]
        }}
    ],
    "functions": [
        {{
            "name": "函数名",
            "purpose": "函数的具体作用",
            "parameters": "主要参数类型",
            "returns": "返回值类型和含义",
            "complexity": "复杂度评估"
        }}
    ],
    "imports": ["导入的模块"],
    "modification_points": ["可以修改的位置1", "可以修改的位置2"],
    "code_quality": {{
        "readability": "可读性评分",
        "maintainability": "可维护性评分",
        "testability": "可测试性评分",
        "issues": ["发现的问题1", "发现的问题2"]
    }},
    "suggestions": ["改进建议1", "改进建议2"]
}}

请确保分析准确、详细，特别关注代码的实际功能而不是表面的命名。"""
        
        elif analysis_type == 'security':
            return f"""你是一个安全专家。

请对以下代码进行安全分析：

文件路径: {file_path}
代码:
```python
{code}
```

请提供JSON格式的安全分析结果：
{{
    "security_issues": [
        {{
            "type": "漏洞类型",
            "severity": "严重程度(高/中/低)",
            "description": "详细描述",
            "location": "问题位置",
            "fix_suggestion": "修复建议"
        }}
    ],
    "overall_security_score": "安全评分(1-10)",
    "recommendations": ["安全建议1", "安全建议2"]
}}"""
        
        else:
            return f"""请分析以下代码：

文件路径: {file_path}
代码:
```python
{code}
```

分析类型: {analysis_type}

请提供详细的分析结果。"""
    
    def _get_code_generation_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """代码生成prompt"""
        issue = context.get('issue', {})
        existing_code = context.get('existing_code', '')
        file_path = context.get('file_path', '')
        requirements = context.get('requirements', '')
        
        if existing_code:
            return f"""你是一个专业的Python开发工程师。

请根据需求对现有代码进行修改：

需求：
标题: {issue.get('title', '')}
描述: {issue.get('description', '')}
详细要求: {requirements}

文件路径: {file_path}

现有代码:
```python
{existing_code}
```

请根据需求对代码进行修改，要求：
1. 保持代码的完整性和可运行性
2. 遵循Python最佳实践
3. 添加必要的注释和文档字符串
4. 确保代码风格一致
5. 实现所有要求的功能

请返回修改后的完整代码。"""
        else:
            return f"""你是一个专业的Python开发工程师。

请根据需求生成新的代码：

需求：
标题: {issue.get('title', '')}
描述: {issue.get('description', '')}
详细要求: {requirements}

文件路径: {file_path}

请生成完整的Python代码，要求：
1. 遵循Python最佳实践
2. 添加必要的注释和文档字符串
3. 确保代码风格一致
4. 实现所有要求的功能
5. 考虑错误处理和边界情况

请返回完整的代码。"""
    
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

请提供JSON格式的审查结果：
{{
    "overall_score": "总体评分(1-10)",
    "meets_requirements": true/false,
    "code_quality": {{
        "readability": "可读性评分",
        "maintainability": "可维护性评分",
        "performance": "性能评分",
        "security": "安全性评分"
    }},
    "issues": [
        {{
            "type": "问题类型",
            "severity": "严重程度",
            "description": "问题描述",
            "suggestion": "改进建议"
        }}
    ],
    "strengths": ["优点1", "优点2"],
    "recommendations": ["建议1", "建议2"],
    "approved": true/false
}}"""
    
    def _get_implementation_plan_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """实现计划prompt"""
        issue = context.get('issue', {})
        analysis = context.get('analysis', {})
        
        return f"""你是一个资深的系统架构师。

请制定详细的实现计划：

Issue:
标题: {issue.get('title', '')}
描述: {issue.get('description', '')}

需求分析:
{json.dumps(analysis, ensure_ascii=False, indent=2)}

请提供JSON格式的实现计划：
{{
    "strategy": "实现策略",
    "phases": [
        {{
            "phase": "阶段名称",
            "description": "阶段描述",
            "tasks": ["任务1", "任务2"],
            "estimated_time": "时间估算"
        }}
    ],
    "files_to_modify": ["文件1", "文件2"],
    "files_to_create": ["新文件1", "新文件2"],
    "dependencies": ["依赖项1", "依赖项2"],
    "risks": ["风险1", "风险2"],
    "success_criteria": ["成功标准1", "成功标准2"]
}}"""
    
    def _get_file_selection_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """文件选择prompt"""
        issue = context.get('issue', {})
        project_structure = context.get('project_structure', {})
        candidate_files = context.get('candidate_files', [])
        
        return f"""你是一个资深的项目架构师。

请根据需求选择最合适的文件进行修改：

Issue:
标题: {issue.get('title', '')}
描述: {issue.get('description', '')}

项目结构:
{json.dumps(project_structure, ensure_ascii=False, indent=2)}

候选文件:
{json.dumps(candidate_files, ensure_ascii=False, indent=2)}

请提供JSON格式的文件选择结果：
{{
    "selected_files": [
        {{
            "file_path": "文件路径",
            "reason": "选择理由",
            "modification_type": "修改类型(add/modify/enhance)",
            "priority": "优先级(high/medium/low)"
        }}
    ],
    "reasoning": "选择逻辑说明",
    "alternative_approaches": ["备选方案1", "备选方案2"]
}}"""
    
    def _get_filename_generation_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """文件名生成prompt"""
        issue = context.get('issue', {})
        file_type = context.get('file_type', 'python')
        
        return f"""你是一个资深的文件命名专家。

请为以下需求生成合适的文件名：

Issue:
标题: {issue.get('title', '')}
描述: {issue.get('description', '')}

文件类型: {file_type}

请提供JSON格式的文件名建议：
{{
    "suggested_names": [
        {{
            "name": "建议的文件名",
            "reason": "命名理由",
            "convention": "遵循的命名规范"
        }}
    ],
    "best_choice": "最佳选择",
    "naming_conventions": ["遵循的规范1", "遵循的规范2"]
}}"""
    
    def _get_project_analysis_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """项目分析prompt"""
        project_structure = context.get('project_structure', {})
        
        return f"""你是一个资深的项目架构师。

请分析以下项目的整体架构：

项目结构:
{json.dumps(project_structure, ensure_ascii=False, indent=2)}

请提供JSON格式的项目分析结果：
{{
    "architecture_pattern": "架构模式",
    "main_components": ["主要组件1", "主要组件2"],
    "data_flow": "数据流向描述",
    "technology_stack": ["技术栈1", "技术栈2"],
    "strengths": ["优势1", "优势2"],
    "weaknesses": ["劣势1", "劣势2"],
    "improvement_suggestions": ["改进建议1", "改进建议2"]
}}"""
    
    def _get_debug_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """调试prompt"""
        code = context.get('code', '')
        error_message = context.get('error_message', '')
        
        return f"""你是一个资深的调试专家。

请帮助调试以下代码：

代码:
```python
{code}
```

错误信息:
{error_message}

请提供JSON格式的调试分析：
{{
    "root_cause": "根本原因",
    "error_type": "错误类型",
    "fix_suggestions": ["修复建议1", "修复建议2"],
    "prevention_tips": ["预防措施1", "预防措施2"],
    "corrected_code": "修正后的代码"
}}"""
    
    def _get_optimization_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """代码优化prompt"""
        code = context.get('code', '')
        optimization_target = context.get('optimization_target', 'performance')
        
        return f"""你是一个资深的代码优化专家。

请优化以下代码：

优化目标: {optimization_target}

代码:
```python
{code}
```

请提供JSON格式的优化建议：
{{
    "current_issues": ["当前问题1", "当前问题2"],
    "optimization_suggestions": [
        {{
            "type": "优化类型",
            "description": "优化描述",
            "impact": "影响程度",
            "implementation": "实现方法"
        }}
    ],
    "optimized_code": "优化后的代码",
    "performance_improvement": "性能提升预期"
}}"""
    
    def _get_test_creation_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """测试创建prompt"""
        code = context.get('code', '')
        test_framework = context.get('test_framework', 'pytest')
        
        return f"""你是一个资深的测试工程师。

请为以下代码创建测试：

测试框架: {test_framework}

代码:
```python
{code}
```

请提供JSON格式的测试计划：
{{
    "test_cases": [
        {{
            "name": "测试用例名称",
            "description": "测试描述",
            "input": "输入数据",
            "expected_output": "期望输出",
            "test_type": "测试类型(unit/integration/functional)"
        }}
    ],
    "test_code": "测试代码",
    "coverage_areas": ["覆盖区域1", "覆盖区域2"],
    "test_data": "测试数据"
}}"""
    
    def _get_documentation_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """文档生成prompt"""
        code = context.get('code', '')
        doc_type = context.get('doc_type', 'api')
        
        return f"""你是一个资深的技术文档专家。

请为以下代码生成文档：

文档类型: {doc_type}

代码:
```python
{code}
```

请提供JSON格式的文档：
{{
    "overview": "功能概述",
    "api_reference": [
        {{
            "name": "函数/类名",
            "description": "功能描述",
            "parameters": ["参数1", "参数2"],
            "returns": "返回值",
            "examples": ["示例1", "示例2"]
        }}
    ],
    "usage_examples": ["使用示例1", "使用示例2"],
    "notes": ["注意事项1", "注意事项2"]
}}"""
    
    def _get_refactoring_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """代码重构prompt"""
        code = context.get('code', '')
        refactoring_goal = context.get('refactoring_goal', 'improve_readability')
        
        return f"""你是一个资深的代码重构专家。

请重构以下代码：

重构目标: {refactoring_goal}

代码:
```python
{code}
```

请提供JSON格式的重构方案：
{{
    "refactoring_plan": [
        {{
            "step": "重构步骤",
            "description": "步骤描述",
            "rationale": "重构理由"
        }}
    ],
    "refactored_code": "重构后的代码",
    "improvements": ["改进点1", "改进点2"],
    "risks": ["风险1", "风险2"]
}}"""
    
    def _get_security_audit_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """安全审计prompt"""
        code = context.get('code', '')
        
        return f"""你是一个资深的安全专家。

请对以下代码进行安全审计：

代码:
```python
{code}
```

请提供JSON格式的安全审计报告：
{{
    "vulnerabilities": [
        {{
            "type": "漏洞类型",
            "severity": "严重程度",
            "description": "漏洞描述",
            "location": "位置",
            "fix": "修复方案"
        }}
    ],
    "security_score": "安全评分",
    "recommendations": ["安全建议1", "安全建议2"],
    "compliance": ["合规性检查1", "合规性检查2"]
}}"""
    
    def _get_performance_analysis_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """性能分析prompt"""
        code = context.get('code', '')
        
        return f"""你是一个资深的性能优化专家。

请分析以下代码的性能：

代码:
```python
{code}
```

请提供JSON格式的性能分析：
{{
    "performance_issues": [
        {{
            "type": "性能问题类型",
            "impact": "影响程度",
            "description": "问题描述",
            "optimization": "优化建议"
        }}
    ],
    "bottlenecks": ["瓶颈1", "瓶颈2"],
    "optimization_opportunities": ["优化机会1", "优化机会2"],
    "performance_score": "性能评分"
}}"""
    
    def _get_architecture_design_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """架构设计prompt"""
        requirements = context.get('requirements', '')
        
        return f"""你是一个资深的系统架构师。

请为以下需求设计系统架构：

需求:
{requirements}

请提供JSON格式的架构设计：
{{
    "architecture_pattern": "架构模式",
    "components": [
        {{
            "name": "组件名称",
            "purpose": "组件用途",
            "responsibilities": ["职责1", "职责2"],
            "interfaces": ["接口1", "接口2"]
        }}
    ],
    "data_flow": "数据流向",
    "technology_choices": ["技术选择1", "技术选择2"],
    "scalability_considerations": ["可扩展性考虑1", "可扩展性考虑2"],
    "security_considerations": ["安全性考虑1", "安全性考虑2"]
}}"""
    
    def _get_api_design_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """API设计prompt"""
        requirements = context.get('requirements', '')
        
        return f"""你是一个资深的API设计专家。

请为以下需求设计API：

需求:
{requirements}

请提供JSON格式的API设计：
{{
    "endpoints": [
        {{
            "path": "API路径",
            "method": "HTTP方法",
            "description": "功能描述",
            "parameters": ["参数1", "参数2"],
            "responses": ["响应1", "响应2"]
        }}
    ],
    "data_models": ["数据模型1", "数据模型2"],
    "authentication": "认证方式",
    "rate_limiting": "限流策略",
    "documentation": "文档要求"
}}"""
    
    def _get_database_design_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """数据库设计prompt"""
        requirements = context.get('requirements', '')
        
        return f"""你是一个资深的数据库设计专家。

请为以下需求设计数据库：

需求:
{requirements}

请提供JSON格式的数据库设计：
{{
    "tables": [
        {{
            "name": "表名",
            "purpose": "表用途",
            "columns": ["列1", "列2"],
            "relationships": ["关系1", "关系2"]
        }}
    ],
    "indexes": ["索引1", "索引2"],
    "constraints": ["约束1", "约束2"],
    "normalization": "规范化程度",
    "performance_considerations": ["性能考虑1", "性能考虑2"]
}}"""
    
    def _get_deployment_plan_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """部署计划prompt"""
        project_info = context.get('project_info', {})
        
        return f"""你是一个资深的DevOps专家。

请为以下项目制定部署计划：

项目信息:
{json.dumps(project_info, ensure_ascii=False, indent=2)}

请提供JSON格式的部署计划：
{{
    "deployment_strategy": "部署策略",
    "environments": ["环境1", "环境2"],
    "infrastructure": ["基础设施1", "基础设施2"],
    "deployment_steps": ["步骤1", "步骤2"],
    "rollback_plan": "回滚计划",
    "monitoring": ["监控项1", "监控项2"],
    "security_measures": ["安全措施1", "安全措施2"]
}}"""

    def _get_implement_issue_prompt(self, context: Dict[str, Any], **kwargs) -> str:
        """实现Issue的prompt"""
        issue = context.get('issue', {})
        recent_thoughts = context.get('recent_thoughts', [])
        
        # 格式化历史思考链
        thoughts_text = ""
        if recent_thoughts:
            thoughts_text = "\n".join([
                f"- {thought.get('thought', '无记录')}" 
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

请严格按如下JSON格式输出：
{{
  "thoughts": [
    {{"thought": "你每一步的思考内容", "context": {{"step": "分析需求"}}, "conclusion": "本步结论", "confidence": 0.9}},
    {{"thought": "设计实现方案", "context": {{"step": "方案设计"}}, "conclusion": "选择的技术方案", "confidence": 0.8}},
    {{"thought": "编写代码实现", "context": {{"step": "代码实现"}}, "conclusion": "代码实现完成", "confidence": 0.9}}
  ],
  "result": {{
    "file_path": "要写入的文件路径（相对项目根目录）",
    "code": "完整的可运行代码内容"
  }}
}}

如果需要修改多个文件，可以返回数组形式：
{{
  "thoughts": [...],
  "result": [
    {{"file_path": "src/components/MultiModal.tsx", "code": "React组件代码..."}},
    {{"file_path": "src/utils/parser.py", "code": "Python解析器代码..."}}
  ]
}}

注意：
- 代码必须是完整的、可运行的
- 包含所有必要的导入和依赖
- 遵循项目现有的代码风格
- 添加适当的注释和文档
"""
    
    def _process_response(self, task_type: str, response: str, context: Dict[str, Any]) -> Any:
        """处理LLM响应"""
        try:
            # 尝试解析JSON响应
            if task_type in ["analyze_requirements", "analyze_code", "review_code", 
                           "plan_implementation", "select_files", "generate_filename",
                           "analyze_project", "debug_code", "optimize_code", 
                           "create_tests", "document_code", "refactor_code",
                           "security_audit", "performance_analysis", "architecture_design",
                           "api_design", "database_design", "deployment_plan", "implement_issue"]:
                return self._parse_json_response(response)
            else:
                return response
        except Exception as e:
            logger.warning(f"处理响应失败: {e}")
            return response
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析JSON响应"""
        try:
            # 尝试提取JSON部分
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            else:
                # 尝试直接解析
                return json.loads(response)
        except json.JSONDecodeError:
            logger.warning("JSON解析失败，返回原始响应")
            return {"raw_response": response}
    
    def _get_fallback_result(self, task_type: str, context: Dict[str, Any]) -> Any:
        """获取fallback结果"""
        if task_type == "analyze_requirements":
            return {
                "summary": "需求分析失败",
                "technical_requirements": ["基础功能实现"],
                "implementation_approach": "标准实现",
                "key_components": ["主要功能"],
                "expected_changes": ["添加新功能"]
            }
        elif task_type == "generate_code":
            return "# 代码生成失败，请手动实现"
        elif task_type == "review_code":
            return {"approved": False, "comments": "代码审查失败"}
        elif task_type == "implement_issue":
            issue = context.get('issue', {})
            return {
                "thoughts": [
                    {
                        "thought": "LLM调用失败，无法生成实现方案",
                        "context": {"step": "错误处理"},
                        "conclusion": "需要人工介入",
                        "confidence": 0.1
                    }
                ],
                "result": {
                    "file_path": f"fallback_{issue.get('title', 'unknown').replace(' ', '_')}.md",
                    "code": f"""# 实现失败

## Issue信息
- 标题: {issue.get('title', '未知')}
- 描述: {issue.get('description', '无描述')}

## 错误说明
LLM调用失败，无法自动生成代码实现。
请手动检查网络连接和API配置，或者手动实现此功能。

## 建议
1. 检查OpenAI API Key是否正确
2. 检查网络连接和代理设置
3. 查看日志获取详细错误信息
"""
                }
            }
        else:
            return {"error": f"任务 {task_type} 执行失败"}
    
    # 保持向后兼容的方法
    async def analyze_requirements(self, requirements: str) -> list[dict[str, str]]:
        """分析用户需求，生成 Issue 列表"""
        result = await self.execute_task("analyze_requirements", {
            "requirements": requirements
        })
        
        if isinstance(result, dict) and "technical_requirements" in result:
            # 转换为旧格式
            issues = []
            for req in result.get("technical_requirements", []):
                issues.append({
                    "title": req,
                    "description": f"实现 {req}"
                })
            return issues
        else:
            return [{"title": "实现用户需求", "description": requirements}]
    
    async def generate_code_from_prompt(self, prompt: str) -> str:
        """从prompt生成代码"""
        return await self.execute_task("generate_code", {
            "prompt": prompt
        })
    
    async def review_code(self, issue: dict[str, Any], code: str) -> dict[str, Any]:
        """审查代码提交"""
        result = await self.execute_task("review_code", {
            "issue": issue,
            "code": code
        })
        
        if isinstance(result, dict):
            return result
        else:
            return {"approved": True, "comments": str(result)}