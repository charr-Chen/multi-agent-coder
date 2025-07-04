"""
运行脚本
用于启动多智能体编码系统
"""

import os
import logging.handlers
import asyncio
import queue
import threading

import coloredlogs

coloredlogs.install()

from src.multi_agent_coder.git_utils import GitManager
from src.multi_agent_coder.multi_repo_manager import MultiRepoManager
from src.multi_agent_coder.llm_utils import LLMManager
from src.multi_agent_coder.agents import CommenterAgent, CoderAgent
from src.multi_agent_coder.collaboration import CollaborationManager
from src.multi_agent_coder.config import get_config

# 创建日志队列和处理器
log_queue = queue.Queue()
queue_handler = logging.handlers.QueueHandler(log_queue)

# 创建文件和控制台处理器
file_handler = logging.FileHandler('multi_agent_coder.log', encoding='utf-8')
console_handler = logging.StreamHandler()

# 设置格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# 创建监听器
listener = logging.handlers.QueueListener(log_queue, file_handler, console_handler)

# 配置根日志器
logging.basicConfig(
    level=logging.INFO,
    handlers=[queue_handler]
)

# 启动监听器
listener.start()

# 设置特定模块的日志级别，减少噪音
logging.getLogger('multi_agent_coder.agents.memory_manager').setLevel(logging.WARNING)
logging.getLogger('multi_agent_coder.agents.tools').setLevel(logging.WARNING)
logging.getLogger('openai').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def get_user_repo():
    """交互式获取用户Git仓库路径"""
    print("=" * 60)
    print("🚀 Multi-Agent Coder - 智能体协作编程系统")
    print("=" * 60)
    print()
    print("💡 请指定你要使用的Git仓库：")
    print("   - 本地项目路径（如：/path/to/project）")
    print("   - GitHub仓库URL（如：https://github.com/user/repo.git）")
    print("   - 留空使用当前目录")
    print()
    
    user_projects_dir = os.path.join(os.getcwd(), "user_projects")
    os.makedirs(user_projects_dir, exist_ok=True)
    
    while True:
        try:
            repo_input = input("📁 Git仓库路径或URL: ").strip()
            
            # 如果用户按回车，使用 user_projects 目录下的当前目录名
            if not repo_input:
                repo_path = os.path.join(user_projects_dir, "current_project")
                print(f"📍 使用 user_projects 目录: {repo_path}")
                if not os.path.exists(repo_path):
                    os.makedirs(repo_path)
            
            # 检查是否是GitHub URL
            elif repo_input.startswith(('https://github.com/', 'git@github.com:', 'http://github.com/')):
                print(f"🌐 检测到GitHub仓库: {repo_input}")
                
                # 提取仓库名
                if repo_input.endswith('.git'):
                    repo_name = repo_input.split('/')[-1][:-4]
                else:
                    repo_name = repo_input.split('/')[-1]
                
                # 在 user_projects 目录下创建克隆目录
                clone_dir = os.path.join(user_projects_dir, repo_name)
                
                # 检查目录是否已存在
                if os.path.exists(clone_dir):
                    print(f"⚠️  目录已存在: {clone_dir}")
                    choice = input("🤔 是否使用现有目录？(y/n): ").strip().lower()
                    if choice in ['y', 'yes', '是']:
                        repo_path = clone_dir
                        print(f"✅ 使用现有目录: {repo_path}")
                    else:
                        # 询问新的目录名
                        new_name = input(f"📝 请输入新的目录名（默认：{repo_name}_clone）: ").strip()
                        if not new_name:
                            new_name = f"{repo_name}_clone"
                        clone_dir = os.path.join(user_projects_dir, new_name)
                        
                        print(f"📥 克隆仓库到: {clone_dir}")
                        try:
                            import subprocess
                            result = subprocess.run(['git', 'clone', repo_input, clone_dir], 
                                                  capture_output=True, text=True)
                            if result.returncode == 0:
                                print(f"✅ 成功克隆仓库: {clone_dir}")
                                repo_path = clone_dir
                            else:
                                print(f"❌ 克隆失败: {result.stderr}")
                                continue
                        except Exception as e:
                            print(f"❌ 克隆过程出错: {e}")
                            continue
                else:
                    print(f"📥 克隆仓库到: {clone_dir}")
                    try:
                        import subprocess
                        result = subprocess.run(['git', 'clone', repo_input, clone_dir], 
                                              capture_output=True, text=True)
                        if result.returncode == 0:
                            print(f"✅ 成功克隆仓库: {clone_dir}")
                            repo_path = clone_dir
                        else:
                            print(f"❌ 克隆失败: {result.stderr}")
                            print("💡 请检查网络连接和仓库URL是否正确")
                            continue
                    except Exception as e:
                        print(f"❌ 克隆过程出错: {e}")
                        print("💡 请确保已安装Git并且网络连接正常")
                        continue
            
            else:
                # 处理本地路径，统一放到 user_projects 目录下
                abs_input_path = os.path.abspath(os.path.expanduser(repo_input))
                repo_name = os.path.basename(abs_input_path.rstrip("/"))
                repo_path = os.path.join(user_projects_dir, repo_name)
                
                # 如果源路径存在且不是 user_projects 目录下的，复制到 user_projects 下
                if os.path.exists(abs_input_path) and abs_input_path != repo_path:
                    import shutil
                    if not os.path.exists(repo_path):
                        shutil.copytree(abs_input_path, repo_path)
                        print(f"✅ 已将本地项目复制到: {repo_path}")
                elif not os.path.exists(abs_input_path):
                    print(f"❌ 路径不存在: {abs_input_path}")
                    print("💡 请检查路径是否正确，或输入GitHub仓库URL进行克隆")
                    continue
            
            # 检查是否是Git仓库
            git_dir = os.path.join(repo_path, '.git')
            if not os.path.exists(git_dir):
                print(f"⚠️  这不是一个Git仓库: {repo_path}")
                
                # 询问是否初始化
                while True:
                    init_choice = input("🤔 是否要初始化为Git仓库？(y/n): ").strip().lower()
                    if init_choice in ['y', 'yes', '是']:
                        try:
                            current_dir = os.getcwd()
                            os.chdir(repo_path)
                            os.system('git init')
                            os.chdir(current_dir)
                            print(f"✅ 已初始化Git仓库: {repo_path}")
                            break
                        except Exception as e:
                            print(f"❌ 初始化失败: {e}")
                            break
                    elif init_choice in ['n', 'no', '否']:
                        print("💡 请选择一个已经是Git仓库的目录，或者手动运行 'git init'")
                        break
                    else:
                        print("⚠️ 请输入 y(是) 或 n(否)")
                
                if init_choice in ['n', 'no', '否']:
                    continue
            
            # 验证成功
            print(f"✅ 选择Git仓库: {repo_path}")
            print()
            
            # 检查用户项目是否包含Issues文件（仅作参考，实际使用playground的Issues）
            issues_file = os.path.join(repo_path, '.issues.json')
            if os.path.exists(issues_file):
                try:
                    import json
                    with open(issues_file, 'r', encoding='utf-8') as f:
                        issues_data = json.load(f)
                    
                    if issues_data.get('issues') and len(issues_data['issues']) > 0:
                        print(f"📋 发现用户项目中有 {len(issues_data['issues'])} 个Issues")
                        print("💡 注意：系统将使用独立的playground仓库管理Issues")
                    else:
                        print("✅ 用户项目Issues文件为空")
                except Exception as e:
                    print(f"⚠️  检查用户项目Issues文件时出错: {e}")
            else:
                print("📝 用户项目中没有Issues文件，系统将创建独立的Issues管理")
            
            return repo_path
            
        except KeyboardInterrupt:
            print("\n\n👋 用户取消，退出系统")
            exit(0)
        except Exception as e:
            print(f"❌ 发生错误: {e}")
            print("💡 请重新输入路径或URL")

