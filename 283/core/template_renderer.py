import os
import re
import shlex
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from typing import Dict, Any, Optional, Union
from config import TEMPLATES_DIR


def shell_escape(value: Any) -> str:
    if value is None:
        return ''
    str_value = str(value)
    return shlex.quote(str_value)


def shell_escape_path(path: str) -> str:
    if not path:
        return ''
    return "'" + path.replace("'", "'\\''") + "'"


def sanitize_filename(filename: str) -> str:
    if not filename:
        return ''
    filename = str(filename)
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.replace('\0', '')
    filename = filename.strip('. ')
    if not filename:
        filename = 'unnamed'
    return filename[:255]


def escape_double_quotes(value: str) -> str:
    if value is None:
        return ''
    return str(value).replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')


def escape_single_quotes(value: str) -> str:
    if value is None:
        return ''
    return str(value).replace("'", "'\\''")


class SecurityFilter:
    @staticmethod
    def shell_escape(value: Any) -> str:
        return shell_escape(value)

    @staticmethod
    def shell_escape_path(value: str) -> str:
        return shell_escape_path(value)

    @staticmethod
    def sanitize_filename(value: str) -> str:
        return sanitize_filename(value)

    @staticmethod
    def escape_double_quotes(value: str) -> str:
        return escape_double_quotes(value)

    @staticmethod
    def escape_single_quotes(value: str) -> str:
        return escape_single_quotes(value)

    @staticmethod
    def sanitize_command(cmd: str) -> str:
        dangerous_patterns = [
            r'`',
            r'\$\(',
            r';',
            r'&&',
            r'\|\|',
            r'>>',
            r'>[^>]',
            r'<',
            r'\|',
            r'&',
        ]
        sanitized = cmd
        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, ' ', sanitized)
        return sanitized.strip()


class TemplateRenderer:
    def __init__(self, templates_dir: Optional[str] = None):
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False
        )
        self._register_filters()

    def _register_filters(self):
        self.env.filters['shell_escape'] = shell_escape
        self.env.filters['shell_escape_path'] = shell_escape_path
        self.env.filters['sanitize_filename'] = sanitize_filename
        self.env.filters['escape_double_quotes'] = escape_double_quotes
        self.env.filters['escape_single_quotes'] = escape_single_quotes
        self.env.filters['sanitize_command'] = SecurityFilter.sanitize_command

    def _apply_auto_escape(self, context: Dict[str, Any], auto_escape: bool = True) -> Dict[str, Any]:
        if not auto_escape:
            return context
        
        escaped_context = {}
        for key, value in context.items():
            if isinstance(value, str):
                escaped_context[key] = shell_escape(value)
            elif isinstance(value, dict):
                escaped_context[key] = self._apply_auto_escape(value, auto_escape)
            elif isinstance(value, (list, tuple)):
                escaped_context[key] = [
                    self._apply_auto_escape(item, auto_escape) 
                    if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                escaped_context[key] = value
        return escaped_context

    def render_template(self, template_name: str, context: Dict[str, Any], 
                       auto_shell_escape: bool = False) -> str:
        if auto_shell_escape:
            context = self._apply_auto_escape(context)
        template = self.env.get_template(template_name)
        return template.render(**context)

    def render_string(self, template_str: str, context: Dict[str, Any],
                     auto_shell_escape: bool = False) -> str:
        if auto_shell_escape:
            context = self._apply_auto_escape(context)
        template = self.env.from_string(template_str)
        return template.render(**context)

    def list_templates(self) -> list:
        return self.env.list_templates()

    def get_template_source(self, template_name: str) -> str:
        with open(os.path.join(self.templates_dir, template_name), 'r', encoding='utf-8') as f:
            return f.read()

    def save_rendered(self, template_name: str, context: Dict[str, Any], output_path: str,
                     auto_shell_escape: bool = False):
        content = self.render_template(template_name, context, auto_shell_escape)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return output_path
