#!/usr/bin/env python3
"""
三个CoderAgent异步编程示例
展示如何让多个CoderAgent并行处理不同的Issues
"""

import os
import sys
import asyncio
import logging
from typing import List, Dict, Any

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.multi_agent_coder.llm_utils import LLMManager
from src.multi_agent_coder.agents.coder import CoderAgent
from src.multi_agent_coder.agents.memory_manager import MemoryManager

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AsyncCoderManager:
    """异步Coder管理器 - 管理多个CoderAgent的并行工作"""
    
    def __init__(self, api_key: str, user_project_path: str, proxy_url: str = None):
        """初始化异步Coder管理器
        
        Args:
            api_key: OpenAI API密钥
            user_project_path: 用户项目路径
            proxy_url: 代理URL（可选）
        """
        self.api_key = api_key
        self.user_project_path = user_project_path
        self.proxy_url = proxy_url
        self.coders: List[CoderAgent] = []
        
        # 创建三个不同专长的CoderAgent
        self._create_coders()
        
        logger.info(f"初始化异步Coder管理器，创建了 {len(self.coders)} 个CoderAgent")
    
    def _create_coders(self):
        """创建三个不同专长的CoderAgent"""
        coder_configs = [
            {
                "agent_id": "frontend_coder",
                "specialty": "前端开发",
                "description": "专注于React/Vue/TypeScript等前端技术"
            },
            {
                "agent_id": "backend_coder", 
                "specialty": "后端开发",
                "description": "专注于Python/Node.js/数据库等后端技术"
            },
            {
                "agent_id": "devops_coder",
                "specialty": "DevOps/部署",
                "description": "专注于Docker/Kubernetes/CI/CD等运维技术"
            }
        ]
        
        for config in coder_configs:
            # 为每个coder创建独立的LLM管理器，避免并发竞争
            llm_manager = LLMManager(self.api_key, proxy_url=self.proxy_url)
            
            # 创建记忆管理器
            memory_manager = MemoryManager(config["agent_id"])
            
            # 创建CoderAgent
            coder = CoderAgent(
                agent_id=config["agent_id"],
                llm_manager=llm_manager,
                user_project_path=self.user_project_path,
                memory_manager=memory_manager
            )
            
            # 记录专长信息
            memory_manager.store_memory(f"我是{config['specialty']}专家: {config['description']}")
            
            self.coders.append(coder)
            logger.info(f"创建CoderAgent: {config['agent_id']} - {config['specialty']}")
    
    async def assign_issues_async(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """异步分配Issues给不同的CoderAgent
        
        Args:
            issues: Issue列表
            
        Returns:
            处理结果列表
        """
        logger.info(f"开始异步处理 {len(issues)} 个Issues")
        
        # 为每个Issue分配最合适的CoderAgent
        assignments = self._assign_issues_to_coders(issues)
        
        # 创建异步任务
        tasks = []
        for coder, assigned_issues in assignments.items():
            for issue in assigned_issues:
                task = asyncio.create_task(
                    self._process_issue_with_coder(coder, issue)
                )
                tasks.append(task)
        
        # 并行执行所有任务
        logger.info(f"启动 {len(tasks)} 个异步任务")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"任务 {i} 执行失败: {result}")
                processed_results.append({
                    "success": False,
                    "error": str(result),
                    "issue": issues[i] if i < len(issues) else "unknown"
                })
            else:
                processed_results.append(result)
        
        logger.info(f"异步处理完成，成功处理 {len([r for r in processed_results if r['success']])} 个Issues")
        return processed_results
    
    def _assign_issues_to_coders(self, issues: List[Dict[str, Any]]) -> Dict[CoderAgent, List[Dict[str, Any]]]:
        """将Issues分配给最合适的CoderAgent"""
        assignments = {coder: [] for coder in self.coders}
        
        for issue in issues:
            # 简单的分配逻辑：根据Issue标题和描述判断最适合的coder
            title = issue.get('title', '').lower()
            description = issue.get('description', '').lower()
            
            if any(keyword in title or keyword in description for keyword in ['frontend', 'ui', 'react', 'vue', 'typescript', 'css']):
                assignments[self.coders[0]].append(issue)  # frontend_coder
            elif any(keyword in title or keyword in description for keyword in ['backend', 'api', 'database', 'server', 'python', 'node']):
                assignments[self.coders[1]].append(issue)  # backend_coder
            elif any(keyword in title or keyword in description for keyword in ['deploy', 'docker', 'kubernetes', 'ci/cd', 'devops']):
                assignments[self.coders[2]].append(issue)  # devops_coder
            else:
                # 默认分配给backend_coder
                assignments[self.coders[1]].append(issue)
        
        return assignments
    
    async def _process_issue_with_coder(self, coder: CoderAgent, issue: Dict[str, Any]) -> Dict[str, Any]:
        """使用指定的CoderAgent处理Issue"""
        try:
            logger.info(f"CoderAgent {coder.agent_id} 开始处理Issue: {issue.get('title', '未知')}")
            
            # 异步处理Issue
            result = await coder.implement_issue(issue, max_iterations=10)
            
            # 添加coder信息到结果
            result["coder_id"] = coder.agent_id
            result["issue"] = issue
            
            logger.info(f"CoderAgent {coder.agent_id} 完成Issue: {issue.get('title', '未知')} - 成功: {result['success']}")
            
            return result
            
        except Exception as e:
            logger.error(f"CoderAgent {coder.agent_id} 处理Issue失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "coder_id": coder.agent_id,
                "issue": issue
            }
    
    async def get_all_memory_summaries(self) -> Dict[str, Dict[str, Any]]:
        """获取所有CoderAgent的记忆总结"""
        summaries = {}
        for coder in self.coders:
            summaries[coder.agent_id] = coder.get_memory_summary()
        return summaries
    
    async def export_all_memories(self, output_dir: str = "memories_export"):
        """导出所有CoderAgent的记忆"""
        os.makedirs(output_dir, exist_ok=True)
        
        for coder in self.coders:
            output_path = os.path.join(output_dir, f"{coder.agent_id}_memories.txt")
            success = coder.export_memories(output_path)
            if success:
                logger.info(f"导出 {coder.agent_id} 的记忆到: {output_path}")
            else:
                logger.error(f"导出 {coder.agent_id} 的记忆失败")

