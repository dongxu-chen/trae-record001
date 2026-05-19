import numpy as np
import pinocchio as pin


class RobotKinematics:
    def __init__(self, urdf_path: str, end_effector_name: str = None):
        self.urdf_path = urdf_path
        self.model, self.collision_model, self.visual_model = pin.buildModelsFromUrdf(
            urdf_path
        )
        self.data = self.model.createData()
        self.collision_data = self.collision_model.createData()
        self.visual_data = self.visual_model.createData()

        if end_effector_name is None:
            end_effector_name = self.model.frames[-1].name
        self.set_end_effector(end_effector_name)

    def set_end_effector(self, frame_name: str):
        frame_ids = [f.name for f in self.model.frames]
        if frame_name not in frame_ids:
            raise ValueError(f"Frame '{frame_name}' not found in model")
        self.end_effector_id = self.model.getFrameId(frame_name)
        self.end_effector_name = frame_name

    def get_joint_names(self):
        return [name for name in self.model.names[1:]]

    def get_joint_limits(self):
        lower = self.model.lowerPositionLimit
        upper = self.model.upperPositionLimit
        return lower, upper

    def random_configuration(self):
        return pin.randomConfiguration(self.model)

    def forward_kinematics(self, q: np.ndarray) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        if q.shape[0] != self.model.nq:
            raise ValueError(
                f"Expected {self.model.nq} joints, got {q.shape[0]}"
            )
        pin.framesForwardKinematics(self.model, self.data, q)
        return self.data.oMf[self.end_effector_id].homogeneous

    def get_frame_position(self, q: np.ndarray, frame_name: str) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        frame_id = self.model.getFrameId(frame_name)
        pin.framesForwardKinematics(self.model, self.data, q)
        return self.data.oMf[frame_id].translation

    def get_frame_rotation(self, q: np.ndarray, frame_name: str) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        frame_id = self.model.getFrameId(frame_name)
        pin.framesForwardKinematics(self.model, self.data, q)
        return self.data.oMf[frame_id].rotation

    def jacobian(self, q: np.ndarray, frame_name: str = None) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        if q.shape[0] != self.model.nq:
            raise ValueError(
                f"Expected {self.model.nq} joints, got {q.shape[0]}"
            )
        
        if frame_name is None:
            frame_id = self.end_effector_id
        else:
            frame_id = self.model.getFrameId(frame_name)
        
        pin.computeJointJacobians(self.model, self.data, q)
        pin.framesForwardKinematics(self.model, self.data, q)
        J = pin.getFrameJacobian(
            self.model, self.data, frame_id, pin.LOCAL_WORLD_ALIGNED
        )
        return J

    def jacobian_geometric(self, q: np.ndarray, frame_name: str = None) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        if frame_name is None:
            frame_id = self.end_effector_id
        else:
            frame_id = self.model.getFrameId(frame_name)
        
        pin.computeJointJacobians(self.model, self.data, q)
        pin.framesForwardKinematics(self.model, self.data, q)
        J = pin.getFrameJacobian(self.model, self.data, frame_id, pin.LOCAL)
        return J

    def manipulability(self, q: np.ndarray) -> float:
        J = self.jacobian(q)
        det_JJT = np.linalg.det(J @ J.T)
        return np.sqrt(max(det_JJT, 0))

    def inverse_kinematics(
        self,
        target_pose: np.ndarray,
        initial_guess: np.ndarray = None,
        max_iter: int = 500,
        tolerance: float = 1e-4,
        damping: float = 1e-3,
        method: str = "damped_least_squares",
    ) -> tuple[np.ndarray, bool, float]:
        target_pose = np.asarray(target_pose, dtype=float)
        if target_pose.shape != (4, 4):
            raise ValueError("target_pose must be a 4x4 homogeneous matrix")

        if initial_guess is None:
            q = self.random_configuration()
        else:
            q = np.asarray(initial_guess, dtype=float)
            if q.shape[0] != self.model.nq:
                raise ValueError(
                    f"Initial guess must have {self.model.nq} elements"
                )

        target_se3 = pin.SE3(target_pose[:3, :3], target_pose[:3, 3])

        for i in range(max_iter):
            pin.framesForwardKinematics(self.model, self.data, q)
            current_se3 = self.data.oMf[self.end_effector_id]
            error = pin.log6(current_se3.inverse() * target_se3).vector

            error_norm = np.linalg.norm(error)
            if error_norm < tolerance:
                return q, True, error_norm

            J = self.jacobian_geometric(q)

            if method == "damped_least_squares":
                JJT = J @ J.T + damping**2 * np.eye(6)
                v = J.T @ np.linalg.solve(JJT, error)
            elif method == "pseudoinverse":
                J_pinv = np.linalg.pinv(J, damping)
                v = J_pinv @ error
            elif method == "gauss_newton":
                v = np.linalg.lstsq(J, error, rcond=None)[0]
            else:
                raise ValueError(f"Unknown method: {method}")

            q = pin.integrate(self.model, q, v)

            lower = self.model.lowerPositionLimit
            upper = self.model.upperPositionLimit
            q = np.clip(q, lower, upper)

        return q, False, error_norm

    def inverse_kinematics_position(
        self,
        target_position: np.ndarray,
        initial_guess: np.ndarray = None,
        max_iter: int = 500,
        tolerance: float = 1e-4,
        damping: float = 1e-3,
    ) -> tuple[np.ndarray, bool, float]:
        target_position = np.asarray(target_position, dtype=float)
        if target_position.shape != (3,):
            raise ValueError("target_position must be a 3D vector")

        if initial_guess is None:
            q = self.random_configuration()
        else:
            q = np.asarray(initial_guess, dtype=float)

        for i in range(max_iter):
            current_pos = self.get_frame_position(q, self.end_effector_name)
            error = target_position - current_pos
            error_norm = np.linalg.norm(error)

            if error_norm < tolerance:
                return q, True, error_norm

            J = self.jacobian(q)[:3, :]
            JJT = J @ J.T + damping**2 * np.eye(3)
            v = J.T @ np.linalg.solve(JJT, error)

            q = pin.integrate(self.model, q, v)
            lower = self.model.lowerPositionLimit
            upper = self.model.upperPositionLimit
            q = np.clip(q, lower, upper)

        return q, False, error_norm

    def check_joint_limits(self, q: np.ndarray) -> bool:
        q = np.asarray(q, dtype=float)
        lower = self.model.lowerPositionLimit
        upper = self.model.upperPositionLimit
        return np.all(q >= lower) and np.all(q <= upper)

    def is_singular(self, q: np.ndarray, threshold: float = 1e-3) -> bool:
        J = self.jacobian(q)
        singular_values = np.linalg.svd(J, compute_uv=False)
        min_singular = np.min(singular_values)
        return min_singular < threshold

    def condition_number(self, q: np.ndarray) -> float:
        J = self.jacobian(q)
        singular_values = np.linalg.svd(J, compute_uv=False)
        if np.min(singular_values) < 1e-10:
            return float('inf')
        return np.max(singular_values) / np.min(singular_values)

    def inverse_kinematics_multi_guess(
        self,
        target_pose: np.ndarray,
        num_guesses: int = 20,
        max_iter: int = 500,
        tolerance: float = 1e-4,
        damping: float = 1e-3,
        method: str = "damped_least_squares",
        initial_guesses: list = None,
        weights: dict = None,
    ) -> tuple[np.ndarray, bool, float, dict]:
        target_pose = np.asarray(target_pose, dtype=float)
        if target_pose.shape != (4, 4):
            raise ValueError("target_pose must be a 4x4 homogeneous matrix")

        if weights is None:
            weights = {
                'error': 1.0,
                'manipulability': 0.1,
                'joint_displacement': 0.01,
                'condition_number': 0.01
            }

        if initial_guesses is None:
            guesses = [self.random_configuration() for _ in range(num_guesses)]
        else:
            guesses = list(initial_guesses)
            while len(guesses) < num_guesses:
                guesses.append(self.random_configuration())

        results = []
        q_nominal = np.zeros(self.model.nq)

        for q0 in guesses:
            q_sol, success, error = self.inverse_kinematics(
                target_pose,
                initial_guess=q0,
                max_iter=max_iter,
                tolerance=tolerance,
                damping=damping,
                method=method
            )

            if success:
                manip = self.manipulability(q_sol)
                joint_disp = np.linalg.norm(q_sol - q_nominal)
                cond = self.condition_number(q_sol)

                score = (
                    weights['error'] * error
                    - weights['manipulability'] * manip
                    + weights['joint_displacement'] * joint_disp
                    + weights['condition_number'] * min(cond, 100)
                )

                results.append({
                    'q': q_sol,
                    'success': True,
                    'error': error,
                    'manipulability': manip,
                    'joint_displacement': joint_disp,
                    'condition_number': cond,
                    'score': score,
                    'initial_guess': q0
                })

        if len(results) == 0:
            q_best = guesses[0]
            best_info = {'error': float('inf'), 'success': False, 'num_solutions': 0}
            return q_best, False, float('inf'), best_info

        results.sort(key=lambda x: x['score'])
        best = results[0]

        best_info = {
            'success': True,
            'error': best['error'],
            'manipulability': best['manipulability'],
            'joint_displacement': best['joint_displacement'],
            'condition_number': best['condition_number'],
            'score': best['score'],
            'num_solutions': len(results),
            'all_solutions': results
        }

        return best['q'], True, best['error'], best_info

    def inverse_kinematics_position_multi_guess(
        self,
        target_position: np.ndarray,
        num_guesses: int = 20,
        max_iter: int = 500,
        tolerance: float = 1e-4,
        damping: float = 1e-3,
        initial_guesses: list = None,
        weights: dict = None,
    ) -> tuple[np.ndarray, bool, float, dict]:
        target_position = np.asarray(target_position, dtype=float)
        if target_position.shape != (3,):
            raise ValueError("target_position must be a 3D vector")

        if weights is None:
            weights = {
                'error': 1.0,
                'manipulability': 0.1,
                'joint_displacement': 0.01,
                'condition_number': 0.01
            }

        if initial_guesses is None:
            guesses = [self.random_configuration() for _ in range(num_guesses)]
        else:
            guesses = list(initial_guesses)
            while len(guesses) < num_guesses:
                guesses.append(self.random_configuration())

        results = []
        q_nominal = np.zeros(self.model.nq)

        for q0 in guesses:
            q_sol, success, error = self.inverse_kinematics_position(
                target_position,
                initial_guess=q0,
                max_iter=max_iter,
                tolerance=tolerance,
                damping=damping
            )

            if success:
                manip = self.manipulability(q_sol)
                joint_disp = np.linalg.norm(q_sol - q_nominal)
                cond = self.condition_number(q_sol)

                score = (
                    weights['error'] * error
                    - weights['manipulability'] * manip
                    + weights['joint_displacement'] * joint_disp
                    + weights['condition_number'] * min(cond, 100)
                )

                results.append({
                    'q': q_sol,
                    'success': True,
                    'error': error,
                    'manipulability': manip,
                    'joint_displacement': joint_disp,
                    'condition_number': cond,
                    'score': score,
                    'initial_guess': q0
                })

        if len(results) == 0:
            q_best = guesses[0]
            best_info = {'error': float('inf'), 'success': False, 'num_solutions': 0}
            return q_best, False, float('inf'), best_info

        results.sort(key=lambda x: x['score'])
        best = results[0]

        best_info = {
            'success': True,
            'error': best['error'],
            'manipulability': best['manipulability'],
            'joint_displacement': best['joint_displacement'],
            'condition_number': best['condition_number'],
            'score': best['score'],
            'num_solutions': len(results),
            'all_solutions': results
        }

        return best['q'], True, best['error'], best_info
