import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import LogNorm, Normalize
from typing import Optional, List, Tuple, Dict, Union
import logging
from mpl_toolkits.mplot3d import Axes3D

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def n_mirrors_per_order(max_order: Union[int, np.ndarray], ndim: int = 3) -> Union[int, np.ndarray]:
    if isinstance(max_order, int):
        orders = np.arange(1, max_order + 1)
        total = 0
        for order in orders:
            if ndim == 2:
                total += 4 * order
            else:
                total += 6 * order ** 2 + 2
        return total
    else:
        totals = []
        for mo in max_order:
            orders = np.arange(1, mo + 1)
            total = 0
            for order in orders:
                if ndim == 2:
                    total += 4 * order
                else:
                    total += 6 * order ** 2 + 2
            totals.append(total)
        return np.array(totals)


class SoundFieldVisualizer:
    def __init__(self, dpi: int = 100, figsize: Tuple[int, int] = (12, 8)):
        self.dpi = dpi
        self.figsize = figsize
        self._default_cmap = cm.viridis
        self._pressure_cmap = cm.inferno
        self._ir_cmap = cm.plasma

    def plot_impulse_response(self, impulse_response: np.ndarray,
                              fs: int,
                              title: str = "Impulse Response",
                              ax: Optional[plt.Axes] = None,
                              show: bool = True) -> plt.Axes:
        if ax is None:
            fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)

        t = np.arange(len(impulse_response)) / fs
        ax.plot(t, impulse_response, linewidth=0.8, color='steelblue')
        ax.set_xlabel('Time [s]')
        ax.set_ylabel('Amplitude')
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='k', linewidth=0.5, alpha=0.5)

        if show:
            plt.tight_layout()
            plt.show()

        return ax

    def plot_band_impulse_responses(self, band_irs: np.ndarray,
                                     frequencies: np.ndarray,
                                     fs: int,
                                     title: str = "Impulse Responses by Frequency Band",
                                     axs: Optional[List[plt.Axes]] = None,
                                     show: bool = True) -> List[plt.Axes]:
        n_bands = len(frequencies)
        n_cols = min(3, n_bands)
        n_rows = (n_bands + n_cols - 1) // n_cols

        if axs is None:
            fig, axs = plt.subplots(n_rows, n_cols, figsize=(16, 4 * n_rows),
                                   dpi=self.dpi, squeeze=False)
        axs_array = np.array(axs)
        axs_flat = axs_array.flat

        t = np.arange(band_irs.shape[-1]) / fs

        for band_idx, freq in enumerate(frequencies):
            if band_idx < len(axs_flat):
                ax = axs_flat[band_idx]
                if ax is not None:
                    ir = band_irs[band_idx]
                    ax.plot(t, ir, linewidth=0.8, color='steelblue')
                    ax.set_title(f'{freq:.0f} Hz')
                    ax.set_xlabel('Time [s]')
                    ax.set_ylabel('Amplitude')
                    ax.grid(True, alpha=0.3)
                    ax.axhline(y=0, color='k', linewidth=0.5, alpha=0.5)
            else:
                break

        for band_idx in range(len(frequencies), len(axs_flat)):
            ax = axs_flat[band_idx]
            if ax is not None:
                ax.axis('off')

        if show:
            plt.tight_layout()
            plt.show()

        return list(axs_flat[:n_bands])

    def plot_band_edc_comparison(self, edc_bands: np.ndarray,
                                  frequencies: np.ndarray,
                                  rt60_bands: Optional[np.ndarray] = None,
                                  fs: int = None,
                                  title: str = "EDC Comparison by Frequency Band",
                                  ax: Optional[plt.Axes] = None,
                                  show: bool = True) -> plt.Axes:
        if ax is None:
            fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)

        if fs is None:
            fs = 1.0

        t = np.arange(edc_bands.shape[-1]) / fs
        colors = cm.tab10(np.linspace(0, 1, len(frequencies)))

        for band_idx, (freq, color) in enumerate(zip(frequencies, colors)):
            edc = edc_bands[band_idx]
            label = f'{freq:.0f} Hz'
            if rt60_bands is not None and rt60_bands[band_idx] > 0:
                label += f' (RT60={rt60_bands[band_idx]:.2f}s)'
            ax.plot(t, edc, linewidth=1.5, color=color, label=label)

        ax.set_xlabel('Time [s]')
        ax.set_ylabel('Energy [dB]')
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right', fontsize=9)
        ax.set_ylim([-70, 5])

        if show:
            plt.tight_layout()
            plt.show()

        return ax

    def plot_rt60_band_comparison(self, rt60_measured: Dict[str, np.ndarray],
                                   frequencies: np.ndarray,
                                   title: str = "RT60 Comparison by Frequency Band",
                                   ax: Optional[plt.Axes] = None,
                                   show: bool = True) -> plt.Axes:
        if ax is None:
            fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)

        colors = cm.tab10(np.linspace(0, 1, len(rt60_measured)))
        markers = ['o', 's', '^', 'D', 'v', 'p', '*']

        for (name, rt60_data), color, marker in zip(rt60_measured.items(), colors, markers):
            ax.semilogx(frequencies, rt60_data, marker=marker, linestyle='-',
                       linewidth=1.5, markersize=7, color=color, label=name)

        ax.set_xlabel('Frequency [Hz]')
        ax.set_ylabel('RT60 [s]')
        ax.set_title(title)
        ax.grid(True, alpha=0.3, which='both')
        ax.legend(loc='best')
        ax.set_ylim(bottom=0)

        for freq in frequencies:
            ax.axvline(freq, color='gray', linestyle=':', linewidth=0.5, alpha=0.3)

        if show:
            plt.tight_layout()
            plt.show()

        return ax

    def plot_adaptive_order_analysis(self, source_pos: np.ndarray,
                                      receiver_pos: np.ndarray,
                                      room_dims: np.ndarray,
                                      max_order_range: Tuple[int, int] = (1, 10),
                                      title: str = "Adaptive Order Analysis",
                                      ax: Optional[plt.Axes] = None,
                                      show: bool = True) -> plt.Axes:
        if ax is None:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), dpi=self.dpi)
        else:
            if isinstance(ax, (np.ndarray, list)):
                ax1 = ax[0]
                ax2 = ax[1] if len(ax) > 1 else None
            else:
                ax1 = ax
                ax2 = None

        direct_dist = np.linalg.norm(source_pos - receiver_pos)
        min_dim = np.min(room_dims)

        orders = np.arange(max_order_range[0], max_order_range[1] + 1)
        distances = direct_dist + 2 * orders * min_dim
        spreading = 1.0 / (4 * np.pi * distances)
        reflections = 0.7 ** orders
        amplitudes = spreading * reflections
        amplitudes_db = 20 * np.log10(amplitudes / amplitudes[0] + 1e-10)

        ax1.plot(orders, amplitudes_db, 'bo-', linewidth=2, markersize=7)
        ax1.axhline(-60, color='r', linestyle='--', label='-60 dB threshold')
        ax1.set_xlabel('Reflection Order')
        ax1.set_ylabel('Relative Amplitude [dB]')
        ax1.set_title('Amplitude Decay vs Reflection Order')
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        for order, amp_db in zip(orders, amplitudes_db):
            ax1.annotate(f'{amp_db:.1f}dB', xy=(order, amp_db),
                        xytext=(0, 10), textcoords='offset points',
                        ha='center', fontsize=8)

        if ax2 is not None:
            ax2.plot(orders, n_mirrors_per_order(orders, len(room_dims)),
                    'go-', linewidth=2, markersize=7)
            ax2.set_xlabel('Max Reflection Order')
            ax2.set_ylabel('Total Mirror Sources')
            ax2.set_title('Computational Complexity')
            ax2.grid(True, alpha=0.3)
            ax2.set_yscale('log')

            for order, n in zip(orders, n_mirrors_per_order(orders, len(room_dims))):
                ax2.annotate(f'{n:,}', xy=(order, n),
                            xytext=(0, 10), textcoords='offset points',
                            ha='center', fontsize=8)

        if show:
            plt.tight_layout()
            plt.show()

        return [ax1, ax2] if ax2 is not None else ax1

    def plot_edc(self, edc_db: np.ndarray,
                 fs: int,
                 rt60: Optional[float] = None,
                 title: str = "Energy Decay Curve (EDC)",
                 ax: Optional[plt.Axes] = None,
                 show: bool = True) -> plt.Axes:
        if ax is None:
            fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)

        t = np.arange(len(edc_db)) / fs
        ax.plot(t, edc_db, linewidth=1.5, color='darkorange', label='EDC')

        if rt60 is not None and rt60 > 0:
            t_line = np.array([0, rt60])
            decay_line = np.array([0, -60])
            ax.plot(t_line, decay_line, 'r--', linewidth=1.5,
                    label=f'RT60 = {rt60:.3f}s')

        ax.set_xlabel('Time [s]')
        ax.set_ylabel('Energy [dB]')
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_ylim([-70, 5])

        if show:
            plt.tight_layout()
            plt.show()

        return ax

    def plot_rt60_frequency(self, frequencies: np.ndarray,
                            rt60_values: np.ndarray,
                            title: str = "RT60 vs Frequency",
                            ax: Optional[plt.Axes] = None,
                            show: bool = True) -> plt.Axes:
        if ax is None:
            fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)

        ax.semilogx(frequencies, rt60_values, 'o-', linewidth=1.5,
                    markersize=6, color='mediumseagreen')
        ax.set_xlabel('Frequency [Hz]')
        ax.set_ylabel('RT60 [s]')
        ax.set_title(title)
        ax.grid(True, alpha=0.3, which='both')
        ax.set_ylim(bottom=0)

        for freq, rt60 in zip(frequencies, rt60_values):
            ax.annotate(f'{rt60:.2f}s', xy=(freq, rt60),
                       xytext=(5, 5), textcoords='offset points',
                       fontsize=9)

        if show:
            plt.tight_layout()
            plt.show()

        return ax

    def plot_sound_pressure_heatmap(self, receiver_positions: np.ndarray,
                                     pressure_values: np.ndarray,
                                     room_dims: np.ndarray,
                                     frequency: Optional[float] = None,
                                     title: str = "Sound Pressure Distribution",
                                     ax: Optional[plt.Axes] = None,
                                     show: bool = True,
                                     log_scale: bool = True,
                                     contour: bool = True) -> plt.Axes:
        if ax is None:
            fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)

        if receiver_positions.shape[1] == 3:
            unique_z = np.unique(receiver_positions[:, 2])
            if len(unique_z) > 1:
                logger.warning(f"Multiple z-planes detected, using z={unique_z[0]}")
            z_mask = receiver_positions[:, 2] == unique_z[0]
            x = receiver_positions[z_mask, 0]
            y = receiver_positions[z_mask, 1]
            pressure = pressure_values[z_mask]
        else:
            x = receiver_positions[:, 0]
            y = receiver_positions[:, 1]
            pressure = pressure_values

        x_unique = np.sort(np.unique(x))
        y_unique = np.sort(np.unique(y))
        X, Y = np.meshgrid(x_unique, y_unique)

        P = np.zeros_like(X, dtype=np.float64)
        for i, xv in enumerate(x_unique):
            for j, yv in enumerate(y_unique):
                mask = (x == xv) & (y == yv)
                if np.any(mask):
                    P[j, i] = pressure[mask][0]

        if log_scale:
            P_db = 20 * np.log10(np.abs(P) + 1e-10)
            vmin = np.max(P_db) - 60
            vmax = np.max(P_db)
            norm = Normalize(vmin=vmin, vmax=vmax)
            levels = np.linspace(vmin, vmax, 20)
            plot_values = P_db
            cbar_label = 'Sound Pressure Level [dB]'
        else:
            norm = LogNorm(vmin=np.max([np.min(np.abs(P)), 1e-10]),
                          vmax=np.max(np.abs(P)))
            plot_values = np.abs(P)
            cbar_label = 'Pressure Amplitude [Pa]'
            levels = np.logspace(np.log10(norm.vmin), np.log10(norm.vmax), 20)

        if contour:
            contour_plot = ax.contourf(X, Y, plot_values,
                                       levels=levels,
                                       cmap=self._pressure_cmap,
                                       norm=norm,
                                       alpha=0.9)
            ax.contour(X, Y, plot_values,
                       levels=levels[::2],
                       colors='black',
                       linewidths=0.5,
                       alpha=0.3)
        else:
            contour_plot = ax.pcolormesh(X, Y, plot_values,
                                         cmap=self._pressure_cmap,
                                         norm=norm,
                                         shading='auto')

        cbar = plt.colorbar(contour_plot, ax=ax)
        cbar.set_label(cbar_label)

        ax.set_xlabel('X [m]')
        ax.set_ylabel('Y [m]')
        ax.set_aspect('equal')
        ax.set_xlim([0, room_dims[0]])
        ax.set_ylim([0, room_dims[1]])

        freq_str = f' @ {frequency:.1f} Hz' if frequency else ''
        ax.set_title(title + freq_str)
        ax.grid(True, alpha=0.3, linestyle='--')

        if show:
            plt.tight_layout()
            plt.show()

        return ax

    def plot_sound_pressure_3d(self, receiver_positions: np.ndarray,
                               pressure_values: np.ndarray,
                               room_dims: np.ndarray,
                               frequency: Optional[float] = None,
                               title: str = "3D Sound Pressure Distribution",
                               ax: Optional[plt.Axes] = None,
                               show: bool = True) -> plt.Axes:
        if ax is None:
            fig = plt.figure(figsize=self.figsize, dpi=self.dpi)
            ax = fig.add_subplot(111, projection='3d')

        x = receiver_positions[:, 0]
        y = receiver_positions[:, 1]
        if receiver_positions.shape[1] == 3:
            z = receiver_positions[:, 2]
        else:
            z = np.zeros_like(x)

        P_db = 20 * np.log10(np.abs(pressure_values) + 1e-10)
        vmin = np.max(P_db) - 60
        vmax = np.max(P_db)
        norm = Normalize(vmin=vmin, vmax=vmax)

        scatter = ax.scatter(x, y, z, c=P_db, cmap=self._pressure_cmap,
                            norm=norm, s=20, alpha=0.8)

        cbar = plt.colorbar(scatter, ax=ax, pad=0.1)
        cbar.set_label('Sound Pressure Level [dB]')

        ax.set_xlabel('X [m]')
        ax.set_ylabel('Y [m]')
        ax.set_zlabel('Z [m]')
        ax.set_xlim([0, room_dims[0]])
        ax.set_ylim([0, room_dims[1]])
        if len(room_dims) > 2:
            ax.set_zlim([0, room_dims[2]])

        freq_str = f' @ {frequency:.1f} Hz' if frequency else ''
        ax.set_title(title + freq_str)

        if show:
            plt.tight_layout()
            plt.show()

        return ax

    def plot_mirror_sources(self, mirror_sources: np.ndarray,
                            source_positions: np.ndarray,
                            receiver_positions: np.ndarray,
                            room_dims: np.ndarray,
                            orders: Optional[np.ndarray] = None,
                            title: str = "Mirror Sources Visualization",
                            ax: Optional[plt.Axes] = None,
                            show: bool = True) -> plt.Axes:
        is_3d = mirror_sources.shape[1] == 3

        if ax is None:
            if is_3d:
                fig = plt.figure(figsize=self.figsize, dpi=self.dpi)
                ax = fig.add_subplot(111, projection='3d')
            else:
                fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)

        if orders is not None:
            unique_orders = np.unique(orders)
            colors = cm.tab10(np.linspace(0, 1, len(unique_orders)))
            for order, color in zip(unique_orders, colors):
                mask = orders == order
                if is_3d:
                    ax.scatter(mirror_sources[mask, 0], mirror_sources[mask, 1], mirror_sources[mask, 2],
                              c=[color], s=30, alpha=0.6, label=f'Order {int(order)}')
                else:
                    ax.scatter(mirror_sources[mask, 0], mirror_sources[mask, 1],
                              c=[color], s=30, alpha=0.6, label=f'Order {int(order)}')
        else:
            if is_3d:
                ax.scatter(mirror_sources[:, 0], mirror_sources[:, 1], mirror_sources[:, 2],
                          c='gray', s=20, alpha=0.5, label='Mirror Sources')
            else:
                ax.scatter(mirror_sources[:, 0], mirror_sources[:, 1],
                          c='gray', s=20, alpha=0.5, label='Mirror Sources')

        if is_3d:
            ax.scatter(source_positions[:, 0], source_positions[:, 1], source_positions[:, 2],
                      c='red', s=100, marker='*', edgecolors='black', label='Real Sources')
            ax.scatter(receiver_positions[:, 0], receiver_positions[:, 1], receiver_positions[:, 2],
                      c='blue', s=80, marker='o', edgecolors='black', label='Receivers')
        else:
            ax.scatter(source_positions[:, 0], source_positions[:, 1],
                      c='red', s=100, marker='*', edgecolors='black', label='Real Sources')
            ax.scatter(receiver_positions[:, 0], receiver_positions[:, 1],
                      c='blue', s=80, marker='o', edgecolors='black', label='Receivers')

        if not is_3d:
            rect = plt.Rectangle((0, 0), room_dims[0], room_dims[1],
                                fill=False, linewidth=2, color='black', label='Room')
            ax.add_patch(rect)
            ax.set_aspect('equal')
            ax.set_xlim([-room_dims[0] * 0.5, room_dims[0] * 1.5])
            ax.set_ylim([-room_dims[1] * 0.5, room_dims[1] * 1.5])

        ax.set_xlabel('X [m]')
        ax.set_ylabel('Y [m]')
        if is_3d:
            ax.set_zlabel('Z [m]')
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)

        if show:
            plt.tight_layout()
            plt.show()

        return ax

    def plot_dynamic_source_trajectory(self, source_positions: np.ndarray,
                                       room_dims: np.ndarray,
                                       receiver_positions: Optional[np.ndarray] = None,
                                       title: str = "Dynamic Source Trajectory",
                                       ax: Optional[plt.Axes] = None,
                                       show: bool = True) -> plt.Axes:
        is_3d = source_positions.shape[1] == 3

        if ax is None:
            if is_3d:
                fig = plt.figure(figsize=self.figsize, dpi=self.dpi)
                ax = fig.add_subplot(111, projection='3d')
            else:
                fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)

        t = np.arange(len(source_positions))
        colors = cm.viridis(np.linspace(0, 1, len(t)))

        if is_3d:
            ax.plot(source_positions[:, 0], source_positions[:, 1], source_positions[:, 2],
                   'k--', linewidth=1, alpha=0.7, label='Trajectory')
            for i in range(len(source_positions) - 1):
                ax.plot(source_positions[i:i+2, 0], source_positions[i:i+2, 1],
                       source_positions[i:i+2, 2], color=colors[i], linewidth=2)
            ax.scatter(source_positions[0, 0], source_positions[0, 1], source_positions[0, 2],
                      c='green', s=100, marker='o', edgecolors='black', label='Start')
            ax.scatter(source_positions[-1, 0], source_positions[-1, 1], source_positions[-1, 2],
                      c='red', s=100, marker='s', edgecolors='black', label='End')
        else:
            ax.plot(source_positions[:, 0], source_positions[:, 1],
                   'k--', linewidth=1, alpha=0.7, label='Trajectory')
            for i in range(len(source_positions) - 1):
                ax.plot(source_positions[i:i+2, 0], source_positions[i:i+2, 1],
                       color=colors[i], linewidth=2)
            ax.scatter(source_positions[0, 0], source_positions[0, 1],
                      c='green', s=100, marker='o', edgecolors='black', label='Start')
            ax.scatter(source_positions[-1, 0], source_positions[-1, 1],
                      c='red', s=100, marker='s', edgecolors='black', label='End')

        if receiver_positions is not None:
            if is_3d:
                ax.scatter(receiver_positions[:, 0], receiver_positions[:, 1], receiver_positions[:, 2],
                          c='blue', s=80, marker='^', edgecolors='black', label='Receivers')
            else:
                ax.scatter(receiver_positions[:, 0], receiver_positions[:, 1],
                          c='blue', s=80, marker='^', edgecolors='black', label='Receivers')

        if not is_3d:
            rect = plt.Rectangle((0, 0), room_dims[0], room_dims[1],
                                fill=False, linewidth=2, color='black', label='Room')
            ax.add_patch(rect)
            ax.set_aspect('equal')

        ax.set_xlabel('X [m]')
        ax.set_ylabel('Y [m]')
        if is_3d:
            ax.set_zlabel('Z [m]')
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)

        sm = plt.cm.ScalarMappable(cmap=cm.viridis, norm=Normalize(vmin=0, vmax=1))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, pad=0.1)
        cbar.set_label('Time Progression')

        if show:
            plt.tight_layout()
            plt.show()

        return ax

    def plot_rt60_comparison(self, rt60_values: Dict[str, float],
                             title: str = "RT60 Method Comparison",
                             ax: Optional[plt.Axes] = None,
                             show: bool = True) -> plt.Axes:
        if ax is None:
            fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)

        methods = list(rt60_values.keys())
        values = list(rt60_values.values())

        bars = ax.bar(methods, values, color=cm.tab10(np.linspace(0, 1, len(methods))))
        ax.set_xlabel('Method')
        ax.set_ylabel('RT60 [s]')
        ax.set_title(title)
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_ylim(bottom=0)

        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{value:.3f}s', ha='center', va='bottom')

        if show:
            plt.tight_layout()
            plt.show()

        return ax

    def plot_spectrogram(self, signal: np.ndarray,
                         fs: int,
                         title: str = "Spectrogram",
                         ax: Optional[plt.Axes] = None,
                         show: bool = True) -> plt.Axes:
        if ax is None:
            fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)

        f, t, Sxx = plt.specgram(signal, NFFT=1024, Fs=fs, noverlap=512,
                                cmap=cm.inferno)
        ax.set_xlabel('Time [s]')
        ax.set_ylabel('Frequency [Hz]')
        ax.set_title(title)

        if show:
            plt.tight_layout()
            plt.show()

        return ax

    def plot_room_modes(self, mode_frequencies: np.ndarray,
                        mode_spacing: Optional[np.ndarray] = None,
                        title: str = "Room Modes Analysis",
                        ax: Optional[plt.Axes] = None,
                        show: bool = True) -> plt.Axes:
        if ax is None:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=self.figsize, dpi=self.dpi,
                                          gridspec_kw={'height_ratios': [2, 1]})
        else:
            ax1 = ax[0] if isinstance(ax, np.ndarray) else ax
            ax2 = None

        ax1.stem(mode_frequencies, np.ones_like(mode_frequencies),
                linefmt='steelblue', markerfmt='o', basefmt=' ')
        ax1.set_xlabel('Frequency [Hz]')
        ax1.set_ylabel('Mode')
        ax1.set_title(title)
        ax1.grid(True, alpha=0.3)
        ax1.set_yticks([])

        for i, freq in enumerate(mode_frequencies[:10]):
            ax1.annotate(f'{freq:.1f}', xy=(freq, 1), xytext=(0, 10),
                        textcoords='offset points', ha='center', fontsize=8)

        if mode_spacing is not None and ax2 is not None:
            ax2.plot(mode_frequencies[1:], mode_spacing, 'o-',
                    linewidth=1.5, markersize=4, color='darkorange')
            ax2.set_xlabel('Frequency [Hz]')
            ax2.set_ylabel('Spacing [Hz]')
            ax2.grid(True, alpha=0.3)
            mean_spacing = np.mean(mode_spacing)
            ax2.axhline(mean_spacing, color='r', linestyle='--',
                       label=f'Mean = {mean_spacing:.1f} Hz')
            ax2.legend()

        if show:
            plt.tight_layout()
            plt.show()

        return ax

    def create_comprehensive_report(self, impulse_response: np.ndarray,
                                     fs: int,
                                     rt60_results: Dict,
                                     room_dims: np.ndarray,
                                     receiver_positions: np.ndarray,
                                     pressure_values: np.ndarray,
                                     save_path: Optional[str] = None) -> None:
        fig = plt.figure(figsize=(16, 12), dpi=self.dpi)
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

        ax1 = fig.add_subplot(gs[0, :])
        self.plot_impulse_response(impulse_response, fs,
                                   title='Impulse Response',
                                   ax=ax1, show=False)

        ax2 = fig.add_subplot(gs[1, 0])
        self.plot_edc(rt60_results['edc'], fs, rt60=rt60_results['rt60'],
                      title='Energy Decay Curve', ax=ax2, show=False)

        ax3 = fig.add_subplot(gs[1, 1])
        if 'rt60_bands' in rt60_results and 'frequencies' in rt60_results:
            self.plot_rt60_frequency(rt60_results['frequencies'],
                                     rt60_results['rt60_bands'],
                                     title='RT60 by Frequency Band',
                                     ax=ax3, show=False)

        ax4 = fig.add_subplot(gs[1, 2])
        rt60_dict = {
            'T20': rt60_results['t20'],
            'T30': rt60_results['t30'],
            'Main': rt60_results['rt60']
        }
        self.plot_rt60_comparison(rt60_dict,
                                   title='RT60 Method Comparison',
                                   ax=ax4, show=False)

        ax5 = fig.add_subplot(gs[2, :])
        self.plot_sound_pressure_heatmap(receiver_positions, pressure_values,
                                          room_dims,
                                          title='Sound Pressure Distribution',
                                          ax=ax5, show=False)

        plt.suptitle('Acoustic Simulation Report', fontsize=16, y=0.995)

        if save_path:
            plt.savefig(save_path, dpi=self.dpi, bbox_inches='tight')
            logger.info(f"Report saved to {save_path}")

        plt.tight_layout()
        plt.show()

    def animate_dynamic_simulation(self, source_positions: np.ndarray,
                                    pressure_timeseries: np.ndarray,
                                    receiver_positions: np.ndarray,
                                    room_dims: np.ndarray,
                                    time_points: np.ndarray,
                                    save_path: Optional[str] = None,
                                    interval: int = 100) -> None:
        from matplotlib.animation import FuncAnimation

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6), dpi=self.dpi)

        rect = plt.Rectangle((0, 0), room_dims[0], room_dims[1],
                            fill=False, linewidth=2, color='black')
        ax1.add_patch(rect)
        ax1.set_aspect('equal')
        ax1.set_xlim([0, room_dims[0]])
        ax1.set_ylim([0, room_dims[1]])
        ax1.set_xlabel('X [m]')
        ax1.set_ylabel('Y [m]')
        ax1.grid(True, alpha=0.3)

        source_line, = ax1.plot([], [], 'k--', linewidth=1, alpha=0.5, label='Trajectory')
        source_point, = ax1.plot([], [], 'ro', markersize=10, markeredgecolor='black',
                                label='Source')
        rec_points = ax1.scatter(receiver_positions[:, 0], receiver_positions[:, 1],
                                c='blue', s=60, marker='o', edgecolors='black', label='Receivers')
        ax1.legend(loc='upper right')

        x_unique = np.sort(np.unique(receiver_positions[:, 0]))
        y_unique = np.sort(np.unique(receiver_positions[:, 1]))
        X, Y = np.meshgrid(x_unique, y_unique)

        P_init = np.zeros_like(X)
        vmax = np.max(20 * np.log10(np.abs(pressure_timeseries) + 1e-10))
        vmin = vmax - 60
        norm = Normalize(vmin=vmin, vmax=vmax)

        contour = ax2.contourf(X, Y, P_init, levels=np.linspace(vmin, vmax, 20),
                              cmap=cm.inferno, norm=norm)
        cbar = plt.colorbar(contour, ax=ax2)
        cbar.set_label('SPL [dB]')
        ax2.set_aspect('equal')
        ax2.set_xlabel('X [m]')
        ax2.set_ylabel('Y [m]')
        ax2.set_title('Sound Pressure Distribution')

        time_text = ax1.text(0.02, 0.98, '', transform=ax1.transAxes,
                            va='top', fontsize=12,
                            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        def init():
            source_line.set_data([], [])
            source_point.set_data([], [])
            time_text.set_text('')
            return source_line, source_point, time_text

        def update(frame):
            source_line.set_data(source_positions[:frame+1, 0],
                                source_positions[:frame+1, 1])
            source_point.set_data([source_positions[frame, 0]],
                                 [source_positions[frame, 1]])
            time_text.set_text(f'Time: {time_points[frame]:.2f}s')

            pressure = pressure_timeseries[frame].flatten()
            P = np.zeros_like(X)
            for i, xv in enumerate(x_unique):
                for j, yv in enumerate(y_unique):
                    mask = (receiver_positions[:, 0] == xv) & (receiver_positions[:, 1] == yv)
                    if np.any(mask):
                        P[j, i] = pressure[mask][0]
            P_db = 20 * np.log10(np.abs(P) + 1e-10)

            for coll in ax2.collections:
                coll.remove()
            ax2.contourf(X, Y, P_db, levels=np.linspace(vmin, vmax, 20),
                        cmap=cm.inferno, norm=norm)

            return source_line, source_point, time_text

        anim = FuncAnimation(fig, update, frames=len(time_points),
                            init_func=init, interval=interval, blit=False)

        if save_path:
            anim.save(save_path, writer='ffmpeg', fps=10)
            logger.info(f"Animation saved to {save_path}")

        plt.tight_layout()
        plt.show()
