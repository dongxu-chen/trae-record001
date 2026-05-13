import imgui
import json
import os
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from scene_hierarchy import (
    Entity, Component,
    TransformComponent,
    MeshRendererComponent,
    SpriteRendererComponent,
    CameraComponent
)
from console import Console


@dataclass
class PrefabOverride:
    component_name: str
    property_name: str
    original_value: Any
    overridden_value: Any


class PrefabInstanceComponent(Component):
    def __init__(self, prefab_id: str):
        super().__init__("Prefab Instance")
        self.prefab_id = prefab_id
        self.instance_id = str(uuid.uuid4())
        self.overrides: List[PrefabOverride] = []


class Prefab:
    def __init__(self, name: str):
        self.name = name
        self.id = str(uuid.uuid4())
        self.source_entity: Optional[Entity] = None
        self.file_path = ""
        self.version = 1
        self.created_at = ""
        self.modified_at = ""
        self.thumbnail_path = ""

    def set_source_entity(self, entity: Entity):
        self.source_entity = entity

    def get_source_entity(self) -> Optional[Entity]:
        return self.source_entity


class PrefabManager:
    def __init__(self):
        self.prefabs: Dict[str, Prefab] = {}
        self.prefab_dir = ""
        self._entity_class_map = {
            "TransformComponent": TransformComponent,
            "MeshRendererComponent": MeshRendererComponent,
            "SpriteRendererComponent": SpriteRendererComponent,
            "CameraComponent": CameraComponent,
        }
        self._selected_prefab: Optional[Prefab] = None

    def set_prefab_directory(self, directory: str):
        self.prefab_dir = os.path.abspath(directory)
        if not os.path.exists(self.prefab_dir):
            os.makedirs(self.prefab_dir, exist_ok=True)

    def create_prefab_from_entity(self, entity: Entity, name: str) -> Optional[Prefab]:
        prefab = Prefab(name)
        prefab.set_source_entity(entity)
        self.prefabs[prefab.id] = prefab
        Console.log("Prefab", f"创建预制体: {name}")
        return prefab

    def get_prefab(self, prefab_id: str) -> Optional[Prefab]:
        return self.prefabs.get(prefab_id)

    def get_prefab_by_name(self, name: str) -> Optional[Prefab]:
        for prefab in self.prefabs.values():
            if prefab.name == name:
                return prefab
        return None

    def instantiate_prefab(self, prefab_id: str) -> Optional[Entity]:
        prefab = self.get_prefab(prefab_id)
        if not prefab or not prefab.source_entity:
            return None

        instance = self._clone_entity_tree(prefab.source_entity, prefab.id)
        Console.log("Prefab", f"实例化预制体: {prefab.name}")
        return instance

    def _clone_entity_tree(self, source: Entity, prefab_id: str) -> Entity:
        clone = Entity(source.name + " (Instance)")
        clone.components = []

        for comp in source.components:
            cloned_comp = type(comp)()
            for attr, value in comp.__dict__.items():
                if attr != "name" and attr != "_on_changed":
                    if isinstance(value, list):
                        setattr(cloned_comp, attr, list(value))
                    else:
                        setattr(cloned_comp, attr, value)
            clone.components.append(cloned_comp)

        instance_comp = PrefabInstanceComponent(prefab_id)
        clone.components.insert(0, instance_comp)

        for child in source.children:
            cloned_child = self._clone_entity_tree(child, prefab_id)
            clone.add_child(cloned_child)

        return clone

    def save_prefab_to_file(self, prefab_id: str, file_path: str) -> bool:
        prefab = self.get_prefab(prefab_id)
        if not prefab or not prefab.source_entity:
            return False

        try:
            data = self._serialize_prefab(prefab)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            prefab.file_path = file_path
            Console.log("Prefab", f"保存预制体到: {file_path}")
            return True
        except Exception as e:
            Console.error("Prefab", f"保存预制体失败: {e}")
            return False

    def load_prefab_from_file(self, file_path: str) -> Optional[Prefab]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            prefab = self._deserialize_prefab(data)
            if prefab:
                self.prefabs[prefab.id] = prefab
                prefab.file_path = file_path
                Console.log("Prefab", f"加载预制体: {prefab.name}")
            return prefab
        except Exception as e:
            Console.error("Prefab", f"加载预制体失败: {e}")
            return None

    def _serialize_component(self, comp: Component) -> Dict[str, Any]:
        data = {
            "type": type(comp).__name__,
            "properties": {}
        }

        for attr, value in comp.__dict__.items():
            if attr == "name" or attr == "_on_changed":
                continue
            data["properties"][attr] = value

        return data

    def _serialize_entity(self, entity: Entity) -> Dict[str, Any]:
        data = {
            "name": entity.name,
            "active": entity.active,
            "components": [],
            "children": []
        }

        for comp in entity.components:
            if isinstance(comp, PrefabInstanceComponent):
                continue
            data["components"].append(self._serialize_component(comp))

        for child in entity.children:
            data["children"].append(self._serialize_entity(child))

        return data

    def _serialize_prefab(self, prefab: Prefab) -> Dict[str, Any]:
        data = {
            "version": prefab.version,
            "name": prefab.name,
            "id": prefab.id,
            "entity": None,
        }

        if prefab.source_entity:
            data["entity"] = self._serialize_entity(prefab.source_entity)

        return data

    def _deserialize_component(self, comp_data: Dict[str, Any]) -> Optional[Component]:
        type_name = comp_data.get("type")
        if not type_name:
            return None

        comp_class = self._entity_class_map.get(type_name)
        if not comp_class:
            Console.warning("Prefab", f"未知组件类型: {type_name}")
            return None

        comp = comp_class()

        properties = comp_data.get("properties", {})
        for attr, value in properties.items():
            if hasattr(comp, attr):
                setattr(comp, attr, value)

        return comp

    def _deserialize_entity(self, entity_data: Dict[str, Any], prefab_id: str) -> Optional[Entity]:
        name = entity_data.get("name", "Entity")
        entity = Entity(name)
        entity.active = entity_data.get("active", True)
        entity.components = []

        for comp_data in entity_data.get("components", []):
            comp = self._deserialize_component(comp_data)
            if comp:
                entity.components.append(comp)

        for child_data in entity_data.get("children", []):
            child = self._deserialize_entity(child_data, prefab_id)
            if child:
                entity.add_child(child)

        return entity

    def _deserialize_prefab(self, data: Dict[str, Any]) -> Optional[Prefab]:
        name = data.get("name", "Unnamed Prefab")
        prefab = Prefab(name)
        prefab.id = data.get("id", prefab.id)
        prefab.version = data.get("version", 1)

        entity_data = data.get("entity")
        if entity_data:
            entity = self._deserialize_entity(entity_data, prefab.id)
            if entity:
                prefab.set_source_entity(entity)

        return prefab

    def load_all_prefabs(self) -> int:
        if not self.prefab_dir or not os.path.exists(self.prefab_dir):
            return 0

        count = 0
        for file_name in os.listdir(self.prefab_dir):
            if file_name.endswith(".prefab.json") or file_name.endswith(".prefab"):
                file_path = os.path.join(self.prefab_dir, file_name)
                if self.load_prefab_from_file(file_path):
                    count += 1

        Console.log("Prefab", f"加载了 {count} 个预制体")
        return count

    def save_all_prefabs(self) -> int:
        if not self.prefab_dir:
            return 0

        count = 0
        for prefab in self.prefabs.values():
            file_path = os.path.join(self.prefab_dir, f"{prefab.name}.prefab.json")
            if self.save_prefab_to_file(prefab.id, file_path):
                count += 1

        return count

    def get_all_prefabs(self) -> List[Prefab]:
        return list(self.prefabs.values())

    def delete_prefab(self, prefab_id: str) -> bool:
        if prefab_id in self.prefabs:
            prefab = self.prefabs[prefab_id]
            del self.prefabs[prefab_id]
            Console.log("Prefab", f"删除预制体: {prefab.name}")
            return True
        return False

    def render(self, scene_hierarchy: Any = None):
        imgui.begin("预制体管理器")

        if imgui.collapsing_header("预制体列表", flags=imgui.TREE_NODE_DEFAULT_OPEN):
            imgui.indent()

            if self.prefabs:
                for prefab_id, prefab in self.prefabs.items():
                    is_selected = (self._selected_prefab == prefab)

                    if imgui.selectable(f"{prefab.name}##{prefab_id}", is_selected):
                        self._selected_prefab = prefab

                    if imgui.begin_popup_context_item():
                        if imgui.menu_item("实例化")[0]:
                            if scene_hierarchy and prefab.source_entity:
                                instance = self.instantiate_prefab(prefab_id)
                                if instance:
                                    scene_hierarchy.root_entities.append(instance)
                                    instance.set_change_callback(scene_hierarchy._on_entity_changed)
                                    scene_hierarchy.mark_scene_dirty(f"InstantiatePrefab:{prefab.name}")
                        if imgui.menu_item("保存到文件")[0]:
                            if self.prefab_dir:
                                file_path = os.path.join(self.prefab_dir, f"{prefab.name}.prefab.json")
                                self.save_prefab_to_file(prefab_id, file_path)
                        if imgui.menu_item("删除")[0]:
                            self.delete_prefab(prefab_id)
                            self._selected_prefab = None
                            break
                        imgui.end_popup()
            else:
                imgui.text("(没有预制体)")

            imgui.unindent()

        imgui.separator()

        if self._selected_prefab:
            if imgui.collapsing_header("预制体详情", flags=imgui.TREE_NODE_DEFAULT_OPEN):
                imgui.indent()
                imgui.text(f"名称: {self._selected_prefab.name}")
                imgui.text(f"ID: {self._selected_prefab.id}")
                if self._selected_prefab.source_entity:
                    imgui.text(f"源实体: {self._selected_prefab.source_entity.name}")
                    imgui.text(f"组件数: {len(self._selected_prefab.source_entity.components)}")
                    imgui.text(f"子实体: {len(self._selected_prefab.source_entity.children)}")

                imgui.dummy(0, 5)

                if imgui.button("实例化到场景", -1, 0):
                    if scene_hierarchy and self._selected_prefab.source_entity:
                        instance = self.instantiate_prefab(self._selected_prefab.id)
                        if instance:
                            scene_hierarchy.root_entities.append(instance)
                            instance.set_change_callback(scene_hierarchy._on_entity_changed)
                            scene_hierarchy.mark_scene_dirty(f"InstantiatePrefab:{self._selected_prefab.name}")

                imgui.unindent()

        imgui.separator()

        if imgui.collapsing_header("从选中实体创建预制体"):
            imgui.indent()

            if scene_hierarchy and scene_hierarchy.selected_entity:
                selected = scene_hierarchy.selected_entity
                imgui.text(f"选中实体: {selected.name}")

                name_input = f"NewPrefab"
                changed, new_name = imgui.input_text("名称", name_input, 128)

                if imgui.button("创建预制体", -1, 0):
                    prefab = self.create_prefab_from_entity(selected, "NewPrefab")
                    if self.prefab_dir:
                        file_path = os.path.join(self.prefab_dir, f"{prefab.name}.prefab.json")
                        self.save_prefab_to_file(prefab.id, file_path)

            else:
                imgui.text("(请在场景层级中选中一个实体)")

            imgui.unindent()

        imgui.separator()

        if imgui.collapsing_header("预制体目录"):
            imgui.indent()

            if self.prefab_dir:
                imgui.text(f"目录: {self.prefab_dir}")
            else:
                imgui.text("(未设置预制体目录)")

            if imgui.small_button("重新扫描"):
                self.load_all_prefabs()

            imgui.unindent()

        imgui.end()
