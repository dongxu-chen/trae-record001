extends CharacterBody3D

@export var move_speed: float = 5.0
@export var jump_velocity: float = 4.5
@export var mouse_sensitivity: float = 0.002
@export var gravity: float = 9.8
@export var friction: float = 10.0

var inventory: Inventory = null
var ui: UI = null
var save_game: SaveGame = null

var rotation_x: float = 0.0
var rotation_y: float = 0.0

func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	inventory = Inventory.new()
	inventory.add_item("wheat_seed", 10)
	inventory.add_item("tomato_seed", 5)
	inventory.add_item("watering_can", 1)
	inventory.add_item("hoe", 1)
	
	call_deferred("_setup_ui")

func _setup_ui() -> void:
	var ui_node = get_parent().get_node_or_null("UIInstance")
	if ui_node:
		ui = ui_node
		ui.set_inventory(inventory)
		ui.select_slot(0)

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		rotation_x -= event.relative.y * mouse_sensitivity
		rotation_y -= event.relative.x * mouse_sensitivity
		rotation_x = clamp(rotation_x, -PI / 2, PI / 2)
		$Camera3D.rotation.x = rotation_x
		rotation.y = rotation_y

	if event.is_action_pressed("interact"):
		interact()

	if event.is_action_pressed("slot_1"):
		if ui:
			ui.select_slot(0)
	elif event.is_action_pressed("slot_2"):
		if ui:
			ui.select_slot(1)
	elif event.is_action_pressed("slot_3"):
		if ui:
			ui.select_slot(2)
	elif event.is_action_pressed("slot_4"):
		if ui:
			ui.select_slot(3)

func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= gravity * delta
	
	var input_dir: Vector3 = Vector3.ZERO
	if Input.is_action_pressed("move_forward"):
		input_dir.z -= 1.0
	if Input.is_action_pressed("move_back"):
		input_dir.z += 1.0
	if Input.is_action_pressed("move_left"):
		input_dir.x -= 1.0
	if Input.is_action_pressed("move_right"):
		input_dir.x += 1.0
	
	if input_dir != Vector3.ZERO:
		input_dir = input_dir.normalized()
		var direction: Vector3 = (transform.basis * Vector3(input_dir.x, 0, input_dir.z)).normalized()
		velocity.x = direction.x * move_speed
		velocity.z = direction.z * move_speed
	else:
		var friction_delta: float = friction * delta
		velocity.x = move_toward(velocity.x, 0, friction_delta)
		velocity.z = move_toward(velocity.z, 0, friction_delta)
	
	move_and_slide()
	
	if is_on_floor():
		var floor_normal: Vector3 = get_floor_normal()
		var slope_angle: float = floor_normal.angle_to(Vector3.UP)
		var max_slope_angle: float = deg_to_rad(45.0)
		
		if slope_angle > 0.01 and slope_angle < max_slope_angle:
			var slide_direction: Vector3 = floor_normal.cross(Vector3.UP).cross(floor_normal).normalized()
			var input_along_slide: float = Vector3(velocity.x, 0, velocity.z).dot(slide_direction)
			if abs(input_along_slide) < 0.1:
				velocity.y = 0.0

func interact() -> void:
	var ray: RayCast3D = $Camera3D/InteractionRayCast3D
	if ray.is_colliding():
		var collider = ray.get_collider()
		if collider.has_method("interact"):
			collider.interact(self)
		else:
			try_plant_crop(collider, ray.get_collision_point())

func try_plant_crop(collider, position: Vector3) -> void:
	if collider.is_in_group("farmland"):
		var selected_slot: int = 0
		if ui:
			selected_slot = ui.selected_slot
		
		var item_id: String = inventory.get_item_at(selected_slot)
		if item_id.ends_with("_seed") and inventory.get_item_count(item_id) > 0:
			var crop_type: String = item_id.replace("_seed", "")
			
			var save_node = get_parent().get_node_or_null("SaveGame")
			if save_node and save_node.has_method("can_plant_in_season"):
				var current_season: int = save_node.get_current_season()
				if not save_node.can_plant_in_season(crop_type, current_season):
					return
			
			var crop_scene: PackedScene = load("res://scenes/crop.tscn")
			if crop_scene:
				var crop = crop_scene.instantiate()
				crop.set_crop_type(crop_type)
				
				if save_node and save_node.has_method("get_current_season"):
					crop.set_season_planted(save_node.get_current_season())
				
				crop.position = Vector3(round(position.x), 0.1, round(position.z))
				get_parent().add_child(crop)
				inventory.remove_item(item_id, 1)
				if ui:
					ui.update_hotbar()
