import imgui
from typing import List, Optional, Callable, Any


class Component:
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
        self._on_changed: Optional[Callable[[str], None]] = None

    def get_type_name(self) -> str:
        return self.__class__.__name__

    def set_change_callback(self, callback: Optional[Callable[[str], None]]):
        self._on_changed = callback

    def mark_changed(self, property_name: str = ""):
        if self._on_changed:
            self._on_changed(property_name)


class TransformComponent(Component):
    def __init__(self):
        super().__init__("Transform")
        self.position = [0.0, 0.0, 0.0]
        self.rotation = [0.0, 0.0, 0.0]
        self.scale = [1.0, 1.0, 1.0]


class MeshRendererComponent(Component):
    def __init__(self):
        super().__init__("Mesh Renderer")
        self.mesh_path = ""
        self.material_path = ""


class SpriteRendererComponent(Component):
    def __init__(self):
        super().__init__("Sprite Renderer")
        self.texture_path = ""
        self.color = [1.0, 1.0, 1.0, 1.0]


class CameraComponent(Component):
    def __init__(self):
        super().__init__("Camera")
        self.orthographic = False
        self.fov = 60.0
        self.near_clip = 0.1
        self.far_clip = 1000.0


class Entity:
    def __init__(self, name: str = "Entity"):
        self.name = name
        self.id = id(self)
        self.active = True
        self.components: List[Component] = []
        self.children: List[Entity] = []
        self.parent: Optional[Entity] = None
        self.expanded = True
        self._dirty = False
        self._on_changed: Optional[Callable[[Any, str], None]] = None

        self.add_component(TransformComponent())

    def set_change_callback(self, callback: Optional[Callable[[Any, str], None]]):
        self._on_changed = callback

    def mark_dirty(self, reason: str = ""):
        self._dirty = True
        if self._on_changed:
            self._on_changed(self, reason)

    def add_component(self, component: Component) -> Component:
        self.components.append(component)
        component.set_change_callback(
            lambda prop: self.mark_dirty(f"Component {component.get_type_name()}.{prop}")
        )
        self.mark_dirty(f"AddComponent:{component.get_type_name()}")
        return component

    def remove_component(self, component: Component) -> None:
        if component in self.components:
            self.components.remove(component)
            component.set_change_callback(None)
            self.mark_dirty(f"RemoveComponent:{component.get_type_name()}")

    def get_component(self, component_type: type) -> Optional[Component]:
        for comp in self.components:
            if isinstance(comp, component_type):
                return comp
        return None

    def add_child(self, child: "Entity") -> None:
        if child.parent:
            child.parent.remove_child(child)
        child.parent = self
        self.children.append(child)
        self.mark_dirty(f"AddChild:{child.name}")

    def remove_child(self, child: "Entity") -> None:
        if child in self.children:
            self.children.remove(child)
            child.parent = None
            self.mark_dirty(f"RemoveChild:{child.name}")

    def has_component(self, component_type: type) -> bool:
        return self.get_component(component_type) is not None


