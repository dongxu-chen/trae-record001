import numpy as np
import pinocchio as pin
from typing import Tuple, Optional, List, Callable


class DynamicsSimulator:
    def __init__(self, robot_kinematics):
        self.robot = robot_kinematics
        self.model = robot_kinematics.model
        self.data = robot_kinematics.data

        self.nv = self.model.nv
        self.nq = self.model.nq

        self.gravity = np.array([0, 0, -9.81])
        self.default_friction = 0.1

    def compute_mass_matrix(self, q: np.ndarray) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        return pin.crba(self.model, self.data, q)

    def compute_coriolis_matrix(
        self, q: np.ndarray, dq: np.ndarray
    ) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        dq = np.asarray(dq, dtype=float)
        return pin.computeCoriolisMatrix(self.model, self.data, q, dq)

    def compute_coriolis_vector(
        self, q: np.ndarray, dq: np.ndarray
    ) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        dq = np.asarray(dq, dtype=float)
        return pin.nonLinearEffects(self.model, self.data, q, dq)

    def compute_gravity_vector(self, q: np.ndarray) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        return pin.computeGeneralizedGravity(self.model, self.data, q, self.gravity)

    def compute_inverse_dynamics(
        self,
        q: np.ndarray,
        dq: np.ndarray,
        ddq: np.ndarray,
    ) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        dq = np.asarray(dq, dtype=float)
        ddq = np.asarray(ddq, dtype=float)
        return pin.rnea(self.model, self.data, q, dq, ddq)

    def compute_forward_dynamics(
        self,
        q: np.ndarray,
        dq: np.ndarray,
        tau: np.ndarray,
        friction: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        dq = np.asarray(dq, dtype=float)
        tau = np.asarray(tau, dtype=float)

        if friction is not None:
            friction = np.asarray(friction, dtype=float)
            tau_eff = tau - friction * dq
        else:
            tau_eff = tau - self.default_friction * dq

        pin.computeAllTerms(self.model, self.data, q, dq)
        M = self.data.M
        h = pin.nonLinearEffects(self.model, self.data, q, dq)

        ddq = np.linalg.solve(M, tau_eff - h)
        return ddq

    def simulate(
        self,
        q0: np.ndarray,
        dq0: np.ndarray,
        torque_function: Callable[[float, np.ndarray, np.ndarray], np.ndarray],
        duration: float,
        dt: float = 0.001,
        friction: Optional[np.ndarray] = None,
        callback: Optional[Callable[[float, np.ndarray, np.ndarray, np.ndarray], None]] = None,
    ) -> dict:
        q0 = np.asarray(q0, dtype=float)
        dq0 = np.asarray(dq0, dtype=float)

        num_steps = int(duration / dt)
        time_steps = np.arange(num_steps) * dt

        q_traj = np.zeros((num_steps, self.nq))
        dq_traj = np.zeros((num_steps, self.nv))
        ddq_traj = np.zeros((num_steps, self.nv))
        tau_traj = np.zeros((num_steps, self.nv))

        q = q0.copy()
        dq = dq0.copy()

        for i in range(num_steps):
            t = time_steps[i]
            tau = torque_function(t, q, dq)
            tau = np.asarray(tau, dtype=float)

            ddq = self.compute_forward_dynamics(q, dq, tau, friction)

            q_traj[i] = q
            dq_traj[i] = dq
            ddq_traj[i] = ddq
            tau_traj[i] = tau

            if callback is not None:
                callback(t, q, dq, ddq)

            dq = dq + ddq * dt
            q = pin.integrate(self.model, q, dq * dt)

            lower = self.model.lowerPositionLimit
            upper = self.model.upperPositionLimit
            q = np.clip(q, lower, upper)

        return {
            'time': time_steps,
            'q': q_traj,
            'dq': dq_traj,
            'ddq': ddq_traj,
            'tau': tau_traj,
        }

    def simulate_constant_torque(
        self,
        q0: np.ndarray,
        dq0: np.ndarray,
        tau: np.ndarray,
        duration: float,
        dt: float = 0.001,
        friction: Optional[np.ndarray] = None,
    ) -> dict:
        tau = np.asarray(tau, dtype=float)

        def torque_func(t, q, dq):
            return tau

        return self.simulate(q0, dq0, torque_func, duration, dt, friction)

    def simulate_pd_control(
        self,
        q0: np.ndarray,
        dq0: np.ndarray,
        target_q: np.ndarray,
        kp: np.ndarray,
        kd: np.ndarray,
        duration: float,
        dt: float = 0.001,
        friction: Optional[np.ndarray] = None,
        feedforward_tau: Optional[np.ndarray] = None,
    ) -> dict:
        target_q = np.asarray(target_q, dtype=float)
        kp = np.asarray(kp, dtype=float)
        kd = np.asarray(kd, dtype=float)

        if feedforward_tau is not None:
            feedforward_tau = np.asarray(feedforward_tau, dtype=float)

        def torque_func(t, q, dq):
            error = target_q - q
            tau = kp * error - kd * dq
            if feedforward_tau is not None:
                tau += feedforward_tau
            return tau

        return self.simulate(q0, dq0, torque_func, duration, dt, friction)

    def simulate_trajectory_tracking(
        self,
        q0: np.ndarray,
        dq0: np.ndarray,
        q_trajectory: np.ndarray,
        dq_trajectory: np.ndarray,
        ddq_trajectory: np.ndarray,
        time_steps: np.ndarray,
        kp: np.ndarray,
        kd: np.ndarray,
        dt: float = 0.001,
        friction: Optional[np.ndarray] = None,
        use_feedforward: bool = True,
    ) -> dict:
        q0 = np.asarray(q0, dtype=float)
        dq0 = np.asarray(dq0, dtype=float)
        kp = np.asarray(kp, dtype=float)
        kd = np.asarray(kd, dtype=float)

        def torque_func(t, q, dq):
            idx = np.searchsorted(time_steps, t)
            idx = min(idx, len(q_trajectory) - 1)

            q_des = q_trajectory[idx]
            dq_des = dq_trajectory[idx]
            ddq_des = ddq_trajectory[idx]

            error = q_des - q
            derror = dq_des - dq

            tau = kp * error + kd * derror

            if use_feedforward:
                M = self.compute_mass_matrix(q)
                h = self.compute_coriolis_vector(q, dq)
                tau += M @ ddq_des + h

            return tau

        duration = time_steps[-1]
        return self.simulate(q0, dq0, torque_func, duration, dt, friction)

    def compute_joint_torque_limits(self) -> Tuple[np.ndarray, np.ndarray]:
        torque_limits = np.ones(self.nv) * 100.0
        return -torque_limits, torque_limits

    def check_torque_limits(self, tau: np.ndarray) -> bool:
        tau = np.asarray(tau, dtype=float)
        lower, upper = self.compute_joint_torque_limits()
        return np.all(tau >= lower) and np.all(tau <= upper)

    def compute_kinetic_energy(self, q: np.ndarray, dq: np.ndarray) -> float:
        q = np.asarray(q, dtype=float)
        dq = np.asarray(dq, dtype=float)
        return pin.computeKineticEnergy(self.model, self.data, q, dq)

    def compute_potential_energy(self, q: np.ndarray) -> float:
        q = np.asarray(q, dtype=float)
        return pin.computePotentialEnergy(self.model, self.data, q, self.gravity)

    def compute_total_energy(self, q: np.ndarray, dq: np.ndarray) -> float:
        return self.compute_kinetic_energy(q, dq) + self.compute_potential_energy(q)

    def compute_end_effector_wrench(
        self,
        q: np.ndarray,
        dq: np.ndarray,
        ddq: np.ndarray,
    ) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        dq = np.asarray(dq, dtype=float)
        ddq = np.asarray(ddq, dtype=float)

        J = self.robot.jacobian_geometric(q)
        tau = self.compute_inverse_dynamics(q, dq, ddq)
        wrench = np.linalg.pinv(J).T @ tau
        return wrench

    def compute_torque_from_wrench(
        self,
        q: np.ndarray,
        wrench: np.ndarray,
    ) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        wrench = np.asarray(wrench, dtype=float)
        J = self.robot.jacobian_geometric(q)
        return J.T @ wrench

    def add_gravity_compensation(
        self,
        q: np.ndarray,
        base_torque: np.ndarray,
    ) -> np.ndarray:
        q = np.asarray(q, dtype=float)
        base_torque = np.asarray(base_torque, dtype=float)
        g = self.compute_gravity_vector(q)
        return base_torque + g
