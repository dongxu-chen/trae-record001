import numpy as np
import matplotlib.pyplot as plt
from obspy import Stream, Trace, UTCDateTime
from matplotlib.dates import DateFormatter
import datetime
from collections import defaultdict


class NetworkNormalizer:
    def __init__(self):
        self.network_stats = {}
        
    def normalize_trace(self, trace, method='std'):
        data = trace.data.copy()
        
        if method == 'std':
            std = np.std(data)
            if std > 0:
                data = (data - np.mean(data)) / std
                
        elif method == 'minmax':
            data_min = np.min(data)
            data_max = np.max(data)
            if data_max > data_min:
                data = (data - data_min) / (data_max - data_min) * 2 - 1
                
        elif method == 'energy':
            energy = np.sum(data ** 2)
            if energy > 0:
                data = data / np.sqrt(energy / len(data))
        
        return data
    
    def align_traces(self, stream, reference_time=None, start_margin=5.0):
        if reference_time is None:
            reference_time = min(trace.stats.starttime for trace in stream)
        
        aligned_stream = Stream()
        
        for trace in stream:
            time_diff = trace.stats.starttime - reference_time
            
            if time_diff > 0:
                padding = int(time_diff * trace.stats.sampling_rate)
                padded_data = np.pad(trace.data, (padding, 0), 'constant')
            else:
                start_idx = int(-time_diff * trace.stats.sampling_rate)
                padded_data = trace.data[start_idx:]
            
            max_len = max(int((trace.stats.endtime - reference_time + start_margin) * trace.stats.sampling_rate), len(padded_data))
            if len(padded_data) < max_len:
                padded_data = np.pad(padded_data, (0, max_len - len(padded_data)), 'constant')
            
            new_trace = trace.copy()
            new_trace.data = padded_data
            new_trace.stats.starttime = reference_time
            aligned_stream.append(new_trace)
            
        return aligned_stream
    
    def group_by_network(self, stream):
        networks = defaultdict(list)
        for trace in stream:
            network = trace.stats.network
            networks[network].append(trace)
        return networks


