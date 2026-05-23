import numpy as np
import matplotlib.pyplot as plt
import pickle
import os
from datetime import datetime
from lbm2d import LBM2D


class FlowClassifier:
    @staticmethod
    def classify_flow(u, v, obstacle, threshold_steady=0.01, threshold_vort=0.5):
        ny, nx = u.shape
        
        vel_mag = np.sqrt(u**2 + v**2)
        
        dvdx = np.gradient(v, axis=1)
        dudy = np.gradient(u, axis=0)
        vorticity = dvdx - dudy
        
        max_vort = np.max(np.abs(vorticity[~obstacle]))
        mean_vel = np.mean(vel_mag[~obstacle])
        
        if max_vort < threshold_vort:
            return 'Steady', 0.0
        else:
            downstream_mask = np.zeros_like(obstacle)
            cy = ny // 2
            downstream_mask[cy-10:cy+10, nx//2:] = True
            downstream_mask = downstream_mask & ~obstacle
            
            if np.sum(downstream_mask) > 0:
                vort_std = np.std(vorticity[downstream_mask])
                if vort_std > threshold_steady:
                    return 'Unsteady/Von Karman', vort_std
                else:
                    return 'Transitional', vort_std
            else:
                return 'Transitional', 0.0
    
    @staticmethod
    def compute_flow_stats(u, v, obstacle, char_length):
        ny, nx = u.shape
        
        vel_mag = np.sqrt(u**2 + v**2)
        
        dvdx = np.gradient(v, axis=1)
        dudy = np.gradient(u, axis=0)
        vorticity = dvdx - dudy
        
        max_vel = np.max(vel_mag)
        mean_vel = np.mean(vel_mag[~obstacle])
        max_vort = np.max(np.abs(vorticity[~obstacle]))
        mean_vort = np.mean(np.abs(vorticity[~obstacle]))
        
        nu = 1/6
        re = mean_vel * char_length / nu
        
        return {
            'max_velocity': max_vel,
            'mean_velocity': mean_vel,
            'max_vorticity': max_vort,
            'mean_vorticity': mean_vort,
            'reynolds': re
        }


class ParameterScanner:
    def __init__(self, output_dir='scan_results'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.results = []
        
    def run_scan(self, tau_values, re_values, nx=200, ny=100, 
                 obstacle_type='circle', obstacle_params=None,
                 n_steps=2000, sample_interval=100):
        if obstacle_params is None:
            obstacle_params = {'cx': 50, 'cy': 50, 'r': 15}
        
        total_runs = len(tau_values) * len(re_values)
        current_run = 0
        
        print(f"Starting parameter scan: {total_runs} total runs")
        print(f"Tau range: [{tau_values[0]}, {tau_values[-1]}]")
        print(f"Re range: [{re_values[0]}, {re_values[-1]}]")
        print()
        
        for tau in tau_values:
            for re in re_values:
                current_run += 1
                print(f"Run {current_run}/{total_runs}: tau={tau:.3f}, Re={re:.1f}")
                
                lbm = LBM2D(nx=nx, ny=ny, tau=tau, force=0.0, enable_temperature=False)
                
                if obstacle_type == 'circle':
                    lbm.add_circle(**obstacle_params)
                    char_length = obstacle_params.get('r', 15) * 2
                elif obstacle_type == 'rectangle':
                    lbm.add_rectangle(**obstacle_params)
                    char_length = obstacle_params.get('height', 20)
                
                lbm.set_reynolds(re, char_length)
                
                for step in range(n_steps):
                    lbm.step()
                    
                    if (step + 1) % sample_interval == 0:
                        stats = FlowClassifier.compute_flow_stats(
                            lbm.u[0], lbm.u[1], lbm.obstacle, char_length
                        )
                        flow_type, vort_std = FlowClassifier.classify_flow(
                            lbm.u[0], lbm.u[1], lbm.obstacle
                        )
                        
                        result = {
                            'tau': tau,
                            're_target': re,
                            're_actual': stats['reynolds'],
                            'step': step + 1,
                            'flow_type': flow_type,
                            'vort_std': vort_std,
                            'max_velocity': stats['max_velocity'],
                            'mean_velocity': stats['mean_velocity'],
                            'max_vorticity': stats['max_vorticity'],
                            'viscosity': lbm.get_viscosity()
                        }
                        self.results.append(result)
                
                print(f"  -> Flow type: {flow_type}, Re_actual: {stats['reynolds']:.1f}")
        
        print()
        print("Scan complete!")
        self.save_results()
        
        return self.results
    
    def save_results(self, filename=None):
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'param_scan_{timestamp}.pkl'
        
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'wb') as f:
            pickle.dump(self.results, f)
        
        print(f"Results saved to: {filepath}")
        return filepath
    
    def load_results(self, filepath):
        with open(filepath, 'rb') as f:
            self.results = pickle.load(f)
        print(f"Loaded {len(self.results)} results")
        return self.results
    
    def plot_phase_diagram(self, filename=None):
        if len(self.results) == 0:
            print("No results to plot")
            return
        
        taus = sorted(list(set([r['tau'] for r in self.results])))
        res = sorted(list(set([r['re_target'] for r in self.results])))
        
        flow_types = ['Steady', 'Transitional', 'Unsteady/Von Karman']
        color_map = {'Steady': 'blue', 'Transitional': 'green', 'Unsteady/Von Karman': 'red'}
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        for flow_type in flow_types:
            data = [r for r in self.results if r['flow_type'] == flow_type]
            if len(data) > 0:
                ax1.scatter([r['tau'] for r in data], 
                           [r['re_target'] for r in data],
                           c=color_map[flow_type], label=flow_type, s=100, alpha=0.7)
        
        ax1.set_xlabel('Tau (Relaxation Time)')
        ax1.set_ylabel('Target Reynolds Number')
        ax1.set_title('Flow Regime Phase Diagram')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        max_vort_data = np.array([[r['tau'], r['re_target'], r['max_vorticity']] 
                                  for r in self.results])
        sc = ax2.scatter(max_vort_data[:, 0], max_vort_data[:, 1], 
                        c=max_vort_data[:, 2], cmap='viridis', s=100)
        ax2.set_xlabel('Tau (Relaxation Time)')
        ax2.set_ylabel('Target Reynolds Number')
        ax2.set_title('Maximum Vorticity')
        plt.colorbar(sc, ax=ax2, label='Max Vorticity')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'phase_diagram_{timestamp}.png'
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        print(f"Phase diagram saved to: {filepath}")
        
        plt.close()
        return filepath
    
    def print_summary(self):
        if len(self.results) == 0:
            print("No results to summarize")
            return
        
        flow_type_counts = {}
        for r in self.results:
            ft = r['flow_type']
            flow_type_counts[ft] = flow_type_counts.get(ft, 0) + 1
        
        print()
        print("="*50)
        print("PARAMETER SCAN SUMMARY")
        print("="*50)
        print(f"Total simulations: {len(self.results)}")
        print()
        print("Flow type distribution:")
        for ft, count in flow_type_counts.items():
            pct = count / len(self.results) * 100
            print(f"  {ft}: {count} ({pct:.1f}%)")
        print()
        
        steady_results = [r for r in self.results if r['flow_type'] == 'Steady']
        unsteady_results = [r for r in self.results if r['flow_type'] == 'Unsteady/Von Karman']
        
        if len(steady_results) > 0:
            max_steady_re = max([r['re_target'] for r in steady_results])
            print(f"Maximum stable Re (Steady): {max_steady_re:.1f}")
        
        if len(unsteady_results) > 0:
            min_unsteady_re = min([r['re_target'] for r in unsteady_results])
            print(f"Critical Re (Onset of unsteadiness): ~{min_unsteady_re:.1f}")
        
        print("="*50)
        print()


def quick_scan():
    scanner = ParameterScanner()
    
    tau_values = np.linspace(0.55, 1.0, 5)
    re_values = np.linspace(50, 500, 10)
    
    results = scanner.run_scan(
        tau_values, re_values,
        nx=150, ny=75,
        obstacle_type='circle',
        obstacle_params={'cx': 40, 'cy': 37, 'r': 10},
        n_steps=1500,
        sample_interval=1500
    )
    
    scanner.print_summary()
    scanner.plot_phase_diagram()
    
    return scanner


if __name__ == '__main__':
    quick_scan()
