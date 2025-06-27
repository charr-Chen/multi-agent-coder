"""
工具执行器
为CoderAgent提供各种编程辅助工具，如文件读取、代码搜索、测试运行等
"""

import os
import re
import ast
import subprocess
import json
import time
from typing import Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ToolResult:
    """工具执行结果"""
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        return {
            'tool_name': self.tool_name,
            'success': self.success,
            'result': self.result,
            'error': self.error,
            'execution_time': self.execution_time
        }

class ToolExecutor:
    """工具执行器"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = project_root
        self.available_tools = {
            'read_file': self.read_file,
            'search_code': self.search_code,
            'analyze_syntax': self.analyze_syntax,
            'run_tests': self.run_tests,
            'analyze_dependencies': self.analyze_dependencies,
            'git_analysis': self.git_analysis,
            'pattern_match': self.pattern_match
        }
        logger.info(f"工具执行器初始化完成，可用工具: {list(self.available_tools.keys())}")
    
    def get_available_tools(self) -> list[str]:
        """获取可用工具列表"""
        return list(self.available_tools.keys())
    
    def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """执行指定工具
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            工具执行结果
        """
        start_time = time.time()
        
        if tool_name not in self.available_tools:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                result=None,
                error=f"未知工具: {tool_name}"
            )
        
        try:
            tool_func = self.available_tools[tool_name]
            result = tool_func(**kwargs)
            execution_time = time.time() - start_time
            
            return ToolResult(
                tool_name=tool_name,
                success=True,
                result=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"工具执行失败 {tool_name}: {e}")
            
            return ToolResult(
                tool_name=tool_name,
                success=False,
                result=None,
                error=str(e),
                execution_time=execution_time
            )
    
    def execute_tools_batch(self, tool_requests: list[dict[str, Any]]) -> list[ToolResult]:
        """批量执行工具
        
        Args:
            tool_requests: 工具请求列表，每个包含tool_name和参数
            
        Returns:
            工具执行结果列表
        """
        results = []
        for request in tool_requests:
            tool_name = request.get('tool_name')
            params = {k: v for k, v in request.items() if k != 'tool_name'}
            result = self.execute_tool(tool_name, **params)
            results.append(result)
        
        return results
    
    def read_file(self, file_path: str, encoding: str = 'utf-8') -> dict[str, Any]:
        """读取文件内容
        
        Args:
            file_path: 文件路径
            encoding: 文件编码
            
        Returns:
            文件信息字典
        """
        full_path = os.path.join(self.project_root, file_path)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        try:
            with open(full_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            # 基本文件分析
            lines = content.split('\n')
            file_info = {
                'path': file_path,
                'content': content,
                'lines': len(lines),
                'characters': len(content),
                'encoding': encoding,
                'extension': os.path.splitext(file_path)[1],
                'size_bytes': os.path.getsize(full_path)
            }
            
            # 如果是Python文件，添加额外分析
            if file_path.endswith('.py'):
                file_info.update(self._analyze_python_file(content))
            
            return file_info
            
        except UnicodeDecodeError as e:
            raise ValueError(f"文件编码错误: {e}")
    
    def search_code(self, pattern: str, file_types: list[str] = None, 
                   case_sensitive: bool = False) -> dict[str, Any]:
        """在代码中搜索模式
        
        Args:
            pattern: 搜索模式（正则表达式）
            file_types: 文件类型列表，如['.py', '.js']
            case_sensitive: 是否区分大小写
            
        Returns:
            搜索结果字典
        """
        if file_types is None:
            file_types = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h']
        
        matches = []
        flags = 0 if case_sensitive else re.IGNORECASE
        
        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            raise ValueError(f"无效的正则表达式: {e}")
        
        for root, dirs, files in os.walk(self.project_root):
            # 跳过隐藏目录和常见的忽略目录
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
            
            for file in files:
                if any(file.endswith(ext) for ext in file_types):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.project_root)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        for line_num, line in enumerate(content.split('\n'), 1):
                            if regex.search(line):
                                matches.append({
                                    'file': rel_path,
                                    'line_number': line_num,
                                    'line_content': line.strip(),
                                    'match': regex.search(line).group()
                                })
                    
                    except (UnicodeDecodeError, PermissionError):
                        continue
        
        return {
            'pattern': pattern,
            'total_matches': len(matches),
            'files_with_matches': len(set(match['file'] for match in matches)),
            'matches': matches[:100]  # 限制返回数量
        }
    
    def analyze_syntax(self, code: str, language: str = 'python') -> dict[str, Any]:
        """分析代码语法
        
        Args:
            code: 代码字符串
            language: 编程语言
            
        Returns:
            语法分析结果
        """
        if language.lower() == 'python':
            return self._analyze_python_syntax(code)
        else:
            # 对于其他语言，进行基本分析
            return self._analyze_generic_syntax(code)
    
    def run_tests(self, test_command: str = None, test_dir: str = "tests") -> dict[str, Any]:
        """运行测试
        
        Args:
            test_command: 测试命令
            test_dir: 测试目录
            
        Returns:
            测试结果
        """
        if test_command is None:
            # 尝试自动检测测试框架
            if os.path.exists(os.path.join(self.project_root, 'pytest.ini')):
                test_command = 'pytest'
            elif os.path.exists(os.path.join(self.project_root, test_dir)):
                test_command = f'python -m unittest discover {test_dir}'
            else:
                test_command = 'python -m pytest'
        
        try:
            result = subprocess.run(
                test_command.split(),
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60  # 60秒超时
            )
            
            return {
                'command': test_command,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'success': result.returncode == 0
            }
            
        except subprocess.TimeoutExpired:
            return {
                'command': test_command,
                'return_code': -1,
                'stdout': '',
                'stderr': 'Test execution timed out',
                'success': False
            }
        except Exception as e:
            return {
                'command': test_command,
                'return_code': -1,
                'stdout': '',
                'stderr': str(e),
                'success': False
            }
    
    def analyze_dependencies(self, file_path: str = None) -> dict[str, Any]:
        """分析项目依赖
        
        Args:
            file_path: 特定文件路径，如果为None则分析整个项目
            
        Returns:
            依赖分析结果
        """
        dependencies = {
            'imports': [],
            'external_packages': [],
            'internal_modules': [],
            'missing_imports': []
        }
        
        if file_path:
            files_to_analyze = [file_path]
        else:
            files_to_analyze = []
            for root, dirs, files in os.walk(self.project_root):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for file in files:
                    if file.endswith('.py'):
                        files_to_analyze.append(os.path.relpath(os.path.join(root, file), self.project_root))
        
        for file_path in files_to_analyze:
            try:
                file_deps = self._analyze_file_dependencies(file_path)
                dependencies['imports'].extend(file_deps['imports'])
                dependencies['external_packages'].extend(file_deps['external_packages'])
                dependencies['internal_modules'].extend(file_deps['internal_modules'])
            except Exception as e:
                logger.warning(f"分析文件依赖失败 {file_path}: {e}")
        
        # 去重
        for key in dependencies:
            dependencies[key] = list(set(dependencies[key]))
        
        return dependencies
    
    def git_analysis(self) -> dict[str, Any]:
        """Git仓库分析
        
        Returns:
            Git分析结果
        """
        try:
            # 获取基本Git信息
            commands = {
                'branch': 'git branch --show-current',
                'status': 'git status --porcelain',
                'log': 'git log --oneline -10',
                'remote': 'git remote -v'
            }
            
            git_info = {}
            for name, command in commands.items():
                try:
                    result = subprocess.run(
                        command.split(),
                        cwd=self.project_root,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    git_info[name] = result.stdout.strip() if result.returncode == 0 else None
                except:
                    git_info[name] = None
            
            return {
                'is_git_repo': os.path.exists(os.path.join(self.project_root, '.git')),
                'current_branch': git_info['branch'],
                'status': git_info['status'],
                'recent_commits': git_info['log'].split('\n') if git_info['log'] else [],
                'remotes': git_info['remote'].split('\n') if git_info['remote'] else []
            }
            
        except Exception as e:
            return {
                'is_git_repo': False,
                'error': str(e)
            }
    
    def pattern_match(self, text: str, patterns: list[str]) -> dict[str, Any]:
        """模式匹配工具
        
        Args:
            text: 要匹配的文本
            patterns: 模式列表
            
        Returns:
            匹配结果
        """
        results = {}
        
        for pattern in patterns:
            try:
                matches = re.findall(pattern, text, re.MULTILINE | re.IGNORECASE)
                results[pattern] = {
                    'matches': matches,
                    'count': len(matches)
                }
            except re.error as e:
                results[pattern] = {
                    'error': str(e),
                    'matches': [],
                    'count': 0
                }
        
        return results
    
    def _analyze_python_file(self, content: str) -> dict[str, Any]:
        """分析Python文件"""
        try:
            tree = ast.parse(content)
            
            classes = []
            functions = []
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        imports.append(f"{module}.{alias.name}")
            
            return {
                'classes': classes,
                'functions': functions,
                'imports': imports,
                'is_valid_python': True
            }
            
        except SyntaxError as e:
            return {
                'is_valid_python': False,
                'syntax_error': str(e),
                'line_number': e.lineno
            }
    
    def _analyze_python_syntax(self, code: str) -> dict[str, Any]:
        """分析Python代码语法"""
        try:
            tree = ast.parse(code)
            return {
                'valid': True,
                'ast_dump': ast.dump(tree)[:500],  # 限制长度
                'analysis': self._analyze_python_file(code)
            }
        except SyntaxError as e:
            return {
                'valid': False,
                'error': str(e),
                'line_number': e.lineno,
                'offset': e.offset
            }
    
    def _analyze_generic_syntax(self, code: str) -> dict[str, Any]:
        """分析通用代码语法"""
        lines = code.split('\n')
        return {
            'lines': len(lines),
            'characters': len(code),
            'empty_lines': len([line for line in lines if not line.strip()]),
            'comment_lines': len([line for line in lines if line.strip().startswith('#')]),
            'brackets_balanced': self._check_brackets_balance(code)
        }
    
    def _check_brackets_balance(self, code: str) -> bool:
        """检查括号是否平衡"""
        stack = []
        pairs = {'(': ')', '[': ']', '{': '}'}
        
        for char in code:
            if char in pairs:
                stack.append(char)
            elif char in pairs.values():
                if not stack:
                    return False
                if pairs[stack.pop()] != char:
                    return False
        
        return len(stack) == 0
    
    def _analyze_file_dependencies(self, file_path: str) -> dict[str, Any]:
        """分析单个文件的依赖"""
        full_path = os.path.join(self.project_root, file_path)
        dependencies = {
            'imports': [],
            'external_packages': [],
            'internal_modules': []
        }
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dependencies['imports'].append(alias.name)
                        if self._is_external_package(alias.name):
                            dependencies['external_packages'].append(alias.name)
                        else:
                            dependencies['internal_modules'].append(alias.name)
                
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    dependencies['imports'].append(module)
                    if self._is_external_package(module):
                        dependencies['external_packages'].append(module)
                    else:
                        dependencies['internal_modules'].append(module)
        
        except Exception as e:
            logger.warning(f"分析文件依赖失败 {file_path}: {e}")
        
        return dependencies
    
    def _is_external_package(self, module_name: str) -> bool:
        """判断是否为外部包"""
        # 简单的判断逻辑，可以根据需要改进
        if not module_name:
            return False
        
        # 标准库模块
        stdlib_modules = {
            'os', 'sys', 'json', 'time', 'datetime', 'logging', 're', 'ast',
            'subprocess', 'pathlib', 'typing', 'collections', 'itertools',
            'functools', 'operator', 'math', 'random', 'string', 'io'
        }
        
        root_module = module_name.split('.')[0]
        
        # 如果是标准库模块，不算外部包
        if root_module in stdlib_modules:
            return False
        
        # 如果以项目名开头，算内部模块
        if root_module.startswith('src') or root_module.startswith('multi_agent_coder'):
            return False
        
        # 其他情况算外部包
        return True 