async def main():
    """主函数"""
    try:
        # 🆕 交互式获取用户Git仓库
        user_repo_path = get_user_repo()
        
        # 获取配置
        config = get_config()
        
        # 🆕 将用户指定的仓库路径覆盖配置
        config["system"]["repo_path"] = user_repo_path
        
        # 获取 API 密钥
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ 未设置 OPENAI_API_KEY 环境变量")
            print("💡 请设置你的OpenAI API密钥：")
            print("   export OPENAI_API_KEY=\"your-api-key\"")
            raise ValueError("未设置 OPENAI_API_KEY 环境变量")
        
        # 获取代理配置（可选）
        proxy_url = os.getenv("OPENAI_PROXY_URL")
        if proxy_url:
            print(f"🌐 使用代理: {proxy_url}")
        
        print("🤖 初始化LLM管理器...")
        # 初始化 LLM 管理器
        llm_manager = LLMManager(api_key, proxy_url=proxy_url)
        
        # 检查是否使用多仓库模式
        if config["system"]["use_separate_repos"]:
            print("📚 启动多仓库协作模式...")
            logger.info("使用多仓库模式")
            
            # 🆕 playground_repo设为空字符串，创建独立的协作空间
            config["system"]["playground_repo"] = ""  # 不使用用户仓库作为playground
            
            # 初始化多仓库管理器
            multi_repo_manager = MultiRepoManager(
                config["system"]["playground_repo"],
                config["system"]["agent_repos_dir"]
            )
            
            # 设置playground仓库
            playground_git_manager = await multi_repo_manager.setup_playground_repo()
            
            # 🆕 关键步骤：复制用户项目内容到playground仓库，让agent能学习参考代码
            logger.info("📁 复制用户项目内容到playground仓库...")
            try:
                # 复制用户项目的所有内容到playground（除了.git目录）
                import shutil
                import fnmatch
                
                # 🆕 智能项目检测：如果用户选择的是当前目录（我们的多智能体系统），
                # 优先查找AgentGPT目录作为参考项目
                current_dir = os.path.abspath(os.getcwd())
                user_dir = os.path.abspath(user_repo_path)
                
                if user_dir == current_dir:
                    logger.info("检测到用户选择当前目录")
                    # 检查是否有AgentGPT目录
                    agentgpt_path = os.path.join(user_repo_path, "AgentGPT")
                    if os.path.exists(agentgpt_path):
                        logger.info("找到AgentGPT项目，将其作为参考项目")
                        source_path = agentgpt_path
                        project_name = "AgentGPT"
                    else:
                        logger.warning("⚠️ 在当前目录未找到AgentGPT项目")
                        logger.info("将复制当前目录的内容（排除系统文件）")
                        source_path = user_repo_path
                        project_name = "当前项目"
                else:
                    logger.info(f"复制用户指定的项目: {user_repo_path}")
                    source_path = user_repo_path
                    project_name = os.path.basename(user_repo_path)
                
                # 通用的文件过滤函数
                def should_copy_file(root, name, source_root):
                    """判断是否应该复制文件"""
                    # 基本的忽略模式
                    ignore_patterns = [
                        '.git', '.git/*',
                        '__pycache__', '*.pyc', '*.pyo',
                        '.DS_Store', 'Thumbs.db',
                        'node_modules',
                        '.pytest_cache',
                        '*.log',
                        '.coverage',
                        '.venv', 'venv',
                        '.env', '.env.*'
                    ]
                    
                    # 如果源路径是当前目录，额外排除我们系统的文件
                    if os.path.abspath(source_root) == current_dir:
                        ignore_patterns.extend([
                            'agent_repos', 'agent_repos/*',
                            'src/multi_agent_coder*', 
                            'test_*.py',
                            'pyproject.toml',
                            'uv.lock',
                            'requirements.txt',
                            '*.egg-info', '*.egg-info/*',
                            'run.py',
                            'test_startup.py'
                        ])
                    
                    # 检查是否匹配忽略模式
                    for pattern in ignore_patterns:
                        if fnmatch.fnmatch(name, pattern):
                            return False
                    
                    return True
                
                # 执行复制
                copied_files = 0
                playground_path = playground_git_manager.repo_path
                
                for root, dirs, files in os.walk(source_path):
                    # 过滤目录
                    dirs[:] = [d for d in dirs if should_copy_file(root, d, source_path)]
                    
                    for file in files:
                        if not should_copy_file(root, file, source_path):
                            continue
                        
                        src_file = os.path.join(root, file)
                        rel_path = os.path.relpath(src_file, source_path)
                        dst_file = os.path.join(playground_path, rel_path)
                        
                        # 确保目标目录存在
                        dst_dir = os.path.dirname(dst_file)
                        if dst_dir:
                            os.makedirs(dst_dir, exist_ok=True)
                        
                        try:
                            shutil.copy2(src_file, dst_file)
                            copied_files += 1
                        except Exception as e:
                            logger.warning(f"⚠️ 复制文件失败 {rel_path}: {e}")
                
                logger.info(f"✅ 成功复制 {copied_files} 个{project_name}文件到playground仓库")
                
                # 提交复制的内容
                if copied_files > 0:
                    await playground_git_manager.commit_changes(
                        f"复制{project_name}内容作为参考代码",
                        ["."]
                    )
                
            except Exception as e:
                logger.error(f"❌ 复制用户项目内容失败: {e}")
                logger.warning("⚠️ Agent将在没有参考代码的情况下工作")
            
            # 🆕 关键步骤：确保playground仓库有Issues文件
            logger.info("🔄 设置playground仓库的Issues文件...")
            try:
                # 检查playground仓库是否已有Issues文件
                playground_issues_file = os.path.join(playground_git_manager.repo_path, ".issues.json")
                
                if not os.path.exists(playground_issues_file):
                    # 创建空的Issues文件
                    import json
                    with open(playground_issues_file, 'w', encoding='utf-8') as f:
                        json.dump({"issues": []}, f, indent=2, ensure_ascii=False)
                    
                    # 提交到playground仓库
                    await playground_git_manager.commit_changes(
                        "初始化Issues文件",
                        [".issues.json"]
                    )
                    
                    logger.info("✅ 在playground仓库创建了Issues文件")
                else:
                    logger.info("✅ playground仓库已有Issues文件")
                    
            except Exception as e:
                logger.error(f"❌ 设置playground仓库Issues文件失败: {e}")
            
            # 🆕 创建协作管理器（使用playground仓库作为主仓库，使用独立的LLM管理器）
            collaboration_llm_manager = LLMManager(api_key, proxy_url=proxy_url)
            collaboration_manager = CollaborationManager(playground_git_manager, collaboration_llm_manager)
            logger.info("✅ 创建协作管理器")
            
            # 🆕 为Commenter创建独立的LLM管理器，避免并发竞争
            commenter_llm_manager = LLMManager(api_key, proxy_url=proxy_url)
            # 创建评论员代理（使用playground仓库）
            commenter = CommenterAgent("commenter", playground_git_manager, commenter_llm_manager)
            commenter.set_collaboration_manager(collaboration_manager)
            
            # 创建编码员代理（每个使用独立仓库和独立的LLM管理器）
            coders = []
            for i in range(config["system"]["num_coders"]):
                agent_id = f"coder_{i}"
                # 为每个coder设置独立仓库
                agent_git_manager = await multi_repo_manager.setup_agent_repo(agent_id)
                # 🆕 使用agent的独立工作目录，而不是用户原始项目路径
                agent_work_path = agent_git_manager.repo_path
                # 🆕 为每个coder创建独立的LLM管理器，避免并发竞争
                coder_llm_manager = LLMManager(api_key, proxy_url=proxy_url)
                coder = CoderAgent(f"coder_{i}", coder_llm_manager, agent_work_path)
                # 设置playground仓库管理器，用于访问Issues
                coder.set_playground_git_manager(playground_git_manager)
                # 设置协作管理器，启用Pull Request流程
                coder.set_collaboration_manager(collaboration_manager)
                # 设置多仓库管理器，用于同步工作
                coder.set_multi_repo_manager(multi_repo_manager)
                coders.append(coder)
            
            print(f"🎉 创建了 {len(coders)} 个编码员代理，每个都有独立仓库")
            print("🔄 启用Pull Request协作流程")
            
        else:
            print("📝 启动单仓库模式...")
            logger.info("使用单仓库模式")
            
            # 🆕 使用用户指定的仓库路径
            repo_path = user_repo_path
            logger.info(f"使用仓库路径: {repo_path}")
            
            # 初始化 Git 管理器
            git_manager = GitManager(repo_path)
            
            # 创建评论员代理（使用独立的LLM管理器）
            commenter_llm_manager = LLMManager(api_key, proxy_url=proxy_url)
            commenter = CommenterAgent("commenter", git_manager, commenter_llm_manager)
            
            # 创建编码员代理（每个使用独立的LLM管理器）
            coders = []
            for i in range(config["system"]["num_coders"]):
                # 🆕 为每个coder创建独立的LLM管理器，避免并发竞争
                coder_llm_manager = LLMManager(api_key, proxy_url=proxy_url)
                # 🆕 在单仓库模式下，使用用户指定的仓库路径
                coder = CoderAgent(f"coder_{i}", coder_llm_manager, user_repo_path)
                coders.append(coder)
        
        # 启动所有代理
        print("\n" + "=" * 60)
        print("🚀 正在启动多智能体协作系统...")
        print(f"📊 系统配置: 1个Commenter + {len(coders)}个Coder")
        print(f"📁 工作仓库: {user_repo_path}")
        print("⏳ 请稍等，系统正在初始化...")
        print("=" * 60)
        print()
        
        # 🆕 增加用户指导信息
        print("💡 系统启动完成后，你可以:")
        print("   1️⃣  查看日志文件: multi_agent_coder.log")
        print("   2️⃣  检查工作成果: python check_agents_work.py")
        print("   3️⃣  查看Memory记录: ls -la .memory/")
        print("   4️⃣  查看工作报告: ls -la reports/ 或 agent_repos/playground/reports/")
        print("   5️⃣  查看代码提交: cd agent_repos/playground && git log --oneline")
        print("   6️⃣  使用 Ctrl+C 停止系统")
        print()
        print("🔍 实时监控AI Agents工作状态...")
        print("⚠️  如果长时间没有输出，可能是网络问题或LLM API调用失败")
        print("=" * 60)
        print()
        
        # 设置日志级别，减少启动时的噪音
        logging.getLogger('src.multi_agent_coder.agents.coder').setLevel(logging.WARNING)
        logging.getLogger('src.multi_agent_coder.git_utils').setLevel(logging.WARNING)
        logging.getLogger('src.multi_agent_coder.multi_repo_manager').setLevel(logging.WARNING)
        
        tasks = [
            asyncio.create_task(commenter.run()),
            *[asyncio.create_task(coder.run()) for coder in coders]
        ]
        
        # 等待所有任务完成
        await asyncio.gather(*tasks)
        
    except Exception as e:
        logger.error(f"运行出错: {e}")
        import traceback
        logger.error(f"🔍 错误详情:\n{traceback.format_exc()}")
    finally:
        # 清理日志监听器
        listener.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        # 确保日志监听器被正确关闭
        listener.stop() 