class SceneHierarchy:
    def __init__(self):
        self.root_entities: List[Entity] = []
        self.selected_entity: Optional[Entity] = None
        self.entity_count = 0
        self.selected_entity_changed: Optional[Callable[[Optional[Entity]], None]] = None
        self.scene_changed: Optional[Callable[[Any, str], None]] = None
        self._scene_dirty = False

        self._init_default_scene()

    def _on_entity_changed(self, entity: Any, reason: str):
        self._scene_dirty = True
        if self.scene_changed:
            self.scene_changed(entity, reason)

    def _init_default_scene(self):
        main_camera = Entity("Main Camera")
        main_camera.set_change_callback(self._on_entity_changed)
        main_camera.add_component(CameraComponent())
        self.root_entities.append(main_camera)

        cube = Entity("Cube")
        cube.set_change_callback(self._on_entity_changed)
        cube.add_component(MeshRendererComponent())
        self.root_entities.append(cube)

        light = Entity("Directional Light")
        light.set_change_callback(self._on_entity_changed)
        self.root_entities.append(light)

        player = Entity("Player")
        player.set_change_callback(self._on_entity_changed)
        self.root_entities.append(player)

        player_head = Entity("Head")
        player_head.set_change_callback(self._on_entity_changed)
        player.add_child(player_head)

        player_body = Entity("Body")
        player_body.set_change_callback(self._on_entity_changed)
        player.add_child(player_body)

        self.entity_count = 5

    def mark_scene_dirty(self, reason: str = ""):
        self._scene_dirty = True
        if self.scene_changed:
            self.scene_changed(None, reason)

    def is_scene_dirty(self) -> bool:
        return self._scene_dirty

    def clear_scene_dirty(self):
        self._scene_dirty = False

    def clear_scene(self):
        self.root_entities = []
        self.selected_entity = None
        self.entity_count = 0
        if self.selected_entity_changed:
            self.selected_entity_changed(None)

    def create_entity(self, name: str = "Entity") -> Entity:
        self.entity_count += 1
        if name == "Entity":
            name = f"Entity {self.entity_count}"
        entity = Entity(name)
        entity.set_change_callback(self._on_entity_changed)
        self.root_entities.append(entity)
        self.mark_scene_dirty(f"CreateEntity:{name}")
        return entity

    def delete_entity(self, entity: Entity):
        def recursive_delete(target: Entity, container: List[Entity]) -> bool:
            for e in container:
                if e == target:
                    container.remove(e)
                    return True
                if recursive_delete(target, e.children):
                    return True
            return False

        entity_name = entity.name

        if self.selected_entity == entity:
            self.selected_entity = None
            if self.selected_entity_changed:
                self.selected_entity_changed(None)

        recursive_delete(entity, self.root_entities)
        self.mark_scene_dirty(f"DeleteEntity:{entity_name}")

    def duplicate_entity(self, entity: Entity) -> Entity:
        new_entity = Entity(entity.name + " (Copy)")
        new_entity.set_change_callback(self._on_entity_changed)
        new_entity.components = []
        for comp in entity.components:
            new_comp = type(comp)()
            for attr, value in comp.__dict__.items():
                if attr != "name" and attr != "_on_changed":
                    if isinstance(value, list):
                        setattr(new_comp, attr, list(value))
                    else:
                        setattr(new_comp, attr, value)
            new_entity.components.append(new_comp)
            new_comp.set_change_callback(
                lambda prop, ne=new_entity, tc=type(new_comp): 
                    ne.mark_dirty(f"Component {tc.__name__}.{prop}")
            )

        def copy_children(src: Entity, dst: Entity):
            for child in src.children:
                new_child = Entity(child.name)
                new_child.set_change_callback(self._on_entity_changed)
                new_child.components = []
                for comp in child.components:
                    new_comp = type(comp)()
                    for attr, value in comp.__dict__.items():
                        if attr != "name" and attr != "_on_changed":
                            if isinstance(value, list):
                                setattr(new_comp, attr, list(value))
                            else:
                                setattr(new_comp, attr, value)
                    new_child.components.append(new_comp)
                    new_comp.set_change_callback(
                        lambda prop, nc=new_child, tc=type(new_comp): 
                            nc.mark_dirty(f"Component {tc.__name__}.{prop}")
                    )
                dst.add_child(new_child)
                copy_children(child, new_child)

        copy_children(entity, new_entity)

        if entity.parent:
            entity.parent.add_child(new_entity)
        else:
            self.root_entities.append(new_entity)

        self.mark_scene_dirty(f"DuplicateEntity:{new_entity.name}")
        return new_entity

    def _render_entity_tree(self, entity: Entity) -> bool:
        flags = imgui.TREE_NODE_OPEN_ON_ARROW
        flags |= imgui.TREE_NODE_OPEN_ON_DOUBLE_CLICK

        if not entity.children:
            flags |= imgui.TREE_NODE_LEAF

        if self.selected_entity == entity:
            flags |= imgui.TREE_NODE_SELECTED

        is_selected = self.selected_entity == entity

        label = f"{'[X] ' if entity.active else '[ ] '}{entity.name}"
        entity.expanded = imgui.tree_node_ex(str(entity.id), flags, label)

        if imgui.is_item_hovered() and imgui.is_mouse_clicked(0):
            if not is_selected:
                self.selected_entity = entity
                if self.selected_entity_changed:
                    self.selected_entity_changed(entity)

        if imgui.begin_popup_context_item():
            if imgui.menu_item("重命名")[0]:
                pass
            if imgui.menu_item("复制")[0]:
                pass
            if imgui.menu_item("粘贴")[0]:
                pass
            imgui.separator()
            if imgui.menu_item("删除")[0]:
                self.delete_entity(entity)
            if imgui.menu_item("复制实体")[0]:
                self.duplicate_entity(entity)
            imgui.end_popup()

        if entity.expanded:
            for child in entity.children:
                self._render_entity_tree(child)
            imgui.tree_pop()

        return entity.expanded

    def render_toolbar(self):
        if imgui.small_button("+"):
            self.create_entity()

        imgui.same_line()
        if imgui.small_button("-") and self.selected_entity:
            self.delete_entity(self.selected_entity)

        imgui.same_line()
        if imgui.small_button("展开全部"):
            def expand_all(entities):
                for e in entities:
                    e.expanded = True
                    expand_all(e.children)
            expand_all(self.root_entities)

        imgui.same_line()
        if imgui.small_button("折叠全部"):
            def collapse_all(entities):
                for e in entities:
                    e.expanded = False
                    collapse_all(e.children)
            collapse_all(self.root_entities)

    def render(self):
        imgui.begin("场景层级")

        self.render_toolbar()

        imgui.separator()

        if not self.root_entities:
            imgui.text("场景为空")
        else:
            for entity in self.root_entities:
                self._render_entity_tree(entity)

        if imgui.begin_popup_context_window():
            if imgui.menu_item("新建实体")[0]:
                self.create_entity()
            if imgui.begin_menu("新建实体 (预设)"):
                if imgui.menu_item("相机")[0]:
                    cam = self.create_entity("Camera")
                    cam.add_component(CameraComponent())
                if imgui.menu_item("方向光")[0]:
                    self.create_entity("Directional Light")
                if imgui.menu_item("3D 物体")[0]:
                    obj = self.create_entity("GameObject")
                    obj.add_component(MeshRendererComponent())
                if imgui.menu_item("2D 精灵")[0]:
                    spr = self.create_entity("Sprite")
                    spr.add_component(SpriteRendererComponent())
                imgui.end_menu()
            imgui.end_popup()

        imgui.end()
