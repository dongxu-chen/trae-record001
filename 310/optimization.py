import numpy as np
from copy import deepcopy
from ray_tracer import RayTracer, ImageAnalysis
from optical_constants import DEFAULT_WAVELENGTHS_ABERRATION
from lens import ThickLens, DoubletLens


class LensOptimizer:
    def __init__(self, optical_system, parameters=None, target_focal_length=100.0):
        self.optical_system = optical_system
        self.original_system = deepcopy(optical_system)
        self.ray_tracer = RayTracer(optical_system)
        self.analysis = ImageAnalysis(optical_system, self.ray_tracer)
        self.parameters = parameters or []
        self.target_focal_length = target_focal_length
        self.history = []

    def add_parameter(self, element_index, parameter_name, min_value=None,
                        max_value=None, step=0.1):
        param = {
            'element_index': element_index,
            'parameter_name': parameter_name,
            'min': min_value,
            'max': max_value,
            'step': step
        }
        self.parameters.append(param)
        return len(self.parameters) - 1

    def get_parameter_value(self, param_idx):
        param = self.parameters[param_idx]
        element = self.optical_system.elements[param['element_index']]
        return getattr(element, param['parameter_name'])

    def set_parameter_value(self, param_idx, value):
        param = self.parameters[param_idx]
        if param['min'] is not None:
            value = max(value, param['min'])
        if param['max'] is not None:
            value = min(value, param['max'])
        element = self.optical_system.elements[param['element_index']]
        setattr(element, param['parameter_name'], value)

    def get_all_parameters(self):
        values = []
        for i in range(len(self.parameters)):
            values.append(self.get_parameter_value(i))
        return np.array(values)

    def set_all_parameters(self, values):
        for i, v in enumerate(values):
            self.set_parameter_value(i, v)

    def evaluate_merit_function(self, verbose=False):
        try:
            self._update_image_plane()
            merit = 0.0
            weights = {}
            if self.target_focal_length is not None:
                f = self.ray_tracer.get_focal_length(wavelength=0.587)
                if f is not None:
                    focal_error = (f - self.target_focal_length) ** 2
                    merit += 10.0 * focal_error
                    weights['focal_length'] = focal_error * 10.0
            sa = self.analysis.calculate_spherical_aberration(
                wavelength=0.587, max_height=10.0, num_rays=21)
            if sa is not None:
                sa_error = (sa * 1000) ** 2
                merit += 5.0 * sa_error
                weights['spherical_aberration'] = sa_error * 5.0
            ca = self.analysis.calculate_chromatic_aberration(
                wavelengths=DEFAULT_WAVELENGTHS_ABERRATION,
                max_height=0.1, num_rays=11)
            ca_error = (ca * 1000) ** 2
            merit += 8.0 * ca_error
            weights['chromatic_aberration'] = ca_error * 8.0
            _, _, distortion = self.analysis.calculate_distortion(
                wavelength=0.587, max_height=10.0)
            max_dist = np.max(np.abs(distortion)) if len(distortion) > 0 else 0
            dist_error = max_dist ** 2
            merit += 2.0 * dist_error
            weights['distortion'] = dist_error * 2.0
            spot_data = self.analysis.get_spot_diagram(
                object_height=0.0, wavelengths=[0.587],
                num_rays=50, max_height=10.0)
            rms = self.analysis.calculate_rms_spot_size(spot_data, 0.587)
            rms_error = (rms * 1000) ** 2
            merit += 3.0 * rms_error
            weights['rms_spot'] = rms_error * 3.0
            if verbose:
                print(f"  Merit breakdown:")
                for k, v in weights.items():
                    print(f"    {k}: {v:.6f}")
                print(f"  Total merit: {merit:.6f}")
            return merit
        except Exception as e:
            if verbose:
                print(f"  Error in merit function: {e}")
            return 1e10

    def _update_image_plane(self):
        z_min, z_max = self.optical_system.get_z_extent()
        best_z, _, _, _ = self.ray_tracer.find_best_image_plane(
            wavelength=0.587, z_min=z_max + 10, z_max=z_max + 200,
            num_points=20, object_height=0.0,
            max_height=10.0, num_rays=11)
        self.optical_system.set_image_plane(best_z, size=50)

    def calculate_jacobian(self, param_indices=None, delta=1e-4):
        if param_indices is None:
            param_indices = list(range(len(self.parameters)))
        n_params = len(param_indices)
        original_values = self.get_all_parameters()
        J = np.zeros(n_params)
        base_merit = self.evaluate_merit_function()
        for i, idx in enumerate(param_indices):
            step = max(abs(original_values[idx]) * delta, delta) if abs(original_values[idx]) > 1e-6 else delta
            self.set_parameter_value(idx, original_values[idx] + step)
            merit_plus = self.evaluate_merit_function()
            self.set_parameter_value(idx, original_values[idx] - step)
            merit_minus = self.evaluate_merit_function()
            J[i] = (merit_plus - merit_minus) / (2 * step)
            self.set_parameter_value(idx, original_values[idx])
        return J, base_merit

    def optimize_damped_least_squares(self, max_iterations=50,
                                        initial_damping=1e-3,
                                        damping_factor=10.0,
                                        tol=1e-6,
                                        verbose=True):
        if len(self.parameters) == 0:
            raise ValueError("No parameters defined for optimization")
        self.history = []
        current_params = self.get_all_parameters()
        best_params = current_params.copy()
        best_merit = self.evaluate_merit_function(verbose=verbose)
        damping = initial_damping
        if verbose:
            print(f"Initial merit: {best_merit:.6f}")
            print(f"Initial parameters: {current_params}")
        for iteration in range(max_iterations):
            if verbose:
                print(f"\nIteration {iteration + 1}/{max_iterations}")
            J, _ = self.calculate_jacobian(delta=1e-4)
            JTJ = np.outer(J, J) if len(J) > 1 else np.array([[J[0]**2]])
            I = np.eye(len(J))
            try:
                delta_params = -np.linalg.solve(JTJ + damping * I, J)
            except np.linalg.LinAlgError:
                delta_params = -J / (np.sum(J**2) + damping)
            new_params = current_params + delta_params
            self.set_all_parameters(new_params)
            new_merit = self.evaluate_merit_function(verbose=verbose)
            if new_merit < best_merit:
                if verbose:
                    print(f"  Improvement: {best_merit:.6f} -> {new_merit:.6f}")
                    print(f"  Damping: {damping:.2e}")
                best_merit = new_merit
                best_params = new_params.copy()
                current_params = new_params.copy()
                damping /= damping_factor
                improvement = best_merit - new_merit
                if improvement < tol and iteration > 5:
                    if verbose:
                        print(f"  Converged (improvement < {improvement:.2e}")
                    break
            else:
                if verbose:
                    print(f"  No improvement, increasing damping to {damping * damping_factor:.2e}")
                damping *= damping_factor
                self.set_all_parameters(current_params)
            self.history.append({
                'iteration': iteration,
                'merit': best_merit,
                'parameters': current_params.copy(),
                'damping': damping
            })
            if damping > 1e10:
                if verbose:
                    print("  Damping too large, stopping")
                break
        self.set_all_parameters(best_params)
        self._update_image_plane()
        if verbose:
            print(f"\nOptimization complete!")
            print(f"Final merit: {best_merit:.6f}")
            print(f"Final parameters: {best_params}")
        return best_params, best_merit

    def optimize_gradient_descent(self, max_iterations=100,
                                    learning_rate=1e-5,
                                    tol=1e-6, verbose=True):
        if len(self.parameters) == 0:
            raise ValueError("No parameters defined for optimization")
        self.history = []
        current_params = self.get_all_parameters()
        best_params = current_params.copy()
        best_merit = self.evaluate_merit_function(verbose=verbose)
        if verbose:
            print(f"Initial merit: {best_merit:.6f}")
        for iteration in range(max_iterations):
            if verbose:
                print(f"\nIteration {iteration + 1}/{max_iterations}")
            J, _ = self.calculate_jacobian(delta=1e-4)
            new_params = current_params - learning_rate * J
            self.set_all_parameters(new_params)
            new_merit = self.evaluate_merit_function(verbose=verbose)
            if new_merit < best_merit:
                if verbose:
                    print(f"  Improvement: {best_merit:.6f} -> {new_merit:.6f}")
                best_merit = new_merit
                best_params = new_params.copy()
                current_params = new_params.copy()
                improvement = best_merit - new_merit
                if improvement < tol and iteration > 10:
                    if verbose:
                        print(f"  Converged")
                    break
            else:
                if verbose:
                    print(f"  No improvement, reducing learning rate")
                learning_rate *= 0.5
                self.set_all_parameters(current_params)
            self.history.append({
                'iteration': iteration,
                'merit': best_merit,
                'parameters': current_params.copy(),
                'learning_rate': learning_rate
            })
            if learning_rate < 1e-10:
                break
        self.set_all_parameters(best_params)
        self._update_image_plane()
        return best_params, best_merit

    def plot_convergence(self, ax=None):
        if len(self.history) == 0:
            return ax
        if ax is None:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(10, 6))
        iterations = [h['iteration'] for h in self.history]
        merits = [h['merit'] for h in self.history]
        ax.semilogy(iterations, merits, 'o-', linewidth=2, markersize=6)
        ax.set_xlabel('Iteration', fontsize=12)
        ax.set_ylabel('Merit Function Value', fontsize=12)
        ax.set_title('Optimization Convergence', fontsize=14)
        ax.grid(True, alpha=0.3)
        return ax

    def compare_before_after(self, ax=None):
        if ax is None:
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(10, 6))
        original_params = []
        optimized_params = []
        param_names = []
        for i, param in enumerate(self.parameters):
            element = self.original_system.elements[param['element_index']]
            original_val = getattr(element, param['parameter_name'])
            optimized_val = self.get_parameter_value(i)
            original_params.append(original_val)
            optimized_params.append(optimized_val)
            param_names.append(f"Elem{param['element_index']}\n{param['parameter_name']}")
        x = np.arange(len(param_names))
        width = 0.35
        ax.bar(x - width/2, original_params, width, label='Original', alpha=0.7)
        ax.bar(x + width/2, optimized_params, width, label='Optimized', alpha=0.7)
        ax.set_xticks(x)
        ax.set_xticklabels(param_names, fontsize=10)
        ax.set_ylabel('Parameter Value', fontsize=12)
        ax.set_title('Parameter Comparison', fontsize=14)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        return ax