class WaveformPlotter:
    def __init__(self, figsize=(12, 8), dpi=100):
        self.figsize = figsize
        self.dpi = dpi

    def plot_waveform(self, trace, title=None, show=True, save_path=None, **kwargs):
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        times = trace.times()
        data = trace.data
        
        ax.plot(times, data, **kwargs)
        
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Amplitude")
        
        if title is None:
            title = f"Waveform - {trace.id}"
        ax.set_title(title)
        
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches="tight")
        
        if show:
            plt.show()
        
        return fig, ax

    def plot_stream(self, stream, title=None, show=True, save_path=None, **kwargs):
        n_traces = len(stream)
        fig, axes = plt.subplots(n_traces, 1, figsize=(self.figsize[0], self.figsize[1] * n_traces / 3), 
                                 dpi=self.dpi, sharex=True)
        
        if n_traces == 1:
            axes = [axes]
        
        for i, (ax, trace) in enumerate(zip(axes, stream)):
            times = trace.times()
            data = trace.data
            
            ax.plot(times, data, **kwargs)
            ax.set_ylabel(f"{trace.stats.channel}")
            ax.grid(True, alpha=0.3)
            
            if i == n_traces - 1:
                ax.set_xlabel("Time (s)")
        
        if title is None:
            title = "Waveform Stream"
        fig.suptitle(title, y=1.02)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches="tight")
        
        if show:
            plt.show()
        
        return fig, axes
    
    def plot_network_aligned(self, stream, normalize=True, normalize_method='std',
                            align_time=True, reference_time=None, title=None, 
                            show=True, save_path=None, **kwargs):
        normalizer = NetworkNormalizer()
        
        if align_time:
            stream = normalizer.align_traces(stream, reference_time)
        
        networks = normalizer.group_by_network(stream)
        n_networks = len(networks)
        n_traces = len(stream)
        
        fig, axes = plt.subplots(n_traces, 1, figsize=(self.figsize[0], max(6, n_traces * 2)), 
                                 dpi=self.dpi, sharex=True)
        
        if n_traces == 1:
            axes = [axes]
        
        colors = plt.cm.tab10(np.linspace(0, 1, max(10, n_networks)))
        network_colors = {net: colors[i] for i, net in enumerate(sorted(networks.keys()))}
        
        ax_idx = 0
        for network in sorted(networks.keys()):
            traces = networks[network]
            for trace in traces:
                times = trace.times()
                data = normalizer.normalize_trace(trace, normalize_method) if normalize else trace.data
                
                axes[ax_idx].plot(times, data, color=network_colors[network], 
                                 label=f"{network}.{trace.stats.station}", **kwargs)
                axes[ax_idx].set_ylabel(f"{network}\n{trace.stats.station}\n{trace.stats.channel}")
                axes[ax_idx].grid(True, alpha=0.3)
                axes[ax_idx].legend(loc='upper right')
                
                if ax_idx == n_traces - 1:
                    axes[ax_idx].set_xlabel("Time (s)")
                ax_idx += 1
        
        if title is None:
            norm_str = "Normalized" if normalize else "Original"
            align_str = "Time-Aligned" if align_time else ""
            title = f"Multi-Network Waveforms ({norm_str}{', ' + align_str if align_time else ''})"
        
        fig.suptitle(title, y=1.02)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches="tight")
        
        if show:
            plt.show()
        
        return fig, axes

    def plot_spectrum(self, spectrum_data, title=None, show=True, save_path=None, **kwargs):
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        freq = spectrum_data.get("freq")
        amplitude = spectrum_data.get("amplitude", spectrum_data.get("psd"))
        
        ax.plot(freq, amplitude, **kwargs)
        
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Amplitude" if "amplitude" in spectrum_data else "PSD")
        ax.set_xscale("log")
        ax.set_yscale("log")
        
        if title is None:
            title = "Frequency Spectrum"
        ax.set_title(title)
        
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches="tight")
        
        if show:
            plt.show()
        
        return fig, ax

    def plot_spectrogram(self, spec_data, title=None, show=True, save_path=None, **kwargs):
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        freq = spec_data["freq"]
        time = spec_data["time"]
        spectrogram = spec_data["spectrogram"]
        
        spec_log = 10 * np.log10(spectrogram + 1e-10)
        
        im = ax.pcolormesh(time, freq, spec_log, shading="auto", cmap=kwargs.get("cmap", "viridis"))
        fig.colorbar(im, ax=ax, label="Power (dB)")
        
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Frequency (Hz)")
        
        if title is None:
            title = "Spectrogram"
        ax.set_title(title)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches="tight")
        
        if show:
            plt.show()
        
        return fig, ax

    def plot_phase_picks(self, trace, picks, title=None, show=True, save_path=None, **kwargs):
        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)
        
        times = trace.times()
        data = trace.data
        
        ax.plot(times, data, label="Waveform", **kwargs)
        
        colors = {"P": "red", "S": "blue"}
        for phase, pick in picks.items():
            if pick is not None:
                pick_time = pick["index"] / trace.stats.sampling_rate
                ax.axvline(x=pick_time, color=colors.get(phase, "green"), 
                          linestyle="--", linewidth=2, label=f"{phase}-wave pick")
        
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Amplitude")
        
        if title is None:
            title = f"Phase Picking - {trace.id}"
        ax.set_title(title)
        
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches="tight")
        
        if show:
            plt.show()
        
        return fig, ax

    def plot_filter_comparison(self, original_trace, filtered_trace, title=None, show=True, save_path=None, **kwargs):
        fig, axes = plt.subplots(2, 1, figsize=(self.figsize[0], 6), dpi=self.dpi, sharex=True)
        
        times = original_trace.times()
        
        axes[0].plot(times, original_trace.data, label="Original")
        axes[0].set_ylabel("Original\nAmplitude")
        axes[0].grid(True, alpha=0.3)
        axes[0].legend()
        
        axes[1].plot(times, filtered_trace.data, label="Filtered", color="orange")
        axes[1].set_xlabel("Time (s)")
        axes[1].set_ylabel("Filtered\nAmplitude")
        axes[1].grid(True, alpha=0.3)
        axes[1].legend()
        
        if title is None:
            title = "Filter Comparison"
        fig.suptitle(title, y=1.02)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches="tight")
        
        if show:
            plt.show()
        
        return fig, axes

    def plot_comprehensive(self, trace, picks=None, spectrum_data=None, spec_data=None, 
                          title=None, show=True, save_path=None):
        n_plots = 1
        if picks is not None:
            n_plots += 0
        if spectrum_data is not None:
            n_plots += 1
        if spec_data is not None:
            n_plots += 1
        
        fig, axes = plt.subplots(n_plots, 1, figsize=(self.figsize[0], 4 * n_plots), 
                                 dpi=self.dpi, sharex=False)
        
        if n_plots == 1:
            axes = [axes]
        
        current_ax = 0
        
        times = trace.times()
        data = trace.data
        
        axes[current_ax].plot(times, data)
        axes[current_ax].set_ylabel("Amplitude")
        axes[current_ax].set_title("Waveform")
        axes[current_ax].grid(True, alpha=0.3)
        
        if picks is not None:
            colors = {"P": "red", "S": "blue"}
            for phase, pick in picks.items():
                if pick is not None:
                    pick_time = pick["index"] / trace.stats.sampling_rate
                    axes[current_ax].axvline(x=pick_time, color=colors.get(phase, "green"), 
                                            linestyle="--", linewidth=2, label=f"{phase}-wave")
            axes[current_ax].legend()
        
        current_ax += 1
        
        if spectrum_data is not None:
            freq = spectrum_data.get("freq")
            amplitude = spectrum_data.get("amplitude", spectrum_data.get("psd"))
            axes[current_ax].plot(freq, amplitude)
            axes[current_ax].set_xlabel("Frequency (Hz)")
            axes[current_ax].set_ylabel("Amplitude" if "amplitude" in spectrum_data else "PSD")
            axes[current_ax].set_title("Frequency Spectrum")
            axes[current_ax].set_xscale("log")
            axes[current_ax].grid(True, alpha=0.3)
            current_ax += 1
        
        if spec_data is not None:
            freq = spec_data["freq"]
            time = spec_data["time"]
            spectrogram = spec_data["spectrogram"]
            spec_log = 10 * np.log10(spectrogram + 1e-10)
            im = axes[current_ax].pcolormesh(time, freq, spec_log, shading="auto", cmap="viridis")
            fig.colorbar(im, ax=axes[current_ax], label="Power (dB)")
            axes[current_ax].set_xlabel("Time (s)")
            axes[current_ax].set_ylabel("Frequency (Hz)")
            axes[current_ax].set_title("Spectrogram")
            current_ax += 1
        
        if title:
            fig.suptitle(title, y=1.02)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches="tight")
        
        if show:
            plt.show()
        
        return fig, axes
