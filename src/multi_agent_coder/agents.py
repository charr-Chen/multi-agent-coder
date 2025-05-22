import sqlite3
import logging
import time
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

def init_db():
    """初始化任务数据库"""
    try:
        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                assigned_to TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                code_submission TEXT
            )
        ''')
        conn.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise
    finally:
        conn.close()

def add_task(description: str) -> int:
    """添加新任务到数据库"""
    try:
        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO tasks (description, status) VALUES (?, ?)
        ''', (description, 'open'))
        task_id = c.lastrowid
        conn.commit()
        logger.info(f"Added new task with ID: {task_id}")
        return task_id
    except Exception as e:
        logger.error(f"Failed to add task: {str(e)}")
        raise
    finally:
        conn.close()

def update_task_status(task_id: int, status: str, code_submission: Optional[str] = None):
    """更新任务状态"""
    try:
        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()
        if code_submission:
            c.execute('''
                UPDATE tasks 
                SET status = ?, code_submission = ?, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, code_submission, task_id))
        else:
            c.execute('''
                UPDATE tasks 
                SET status = ?
                WHERE id = ?
            ''', (status, task_id))
        conn.commit()
        logger.info(f"Updated task {task_id} status to {status}")
    except Exception as e:
        logger.error(f"Failed to update task status: {str(e)}")
        raise
    finally:
        conn.close()

def get_tasks(status: str) -> List[Tuple]:
    """获取指定状态的任务"""
    try:
        conn = sqlite3.connect('tasks.db')
        c = conn.cursor()
        c.execute('''
            SELECT * FROM tasks WHERE status = ?
        ''', (status,))
        tasks = c.fetchall()
        return tasks
    except Exception as e:
        logger.error(f"Failed to get tasks: {str(e)}")
        raise
    finally:
        conn.close()

#创建 Commenter Agent
class CommenterAgent:
    def __init__(self, task_db: str = 'tasks.db'):
        self.task_db = task_db
        logger.info("CommenterAgent initialized")

    def create_task(self, description: str) -> int:
        """创建新任务"""
        task_id = add_task(description)
        logger.info(f"Created task: {description}")
        return task_id

    def review_task(self, task_id: int, coder_submission: str) -> str:
        """审查代码提交"""
        # 这里可以添加实际的代码审查逻辑
        # 例如：检查代码质量、运行测试、检查代码风格等
        logger.info(f"Reviewing task {task_id}")
        
        # 模拟代码审查过程
        time.sleep(1)  # 模拟审查时间
        
        # 简单的审查逻辑
        if len(coder_submission) > 10:  # 这里只是一个示例条件
            update_task_status(task_id, "completed", coder_submission)
            return "completed"
        else:
            update_task_status(task_id, "needs_revision")
            return "needs_revision"

    def get_open_tasks(self) -> List[Tuple]:
        """获取所有开放的任务"""
        return get_tasks("open")

#创建 Coder Agents
class CoderAgent:
    def __init__(self, commenter_agent: CommenterAgent, task_db: str = 'tasks.db'):
        self.commenter_agent = commenter_agent
        self.task_db = task_db
        self.current_task = None
        logger.info("CoderAgent initialized")

    def grab_task(self) -> Tuple[Optional[int], Optional[str]]:
        """获取一个任务"""
        open_tasks = get_tasks("open")
        if open_tasks:
            task = open_tasks[0]
            task_id = task[0]
            task_description = task[1]
            self.current_task = task_id
            logger.info(f"Grabbed task {task_id}: {task_description}")
            return task_id, task_description
        logger.info("No open tasks available")
        return None, None

    def complete_task(self, task_id: int) -> bool:
        """完成任务"""
        if not self.current_task or self.current_task != task_id:
            logger.warning(f"Task {task_id} is not assigned to this coder")
            return False

        # 模拟代码实现
        coder_submission = self._implement_task(task_id)
        logger.info(f"Submitting code for task {task_id}")
        
        # 提交代码进行审查
        status = self.commenter_agent.review_task(task_id, coder_submission)
        
        if status == "completed":
            logger.info(f"Task {task_id} completed successfully")
            self.current_task = None
            return True
        else:
            logger.info(f"Task {task_id} needs revision")
            return False

    def _implement_task(self, task_id: int) -> str:
        """实现任务（这里只是模拟）"""
        # 模拟编码过程
        time.sleep(2)  # 模拟编码时间
        
        # 这里可以添加实际的代码实现逻辑
        # 例如：根据任务描述生成代码、调用代码生成API等
        return f"# Implementation for task {task_id}\ndef solution():\n    # Task implementation\n    pass"