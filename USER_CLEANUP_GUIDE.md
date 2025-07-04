# 多智能体编码系统 - 用户清理指南

## 🧹 用户每次运行前需要清理的文件

### 📋 清理清单

#### 🔴 **必须清理** (强烈建议)

1. **Python包元数据目录**
   ```bash
   # 清理 egg-info 目录
   rm -rf src/*.egg-info/
   ```
   - **原因**: 自动生成的文件，可能过时，不应该提交到版本控制
   - **影响**: 不清理可能导致包信息不准确

2. **Python缓存文件**
   ```bash
   # 清理 __pycache__ 目录
   find . -type d -name "__pycache__" -exec rm -rf {} +
   
   # 清理 .pyc 文件
   find . -name "*.pyc" -delete
   ```
   - **原因**: Python自动生成的字节码缓存，可能过时
   - **影响**: 不清理可能导致代码更新后仍使用旧缓存

#### 🟡 **建议清理** (根据情况决定)

3. **Agent工作目录**
   ```bash
   # 清理所有agent的工作目录
   rm -rf agent_repos/
   ```
   - **原因**: 包含上次运行的工作成果，重新开始时可清理
   - **影响**: 清理后需要重新创建agent仓库
   - **建议**: 如果需要保留工作成果，可以不清理

4. **Memory记忆文件**
   ```bash
   # 清理AI记忆文件
   rm -rf .memory/
   ```
   - **原因**: AI的学习记忆，重新开始时可能需要清理
   - **影响**: 清理后AI需要重新学习
   - **建议**: 如果希望AI保持学习经验，可以不清理

5. **日志文件**
   ```bash
   # 清空日志文件内容
   > multi_agent_coder.log
   
   # 或者删除日志文件
   rm multi_agent_coder.log
   ```
   - **原因**: 日志文件会不断增长
   - **影响**: 清理后无法查看历史日志
   - **建议**: 如果日志文件不大，可以不清理

#### 🟢 **可选清理** (通常不需要)

6. **Issues文件**
   ```bash
   # 清空Issues（现在在playground仓库中）
   echo '{"issues": []}' > agent_repos/playground/.issues.json
   ```
   - **原因**: 如果需要重新开始项目
   - **影响**: 清理后所有Issues丢失
   - **建议**: 通常不需要清理，系统会询问是否清空

7. **虚拟环境** (谨慎操作)
   ```bash
   # 重新创建虚拟环境
   rm -rf .venv/
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   - **原因**: 依赖包有问题时
   - **影响**: 需要重新安装所有依赖
   - **建议**: 只有在依赖有问题时才清理

## 🚀 一键清理脚本

创建以下脚本 `cleanup.sh`：

```bash
#!/bin/bash

echo "🧹 开始清理多智能体编码系统..."

# 必须清理
echo "🔴 清理Python包元数据..."
rm -rf src/*.egg-info/

echo "🔴 清理Python缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null

# 询问是否清理其他文件
echo ""
read -p "🟡 是否清理agent工作目录? (y/n): " clean_agents
if [[ $clean_agents == "y" || $clean_agents == "Y" ]]; then
    rm -rf agent_repos/
    echo "✅ 已清理agent工作目录"
fi

read -p "🟡 是否清理AI记忆文件? (y/n): " clean_memory
if [[ $clean_memory == "y" || $clean_memory == "Y" ]]; then
    rm -rf .memory/
    echo "✅ 已清理AI记忆文件"
fi

read -p "🟡 是否清空日志文件? (y/n): " clean_log
if [[ $clean_log == "y" || $clean_log == "Y" ]]; then
    > multi_agent_coder.log
    echo "✅ 已清空日志文件"
fi

read -p "🟡 是否清空Issues? (y/n): " clean_issues
if [[ $clean_issues == "y" || $clean_issues == "Y" ]]; then
    echo '{"issues": []}' > agent_repos/playground/.issues.json
    echo "✅ 已清空Issues"
fi

echo "🎉 清理完成！"
```

使用方法：
```bash
chmod +x cleanup.sh
./cleanup.sh
```

## 📊 清理优先级说明

### 🔴 **高优先级** (每次运行前必须清理)
- `*.egg-info/` - Python包元数据
- `__pycache__/` - Python缓存

### 🟡 **中优先级** (根据情况决定)
- `agent_repos/` - Agent工作目录
- `.memory/` - AI记忆文件
- `multi_agent_coder.log` - 日志文件

### 🟢 **低优先级** (通常不需要)
- `.issues.json` - Issues文件
- `.venv/` - 虚拟环境

## 🤔 关于 .memory 目录的特别说明

### **.memory 目录的作用**
- 存储AI Agent的学习经验和决策记录
- 包含思考过程、工作流程洞察、协作笔记等
- 帮助AI在后续运行中保持学习连续性

### **是否需要清理？**

#### ✅ **建议保留的情况**：
- 希望AI保持学习经验
- 系统运行稳定，AI表现良好
- 需要AI记住之前的工作模式

#### ❌ **建议清理的情况**：
- 重新开始新项目
- AI表现不佳，需要重新学习
- 记忆文件过大或混乱
- 测试新功能时

### **智能清理策略**
```bash
# 只清理过期的记忆（保留30天内的）
find .memory/ -name "*.json" -mtime +30 -delete

# 清理特定agent的记忆
rm .memory/coder_0_memory.json

# 备份后清理
mv .memory .memory.backup
```

## 🎯 最佳实践建议

### **首次使用**
```bash
# 完整清理
rm -rf src/*.egg-info/
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete
rm -rf agent_repos/
rm -rf .memory/
> multi_agent_coder.log
```

### **日常使用**
```bash
# 基础清理
rm -rf src/*.egg-info/
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete
```

### **问题排查时**
```bash
# 完整清理重新开始
./cleanup.sh  # 选择清理所有选项
```

## 📝 总结

1. **必须清理**: Python包元数据和缓存文件
2. **建议清理**: Agent工作目录和AI记忆（根据情况）
3. **可选清理**: 日志文件和Issues（通常不需要）
4. **使用脚本**: 创建 `cleanup.sh` 脚本简化清理过程
5. **灵活策略**: 根据使用场景选择合适的清理策略

通过合理的清理策略，可以确保系统每次运行都在干净的环境中，同时保留有价值的学习经验。 