def setup_singlet_optimizer(focal_length=100.0, material='BK7'):
    from lens import LensSystem, create_singlet_lens
    system = LensSystem('Singlet_Optimization')
    lens = create_singlet_lens(focal_length=focal_length, z_position=0,
                            thickness=8.0, material=material,
                            aperture_radius=15.0)
    for surf in lens.get_surfaces():
        system.add_element(surf)
    system.set_image_plane(focal_length + 10, size=20)
    optimizer = LensOptimizer(system, target_focal_length=focal_length)
    optimizer.add_parameter(0, 'radius_of_curvature', min_value=20.0, max_value=200.0)
    optimizer.add_parameter(1, 'radius_of_curvature', min_value=-200.0, max_value=-20.0)
    return optimizer


def setup_doublet_optimizer(focal_length=100.0):
    from lens import LensSystem, create_achromatic_doublet
    system = LensSystem('Doublet_Optimization')
    doublet = create_achromatic_doublet(focal_length=focal_length, z_position=0,
                                     thickness1=8.0, thickness2=4.0,
                                     material1='BK7', material2='SF11',
                                     aperture_radius=15.0)
    for surf in doublet.get_surfaces():
        system.add_element(surf)
    system.set_image_plane(focal_length + 10, size=20)
    optimizer = LensOptimizer(system, target_focal_length=focal_length)
    for i in range(3):
        optimizer.add_parameter(i, 'radius_of_curvature',
                                 min_value=-300.0 if i > 0 else 20.0,
                                 max_value=-20.0 if i == 1 else 300.0)
    return optimizer
