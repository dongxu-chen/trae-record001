import os
import sys
import importlib.util
import importlib.machinery
import imgui
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from console import Console


class EditorPlugin:
    def __init__(self):
        self.name = "Unnamed Plugin"
        self.version = "1.0.0"
        self.author = "Unknown"
        self.description = ""
        self.enabled = True

    def on_load(self, editor: Any) -> None:
        pass

    def on_unload(self, editor: Any) -> None:
        pass

    def on_update(self, editor: Any, delta_time: float) -> None:
        pass

    def on_render(self, editor: Any) -> None:
        pass

    def on_menu(self, editor: Any) -> None:
        pass

    def on_scene_changed(self, editor: Any, entity: Any, reason: str) -> None:
        pass


class PluginManager:
    def __init__(self, editor: Any = None):
        self.editor = editor
        self.plugins: Dict[str, EditorPlugin] = {}
        self.plugin_paths: List[str] = []
        self.plugin_dir = ""

    def set_editor(self, editor: Any):
        self.editor = editor

    def set_plugin_directory(self, directory: str):
        self.plugin_dir = os.path.abspath(directory)
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir, exist_ok=True)

    def register_plugin(self, name: str, plugin: EditorPlugin) -> bool:
        if name in self.plugins:
            Console.warning("PluginManager", f"插件 '{name}' 已存在，将覆盖")

        plugin.name = name
        self.plugins[name] = plugin

        if self.editor:
            try:
                plugin.on_load(self.editor)
                Console.log("PluginManager", f"已加载插件: {name} v{plugin.version}")
                return True
            except Exception as e:
                Console.error("PluginManager", f"加载插件 '{name}' 失败: {e}")
                del self.plugins[name]
                return False

        return True

    def unregister_plugin(self, name: str) -> bool:
        if name in self.plugins:
            plugin = self.plugins[name]
            if self.editor:
                try:
                    plugin.on_unload(self.editor)
                except Exception as e:
                    Console.error("PluginManager", f"卸载插件 '{name}' 时出错: {e}")

            del self.plugins[name]
            Console.log("PluginManager", f"已卸载插件: {name}")
            return True
        return False

    def get_plugin(self, name: str) -> Optional[EditorPlugin]:
        return self.plugins.get(name)

    def get_all_plugins(self) -> List[EditorPlugin]:
        return list(self.plugins.values())

    def is_plugin_enabled(self, name: str) -> bool:
        plugin = self.plugins.get(name)
        return plugin is not None and plugin.enabled

    def set_plugin_enabled(self, name: str, enabled: bool):
        plugin = self.plugins.get(name)
        if plugin:
            plugin.enabled = enabled
            status = "启用" if enabled else "禁用"
            Console.log("PluginManager", f"{status}插件: {name}")

    def load_plugin_from_file(self, file_path: str) -> Optional[EditorPlugin]:
        if not os.path.exists(file_path):
            Console.error("PluginManager", f"插件文件不存在: {file_path}")
            return None

        try:
            module_name = os.path.splitext(os.path.basename(file_path))[0]

            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                Console.error("PluginManager", f"无法加载插件规范: {file_path}")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module

            spec.loader.exec_module(module)

            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, EditorPlugin) and
                    attr != EditorPlugin):
                    plugin_class = attr
                    break

            if plugin_class is None:
                Console.error("PluginManager", f"插件中未找到 EditorPlugin 子类: {file_path}")
                return None

            plugin = plugin_class()
            plugin_name = getattr(module, "PLUGIN_NAME", plugin_class.__name__)

            if self.register_plugin(plugin_name, plugin):
                self.plugin_paths.append(file_path)
                return plugin

            return None

        except Exception as e:
            Console.error("PluginManager", f"加载插件文件 '{file_path}' 失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def load_plugins_from_directory(self, directory: str = "") -> int:
        if directory:
            self.set_plugin_directory(directory)

        if not self.plugin_dir or not os.path.exists(self.plugin_dir):
            Console.warning("PluginManager", "插件目录不存在")
            return 0

        loaded_count = 0

        for file_name in os.listdir(self.plugin_dir):
            if file_name.startswith("_"):
                continue

            file_path = os.path.join(self.plugin_dir, file_name)

            if os.path.isfile(file_path) and file_name.endswith(".py"):
                if self.load_plugin_from_file(file_path):
                    loaded_count += 1
            elif os.path.isdir(file_path):
                init_file = os.path.join(file_path, "__init__.py")
                if os.path.exists(init_file):
                    if self.load_plugin_from_file(init_file):
                        loaded_count += 1

        Console.log("PluginManager", f"从目录加载了 {loaded_count} 个插件")
        return loaded_count

    def update_all(self, delta_time: float):
        for name, plugin in self.plugins.items():
            if plugin.enabled and self.editor:
                try:
                    plugin.on_update(self.editor, delta_time)
                except Exception as e:
                    Console.error("PluginManager", f"插件 '{name}' update 出错: {e}")

    def render_all(self):
        for name, plugin in self.plugins.items():
            if plugin.enabled and self.editor:
                try:
                    plugin.on_render(self.editor)
                except Exception as e:
                    Console.error("PluginManager", f"插件 '{name}' render 出错: {e}")

    def render_menu_all(self):
        for name, plugin in self.plugins.items():
            if plugin.enabled and self.editor:
                try:
                    plugin.on_menu(self.editor)
                except Exception as e:
                    Console.error("PluginManager", f"插件 '{name}' menu 出错: {e}")

    def on_scene_changed_all(self, entity: Any, reason: str):
        for name, plugin in self.plugins.items():
            if plugin.enabled and self.editor:
                try:
                    plugin.on_scene_changed(self.editor, entity, reason)
                except Exception as e:
                    Console.error("PluginManager", f"插件 '{name}' scene_changed 出错: {e}")

    def unload_all(self):
        plugin_names = list(self.plugins.keys())
        for name in plugin_names:
            self.unregister_plugin(name)

    def render(self):
        imgui.begin("插件管理器")

        if imgui.collapsing_header("已加载插件", flags=imgui.TREE_NODE_DEFAULT_OPEN):
            imgui.indent()

            if not self.plugins:
                imgui.text("没有加载任何插件")
            else:
                for name, plugin in self.plugins.items():
                    changed, plugin.enabled = imgui.checkbox(f"##enabled_{name}", plugin.enabled)

                    imgui.same_line()
                    if imgui.collapsing_header(f"{name}", flags=imgui.TREE_NODE_OPEN_ON_DOUBLE_CLICK):
                        imgui.indent()
                        imgui.text(f"版本: {plugin.version}")
                        imgui.text(f"作者: {plugin.author}")
                        if plugin.description:
                            imgui.text_wrapped(f"描述: {plugin.description}")

                        imgui.dummy(0, 5)
                        if imgui.small_button(f"卸载##unload_{name}"):
                            self.unregister_plugin(name)
                            break

                        imgui.unindent()

            imgui.unindent()

        imgui.separator()

        if imgui.collapsing_header("插件目录"):
            imgui.indent()

            if self.plugin_dir:
                imgui.text(f"目录: {self.plugin_dir}")
            else:
                imgui.text("(未设置插件目录)")

            if imgui.small_button("重新扫描"):
                if self.plugin_dir:
                    self.load_plugins_from_directory()

            imgui.unindent()

        imgui.end()
