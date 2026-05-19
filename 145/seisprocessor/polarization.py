import numpy as np
from obspy import Stream, Trace
from scipy.signal import correlate
from scipy.linalg import eigh


class PolarizationAnalyzer:
    def __init__(self):
        pass
    
    def get_three_components(self, stream):
        z_comp = None
        n_comp = None
        e_comp = None
        
        for trace in stream:
            chan = trace.stats.channel.upper()
            if chan.endswith('Z'):
                z_comp = trace
            elif chan.endswith('N') or chan.endswith('1'):
                n_comp = trace
            elif chan.endswith('E') or chan.endswith('2'):
                e_comp = trace
        
        return z_comp, n_comp, e_comp
    
    def align_traces(self, z_trace, n_trace, e_trace):
        if z_trace is None or n_trace is None or e_trace is None:
            return None, None, None
        
        start_time = max(z_trace.stats.starttime, 
                        n_trace.stats.starttime, 
                        e_trace.stats.starttime)
        end_time = min(z_trace.stats.endtime, 
                      n_trace.stats.endtime, 
                      e_trace.stats.endtime)
        
        z_cut = z_trace.copy().trim(start_time, end_time)
        n_cut = n_trace.copy().trim(start_time, end_time)
        e_cut = e_trace.copy().trim(start_time, end_time)
        
        return z_cut, n_cut, e_cut
    
    def sliding_window_covariance(self, data, window_size, overlap=0.5):
        n_samples = data.shape[1]
        step = int(window_size * (1 - overlap))
        n_windows = (n_samples - window_size) // step + 1
        
        rectilinearity = np.zeros(n_windows)
        azimuths = np.zeros(n_windows)
        incidents = np.zeros(n_windows)
        times = np.zeros(n_windows)
        
        for i in range(n_windows):
            start = i * step
            end = start + window_size
            
            window_data = data[:, start:end]
            cov_matrix = np.cov(window_data)
            
            eigenvalues, eigenvectors = eigh(cov_matrix)
            idx = eigenvalues.argsort()[::-1]
            eigenvalues = eigenvalues[idx]
            eigenvectors = eigenvectors[:, idx]
            
            eig_sum = np.sum(eigenvalues)
            if eig_sum > 0:
                rectilinearity[i] = 1 - np.sqrt(
                    (eigenvalues[1] + eigenvalues[2]) / (2 * eigenvalues[0])
                )
            
            main_vector = eigenvectors[:, 0]
            
            z_amp = abs(main_vector[0])
            n_amp = abs(main_vector[1])
            e_amp = abs(main_vector[2])
            
            horizontal_amp = np.sqrt(n_amp**2 + e_amp**2)
            if horizontal_amp > 0:
                azimuth = np.degrees(np.arctan2(e_amp, n_amp))
                if azimuth < 0:
                    azimuth += 360
                azimuths[i] = azimuth
            
            total_amp = np.sqrt(z_amp**2 + horizontal_amp**2)
            if total_amp > 0:
                incident = np.degrees(np.arccos(z_amp / total_amp))
                incidents[i] = incident
            
            times[i] = start + window_size // 2
        
        return times, rectilinearity, azimuths, incidents
    
    def analyze_polarization(self, stream, window_length=1.0, overlap=0.5):
        z_trace, n_trace, e_trace = self.get_three_components(stream)
        z_trace, n_trace, e_trace = self.align_traces(z_trace, n_trace, e_trace)
        
        if z_trace is None:
            raise ValueError("Need Z, N, E three component data for polarization analysis")
        
        sampling_rate = z_trace.stats.sampling_rate
        window_size = int(window_length * sampling_rate)
        
        data = np.vstack([
            z_trace.data,
            n_trace.data,
            e_trace.data
        ])
        
        times, rectilinearity, azimuths, incidents = self.sliding_window_covariance(
            data, window_size, overlap
        )
        
        times_seconds = times / sampling_rate
        
        return {
            'time': times_seconds,
            'rectilinearity': rectilinearity,
            'azimuth': azimuths,
            'incident': incidents,
            'sampling_rate': sampling_rate
        }
    
    def estimate_wavefront_direction(self, pol_result, min_rectilinearity=0.7):
        valid_idx = pol_result['rectilinearity'] >= min_rectilinearity
        
        if not np.any(valid_idx):
            return None
        
        valid_azimuths = pol_result['azimuth'][valid_idx]
        valid_incidents = pol_result['incident'][valid_idx]
        valid_rect = pol_result['rectilinearity'][valid_idx]
        
        weights = valid_rect / np.sum(valid_rect)
        
        mean_azimuth = np.sum(valid_azimuths * weights)
        mean_incident = np.sum(valid_incidents * weights)
        
        return {
            'azimuth': mean_azimuth,
            'incident': mean_incident,
            'backazimuth': (mean_azimuth + 180) % 360,
            'confidence': np.mean(valid_rect)
        }
    
    def hodogram(self, trace1, trace2, start_time=None, end_time=None):
        if start_time is not None and end_time is not None:
            t1 = trace1.copy().trim(start_time, end_time)
            t2 = trace2.copy().trim(start_time, end_time)
            data1 = t1.data
            data2 = t2.data
        else:
            data1 = trace1.data
            data2 = trace2.data
        
        return {
            'x': data1,
            'y': data2,
            'trace1_id': trace1.id,
            'trace2_id': trace2.id
        }
