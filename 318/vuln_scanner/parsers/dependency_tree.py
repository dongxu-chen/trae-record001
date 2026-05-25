"""
依赖树解析器
支持解析 Maven、npm、pip、Go 的完整依赖树，包括传递依赖
"""
import os
import json
import subprocess
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from ..models import Dependency, PackageManager


@dataclass
class DependencyTree:
    """依赖树结构"""
    root: Optional[Dependency] = None
    all_dependencies: List[Dependency] = field(default_factory=list)

    def flatten(self) -> List[Dependency]:
        """将依赖树展开为平面列表"""
        return list(self.all_dependencies)

    def get_direct_dependencies(self) -> List[Dependency]:
        """获取直接依赖"""
        return [d for d in self.all_dependencies if d.depth == 0]

    def get_transitive_dependencies(self) -> List[Dependency]:
        """获取传递依赖"""
        return [d for d in self.all_dependencies if d.depth > 0]

    def print_tree(self) -> None:
        """打印依赖树"""
        if not self.root:
            return

        def print_node(node: Dependency, prefix: str = ""):
            connector = "├── " if prefix else ""
            print(f"{prefix}{connector}{node.full_name}@{node.version}")
            for i, child in enumerate(node.children):
                is_last = i == len(node.children) - 1
                new_prefix = prefix + ("│   " if not is_last else "    ")
                print_node(child, new_prefix)

        print_node(self.root)


class DependencyTreeResolver:
    """依赖树解析器基类"""

    def __init__(self, project_path: str):
        self.project_path = project_path

    def resolve(self, include_transitive: bool = True) -> DependencyTree:
        """解析依赖树"""
        raise NotImplementedError


