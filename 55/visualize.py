import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib import cm
import gc


class PSOVisualizer:
    def __init__(self, fitness_func, bounds, func_name='test_function', optimal_x=None):
        self.fitness_func = fitness_func
        self.bounds = bounds
        self.func_name = func_name
        self.optimal_x = optimal_x

        self.x_min, self.x_max = bounds[0]
        self.y_min, self.y_max = bounds[1]

        self._prepare_contour_data()

    def _prepare_contour_data(self, grid_size=100):
        self.X, self.Y = np.meshgrid(
            np.linspace(self.x_min, self.x_max, grid_size),
            np.linspace(self.y_min, self.y_max, grid_size)
        )
        self.Z = np.zeros_like(self.X)
        for i in range(self.X.shape[0]):
            for j in range(self.X.shape[1]):
                self.Z[i, j] = self.fitness_func(np.array([self.X[i, j], self.Y[i, j]]))

    def plot_contour(self, ax=None, levels=20, cmap='viridis'):
        created_fig = False
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 8))
            created_fig = True

        contour = ax.contour(self.X, self.Y, self.Z, levels=levels, cmap=cmap, alpha=0.7)
        ax.contourf(self.X, self.Y, self.Z, levels=levels, cmap=cmap, alpha=0.5)
        plt.colorbar(contour, ax=ax)

        if self.optimal_x is not None:
            ax.plot(self.optimal_x[0], self.optimal_x[1], 'r*', markersize=15, label='Global Optimum')

        ax.set_xlabel('x1')
        ax.set_ylabel('x2')
        ax.set_title(f'{self.func_name} - Contour Plot')
        ax.set_xlim(self.x_min, self.x_max)
        ax.set_ylim(self.y_min, self.y_max)

        if created_fig:
            return fig, ax
        return ax

    def plot_surface(self, ax=None, cmap='viridis'):
        created_fig = False
        if ax is None:
            fig = plt.figure(figsize=(10, 8))
            ax = fig.add_subplot(111, projection='3d')
            created_fig = True

        surface = ax.plot_surface(self.X, self.Y, self.Z, cmap=cmap, alpha=0.7, linewidth=0)
        plt.colorbar(surface, ax=ax)

        if self.optimal_x is not None:
            optimal_z = self.fitness_func(self.optimal_x)
            ax.scatter(self.optimal_x[0], self.optimal_x[1], optimal_z,
                       color='red', s=200, marker='*', label='Global Optimum')

        ax.set_xlabel('x1')
        ax.set_ylabel('x2')
        ax.set_zlabel('f(x)')
        ax.set_title(f'{self.func_name} - 3D Surface Plot')

        if created_fig:
            return fig, ax
        return ax

    def create_animation(self, history, save_path=None, fps=5, show_velocity=False):
        particles_history = history['particles_position']
        gbest_history = history['gbest_position']
        gbest_fitness_history = history['gbest_fitness']

        fig, ax = plt.subplots(figsize=(10, 8))

        self.plot_contour(ax)

        particles_scat = ax.scatter([], [], c='blue', s=50, alpha=0.7, label='Particles')
        gbest_scat = ax.scatter([], [], c='red', s=100, marker='o', label='Global Best')

        if self.optimal_x is not None:
            ax.plot(self.optimal_x[0], self.optimal_x[1], 'r*', markersize=15, label='Global Optimum')

        ax.legend(loc='upper right')

        iter_text = ax.text(0.02, 0.98, '', transform=ax.transAxes,
                            verticalalignment='top', fontsize=12,
                            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        def init():
            particles_scat.set_offsets(np.empty((0, 2)))
            gbest_scat.set_offsets(np.empty((0, 2)))
            iter_text.set_text('')
            return particles_scat, gbest_scat, iter_text

        def update(frame):
            positions = particles_history[frame]
            particles_scat.set_offsets(positions)

            gbest_pos = gbest_history[frame]
            gbest_scat.set_offsets([gbest_pos])

            iter_text.set_text(
                f'Iteration: {frame + 1}/{len(particles_history)}\n'
                f'Best Fitness: {gbest_fitness_history[frame]:.6f}'
            )

            return particles_scat, gbest_scat, iter_text

        anim = FuncAnimation(
            fig, update, frames=len(particles_history),
            init_func=init, blit=True, interval=1000 / fps, repeat=True
        )

        if save_path is not None:
            anim.save(save_path, writer='pillow', fps=fps)

        if hasattr(self, '_anim'):
            del self._anim
            plt.close(self._anim_fig)
        self._anim = anim
        self._anim_fig = fig
        self._anim.pause = self._pause_animation
        self._anim.resume = self._resume_animation

        return anim

    def _pause_animation(self):
        if hasattr(self, '_anim') and self._anim is not None:
            self._anim.event_source.stop()

    def _resume_animation(self):
        if hasattr(self, '_anim') and self._anim is not None:
            self._anim.event_source.start()

    def cleanup(self):
        if hasattr(self, '_anim'):
            del self._anim
        if hasattr(self, '_anim_fig'):
            plt.close(self._anim_fig)
            del self._anim_fig
        plt.close('all')
        gc.collect()

    def plot_convergence(self, history, ax=None):
        created_fig = False
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
            created_fig = True

        fitness_history = history['gbest_fitness']
        iterations = range(1, len(fitness_history) + 1)

        ax.plot(iterations, fitness_history, 'b-', linewidth=2, label='Global Best Fitness')
        ax.set_xlabel('Iteration')
        ax.set_ylabel('Fitness')
        ax.set_title(f'{self.func_name} - Convergence Curve')
        ax.set_yscale('log' if min(fitness_history) > 0 else 'linear')
        ax.grid(True, alpha=0.3)
        ax.legend()

        if created_fig:
            return fig, ax
        return ax


def run_and_visualize(
    func_name='sphere',
    n_particles=30,
    max_iter=50,
    w=0.7,
    c1=1.49,
    c2=1.49,
    random_state=42,
    save_animation=False,
    show_plots=True,
    show_animation=False
):
    from objective import TEST_FUNCTIONS
    from pso import PSO

    func_info = TEST_FUNCTIONS[func_name]

    pso = PSO(
        fitness_func=func_info['function'],
        dim=2,
        bounds=func_info['bounds'],
        n_particles=n_particles,
        max_iter=max_iter,
        w=w,
        c1=c1,
        c2=c2,
        random_state=random_state
    )

    best_position, best_fitness = pso.optimize(verbose=True)
    history = pso.get_history()

    print(f"\nResults for {func_name}:")
    print(f"Best Position: {best_position}")
    print(f"Best Fitness: {best_fitness}")
    print(f"Optimal Position: {func_info['optimal_x']}")
    print(f"Optimal Fitness: {func_info['optimal']}")

    visualizer = PSOVisualizer(
        fitness_func=func_info['function'],
        bounds=func_info['bounds'],
        func_name=func_name,
        optimal_x=func_info['optimal_x']
    )

    anim = None
    try:
        if show_plots:
            fig = plt.figure(figsize=(16, 12))

            ax1 = fig.add_subplot(2, 2, 1)
            visualizer.plot_contour(ax1)

            ax2 = fig.add_subplot(2, 2, 2, projection='3d')
            visualizer.plot_surface(ax2)

            ax3 = fig.add_subplot(2, 2, 3)
            visualizer.plot_convergence(history, ax3)

            plt.tight_layout()
            plt.show()
            plt.close(fig)
            del fig
            gc.collect()

        anim = visualizer.create_animation(
            history,
            save_path=f'{func_name}_pso.gif' if save_animation else None,
            fps=5
        )

        if show_animation and anim is not None:
            plt.show()
    finally:
        if not save_animation and not show_animation:
            visualizer.cleanup()
        gc.collect()

    return best_position, best_fitness, history, anim


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='PSO Algorithm Visualization')
    parser.add_argument('--func', type=str, default='sphere',
                        help='Test function name (e.g., sphere, rosenbrock, rastrigin)')
    parser.add_argument('--particles', type=int, default=30, help='Number of particles')
    parser.add_argument('--iterations', type=int, default=50, help='Maximum iterations')
    parser.add_argument('--save', action='store_true', help='Save animation as GIF')
    parser.add_argument('--no-show', action='store_true', help='Do not show plots')
    parser.add_argument('--show-animation', action='store_true', help='Show particle animation')

    args = parser.parse_args()

    run_and_visualize(
        func_name=args.func,
        n_particles=args.particles,
        max_iter=args.iterations,
        save_animation=args.save,
        show_plots=not args.no_show,
        show_animation=args.show_animation
    )
