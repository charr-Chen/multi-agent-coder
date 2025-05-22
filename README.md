# Multi-Agent Coder

一个基于多智能体的代码协作系统，模拟了代码审查和任务分配的工作流程。

## 功能特点

- 多智能体协作：包含评论员（Commenter）和编码员（Coder）两种角色
- 任务管理：支持任务的创建、分配和状态跟踪
- 代码审查：模拟代码审查流程
- 数据库持久化：使用 SQLite 存储任务信息
- 日志记录：详细的运行日志

## 系统架构

- `CommenterAgent`: 负责创建任务和审查代码
- `CoderAgent`: 负责实现任务和提交代码
- SQLite 数据库：存储任务信息和状态

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

运行主程序：
```bash
python src/multi_agent_coder/main.py
```

## 项目结构

```
multi-agent-coder/
├── src/
│   └── multi_agent_coder/
│       ├── main.py
│       └── agents.py
├── README.md
├── requirements.txt
└── .gitignore
```

## 开发计划

- [ ] 添加更复杂的代码审查逻辑
- [ ] 实现实际的代码生成功能
- [ ] 添加任务优先级
- [ ] 实现任务重试机制
- [ ] 添加更多的任务状态

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License 