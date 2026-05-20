import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Circle


class FocalMechanism:
    def __init__(self, strike, dip, rake):
        self.strike = strike
        self.dip = dip
        self.rake = rake
        self.aux_plane = None
        self._calculate_auxiliary_plane()
    
    def _calculate_auxiliary_plane(self):
        s1 = np.radians(self.strike)
        d1 = np.radians(self.dip)
        r1 = np.radians(self.rake)
        
        n1z = np.sin(d1)
        n1n = -np.cos(d1) * np.cos(s1)
        n1e = -np.cos(d1) * np.sin(s1)
        
        d1z = np.sin(r1) * np.cos(d1)
        d1n = np.cos(r1) * np.sin(s1) - np.sin(r1) * np.sin(d1) * np.cos(s1)
        d1e = -np.cos(r1) * np.cos(s1) - np.sin(r1) * np.sin(d1) * np.sin(s1)
        
        n2n = d1n
        n2e = d1e
        n2z = d1z
        
        n2_norm = np.sqrt(n2n**2 + n2e**2 + n2z**2)
        if n2_norm > 0:
            n2n /= n2_norm
            n2e /= n2_norm
            n2z /= n2_norm
        
        s2 = np.arctan2(-n2e, n2n)
        d2 = np.arcsin(n2z)
        
        p1n = n1n
        p1e = n1e
        p1z = n1z
        
        cross_z = n2n * p1e - n2e * p1n
        cross_n = n2e * p1z - n2z * p1e
        cross_e = n2z * p1n - n2n * p1z
        
        r2 = np.arctan2(-cross_z, 
                        cross_n * np.cos(s2) + cross_e * np.sin(s2))
        
        s2 = np.degrees(s2)
        d2 = np.degrees(d2)
        r2 = np.degrees(r2)
        
        if s2 < 0:
            s2 += 360
        if d2 < 0:
            d2 = -d2
            s2 = (s2 + 180) % 360
            r2 = 180 - r2
        
        self.aux_plane = {
            'strike': s2,
            'dip': d2,
            'rake': r2
        }
    
    def get_t_axes(self):
        s1 = np.radians(self.strike)
        d1 = np.radians(self.dip)
        r1 = np.radians(self.rake)
        
        cos2r = np.cos(2 * r1)
        sin2r = np.sin(2 * r1)
        
        t_az = s1 + np.arctan2(sin2r * np.sin(d1), 
                                -cos2r * np.cos(s1) + sin2r * np.cos(d1) * np.sin(s1))
        t_pl = np.arcsin(np.sqrt(1 - (cos2r * np.cos(d1))**2))
        
        t_az = np.degrees(t_az) % 360
        t_pl = np.degrees(t_pl)
        
        p_az = (t_az + 90) % 360
        p_pl = 90 - t_pl
        
        return {
            'T': {'azimuth': t_az, 'plunge': t_pl},
            'P': {'azimuth': p_az, 'plunge': p_pl}
        }


