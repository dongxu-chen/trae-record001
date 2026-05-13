import imgui
from imgui.integrations.glfw import GlfwRenderer
import glfw
import OpenGL.GL as gl
import os
import platform
import time
from scene_hierarchy import SceneHierarchy
from inspector import Inspector
from asset_browser import AssetBrowser
from console import Console
from plugin_manager import PluginManager
from performance_stats import PerformanceStats
from prefab import PrefabManager


class GameEditor:
    def __init__(self):
        self.window = None
        self.impl = None
        self.io = None
        self.width = 1600
        self.height = 900
        self._last_frame_time = 0.0
        self._delta_time = 0.0
        self._frame_count = 0

        self.scene_hierarchy = SceneHierarchy()
        self.inspector = Inspector()
        self.asset_browser = AssetBrowser()
        self.console = Console()
        self.plugin_manager = PluginManager(self)
        self.perf_stats = PerformanceStats(max_samples=120)
        self.prefab_manager = PrefabManager()

        self._dragged_files = []
        self._drop_callback_initialized = False
        self._show_debug_overlay = True

        self.scene_hierarchy.selected_entity_changed = self.on_entity_selected
        self.scene_hierarchy.scene_changed = self.on_scene_changed

        self.inspector.set_performance_stats(self.perf_stats)

        Console.log("GameEditor", "初始化游戏引擎编辑器...")

    def on_scene_changed(self, entity, reason: str):
        if entity:
            Console.debug("Scene", f"场景变化 - {entity.name}: {reason}")
        else:
            Console.debug("Scene", f"场景变化: {reason}")
        self.plugin_manager.on_scene_changed_all(entity, reason)

    def init_prefabs(self):
        prefab_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prefabs")
        self.prefab_manager.set_prefab_directory(prefab_dir)
        self.prefab_manager.load_all_prefabs()
        Console.log("GameEditor", f"预制体目录: {prefab_dir}")

    def init_plugins(self):
        plugin_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")
        self.plugin_manager.set_plugin_directory(plugin_dir)
        self.plugin_manager.load_plugins_from_directory()
        Console.log("GameEditor", f"插件目录: {plugin_dir}")

    def _on_drop_callback(self, window, paths):
        try:
            normalized_paths = []
            for p in paths:
                if p:
                    p_abs = os.path.abspath(p)
                    normalized_paths.append(p_abs)
            self._dragged_files = normalized_paths
            Console.log("Drop", f"接收到 {len(normalized_paths)} 个拖拽文件")
            for fp in normalized_paths:
                Console.log("Drop", f"  - {fp}")
        except Exception as e:
            Console.error("Drop", f"处理拖拽文件时出错: {e}")

    def on_entity_selected(self, entity):
        self.inspector.set_selected_entity(entity)
        if entity:
            Console.log("Selection", f"选中实体: {entity.name}")
        else:
            Console.log("Selection", "取消选择")

    def init_glfw(self):
        if not glfw.init():
            raise Exception("无法初始化 GLFW")

        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, gl.GL_TRUE)

        self.window = glfw.create_window(self.width, self.height, "游戏引擎编辑器", None, None)
        if not self.window:
            glfw.terminate()
            raise Exception("无法创建 GLFW 窗口")

        glfw.make_context_current(self.window)
        glfw.swap_interval(1)

    def init_imgui(self):
        imgui.create_context()
        self.io = imgui.get_io()
        self.io.display_size = (self.width, self.height)
        self.io.config_flags |= imgui.CONFIG_DOCKING_ENABLE

        self.impl = GlfwRenderer(self.window)

        self.setup_style()

    def setup_drop_callback(self):
        if self.window and not self._drop_callback_initialized:
            try:
                glfw.set_drop_callback(self.window, self._on_drop_callback)
                self._drop_callback_initialized = True
                Console.log("GameEditor", "文件拖拽功能已启用")
            except Exception as e:
                Console.error("GameEditor", f"无法设置拖拽回调: {e}")

    def setup_style(self):
        style = imgui.get_style()
        style.window_rounding = 0.0
        style.frame_rounding = 4.0
        style.scrollbar_rounding = 6.0
        style.grab_rounding = 4.0

        colors = style.colors
        colors[imgui.COLOR_WINDOW_BACKGROUND] = (0.15, 0.15, 0.15, 1.0)
        colors[imgui.COLOR_MENU_BAR_BACKGROUND] = (0.1, 0.1, 0.1, 1.0)
        colors[imgui.COLOR_FRAME_BACKGROUND] = (0.25, 0.25, 0.25, 1.0)
        colors[imgui.COLOR_FRAME_BACKGROUND_HOVERED] = (0.35, 0.35, 0.35, 1.0)
        colors[imgui.COLOR_FRAME_BACKGROUND_ACTIVE] = (0.45, 0.45, 0.45, 1.0)
        colors[imgui.COLOR_BUTTON] = (0.3, 0.3, 0.3, 1.0)
        colors[imgui.COLOR_BUTTON_HOVERED] = (0.4, 0.4, 0.4, 1.0)
        colors[imgui.COLOR_BUTTON_ACTIVE] = (0.5, 0.5, 0.5, 1.0)
        colors[imgui.COLOR_HEADER] = (0.25, 0.25, 0.25, 1.0)
        colors[imgui.COLOR_HEADER_HOVERED] = (0.35, 0.35, 0.35, 1.0)
        colors[imgui.COLOR_HEADER_ACTIVE] = (0.45, 0.45, 0.45, 1.0)
        colors[imgui.COLOR_DOCKING_PREVIEW_ALPHA] = (0.5, 0.5, 0.5, 0.7)

    def render_menu_bar(self):
        if imgui.begin_menu_bar():
            if imgui.begin_menu("文件"):
                if imgui.menu_item("新建场景", "Ctrl+N")[0]:
                    self.scene_hierarchy.clear_scene()
                    Console.log("File", "创建新场景")
                if imgui.menu_item("打开场景", "Ctrl+O")[0]:
                    Console.log("File", "打开场景")
                if imgui.menu_item("保存场景", "Ctrl+S")[0]:
                    Console.log("File", "保存场景")
                imgui.separator()
                if imgui.menu_item("退出")[0]:
                    glfw.set_window_should_close(self.window, True)
                imgui.end_menu()

            if imgui.begin_menu("编辑"):
                if imgui.menu_item("撤销", "Ctrl+Z")[0]:
                    Console.log("Edit", "撤销操作")
                if imgui.menu_item("重做", "Ctrl+Y")[0]:
                    Console.log("Edit", "重做操作")
                imgui.end_menu()

            if imgui.begin_menu("视图"):
                if imgui.menu_item("场景层级")[0]:
                    pass
                if imgui.menu_item("属性检查器")[0]:
                    pass
                if imgui.menu_item("资源浏览器")[0]:
                    pass
                if imgui.menu_item("控制台")[0]:
                    pass
                imgui.separator()
                if imgui.menu_item("性能统计")[0]:
                    pass
                if imgui.menu_item("插件管理器")[0]:
                    pass
                imgui.end_menu()

            if imgui.begin_menu("插件"):
                plugin_count = len(self.plugin_manager.plugins)
                if plugin_count > 0:
                    for name, plugin in self.plugin_manager.plugins.items():
                        changed, plugin.enabled = imgui.menu_item(
                            name, "", selected=plugin.enabled
                        )
                else:
                    imgui.menu_item("(无已加载插件)", "", enabled=False)
                imgui.separator()
                if imgui.menu_item("重新加载所有插件")[0]:
                    self.plugin_manager.unload_all()
                    self.init_plugins()
                imgui.end_menu()

            if imgui.begin_menu("调试"):
                changed, self._show_debug_overlay = imgui.menu_item(
                    "显示调试信息", "", selected=self._show_debug_overlay
                )
                imgui.separator()
                if imgui.menu_item("记录帧调试信息")[0]:
                    self._frame_count = 0
                    Console.log("Debug", "开始帧调试...")
                if imgui.menu_item("重置性能统计")[0]:
                    self.perf_stats.frame_times.clear()
                    self.perf_stats.render_times.clear()
                    self.perf_stats.update_times.clear()
                    Console.log("Debug", "已重置性能统计")
                imgui.end_menu()

            self.plugin_manager.render_menu_all()

            if imgui.begin_menu("帮助"):
                if imgui.menu_item("关于")[0]:
                    pass
                imgui.end_menu()

            imgui.end_menu_bar()

    def render_dockspace(self):
        dockspace_id = imgui.get_id("DockSpace")
        imgui.dockspace(dockspace_id, imgui.Vec2(0.0, 0.0), imgui.DOCKNODE_PASSTHRU_CENTRAL_NODE)

    def process_dragged_files(self):
        if self._dragged_files:
            files_to_process = list(self._dragged_files)
            self._dragged_files = []
            for file_path in files_to_process:
                if os.path.exists(file_path):
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in ['.scene']:
                        Console.log("Import", f"加载场景: {file_path}")
                    elif ext in ['.png', '.jpg', '.jpeg', '.tga', '.bmp', '.gif']:
                        Console.log("Import", f"导入纹理: {file_path}")
                        from scene_hierarchy import Entity, SpriteRendererComponent
                        name = os.path.basename(file_path)
                        entity = self.scene_hierarchy.create_entity(name)
                        sprite = SpriteRendererComponent()
                        sprite.texture_path = file_path
                        entity.add_component(sprite)
                    elif ext in ['.obj', '.fbx', '.gltf', '.glb', '.ply']:
                        Console.log("Import", f"导入模型: {file_path}")
                        from scene_hierarchy import Entity, MeshRendererComponent
                        name = os.path.basename(file_path)
                        entity = self.scene_hierarchy.create_entity(name)
                        mesh = MeshRendererComponent()
                        mesh.mesh_path = file_path
                        entity.add_component(mesh)
                    elif ext in ['.py', '.lua']:
                        Console.log("Import", f"脚本文件: {file_path}")
                    else:
                        Console.log("Import", f"未知类型文件: {file_path}")

    def render_scene_view(self):
        imgui.begin("场景视图")
        imgui.text("场景预览区域")
        imgui.separator()
        imgui.text(f"鼠标位置: ({self.io.mouse_pos.x:.1f}, {self.io.mouse_pos.y:.1f})")

        if self._dragged_files:
            imgui.separator()
            imgui.text_colored(0.4, 0.8, 1.0, 1.0, f"检测到 {len(self._dragged_files)} 个拖拽文件")
            for fp in self._dragged_files:
                imgui.text(f"  - {os.path.basename(fp)}")

        imgui.end()

    def render_debug_overlay(self):
        if not self._show_debug_overlay:
            return

        fps = self.perf_stats.get_fps()
        frame_time = self.perf_stats.get_avg_frame_time()
        draw_calls = self.perf_stats.get_total_draw_calls()

        if fps >= 55.0:
            color = (0.3, 1.0, 0.3, 1.0)
        elif fps >= 30.0:
            color = (1.0, 0.8, 0.2, 1.0)
        else:
            color = (1.0, 0.3, 0.3, 1.0)

        window_flags = imgui.WINDOW_NO_TITLE_BAR
        window_flags |= imgui.WINDOW_NO_RESIZE
        window_flags |= imgui.WINDOW_NO_MOVE
        window_flags |= imgui.WINDOW_NO_SCROLLBAR
        window_flags |= imgui.WINDOW_NO_SAVED_SETTINGS
        window_flags |= imgui.WINDOW_NO_FOCUS_ON_APPEARING
        window_flags |= imgui.WINDOW_ALWAYS_AUTO_RESIZE

        io = imgui.get_io()
        pos = imgui.Vec2(10.0, 30.0)
        imgui.set_next_window_pos(pos, imgui.ALWAYS, imgui.Vec2(0.0, 0.0))

        imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, imgui.Vec2(8.0, 6.0))
        imgui.push_style_var(imgui.STYLE_WINDOW_ROUNDING, 6.0)
        imgui.push_style_color(imgui.COLOR_WINDOW_BACKGROUND, 0.0, 0.0, 0.0, 0.7)
        imgui.push_style_color(imgui.COLOR_BORDER, 0.4, 0.4, 0.4, 0.5)

        imgui.begin("DebugOverlay", None, window_flags)

        imgui.text_colored(*color, f"FPS: {fps:.1f}")
        imgui.same_line()
        imgui.text(f"| {frame_time:.2f} ms")

        imgui.text(f"绘制调用: {draw_calls}")
        imgui.text(f"帧: {self._frame_count}")
        imgui.text(f"实体: {self.scene_hierarchy.entity_count}")

        imgui.end()
        imgui.pop_style_color(2)
        imgui.pop_style_var(2)

    def render(self):
        self.perf_stats.begin_render()

        imgui.new_frame()

        viewport = imgui.get_main_viewport()
        imgui.set_next_window_viewport(viewport.id)
        imgui.set_next_window_pos(imgui.Vec2(viewport.pos.x, viewport.pos.y))
        imgui.set_next_window_size(imgui.Vec2(viewport.size.x, viewport.size.y))
        imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, imgui.Vec2(0.0, 0.0))
        imgui.push_style_var(imgui.STYLE_WINDOW_BORDERSIZE, 0.0)

        window_flags = imgui.WINDOW_MENU_BAR
        window_flags |= imgui.WINDOW_NO_DOCKING
        window_flags |= imgui.WINDOW_NO_TITLE_BAR
        window_flags |= imgui.WINDOW_NO_COLLAPSE
        window_flags |= imgui.WINDOW_NO_RESIZE
        window_flags |= imgui.WINDOW_NO_MOVE
        window_flags |= imgui.WINDOW_NO_BRING_TO_FRONT_ON_FOCUS
        window_flags |= imgui.WINDOW_NO_NAV_FOCUS

        imgui.begin("DockSpaceDemo", None, window_flags)
        imgui.pop_style_var(2)

        self.render_menu_bar()
        self.render_dockspace()

        self.scene_hierarchy.render()
        self.inspector.render()
        self.asset_browser.render()
        self.console.render()
        self.render_scene_view()
        self.plugin_manager.render()
        self.perf_stats.render()
        self.prefab_manager.render(self.scene_hierarchy)

        imgui.end()

        self.plugin_manager.render_all()

        self.render_debug_overlay()

        imgui.render()
        self.impl.render(imgui.get_draw_data())

        self.perf_stats.end_render()

    def run(self):
        self.init_glfw()
        self.setup_drop_callback()
        self.init_imgui()
        self.init_plugins()
        self.init_prefabs()

        self._last_frame_time = time.perf_counter()

        Console.log("GameEditor", "编辑器启动完成")

        while not glfw.window_should_close(self.window):
            current_time = time.perf_counter()
            self._delta_time = current_time - self._last_frame_time
            self._last_frame_time = current_time
            self._frame_count += 1

            self.perf_stats.begin_frame()
            self.perf_stats.reset_draw_calls()

            glfw.poll_events()
            self.impl.process_inputs()

            self.perf_stats.begin_update()
            self.process_dragged_files()
            self.plugin_manager.update_all(self._delta_time)
            self.perf_stats.end_update()

            gl.glClearColor(0.1, 0.1, 0.1, 1.0)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)

            self.render()

            glfw.swap_buffers(self.window)

            self.perf_stats.end_frame()

        self.shutdown()

    def shutdown(self):
        Console.log("GameEditor", "正在关闭编辑器...")
        self.plugin_manager.unload_all()
        self.impl.shutdown()
        imgui.destroy_context()
        glfw.terminate()
        Console.log("GameEditor", "编辑器已关闭")


if __name__ == "__main__":
    editor = GameEditor()
    editor.run()
