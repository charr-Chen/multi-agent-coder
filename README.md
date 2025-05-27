# Multi-Agent Coder

[English](#english) | [简体中文](#简体中文)

<a name="english"></a>
# Multi-Agent Coder

A code generation system based on multi-agent collaboration, simulating real development team cooperation.

## System Components

### Commenter Agent
- LLM-based agent responsible for determining development tasks
- Continuously monitors codebase status
- Creates and manages issues
- Reviews code submissions
- Determines task completion status

### Coder Agents
- LLM-based agents responsible for implementing code
- Asynchronously monitor and acquire tasks
- Implement code and submit changes
- Handle code conflicts
- Interact with commenter agent for code review

### Code Base
- Git repository as coordination center
- Supports issue tracking
- Manages code submissions
- Handles concurrent conflicts

## Workflow

1. User prepares a Git repository (new or existing)
2. User describes requirements to the commenter agent
3. Commenter agent starts running:
   - Continuously adds new issues
   - Reviews code submissions
   - Monitors codebase status
4. Coder agents run in the background:
   - Continuously check for unresolved issues
   - Grab and lock tasks
   - Implement code and submit
   - Handle code conflicts
5. All operations are asynchronous and concurrent:
   - Commenter agent simultaneously performs code review and issue management
   - Coder agents simultaneously implement and submit code
   - Automatically handle Git conflicts

## Project Structure

```
multi-agent-coder/
├── run.py                 # Main entry and running script
├── src/
│   └── multi_agent_coder/
│       ├── __init__.py
│       ├── config.py      # Configuration file
│       ├── git_utils.py   # Git operation tools
│       └── agents/
│           ├── __init__.py
│           ├── commenter.py  # Commenter agent
│           └── coder.py      # Coder agent
├── README.md
├── requirements.txt
└── .gitignore
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/charr-Chen/multi-agent-coder.git
cd multi-agent-coder
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Prepare Git repository:
```bash
# Create new repository
git init
# Or use existing repository
git clone <repository-url>
```

2. Run the system:
```bash
python run.py
```

## Dependencies

- Python 3.9+
- GitPython: Git operations
- aiofiles: Asynchronous file operations
- openai: LLM interface
- python-dotenv: Environment variable management

## Development Plan

- [ ] Implement Git operation tools
- [ ] Improve issue tracking system
- [ ] Add code conflict handling
- [ ] Implement LLM interface
- [ ] Add configuration file support
- [ ] Improve error handling
- [ ] Add logging system

## Contributing

Issues and Pull Requests are welcome!

## License

MIT License

---

<a name="简体中文"></a>
# Multi-Agent Coder

基于多智能体协作的代码生成系统，模拟真实开发团队的协作过程。

## 系统组件

### 评论员代理 (Commenter Agent)
- 基于 LLM 的代理，负责确定开发任务
- 持续监控代码库状态
- 创建和管理 Issue
- 审查代码提交
- 决定任务完成状态

### 编码员代理 (Coder Agents)
- 基于 LLM 的代理，负责实现代码
- 异步监控和获取任务
- 实现代码并提交
- 处理代码冲突
- 与评论员交互进行代码审查

### 代码库 (Code Base)
- Git 仓库作为协调中心
- 支持 Issue 跟踪
- 管理代码提交
- 处理并发冲突

## 工作流程

1. 用户准备一个 Git 仓库（新建或现有）
2. 用户向评论员代理描述需求
3. 评论员代理开始运行：
   - 持续添加新的 Issue
   - 审查代码提交
   - 监控代码库状态
4. 编码员代理在后台运行：
   - 持续检查未解决的 Issue
   - 获取并锁定任务
   - 实现代码并提交
   - 处理代码冲突
5. 所有操作都是异步并发的：
   - 评论员代理同时进行代码审查和 Issue 管理
   - 编码员代理同时进行代码实现和提交
   - 自动处理 Git 冲突

## 项目结构

```
multi-agent-coder/
├── run.py                 # 主入口和运行脚本
├── src/
│   └── multi_agent_coder/
│       ├── __init__.py
│       ├── config.py      # 配置文件
│       ├── git_utils.py   # Git 操作工具
│       └── agents/
│           ├── __init__.py
│           ├── commenter.py  # 评论员代理
│           └── coder.py      # 编码员代理
├── README.md
├── requirements.txt
└── .gitignore
```

## 安装

1. 克隆仓库：
```bash
git clone https://github.com/charr-Chen/multi-agent-coder.git
cd multi-agent-coder
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

1. 准备 Git 仓库：
```bash
# 新建仓库
git init
# 或使用现有仓库
git clone <repository-url>
```

2. 运行系统：
```bash
python run.py
```

## 依赖

- Python 3.9+
- GitPython: Git 操作
- aiofiles: 异步文件操作
- openai: LLM 接口
- python-dotenv: 环境变量管理

## 开发计划

- [ ] 实现 Git 操作工具
- [ ] 完善 Issue 跟踪系统
- [ ] 添加代码冲突处理
- [ ] 实现 LLM 接口
- [ ] 添加配置文件支持
- [ ] 改进错误处理
- [ ] 添加日志系统

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License 