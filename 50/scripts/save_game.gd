extends Node

enum Season {
	SPRING,
	SUMMER,
	AUTUMN,
	WINTER
}

var current_season: Season = Season.SPRING
var day_count: int = 1
var total_days: int = 0

const SAVE_PATH: String = "user://farm_save.json"
const SEASON_LENGTH: int = 30

func get_season_name(season: Season) -> String:
	match season:
		Season.SPRING:
			return "春季"
		Season.SUMMER:
			return "夏季"
		Season.AUTUMN:
			return "秋季"
		Season.WINTER:
			return "冬季"
	return "未知"

func get_season_color(season: Season) -> Color:
	match season:
		Season.SPRING:
			return Color(0.6, 0.9, 0.6, 1)
		Season.SUMMER:
			return Color(1.0, 0.9, 0.5, 1)
		Season.AUTUMN:
			return Color(0.9, 0.7, 0.4, 1)
		Season.WINTER:
			return Color(0.8, 0.9, 1.0, 1)
	return Color.WHITE

func advance_day() -> void:
	day_count += 1
	total_days += 1
	
	if day_count > SEASON_LENGTH:
		day_count = 1
		current_season = (current_season + 1) % 4

func get_current_season() -> Season:
	return current_season

func can_plant_in_season(crop_type: String, season: Season) -> bool:
	var spring_crops: Array = ["wheat", "tomato", "carrot"]
	var summer_crops: Array = ["tomato", "corn", "sunflower"]
	var autumn_crops: Array = ["wheat", "pumpkin", "carrot"]
	var winter_crops: Array = []
	
	match season:
		Season.SPRING:
			return crop_type in spring_crops
		Season.SUMMER:
			return crop_type in summer_crops
		Season.AUTUMN:
			return crop_type in autumn_crops
		Season.WINTER:
			return crop_type in winter_crops
	return false

func save_game(player, animals: Array, crops: Array) -> void:
	var save_data: Dictionary = {
		"season": current_season,
		"day_count": day_count,
		"total_days": total_days,
		"player_position": [player.position.x, player.position.y, player.position.z],
		"player_rotation": [player.rotation.x, player.rotation.y, player.rotation.z],
		"inventory": player.inventory.items if player.inventory else {},
		"animals": [],
		"crops": []
	}
	
	for animal in animals:
		if animal.has_method("save_data"):
			save_data["animals"].append(animal.save_data())
	
	for crop in crops:
		if crop.has_method("save_data"):
			save_data["crops"].append(crop.save_data())
	
	var json_string: String = JSON.stringify(save_data)
	var file: FileAccess = FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if file:
		file.store_string(json_string)
		file.close()

func load_game() -> Dictionary:
	if not FileAccess.file_exists(SAVE_PATH):
		return {}
	
	var file: FileAccess = FileAccess.open(SAVE_PATH, FileAccess.READ)
	if not file:
		return {}
	
	var json_string: String = file.get_as_text()
	file.close()
	
	var parse_result: JSONParseResult = JSON.parse(json_string)
	if parse_result.error != OK:
		return {}
	
	var data: Dictionary = parse_result.data
	if data.has("season"):
		current_season = data["season"]
	if data.has("day_count"):
		day_count = data["day_count"]
	if data.has("total_days"):
		total_days = data["total_days"]
	
	return data
