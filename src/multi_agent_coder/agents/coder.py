"""
记忆管理器
负责存储和检索代理的历史经验，使用自然语言处理，简单高效
"""
class CoderAgent:
    def __init__(self, agent_id, llm, tools_api):
        self.agent_id = agent_id
        self.llm = llm
        self.tools_api = tools_api
        self.memories = []
    
    def update_memory(self, action, return_value):
        self.memories.append(f"Action: {action} | Result: {return_value}")
        # 只保留最近20条记忆
        if len(self.memories) > 20:
            self.memories = self.memories[-20:]
    
    def implement_issue(self, issue, max_iterations=30):
        while len(self.memories) < max_iterations:
            memories = "\n".join(self.memories) if self.memories else "No previous actions"
            
            # 决定下一步动作的prompt
            action_prompt = f"""
You are a skilled software developer. Based on the current situation, decide what action to take next.

AVAILABLE ACTIONS:
- read_file <filepath>: Read a file
- write_file <filepath> <content>: Write content to a file  
- run_command <command>: Execute a shell command
- analyze_code <code_or_filepath>: Analyze code structure
- create_test <test_name> <test_code>: Create a test file
- search_pattern <pattern> <directory>: Search for code patterns
- complete: Mark task as finished

CURRENT MEMORIES:
{memories}

CURRENT ISSUE:
{issue}

Think step by step:
1. What have I done so far?
2. What needs to be done next?
3. What's the most logical next action?

Respond with just the action command, for example:
read_file src/main.py
or
write_file utils.py def helper_function(): pass
or
complete

Your action:
"""
            
            action = self.llm.generate(action_prompt).strip()
            
            if action == "complete":
                break
                
            return_value = self.tools_api.execute(action)
            self.update_memory(action, return_value)
            
            # 检查是否完成的prompt
            completion_prompt = f"""
Look at the original issue and what has been accomplished so far. 

ORIGINAL ISSUE:
{issue}

ACTIONS TAKEN:
{chr(10).join(self.memories)}

Has this issue been fully resolved? Consider:
- Are all requirements implemented?
- Does the code work correctly?
- Are there tests if needed?
- Is the implementation complete?

If the issue is fully resolved, respond with "yes".
If more work is needed, respond with "no".

Answer:
"""
            
            completed = self.llm.generate(completion_prompt).strip().lower()
            if completed.startswith("yes"):
                break
        
        return {
            "completed": completed.startswith("yes") if 'completed' in locals() else False,
            "iterations": len(self.memories),
            "final_memories": self.memories
        }

# 简单的工具API
class ToolsAPI:
    def execute(self, action):
        try:
            parts = action.split(' ', 1)
            command = parts[0]
            args = parts[1] if len(parts) > 1 else ""
            
            if command == "read_file":
                with open(args, 'r') as f:
                    return f.read()
            elif command == "write_file":
                filepath, content = args.split(' ', 1)
                with open(filepath, 'w') as f:
                    f.write(content)
                return f"File {filepath} written successfully"
            elif command == "run_command":
                import subprocess
                result = subprocess.run(args, shell=True, capture_output=True, text=True)
                return f"Exit code: {result.returncode}\nOutput: {result.stdout}\nError: {result.stderr}"
            elif command == "analyze_code":
                return f"Analyzed code: {args[:100]}..."
            elif command == "create_test":
                test_name, test_code = args.split(' ', 1)
                with open(f"test_{test_name}.py", 'w') as f:
                    f.write(test_code)
                return f"Test file test_{test_name}.py created"
            elif command == "search_pattern":
                pattern, directory = args.split(' ', 1)
                return f"Searched for {pattern} in {directory}"
            else:
                return f"Unknown command: {command}"
        except Exception as e:
            return f"Error: {str(e)}"

# 简单的LLM接口
class LLM:
    def generate(self, prompt):
        # 这里替换为实际的LLM API调用
        # 比如 OpenAI API, Claude API 等
        print(f"LLM Prompt:\n{prompt}\n" + "="*50)
        
        # 模拟响应
        if "decide what action" in prompt:
            return "read_file main.py"
        elif "Has this issue been fully resolved" in prompt:
            return "no"
        else:
            return "Processing..."

# 使用示例
if __name__ == "__main__":
    llm = LLM()
    tools_api = ToolsAPI()
    coder = CoderAgent("coder_1", llm, tools_api)
    
    issue = "Create a Python function that calculates fibonacci numbers and write a test for it"
    result = coder.implement_issue(issue)
    print(f"Result: {result}")