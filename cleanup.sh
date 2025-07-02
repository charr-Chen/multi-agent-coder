#!/bin/bash

echo "🧹 开始清理多智能体编码系统..."
echo "=================================="

# 必须清理
echo "🔴 清理Python包元数据..."
rm -rf src/*.egg-info/ 2>/dev/null
echo "✅ 已清理Python包元数据"

echo "🔴 清理Python缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
echo "✅ 已清理Python缓存"

# 询问是否清理其他文件
echo ""
echo "🟡 可选清理项目："
echo ""

read -p "是否清理agent工作目录? (y/n): " clean_agents
if [[ $clean_agents == "y" || $clean_agents == "Y" ]]; then
    rm -rf agent_repos/ 2>/dev/null
    echo "✅ 已清理agent工作目录"
else
    echo "⏭️  跳过清理agent工作目录"
fi

read -p "是否清理AI记忆文件? (y/n): " clean_memory
if [[ $clean_memory == "y" || $clean_memory == "Y" ]]; then
    rm -rf .memory/ 2>/dev/null
    echo "✅ 已清理AI记忆文件"
else
    echo "⏭️  跳过清理AI记忆文件"
fi

read -p "是否清空日志文件? (y/n): " clean_log
if [[ $clean_log == "y" || $clean_log == "Y" ]]; then
    > multi_agent_coder.log 2>/dev/null
    echo "✅ 已清空日志文件"
else
    echo "⏭️  跳过清空日志文件"
fi

read -p "是否清空Issues? (y/n): " clean_issues
if [[ $clean_issues == "y" || $clean_issues == "Y" ]]; then
    echo '{"issues": []}' > .issues.json 2>/dev/null
    echo "✅ 已清空Issues"
else
    echo "⏭️  跳过清空Issues"
fi

echo ""
echo "🎉 清理完成！"
echo "=================================="
echo "💡 现在可以运行: python3 run.py" 