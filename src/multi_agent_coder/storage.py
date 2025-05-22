# -*- coding: utf-8 -*-
"""Storage module for task management using JSON file."""

import json
import logging
import asyncio
from typing import Optional, List, Tuple
from datetime import datetime
import os
import aiofiles

logger = logging.getLogger(__name__)

# 数据文件路径
DATA_FILE = 'tasks.json'
# 文件锁，防止并发写入
_file_lock = asyncio.Lock()

async def _load_data() -> dict:
    """Load data from JSON file."""
    if os.path.exists(DATA_FILE):
        try:
            async with aiofiles.open(DATA_FILE, 'r', encoding='utf-8') as f:
                content = await f.read()
                if content.strip():  # 确保文件内容不为空
                    return json.loads(content)
                return {"tasks": []}
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"数据文件损坏或格式错误: {str(e)}，创建新的数据文件")
    return {"tasks": []}

async def _save_data(data: dict):
    """Save data to JSON file."""
    async with _file_lock:  # 使用锁确保并发安全
        async with aiofiles.open(DATA_FILE, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))

async def init_db():
    """Initialize storage."""
    if not os.path.exists(DATA_FILE):
        await _save_data({"tasks": []})
        logger.info("Storage initialized successfully")

async def add_task(description: str) -> int:
    """Add a new task."""
    data = await _load_data()
    task_id = len(data["tasks"]) + 1
    task = {
        "id": task_id,
        "description": description,
        "status": "open",
        "assigned_to": None,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "code_submission": None
    }
    data["tasks"].append(task)
    await _save_data(data)
    logger.info(f"Added new task with ID: {task_id}")
    return task_id

async def update_task_status(task_id: int, status: str, code_submission: Optional[str] = None):
    """Update task status."""
    data = await _load_data()
    for task in data["tasks"]:
        if task["id"] == task_id:
            task["status"] = status
            if code_submission:
                task["code_submission"] = code_submission
                task["completed_at"] = datetime.now().isoformat()
            await _save_data(data)
            logger.info(f"Updated task {task_id} status to {status}")
            return
    logger.warning(f"Task {task_id} not found")

async def get_tasks(status: str) -> List[Tuple]:
    """Get tasks by status."""
    data = await _load_data()
    tasks = []
    for task in data["tasks"]:
        if task["status"] == status:
            # 转换为与原来数据库格式相同的元组
            tasks.append((
                task["id"],
                task["description"],
                task["status"],
                task["assigned_to"],
                task["created_at"],
                task["completed_at"],
                task["code_submission"]
            ))
    return tasks 