class PipDependencyTreeResolver(DependencyTreeResolver):
    """pip 依赖树解析器"""

    def resolve(self, include_transitive: bool = True) -> DependencyTree:
        tree = DependencyTree()

        if not include_transitive:
            from .pip_parser import PipParser
            parser = PipParser(self.project_path)
            deps = parser.parse()
            tree.all_dependencies = deps
            if deps:
                tree.root = deps[0]
            return tree

        try:
            deps = self._resolve_with_pipdeptree()
            if deps:
                tree.all_dependencies = deps
                if deps:
                    tree.root = deps[0]
                return tree
        except Exception:
            pass

        try:
            deps = self._resolve_with_pip_show()
            if deps:
                tree.all_dependencies = deps
                if deps:
                    tree.root = deps[0]
                return tree
        except Exception:
            pass

        from .pip_parser import PipParser
        parser = PipParser(self.project_path)
        deps = parser.parse()
        tree.all_dependencies = deps
        if deps:
            tree.root = deps[0]

        return tree

    def _resolve_with_pipdeptree(self) -> List[Dependency]:
        """使用 pipdeptree 解析依赖树"""
        try:
            result = subprocess.run(
                ["pip", "deptree", "--json-output", "--warn", "silence"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.project_path,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return self._parse_pipdeptree_json(data)
        except Exception:
            pass

        try:
            result = subprocess.run(
                ["python", "-m", "pipdeptree", "--json-output", "--warn", "silence"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.project_path,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return self._parse_pipdeptree_json(data)
        except Exception:
            pass

        return []

    def _parse_pipdeptree_json(self, data: List[Dict[str, Any]]) -> List[Dependency]:
        """解析 pipdeptree JSON 输出"""
        dependencies: List[Dependency] = []
        dep_map: Dict[str, Dependency] = {}

        def create_dep(item: Dict[str, Any], parent: Optional[Dependency] = None, depth: int = 0) -> Dependency:
            package = item.get("package", {})
            name = package.get("package_name", package.get("key", ""))
            version = package.get("installed_version", "")

            key = f"{name}=={version}"
            if key in dep_map:
                existing = dep_map[key]
                if parent:
                    parent.children.append(existing)
                    existing.parent = parent
                    existing.depth = min(existing.depth, depth)
                return existing

            dep = Dependency(
                name=name,
                version=version,
                package_manager=PackageManager.PIP,
                parent=parent,
                depth=depth,
                is_transitive=depth > 0,
            )
            dep_map[key] = dep
            dependencies.append(dep)

            for child_item in item.get("dependencies", []):
                child = create_dep(child_item, dep, depth + 1)
                if child not in dep.children:
                    dep.children.append(child)

            return dep

        for item in data:
            create_dep(item)

        return dependencies

    def _resolve_with_pip_show(self) -> List[Dependency]:
        """使用 pip show 解析依赖"""
        try:
            req_file = os.path.join(self.project_path, "requirements.txt")
            if not os.path.exists(req_file):
                return []

            direct_deps = []
            with open(req_file, "r") as f:
                import re
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    match = re.match(r"^([a-zA-Z0-9_\-\.]+)\s*([=><!~]+[^,\s]+)?", line)
                    if match:
                        name = match.group(1)
                        version = match.group(2) or ""
                        version = version.lstrip("=><!~")
                        direct_deps.append((name, version))

            dependencies: List[Dependency] = []
            visited: set = set()

            def resolve_dep(name: str, version: str, parent: Optional[Dependency] = None, depth: int = 0) -> Optional[Dependency]:
                key = f"{name}=={version}"
                if key in visited:
                    return None
                visited.add(key)

                dep = Dependency(
                    name=name,
                    version=version,
                    package_manager=PackageManager.PIP,
                    parent=parent,
                    depth=depth,
                    is_transitive=depth > 0,
                )
                dependencies.append(dep)

                try:
                    result = subprocess.run(
                        ["pip", "show", name],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if result.returncode == 0:
                        for line in result.stdout.split("\n"):
                            if line.startswith("Requires:"):
                                requires = line[len("Requires:"):].strip()
                                if requires:
                                    for sub_name in [r.strip() for r in requires.split(",")]:
                                        if sub_name:
                                            sub_dep = resolve_dep(sub_name, "", dep, depth + 1)
                                            if sub_dep and sub_dep not in dep.children:
                                                dep.children.append(sub_dep)
                except Exception:
                    pass

                return dep

            for name, version in direct_deps:
                resolve_dep(name, version)

            return dependencies

        except Exception:
            return []


class NpmDependencyTreeResolver(DependencyTreeResolver):
    """npm 依赖树解析器"""

    def resolve(self, include_transitive: bool = True) -> DependencyTree:
        tree = DependencyTree()

        try:
            deps = self._resolve_with_npm_ls()
            if deps:
                tree.all_dependencies = deps
                if deps:
                    tree.root = deps[0]
                return tree
        except Exception:
            pass

        try:
            deps = self._resolve_from_package_lock()
            if deps:
                tree.all_dependencies = deps
                if deps:
                    tree.root = deps[0]
                return tree
        except Exception:
            pass

        from .npm_parser import NpmParser
        parser = NpmParser(self.project_path)
        deps = parser.parse()
        tree.all_dependencies = deps
        if deps:
            tree.root = deps[0]

        return tree

    def _resolve_with_npm_ls(self) -> List[Dependency]:
        """使用 npm ls 解析依赖树"""
        try:
            result = subprocess.run(
                ["npm", "ls", "--json", "--all"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.project_path,
            )
            if result.returncode == 0 or result.stdout.strip():
                data = json.loads(result.stdout)
                return self._parse_npm_ls_json(data)
        except Exception:
            pass

        try:
            result = subprocess.run(
                ["npx", "ls", "--json", "--all"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.project_path,
            )
            if result.returncode == 0 or result.stdout.strip():
                data = json.loads(result.stdout)
                return self._parse_npm_ls_json(data)
        except Exception:
            pass

        return []

    def _parse_npm_ls_json(self, data: Dict[str, Any]) -> List[Dependency]:
        """解析 npm ls JSON 输出"""
        dependencies: List[Dependency] = []
        dep_map: Dict[str, Dependency] = {}

        def parse_node(node: Dict[str, Any], parent: Optional[Dependency] = None, depth: int = 0) -> Optional[Dependency]:
            name = node.get("name", "")
            version = node.get("version", "")

            if not name:
                return None

            key = f"{name}@${version}"
            if key in dep_map:
                return dep_map[key]

            dep = Dependency(
                name=name,
                version=version,
                package_manager=PackageManager.NPM,
                parent=parent,
                depth=depth,
                is_transitive=depth > 0,
            )
            dep_map[key] = dep
            dependencies.append(dep)

            for child_name, child_node in node.get("dependencies", {}).items():
                if isinstance(child_node, dict):
                    child_dep = parse_node(child_node, dep, depth + 1)
                    if child_dep and child_dep not in dep.children:
                        dep.children.append(child_dep)

            return dep

        root = parse_node(data)
        if root:
            root.is_transitive = False
            root.depth = 0

        return dependencies

    def _resolve_from_package_lock(self) -> List[Dependency]:
        """从 package-lock.json 解析依赖"""
        lock_file = os.path.join(self.project_path, "package-lock.json")
        if not os.path.exists(lock_file):
            return []

        try:
            with open(lock_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            dependencies: List[Dependency] = []
            packages = data.get("packages", {})

            for path, pkg_info in packages.items():
                if not path:
                    continue

                name = pkg_info.get("name", path.split("/")[-1])
                version = pkg_info.get("version", "")

                if not name or not version:
                    continue

                dep = Dependency(
                    name=name,
                    version=version,
                    package_manager=PackageManager.NPM,
                    is_transitive=True,
                )
                dependencies.append(dep)

            return dependencies

        except Exception:
            return []


class MavenDependencyTreeResolver(DependencyTreeResolver):
    """Maven 依赖树解析器"""

    def resolve(self, include_transitive: bool = True) -> DependencyTree:
        tree = DependencyTree()

        try:
            deps = self._resolve_with_maven_dependency_tree()
            if deps:
                tree.all_dependencies = deps
                if deps:
                    tree.root = deps[0]
                return tree
        except Exception:
            pass

        try:
            deps = self._resolve_from_effective_pom()
            if deps:
                tree.all_dependencies = deps
                if deps:
                    tree.root = deps[0]
                return tree
        except Exception:
            pass

        from .maven_parser import MavenParser
        parser = MavenParser(self.project_path)
        deps = parser.parse()
        tree.all_dependencies = deps
        if deps:
            tree.root = deps[0]

        return tree

    def _resolve_with_maven_dependency_tree(self) -> List[Dependency]:
        """使用 maven dependency:tree 解析依赖树"""
        try:
            result = subprocess.run(
                ["mvn", "dependency:tree", "-DoutputType=json", "-q"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=self.project_path,
            )
            if result.returncode == 0:
                return self._parse_maven_tree_json(result.stdout)
        except Exception:
            pass

        try:
            result = subprocess.run(
                ["mvn", "dependency:tree", "-Dverbose", "-q"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=self.project_path,
            )
            if result.returncode == 0:
                return self._parse_maven_tree_text(result.stdout)
        except Exception:
            pass

        return []

    def _parse_maven_tree_json(self, output: str) -> List[Dependency]:
        """解析 Maven JSON 格式的依赖树"""
        try:
            data = json.loads(output)
            dependencies: List[Dependency] = []

            def parse_node(node: Dict[str, Any], parent: Optional[Dependency] = None, depth: int = 0) -> Dependency:
                group_id = node.get("groupId", "")
                artifact_id = node.get("artifactId", "")
                version = node.get("version", "")

                dep = Dependency(
                    name=artifact_id,
                    version=version,
                    package_manager=PackageManager.MAVEN,
                    group_id=group_id,
                    parent=parent,
                    depth=depth,
                    is_transitive=depth > 0,
                )
                dependencies.append(dep)

                for child in node.get("dependencies", []):
                    child_dep = parse_node(child, dep, depth + 1)
                    if child_dep not in dep.children:
                        dep.children.append(child_dep)

                return dep

            if "dependencyTree" in data:
                parse_node(data["dependencyTree"])
            elif "nodes" in data:
                for node in data["nodes"]:
                    parse_node(node)

            return dependencies

        except Exception:
            return []

    def _parse_maven_tree_text(self, output: str) -> List[Dependency]:
        """解析 Maven 文本格式的依赖树"""
        dependencies: List[Dependency] = []
        stack: List[Tuple[int, Dependency]] = []

        for line in output.split("\n"):
            line = line.strip()
            if not line or "---" in line:
                continue

            depth = 0
            while line.startswith(("+-", "| ", "\\-", "  ")):
                if line.startswith("+-") or line.startswith("\\-"):
                    line = line[2:]
                    depth += 1
                elif line.startswith("| "):
                    line = line[2:]
                    depth += 1
                elif line.startswith("  "):
                    line = line[2:]
                    depth += 1

            parts = line.split(":")
            if len(parts) >= 4:
                group_id = parts[0]
                artifact_id = parts[1]
                version = parts[3] if len(parts) > 3 else ""

                parent = None
                while stack and stack[-1][0] >= depth:
                    stack.pop()
                if stack:
                    parent = stack[-1][1]

                dep = Dependency(
                    name=artifact_id,
                    version=version,
                    package_manager=PackageManager.MAVEN,
                    group_id=group_id,
                    parent=parent,
                    depth=depth,
                    is_transitive=depth > 0,
                )
                dependencies.append(dep)
                stack.append((depth, dep))

                if parent:
                    parent.children.append(dep)

        return dependencies

    def _resolve_from_effective_pom(self) -> List[Dependency]:
        """从 effective pom 解析依赖"""
        try:
            result = subprocess.run(
                ["mvn", "help:effective-pom", "-q"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=self.project_path,
            )
            if result.returncode == 0:
                from .maven_parser import MavenParser
                parser = MavenParser(self.project_path)
                temp_file = os.path.join(self.project_path, ".effective_pom.xml")
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(result.stdout)
                deps = parser._parse_pom_xml(temp_file)
                os.remove(temp_file)
                return deps
        except Exception:
            pass

        return []


class GoDependencyTreeResolver(DependencyTreeResolver):
    """Go 模块依赖树解析器"""

    def resolve(self, include_transitive: bool = True) -> DependencyTree:
        tree = DependencyTree()

        try:
            deps = self._resolve_with_go_mod_graph()
            if deps:
                tree.all_dependencies = deps
                if deps:
                    tree.root = deps[0]
                return tree
        except Exception:
            pass

        try:
            deps = self._resolve_with_go_list()
            if deps:
                tree.all_dependencies = deps
                if deps:
                    tree.root = deps[0]
                return tree
        except Exception:
            pass

        from .go_parser import GoParser
        parser = GoParser(self.project_path)
        deps = parser.parse()
        tree.all_dependencies = deps
        if deps:
            tree.root = deps[0]

        return tree

    def _resolve_with_go_mod_graph(self) -> List[Dependency]:
        """使用 go mod graph 解析依赖树"""
        try:
            result = subprocess.run(
                ["go", "mod", "graph"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.project_path,
            )
            if result.returncode == 0:
                return self._parse_go_mod_graph(result.stdout)
        except Exception:
            pass

        return []

    def _parse_go_mod_graph(self, output: str) -> List[Dependency]:
        """解析 go mod graph 输出"""
        dependencies: List[Dependency] = []
        dep_map: Dict[str, Dependency] = {}
        edges: List[Tuple[str, str]] = []

        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue

            parts = line.split(" ")
            if len(parts) == 2:
                parent = parts[0]
                child = parts[1]
                edges.append((parent, child))

        def get_or_create_dep(spec: str, parent: Optional[Dependency] = None, depth: int = 0) -> Dependency:
            if "@" in spec:
                name, version = spec.split("@", 1)
            else:
                name = spec
                version = ""

            key = f"{name}@${version}"
            if key in dep_map:
                existing = dep_map[key]
                if existing.depth > depth:
                    existing.depth = depth
                    existing.parent = parent
                return existing

            version = version.lstrip("v")
            dep = Dependency(
                name=name,
                version=version,
                package_manager=PackageManager.GO,
                parent=parent,
                depth=depth,
                is_transitive=depth > 0,
            )
            dep_map[key] = dep
            dependencies.append(dep)

            return dep

        root_spec = edges[0][0] if edges else ""
        if root_spec:
            root = get_or_create_dep(root_spec, depth=0)

            processed_parents = set()

            def build_tree(parent_spec: str, parent_dep: Dependency, current_depth: int):
                if parent_spec in processed_parents:
                    return
                processed_parents.add(parent_spec)

                for p_spec, c_spec in edges:
                    if p_spec == parent_spec:
                        child_dep = get_or_create_dep(c_spec, parent_dep, current_depth + 1)
                        if child_dep not in parent_dep.children:
                            parent_dep.children.append(child_dep)
                        build_tree(c_spec, child_dep, current_depth + 1)

            build_tree(root_spec, root, 0)

        return dependencies

    def _resolve_with_go_list(self) -> List[Dependency]:
        """使用 go list 解析依赖"""
        try:
            result = subprocess.run(
                ["go", "list", "-m", "-json", "all"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.project_path,
            )
            if result.returncode == 0:
                return self._parse_go_list_json(result.stdout)
        except Exception:
            pass

        return []

    def _parse_go_list_json(self, output: str) -> List[Dependency]:
        """解析 go list JSON 输出"""
        dependencies: List[Dependency] = []
        decoder = json.JSONDecoder()
        idx = 0

        while idx < len(output):
            try:
                data, idx = decoder.raw_decode(output, idx)
                if isinstance(data, dict):
                    name = data.get("Path", "")
                    version = data.get("Version", "")
                    if name and version:
                        version = version.lstrip("v")
                        dep = Dependency(
                            name=name,
                            version=version,
                            package_manager=PackageManager.GO,
                            is_transitive=True,
                        )
                        dependencies.append(dep)
            except json.JSONDecodeError:
                idx += 1

        if dependencies:
            dependencies[0].is_transitive = False
            dependencies[0].depth = 0

        return dependencies


class DependencyTreeResolverFactory:
    """依赖树解析器工厂"""

    @staticmethod
    def get_resolver(package_manager: PackageManager, project_path: str) -> DependencyTreeResolver:
        """获取对应包管理器的依赖树解析器"""
        resolvers = {
            PackageManager.PIP: PipDependencyTreeResolver,
            PackageManager.NPM: NpmDependencyTreeResolver,
            PackageManager.MAVEN: MavenDependencyTreeResolver,
            PackageManager.GO: GoDependencyTreeResolver,
        }
        resolver_class = resolvers.get(package_manager)
        if resolver_class:
            return resolver_class(project_path)
        raise ValueError(f"Unsupported package manager: {package_manager}")

    @staticmethod
    def detect_and_resolve(project_path: str, include_transitive: bool = True) -> DependencyTree:
        """自动检测项目类型并解析依赖树"""
        from .parser_factory import ParserFactory
        parser = ParserFactory.detect_parser(project_path)
        if not parser:
            raise ValueError(f"Could not detect project type in {project_path}")

        resolver = DependencyTreeResolverFactory.get_resolver(
            parser.package_manager, project_path
        )
        return resolver.resolve(include_transitive=include_transitive)
