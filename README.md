# Multi-Agent Coder

[English](#english) | [简体中文](#简体中文)

<a name="english"></a>
# Multi-Agent Coder

A sophisticated AI-powered collaborative coding system that simulates real development teams with GitHub-style workflows, intelligent code generation, and advanced project management capabilities.

## 🚀 Key Features

### 🤖 Multi-Agent Collaboration
- **Commenter Agent**: Analyzes projects, creates tasks, and reviews code
- **Coder Agents**: Implement features with context-aware code generation
- **Collaboration Manager**: Orchestrates workflow and manages conflicts
- **GitHub-Style Workflow**: Complete Pull Request workflow with review and merging

### 🎯 Project Support
- **Universal Repository Support**: Works with local projects, GitHub repos, or new projects
- **Smart Project Detection**: Automatically handles complex project structures
- **Auto-initialization**: Sets up Git repositories and required files automatically
- **Real-time Collaboration**: Agents coordinate work and avoid conflicts

### 🔧 Latest Features
- **🌐 GitHub Integration**: Direct support for GitHub URLs with automatic cloning
- **🎯 Interactive Setup**: User-friendly startup process with clear guidance
- **📁 Smart Synchronization**: Intelligent project content management
- **📊 Detailed Reports**: Comprehensive summaries of all code changes
- **⚡ Async Operations**: Enhanced performance with concurrent agent operations

## 📁 Project Structure

```
multi-agent-coder/
├── run.py                    # 🚀 Main entry point
├── src/multi_agent_coder/    # 🤖 Core system modules
├── agent_repos/              # 🏢 Agent workspaces
│   ├── playground/           # 🎮 Main collaboration repository
│   └── coder_0, coder_1...  # 👨‍💻 Individual coder workspaces
├── pyproject.toml           # 📦 Project configuration
└── README.md
```

## ⚡ Quick Start

### 1. Installation

```bash
# Clone and install
git clone https://github.com/charr-Chen/multi-agent-coder.git
cd multi-agent-coder
uv sync  # or: pip install -e .
```

### 2. Environment Setup

```bash
# Required: Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# Optional: Set proxy if needed
export OPENAI_PROXY_URL="your-proxy-url"
```

### 3. Launch

```bash
python run.py
```

## 🎯 Usage

When you run the system, you'll see an interactive setup:

```
============================================================
🚀 Multi-Agent Coder - AI Collaborative Programming System
============================================================

💡 Please specify the Git repository to use:
   - Local project path (e.g., /path/to/project)
   - GitHub repository URL (e.g., https://github.com/user/repo.git)
   - Leave empty to use current directory

📁 Git repository path or URL: 
```

### Supported Input Types

| Input Type | Example | Description |
|------------|---------|-------------|
| **Local Path** | `/home/user/my-project` | Use existing local project |
| **GitHub URL** | `https://github.com/user/repo.git` | Clone from GitHub |
| **Empty** | `(press Enter)` | Use current directory |

## 🔄 How It Works

1. **🔍 Analysis**: Commenter analyzes your project and creates development tasks
2. **📋 Task Creation**: Issues are created and assigned to coder agents
3. **🛠️ Implementation**: Coder agents implement features in their workspaces
4. **📤 Pull Requests**: Changes are submitted as Pull Requests
5. **👀 Review**: Commenter reviews and approves changes
6. **🔄 Merge**: Approved changes are merged to main branch

## 🎉 What You Get

- **📊 Detailed Reports**: See exactly what each agent modified
- **🔍 Change Tracking**: Comprehensive summaries of all code changes
- **📁 Organized Work**: Clean separation between project and agent workspaces
- **🔄 Version Control**: Full Git history of all collaborative work

---

<a name="简体中文"></a>
# Multi-Agent Coder

一个先进的AI驱动的协作编程系统，模拟真实的开发团队，具有GitHub风格的工作流程、智能代码生成和高级项目管理功能。

## 🚀 核心功能

### 🤖 多智能体协作
- **评论员代理**: 分析项目、创建任务、审查代码
- **编码员代理**: 基于上下文感知的代码生成实现功能
- **协作管理器**: 编排工作流程并管理冲突
- **GitHub风格工作流**: 完整的Pull Request工作流程

### 🎯 项目支持
- **通用仓库支持**: 支持本地项目、GitHub仓库或新项目
- **智能项目检测**: 自动处理复杂的项目结构
- **自动初始化**: 自动设置Git仓库和必需文件
- **实时协作**: 智能体协调工作并避免冲突

### 🔧 最新功能
- **🌐 GitHub集成**: 直接支持GitHub URL并自动克隆
- **🎯 交互式设置**: 用户友好的启动过程
- **📁 智能同步**: 智能项目内容管理
- **📊 详细报告**: 所有代码更改的全面摘要
- **⚡ 异步操作**: 增强的并发智能体操作性能

## 📁 项目结构

```
multi-agent-coder/
├── run.py                    # 🚀 主入口点
├── src/multi_agent_coder/    # 🤖 核心系统模块
├── agent_repos/              # 🏢 智能体工作空间
│   ├── playground/           # 🎮 主协作仓库
│   └── coder_0, coder_1...  # 👨‍💻 独立编码员工作空间
├── pyproject.toml           # 📦 项目配置
└── README.md
```

## ⚡ 快速开始

### 1. 安装

```bash
# 克隆并安装
git clone https://github.com/charr-Chen/multi-agent-coder.git
cd multi-agent-coder
uv sync  # 或: pip install -e .
```

### 2. 环境设置

```bash
# 必需: 设置OpenAI API密钥
export OPENAI_API_KEY="your-api-key-here"

# 可选: 设置代理（如需要）
export OPENAI_PROXY_URL="your-proxy-url"
```

### 3. 启动

```bash
python run.py
```

## 🎯 使用方法

运行系统时，你会看到交互式设置界面：

```
============================================================
🚀 Multi-Agent Coder - AI协作编程系统
============================================================

💡 请指定要使用的Git仓库：
   - 本地项目路径 (例如: /path/to/project)
   - GitHub仓库URL (例如: https://github.com/user/repo.git)
   - 留空使用当前目录

📁 Git仓库路径或URL: 
```

### 支持的输入类型

| 输入类型 | 示例 | 描述 |
|----------|------|------|
| **本地路径** | `/home/user/my-project` | 使用现有本地项目 |
| **GitHub URL** | `https://github.com/user/repo.git` | 从GitHub克隆 |
| **留空** | `(按Enter)` | 使用当前目录 |

## 🔄 工作原理

1. **🔍 分析**: 评论员分析你的项目并创建开发任务
2. **📋 任务创建**: 创建Issues并分配给编码员智能体
3. **🛠️ 实现**: 编码员智能体在其工作空间中实现功能
4. **📤 Pull Request**: 更改作为Pull Request提交
5. **👀 审查**: 评论员审查并批准更改
6. **🔄 合并**: 批准的更改合并到主分支

## 🎉 获得什么

- **📊 详细报告**: 查看每个智能体的具体修改
- **🔍 变更跟踪**: 所有代码更改的全面摘要
- **📁 有序工作**: 项目与智能体工作空间的清晰分离
- **🔄 版本控制**: 所有协作工作的完整Git历史
