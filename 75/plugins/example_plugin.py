import imgui
from plugin_manager import EditorPlugin
from console import Console


PLUGIN_NAME = "ExamplePlugin"


class ExamplePlugin(EditorPlugin):
    def __init__(self):
        super().__init__()
        self.name = "示例插件"
        self.version = "1.0.0"
        self.author = "GameEditor Team"
        self.description = "一个演示插件系统功能的示例插件"
        self._show_plugin_window = True
        self._click_count = 0
        self._editor = None

    def on_load(self, editor):
        self._editor = editor
        Console.log("ExamplePlugin", "插件已加载!")

    def on_unload(self, editor):
        Console.log("ExamplePlugin", "插件已卸载")

    def on_update(self, editor, delta_time):
        pass

    def on_render(self, editor):
        if not self._show_plugin_window:
            return

        imgui.begin("示例插件窗口", True)

        imgui.text(f"这是一个示例插件窗口")
        imgui.separator()

        imgui.text(f"点击次数: {self._click_count}")
        if imgui.button("点击我"):
            self._click_count += 1
            Console.log("ExamplePlugin", f"按钮被点击了 {self._click_count} 次")

        imgui.separator()

        if imgui.button("记录日志"):
            Console.log("ExamplePlugin", "这是一条信息日志")
            Console.warning("ExamplePlugin", "这是一条警告日志")
            Console.error("ExamplePlugin", "这是一条错误日志")
            Console.debug("ExamplePlugin", "这是一条调试日志")

        if imgui.button("创建测试实体"):
            if self._editor:
                entity = self._editor.scene_hierarchy.create_entity("插件创建的实体")
                Console.log("ExamplePlugin", f"创建了实体: {entity.name}")

        imgui.end()

    def on_menu(self, editor):
        if imgui.begin_menu("示例插件"):
            if imgui.menu_item("显示窗口", "", selected=self._show_plugin_window):
                self._show_plugin_window = not self._show_plugin_window
            if imgui.menu_item("关于"):
                Console.log("ExamplePlugin", f"示例插件 v{self.version} - 作者: {self.author}")
            imgui.end_menu()

    def on_scene_changed(self, editor, entity, reason):
        if entity:
            Console.debug("ExamplePlugin", f"场景变化: {entity.name} - {reason}")
        else:
            Console.debug("ExamplePlugin", f"场景变化: {reason}")
