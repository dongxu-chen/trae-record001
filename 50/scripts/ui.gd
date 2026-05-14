extends CanvasLayer

var selected_slot: int = 0
var inventory: Inventory = null
var save_game: SaveGame = null

var item_names: Dictionary = {
	"wheat_seed": "小麦种子",
	"tomato_seed": "番茄种子",
	"corn_seed": "玉米种子",
	"sunflower_seed": "向日葵种",
	"pumpkin_seed": "南瓜种子",
	"carrot_seed": "胡萝卜种",
	"wheat": "小麦",
	"tomato": "番茄",
	"corn": "玉米",
	"sunflower_seed": "向日葵",
	"pumpkin": "南瓜",
	"carrot": "胡萝卜",
	"egg": "鸡蛋",
	"milk": "牛奶",
	"watering_can": "浇水壶",
	"hoe": "锄头"
}

var season_icons: Dictionary = {
	0: "🌸",
	1: "☀️",
	2: "🍂",
	3: "❄️"
}

func _ready() -> void:
	var crosshair_line = $Crosshair/Line2D
	crosshair_line.points = [Vector2(0, 10), Vector2(0, -10)]
	crosshair_line.width = 2.0
	
	call_deferred("_connect_save_game")

func _connect_save_game() -> void:
	if get_parent().has_node("SaveGame"):
		save_game = get_parent().get_node("SaveGame")
		update_season_display()

func set_inventory(inv: Inventory) -> void:
	inventory = inv
	update_hotbar()

func select_slot(slot_index: int) -> void:
	for i in range(4):
		var slot = $CenterContainer/Background/HBoxContainer.get_child(i)
		var stylebox = slot.get_theme_stylebox("panel")
		var new_style = stylebox.duplicate()
		if i == slot_index:
			new_style.bg_color = Color(0.3, 0.5, 0.3, 0.8)
			new_style.border_color = Color(0.6, 0.8, 0.6, 1)
			new_style.border_width_left = 3
			new_style.border_width_top = 3
			new_style.border_width_right = 3
			new_style.border_width_bottom = 3
		else:
			new_style.bg_color = Color(0.2, 0.2, 0.25, 0.8)
			new_style.border_color = Color(0.4, 0.4, 0.4, 1)
			new_style.border_width_left = 2
			new_style.border_width_top = 2
			new_style.border_width_right = 2
			new_style.border_width_bottom = 2
		slot.add_theme_stylebox_override("panel", new_style)
	selected_slot = slot_index

func update_hotbar() -> void:
	if not inventory:
		return
	
	var hotbar: Array = inventory.get_hotbar()
	for i in range(4):
		var slot = $CenterContainer/Background/HBoxContainer.get_child(i)
		var vbox = slot.get_child(0)
		var item_label = vbox.get_child(0)
		var count_label = vbox.get_child(1)
		
		var item_id: String = hotbar[i]
		if item_id != "" and inventory.get_item_count(item_id) > 0:
			var display_name: String = item_names.get(item_id, item_id)
			item_label.text = display_name.left(6)
			var count: int = inventory.get_item_count(item_id)
			if count > 1:
				count_label.text = "x" + str(count)
			else:
				count_label.text = ""
		else:
			item_label.text = str(i + 1)
			count_label.text = ""

func update_season_display() -> void:
	if not save_game:
		return
	
	var season_label = $SeasonPanel/VBoxContainer/SeasonLabel
	var day_label = $SeasonPanel/VBoxContainer/DayLabel
	var season_panel = $SeasonPanel
	
	var current_season: int = save_game.get_current_season()
	var day_count: int = save_game.day_count
	var season_name: String = save_game.get_season_name(current_season)
	var season_color: Color = save_game.get_season_color(current_season)
	
	season_label.text = season_icons.get(current_season, "?") + " " + season_name
	day_label.text = "第 " + str(day_count) + " 天"
	
	var stylebox = season_panel.get_theme_stylebox("panel")
	var new_style = stylebox.duplicate()
	new_style.bg_color = Color(season_color.r * 0.3, season_color.g * 0.3, season_color.b * 0.3, 0.85)
	new_style.border_color = season_color
	season_panel.add_theme_stylebox_override("panel", new_style)
