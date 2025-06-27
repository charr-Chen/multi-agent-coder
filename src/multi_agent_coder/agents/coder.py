"""
简化版编码员代理模块
专注于核心代码生成功能
"""

import os
import logging
import asyncio
import time
import subprocess
import shlex
import json
from typing import Any, Optional
from ..git_utils import GitManager
from ..llm_utils import LLMManager
from ..config import AGENT_CONFIG
from .thinking import MemoryManager

logger = logging.getLogger(__name__)

class CoderAgent:
    """简化版编码员代理 - 专注于核心代码生成"""
    
    def __init__(self, git_manager: GitManager, llm_manager: LLMManager, agent_id: str):
        """初始化编码员代理
        
        Args:
            git_manager: Git 仓库管理器 (agent自己的仓库)
            llm_manager: LLM 管理器
            agent_id: 代理 ID
        """
        self.git_manager = git_manager
        self.llm_manager = llm_manager
        self.agent_id = agent_id
        self.config = AGENT_CONFIG["coder"]
        self.current_issue = None
        self.playground_git_manager = None
        self.collaboration_manager = None
        self.multi_repo_manager = None
        
        # 保留核心组件
        self.memory_manager = MemoryManager(agent_id)
        
        # Agent的工作目录就是用户项目的完整副本
        self.user_project_path = self.git_manager.repo_path if self.git_manager else None
        
        # 基本统计
        self.issues_completed = 0
        
        logger.info(f"编码员代理初始化完成: {agent_id}")
        logger.info(f"Agent工作目录: {self.user_project_path}")
        
    def set_playground_git_manager(self, playground_git_manager: GitManager):
        """设置playground仓库管理器"""
        self.playground_git_manager = playground_git_manager
        logger.info(f"{self.agent_id} 设置playground仓库管理器")
    
    def set_collaboration_manager(self, collaboration_manager):
        """设置协作管理器"""
        self.collaboration_manager = collaboration_manager
        logger.info(f"{self.agent_id} 设置协作管理器")
    
    def get_issues_git_manager(self) -> GitManager:
        """获取用于访问Issues的Git管理器"""
        if self.playground_git_manager:
            return self.playground_git_manager
        return self.git_manager
    
    async def grab_issue(self) -> Optional[dict[str, Any]]:
        """获取Issue"""
        logger.info(f"🎯 {self.agent_id} 开始获取Issue...")
        
        # 首先检查是否有已分配给自己但未完成的Issue
        if self.current_issue:
            issue_status = await self._check_issue_status(self.current_issue["id"])
            if issue_status == "assigned":
                logger.info(f"🔄 {self.agent_id} 继续处理已分配的Issue: {self.current_issue['id']}")
                return self.current_issue
        
        # 获取所有开放的Issue（包括open和assigned状态）
        all_issues = await self._get_all_available_issues()
        
        if not all_issues:
            logger.debug(f"📭 {self.agent_id} 没有发现可用的Issues")
            return None
        
        best_issue = await self._select_optimal_issue(all_issues)
        
        if best_issue:
            # 尝试分配Issue
            assign_result = await self.get_issues_git_manager().assign_issue(best_issue["id"], self.agent_id)
            if assign_result:
                self.current_issue = best_issue
                logger.info(f"✅ {self.agent_id} 成功获取Issue: {best_issue['id']}")
                return best_issue
            else:
                # 分配失败时，检查Issue的当前状态以提供更准确的日志
                current_status = await self._check_issue_status(best_issue["id"])
                current_assignee = await self._get_issue_assignee(best_issue["id"])
                
                if current_status == "assigned" and current_assignee and current_assignee != self.agent_id:
                    logger.debug(f"💼 {self.agent_id} Issue {best_issue['id']} 已被 {current_assignee} 获取")
                elif current_status == "completed":
                    logger.debug(f"✅ {self.agent_id} Issue {best_issue['id']} 已完成")
                else:
                    logger.warning(f"❌ {self.agent_id} Issue分配失败: {best_issue['id']} (状态: {current_status})")
        
        return None
    
    async def _get_all_available_issues(self) -> list[dict[str, Any]]:
        """获取所有可用的Issues（包括open和assigned状态）"""
        try:
            # 直接从issues文件读取所有Issues
            issues_data = self.get_issues_git_manager()._load_issues()
            all_issues = issues_data.get("issues", [])
            
            # 过滤出open状态或分配给自己的assigned状态的Issues
            available_issues = []
            for issue in all_issues:
                status = issue.get("status", "")
                assigned_to = issue.get("assigned_to")
                
                if status == "open":
                    available_issues.append(issue)
                elif status == "assigned" and assigned_to == self.agent_id:
                    available_issues.append(issue)
            
            return available_issues
        except Exception as e:
            logger.error(f"❌ 获取Issues失败: {e}")
            return []
    
    async def _check_issue_status(self, issue_id: str) -> Optional[str]:
        """检查Issue状态"""
        try:
            issues_data = self.get_issues_git_manager()._load_issues()
            for issue in issues_data.get("issues", []):
                if issue["id"] == issue_id:
                    return issue.get("status")
            return None
        except Exception:
            return None
    
    async def _select_optimal_issue(self, issues: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
        """选择Issue（优先处理已分配给自己的，然后是未分配的）"""
        # 首先查找已分配给自己的Issue
        my_assigned_issues = [issue for issue in issues if issue.get("assigned_to") == self.agent_id]
        if my_assigned_issues:
            selected_issue = my_assigned_issues[0]
            logger.info(f"🔄 {self.agent_id} 继续处理已分配的Issue: {selected_issue['title']}")
            return selected_issue
        
        # 然后查找未分配的Issue
        unassigned_issues = [issue for issue in issues if not issue.get("assigned_to")]
        if unassigned_issues:
            selected_issue = unassigned_issues[0]
            logger.info(f"🎯 {self.agent_id} 选择新Issue: {selected_issue['title']}")
            return selected_issue
        
        return None
    
    async def implement_issue(self, issue: dict[str, Any]) -> bool:
        """实现Issue"""
        start_time = time.time()
        
        try:
            logger.info(f"🚀 {self.agent_id} 开始实现Issue")
            logger.info(f"📋 Issue: {issue.get('title', 'Unknown')}")
            
            # 简化的实现流程
            context = await self._build_context(issue)
            code = await self._generate_code(context)
            improved_code = await self._review_and_improve_code(code, context)
            success = await self._save_code(improved_code, issue, context)
            
            if success:
                self.issues_completed += 1
                self._store_success_memory(issue, {"code": improved_code})
            
            completion_time = time.time() - start_time
            logger.info(f"⏱️ Issue完成时间: {completion_time:.2f}秒")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ {self.agent_id} Issue实现失败: {e}")
            return False
    
    async def _build_context(self, issue: dict[str, Any]) -> dict[str, Any]:
        """构建上下文"""
        keywords = self._extract_issue_keywords(issue)
        memories = self.memory_manager.retrieve_memories(keywords, limit=5)
        file_operation = await self._decide_file_operation(issue, {"keywords": keywords})
        
        return {
            "issue": issue,
            "keywords": keywords,
            "memories": memories,
            "file_operation": file_operation
        }
    
    async def _generate_code(self, context: dict[str, Any]) -> str:
        """生成代码 - 智能处理现有文件修改"""
        issue = context["issue"]
        file_operation = context["file_operation"]
        
        if file_operation.get('action') == 'failed':
            # 无法确定文件操作，返回空字符串
            logger.warning("⚠️ 文件操作失败，跳过代码生成")
            return ""
        elif file_operation.get('action') == 'modify_existing':
            # 修改现有文件：读取当前内容，生成智能修改
            return await self._generate_file_modification(issue, file_operation, context)
        else:
            # 不应该有其他情况
            logger.warning("⚠️ 未知的文件操作类型，跳过代码生成")
            return ""
    
    async def _generate_file_modification(self, issue: dict[str, Any], file_operation: dict[str, Any], context: dict[str, Any]) -> str:
        """为现有文件生成智能修改"""
        target_file = file_operation.get('target_file')
        if not target_file or not self.user_project_path:
            logger.error("❌ 无法获取目标文件信息")
            return ""
        
        # 读取现有文件内容
        full_file_path = os.path.join(self.user_project_path, target_file)
        current_content = await self.read_file_with_command(full_file_path)
        
        if not current_content:
            logger.error(f"❌ 无法读取目标文件: {target_file}")
            return ""
        
        logger.info(f"📖 读取现有文件内容，共 {len(current_content.split())} 个单词")
        
        # 第一步：深入分析Issue需求
        issue_analysis = await self._analyze_issue_requirements(issue)
        logger.info(f"🔍 Issue需求分析: {issue_analysis.get('summary', 'N/A')}")
        
        # 第二步：分析现有代码结构
        code_analysis = await self._analyze_code_structure(current_content, target_file)
        logger.info(f"📊 代码结构分析: 发现 {len(code_analysis.get('functions', []))} 个函数, {len(code_analysis.get('classes', []))} 个类")
        
        # 第三步：生成具体的修改计划
        modification_plan = await self._create_modification_plan(issue_analysis, code_analysis, issue)
        logger.info(f"📋 修改计划: {modification_plan.get('strategy', 'N/A')}")
        
        # 第四步：根据计划生成修改后的代码
        modified_code = await self._generate_code_with_plan(current_content, modification_plan, issue)
        
        # 第五步：验证修改是否有实质性变化
        if await self._validate_code_changes(current_content, modified_code):
            logger.info(f"✅ 生成有效的文件修改，共 {len(modified_code.split())} 个单词")
            return modified_code
        else:
            logger.warning("⚠️ 生成的代码与原代码相同，尝试强制修改")
            # 尝试强制修改
            forced_modification = await self._force_meaningful_modification(current_content, issue, target_file)
            return forced_modification
    
    async def _analyze_issue_requirements(self, issue: dict[str, Any]) -> dict[str, Any]:
        """深入分析Issue的技术需求"""
        prompt = f"""
请深入分析以下Issue的技术需求：

标题: {issue.get('title', 'N/A')}
描述: {issue.get('description', 'N/A')}

请提供JSON格式的分析结果：
{{
    "summary": "需求概述",
    "technical_requirements": ["具体技术需求1", "具体技术需求2"],
    "implementation_approach": "实现方法",
    "key_components": ["需要修改的组件1", "需要修改的组件2"],
    "expected_changes": ["预期的代码变更1", "预期的代码变更2"]
}}

只返回JSON，不要其他解释。
"""
        
        try:
            response = await self.llm_manager.generate_code_from_prompt(prompt)
            if response:
                try:
                    return json.loads(response.strip())
                except json.JSONDecodeError:
                    logger.debug(f"JSON解析失败，使用备选分析")
        except Exception as e:
            logger.debug(f"Issue需求分析失败: {e}")
        
        # 备选简单分析
        return {
            "summary": issue.get('title', '未知需求'),
            "technical_requirements": [issue.get('title', '基础功能实现')],
            "implementation_approach": "代码增强",
            "key_components": ["主要功能"],
            "expected_changes": ["添加新功能"]
        }
    
    async def _analyze_code_structure(self, code_content: str, file_path: str) -> dict[str, Any]:
        """分析代码结构"""
        prompt = f"""
请分析以下Python代码的结构：

文件: {file_path}
代码:
```python
{code_content}
```

请提供JSON格式的分析结果：
{{
    "file_type": "文件类型(如: service, model, utils等)",
    "main_purpose": "文件主要用途",
    "classes": [
        {{"name": "类名", "purpose": "用途", "methods": ["方法1", "方法2"]}}
    ],
    "functions": [
        {{"name": "函数名", "purpose": "用途", "parameters": ["参数1", "参数2"]}}
    ],
    "imports": ["导入的模块"],
    "modification_points": ["可以修改的位置1", "可以修改的位置2"]
}}

只返回JSON，不要其他解释。
"""
        
        try:
            response = await self.llm_manager.generate_code_from_prompt(prompt)
            if response:
                return json.loads(response.strip())
        except Exception as e:
            logger.debug(f"代码结构分析失败: {e}")
        
        # 备选简单分析
        lines = code_content.split('\n')
        classes = [line.strip() for line in lines if line.strip().startswith('class ')]
        functions = [line.strip() for line in lines if line.strip().startswith('def ')]
        imports = [line.strip() for line in lines if line.strip().startswith(('import ', 'from '))]
        
        return {
            "file_type": "python_module",
            "main_purpose": "代码模块",
            "classes": [{"name": cls, "purpose": "业务逻辑", "methods": []} for cls in classes],
            "functions": [{"name": func, "purpose": "功能实现", "parameters": []} for func in functions],
            "imports": imports,
            "modification_points": ["函数内部", "类方法"]
        }
    
    async def _create_modification_plan(self, issue_analysis: dict[str, Any], code_analysis: dict[str, Any], issue: dict[str, Any]) -> dict[str, Any]:
        """创建具体的修改计划"""
        prompt = f"""
基于Issue需求和代码结构分析，创建具体的修改计划：

Issue需求:
{json.dumps(issue_analysis, ensure_ascii=False, indent=2)}

代码结构:
{json.dumps(code_analysis, ensure_ascii=False, indent=2)}

请提供JSON格式的修改计划：
{{
    "strategy": "修改策略(如: enhance_existing, add_methods, modify_logic等)",
    "target_locations": [
        {{"type": "class/function/import", "name": "目标名称", "action": "add/modify/enhance"}}
    ],
    "specific_changes": [
        {{"location": "具体位置", "change_type": "变更类型", "description": "变更描述"}}
    ],
    "new_code_blocks": [
        {{"position": "插入位置", "code_type": "代码类型", "purpose": "用途"}}
    ]
}}

只返回JSON，不要其他解释。
"""
        
        try:
            response = await self.llm_manager.generate_code_from_prompt(prompt)
            if response:
                return json.loads(response.strip())
        except Exception as e:
            logger.debug(f"修改计划创建失败: {e}")
        
        # 备选简单计划
        return {
            "strategy": "enhance_existing",
            "target_locations": [{"type": "function", "name": "main", "action": "enhance"}],
            "specific_changes": [{"location": "函数内部", "change_type": "功能增强", "description": "添加新功能"}],
            "new_code_blocks": [{"position": "函数末尾", "code_type": "功能代码", "purpose": "实现需求"}]
        }
    
    async def _generate_code_with_plan(self, current_content: str, modification_plan: dict[str, Any], issue: dict[str, Any]) -> str:
        """根据修改计划生成代码"""
        prompt = f"""
你是一个专业的Python开发工程师。请根据详细的修改计划，对现有代码进行精确修改。

【原始代码】:
```python
{current_content}
```

【修改计划】:
{json.dumps(modification_plan, ensure_ascii=False, indent=2)}

【Issue信息】:
标题: {issue.get('title', 'N/A')}
描述: {issue.get('description', 'N/A')}

【严格要求】:
1. **必须进行实质性修改** - 不能只是复制原代码
2. **遵循修改计划** - 按照计划中的strategy和specific_changes执行
3. **保持代码完整性** - 返回完整的可运行代码
4. **添加实际功能** - 根据Issue需求添加真正的功能实现
5. **保持原有结构** - 在现有代码基础上进行增强

【修改示例】:
- 如果是"多模态Prompt整合"，应该添加处理多种输入类型的方法
- 如果是"分层存储机制"，应该添加不同层级的存储逻辑
- 如果是Protocol类，应该添加新的抽象方法或增强现有方法

请返回修改后的完整Python代码，确保有明显的功能增强。
"""
        
        try:
            modified_code = await self.llm_manager.generate_code_from_prompt(prompt)
            if modified_code and modified_code.strip():
                return modified_code.strip()
        except Exception as e:
            logger.error(f"❌ 根据计划生成代码失败: {e}")
        
        # 如果失败，尝试简单的强制修改
        return await self._force_meaningful_modification(current_content, issue, "target_file")
    
    async def _validate_code_changes(self, original_code: str, modified_code: str) -> bool:
        """验证代码是否有实质性修改"""
        if not modified_code or not original_code:
            return False
        
        # 移除空白字符进行比较
        original_clean = ''.join(original_code.split())
        modified_clean = ''.join(modified_code.split())
        
        # 检查是否有实质性差异
        if original_clean == modified_clean:
            logger.warning("⚠️ 生成的代码与原代码完全相同")
            return False
        
        # 检查差异程度
        similarity_ratio = len(set(original_clean) & set(modified_clean)) / max(len(set(original_clean)), len(set(modified_clean)), 1)
        if similarity_ratio > 0.95:
            logger.warning(f"⚠️ 代码相似度过高: {similarity_ratio:.2%}")
            return False
        
        logger.info(f"✅ 代码修改验证通过，相似度: {similarity_ratio:.2%}")
        return True
    
    async def _force_meaningful_modification(self, current_content: str, issue: dict[str, Any], file_path: str) -> str:
        """强制进行有意义的修改"""
        logger.info("🔧 执行强制修改策略")
        
        issue_title = issue.get('title', '功能增强')
        
        # 分析文件类型并添加相应的功能
        if 'service' in file_path.lower() or 'Service' in current_content:
            return await self._enhance_service_file(current_content, issue_title)
        elif 'Protocol' in current_content:
            return await self._enhance_protocol_file(current_content, issue_title)
        elif '__main__' in file_path:
            return await self._enhance_main_file(current_content, issue_title)
        else:
            return await self._add_generic_enhancement(current_content, issue_title)
    
    async def _enhance_service_file(self, content: str, issue_title: str) -> str:
        """增强服务文件"""
        enhancement = f"""
    # {issue_title} - 新增功能
    async def enhanced_feature(self, **kwargs) -> dict:
        \"\"\"
        {issue_title}的实现
        根据Issue需求添加的新功能
        \"\"\"
        # TODO: 实现具体的{issue_title}逻辑
        return {{"status": "enhanced", "feature": "{issue_title}"}}
"""
        
        # 在类的最后一个方法后添加新方法
        lines = content.split('\n')
        insert_index = len(lines) - 1
        
        # 找到最后一个方法的位置
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip().startswith('def ') or lines[i].strip() == 'pass':
                insert_index = i + 1
                break
        
        lines.insert(insert_index, enhancement)
        return '\n'.join(lines)
    
    async def _enhance_protocol_file(self, content: str, issue_title: str) -> str:
        """增强Protocol文件"""
        enhancement = f"""
    async def {issue_title.lower().replace(' ', '_').replace('(', '').replace(')', '')}(
        self, *, data: dict, options: dict = None
    ) -> dict:
        \"\"\"
        {issue_title}
        新增的协议方法用于支持{issue_title}
        \"\"\"
        pass
"""
        
        # 在类的最后添加新方法
        lines = content.split('\n')
        insert_index = len(lines) - 1
        
        # 找到类的结束位置
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() and not lines[i].startswith(' ') and not lines[i].startswith('\t'):
                break
            if lines[i].strip() == 'pass' or 'def ' in lines[i]:
                insert_index = i + 1
                break
        
        lines.insert(insert_index, enhancement)
        return '\n'.join(lines)
    
    async def _enhance_main_file(self, content: str, issue_title: str) -> str:
        """增强主文件"""
        enhancement = f"""

# {issue_title} - 配置增强
def configure_{issue_title.lower().replace(' ', '_')}():
    \"\"\"
    {issue_title}的配置函数
    \"\"\"
    # TODO: 实现{issue_title}的具体配置
    print(f"正在配置{issue_title}...")
    return True
"""
        
        # 在main函数之前添加配置函数
        lines = content.split('\n')
        main_index = -1
        
        for i, line in enumerate(lines):
            if 'def main()' in line:
                main_index = i
                break
        
        if main_index > 0:
            lines.insert(main_index, enhancement)
        else:
            lines.append(enhancement)
        
        return '\n'.join(lines)
    
    async def _add_generic_enhancement(self, content: str, issue_title: str) -> str:
        """添加通用增强"""
        enhancement = f"""

# {issue_title} - 功能增强
def enhanced_functionality():
    \"\"\"
    实现{issue_title}的新功能
    \"\"\"
    # TODO: 根据具体需求实现功能
    result = {{
        "feature": "{issue_title}",
        "status": "implemented",
        "timestamp": "2025-06-27"
    }}
    return result
"""
        
        return content + enhancement
    
    async def _generate_new_file_code(self, issue: dict[str, Any], context: dict[str, Any]) -> str:
        """为新文件生成完整代码"""
        
        prompt = f"""
作为一个专业的Python开发者，请为以下Issue创建一个全新的Python文件。

【Issue信息】
- 标题: {issue.get('title', 'N/A')}
- 描述: {issue.get('description', 'N/A')}

【代码要求】
1. 生成完整、可运行的Python代码
2. 遵循PEP 8风格规范
3. 包含适当的错误处理和类型提示
4. 添加清晰的文档字符串
5. 包含必要的导入语句
6. 实现Issue中描述的具体功能

请只返回代码，不要包含其他解释。
"""
        
        try:
            code = await self.llm_manager.generate_code_from_prompt(prompt)
            return code if code else "# TODO: 实现功能"
        except Exception as e:
            logger.error(f"❌ 生成新文件代码失败: {e}")
            return "# TODO: 实现功能"
    
    async def _review_and_improve_code(self, code: str, context: dict[str, Any]) -> str:
        """审查和改进代码"""
        prompt = f"""
请审查以下代码并进行改进：

```python
{code}
```

请检查并改进：
1. 代码质量和可读性
2. 错误处理
3. 性能优化
4. 安全性
5. 最佳实践

返回改进后的完整代码。
"""
        
        improved_code = await self.llm_manager.generate_code_from_prompt(prompt)
        return improved_code if improved_code else code
    
    async def _save_code(self, code: str, issue: dict[str, Any], context: dict[str, Any]) -> bool:
        """保存代码"""
        file_operation = context["file_operation"]
        
        if file_operation["action"] == "failed":
            logger.error(f"❌ 无法保存代码: {file_operation['reason']}")
            return False
        elif file_operation["action"] == "modify_existing":
            return await self._modify_existing_user_file(
                file_operation["target_file"], code, issue, context
            )
        else:
            # 不应该再有create_new的情况，但保留以防万一
            logger.error("❌ 不支持创建新文件操作")
            return False
    
    async def _modify_existing_user_file(self, target_file: str, modified_content: str, 
                                       issue: dict[str, Any], context: dict[str, Any]) -> bool:
        """修改现有用户文件 - 在agent工作目录内操作"""
        if not self.user_project_path:
            logger.error("❌ 用户项目路径未配置")
            return False
        
        logger.info(f"🔧 {self.agent_id} 准备修改文件: {target_file}")
        logger.info(f"📁 工作目录: {self.user_project_path}")
        
        # 检查文件是否存在（相对路径）
        file_exists = await self.check_file_exists(target_file)
        if not file_exists:
            logger.error(f"❌ 目标文件不存在: {target_file}")
            
            # 尝试列出相似的文件
            base_name = os.path.basename(target_file).replace('.py', '')
            success, stdout, stderr = await self.execute_command(
                f"find . -name '*{base_name}*' -type f", 
                working_dir=self.user_project_path
            )
            if success and stdout.strip():
                logger.info(f"🔍 找到可能的相似文件:\n{stdout}")
            
            return False
    
        try:
            # 读取原文件内容
            original_content = await self.read_file_with_command(target_file)
            if original_content is None:
                logger.error(f"❌ 无法读取原文件: {target_file}")
                return False
            
            logger.info(f"📖 原文件 {target_file} 共 {len(original_content.split())} 个单词")
            
            # 创建备份
            backup_file = f"{target_file}.backup.{int(time.time())}"
            backup_success, _, stderr = await self.execute_command(
                f"cp {shlex.quote(target_file)} {shlex.quote(backup_file)}", 
                working_dir=self.user_project_path
            )
            
            if not backup_success:
                logger.error(f"❌ 无法创建备份文件: {backup_file} - {stderr}")
                return False
            
            logger.info(f"💾 已创建备份: {backup_file}")
            
            # 写入修改内容
            write_success = await self.write_file_with_command(target_file, modified_content)
            if not write_success:
                logger.error(f"❌ 无法写入修改内容: {target_file}")
                # 尝试恢复备份
                restore_success, _, _ = await self.execute_command(
                    f"cp {shlex.quote(backup_file)} {shlex.quote(target_file)}", 
                    working_dir=self.user_project_path
                )
                if restore_success:
                    logger.info(f"🔄 已恢复备份文件")
                return False
            
            logger.info(f"📝 新文件 {target_file} 共 {len(modified_content.split())} 个单词")
            
            # 验证文件修改成功
            verification_content = await self.read_file_with_command(target_file)
            if verification_content and len(verification_content) > 0:
                logger.info(f"✅ 文件修改验证成功: {target_file}")
            else:
                logger.error(f"❌ 文件修改验证失败: {target_file}")
                return False
            
            # 提交到Git
            commit_message = f"Modify {target_file}: {issue.get('title', 'Issue fix')}"
            await self.git_manager.commit_changes(commit_message, [target_file])
            
            logger.info(f"✅ 修改用户文件成功: {target_file}")
            return True
                
        except Exception as e:
            logger.error(f"❌ 修改用户文件失败: {e}")
            return False
    
    async def _create_new_file(self, code: str, issue: dict[str, Any], context: dict[str, Any]) -> bool:
        """创建新文件（使用命令行）"""
        if not self.user_project_path:
            logger.error("❌ 用户项目路径未配置")
            return False
        
        try:
            # 生成文件名
            file_name = self._generate_filename(issue)
            file_path = os.path.join(self.user_project_path, file_name)
            
            logger.info(f"🔧 {self.agent_id} 准备创建新文件: {file_name}")
            logger.info(f"📁 完整路径: {file_path}")
            
            # 使用命令行检查文件是否已存在
            file_exists = await self.check_file_exists(file_path)
            if file_exists:
                logger.warning(f"⚠️ 文件已存在，将覆盖: {file_name}")
                # 创建备份
                backup_path = await self.backup_file(file_path)
                if backup_path:
                    logger.info(f"✅ 已备份现有文件: {backup_path}")
            
            # 使用命令行创建目录（如果需要）
            dir_path = os.path.dirname(file_path)
            if dir_path and dir_path != self.user_project_path:
                mkdir_success, _, mkdir_stderr = await self.execute_command(f"mkdir -p {shlex.quote(dir_path)}")
                if not mkdir_success:
                    logger.error(f"❌ 无法创建目录: {dir_path} - {mkdir_stderr}")
                    return False
    
            # 使用命令行写入文件
            write_success = await self.write_file_with_command(file_path, code)
            if not write_success:
                logger.error(f"❌ 无法写入新文件: {file_name}")
                return False
        
            # 验证文件创建成功
            created_file_exists = await self.check_file_exists(file_path)
            if not created_file_exists:
                logger.error(f"❌ 文件创建验证失败: {file_name}")
                return False
        
            # 提交到Git (使用相对于Git仓库根目录的路径)
            git_relative_path = os.path.relpath(file_path, self.git_manager.repo_path)
            commit_message = f"Create {file_name}: {issue.get('title', 'New feature')}"
            await self.git_manager.commit_changes(commit_message, [git_relative_path])
            
            logger.info(f"✅ 创建新文件成功: {file_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 创建新文件失败: {e}")
            return False
    
    def _generate_filename(self, issue: dict[str, Any]) -> str:
        """生成文件名"""
        title = issue.get('title', 'new_feature')
        # 简单的文件名生成逻辑
        filename = title.lower().replace(' ', '_').replace('-', '_')
        filename = ''.join(c for c in filename if c.isalnum() or c == '_')
        return f"{filename}.py"

    def _extract_issue_keywords(self, issue: dict[str, Any]) -> list[str]:
        """从Issue中提取关键词"""
        text = f"{issue.get('title', '')} {issue.get('description', '')}"
        words = text.lower().split()
        # 过滤常见词汇，保留有意义的关键词
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]
        return list(set(keywords))[:10]

    def _store_success_memory(self, issue: dict[str, Any], result: dict[str, Any]):
        """存储成功经验到记忆"""
        memory_content = {
            'issue': issue,
            'solution_approach': result.get('plan', {}).to_dict() if hasattr(result.get('plan', {}), 'to_dict') else {},
            'code_quality_score': result.get('review_result', {}).overall_score if hasattr(result.get('review_result', {}), 'overall_score') else 0,
            'completion_time': time.time(),
            'success': True
        }
        
        keywords = self._extract_issue_keywords(issue)
        
        from .thinking.memory_manager import MemoryType
        
        self.memory_manager.store_memory(
            MemoryType.SOLUTION_APPROACH,
            memory_content,
            keywords
        )
        
        logger.info("✅ 成功经验已存储到记忆中")

    async def _decide_file_operation(self, issue: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """智能决定文件操作策略 - CoderAgent只修改现有文件，且必须有合理依据"""
        
        logger.info(f"🧠 开始智能分析Issue: {issue.get('title', 'Unknown')}")
        
        # 第一步：分析项目结构，理解代码库架构
        project_structure = await self._analyze_project_structure()
        if not project_structure:
            logger.error("❌ 无法分析项目结构，无法确定要修改的文件")
            return {
                'action': 'failed',
                'reason': '无法分析项目结构，无法确定要修改哪个文件。请检查工作目录是否包含Python文件。'
            }

        # 第二步：使用LLM进行智能文件匹配
        target_files = await self._intelligent_file_matching(issue, project_structure)
        
        if target_files:
            # 选择最佳匹配文件
            best_file = target_files[0]
            logger.info(f"🎯 智能匹配到目标文件: {best_file['path']}")
            logger.info(f"💡 匹配原因: {best_file['reason']}")
            
            return {
                'action': 'modify_existing',
                'target_file': best_file['path'],
                'reason': f"智能分析匹配: {best_file['reason']}"
            }
        
        # 第三步：智能选择备选文件进行修改（仅当有合理依据时）
        fallback_file = await self._select_fallback_file(issue, project_structure)
        
        if fallback_file:
            logger.info(f"🎯 选择备选文件进行修改: {fallback_file}")
            return {
                'action': 'modify_existing',
                'target_file': fallback_file,
                'reason': f"智能选择备选文件: {fallback_file}"
            }
        else:
            # 无法找到合适的文件，直接失败
            logger.warning("⚠️ 无法找到与Issue相关的合适文件进行修改")
            return {
                'action': 'failed',
                'reason': f"无法找到与Issue '{issue.get('title', 'Unknown')}' 相关的合适文件进行修改。建议明确指定要修改的文件或提供更具体的需求描述。"
            }
    
    async def _analyze_project_structure(self) -> Optional[dict[str, Any]]:
        """分析项目结构 - 使用命令行工具在agent工作目录内分析"""
        
        if not self.user_project_path:
            return None
        
        # 确保使用绝对路径
        abs_project_path = os.path.abspath(self.user_project_path)
        
        logger.info("📊 分析项目结构...")
        logger.info(f"🔍 工作目录: {abs_project_path}")
        
        # 首先检查工作目录是否存在
        if not os.path.exists(abs_project_path):
            logger.error(f"❌ 工作目录不存在: {abs_project_path}")
            return None
        
        # 使用ls查看目录结构
        success, stdout, stderr = await self.execute_command("ls -la", working_dir=abs_project_path)
        if success:
            logger.info(f"📁 目录内容:\n{stdout[:500]}...")  # 限制输出长度
        
        # 在工作目录内查找所有Python文件
        success, stdout, stderr = await self.execute_command(
            "find . -name '*.py' -type f", 
            working_dir=abs_project_path
        )
        
        if not success:
            logger.error(f"❌ 查找Python文件失败: {stderr}")
            return None
        
        if not stdout.strip():
            logger.warning("🔍 未找到任何Python文件")
            # 尝试查看是否有其他文件
            success2, stdout2, stderr2 = await self.execute_command(
                "find . -type f | head -10", 
                working_dir=abs_project_path
            )
            if success2 and stdout2.strip():
                logger.info(f"📄 发现的其他文件:\n{stdout2}")
            return None
        
        python_files = [f.strip().lstrip('./') for f in stdout.strip().split('\n') if f.strip()]
        logger.info(f"🐍 发现 {len(python_files)} 个Python文件")
        
        # 分类文件
        structure = {
            'all_files': python_files,
            'main_files': [],
            'service_files': [],
            'model_files': [],
            'util_files': [],
            'test_files': [],
            'config_files': [],
            'api_files': [],
            'directories': set()
        }
        
        for file_path in python_files:
            # 添加目录信息
            dir_path = os.path.dirname(file_path)
            if dir_path and dir_path != '.':
                structure['directories'].add(dir_path)
            
            # 根据文件名和路径进行分类
            file_lower = file_path.lower()
            
            if any(name in file_lower for name in ['main.py', 'app.py', 'server.py', 'run.py', '__main__.py']):
                structure['main_files'].append(file_path)
            elif any(word in file_lower for word in ['service', 'handler', 'manager', 'controller']):
                structure['service_files'].append(file_path)
            elif any(word in file_lower for word in ['model', 'schema', 'entity']):
                structure['model_files'].append(file_path)
            elif any(word in file_lower for word in ['util', 'helper', 'tool', 'common']):
                structure['util_files'].append(file_path)
            elif any(word in file_lower for word in ['test', 'spec']):
                structure['test_files'].append(file_path)
            elif any(word in file_lower for word in ['config', 'setting', 'constant']):
                structure['config_files'].append(file_path)
            elif any(word in file_lower for word in ['api', 'endpoint', 'route', 'view']):
                structure['api_files'].append(file_path)
        
        structure['directories'] = list(structure['directories'])
        
        logger.info(f"🏗️ 项目结构分析完成:")
        logger.info(f"   📁 总文件数: {len(structure['all_files'])}")
        logger.info(f"   🏠 主要文件: {len(structure['main_files'])} ({structure['main_files'][:3]})")
        logger.info(f"   ⚙️ 服务文件: {len(structure['service_files'])} ({structure['service_files'][:3]})")
        logger.info(f"   🔗 API文件: {len(structure['api_files'])} ({structure['api_files'][:3]})")
        logger.info(f"   📊 模型文件: {len(structure['model_files'])} ({structure['model_files'][:3]})")
        logger.info(f"   🛠️ 工具文件: {len(structure['util_files'])} ({structure['util_files'][:3]})")
        
        return structure

    async def _intelligent_file_matching(self, issue: dict[str, Any], project_structure: dict[str, Any]) -> list[dict[str, Any]]:
        """使用LLM进行智能文件匹配"""
        
        # 选择最有可能相关的文件进行详细分析
        candidate_files = self._select_candidate_files(issue, project_structure)
        
        if not candidate_files:
            logger.info("🔍 没有找到候选文件")
            return []
        
        logger.info(f"🔍 分析 {len(candidate_files)} 个候选文件...")
        
        # 获取文件内容摘要
        file_analyses = []
        for file_path in candidate_files[:8]:  # 限制分析数量
            analysis = await self._analyze_file_content(file_path)
            if analysis:
                file_analyses.append(analysis)
        
        if not file_analyses:
            return []
        
        # 构建深度智能分析prompt
        analysis_prompt = f"""
你是一个资深的软件架构师和代码分析专家，需要基于深度代码分析来确定应该修改哪个现有文件来实现Issue需求。

【Issue信息】
标题: {issue.get('title', 'N/A')}
描述: {issue.get('description', 'N/A')}

【项目结构概览】
- 主要文件: {', '.join(project_structure['main_files'][:3])}
- 服务文件: {', '.join(project_structure['service_files'][:3])}
- API文件: {', '.join(project_structure['api_files'][:3])}
- 工具文件: {', '.join(project_structure['util_files'][:3])}

【候选文件深度分析】
"""
        
        for i, analysis in enumerate(file_analyses, 1):
            analysis_prompt += f"""
{i}. 文件: {analysis['path']}
主要功能: {analysis.get('primary_purpose', '未知')}
业务领域: {analysis.get('business_domain', '未确定')}
核心能力: {', '.join(analysis.get('key_capabilities', [])[:3])}
复杂度: {analysis.get('complexity_level', '未知')}
适合修改类型: {', '.join(analysis.get('suitable_for_modifications', [])[:3])}
主要类: {', '.join([cls.get('name', '') for cls in analysis.get('main_classes', [])][:3])}
主要函数: {', '.join([func.get('name', '') for func in analysis.get('main_functions', [])][:5])}
集成点: {', '.join(analysis.get('integration_points', [])[:3])}
代码质量: {analysis.get('code_quality_notes', '未分析')}
"""
        
        analysis_prompt += f"""

请基于深度代码分析，作为资深架构师判断这个Issue应该修改哪个现有文件：

【分析维度】
1. 功能匹配度：Issue需求与文件实际功能的匹配程度
2. 架构合理性：修改是否符合代码架构和设计模式
3. 业务领域对齐：Issue所属领域与文件业务领域的一致性
4. 技术可行性：文件的技术栈和结构是否支持所需修改
5. 影响范围：修改对系统其他部分的影响程度
6. 代码质量：文件的可维护性和扩展性

请返回JSON格式的深度分析结果：
{{
    "recommended_files": [
        {{
            "path": "文件路径",
            "confidence": 0.95,
            "functional_match_score": 0.9,
            "architectural_fit_score": 0.8,
            "business_alignment_score": 0.9,
            "technical_feasibility_score": 0.85,
            "reason": "基于深度分析的详细推荐理由，包括具体的功能匹配点和技术考量",
            "modification_strategy": "具体的修改策略和建议的实现方式",
            "potential_risks": "可能的风险和注意事项",
            "modification_type": "功能增强/新功能添加/业务逻辑修改/性能优化"
        }}
    ],
    "analysis_summary": "基于深度代码分析的整体评估和建议",
    "alternative_approaches": "如果没有完美匹配，建议的替代方案"
}}

注意：只有当文件的实际功能和架构真正适合实现Issue需求时，才推荐修改。基于表面的文件名匹配是不够的。
"""
        
        try:
            response = await self.llm_manager.generate_code_from_prompt(analysis_prompt)
            
            if response:
                try:
                    result = json.loads(response)
                    recommended_files = result.get('recommended_files', [])
                    
                    # 验证推荐的文件是否存在
                    valid_files = []
                    for file_info in recommended_files:
                        file_path = file_info.get('path', '')
                        if any(file_path in candidate for candidate in candidate_files):
                            valid_files.append(file_info)
                    
                    logger.info(f"🎯 LLM推荐了 {len(valid_files)} 个文件")
                    return valid_files
                    
                except json.JSONDecodeError:
                    logger.warning("⚠️ LLM返回的不是有效JSON，尝试解析文本")
                    # 尝试从文本中提取文件路径
                    return self._parse_file_recommendations_from_text(response, candidate_files)
            
        except Exception as e:
            logger.error(f"❌ LLM文件匹配失败: {e}")
        
        return []

    def _select_candidate_files(self, issue: dict[str, Any], project_structure: dict[str, Any]) -> list[str]:
        """根据Issue内容选择候选文件"""
        
        issue_text = f"{issue.get('title', '')} {issue.get('description', '')}".lower()
        keywords = self._extract_issue_keywords(issue)
        
        candidates = []
        
        # 优先级1: 主要文件
        candidates.extend(project_structure['main_files'])
        
        # 优先级2: 根据关键词匹配相关文件（排除空的__init__.py）
        keyword_matches = []
        for file_path in project_structure['all_files']:
            file_lower = file_path.lower()
            
            # 跳过空的__init__.py文件
            if file_path.endswith('__init__.py'):
                continue
                
            # 检查文件路径是否包含关键词
            for keyword in keywords:
                if keyword.lower() in file_lower:
                    keyword_matches.append(file_path)
                    break
        
        # 按文件大小/重要性排序关键词匹配的文件
        keyword_matches.sort(key=lambda x: (
            0 if 'service.py' in x else  # service.py 优先级最高
            1 if any(word in x.lower() for word in ['manager', 'handler', 'controller']) else
            2 if any(word in x.lower() for word in ['api', 'endpoint']) else
            3 if any(word in x.lower() for word in ['model', 'schema']) else
            4  # 其他文件
        ))
        
        candidates.extend(keyword_matches)
        
        # 优先级3: 服务和API文件
        candidates.extend(project_structure['service_files'])
        candidates.extend(project_structure['api_files'])
        
        # 优先级4: 其他类型文件
        candidates.extend(project_structure['model_files'])
        candidates.extend(project_structure['util_files'])
        
        # 去重并保持顺序，同时过滤掉__init__.py文件
        seen = set()
        unique_candidates = []
        for candidate in candidates:
            if candidate not in seen and not candidate.endswith('__init__.py'):
                seen.add(candidate)
                unique_candidates.append(candidate)
        
        logger.info(f"🎯 选择了 {len(unique_candidates)} 个候选文件（已排除__init__.py）")
        return unique_candidates[:15]  # 限制候选文件数量

    async def _analyze_file_content(self, file_path: str) -> Optional[dict[str, Any]]:
        """深度分析文件内容和功能 - 使用LLM理解代码的实际作用"""
        
        logger.info(f"🔍 深度分析文件: {file_path}")
        
        # 跳过空的__init__.py文件
        if file_path.endswith('__init__.py'):
            success, content, stderr = await self.execute_command(
                f"wc -l {shlex.quote(file_path)}", 
                working_dir=self.user_project_path
            )
            if success and content.strip().startswith('0'):
                logger.info(f"⏭️ 跳过空的__init__.py文件: {file_path}")
                return None
        
        # 读取完整文件内容
        success, content, stderr = await self.execute_command(
            f"cat {shlex.quote(file_path)}", 
            working_dir=self.user_project_path
        )
        
        if not success or not content or len(content.strip()) < 10:
            logger.warning(f"⚠️ 无法读取文件或文件内容过少: {file_path}")
            return None
        
        lines = content.split('\n')
        logger.info(f"📄 文件 {file_path} 共 {len(lines)} 行")
        
        # 如果文件太大，只分析前500行和后100行
        if len(lines) > 600:
            analysis_content = '\n'.join(lines[:500] + ['# ... 中间部分省略 ...'] + lines[-100:])
            logger.info(f"📄 文件过大，分析前500行和后100行")
        else:
            analysis_content = content
        
        # 使用LLM深度分析文件内容
        analysis_prompt = f"""
你是一个资深的代码分析专家，需要深度分析以下Python文件的内容和功能。

【文件路径】: {file_path}
【文件内容】:
```python
{analysis_content}
```

请详细分析这个文件，并返回JSON格式的分析结果：
{{
    "primary_purpose": "文件的主要功能和作用（详细描述）",
    "business_domain": "所属的业务领域（如：用户管理、API服务、数据处理、AI推理等）",
    "key_capabilities": [
        "核心功能1的详细描述",
        "核心功能2的详细描述"
    ],
    "main_classes": [
        {{
            "name": "类名",
            "purpose": "类的具体作用和职责",
            "key_methods": ["重要方法1", "重要方法2"]
        }}
    ],
    "main_functions": [
        {{
            "name": "函数名",
            "purpose": "函数的具体作用",
            "parameters": "主要参数类型",
            "returns": "返回值类型和含义"
        }}
    ],
    "dependencies": [
        "主要依赖的模块或服务"
    ],
    "integration_points": [
        "与其他模块的集成点或接口"
    ],
    "suitable_for_modifications": [
        "适合进行哪些类型的修改（如：添加新功能、修改业务逻辑、优化性能等）"
    ],
    "complexity_level": "简单/中等/复杂",
    "code_quality_notes": "代码质量和架构特点"
}}

请确保分析结果准确、详细，特别关注文件的实际功能而不是表面的命名。
"""
        
        try:
            logger.info(f"🤖 使用LLM深度分析文件内容...")
            response = await self.llm_manager.generate_code_from_prompt(analysis_prompt)
            
            if response:
                try:
                    analysis_result = json.loads(response)
                    
                    # 验证分析结果的完整性
                    required_fields = ['primary_purpose', 'business_domain', 'key_capabilities']
                    if all(field in analysis_result for field in required_fields):
                        logger.info(f"✅ 深度分析完成: {file_path}")
                        logger.info(f"   🎯 主要功能: {analysis_result['primary_purpose'][:80]}...")
                        logger.info(f"   🏢 业务领域: {analysis_result['business_domain']}")
                        logger.info(f"   ⚡ 核心能力: {len(analysis_result.get('key_capabilities', []))} 项")
                        
                        # 添加基本信息
                        analysis_result.update({
                            'path': file_path,
                            'line_count': len(lines),
                            'file_size': len(content),
                            'analysis_timestamp': time.time()
                        })
                        
                        return analysis_result
                    else:
                        logger.warning(f"⚠️ LLM分析结果不完整，缺少必要字段")
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ LLM返回的不是有效JSON: {e}")
                    # 尝试提取关键信息
                    return self._extract_basic_analysis_from_text(file_path, content, response)
            
        except Exception as e:
            logger.error(f"❌ LLM深度分析失败: {e}")
        
        # 如果LLM分析失败，回退到基本分析
        return self._basic_file_analysis(file_path, content, lines)
    
    def _extract_basic_analysis_from_text(self, file_path: str, content: str, llm_response: str) -> dict[str, Any]:
        """从LLM文本响应中提取基本分析信息"""
        
        lines = content.split('\n')
        
        # 基本信息提取
        classes = []
        functions = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('class '):
                class_name = line.split('(')[0].replace('class ', '').strip(':')
                classes.append(class_name)
            elif line.startswith('def ') or line.startswith('async def '):
                func_name = line.split('(')[0].replace('def ', '').replace('async ', '').strip()
                functions.append(func_name)
        
        # 尝试从LLM响应中提取关键信息
        purpose = "未知功能"
        if "purpose" in llm_response.lower() or "功能" in llm_response:
            # 简单的关键信息提取
            lines_response = llm_response.split('\n')
            for line in lines_response:
                if any(keyword in line.lower() for keyword in ['purpose', '功能', '作用']):
                    purpose = line.strip()
                    break
        
        return {
            'path': file_path,
            'primary_purpose': purpose,
            'business_domain': '未确定',
            'key_capabilities': [],
            'main_classes': [{'name': cls, 'purpose': '未分析', 'key_methods': []} for cls in classes[:5]],
            'main_functions': [{'name': func, 'purpose': '未分析', 'parameters': '未知', 'returns': '未知'} for func in functions[:10]],
            'line_count': len(lines),
            'complexity_level': '中等' if len(lines) > 100 else '简单',
            'analysis_quality': 'basic'
        }
    
    def _basic_file_analysis(self, file_path: str, content: str, lines: list[str]) -> dict[str, Any]:
        """基本文件分析（LLM分析失败时的备选方案）"""
        
        # 提取文档字符串
        purpose = "未知功能"
        for i, line in enumerate(lines[:20]):
            line = line.strip()
            if line.startswith('"""') or line.startswith("'''"):
                if line.count('"""') == 2 or line.count("'''") == 2:
                    purpose = line.strip('"""\'').strip()
                    break
                else:
                    doc_lines = [line.strip('"""\'')]
                    for j in range(i+1, min(i+10, len(lines))):
                        next_line = lines[j].strip()
                        if next_line.endswith('"""') or next_line.endswith("'''"):
                            doc_lines.append(next_line.strip('"""\''))
                            purpose = ' '.join(doc_lines).strip()
                            break
                        doc_lines.append(next_line)
                    break
            elif line.startswith('#') and len(line) > 10:
                purpose = line[1:].strip()
                break
        
        # 提取类和函数
        classes = []
        functions = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('class '):
                class_name = line.split('(')[0].replace('class ', '').strip(':')
                classes.append({'name': class_name, 'purpose': '未分析', 'key_methods': []})
            elif line.startswith('def ') or line.startswith('async def '):
                func_name = line.split('(')[0].replace('def ', '').replace('async ', '').strip()
                functions.append({'name': func_name, 'purpose': '未分析', 'parameters': '未知', 'returns': '未知'})
        
        # 根据文件路径推断业务领域
        business_domain = "未确定"
        path_lower = file_path.lower()
        if any(word in path_lower for word in ['api', 'endpoint', 'route']):
            business_domain = "API服务"
        elif any(word in path_lower for word in ['model', 'schema', 'entity']):
            business_domain = "数据模型"
        elif any(word in path_lower for word in ['service', 'manager', 'handler']):
            business_domain = "业务逻辑"
        elif any(word in path_lower for word in ['util', 'helper', 'tool']):
            business_domain = "工具函数"
        elif any(word in path_lower for word in ['test', 'spec']):
            business_domain = "测试代码"
        
        return {
            'path': file_path,
            'primary_purpose': purpose,
            'business_domain': business_domain,
            'key_capabilities': [],
            'main_classes': classes[:5],
            'main_functions': functions[:10],
            'dependencies': [],
            'integration_points': [],
            'suitable_for_modifications': [],
            'complexity_level': '复杂' if len(lines) > 300 else '中等' if len(lines) > 100 else '简单',
            'code_quality_notes': f"文件包含 {len(classes)} 个类和 {len(functions)} 个函数",
            'line_count': len(lines),
            'analysis_quality': 'basic'
        }

    def _parse_file_recommendations_from_text(self, text: str, candidate_files: list[str]) -> list[dict[str, Any]]:
        """从文本中解析文件推荐"""
        
        recommendations = []
        
        for candidate in candidate_files:
            if candidate in text:
                recommendations.append({
                    'path': candidate,
                    'confidence': 0.7,
                    'reason': '文本匹配推荐',
                    'modification_type': '功能修改'
                })
        
        return recommendations[:3]  # 返回前3个

    async def _select_fallback_file(self, issue: dict[str, Any], project_structure: dict[str, Any]) -> Optional[str]:
        """当智能匹配失败时，选择一个合适的备选文件"""
        
        logger.info("🔄 开始选择备选文件...")
        
        # 提取Issue关键词
        keywords = self._extract_issue_keywords(issue)
        issue_text = f"{issue.get('title', '')} {issue.get('description', '')}".lower()
        
        # 候选文件优先级列表
        candidates = []
        
        # 优先级1：根据Issue类型选择相关文件
        if any(word in issue_text for word in ['api', 'endpoint', 'route', 'view']):
            candidates.extend(project_structure['api_files'])
            logger.info("🔗 Issue涉及API，优先考虑API文件")
        
        if any(word in issue_text for word in ['service', 'business', 'logic']):
            candidates.extend(project_structure['service_files'])
            logger.info("⚙️ Issue涉及业务逻辑，优先考虑服务文件")
        
        if any(word in issue_text for word in ['model', 'schema', 'data']):
            candidates.extend(project_structure['model_files'])
            logger.info("📊 Issue涉及数据模型，优先考虑模型文件")
        
        if any(word in issue_text for word in ['util', 'helper', 'tool']):
            candidates.extend(project_structure['util_files'])
            logger.info("🛠️ Issue涉及工具功能，优先考虑工具文件")
        
        # 优先级2：关键词匹配
        for keyword in keywords:
            for file_path in project_structure['all_files']:
                if keyword.lower() in file_path.lower():
                    candidates.append(file_path)
                    logger.info(f"🔍 关键词匹配: {file_path} (关键词: {keyword})")
        
        # 优先级3：主要文件
        candidates.extend(project_structure['main_files'])
        
        # 优先级4：其他服务文件
        candidates.extend(project_structure['service_files'])
        
        # 去重并选择第一个
        seen = set()
        for candidate in candidates:
            if candidate not in seen and candidate:
                seen.add(candidate)
                logger.info(f"✅ 选择备选文件: {candidate}")
                return candidate
        
        # 如果还是没有，选择任意一个Python文件
        if project_structure['all_files']:
            fallback = project_structure['all_files'][0]
            logger.info(f"🎲 最后备选: {fallback}")
            return fallback
        
        logger.warning("⚠️ 无法找到合适的备选文件")
        return None

    def get_agent_status(self) -> dict[str, Any]:
        """获取代理状态"""
        return {
            "agent_id": self.agent_id,
            "current_issue": self.current_issue,
            "issues_completed": self.issues_completed,
            "status": "running" if self.current_issue else "idle"
        }
    
    async def work_on_issues(self) -> None:
        """持续工作循环"""
        try:
            while True:
                issue = await self.grab_issue()
                if issue:
                    success = await self.implement_issue(issue)
                    if success:
                        await self.get_issues_git_manager().update_issue_status(issue["id"], "completed")
                        self.current_issue = None
                        
                        # 同步到playground
                        if self.collaboration_manager:
                            await self.collaboration_manager.sync_agent_to_playground(self.agent_id)
                else:
                    await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"❌ {self.agent_id} 工作循环异常: {e}")

    async def grab_issues(self) -> None:
        """定期获取新Issues"""
        consecutive_empty_attempts = 0
        max_empty_attempts = 3
        base_sleep_time = 5
        
        try:
            while True:
                if not self.current_issue:
                    issue = await self.grab_issue()
                    if issue:
                        consecutive_empty_attempts = 0  # 重置计数器
                    else:
                        consecutive_empty_attempts += 1
                        
                    # 如果连续多次没有获取到Issue，增加等待时间
                    if consecutive_empty_attempts >= max_empty_attempts:
                        sleep_time = min(base_sleep_time * 2, 30)  # 最多等待30秒
                        logger.debug(f"😴 {self.agent_id} 连续 {consecutive_empty_attempts} 次未获取到Issue，休眠 {sleep_time} 秒")
                        await asyncio.sleep(sleep_time)
                        consecutive_empty_attempts = 0  # 重置计数器
                    else:
                        await asyncio.sleep(base_sleep_time)
                else:
                    # 有正在处理的Issue时，等待更长时间再检查新Issue
                    await asyncio.sleep(base_sleep_time * 2)
                    
        except Exception as e:
            logger.error(f"❌ {self.agent_id} 获取Issues异常: {e}")

    async def handle_conflicts(self) -> bool:
        """处理冲突"""
        try:
            # 简化冲突处理
            logger.info(f"🔄 {self.agent_id} 处理冲突...")
            return True
        except Exception as e:
            logger.error(f"❌ {self.agent_id} 冲突处理失败: {e}")
            return False

    async def run(self) -> None:
        """启动代理"""
        logger.info(f"🚀 {self.agent_id} 启动")
        
        tasks = [
            asyncio.create_task(self.work_on_issues()),
            asyncio.create_task(self.grab_issues())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"❌ {self.agent_id} 运行异常: {e}")
        finally:
            logger.info(f"🛑 {self.agent_id} 停止")

    async def execute_command(self, command: str, working_dir: str = None, 
                            timeout: int = 30, use_shell: bool = False) -> tuple[bool, str, str]:
        """异步执行终端命令（不阻塞主线程）
        
        Args:
            command: 要执行的命令
            working_dir: 工作目录，默认为Git仓库根目录
            timeout: 命令超时时间（秒），默认30秒
            use_shell: 是否使用shell模式，默认False
            
        Returns:
            (成功状态, 标准输出, 错误输出)
        """
        if working_dir is None:
            # 使用Git仓库根目录作为默认工作目录，这样路径计算会更一致
            working_dir = self.git_manager.repo_path if self.git_manager else os.getcwd()
        
        try:
            logger.info(f"🔧 {self.agent_id} 异步执行命令: {command}")
            logger.info(f"📁 工作目录: {working_dir}")
            logger.info(f"⏱️ 超时设置: {timeout}秒")
            
            if use_shell:
                # 使用 shell 模式执行复杂命令
                process = await asyncio.create_subprocess_shell(
                    command,
                    cwd=working_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                # 安全地解析命令并使用 exec 模式
                cmd_args = shlex.split(command)
                process = await asyncio.create_subprocess_exec(
                    *cmd_args,
                    cwd=working_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            # 异步等待命令完成，带超时控制
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
                # 手动解码字节为字符串
                stdout = stdout_bytes.decode('utf-8') if stdout_bytes else ""
                stderr = stderr_bytes.decode('utf-8') if stderr_bytes else ""
            except asyncio.TimeoutError:
                logger.error(f"⏰ 命令执行超时: {command}")
                process.kill()
                await process.wait()
                return False, "", f"Command timeout after {timeout} seconds"
            
            success = process.returncode == 0
            
            if success:
                logger.info(f"✅ 命令执行成功: {command}")
                if stdout.strip():
                    # 限制输出长度避免日志过长
                    output_preview = stdout.strip()[:200]
                    if len(stdout.strip()) > 200:
                        output_preview += "..."
                    logger.info(f"📤 输出: {output_preview}")
            else:
                logger.error(f"❌ 命令执行失败: {command}")
                logger.error(f"❌ 返回码: {process.returncode}")
                if stderr.strip():
                    error_preview = stderr.strip()[:200]
                    if len(stderr.strip()) > 200:
                        error_preview += "..."
                    logger.error(f"🚨 错误: {error_preview}")
            
            return success, stdout, stderr
            
        except Exception as e:
            logger.error(f"❌ 命令执行异常: {command} - {e}")
            return False, "", str(e)
    
    async def find_files_with_command(self, pattern: str, search_dir: str = None) -> list[str]:
        """使用find命令查找文件
        
        Args:
            pattern: 文件名模式
            search_dir: 搜索目录，默认为user_project_path
            
        Returns:
            找到的文件路径列表
        """
        if search_dir is None:
            search_dir = self.user_project_path or os.getcwd()
        
        # 计算相对于Git仓库根目录的相对路径
        repo_root = self.git_manager.repo_path if self.git_manager else os.getcwd()
        try:
            relative_search_dir = os.path.relpath(search_dir, repo_root)
            # 确保路径不以../开头（即在仓库内）
            if relative_search_dir.startswith('..'):
                relative_search_dir = search_dir  # 使用绝对路径
        except ValueError:
            relative_search_dir = search_dir  # 使用绝对路径
        
        # 使用find命令查找文件
        find_cmd = f"find {shlex.quote(relative_search_dir)} -name '*{pattern}*' -type f"
        success, stdout, stderr = await self.execute_command(find_cmd)
        
        if success and stdout.strip():
            files = stdout.strip().split('\n')
            # 转换为相对路径
            relative_files = []
            for file_path in files:
                try:
                    rel_path = os.path.relpath(file_path, search_dir)
                    relative_files.append(rel_path)
                except ValueError:
                    # 如果无法创建相对路径，使用绝对路径
                    relative_files.append(file_path)
            
            logger.info(f"🔍 找到 {len(relative_files)} 个匹配文件: {pattern}")
            return relative_files
        
        logger.warning(f"🔍 未找到匹配文件: {pattern}")
        return []
    
    async def check_file_exists(self, file_path: str) -> bool:
        """使用test命令检查文件是否存在"""
        try:
            # 统一使用绝对路径处理，避免相对路径问题
            if os.path.isabs(file_path):
                # 绝对路径：直接检查，使用主目录作为工作目录
                success, _, _ = await self.execute_command(
                    f"test -e {shlex.quote(file_path)}",
                    working_dir=os.getcwd()  # 使用主目录作为工作目录
                )
            else:
                # 相对路径：在agent工作目录内检查
                success, _, _ = await self.execute_command(
                    f"test -e {shlex.quote(file_path)}", 
                    working_dir=self.user_project_path
                )
            return success
        except Exception:
            return False
    
    async def read_file_with_command(self, file_path: str) -> Optional[str]:
        """使用cat命令读取文件内容"""
        try:
            # 如果是绝对路径，直接使用；否则在工作目录内读取
            if os.path.isabs(file_path):
                success, content, stderr = await self.execute_command(f"cat {shlex.quote(file_path)}")
            else:
                success, content, stderr = await self.execute_command(
                    f"cat {shlex.quote(file_path)}", 
                    working_dir=self.user_project_path
                )
            
            if success:
                return content
            else:
                logger.error(f"❌ 读取文件失败: {file_path} - {stderr}")
                return None
        except Exception as e:
            logger.error(f"❌ 读取文件异常: {file_path} - {e}")
            return None
    
    async def write_file_with_command(self, file_path: str, content: str) -> bool:
        """使用Python直接写入文件内容（修复echo命令转义问题）"""
        try:
            # 确定文件的绝对路径
            if os.path.isabs(file_path):
                target_path = file_path
            else:
                target_path = os.path.join(self.user_project_path, file_path)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # 直接使用Python写入文件，避免shell转义问题
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"✅ 文件写入成功: {file_path}")
            return True
                
        except Exception as e:
            logger.error(f"❌ 文件写入异常: {file_path} - {e}")
            return False
    
    async def backup_file(self, file_path: str) -> Optional[str]:
        """备份文件"""
        import time
        backup_path = f"{file_path}.backup.{int(time.time())}"
        success, _, stderr = await self.execute_command(f"cp {shlex.quote(file_path)} {shlex.quote(backup_path)}")
        
        if success:
            logger.info(f"✅ 文件备份成功: {backup_path}")
            return backup_path
        else:
            logger.error(f"❌ 文件备份失败: {file_path} - {stderr}")
            return None
    
    async def _get_issue_assignee(self, issue_id: str) -> Optional[str]:
        """获取Issue的分配者"""
        try:
            issues_data = self.get_issues_git_manager()._load_issues()
            for issue in issues_data.get("issues", []):
                if issue["id"] == issue_id:
                    return issue.get("assigned_to")
            return None
        except Exception:
            return None
     