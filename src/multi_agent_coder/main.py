import logging
from agents import init_db, CommenterAgent, CoderAgent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    try:
        # 初始化任务数据库
        logger.info("Initializing task database...")
        init_db()

        # 初始化 Commenter Agent 和 Coder Agents
        logger.info("Initializing agents...")
        commenter_agent = CommenterAgent()
        coder_agents = [CoderAgent(commenter_agent) for _ in range(3)]  # 创建3个编码员

        # 创建示例任务
        logger.info("Creating sample tasks...")
        tasks = [
            "Fix bug in the authentication system",
            "Add new feature for data export",
            "Implement user profile page",
            "Optimize database queries"
        ]
        
        for task in tasks:
            commenter_agent.create_task(task)

        # 编码员代理开始工作
        logger.info("Starting coding tasks...")
        for coder in coder_agents:
            task_id, task_description = coder.grab_task()
            if task_id:
                logger.info(f"Coder {coder_agents.index(coder) + 1} is working on task {task_id}")
                coder.complete_task(task_id)
            else:
                logger.info(f"No more tasks available for coder {coder_agents.index(coder) + 1}")

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main()
