"""
参考项目分析器

负责分析用户传入的参考项目，提取关键的代码模式、架构风格、
最佳实践等信息，用于指导后续的代码生成。
"""

import os
import ast
import json
import logging
import asyncio
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Set

logger = logging.getLogger(__name__)


class ArchitecturePattern(Enum):
    """架构模式枚举"""
    MVC = "mvc"
    MICROSERVICES = "microservices"
    LAYERED = "layered"
    CLEAN_ARCHITECTURE = "clean_architecture"
    EVENT_DRIVEN = "event_driven"
    PLUGIN = "plugin"
    MONOLITHIC = "monolithic"


class FrameworkType(Enum):
    """框架类型枚举"""
    FASTAPI = "fastapi"
    DJANGO = "django"
    FLASK = "flask"
    STREAMLIT = "streamlit"
    TKINTER = "tkinter"
    PYTEST = "pytest"
    LANGCHAIN = "langchain"
    PYDANTIC = "pydantic"
    SQLALCHEMY = "sqlalchemy"


@dataclass
class CodePattern:
    """代码模式数据类"""
    pattern_type: str
    description: str
    example_code: str
    file_path: str
    frequency: int = 1


@dataclass
class ProjectStructure:
    """项目结构数据类"""
    directories: list[str]
    main_modules: list[str]
    config_files: list[str]
    test_directories: list[str]
    documentation_files: list[str]


@dataclass
class CodingStyle:
    """编码风格数据类"""
    naming_conventions: dict[str, str]
    import_patterns: list[str]
    error_handling_patterns: list[str]
    documentation_style: str
    type_hints_usage: bool
    async_patterns: list[str]


@dataclass
class TechStack:
    """技术栈数据类"""
    frameworks: list[FrameworkType]
    dependencies: dict[str, str]
    python_version: Optional[str]
    architecture_patterns: list[ArchitecturePattern]


@dataclass
class ReferenceProjectAnalysis:
    """参考项目分析结果"""
    project_name: str
    project_path: str
    tech_stack: TechStack
    project_structure: ProjectStructure
    coding_style: CodingStyle
    code_patterns: list[CodePattern]
    best_practices: list[str]
    common_utilities: list[str]
    api_patterns: list[str]
    error_handling_strategies: list[str]
    testing_patterns: list[str]
    deployment_patterns: list[str]