async def main():
    """主函数 - 演示三个CoderAgent的异步编程"""
    print("🚀 开始三个CoderAgent异步编程演示...")
    
    # 配置
    api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    user_project_path = "/tmp/async_coder_project"
    
    # 确保项目目录存在
    os.makedirs(user_project_path, exist_ok=True)
    
    # 创建异步Coder管理器
    async_manager = AsyncCoderManager(api_key, user_project_path)
    
    # 定义要处理的Issues
    issues = [
        {
            "title": "创建React组件库",
            "description": "开发一个可复用的React组件库，包含Button、Input、Modal等基础组件"
        },
        {
            "title": "实现用户认证API",
            "description": "创建用户注册、登录、JWT token验证的后端API"
        },
        {
            "title": "配置Docker部署",
            "description": "为项目创建Dockerfile和docker-compose.yml，支持容器化部署"
        },
        {
            "title": "优化数据库查询",
            "description": "分析和优化现有的数据库查询性能，添加适当的索引"
        },
        {
            "title": "实现前端路由",
            "description": "使用React Router实现前端路由系统，支持页面导航"
        }
    ]
    
    print(f"📋 准备处理 {len(issues)} 个Issues...")
    
    # 异步处理所有Issues
    start_time = asyncio.get_event_loop().time()
    results = await async_manager.assign_issues_async(issues)
    end_time = asyncio.get_event_loop().time()
    
    # 显示结果
    print(f"\n=== 异步处理结果 ===")
    print(f"⏱️  总耗时: {end_time - start_time:.2f} 秒")
    
    success_count = 0
    for result in results:
        status = "✅" if result.get("success") else "❌"
        coder_id = result.get("coder_id", "unknown")
        issue_title = result.get("issue", {}).get("title", "unknown")
        print(f"{status} {coder_id}: {issue_title}")
        
        if result.get("success"):
            success_count += 1
        else:
            print(f"   错误: {result.get('error', '未知错误')}")
    
    print(f"\n📊 成功率: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")
    
    # 获取记忆总结
    print(f"\n=== 各CoderAgent记忆总结 ===")
    summaries = await async_manager.get_all_memory_summaries()
    for coder_id, summary in summaries.items():
        print(f"🧠 {coder_id}: {summary['total_memories']} 条记忆")
    
    # 导出记忆
    print(f"\n=== 导出记忆 ===")
    await async_manager.export_all_memories()
    
    print(f"\n🎉 异步编程演示完成！")

if __name__ == "__main__":
    asyncio.run(main()) 