import numpy as np
import pinocchio as pin
from typing import List, Tuple, Optional, Dict
from scipy.spatial import ConvexHull


class CollisionChecker:
    def __init__(self, robot_kinematics):
        self.robot = robot_kinematics
        self.collision_model = robot_kinematics.collision_model
        self.collision_data = robot_kinematics.collision_data

        self._setup_collision_pairs()
        self._environment_objects = []
        self._link_mesh_cache = {}
        self._default_mesh_density = 20

    def _setup_collision_pairs(self):
        self.collision_model.removeAllCollisionPairs()
        for i in range(len(self.collision_model.geometryObjects)):
            for j in range(i + 1, len(self.collision_model.geometryObjects)):
                obj1 = self.collision_model.geometryObjects[i]
                obj2 = self.collision_model.geometryObjects[j]

                if self._is_adjacent_link(obj1.parentFrame, obj2.parentFrame):
                    continue

                self.collision_model.addCollisionPair(
                    pin.CollisionPair(i, j)
                )

    def _is_adjacent_link(self, frame1_id: int, frame2_id: int) -> bool:
        if frame1_id == frame2_id:
            return True

        model = self.robot.model
        for joint_id in range(model.njoints):
            joint = model.joints[joint_id]
            if joint_id + 1 < model.njoints:
                next_joint = model.joints[joint_id + 1]
                if (joint.idx_q == frame1_id and next_joint.idx_q == frame2_id) or \
                   (joint.idx_q == frame2_id and next_joint.idx_q == frame1_id):
                    return True
        return False

    def add_collision_pair(self, geom_name1: str, geom_name2: str):
        id1 = self.collision_model.getGeometryId(geom_name1)
        id2 = self.collision_model.getGeometryId(geom_name2)
        self.collision_model.addCollisionPair(pin.CollisionPair(id1, id2))

    def remove_collision_pair(self, geom_name1: str, geom_name2: str):
        id1 = self.collision_model.getGeometryId(geom_name1)
        id2 = self.collision_model.getGeometryId(geom_name2)
        pair = pin.CollisionPair(id1, id2)
        if self.collision_model.existCollisionPair(pair):
            self.collision_model.removeCollisionPair(pair)

    def check_collision(self, q: np.ndarray) -> bool:
        q = np.asarray(q, dtype=float)
        pin.updateGeometryPlacements(
            self.robot.model, self.robot.data,
            self.collision_model, self.collision_data, q
        )
        return pin.computeCollisions(
            self.collision_model, self.collision_data, False
        )

    def _generate_box_mesh(self, half_size: np.ndarray, density: int = 20) -> np.ndarray:
        x = np.linspace(-half_size[0], half_size[0], density)
        y = np.linspace(-half_size[1], half_size[1], density)
        z = np.linspace(-half_size[2], half_size[2], density)

        points = []
        for xi in x:
            for yi in y:
                for zi in z:
                    on_face = (abs(xi) == half_size[0] or
                               abs(yi) == half_size[1] or
                               abs(zi) == half_size[2])
                    if on_face:
                        points.append([xi, yi, zi])
        return np.array(points)

    def _generate_cylinder_mesh(self, radius: float, length: float,
                                density: int = 20) -> np.ndarray:
        theta = np.linspace(0, 2 * np.pi, density)
        z = np.linspace(-length / 2, length / 2, density)

        points = []
        for t in theta:
            for zi in z:
                points.append([
                    radius * np.cos(t),
                    radius * np.sin(t),
                    zi
                ])

        for t in theta:
            points.append([
                radius * np.cos(t),
                radius * np.sin(t),
                -length / 2
            ])
            points.append([
                radius * np.cos(t),
                radius * np.sin(t),
                length / 2
            ])

        return np.array(points)

    def _generate_sphere_mesh(self, radius: float, density: int = 20) -> np.ndarray:
        phi = np.linspace(0, np.pi, density)
        theta = np.linspace(0, 2 * np.pi, density)

        points = []
        for p in phi:
            for t in theta:
                points.append([
                    radius * np.sin(p) * np.cos(t),
                    radius * np.sin(p) * np.sin(t),
                    radius * np.cos(p)
                ])
        return np.array(points)

    def _get_geometry_mesh_points(self, geom_obj, density: int = None) -> np.ndarray:
        if density is None:
            density = self._default_mesh_density

        geom_id = id(geom_obj)
        if geom_id in self._link_mesh_cache:
            return self._link_mesh_cache[geom_id]

        geometry = geom_obj.geometry

        try:
            if hasattr(geometry, 'halfSide'):
                half_size = np.array(geometry.halfSide)
                points = self._generate_box_mesh(half_size, density)
            elif hasattr(geometry, 'radius') and hasattr(geometry, 'length'):
                points = self._generate_cylinder_mesh(
                    geometry.radius, geometry.length, density
                )
            elif hasattr(geometry, 'radius') and not hasattr(geometry, 'length'):
                points = self._generate_sphere_mesh(geometry.radius, density)
            else:
                points = np.array([[0, 0, 0]])
        except Exception:
            points = np.array([[0, 0, 0]])

        self._link_mesh_cache[geom_id] = points
        return points

    def _transform_points(self, points: np.ndarray,
                          transform: np.ndarray) -> np.ndarray:
        R = transform[:3, :3]
        t = transform[:3, 3]
        return (R @ points.T).T + t

    def _gjk_distance_2d(self, points_a: np.ndarray, points_b: np.ndarray) -> float:
        def support(direction: np.ndarray) -> np.ndarray:
            a = points_a[np.argmax(points_a @ direction)]
            b = points_b[np.argmin(points_b @ direction)]
            return a - b

        direction = np.array([1.0, 0.0])
        simplex = [support(direction)]
        direction = -simplex[0]

        for _ in range(50):
            new_point = support(direction)
            if np.dot(new_point, direction) <= 0:
                return np.linalg.norm(simplex[0])
            simplex.append(new_point)

            if len(simplex) == 2:
                ab = simplex[0] - simplex[1]
                ao = -simplex[1]
                if np.dot(ab, ao) > 0:
                    direction = np.array([-ab[1], ab[0]])
                    simplex = [simplex[1]]
                else:
                    direction = ao
            elif len(simplex) == 3:
                ab = simplex[1] - simplex[2]
                ac = simplex[0] - simplex[2]
                ao = -simplex[2]

                ab_perp = np.array([-ab[1], ab[0]])
                ac_perp = np.array([-ac[1], ac[0]])

                if np.dot(ab_perp, ao) > 0:
                    direction = ab_perp
                    simplex = [simplex[1], simplex[2]]
                elif np.dot(ac_perp, ao) > 0:
                    direction = ac_perp
                    simplex = [simplex[0], simplex[2]]
                else:
                    return 0.0

        return np.linalg.norm(simplex[0])

    def _compute_mesh_distance_gjk(self, points_a: np.ndarray,
                                    points_b: np.ndarray) -> float:
        try:
            hull_a = ConvexHull(points_a)
            hull_b = ConvexHull(points_b)
            vertices_a = points_a[hull_a.vertices]
            vertices_b = points_b[hull_b.vertices]
        except Exception:
            vertices_a = points_a
            vertices_b = points_b

        min_dist = float('inf')

        for i in range(3):
            for j in range(3):
                if i == j:
                    continue
                proj_a = vertices_a[:, [i, j]]
                proj_b = vertices_b[:, [i, j]]
                dist = self._gjk_distance_2d(proj_a, proj_b)
                min_dist = min(min_dist, dist)

        return min_dist

    def check_mesh_collision(self, q: np.ndarray, density: int = None) -> bool:
        q = np.asarray(q, dtype=float)
        if density is None:
            density = self._default_mesh_density

        pin.updateGeometryPlacements(
            self.robot.model, self.robot.data,
            self.collision_model, self.collision_data, q
        )

        geom_count = len(self.collision_model.geometryObjects)

        for i in range(geom_count):
            for j in range(i + 1, geom_count):
                obj1 = self.collision_model.geometryObjects[i]
                obj2 = self.collision_model.geometryObjects[j]

                if self._is_adjacent_link(obj1.parentFrame, obj2.parentFrame):
                    continue

                pose1 = self.collision_data.oMg[i].homogeneous
                pose2 = self.collision_data.oMg[j].homogeneous

                mesh1_local = self._get_geometry_mesh_points(obj1, density)
                mesh2_local = self._get_geometry_mesh_points(obj2, density)

                mesh1_world = self._transform_points(mesh1_local, pose1)
                mesh2_world = self._transform_points(mesh2_local, pose2)

                dist = self._compute_mesh_distance_gjk(mesh1_world, mesh2_world)

                if dist <= 1e-6:
                    return True

        return False

    def compute_minimum_mesh_distance(self, q: np.ndarray,
                                       density: int = None) -> Tuple[float, str, str]:
        q = np.asarray(q, dtype=float)
        if density is None:
            density = self._default_mesh_density

        pin.updateGeometryPlacements(
            self.robot.model, self.robot.data,
            self.collision_model, self.collision_data, q
        )

        min_dist = float('inf')
        min_pair = (None, None)

        geom_count = len(self.collision_model.geometryObjects)

        for i in range(geom_count):
            for j in range(i + 1, geom_count):
                obj1 = self.collision_model.geometryObjects[i]
                obj2 = self.collision_model.geometryObjects[j]

                if self._is_adjacent_link(obj1.parentFrame, obj2.parentFrame):
                    continue

                pose1 = self.collision_data.oMg[i].homogeneous
                pose2 = self.collision_data.oMg[j].homogeneous

                mesh1_local = self._get_geometry_mesh_points(obj1, density)
                mesh2_local = self._get_geometry_mesh_points(obj2, density)

                mesh1_world = self._transform_points(mesh1_local, pose1)
                mesh2_world = self._transform_points(mesh2_local, pose2)

                dist = self._compute_mesh_distance_gjk(mesh1_world, mesh2_world)

                if dist < min_dist:
                    min_dist = dist
                    min_pair = (obj1.name, obj2.name)

        return min_dist, min_pair[0], min_pair[1]

    def check_collision_with_env(self, q: np.ndarray, use_mesh: bool = True) -> bool:
        if use_mesh:
            if self.check_mesh_collision(q):
                return True
        else:
            if self.check_collision(q):
                return True
        return self._check_environment_collisions(q)

    def _check_environment_collisions(self, q: np.ndarray) -> bool:
        pin.updateGeometryPlacements(
            self.robot.model, self.robot.data,
            self.collision_model, self.collision_data, q
        )

        for obj in self._environment_objects:
            obj_pos = obj['position']

            if obj['type'] == 'box':
                obj_size = obj['size']
                obj_mesh = self._generate_box_mesh(obj_size / 2)
                obj_world = obj_mesh + obj_pos
            elif obj['type'] == 'sphere':
                obj_radius = obj['radius']
                obj_mesh = self._generate_sphere_mesh(obj_radius)
                obj_world = obj_mesh + obj_pos
            else:
                continue

            for i in range(len(self.collision_model.geometryObjects)):
                geom = self.collision_model.geometryObjects[i]
                geom_pose = self.collision_data.oMg[i].homogeneous
                geom_mesh = self._get_geometry_mesh_points(geom)
                geom_world = self._transform_points(geom_mesh, geom_pose)

                dist = self._compute_mesh_distance_gjk(geom_world, obj_world)
                if dist <= 1e-6:
                    return True
        return False

    def get_colliding_pairs(self, q: np.ndarray, use_mesh: bool = True) -> List[Tuple[str, str]]:
        q = np.asarray(q, dtype=float)

        if not use_mesh:
            pin.updateGeometryPlacements(
                self.robot.model, self.robot.data,
                self.collision_model, self.collision_data, q
            )
            pin.computeCollisions(
                self.collision_model, self.collision_data, False
            )

            colliding_pairs = []
            for pair_id, collision_pair in enumerate(self.collision_model.collisionPairs):
                if self.collision_data.collisionResults[pair_id].isCollision():
                    geom1 = self.collision_model.geometryObjects[collision_pair.first]
                    geom2 = self.collision_model.geometryObjects[collision_pair.second]
                    colliding_pairs.append((geom1.name, geom2.name))
            return colliding_pairs

        pin.updateGeometryPlacements(
            self.robot.model, self.robot.data,
            self.collision_model, self.collision_data, q
        )

        colliding_pairs = []
        geom_count = len(self.collision_model.geometryObjects)

        for i in range(geom_count):
            for j in range(i + 1, geom_count):
                obj1 = self.collision_model.geometryObjects[i]
                obj2 = self.collision_model.geometryObjects[j]

                if self._is_adjacent_link(obj1.parentFrame, obj2.parentFrame):
                    continue

                pose1 = self.collision_data.oMg[i].homogeneous
                pose2 = self.collision_data.oMg[j].homogeneous

                mesh1_local = self._get_geometry_mesh_points(obj1)
                mesh2_local = self._get_geometry_mesh_points(obj2)

                mesh1_world = self._transform_points(mesh1_local, pose1)
                mesh2_world = self._transform_points(mesh2_local, pose2)

                dist = self._compute_mesh_distance_gjk(mesh1_world, mesh2_world)

                if dist <= 1e-6:
                    colliding_pairs.append((obj1.name, obj2.name))

        return colliding_pairs

    def compute_minimum_distance(self, q: np.ndarray) -> float:
        q = np.asarray(q, dtype=float)
        pin.updateGeometryPlacements(
            self.robot.model, self.robot.data,
            self.collision_model, self.collision_data, q
        )

        distances = pin.computeDistances(
            self.collision_model, self.collision_data
        )

        if len(distances) == 0:
            return float('inf')
        return np.min(distances)

    def compute_pairwise_distances(self, q: np.ndarray) -> List[Tuple[str, str, float]]:
        q = np.asarray(q, dtype=float)
        pin.updateGeometryPlacements(
            self.robot.model, self.robot.data,
            self.collision_model, self.collision_data, q
        )

        pin.computeDistances(self.collision_model, self.collision_data)

        results = []
        for pair_id, collision_pair in enumerate(self.collision_model.collisionPairs):
            dist = self.collision_data.distanceResults[pair_id].min_distance
            geom1 = self.collision_model.geometryObjects[collision_pair.first]
            geom2 = self.collision_model.geometryObjects[collision_pair.second]
            results.append((geom1.name, geom2.name, dist))

        return results

    def add_environment_box(
        self,
        name: str,
        position: np.ndarray,
        size: np.ndarray,
    ):
        self._environment_objects.append({
            'name': name,
            'type': 'box',
            'position': np.asarray(position, dtype=float),
            'size': np.asarray(size, dtype=float),
        })

    def add_environment_sphere(
        self,
        name: str,
        position: np.ndarray,
        radius: float,
    ):
        self._environment_objects.append({
            'name': name,
            'type': 'sphere',
            'position': np.asarray(position, dtype=float),
            'radius': float(radius),
        })

    def remove_environment_object(self, name: str):
        self._environment_objects = [
            obj for obj in self._environment_objects if obj['name'] != name
        ]

    def clear_environment(self):
        self._environment_objects.clear()

    def is_configuration_safe(
        self,
        q: np.ndarray,
        safety_margin: float = 0.02,
        use_mesh: bool = True,
    ) -> bool:
        if use_mesh:
            if self.check_mesh_collision(q):
                return False
            min_dist, _, _ = self.compute_minimum_mesh_distance(q)
        else:
            if self.check_collision(q):
                return False
            min_dist = self.compute_minimum_distance(q)
        return min_dist >= safety_margin

    def check_path_collision(
        self,
        q_start: np.ndarray,
        q_end: np.ndarray,
        num_steps: int = 20,
        use_mesh: bool = True,
    ) -> bool:
        q_start = np.asarray(q_start, dtype=float)
        q_end = np.asarray(q_end, dtype=float)

        for i in range(num_steps + 1):
            alpha = i / num_steps
            q = q_start + alpha * (q_end - q_start)
            if use_mesh:
                if self.check_mesh_collision(q):
                    return True
            else:
                if self.check_collision(q):
                    return True
        return False

    def get_safety_margin(self, q: np.ndarray, use_mesh: bool = True) -> float:
        if use_mesh:
            min_dist, _, _ = self.compute_minimum_mesh_distance(q)
            return min_dist
        return self.compute_minimum_distance(q)

    def get_link_surface_points(self, q: np.ndarray, link_name: str,
                                 density: int = None) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        if density is None:
            density = self._default_mesh_density

        pin.updateGeometryPlacements(
            self.robot.model, self.robot.data,
            self.collision_model, self.collision_data, q
        )

        for i, geom in enumerate(self.collision_model.geometryObjects):
            if link_name in geom.name:
                pose = self.collision_data.oMg[i].homogeneous
                mesh_local = self._get_geometry_mesh_points(geom, density)
                return self._transform_points(mesh_local, pose)

        return np.array([])

    def set_mesh_density(self, density: int):
        self._default_mesh_density = max(5, min(density, 100))
        self._link_mesh_cache.clear()
