import imgui
from typing import Optional
from scene_hierarchy import (
    Entity, Component,
    TransformComponent,
    MeshRendererComponent,
    SpriteRendererComponent,
    CameraComponent
)


class Inspector:
    def __init__(self):
        self.selected_entity: Optional[Entity] = None
        self.entity_name_buffer = ""
        self._perf_stats = None

    def set_performance_stats(self, perf_stats):
        self._perf_stats = perf_stats

    def _record_draw_call(self, call_type: str, count: int = 1):
        if self._perf_stats:
            self._perf_stats.record_draw_call(call_type, count)

    def set_selected_entity(self, entity: Optional[Entity]):
        self.selected_entity = entity
        if entity:
            self.entity_name_buffer = entity.name

    def _render_entity_header(self):
        if not self.selected_entity:
            return

        imgui.align_text_to_frame_padding()
        imgui.text("名称:")
        imgui.same_line()

        changed, new_name = imgui.input_text(
            "##entity_name",
            self.entity_name_buffer,
            256,
            imgui.INPUT_TEXT_ENTER_RETURNS_TRUE
        )

        if changed:
            self.entity_name_buffer = new_name
            old_name = self.selected_entity.name
            self.selected_entity.name = new_name
            self.selected_entity.mark_dirty(f"Rename:{old_name}->{new_name}")
            self._record_draw_call("shader_switches")

        imgui.same_line()
        changed_active, new_active = imgui.checkbox("激活", self.selected_entity.active)
        if changed_active:
            self.selected_entity.active = new_active
            self.selected_entity.mark_dirty(f"Active:{new_active}")
            self._record_draw_call("shader_switches")

        imgui.separator()

    def _render_vec3(self, label: str, values: list, speed: float = 0.1) -> bool:
        imgui.push_id(label)
        imgui.align_text_to_frame_padding()
        imgui.text(label)
        imgui.same_line()

        changed = False
        imgui.push_item_width(70)

        imgui.push_style_color(imgui.COLOR_BUTTON, 0.8, 0.1, 0.1, 1.0)
        imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, 0.9, 0.2, 0.2, 1.0)
        imgui.small_button("X")
        imgui.pop_style_color(2)
        imgui.same_line()
        changed_x, values[0] = imgui.drag_float("##x", values[0], speed, format="%.2f")
        imgui.same_line()

        imgui.push_style_color(imgui.COLOR_BUTTON, 0.1, 0.6, 0.1, 1.0)
        imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, 0.2, 0.7, 0.2, 1.0)
        imgui.small_button("Y")
        imgui.pop_style_color(2)
        imgui.same_line()
        changed_y, values[1] = imgui.drag_float("##y", values[1], speed, format="%.2f")
        imgui.same_line()

        imgui.push_style_color(imgui.COLOR_BUTTON, 0.1, 0.1, 0.8, 1.0)
        imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, 0.2, 0.2, 0.9, 1.0)
        imgui.small_button("Z")
        imgui.pop_style_color(2)
        imgui.same_line()
        changed_z, values[2] = imgui.drag_float("##z", values[2], speed, format="%.2f")

        imgui.pop_item_width()
        imgui.pop_id()

        return changed_x or changed_y or changed_z

    def _render_transform(self, comp: TransformComponent):
        if imgui.collapsing_header("Transform", flags=imgui.TREE_NODE_DEFAULT_OPEN):
            imgui.indent()
            changed_pos = self._render_vec3("位置", comp.position)
            changed_rot = self._render_vec3("旋转", comp.rotation, speed=1.0)
            changed_scale = self._render_vec3("缩放", comp.scale, speed=0.05)
            if changed_pos:
                comp.mark_changed("position")
                self._record_draw_call("vao_binds", 2)
            if changed_rot:
                comp.mark_changed("rotation")
                self._record_draw_call("vao_binds")
            if changed_scale:
                comp.mark_changed("scale")
                self._record_draw_call("vao_binds")
            imgui.unindent()

    def _render_mesh_renderer(self, comp: MeshRendererComponent):
        if imgui.collapsing_header("Mesh Renderer", flags=imgui.TREE_NODE_DEFAULT_OPEN):
            imgui.indent()
            imgui.text("网格:")
            imgui.same_line()
            imgui.push_item_width(-1)
            changed_mesh, new_mesh = imgui.input_text("##mesh", comp.mesh_path, 256)
            if changed_mesh:
                comp.mesh_path = new_mesh
                comp.mark_changed("mesh_path")
                self._record_draw_call("triangles", 36)
                self._record_draw_call("vao_binds")
            imgui.pop_item_width()

            imgui.text("材质:")
            imgui.same_line()
            imgui.push_item_width(-1)
            changed_mat, new_mat = imgui.input_text("##mat", comp.material_path, 256)
            if changed_mat:
                comp.material_path = new_mat
                comp.mark_changed("material_path")
                self._record_draw_call("shader_switches")
            imgui.pop_item_width()
            imgui.unindent()

    def _render_sprite_renderer(self, comp: SpriteRendererComponent):
        if imgui.collapsing_header("Sprite Renderer", flags=imgui.TREE_NODE_DEFAULT_OPEN):
            imgui.indent()
            imgui.text("纹理:")
            imgui.same_line()
            imgui.push_item_width(-1)
            changed_tex, new_tex = imgui.input_text("##tex", comp.texture_path, 256)
            if changed_tex:
                comp.texture_path = new_tex
                comp.mark_changed("texture_path")
                self._record_draw_call("textures_bound")
            imgui.pop_item_width()

            imgui.text("颜色:")
            imgui.same_line()
            changed_color, *new_color = imgui.color_edit4("##color", *comp.color)
            if changed_color:
                comp.color = list(new_color)
                comp.mark_changed("color")
                self._record_draw_call("shader_switches")
            imgui.unindent()

    def _render_camera(self, comp: CameraComponent):
        if imgui.collapsing_header("Camera", flags=imgui.TREE_NODE_DEFAULT_OPEN):
            imgui.indent()

            changed_proj, new_ortho = imgui.checkbox("正交投影", comp.orthographic)
            if changed_proj:
                comp.orthographic = new_ortho
                comp.mark_changed("orthographic")
                self._record_draw_call("shader_switches")

            if comp.orthographic:
                changed_size, new_size = imgui.drag_float("大小", 5.0, 0.1, 0.1, 100.0)
                if changed_size:
                    comp.mark_changed("ortho_size")
                    self._record_draw_call("shader_switches")
            else:
                changed_fov, new_fov = imgui.slider_float(
                    "视场角", comp.fov, 1.0, 179.0, "%.1f"
                )
                if changed_fov:
                    comp.fov = new_fov
                    comp.mark_changed("fov")
                    self._record_draw_call("shader_switches")

            changed_near, new_near = imgui.drag_float(
                "近裁剪面", comp.near_clip, 0.01, 0.001, 10.0
            )
            if changed_near:
                comp.near_clip = new_near
                comp.mark_changed("near_clip")
                self._record_draw_call("shader_switches")

            changed_far, new_far = imgui.drag_float(
                "远裁剪面", comp.far_clip, 10.0, 1.0, 10000.0
            )
            if changed_far:
                comp.far_clip = new_far
                comp.mark_changed("far_clip")
                self._record_draw_call("shader_switches")

            imgui.unindent()

    def _render_component(self, component: Component):
        component_type = type(component)

        if component_type == TransformComponent:
            self._render_transform(component)
        elif component_type == MeshRendererComponent:
            self._render_mesh_renderer(component)
        elif component_type == SpriteRendererComponent:
            self._render_sprite_renderer(component)
        elif component_type == CameraComponent:
            self._render_camera(component)
        else:
            if imgui.collapsing_header(component.name):
                imgui.indent()
                imgui.text("(无编辑属性)")
                imgui.unindent()

    def _render_add_component_button(self):
        if imgui.button("添加组件", -1, 0):
            imgui.open_popup("add_component_popup")

        if imgui.begin_popup("add_component_popup"):
            if imgui.menu_item("Mesh Renderer")[0]:
                if self.selected_entity and not self.selected_entity.has_component(MeshRendererComponent):
                    self.selected_entity.add_component(MeshRendererComponent())
            if imgui.menu_item("Sprite Renderer")[0]:
                if self.selected_entity and not self.selected_entity.has_component(SpriteRendererComponent):
                    self.selected_entity.add_component(SpriteRendererComponent())
            if imgui.menu_item("Camera")[0]:
                if self.selected_entity and not self.selected_entity.has_component(CameraComponent):
                    self.selected_entity.add_component(CameraComponent())
            imgui.end_popup()

    def _render_draw_stats(self):
        if not self._perf_stats:
            return

        imgui.separator()
        imgui.text("绘制统计")
        imgui.separator()

        draw_calls = self._perf_stats.draw_calls
        total = sum(draw_calls.values())

        imgui.indent()
        imgui.text(f"总绘制调用: {total}")
        imgui.text(f"三角形: {draw_calls['triangles']}")
        imgui.text(f"线条: {draw_calls['lines']}")
        imgui.text(f"点: {draw_calls['points']}")
        imgui.text(f"纹理绑定: {draw_calls['textures_bound']}")
        imgui.text(f"Shader 切换: {draw_calls['shader_switches']}")
        imgui.text(f"VAO 绑定: {draw_calls['vao_binds']}")
        imgui.unindent()

    def render(self):
        imgui.begin("属性检查器")

        if not self.selected_entity:
            imgui.text("没有选中任何实体")
            imgui.text("请在场景层级中选择一个实体")
            self._render_draw_stats()
            imgui.end()
            return

        self._render_entity_header()

        for component in self.selected_entity.components:
            self._render_component(component)

        imgui.dummy(0, 10)
        self._render_add_component_button()

        imgui.dummy(0, 10)
        imgui.separator()
        imgui.text("信息")
        imgui.separator()
        imgui.text(f"ID: {self.selected_entity.id}")
        imgui.text(f"子实体: {len(self.selected_entity.children)}")
        if self.selected_entity.parent:
            imgui.text(f"父实体: {self.selected_entity.parent.name}")
        else:
            imgui.text("父实体: 无")

        self._render_draw_stats()

        imgui.end()
