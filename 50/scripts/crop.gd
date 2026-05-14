extends StaticBody3D

enum GrowthState {
	SEED,
	SPROUT,
	GROWING,
	MATURE,
	HARVESTABLE
}

@export var growth_time: float = 30.0
@export var watered: bool = false
@export var crop_type: String = "wheat"

var current_state: GrowthState = GrowthState.SEED
var growth_progress: float = 0.0
var season_planted: int = 0

var harvest_yield: Dictionary = {
	"wheat": {"item": "wheat", "count": 3},
	"tomato": {"item": "tomato", "count": 2},
	"corn": {"item": "corn", "count": 2},
	"sunflower": {"item": "sunflower_seed", "count": 4},
	"pumpkin": {"item": "pumpkin", "count": 1},
	"carrot": {"item": "carrot", "count": 3}
}

func _ready() -> void:
	$CollisionShape3D.disabled = true
	update_visual()

func _process(delta: float) -> void:
	if watered and current_state != GrowthState.HARVESTABLE:
		var previous_state: GrowthState = current_state
		growth_progress += delta
		var state_threshold: float = growth_time / 4.0
		
		if growth_progress >= state_threshold * 4:
			current_state = GrowthState.HARVESTABLE
			$CollisionShape3D.disabled = false
		elif growth_progress >= state_threshold * 3:
			current_state = GrowthState.MATURE
		elif growth_progress >= state_threshold * 2:
			current_state = GrowthState.GROWING
		elif growth_progress >= state_threshold:
			current_state = GrowthState.SPROUT
		
		if current_state != previous_state:
			update_visual()

func set_crop_type(type: String) -> void:
	crop_type = type

func set_season_planted(season: int) -> void:
	season_planted = season

func can_survive(current_season: int) -> bool:
	var spring_crops: Array = ["wheat", "tomato", "carrot"]
	var summer_crops: Array = ["tomato", "corn", "sunflower"]
	var autumn_crops: Array = ["wheat", "pumpkin", "carrot"]
	var winter_crops: Array = []
	
	var all_valid_seasons: Array = []
	if crop_type in spring_crops:
		all_valid_seasons.append(0)
	if crop_type in summer_crops:
		all_valid_seasons.append(1)
	if crop_type in autumn_crops:
		all_valid_seasons.append(2)
	if crop_type in winter_crops:
		all_valid_seasons.append(3)
	
	return current_season in all_valid_seasons

func water() -> void:
	watered = true

func interact(player) -> void:
	if current_state == GrowthState.HARVESTABLE:
		harvest(player)
	elif current_state != GrowthState.HARVESTABLE and not watered:
		if player.inventory and player.inventory.has_item("watering_can"):
			water()

func harvest(player) -> void:
	if harvest_yield.has(crop_type):
		var yield_data: Dictionary = harvest_yield[crop_type]
		if player.inventory:
			player.inventory.add_item(yield_data.item, yield_data.count)
			player.inventory.add_item(crop_type + "_seed", 1)
		if player.ui:
			player.ui.update_hotbar()
	queue_free()

func save_data() -> Dictionary:
	return {
		"crop_type": crop_type,
		"position": [position.x, position.y, position.z],
		"growth_progress": growth_progress,
		"watered": watered,
		"season_planted": season_planted,
		"current_state": current_state
	}

func load_data(data: Dictionary) -> void:
	if data.has("crop_type"):
		crop_type = data["crop_type"]
	if data.has("growth_progress"):
		growth_progress = data["growth_progress"]
	if data.has("watered"):
		watered = data["watered"]
	if data.has("season_planted"):
		season_planted = data["season_planted"]
	if data.has("current_state"):
		current_state = data["current_state"]
		if current_state == GrowthState.HARVESTABLE:
			$CollisionShape3D.disabled = false
	update_visual()

func update_visual() -> void:
	var mesh: MeshInstance3D = $MeshInstance3D
	var colors: Dictionary = {
		GrowthState.SEED: Color(0.5, 0.35, 0.2, 1),
		GrowthState.SPROUT: Color(0.5, 0.7, 0.4, 1),
		GrowthState.GROWING: Color(0.4, 0.65, 0.3, 1),
		GrowthState.MATURE: Color(0.6, 0.7, 0.3, 1),
		GrowthState.HARVESTABLE: Color(0.8, 0.7, 0.2, 1)
	}
	
	var heights: Dictionary = {
		GrowthState.SEED: 0.1,
		GrowthState.SPROUT: 0.3,
		GrowthState.GROWING: 0.6,
		GrowthState.MATURE: 0.9,
		GrowthState.HARVESTABLE: 1.0
	}
	
	var scales: Dictionary = {
		GrowthState.SEED: 0.3,
		GrowthState.SPROUT: 0.5,
		GrowthState.GROWING: 0.7,
		GrowthState.MATURE: 0.9,
		GrowthState.HARVESTABLE: 1.0
	}
	
	var material: StandardMaterial3D = mesh.material_override
	if material:
		material.albedo_color = colors[current_state]
	
	var scale_val: float = scales[current_state]
	mesh.scale = Vector3(scale_val, heights[current_state], scale_val)
	mesh.position.y = heights[current_state] * 0.5
