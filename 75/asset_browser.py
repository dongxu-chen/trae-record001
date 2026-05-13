import imgui
import os
from typing import List, Optional
from pathlib import Path


class AssetBrowser:
    def __init__(self, root_path: str = None):
        if root_path:
            self.root_path = os.path.abspath(root_path)
        else:
            self.root_path = os.path.dirname(os.path.abspath(__file__))

        self.current_path = self.root_path
        self.history: List[str] = []
        self.history_index = -1
        self.selected_file: Optional[str] = None
        self.view_mode = 0
        self.show_hidden = False

        self.known_extensions = {
            '.png': '纹理',
            '.jpg': '纹理',
            '.jpeg': '纹理',
            '.gif': '纹理',
            '.bmp': '纹理',
            '.tga': '纹理',
            '.obj': '3D 模型',
            '.fbx': '3D 模型',
            '.gltf': '3D 模型',
            '.glb': '3D 模型',
            '.ply': '3D 模型',
            '.wav': '音频',
            '.mp3': '音频',
            '.ogg': '音频',
            '.flac': '音频',
            '.py': '脚本',
            '.lua': '脚本',
            '.json': '数据',
            '.xml': '数据',
            '.yaml': '数据',
            '.yml': '数据',
            '.mat': '材质',
            '.shader': '着色器',
            '.vert': '顶点着色器',
            '.frag': '片段着色器',
            '.scene': '场景',
        }

    def get_icon_name(self, path: str) -> str:
        if os.path.isdir(path):
            return '[D]'
        ext = os.path.splitext(path)[1].lower()
        asset_type = self.known_extensions.get(ext)
        if asset_type == '纹理':
            return '[T]'
        elif asset_type == '3D 模型':
            return '[M]'
        elif asset_type == '音频':
            return '[A]'
        elif asset_type == '脚本':
            return '[S]'
        elif asset_type == '着色器' or ext in ['.vert', '.frag']:
            return '[H]'
        elif ext == '.scene':
            return '[C]'
        elif asset_type == '材质':
            return '[R]'
        else:
            return '[F]'

    def navigate_to(self, path: str):
        path = os.path.abspath(path)
        if not os.path.exists(path) or not os.path.isdir(path):
            return

        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]

        self.history.append(path)
        self.history_index = len(self.history) - 1
        self.current_path = path
        self.selected_file = None

    def go_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.current_path = self.history[self.history_index]
            self.selected_file = None

    def go_forward(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.current_path = self.history[self.history_index]
            self.selected_file = None

    def go_up(self):
        parent = os.path.dirname(self.current_path)
        if os.path.isdir(parent):
            self.navigate_to(parent)

    def get_relative_path(self, path: str) -> str:
        try:
            return os.path.relpath(path, self.root_path)
        except ValueError:
            return path

    def render_navigation_bar(self):
        if imgui.small_button("<"):
            self.go_back()
        imgui.same_line()
        if imgui.small_button(">"):
            self.go_forward()
        imgui.same_line()
        if imgui.small_button("^"):
            self.go_up()
        imgui.same_line()
        if imgui.small_button("R"):
            self.navigate_to(self.root_path)

        imgui.same_line()
        imgui.push_item_width(-1)
        display_path = self.get_relative_path(self.current_path)
        if display_path == '.':
            display_path = 'assets'
        imgui.input_text("##path", display_path, 512, imgui.INPUT_TEXT_READ_ONLY)
        imgui.pop_item_width()

    def render_view_controls(self):
        view_modes = ["列表视图", "网格视图"]
        changed, self.view_mode = imgui.combo("视图模式", self.view_mode, view_modes)
        imgui.same_line()
        changed_hidden, self.show_hidden = imgui.checkbox("显示隐藏", self.show_hidden)

    def render_file_item(self, filename: str, full_path: str):
        is_dir = os.path.isdir(full_path)
        is_selected = self.selected_file == full_path

        icon = self.get_icon_name(full_path)
        display_name = filename

        if self.view_mode == 0:
            flags = imgui.SELECTABLE_SPAN_ALL_COLUMNS
            if is_selected:
                flags |= imgui.SELECTABLE_SELECTED

            clicked, _ = imgui.selectable(f"{icon}  {display_name}", is_selected, flags)

            if imgui.is_item_hovered():
                ext = os.path.splitext(filename)[1].lower()
                file_type = self.known_extensions.get(ext, '文件')
                if is_dir:
                    file_type = '文件夹'

                imgui.begin_tooltip()
                imgui.text(f"类型: {file_type}")
                imgui.text(f"路径: {full_path}")
                try:
                    size = os.path.getsize(full_path)
                    imgui.text(f"大小: {size:,} 字节")
                except:
                    pass
                imgui.end_tooltip()

            if clicked:
                self.selected_file = full_path

            if imgui.is_item_hovered() and imgui.is_mouse_double_clicked(0):
                if is_dir:
                    self.navigate_to(full_path)
        else:
            imgui.button(f"{icon}\n{display_name}", 80, 60)
            if imgui.is_item_hovered():
                if imgui.is_mouse_clicked(0):
                    self.selected_file = full_path
                if imgui.is_mouse_double_clicked(0) and is_dir:
                    self.navigate_to(full_path)

    def render_file_list(self):
        try:
            entries = os.listdir(self.current_path)
        except PermissionError:
            imgui.text("权限不足")
            return
        except Exception as e:
            imgui.text(f"错误: {e}")
            return

        dirs = []
        files = []

        for entry in entries:
            if not self.show_hidden and entry.startswith('.'):
                continue
            full_path = os.path.join(self.current_path, entry)
            if os.path.isdir(full_path):
                dirs.append((entry, full_path))
            else:
                files.append((entry, full_path))

        dirs.sort(key=lambda x: x[0].lower())
        files.sort(key=lambda x: x[0].lower())

        if self.view_mode == 0:
            columns = 2
            imgui.columns(columns, "file_columns", True)
            imgui.set_column_width(0, -1)
            imgui.set_column_width(1, 80)

            imgui.text("名称")
            imgui.next_column()
            imgui.text("类型")
            imgui.next_column()
            imgui.separator()

            for name, path in dirs:
                self.render_file_item(name, path)
                imgui.next_column()
                imgui.text("文件夹")
                imgui.next_column()

            for name, path in files:
                self.render_file_item(name, path)
                imgui.next_column()
                ext = os.path.splitext(name)[1].lower()
                file_type = self.known_extensions.get(ext, '文件')
                imgui.text(file_type)
                imgui.next_column()

            imgui.columns(1)
        else:
            item_spacing_x, item_spacing_y = imgui.get_style().item_spacing
            cell_size = 80 + item_spacing_x
            region_size = imgui.get_content_region_available().x
            column_count = int(max(1, region_size / cell_size))

            imgui.columns(column_count, "grid_columns", False)

            for name, path in dirs:
                self.render_file_item(name, path)
                imgui.next_column()

            for name, path in files:
                self.render_file_item(name, path)
                imgui.next_column()

            imgui.columns(1)

    def render_file_info(self):
        if not self.selected_file:
            return

        imgui.separator()
        imgui.text("选中资源")
        imgui.separator()

        name = os.path.basename(self.selected_file)
        ext = os.path.splitext(name)[1].lower()
        is_dir = os.path.isdir(self.selected_file)

        imgui.text(f"名称: {name}")
        if is_dir:
            imgui.text("类型: 文件夹")
            try:
                children = len(os.listdir(self.selected_file))
                imgui.text(f"包含: {children} 项")
            except:
                pass
        else:
            file_type = self.known_extensions.get(ext, '文件')
            imgui.text(f"类型: {file_type}")
            try:
                size = os.path.getsize(self.selected_file)
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size/1024:.1f} KB"
                else:
                    size_str = f"{size/(1024*1024):.1f} MB"
                imgui.text(f"大小: {size_str}")
            except:
                pass

        imgui.text(f"路径: {self.selected_file}")

    def render(self):
        imgui.begin("资源浏览器")

        self.render_navigation_bar()
        imgui.separator()
        self.render_view_controls()
        imgui.separator()

        if not self.history:
            self.navigate_to(self.current_path)

        imgui.begin_child("file_list_region")
        self.render_file_list()
        imgui.end_child()

        self.render_file_info()

        imgui.end()
