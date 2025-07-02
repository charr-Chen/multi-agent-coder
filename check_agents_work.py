#!/usr/bin/env python3
"""
检查AI Agents工作成果的脚本
显示Memory记录、工作报告和代码修改情况
"""

import os
import json
import glob
from pathlib import Path

def check_memory_files():
    """检查Memory文件"""
    print("🧠 检查AI Agent Memory记录...")
    print("=" * 50)
    
    memory_files = []
    
    # 检查agent_repos目录下的.memory文件
    agent_repos_path = "agent_repos"
    if os.path.exists(agent_repos_path):
        memory_pattern = os.path.join(agent_repos_path, "**", ".memory", "*_memory.json")
        memory_files.extend(glob.glob(memory_pattern, recursive=True))
    
    # 检查当前目录的.memory文件
    current_memory_pattern = ".memory/*_memory.json"
    memory_files.extend(glob.glob(current_memory_pattern))
    
    if memory_files:
        for memory_file in memory_files:
            print(f"\n📁 Memory文件: {memory_file}")
            try:
                with open(memory_file, 'r', encoding='utf-8') as f:
                    memory_data = json.load(f)
                    agent_id = memory_data.get('agent_id', 'unknown')
                    memories = memory_data.get('memories', [])
                    print(f"   Agent: {agent_id}")
                    print(f"   记录数量: {len(memories)}")
                    
                    # 显示最近的几条记录
                    recent_memories = sorted(memories, key=lambda x: x.get('created_at', 0), reverse=True)[:3]
                    for i, mem in enumerate(recent_memories, 1):
                        mem_type = mem.get('memory_type', 'unknown')
                        content = mem.get('content', {})
                        created_at = mem.get('created_at', 0)
                        import datetime
                        time_str = datetime.datetime.fromtimestamp(created_at).strftime('%Y-%m-%d %H:%M:%S')
                        
                        print(f"   [{i}] {mem_type} - {time_str}")
                        if 'action' in content:
                            print(f"       操作: {content['action']}")
                        if 'issue_title' in content:
                            print(f"       Issue: {content['issue_title']}")
                        if 'thought' in content:
                            thought = content['thought'][:100] + "..." if len(content['thought']) > 100 else content['thought']
                            print(f"       思考: {thought}")
                        print()
                        
            except Exception as e:
                print(f"   ❌ 读取失败: {e}")
    else:
        print("❌ 没有找到任何Memory文件")
        print("💡 Agents可能还没有开始工作，或者Memory系统未正常工作")

def check_work_reports():
    """检查工作报告"""
    print("\n📊 检查AI Agent工作报告...")
    print("=" * 50)
    
    report_files = []
    
    # 检查各种可能的reports目录
    possible_report_dirs = [
        "reports",
        "agent_repos/playground/reports",
        os.path.join(os.getcwd(), "reports")
    ]
    
    for report_dir in possible_report_dirs:
        if os.path.exists(report_dir):
            report_pattern = os.path.join(report_dir, "agent_report_*.md")
            report_files.extend(glob.glob(report_pattern))
    
    if report_files:
        # 按时间排序，最新的在前
        report_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        for report_file in report_files:
            print(f"\n📄 报告: {report_file}")
            try:
                # 获取文件修改时间
                import datetime
                mtime = os.path.getmtime(report_file)
                time_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                print(f"   创建时间: {time_str}")
                
                # 读取并显示报告摘要
                with open(report_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # 提取基本信息
                    for line in lines[:20]:  # 只看前20行
                        if "Agent ID" in line:
                            print(f"   {line.strip()}")
                        elif "Issue标题" in line:
                            print(f"   {line.strip()}")
                        elif "创建/修改的文件" in line:
                            print(f"   {line.strip()}")
                        elif "任务状态" in line:
                            print(f"   {line.strip()}")
                            
            except Exception as e:
                print(f"   ❌ 读取失败: {e}")
    else:
        print("❌ 没有找到任何工作报告")
        print("💡 Agents可能还没有完成任何工作，或者报告生成功能未启用")

def check_git_commits():
    """检查Git提交记录"""
    print("\n🔄 检查最近的Git提交...")
    print("=" * 50)
    
    try:
        import subprocess
        
        # 检查playground仓库
        playground_path = "agent_repos/playground"
        if os.path.exists(os.path.join(playground_path, ".git")):
            print(f"📁 Playground仓库提交记录 ({playground_path}):")
            result = subprocess.run(
                ['git', 'log', '--oneline', '-10'], 
                cwd=playground_path,
                capture_output=True, 
                text=True
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        print(f"   {line}")
            else:
                print("   ❌ 获取Git日志失败")
        
        # 检查主项目的提交
        if os.path.exists(".git"):
            print(f"\n📁 主项目提交记录:")
            result = subprocess.run(
                ['git', 'log', '--oneline', '-5'], 
                capture_output=True, 
                text=True
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        print(f"   {line}")
            else:
                print("   ❌ 获取Git日志失败")
                
    except Exception as e:
        print(f"❌ 检查Git提交失败: {e}")

def check_created_files():
    """检查最近创建的文件"""
    print("\n📁 检查最近创建/修改的文件...")
    print("=" * 50)
    
    try:
        import time
        current_time = time.time()
        recent_files = []
        
        # 检查playground目录
        playground_path = "agent_repos/playground"
        if os.path.exists(playground_path):
            for root, dirs, files in os.walk(playground_path):
                # 跳过.git目录
                if '.git' in dirs:
                    dirs.remove('.git')
                    
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        mtime = os.path.getmtime(file_path)
                        # 只显示最近1小时内修改的文件
                        if current_time - mtime < 3600:  
                            recent_files.append((file_path, mtime))
                    except:
                        pass
        
        if recent_files:
            # 按时间排序
            recent_files.sort(key=lambda x: x[1], reverse=True)
            
            print("🕐 最近1小时内修改的文件:")
            for file_path, mtime in recent_files[:10]:  # 只显示前10个
                import datetime
                time_str = datetime.datetime.fromtimestamp(mtime).strftime('%H:%M:%S')
                rel_path = os.path.relpath(file_path)
                print(f"   {time_str} - {rel_path}")
        else:
            print("❌ 没有发现最近修改的文件")
            
    except Exception as e:
        print(f"❌ 检查文件失败: {e}")

def main():
    """主函数"""
    print("🔍 AI Multi-Agent工作成果检查器")
    print("=" * 60)
    
    check_memory_files()
    check_work_reports() 
    check_git_commits()
    check_created_files()
    
    print("\n" + "=" * 60)
    print("✅ 检查完成!")
    print("\n💡 提示:")
    print("   - 如果没有看到期望的结果，可能是:")
    print("     1. Agents还在运行中")
    print("     2. LLM API调用失败")
    print("     3. 网络连接问题")
    print("   - 查看运行日志了解详细情况")
    print("   - 工作报告保存在 reports/ 目录中")
    print("   - Memory记录保存在 .memory/ 目录中")

if __name__ == "__main__":
    main() 