"""
主入口文件
用于启动多智能体编码系统
支持异步操作和 JSON 文件存储
"""

import sys
import os
import asyncio

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from run import main

if __name__ == "__main__":
    asyncio.run(main())
