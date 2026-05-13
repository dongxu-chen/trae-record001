#!/usr/bin/env python3
"""
Dockerfile 生成器 - 根据模板生成 Dockerfile
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Optional


class DockerfileGenerator:
    """Dockerfile 生成器"""

    def __init__(self, config: Dict):
        """
        初始化生成器

        Args:
            config: 配置字典
        """
        self.config = config
        self.templates_dir = Path(config.get("templates_dir", "templates"))

    def _render_template(self, template_str: str, variables: Dict) -> str:
        """
        渲染模板字符串

        Args:
            template_str: 模板字符串
            variables: 变量字典

        Returns:
            渲染后的字符串
        """
        result = template_str
        for key, value in variables.items():
            placeholder = f"{{{{ {key} }}}}"
            result = result.replace(placeholder, str(value))
        return result

    def _load_template(self, template_name: str) -> str:
        """
        加载模板文件

        Args:
            template_name: 模板名称

        Returns:
            模板内容
        """
        template_path = self.templates_dir / template_name
        if template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def _get_default_template(self) -> str:
        """
        获取默认模板

        Returns:
            默认模板内容
        """
        return """# 自动生成的 Dockerfile
# 基础镜像
FROM {{ base_image }} AS base

# 设置工作目录
WORKDIR {{ workdir }}

# 设置环境变量
{{ env_vars }}

# 复制文件
{{ copy_commands }}

# 运行命令
{{ run_commands }}

# 暴露端口
{{ expose_ports }}

# 设置启动命令
{{ cmd }}
"""

    def _get_multi_stage_template(self) -> str:
        """
        获取多阶段构建模板

        Returns:
            多阶段构建模板内容
        """
        return """# 多阶段构建 Dockerfile
{{ stage_definitions }}
"""

    def _generate_stage_content(self, stage_config: Dict, variables: Dict) -> str:
        """
        生成单个阶段的内容

        Args:
            stage_config: 阶段配置
            variables: 变量字典

        Returns:
            阶段内容
        """
        stage_name = stage_config.get("name", "")
        base_image = stage_config.get("base_image", variables.get("base_image", "alpine:latest"))
        workdir = stage_config.get("workdir", variables.get("workdir", "/app"))
        env_vars = stage_config.get("env", {})
        copy_commands = stage_config.get("copy", [])
        run_commands = stage_config.get("run", [])
        expose_ports = stage_config.get("expose", [])
        cmd = stage_config.get("cmd", [])
        entrypoint = stage_config.get("entrypoint", [])
        template_name = stage_config.get("template")

        if template_name:
            template = self._load_template(template_name)
            if not template:
                template = self._get_default_template()
        else:
            template = self._get_default_template()

        stage_vars = {
            "base_image": base_image,
            "workdir": workdir,
            "stage_name": stage_name,
        }
        stage_vars.update(variables)

        env_str = ""
        if env_vars:
            env_lines = [f"ENV {k}={v}" for k, v in env_vars.items()]
            env_str = "\n".join(env_lines)

        copy_str = ""
        if copy_commands:
            copy_lines = []
            for copy_cmd in copy_commands:
                if isinstance(copy_cmd, dict):
                    src = copy_cmd.get("src", "")
                    dest = copy_cmd.get("dest", "")
                    from_stage = copy_cmd.get("from")
                    if from_stage:
                        copy_lines.append(f"COPY --from={from_stage} {src} {dest}")
                    else:
                        copy_lines.append(f"COPY {src} {dest}")
                else:
                    copy_lines.append(f"COPY {copy_cmd}")
            copy_str = "\n".join(copy_lines)

        run_str = ""
        if run_commands:
            run_lines = [f"RUN {cmd}" for cmd in run_commands]
            run_str = "\n".join(run_lines)

        expose_str = ""
        if expose_ports:
            ports_str = " ".join(map(str, expose_ports))
            expose_str = f"EXPOSE {ports_str}"

        cmd_str = ""
        if cmd:
            if isinstance(cmd, list):
                cmd_str = f"CMD [{', '.join(f'\"{c}\"' for c in cmd)}]"
            else:
                cmd_str = f"CMD {cmd}"

        entrypoint_str = ""
        if entrypoint:
            if isinstance(entrypoint, list):
                entrypoint_str = f"ENTRYPOINT [{', '.join(f'\"{e}\"' for e in entrypoint)}]"
            else:
                entrypoint_str = f"ENTRYPOINT {entrypoint}"

        stage_vars.update({
            "env_vars": env_str,
            "copy_commands": copy_str,
            "run_commands": run_str,
            "expose_ports": expose_str,
            "cmd": cmd_str,
            "entrypoint": entrypoint_str,
        })

        stage_content = self._render_template(template, stage_vars)

        if stage_name:
            from_pattern = re.compile(
                r'^\s*FROM\s+(?P<image>[^\s]+)(?:\s+AS\s+(?P<old_name>[^\s]+))?\s*$',
                re.IGNORECASE | re.MULTILINE
            )

            match = from_pattern.search(stage_content)
            if match:
                new_from_line = f"FROM {base_image} AS {stage_name}"
                stage_content = stage_content[:match.start()] + new_from_line + stage_content[match.end():]
            else:
                new_from_line = f"FROM {base_image} AS {stage_name}\n\n"
                stage_content = new_from_line + stage_content

        return stage_content

    def generate(self, output_path: str = "Dockerfile", stage: str = "all") -> str:
        """
        生成 Dockerfile

        Args:
            output_path: 输出路径
            stage: 生成的阶段，'all' 表示生成完整的多阶段 Dockerfile

        Returns:
            生成的 Dockerfile 内容
        """
        variables = self.config.get("variables", {})
        stages = self.config.get("stages", [])

        if not stages or stage == "all":
            if stages:
                stage_contents = []
                for stage_config in stages:
                    stage_content = self._generate_stage_content(stage_config, variables)
                    stage_contents.append(stage_content)
                dockerfile_content = "\n\n".join(stage_contents)
            else:
                default_stage = {
                    "base_image": self.config.get("base_image", "alpine:latest"),
                    "workdir": self.config.get("workdir", "/app"),
                    "env": self.config.get("env", {}),
                    "copy": self.config.get("copy", []),
                    "run": self.config.get("run", []),
                    "expose": self.config.get("expose", []),
                    "cmd": self.config.get("cmd", []),
                    "entrypoint": self.config.get("entrypoint", []),
                    "template": self.config.get("template"),
                }
                dockerfile_content = self._generate_stage_content(default_stage, variables)
        else:
            stage_config = None
            for s in stages:
                if s.get("name") == stage:
                    stage_config = s
                    break

            if not stage_config:
                raise ValueError(f"未找到阶段: {stage}")

            dockerfile_content = self._generate_stage_content(stage_config, variables)

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, "w", encoding="utf-8") as f:
            f.write(dockerfile_content)

        print(f"Dockerfile 已生成: {output_path}")
        return dockerfile_content
