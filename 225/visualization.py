import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import threading
import queue
import time
from matplotlib.colors import Normalize


class AsyncFluidVisualizer:
    def __init__(self, lbm, interval=50, steps_per_update=10, 
                 tracer=None, show_particles=True, show_temperature=True):
        self.lbm = lbm
        self.interval = interval
        self.steps_per_update = steps_per_update
        self.tracer = tracer
        self.show_particles = show_particles
        self.show_temperature = show_temperature and lbm.enable_temperature
        
        self.data_queue = queue.Queue(maxsize=2)
        self.particle_queue = queue.Queue(maxsize=2)
        self.running = False
        self.paused = False
        self.compute_thread = None
        
        self.fig = None
        self.ani = None
        self.current_data = None
        self.current_particles = None
        
        self.scatter = None
        self.trails = []
    
    def compute_loop(self):
        while self.running:
            if not self.paused:
                for _ in range(self.steps_per_update):
                    self.lbm.step()
                
                if self.tracer is not None:
                    self.tracer.update(dt=1.0)
                
                field_data = self.lbm.get_field_data()
                
                try:
                    self.data_queue.put_nowait(field_data)
                except queue.Full:
                    try:
                        self.data_queue.get_nowait()
                        self.data_queue.put_nowait(field_data)
                    except queue.Empty:
                        pass
                
                if self.tracer is not None:
                    particle_data = {
                        'positions': self.tracer.get_positions(),
                        'history': self.tracer.get_history()
                    }
                    try:
                        self.particle_queue.put_nowait(particle_data)
                    except queue.Full:
                        try:
                            self.particle_queue.get_nowait()
                            self.particle_queue.put_nowait(particle_data)
                        except queue.Empty:
                            pass
            
            time.sleep(0.001)
    
    def start_compute(self):
        self.running = True
        self.compute_thread = threading.Thread(target=self.compute_loop, daemon=True)
        self.compute_thread.start()
    
    def stop_compute(self):
        self.running = False
        if self.compute_thread:
            self.compute_thread.join(timeout=1.0)
    
    def setup_thermal_plot(self):
        n_plots = 3 if self.show_temperature else 2
        self.fig, self.axes = plt.subplots(n_plots, 2, figsize=(14, 4 * n_plots))
        self.fig.suptitle('Thermal LBM Simulation', fontsize=14)
        
        ny, nx = self.lbm.ny, self.lbm.nx
        
        row = 0
        self.im_vel = self.axes[row, 0].imshow(
            np.zeros((ny, nx)),
            cmap='jet', origin='lower', aspect='auto'
        )
        self.axes[row, 0].set_title('Velocity Magnitude')
        plt.colorbar(self.im_vel, ax=self.axes[row, 0])
        
        self.im_vort = self.axes[row, 1].imshow(
            np.zeros((ny, nx)),
            cmap='RdBu', origin='lower', aspect='auto'
        )
        self.axes[row, 1].set_title('Vorticity')
        plt.colorbar(self.im_vort, ax=self.axes[row, 1])
        
        row = 1
        if self.show_temperature:
            self.im_temp = self.axes[row, 0].imshow(
                np.zeros((ny, nx)),
                cmap='hot', origin='lower', aspect='auto'
            )
            self.axes[row, 0].set_title('Temperature')
            plt.colorbar(self.im_temp, ax=self.axes[row, 0])
            
            self.im_temp_grad = self.axes[row, 1].imshow(
                np.zeros((ny, nx)),
                cmap='coolwarm', origin='lower', aspect='auto'
            )
            self.axes[row, 1].set_title('Temperature Gradient')
            plt.colorbar(self.im_temp_grad, ax=self.axes[row, 1])
            row += 1
        
        if self.tracer is not None and self.show_particles:
            self.ax_particles = self.axes[row, 0]
            self.ax_particles.set_title('Particle Tracer')
            self.ax_particles.set_xlim(0, nx)
            self.ax_particles.set_ylim(0, ny)
            
            self.scatter = self.ax_particles.scatter([], [], s=3, c='red', alpha=0.7)
            
            self.ax_stream = self.axes[row, 1]
            self.ax_stream.set_title('Streamlines with Particles')
            self.ax_stream.set_xlim(0, nx)
            self.ax_stream.set_ylim(0, ny)
        
        obstacle_mask = np.ma.masked_where(~self.lbm.obstacle, self.lbm.obstacle)
        for ax in self.axes.flat:
            ax.imshow(obstacle_mask, cmap='gray', origin='lower', aspect='auto', alpha=0.5)
        
        self.text = self.fig.text(0.02, 0.98, '', transform=self.fig.transFigure, 
                                  verticalalignment='top')
        
        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        self.fig.canvas.mpl_connect('close_event', self.on_close)
        plt.tight_layout()
    
    def setup_streamline_plot(self):
        self.fig, self.ax = plt.subplots(figsize=(12, 6))
        self.fig.suptitle('LBM Flow Streamlines', fontsize=14)
        
        self.text = self.fig.text(0.02, 0.98, '', transform=self.fig.transFigure,
                                  verticalalignment='top')
        
        self.ax.set_xlim(0, self.lbm.nx)
        self.ax.set_ylim(0, self.lbm.ny)
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_title('Flow Streamlines')
        
        if self.tracer is not None and self.show_particles:
            self.scatter = self.ax.scatter([], [], s=5, c='red', alpha=0.8)
        
        self.fig.canvas.mpl_connect('button_press_event', self.on_click)
        self.fig.canvas.mpl_connect('close_event', self.on_close)
        plt.tight_layout()
    
    def update_thermal(self, frame):
        try:
            self.current_data = self.data_queue.get_nowait()
        except queue.Empty:
            pass
        
        try:
            self.current_particles = self.particle_queue.get_nowait()
        except queue.Empty:
            pass
        
        if self.current_data is None:
            return []
        
        u = self.current_data['u'][0]
        v = self.current_data['u'][1]
        step = self.current_data['step']
        obstacle = self.current_data['obstacle']
        
        vel_mag = np.sqrt(u**2 + v**2)
        
        dvdx = np.gradient(v, axis=1)
        dudy = np.gradient(u, axis=0)
        vort = dvdx - dudy
        
        self.im_vel.set_data(vel_mag)
        self.im_vel.set_clim(vmin=0, vmax=vel_mag.max() + 1e-10)
        
        self.im_vort.set_data(vort)
        vort_max = max(abs(vort.min()), abs(vort.max())) + 1e-10
        self.im_vort.set_clim(vmin=-vort_max, vmax=vort_max)
        
        if self.show_temperature and 'T' in self.current_data:
            T = self.current_data['T']
            self.im_temp.set_data(T)
            self.im_temp.set_clim(vmin=T.min(), vmax=T.max())
            
            dTdx = np.gradient(T, axis=1)
            dTdy = np.gradient(T, axis=0)
            temp_grad = np.sqrt(dTdx**2 + dTdy**2)
            self.im_temp_grad.set_data(temp_grad)
            self.im_temp_grad.set_clim(vmin=0, vmax=temp_grad.max() + 1e-10)
        
        if self.tracer is not None and self.show_particles and self.current_particles is not None:
            positions = self.current_particles['positions']
            self.scatter.set_offsets(positions)
            
            Y, X = np.mgrid[0:self.lbm.ny, 0:self.lbm.nx]
            mask = ~obstacle
            u_masked = np.ma.masked_where(~mask, u)
            v_masked = np.ma.masked_where(~mask, v)
            
            self.ax_stream.clear()
            obstacle_mask = np.ma.masked_where(~obstacle, obstacle)
            self.ax_stream.imshow(obstacle_mask, cmap='gray', origin='lower', aspect='auto', alpha=0.5)
            self.ax_stream.streamplot(X, Y, u_masked, v_masked, density=1.5, color='blue', linewidth=0.5)
            self.ax_stream.scatter(positions[:, 0], positions[:, 1], s=3, c='red', alpha=0.7)
            self.ax_stream.set_xlim(0, self.lbm.nx)
            self.ax_stream.set_ylim(0, self.lbm.ny)
            self.ax_stream.set_title('Streamlines with Particles')
        
        nu = (self.lbm.tau - 0.5) / 3.0
        u_avg = np.sqrt(np.mean(u**2 + v**2))
        re = u_avg * self.lbm.ny / nu
        
        self.text.set_text(
            f'Step: {step} | Re: {re:.1f} | CFL: {self.lbm.cfl_max:.2f} | '
            f'dt: {self.current_data["dt"]:.4f} | {"PAUSED" if self.paused else "RUNNING"}'
        )
        
        return []
    
    def update_streamline(self, frame):
        try:
            self.current_data = self.data_queue.get_nowait()
        except queue.Empty:
            pass
        
        try:
            self.current_particles = self.particle_queue.get_nowait()
        except queue.Empty:
            pass
        
        if self.current_data is None:
            return []
        
        u = self.current_data['u'][0]
        v = self.current_data['u'][1]
        step = self.current_data['step']
        obstacle = self.current_data['obstacle']
        
        vel_mag = np.sqrt(u**2 + v**2)
        
        self.ax.clear()
        
        Y, X = np.mgrid[0:self.lbm.ny, 0:self.lbm.nx]
        mask = ~obstacle
        
        u_masked = np.ma.masked_where(~mask, u)
        v_masked = np.ma.masked_where(~mask, v)
        vel_masked = np.ma.masked_where(~mask, vel_mag)
        
        obstacle_mask = np.ma.masked_where(~obstacle, obstacle)
        self.ax.imshow(obstacle_mask, cmap='gray', origin='lower', aspect='auto', alpha=0.8)
        
        if self.show_temperature and 'T' in self.current_data:
            T = self.current_data['T']
            T_masked = np.ma.masked_where(~mask, T)
            im = self.ax.imshow(T_masked, cmap='hot', origin='lower', 
                                aspect='auto', alpha=0.3, 
                                norm=Normalize(vmin=T.min(), vmax=T.max()))
            if not hasattr(self, 'cbar'):
                self.cbar = plt.colorbar(im, ax=self.ax, label='Temperature')
        
        self.ax.streamplot(X, Y, u_masked, v_masked,
                           density=2, linewidth=1, 
                           color=vel_masked, cmap='jet',
                           norm=Normalize(vmin=0, vmax=vel_mag.max() + 1e-10))
        
        if self.tracer is not None and self.show_particles and self.current_particles is not None:
            positions = self.current_particles['positions']
            self.ax.scatter(positions[:, 0], positions[:, 1], s=8, c='white', 
                           edgecolors='black', alpha=0.8, zorder=5)
            
            history = self.current_particles['history']
            if history is not None and len(history) > 1:
                for i in range(min(50, self.tracer.n_particles)):
                    self.ax.plot(history[:, i, 0], history[:, i, 1], 
                                '-', linewidth=0.5, alpha=0.3, color='white')
        
        nu = (self.lbm.tau - 0.5) / 3.0
        u_avg = np.sqrt(np.mean(u**2 + v**2))
        re = u_avg * self.lbm.ny / nu
        
        temp_info = ''
        if self.show_temperature and 'T' in self.current_data:
            T = self.current_data['T']
            temp_info = f' | T_range: [{T.min():.2f}, {T.max():.2f}]'
        
        self.text.set_text(
            f'Step: {step} | Re: {re:.1f} | Max Vel: {vel_mag.max():.4f} | '
            f'CFL: {self.lbm.cfl_max:.2f} | {"PAUSED" if self.paused else "RUNNING"}' + temp_info
        )
        
        self.ax.set_xlim(0, self.lbm.nx)
        self.ax.set_ylim(0, self.lbm.ny)
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_title('Flow Streamlines')
        
        return [self.text]
    
    def on_click(self, event):
        if event.button == 1:
            self.paused = not self.paused
    
    def on_close(self, event):
        self.stop_compute()
    
    def animate(self, mode='thermal'):
        if mode == 'thermal':
            self.setup_thermal_plot()
            update_func = self.update_thermal
        elif mode == 'streamline':
            self.setup_streamline_plot()
            update_func = self.update_streamline
        else:
            raise ValueError(f"Unknown mode: {mode}")
        
        self.start_compute()
        
        self.ani = FuncAnimation(self.fig, update_func, 
                                 interval=self.interval, blit=False)
        plt.show()
    
    def save_snapshot(self, filename='snapshot.png'):
        self.fig.savefig(filename, dpi=150, bbox_inches='tight')
        print(f'Snapshot saved to {filename}')
