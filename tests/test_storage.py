"""
存储模块的测试用例
"""

import pytest
import os
import json
from src.multi_agent_coder.storage import init_db, add_task, get_tasks, update_task_status

@pytest.fixture
async def setup_storage():
    """设置测试环境"""
    test_file = 'test_tasks.json'
    os.environ['DATA_FILE'] = test_file
    await init_db()
    yield
    if os.path.exists(test_file):
        os.remove(test_file)

@pytest.mark.asyncio
async def test_add_task(setup_storage):
    """测试添加任务"""
    task_id = await add_task("测试任务")
    assert task_id == 1
    tasks = await get_tasks("open")
    assert len(tasks) == 1
    assert tasks[0][1] == "测试任务"

@pytest.mark.asyncio
async def test_update_task_status(setup_storage):
    """测试更新任务状态"""
    task_id = await add_task("测试任务")
    await update_task_status(task_id, "completed", "测试代码")
    tasks = await get_tasks("completed")
    assert len(tasks) == 1
    assert tasks[0][2] == "completed"
    assert tasks[0][6] == "测试代码" 