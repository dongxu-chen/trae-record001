import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from typing import Optional, Tuple, List
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ClimateVisualizer:
    def __init__(self, figsize: Tuple[int, int] = (12, 8), dpi: int = 100):
        self.figsize = figsize
        self.dpi = dpi

    def plot_heatmap(
        self,
        data: xr.DataArray,
        title: str = "Climate Heatmap",
        cmap: str = "RdBu_r",
        vmin: Optional[float] = None,
        vmax: Optional[float] = None,
        levels: Optional[int] = None,
        projection: str = "PlateCarree",
        coastlines: bool = True,
        country_borders: bool = True,
        gridlines: bool = True,
        colorbar: bool = True,
        colorbar_label: Optional[str] = None,
        output_path: Optional[str] = None,
        extent: Optional[List[float]] = None,
        central_longitude: float = 180
    ):
        logger.info(f"绘制热力图: {title}")

        proj_dict = {
            "PlateCarree": ccrs.PlateCarree(central_longitude=central_longitude),
            "Robinson": ccrs.Robinson(central_longitude=central_longitude),
            "Mollweide": ccrs.Mollweide(central_longitude=central_longitude),
            "LambertConformal": ccrs.LambertConformal(central_longitude=central_longitude)
        }
        proj = proj_dict.get(projection, ccrs.PlateCarree(central_longitude=central_longitude))

        fig, ax = plt.subplots(
            figsize=self.figsize,
            dpi=self.dpi,
            subplot_kw={"projection": proj}
        )

        if extent:
            ax.set_extent(extent, crs=ccrs.PlateCarree())

        if coastlines:
            ax.coastlines(linewidth=0.5, resolution="110m")
        if country_borders:
            ax.add_feature(cfeature.BORDERS, linewidth=0.5, edgecolor="gray")

        if gridlines:
            gl = ax.gridlines(
                crs=ccrs.PlateCarree(),
                draw_labels=True,
                linewidth=0.5,
                color="gray",
                alpha=0.5,
                linestyle="--"
            )
            gl.top_labels = False
            gl.right_labels = False

        lons = data.lon.values
        lats = data.lat.values
        values = data.values

        if levels is None:
            levels = 20

        if vmin is None:
            vmin = np.nanmin(values)
        if vmax is None:
            vmax = np.nanmax(values)

        contour = ax.contourf(
            lons, lats, values,
            transform=ccrs.PlateCarree(),
            cmap=cmap,
            levels=levels,
            vmin=vmin,
            vmax=vmax,
            extend="both"
        )

        if colorbar:
            cb = plt.colorbar(
                contour,
                ax=ax,
                orientation="horizontal",
                pad=0.08,
                shrink=0.8
            )
            if colorbar_label:
                cb.set_label(colorbar_label, fontsize=12)

        ax.set_title(title, fontsize=14, pad=20)

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(output_path, bbox_inches="tight", dpi=self.dpi)
            logger.info(f"热力图已保存到: {output_path}")

        plt.close()
        return fig, ax

    def plot_trend_with_significance(
        self,
        trend_data: xr.DataArray,
        p_value: xr.DataArray,
        alpha: float = 0.05,
        title: str = "Trend with Significance",
        cmap: str = "RdBu_r",
        output_path: Optional[str] = None,
        **kwargs
    ):
        logger.info(f"绘制带显著性的趋势图: {title}")

        fig, ax = plt.subplots(
            figsize=self.figsize,
            dpi=self.dpi,
            subplot_kw={"projection": ccrs.PlateCarree(central_longitude=180)}
        )

        ax.coastlines(linewidth=0.5)
        ax.add_feature(cfeature.BORDERS, linewidth=0.5, edgecolor="gray")

        gl = ax.gridlines(
            crs=ccrs.PlateCarree(),
            draw_labels=True,
            linewidth=0.5,
            color="gray",
            alpha=0.5,
            linestyle="--"
        )
        gl.top_labels = False
        gl.right_labels = False

        lons = trend_data.lon.values
        lats = trend_data.lat.values
        trends = trend_data.values
        sig_mask = p_value.values < alpha

        vmax = np.nanmax(np.abs(trends))
        vmin = -vmax

        contour = ax.contourf(
            lons, lats, trends,
            transform=ccrs.PlateCarree(),
            cmap=cmap,
            levels=20,
            vmin=vmin,
            vmax=vmax,
            extend="both"
        )

        sig_lons, sig_lats = np.meshgrid(lons, lats)
        sig_lons = sig_lons[sig_mask]
        sig_lats = sig_lats[sig_mask]

        ax.scatter(
            sig_lons, sig_lats,
            transform=ccrs.PlateCarree(),
            marker=".",
            color="black",
            s=1,
            alpha=0.5
        )

        cb = plt.colorbar(
            contour,
            ax=ax,
            orientation="horizontal",
            pad=0.08,
            shrink=0.8
        )
        cb.set_label("Trend", fontsize=12)

        ax.set_title(title, fontsize=14, pad=20)

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(output_path, bbox_inches="tight", dpi=self.dpi)
            logger.info(f"趋势图已保存到: {output_path}")

        plt.close()
        return fig, ax

    def plot_eof_modes(
        self,
        eofs: xr.DataArray,
        explained_variance_ratio: np.ndarray,
        n_modes: int = 4,
        output_path: Optional[str] = None,
        **kwargs
    ):
        logger.info(f"绘制前 {n_modes} 个EOF模态")

        fig, axes = plt.subplots(
            n_modes, 1,
            figsize=(12, 6 * n_modes),
            dpi=self.dpi,
            subplot_kw={"projection": ccrs.PlateCarree(central_longitude=180)}
        )
        if n_modes == 1:
            axes = [axes]

        for i, ax in enumerate(axes):
            mode = i + 1
            eof_data = eofs.sel(mode=mode)

            ax.coastlines(linewidth=0.5)
            ax.add_feature(cfeature.BORDERS, linewidth=0.5, edgecolor="gray")

            gl = ax.gridlines(
                crs=ccrs.PlateCarree(),
                draw_labels=True,
                linewidth=0.5,
                color="gray",
                alpha=0.5,
                linestyle="--"
            )
            gl.top_labels = False
            gl.right_labels = False

            lons = eof_data.lon.values
            lats = eof_data.lat.values
            values = eof_data.values

            vmax = np.nanmax(np.abs(values))
            vmin = -vmax

            contour = ax.contourf(
                lons, lats, values,
                transform=ccrs.PlateCarree(),
                cmap="RdBu_r",
                levels=20,
                vmin=vmin,
                vmax=vmax,
                extend="both"
            )

            plt.colorbar(
                contour,
                ax=ax,
                orientation="horizontal",
                pad=0.08,
                shrink=0.8
            )

            variance = explained_variance_ratio[i] * 100
            ax.set_title(
                f"EOF Mode {mode} ({variance:.1f}% variance)",
                fontsize=12,
                pad=15
            )

        plt.tight_layout()

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(output_path, bbox_inches="tight", dpi=self.dpi)
            logger.info(f"EOF模态图已保存到: {output_path}")

        plt.close()
        return fig, axes

    def plot_time_series(
        self,
        data: xr.DataArray,
        title: str = "Time Series",
        ylabel: str = "Value",
        output_path: Optional[str] = None,
        **kwargs
    ):
        logger.info(f"绘制时间序列: {title}")

        fig, ax = plt.subplots(figsize=self.figsize, dpi=self.dpi)

        times = data.time.values
        values = data.values

        ax.plot(times, values, linewidth=2, color="steelblue")

        ax.set_xlabel("Time", fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(title, fontsize=14, pad=15)
        ax.grid(True, alpha=0.3)

        plt.xticks(rotation=45)

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(output_path, bbox_inches="tight", dpi=self.dpi)
            logger.info(f"时间序列图已保存到: {output_path}")

        plt.close()
        return fig, ax

    def plot_pcs(
        self,
        pcs: xr.DataArray,
        explained_variance_ratio: np.ndarray,
        n_modes: int = 4,
        output_path: Optional[str] = None,
        **kwargs
    ):
        logger.info(f"绘制前 {n_modes} 个主成分时间序列")

        fig, axes = plt.subplots(
            n_modes, 1,
            figsize=(12, 4 * n_modes),
            dpi=self.dpi
        )
        if n_modes == 1:
            axes = [axes]

        times = pcs.time.values

        for i, ax in enumerate(axes):
            mode = i + 1
            pc_data = pcs.sel(mode=mode).values

            ax.plot(times, pc_data, linewidth=1.5, color="steelblue")

            variance = explained_variance_ratio[i] * 100
            ax.set_title(
                f"PC {mode} ({variance:.1f}% variance)",
                fontsize=12,
                pad=10
            )
            ax.set_ylabel("Amplitude", fontsize=10)
            ax.grid(True, alpha=0.3)
            ax.tick_params(axis="x", rotation=45)

        plt.tight_layout()

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(output_path, bbox_inches="tight", dpi=self.dpi)
            logger.info(f"主成分时间序列图已保存到: {output_path}")

        plt.close()
        return fig, axes

    def plot_explained_variance(
        self,
        explained_variance_ratio: np.ndarray,
        title: str = "Explained Variance Ratio",
        output_path: Optional[str] = None,
        **kwargs
    ):
        logger.info("绘制解释方差图")

        fig, ax = plt.subplots(figsize=(10, 6), dpi=self.dpi)

        n_modes = len(explained_variance_ratio)
        modes = np.arange(1, n_modes + 1)
        cumulative = np.cumsum(explained_variance_ratio) * 100

        ax.bar(
            modes,
            explained_variance_ratio * 100,
            color="steelblue",
            alpha=0.7,
            label="Individual"
        )
        ax.plot(
            modes,
            cumulative,
            color="red",
            marker="o",
            linewidth=2,
            label="Cumulative"
        )

        ax.set_xlabel("EOF Mode", fontsize=12)
        ax.set_ylabel("Explained Variance (%)", fontsize=12)
        ax.set_title(title, fontsize=14, pad=15)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3, axis="y")
        ax.set_xticks(modes)

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(output_path, bbox_inches="tight", dpi=self.dpi)
            logger.info(f"解释方差图已保存到: {output_path}")

        plt.close()
        return fig, ax
