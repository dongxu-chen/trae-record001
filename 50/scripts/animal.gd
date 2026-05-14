extends CharacterBody3D

enum AnimalType {
	CHICKEN,
	COW
}

@export var animal_type: AnimalType = AnimalType.CHICKEN
@export var animal_name: String = "动物"
@export var wander_speed: float = 1.5
@export var wander_range: float = 3.0
@export var happiness: float = 50.0
@export var hunger: float = 50.0

var is_fed: bool = false
var last_fed_day: int = 0
var home_position: Vector3
var wander_timer: float = 0.0
var wander_direction: Vector3 = Vector3.ZERO
var production_timer: float = 0.0

const PRODUCTION_INTERVAL: float = 60.0
const HUNGER_DECAY_RATE: float = 5.0
const HAPPINESS_DECAY_RATE: float = 2.0

func _ready() -> void:
	if name.to_lower().contains("cow"):
		animal_type = AnimalType.COW
	elif name.to_lower().contains("chicken"):
		animal_type = AnimalType.CHICKEN
	
	home_position = position
	$CollisionShape3D.disabled = false
	update_visual()

func _physics_process(delta: float) -> void:
	hunger -= HUNGER_DECAY_RATE * delta
	if hunger < 0:
		hunger = 0
	
	if is_fed:
		happiness += delta
		if happiness > 100:
			happiness = 100
	else:
		happiness -= HAPPINESS_DECAY_RATE * delta
		if happiness < 0:
			happiness = 0
	
	production_timer += delta
	if production_timer >= PRODUCTION_INTERVAL:
		production_timer = 0.0
		if happiness > 30.0:
			produce()
	
	wander_timer -= delta
	if wander_timer <= 0.0:
		choose_new_direction()
	
	if wander_direction != Vector3.ZERO:
		velocity = wander_direction * wander_speed
		velocity.y = velocity.y - 9.8 * delta
		move_and_slide()
		
		var distance_from_home: float = position.distance_to(home_position)
		if distance_from_home > wander_range:
			var back_to_home: Vector3 = (home_position - position).normalized()
			velocity.x = back_to_home.x * wander_speed
			velocity.z = back_to_home.z * wander_speed

func choose_new_direction() -> void:
	var random_angle: float = randf() * TAU
	wander_direction = Vector3(cos(random_angle), 0, sin(random_angle)).normalized()
	wander_timer = randf_range(1.0, 3.0)

func interact(player) -> void:
	if player.inventory and player.inventory.has_item("wheat", 1):
		feed(player)
	elif player.inventory and player.inventory.has_item("watering_can"):
		give_water()
	else:
		pet()

func feed(player) -> void:
	if player.inventory.remove_item("wheat", 1):
		is_fed = true
		hunger = 100.0
		happiness += 20.0
		if happiness > 100:
			happiness = 100
		if player.ui:
			player.ui.update_hotbar()

func give_water() -> void:
	happiness += 10.0
	if happiness > 100:
		happiness = 100

func pet() -> void:
	happiness += 5.0
	if happiness > 100:
		happiness = 100

func produce() -> void:
	match animal_type:
		AnimalType.CHICKEN:
			if get_tree().root.has_node("PlayerInstance"):
				var player = get_tree().root.get_node("PlayerInstance")
				if player.inventory:
					player.inventory.add_item("egg", 1)
					if player.ui:
						player.ui.update_hotbar()
		AnimalType.COW:
			if get_tree().root.has_node("PlayerInstance"):
				var player = get_tree().root.get_node("PlayerInstance")
				if player.inventory:
					player.inventory.add_item("milk", 1)
					if player.ui:
						player.ui.update_hotbar()

func get_animal_name() -> String:
	match animal_type:
		AnimalType.CHICKEN:
			return "鸡"
		AnimalType.COW:
			return "牛"
	return "动物"

func save_data() -> Dictionary:
	return {
		"animal_type": animal_type,
		"position": [position.x, position.y, position.z],
		"home_position": [home_position.x, home_position.y, home_position.z],
		"happiness": happiness,
		"hunger": hunger,
		"is_fed": is_fed,
		"production_timer": production_timer
	}

func load_data(data: Dictionary) -> void:
	if data.has("animal_type"):
		animal_type = data["animal_type"]
	if data.has("happiness"):
		happiness = data["happiness"]
	if data.has("hunger"):
		hunger = data["hunger"]
	if data.has("is_fed"):
		is_fed = data["is_fed"]
	if data.has("production_timer"):
		production_timer = data["production_timer"]
	update_visual()

func update_visual() -> void:
	var mesh: MeshInstance3D = $MeshInstance3D
	var material: StandardMaterial3D = mesh.material_override
	if material:
		match animal_type:
			AnimalType.CHICKEN:
				material.albedo_color = Color(1.0, 0.9, 0.7, 1)
				mesh.scale = Vector3(0.5, 0.6, 0.5)
			AnimalType.COW:
				material.albedo_color = Color(0.8, 0.5, 0.2, 1)
				mesh.scale = Vector3(1.0, 1.2, 1.5)