class BeachBall:
    def __init__(self, focal_mechanism=None, strike=None, dip=None, rake=None):
        if focal_mechanism is not None:
            self.fm = focal_mechanism
        elif strike is not None and dip is not None and rake is not None:
            self.fm = FocalMechanism(strike, dip, rake)
        else:
            raise ValueError("Need either FocalMechanism object or strike/dip/rake")
    
    def _stereographic_project(self, azimuth, plunge):
        az = np.radians(azimuth)
        pl = np.radians(plunge)
        
        r = np.sin(np.pi / 4 - pl / 2)
        x = r * np.sin(az)
        y = -r * np.cos(az)
        
        return x, y
    
    def _draw_fault_plane(self, ax, strike, dip, color, fill=True):
        s = np.radians(strike)
        d = np.radians(dip)
        
        n_pts = 100
        angles = np.linspace(0, 2 * np.pi, n_pts)
        
        x = np.zeros(n_pts)
        y = np.zeros(n_pts)
        
        for i, angle in enumerate(angles):
            if d == 0:
                x[i], y[i] = 0, 0
                continue
            
            a = np.sin(angle)**2 + (np.cos(angle)**2) / np.tan(d)**2
            if a <= 0:
                continue
            
            r = 1 / np.sqrt(a)
            if r > 1:
                r = 1
            
            px = r * np.cos(angle + s)
            py = r * np.sin(angle + s)
            
            if np.cos(angle) >= 0:
                x[i], y[i] = px, py
            else:
                x[i], y[i] = np.nan, np.nan
        
        valid = ~np.isnan(x)
        if fill:
            ax.fill(x[valid], y[valid], color=color, alpha=0.7)
        ax.plot(x[valid], y[valid], color='black', linewidth=2)
    
    def _calculate_quadrants(self):
        s1 = np.radians(self.fm.strike)
        d1 = np.radians(self.fm.dip)
        r1 = np.radians(self.fm.rake)
        
        s2 = np.radians(self.fm.aux_plane['strike'])
        d2 = np.radians(self.fm.aux_plane['dip'])
        
        n_pts = 200
        theta = np.linspace(0, 2 * np.pi, n_pts)
        r = 1.0
        
        quadrants = []
        current_quad = None
        
        for t in theta:
            x = r * np.cos(t)
            y = r * np.sin(t)
            
            if x**2 + y**2 > 1:
                continue
            
            sign1 = (x * np.sin(s1) - y * np.cos(s1)) * np.sin(d1)
            sign2 = (x * np.sin(s2) - y * np.cos(s2)) * np.sin(d2)
            
            if abs(sign1) < 1e-10 or abs(sign2) < 1e-10:
                continue
            
            quad = 'compressional' if sign1 * sign2 > 0 else 'dilatational'
            
            if quad != current_quad:
                current_quad = quad
                quadrants.append({'start': t, 'type': quad})
        
        return quadrants
    
    def plot(self, ax=None, size=1.0, compression_color='red', 
            dilatation_color='white', linewidth=2):
        if ax is None:
            fig, ax = plt.subplots(figsize=(6, 6))
        
        outer_circle = Circle((0, 0), size, fill=False, color='black', 
                             linewidth=linewidth)
        ax.add_patch(outer_circle)
        
        self._draw_fault_plane(ax, self.fm.strike, self.fm.dip, 
                              compression_color, fill=False)
        self._draw_fault_plane(ax, self.fm.aux_plane['strike'], 
                              self.fm.aux_plane['dip'],
                              compression_color, fill=False)
        
        n_angles = 360
        angles = np.linspace(0, 2 * np.pi, n_angles)
        x = np.cos(angles)
        y = np.sin(angles)
        
        s1 = np.radians(self.fm.strike)
        d1 = np.radians(self.fm.dip)
        s2 = np.radians(self.fm.aux_plane['strike'])
        d2 = np.radians(self.fm.aux_plane['dip'])
        
        for i in range(len(x)):
            if x[i]**2 + y[i]**2 > 1:
                continue
            
            sign1 = (x[i] * np.sin(s1) - y[i] * np.cos(s1)) * np.sin(d1)
            sign2 = (x[i] * np.sin(s2) - y[i] * np.cos(s2)) * np.sin(d2)
            
            if sign1 * sign2 > 0:
                ax.plot([0, x[i]], [0, y[i]], color=compression_color, 
                       alpha=0.3, linewidth=0.5)
            else:
                ax.plot([0, x[i]], [0, y[i]], color=dilatation_color, 
                       alpha=0.3, linewidth=0.5)
        
        self._draw_fault_plane(ax, self.fm.strike, self.fm.dip, 'none', fill=False)
        self._draw_fault_plane(ax, self.fm.aux_plane['strike'], 
                              self.fm.aux_plane['dip'], 'none', fill=False)
        
        axes = self.fm.get_t_axes()
        t_x, t_y = self._stereographic_project(axes['T']['azimuth'], 
                                               axes['T']['plunge'])
        p_x, p_y = self._stereographic_project(axes['P']['azimuth'], 
                                               axes['P']['plunge'])
        
        ax.plot(t_x, t_y, 'o', color='white', markersize=8, markeredgecolor='black')
        ax.text(t_x, t_y, 'T', fontsize=12, ha='center', va='center')
        
        ax.plot(p_x, p_y, 'o', color='black', markersize=8, markeredgecolor='white')
        ax.text(p_x, p_y, 'P', fontsize=12, ha='center', va='center', color='white')
        
        ax.set_aspect('equal')
        ax.set_xlim(-1.1, 1.1)
        ax.set_ylim(-1.1, 1.1)
        ax.axis('off')
        
        return ax
    
    def plot_station_polarity(self, stations, ax=None, **kwargs):
        if ax is None:
            ax = self.plot(**kwargs)
        
        for sta in stations:
            x, y = self._stereographic_project(sta['azimuth'], sta['takeoff'])
            
            if sta.get('polarity', 'positive') == 'positive':
                ax.plot(x, y, 'o', color='black', markersize=6, 
                       markeredgecolor='white')
            else:
                ax.plot(x, y, 'o', color='white', markersize=6, 
                       markeredgecolor='black')
            
            if 'name' in sta:
                ax.text(x + 0.05, y + 0.05, sta['name'], fontsize=8)
        
        return ax


class MomentTensor:
    def __init__(self, mrr, mtt, mpp, mrt, mrp, mtp):
        self.M = np.array([
            [mrr, mrt, mrp],
            [mrt, mtt, mtp],
            [mrp, mtp, mpp]
        ])
        self.eigenvalues, self.eigenvectors = np.linalg.eigh(self.M)
        
        idx = self.eigenvalues.argsort()[::-1]
        self.eigenvalues = self.eigenvalues[idx]
        self.eigenvectors = self.eigenvectors[:, idx]
    
    def to_focal_mechanism(self):
        t_axis = self.eigenvectors[:, 0]
        p_axis = self.eigenvectors[:, 2]
        
        n_axis = np.cross(t_axis, p_axis)
        n_axis = n_axis / np.linalg.norm(n_axis)
        
        strike = np.degrees(np.arctan2(n_axis[1], n_axis[0]))
        if strike < 0:
            strike += 360
        
        dip = np.degrees(np.arccos(np.clip(n_axis[2], -1, 1)))
        
        rake = np.degrees(np.arctan2(-t_axis[2], 
                                      t_axis[0] * n_axis[1] - t_axis[1] * n_axis[0]))
        
        return FocalMechanism(strike, dip, rake)