class ReferenceProjectAnalyzer:
    """参考项目分析器"""
    
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        self.supported_extensions = {'.py', '.yaml', '.yml', '.json', '.toml', '.md', '.txt'}
        
    def detect_reference_projects(self) -> list[str]:
        """检测工作空间中的参考项目"""
        reference_projects = []
        
        for item in self.workspace_root.iterdir():
            if item.is_dir() and item.name not in {'.git', '.venv', '__pycache__', 'node_modules', 'agent_repos', 'src', '.memory'}:
                # 检查是否是有效的Python项目
                if self._is_valid_python_project(item):
                    reference_projects.append(item.name)
                    logger.info(f"🔍 检测到参考项目: {item.name}")
        
        return reference_projects
    
    def _is_valid_python_project(self, project_path: Path) -> bool:
        """判断是否是有效的Python项目"""
        # 检查常见的Python项目标识文件
        indicators = [
            'setup.py', 'pyproject.toml', 'requirements.txt', 
            'Pipfile', 'poetry.lock', 'environment.yml'
        ]
        
        for indicator in indicators:
            if (project_path / indicator).exists():
                return True
        
        # 检查是否包含Python文件
        python_files = list(project_path.rglob('*.py'))
        return len(python_files) > 0
    
    async def analyze_project(self, project_name: str) -> ReferenceProjectAnalysis:
        """分析指定的参考项目"""
        project_path = self.workspace_root / project_name
        
        if not project_path.exists():
            raise ValueError(f"参考项目不存在: {project_name}")
        
        logger.info(f"🔍 开始分析参考项目: {project_name}")
        
        # 分析项目结构
        project_structure = self._analyze_project_structure(project_path)
        
        # 分析技术栈
        tech_stack = self._analyze_tech_stack(project_path)
        
        # 分析编码风格
        coding_style = await self._analyze_coding_style(project_path)
        
        # 提取代码模式
        code_patterns = await self._extract_code_patterns(project_path)
        
        # 分析最佳实践
        best_practices = self._analyze_best_practices(project_path, code_patterns)
        
        # 分析常用工具
        common_utilities = self._extract_common_utilities(project_path)
        
        # 分析API模式
        api_patterns = self._extract_api_patterns(project_path)
        
        # 分析错误处理策略
        error_handling = self._extract_error_handling_strategies(project_path)
        
        # 分析测试模式
        testing_patterns = self._extract_testing_patterns(project_path)
        
        # 分析部署模式
        deployment_patterns = self._extract_deployment_patterns(project_path)
        
        analysis = ReferenceProjectAnalysis(
            project_name=project_name,
            project_path=str(project_path),
            tech_stack=tech_stack,
            project_structure=project_structure,
            coding_style=coding_style,
            code_patterns=code_patterns,
            best_practices=best_practices,
            common_utilities=common_utilities,
            api_patterns=api_patterns,
            error_handling_strategies=error_handling,
            testing_patterns=testing_patterns,
            deployment_patterns=deployment_patterns
        )
        
        logger.info(f"✅ 完成参考项目分析: {project_name}")
        return analysis
    
    def _analyze_project_structure(self, project_path: Path) -> ProjectStructure:
        """分析项目结构"""
        directories = []
        main_modules = []
        config_files = []
        test_directories = []
        documentation_files = []
        
        for root, dirs, files in os.walk(project_path):
            root_path = Path(root)
            relative_path = root_path.relative_to(project_path)
            
            # 跳过隐藏目录和虚拟环境
            if any(part.startswith('.') or part in {'__pycache__', 'node_modules'} for part in relative_path.parts):
                continue
            
            directories.append(str(relative_path))
            
            # 识别测试目录
            if any(keyword in str(relative_path).lower() for keyword in ['test', 'tests']):
                test_directories.append(str(relative_path))
            
            for file in files:
                file_path = root_path / file
                relative_file_path = file_path.relative_to(project_path)
                
                # 配置文件
                if file in ['setup.py', 'pyproject.toml', 'requirements.txt', 'Dockerfile', 'docker-compose.yml']:
                    config_files.append(str(relative_file_path))
                
                # 文档文件
                elif file.lower().endswith(('.md', '.rst', '.txt')) and any(keyword in file.lower() for keyword in ['readme', 'doc', 'guide']):
                    documentation_files.append(str(relative_file_path))
                
                # 主要模块（Python文件）
                elif file.endswith('.py') and not file.startswith('test_'):
                    if file in ['__init__.py', 'main.py', 'app.py', 'server.py']:
                        main_modules.append(str(relative_file_path))
        
        return ProjectStructure(
            directories=directories[:20],  # 限制数量
            main_modules=main_modules,
            config_files=config_files,
            test_directories=test_directories,
            documentation_files=documentation_files
        )
    
    def _analyze_tech_stack(self, project_path: Path) -> TechStack:
        """分析技术栈"""
        frameworks = []
        dependencies = {}
        python_version = None
        architecture_patterns = []
        
        # 分析依赖文件
        deps = self._parse_dependencies(project_path)
        dependencies.update(deps)
        
        # 检测框架
        for dep, version in deps.items():
            dep_lower = dep.lower()
            if 'fastapi' in dep_lower:
                frameworks.append(FrameworkType.FASTAPI)
            elif 'django' in dep_lower:
                frameworks.append(FrameworkType.DJANGO)
            elif 'flask' in dep_lower:
                frameworks.append(FrameworkType.FLASK)
            elif 'streamlit' in dep_lower:
                frameworks.append(FrameworkType.STREAMLIT)
            elif 'pytest' in dep_lower:
                frameworks.append(FrameworkType.PYTEST)
            elif 'langchain' in dep_lower:
                frameworks.append(FrameworkType.LANGCHAIN)
            elif 'pydantic' in dep_lower:
                frameworks.append(FrameworkType.PYDANTIC)
            elif 'sqlalchemy' in dep_lower:
                frameworks.append(FrameworkType.SQLALCHEMY)
        
        # 检测架构模式
        architecture_patterns = self._detect_architecture_patterns(project_path)
        
        # 检测Python版本
        python_version = self._detect_python_version(project_path)
        
        return TechStack(
            frameworks=frameworks,
            dependencies=dependencies,
            python_version=python_version,
            architecture_patterns=architecture_patterns
        )
    
    def _parse_dependencies(self, project_path: Path) -> dict[str, str]:
        """解析依赖文件"""
        dependencies = {}
        
        # 在项目根目录和主要子目录中查找依赖文件
        search_paths = [project_path]
        
        # 添加常见的子项目目录
        for subdir in ['platform', 'backend', 'api', 'server', 'src']:
            subpath = project_path / subdir
            if subpath.exists() and subpath.is_dir():
                search_paths.append(subpath)
        
        for search_path in search_paths:
            # requirements.txt
            req_file = search_path / 'requirements.txt'
            if req_file.exists():
                try:
                    content = req_file.read_text()
                    for line in content.splitlines():
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '==' in line:
                                name, version = line.split('==', 1)
                                dependencies[name.strip()] = version.strip()
                            elif '>=' in line:
                                name = line.split('>=')[0].strip()
                                dependencies[name] = 'latest'
                            else:
                                dependencies[line] = 'latest'
                except Exception as e:
                    logger.warning(f"解析requirements.txt失败: {e}")
            
            # pyproject.toml
            pyproject_file = search_path / 'pyproject.toml'
            if pyproject_file.exists():
                try:
                    import toml
                    data = toml.load(pyproject_file)
                    
                    # 支持Poetry格式: [tool.poetry.dependencies]
                    poetry_deps = data.get('tool', {}).get('poetry', {}).get('dependencies', {})
                    for name, version_spec in poetry_deps.items():
                        if name != 'python':  # 跳过python版本约束
                            if isinstance(version_spec, str):
                                # 处理 "^0.98.0" 格式
                                version = version_spec.lstrip('^~>=<')
                                dependencies[name] = version
                            elif hasattr(version_spec, 'get'):  # 处理字典或类字典对象
                                # 处理 { version = "^0.22.0", extras = ["standard"] } 格式
                                version = version_spec.get('version', 'latest')
                                if isinstance(version, str):
                                    dependencies[name] = version.lstrip('^~>=<')
                                else:
                                    dependencies[name] = 'latest'
                    
                    # 支持标准格式: [project.dependencies]
                    if 'dependencies' in data.get('project', {}):
                        for dep in data['project']['dependencies']:
                            if '==' in dep:
                                name, version = dep.split('==', 1)
                                dependencies[name.strip()] = version.strip()
                            else:
                                dependencies[dep] = 'latest'
                                
                except Exception as e:
                    logger.warning(f"解析pyproject.toml失败 ({search_path}): {e}")
        
        return dependencies
    
    def _detect_architecture_patterns(self, project_path: Path) -> list[ArchitecturePattern]:
        """检测架构模式"""
        patterns = []
        
        # 检查目录结构来推断架构模式
        dirs = [d.name for d in project_path.iterdir() if d.is_dir()]
        
        # 微服务架构
        if any(keyword in ' '.join(dirs).lower() for keyword in ['service', 'api', 'microservice']):
            patterns.append(ArchitecturePattern.MICROSERVICES)
        
        # MVC模式
        if any(keyword in ' '.join(dirs).lower() for keyword in ['model', 'view', 'controller']):
            patterns.append(ArchitecturePattern.MVC)
        
        # 分层架构
        if any(keyword in ' '.join(dirs).lower() for keyword in ['domain', 'application', 'infrastructure']):
            patterns.append(ArchitecturePattern.LAYERED)
        
        # 清洁架构
        if any(keyword in ' '.join(dirs).lower() for keyword in ['use_case', 'entity', 'adapter']):
            patterns.append(ArchitecturePattern.CLEAN_ARCHITECTURE)
        
        # 插件架构
        if any(keyword in ' '.join(dirs).lower() for keyword in ['plugin', 'extension']):
            patterns.append(ArchitecturePattern.PLUGIN)
        
        return patterns if patterns else [ArchitecturePattern.MONOLITHIC]
    
    def _detect_python_version(self, project_path: Path) -> Optional[str]:
        """检测Python版本"""
        # 在项目根目录和主要子目录中查找Python版本信息
        search_paths = [project_path]
        
        # 添加常见的子项目目录
        for subdir in ['platform', 'backend', 'api', 'server', 'src']:
            subpath = project_path / subdir
            if subpath.exists() and subpath.is_dir():
                search_paths.append(subpath)
        
        for search_path in search_paths:
            # 从pyproject.toml检测
            pyproject_file = search_path / 'pyproject.toml'
            if pyproject_file.exists():
                try:
                    import toml
                    data = toml.load(pyproject_file)
                    
                    # Poetry格式
                    poetry_python = data.get('tool', {}).get('poetry', {}).get('dependencies', {}).get('python')
                    if poetry_python:
                        return poetry_python
                    
                    # 标准格式
                    python_req = data.get('project', {}).get('requires-python')
                    if python_req:
                        return python_req
                except Exception:
                    continue
            
            # 从.python-version检测
            python_version_file = search_path / '.python-version'
            if python_version_file.exists():
                try:
                    return python_version_file.read_text().strip()
                except Exception:
                    continue
        
        return None
    
    async def _analyze_coding_style(self, project_path: Path) -> CodingStyle:
        """分析编码风格"""
        naming_conventions = {}
        import_patterns = []
        error_handling_patterns = []
        documentation_style = "google"  # 默认
        type_hints_usage = False
        async_patterns = []
        
        # 分析Python文件
        python_files = list(project_path.rglob('*.py'))[:50]  # 限制文件数量
        
        for py_file in python_files:
            try:
                content = py_file.read_text(encoding='utf-8')
                tree = ast.parse(content)
                
                # 分析命名约定
                self._analyze_naming_conventions(tree, naming_conventions)
                
                # 分析导入模式
                self._analyze_import_patterns(content, import_patterns)
                
                # 分析错误处理
                self._analyze_error_handling(tree, error_handling_patterns)
                
                # 检查类型提示
                if self._has_type_hints(tree):
                    type_hints_usage = True
                
                # 检查异步模式
                self._analyze_async_patterns(tree, async_patterns)
                
            except Exception as e:
                logger.warning(f"分析文件 {py_file} 失败: {e}")
                continue
        
        return CodingStyle(
            naming_conventions=naming_conventions,
            import_patterns=list(set(import_patterns)),
            error_handling_patterns=list(set(error_handling_patterns)),
            documentation_style=documentation_style,
            type_hints_usage=type_hints_usage,
            async_patterns=list(set(async_patterns))
        )
    
    def _analyze_naming_conventions(self, tree: ast.AST, conventions: dict[str, str]):
        """分析命名约定"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if re.match(r'^[A-Z][a-zA-Z0-9]*$', node.name):
                    conventions['class'] = 'PascalCase'
            elif isinstance(node, ast.FunctionDef):
                if re.match(r'^[a-z_][a-z0-9_]*$', node.name):
                    conventions['function'] = 'snake_case'
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                if re.match(r'^[a-z_][a-z0-9_]*$', node.id):
                    conventions['variable'] = 'snake_case'
                elif re.match(r'^[A-Z_][A-Z0-9_]*$', node.id):
                    conventions['constant'] = 'UPPER_SNAKE_CASE'
    
    def _analyze_import_patterns(self, content: str, patterns: list[str]):
        """分析导入模式"""
        lines = content.splitlines()
        for line in lines:
            line = line.strip()
            if line.startswith('from ') and ' import ' in line:
                patterns.append('relative_import')
            elif line.startswith('import '):
                patterns.append('absolute_import')
            elif re.match(r'from \. import', line):
                patterns.append('package_relative_import')
    
    def _analyze_error_handling(self, tree: ast.AST, patterns: list[str]):
        """分析错误处理模式"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                if node.handlers:
                    patterns.append('try_except')
                if node.finalbody:
                    patterns.append('try_finally')
            elif isinstance(node, ast.Raise):
                patterns.append('explicit_raise')
            elif isinstance(node, ast.Assert):
                patterns.append('assertion')
    
    def _has_type_hints(self, tree: ast.AST) -> bool:
        """检查是否使用类型提示"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.returns or any(arg.annotation for arg in node.args.args):
                    return True
        return False
    
    def _analyze_async_patterns(self, tree: ast.AST, patterns: list[str]):
        """分析异步模式"""
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                patterns.append('async_function')
            elif isinstance(node, ast.Await):
                patterns.append('await_usage')
            elif isinstance(node, ast.AsyncWith):
                patterns.append('async_context_manager')
    
    async def _extract_code_patterns(self, project_path: Path) -> list[CodePattern]:
        """提取代码模式"""
        patterns = []
        
        # 扫描Python文件寻找常见模式
        python_files = list(project_path.rglob('*.py'))[:30]  # 限制文件数量
        
        for py_file in python_files:
            try:
                content = py_file.read_text(encoding='utf-8')
                
                # 检测设计模式
                self._detect_design_patterns(content, py_file, patterns)
                
                # 检测API模式
                self._detect_api_patterns_in_file(content, py_file, patterns)
                
                # 检测数据处理模式
                self._detect_data_patterns(content, py_file, patterns)
                
            except Exception as e:
                logger.warning(f"提取模式失败 {py_file}: {e}")
                continue
        
        return patterns
    
    def _detect_design_patterns(self, content: str, file_path: Path, patterns: list[CodePattern]):
        """检测设计模式"""
        # Singleton模式
        if 'def __new__' in content and '_instance' in content:
            patterns.append(CodePattern(
                pattern_type="Singleton",
                description="单例模式实现",
                example_code=self._extract_class_code(content, 'singleton'),
                file_path=str(file_path)
            ))
        
        # Factory模式
        if re.search(r'def create.*\(.*\):', content):
            patterns.append(CodePattern(
                pattern_type="Factory",
                description="工厂模式实现",
                example_code=self._extract_function_code(content, 'create'),
                file_path=str(file_path)
            ))
        
        # Dependency Injection模式
        if 'Depends(' in content or '@inject' in content:
            patterns.append(CodePattern(
                pattern_type="DependencyInjection",
                description="依赖注入模式",
                example_code=self._extract_dependency_code(content),
                file_path=str(file_path)
            ))
    
    def _detect_api_patterns_in_file(self, content: str, file_path: Path, patterns: list[CodePattern]):
        """检测API模式"""
        # FastAPI路由模式
        if '@router.' in content or '@app.' in content:
            patterns.append(CodePattern(
                pattern_type="APIRouter",
                description="API路由定义模式",
                example_code=self._extract_route_code(content),
                file_path=str(file_path)
            ))
        
        # 中间件模式
        if 'middleware' in content.lower():
            patterns.append(CodePattern(
                pattern_type="Middleware",
                description="中间件模式",
                example_code=self._extract_middleware_code(content),
                file_path=str(file_path)
            ))
    
    def _detect_data_patterns(self, content: str, file_path: Path, patterns: list[CodePattern]):
        """检测数据处理模式"""
        # Pydantic模型模式
        if 'BaseModel' in content:
            patterns.append(CodePattern(
                pattern_type="PydanticModel",
                description="Pydantic数据模型",
                example_code=self._extract_model_code(content),
                file_path=str(file_path)
            ))
        
        # 数据库ORM模式
        if 'declarative_base' in content or 'Table' in content:
            patterns.append(CodePattern(
                pattern_type="ORMModel",
                description="ORM数据模型",
                example_code=self._extract_orm_code(content),
                file_path=str(file_path)
            ))
    
    def _extract_class_code(self, content: str, keyword: str) -> str:
        """提取类定义代码"""
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith('class ') and keyword.lower() in line.lower():
                # 提取整个类定义
                class_lines = [line]
                indent = len(line) - len(line.lstrip())
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() == '':
                        class_lines.append(lines[j])
                    elif len(lines[j]) - len(lines[j].lstrip()) > indent:
                        class_lines.append(lines[j])
                    else:
                        break
                return '\n'.join(class_lines[:20])  # 限制行数
        return ""
    
    def _extract_function_code(self, content: str, keyword: str) -> str:
        """提取函数定义代码"""
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith('def ') and keyword in line:
                func_lines = [line]
                indent = len(line) - len(line.lstrip())
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() == '':
                        func_lines.append(lines[j])
                    elif len(lines[j]) - len(lines[j].lstrip()) > indent:
                        func_lines.append(lines[j])
                    else:
                        break
                return '\n'.join(func_lines[:15])  # 限制行数
        return ""
    
    def _extract_dependency_code(self, content: str) -> str:
        """提取依赖注入相关代码"""
        lines = content.splitlines()
        result_lines = []
        for line in lines:
            if 'Depends(' in line or '@inject' in line:
                result_lines.append(line)
        return '\n'.join(result_lines[:10])
    
    def _extract_route_code(self, content: str) -> str:
        """提取路由定义代码"""
        lines = content.splitlines()
        result_lines = []
        for i, line in enumerate(lines):
            if '@router.' in line or '@app.' in line:
                result_lines.append(line)
                # 添加函数定义
                if i + 1 < len(lines):
                    result_lines.append(lines[i + 1])
        return '\n'.join(result_lines[:15])
    
    def _extract_middleware_code(self, content: str) -> str:
        """提取中间件代码"""
        lines = content.splitlines()
        result_lines = []
        for line in lines:
            if 'middleware' in line.lower():
                result_lines.append(line)
        return '\n'.join(result_lines[:10])
    
    def _extract_model_code(self, content: str) -> str:
        """提取模型定义代码"""
        return self._extract_class_code(content, 'BaseModel')
    
    def _extract_orm_code(self, content: str) -> str:
        """提取ORM模型代码"""
        return self._extract_class_code(content, 'Table')
    
    def _analyze_best_practices(self, project_path: Path, code_patterns: list[CodePattern]) -> list[str]:
        """分析最佳实践"""
        practices = []
        
        # 基于代码模式推断最佳实践
        pattern_types = [p.pattern_type for p in code_patterns]
        
        if 'DependencyInjection' in pattern_types:
            practices.append("使用依赖注入提高代码可测试性")
        
        if 'PydanticModel' in pattern_types:
            practices.append("使用Pydantic进行数据验证")
        
        if 'APIRouter' in pattern_types:
            practices.append("使用路由器组织API端点")
        
        # 检查文档
        if any((project_path / f).exists() for f in ['README.md', 'docs']):
            practices.append("维护详细的项目文档")
        
        # 检查测试
        if any(p.name.startswith('test') for p in project_path.rglob('*.py')):
            practices.append("编写comprehensive测试")
        
        # 检查配置管理
        if (project_path / 'config').exists() or any('config' in str(p) for p in project_path.rglob('*.py')):
            practices.append("集中管理配置")
        
        return practices
    
    def _extract_common_utilities(self, project_path: Path) -> list[str]:
        """提取常用工具函数"""
        utilities = []
        
        utils_dirs = ['utils', 'helpers', 'common', 'core']
        for utils_dir in utils_dirs:
            utils_path = project_path / utils_dir
            if utils_path.exists():
                for py_file in utils_path.rglob('*.py'):
                    utilities.append(f"{utils_dir}/{py_file.name}")
        
        return utilities
    
    def _extract_api_patterns(self, project_path: Path) -> list[str]:
        """提取API模式"""
        patterns = []
        
        # 查找API相关文件
        api_files = list(project_path.rglob('*api*.py')) + list(project_path.rglob('*router*.py'))
        
        for api_file in api_files[:10]:  # 限制文件数量
            try:
                content = api_file.read_text()
                if 'async def' in content:
                    patterns.append("异步API端点")
                if 'StreamingResponse' in content:
                    patterns.append("流式响应")
                if 'HTTPException' in content:
                    patterns.append("HTTP异常处理")
                if 'middleware' in content.lower():
                    patterns.append("API中间件")
            except Exception:
                continue
        
        return list(set(patterns))
    
    def _extract_error_handling_strategies(self, project_path: Path) -> list[str]:
        """提取错误处理策略"""
        strategies = []
        
        python_files = list(project_path.rglob('*.py'))[:20]
        for py_file in python_files:
            try:
                content = py_file.read_text()
                if 'logging' in content:
                    strategies.append("结构化日志记录")
                if 'HTTPException' in content:
                    strategies.append("HTTP异常处理")
                if 'ValidationError' in content:
                    strategies.append("数据验证错误处理")
                if 'try:' in content and 'except' in content:
                    strategies.append("异常捕获和处理")
            except Exception:
                continue
        
        return list(set(strategies))
    
    def _extract_testing_patterns(self, project_path: Path) -> list[str]:
        """提取测试模式"""
        patterns = []
        
        test_files = list(project_path.rglob('test_*.py')) + list(project_path.rglob('*_test.py'))
        
        for test_file in test_files[:10]:
            try:
                content = test_file.read_text()
                if 'pytest' in content:
                    patterns.append("pytest测试框架")
                if 'mock' in content.lower():
                    patterns.append("模拟对象测试")
                if 'fixture' in content:
                    patterns.append("测试夹具")
                if 'async def test_' in content:
                    patterns.append("异步测试")
            except Exception:
                continue
        
        return list(set(patterns))
    
    def _extract_deployment_patterns(self, project_path: Path) -> list[str]:
        """提取部署模式"""
        patterns = []
        
        if (project_path / 'Dockerfile').exists():
            patterns.append("Docker容器化")
        
        if (project_path / 'docker-compose.yml').exists():
            patterns.append("Docker Compose编排")
        
        if (project_path / '.github' / 'workflows').exists():
            patterns.append("GitHub Actions CI/CD")
        
        if (project_path / 'requirements.txt').exists():
            patterns.append("pip依赖管理")
        
        if (project_path / 'pyproject.toml').exists():
            patterns.append("现代Python项目结构")
        
        return patterns
    
    def get_analysis_summary(self, analysis: ReferenceProjectAnalysis) -> str:
        """获取分析摘要"""
        summary_parts = [
            f"📦 项目: {analysis.project_name}",
            f"🏗️ 架构: {', '.join([p.value for p in analysis.tech_stack.architecture_patterns])}",
            f"🛠️ 框架: {', '.join([f.value for f in analysis.tech_stack.frameworks])}",
            f"📝 代码模式: {len(analysis.code_patterns)} 个",
            f"✨ 最佳实践: {len(analysis.best_practices)} 个",
            f"🔧 工具函数: {len(analysis.common_utilities)} 个"
        ]
        
        return '\n'.join(summary_parts) 

    async def analyze_projects(self) -> dict[str, dict[str, Any]]:
        """分析所有检测到的参考项目"""
        results = {}
        
        # 检测参考项目
        reference_projects = self.detect_reference_projects()
        
        if not reference_projects:
            logger.info("📭 未检测到参考项目")
            return results
        
        logger.info(f"🔍 检测到 {len(reference_projects)} 个参考项目: {', '.join(reference_projects)}")
        
        for project_name in reference_projects:
            try:
                logger.info(f"🔎 开始分析参考项目: {project_name}")
                analysis = await self.analyze_project(project_name)
                
                # 转换为可序列化的字典格式
                project_data = {
                    'name': analysis.project_name,
                    'path': analysis.project_path,
                    'frameworks': [f.value for f in analysis.tech_stack.frameworks],
                    'patterns': [p.value for p in analysis.tech_stack.architecture_patterns],
                    'dependencies': analysis.tech_stack.dependencies,
                    'python_version': analysis.tech_stack.python_version,
                    'best_practices': analysis.best_practices,
                    'code_patterns': [
                        {
                            'type': pattern.pattern_type,
                            'description': pattern.description,
                            'example': pattern.example_code,
                            'file_path': pattern.file_path,
                            'frequency': pattern.frequency
                        }
                        for pattern in analysis.code_patterns
                    ],
                    'coding_guidelines': [
                        "遵循PEP 8风格规范",
                        "使用类型提示" if analysis.coding_style.type_hints_usage else "考虑添加类型提示",
                        f"文档风格: {analysis.coding_style.documentation_style}",
                        *analysis.coding_style.import_patterns[:3],
                        *analysis.coding_style.error_handling_patterns[:3]
                    ],
                    'architecture_insights': [
                        f"项目采用 {', '.join([p.value for p in analysis.tech_stack.architecture_patterns])} 架构模式",
                        f"主要技术栈: {', '.join([f.value for f in analysis.tech_stack.frameworks])}",
                        f"包含 {len(analysis.code_patterns)} 种代码模式",
                        *analysis.api_patterns[:2],
                        *analysis.testing_patterns[:2]
                    ],
                    'common_utilities': analysis.common_utilities,
                    'api_patterns': analysis.api_patterns,
                    'error_handling_strategies': analysis.error_handling_strategies,
                    'testing_patterns': analysis.testing_patterns,
                    'deployment_patterns': analysis.deployment_patterns
                }
                
                results[project_name] = project_data
                
                # 打印分析摘要
                summary = self.get_analysis_summary(analysis)
                logger.info(f"✅ 完成项目分析:\n{summary}")
                
            except Exception as e:
                logger.error(f"❌ 分析项目 {project_name} 失败: {e}")
                # 继续分析其他项目
                continue
        
        if results:
            logger.info(f"🎉 成功分析了 {len(results)} 个参考项目")
        else:
            logger.warning("⚠️ 没有成功分析任何参考项目")
        
        return results 