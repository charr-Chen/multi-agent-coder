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
logging.getLogger('multi_agent_coder.agents.thinking').setLevel(logging.WARNING)
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
    
    while True:
        try:
            repo_input = input("📁 Git仓库路径或URL: ").strip()
            
            # 如果用户按回车，使用当前目录
            if not repo_input:
                repo_path = os.getcwd()
                print(f"📍 使用当前目录: {repo_path}")
            
            # 检查是否是GitHub URL
            elif repo_input.startswith(('https://github.com/', 'git@github.com:', 'http://github.com/')):
                print(f"🌐 检测到GitHub仓库: {repo_input}")
                
                # 提取仓库名
                if repo_input.endswith('.git'):
                    repo_name = repo_input.split('/')[-1][:-4]
                else:
                    repo_name = repo_input.split('/')[-1]
                
                # 在当前目录下创建克隆目录
                clone_dir = os.path.join(os.getcwd(), repo_name)
                
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
                        clone_dir = os.path.join(os.getcwd(), new_name)
                        
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
                # 处理本地路径
                repo_path = os.path.abspath(os.path.expanduser(repo_input))
                
                # 检查路径是否存在
                if not os.path.exists(repo_path):
                    print(f"❌ 路径不存在: {repo_path}")
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
            
            # 检查Issues文件
            issues_file = os.path.join(repo_path, '.issues.json')
            if not os.path.exists(issues_file):
                print("📝 创建Issues管理文件...")
                with open(issues_file, 'w', encoding='utf-8') as f:
                    f.write('{"issues": []}\n')
                print("✅ 已创建 .issues.json 文件")
            else:
                # 检查Issues文件内容，确保不包含预设Issues
                try:
                    import json
                    with open(issues_file, 'r', encoding='utf-8') as f:
                        issues_data = json.load(f)
                    
                    if issues_data.get('issues') and len(issues_data['issues']) > 0:
                        print(f"⚠️  发现 {len(issues_data['issues'])} 个现有Issues")
                        clear_choice = input("🤔 是否清空现有Issues？(y/n): ").strip().lower()
                        if clear_choice in ['y', 'yes', '是']:
                            with open(issues_file, 'w', encoding='utf-8') as f:
                                f.write('{"issues": []}\n')
                            print("✅ 已清空Issues文件")
                        else:
                            print("📋 保留现有Issues")
                    else:
                        print("✅ Issues文件已存在且为空")
                except Exception as e:
                    print(f"⚠️  检查Issues文件时出错: {e}")
                    print("📝 重新创建Issues文件...")
                    with open(issues_file, 'w', encoding='utf-8') as f:
                        f.write('{"issues": []}\n')
                    print("✅ 已重新创建 .issues.json 文件")
            
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
            
            # 🆕 关键步骤：同步主项目的Issues到playground仓库
            logger.info("🔄 同步主项目Issues到playground仓库...")
            try:
                # 读取主项目的Issues
                main_issues_file = os.path.join(user_repo_path, ".issues.json")
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
            
            # 🆕 创建协作管理器（使用playground仓库作为主仓库）
            collaboration_manager = CollaborationManager(playground_git_manager, llm_manager)
            logger.info("✅ 创建协作管理器")
            
            # 创建评论员代理（使用playground仓库）
            commenter = CommenterAgent("commenter", playground_git_manager, llm_manager)
            commenter.set_collaboration_manager(collaboration_manager)
            
            # 创建编码员代理（每个使用独立仓库）
            coders = []
            for i in range(config["system"]["num_coders"]):
                agent_id = f"coder_{i}"
                # 为每个coder设置独立仓库
                agent_git_manager = await multi_repo_manager.setup_agent_repo(agent_id)
                coder = CoderAgent(agent_git_manager, llm_manager, agent_id)
                # 设置playground仓库管理器，用于访问Issues
                coder.set_playground_git_manager(playground_git_manager)
                # 设置协作管理器，启用Pull Request流程
                coder.set_collaboration_manager(collaboration_manager)
                # 注册agent仓库到协作管理器
                collaboration_manager.register_agent_repo(agent_id, agent_git_manager)
                # 将多仓库管理器传递给coder，用于同步工作
                coder.multi_repo_manager = multi_repo_manager
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
            
            # 创建评论员代理
            commenter = CommenterAgent("commenter", git_manager, llm_manager)
            
            # 创建编码员代理
            coders = [
                CoderAgent(git_manager, llm_manager, f"coder_{i}")
                for i in range(config["system"]["num_coders"])
            ]
        
        # 启动所有代理
        print("\n" + "=" * 60)
        print("🚀 正在启动多智能体协作系统...")
        print(f"📊 系统配置: 1个Commenter + {len(coders)}个Coder")
        print(f"📁 工作仓库: {user_repo_path}")
        print("⏳ 请稍等，系统正在初始化...")
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