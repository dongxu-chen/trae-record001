extends RefCounted

var items: Dictionary = {}
var hotbar_slots: Array = ["", "", "", ""]
var hotbar_size: int = 4
const MAX_STACK_SIZE: int = 99

signal inventory_changed

func add_item(item_id: String, count: int = 1) -> void:
	if items.has(item_id):
		var new_count: int = items[item_id] + count
		if new_count > MAX_STACK_SIZE:
			items[item_id] = MAX_STACK_SIZE
		else:
			items[item_id] = new_count
	else:
		if count > MAX_STACK_SIZE:
			items[item_id] = MAX_STACK_SIZE
		else:
			items[item_id] = count
		for i in range(hotbar_size):
			if hotbar_slots[i] == "":
				hotbar_slots[i] = item_id
				break
	inventory_changed.emit()

func remove_item(item_id: String, count: int = 1) -> bool:
	if not items.has(item_id) or items[item_id] < count:
		return false
	
	items[item_id] -= count
	if items[item_id] <= 0:
		items.erase(item_id)
		for i in range(hotbar_size):
			if hotbar_slots[i] == item_id:
				hotbar_slots[i] = ""
	inventory_changed.emit()
	return true

func get_item_count(item_id: String) -> int:
	if items.has(item_id):
		return items[item_id]
	return 0

func has_item(item_id: String, count: int = 1) -> bool:
	return get_item_count(item_id) >= count

func get_item_at(slot_index: int) -> String:
	if slot_index >= 0 and slot_index < hotbar_size:
		return hotbar_slots[slot_index]
	return ""

func get_hotbar() -> Array:
	return hotbar_slots.duplicate()

func get_all_items() -> Dictionary:
	return items.duplicate()
