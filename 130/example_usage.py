import sys
from pathlib import Path
import logging
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from climate_analysis import (
    ClimateDataReader,
    EOFAnalysis,
    TrendAnalysis,
    ClimateVisualizer,
    GridInterpolator,
    RegularGridInterpolator,
    optimal_chunks
)


def main():
    sample_data_path = Path("sample_data/sample_temperature.nc")

    if not sample_data_path.exists():
        logger.info("示例数据不存在，正在生成...")
        from generate_sample_data import generate_sample_climate_data
        generate_sample_climate_data()

    logger.info("=" * 60)
    logger.info("1. 数据读取与Dask Chunk优化")
    logger.info("=" * 60)

    reader = ClimateDataReader(target_chunk_mb=50)
    ds = reader.read_netcdf(sample_data_path, auto_chunk=True)

    logger.info(f"\n数据集信息:")
    logger.info(f"  维度: {dict(ds.dims)}")
    logger.info(f"  变量: {list(ds.data_vars)}")

    memory_usage = reader.get_memory_usage()
    logger.info(f"  内存使用: {memory_usage['temperature']:.2f} MB")

    reader.rechunk(target_size_mb=100)

    temp_clim = reader.climatology("temperature", lazy=True)
    temp_clim_computed = reader.compute(temp_clim, show_progress=True)

    logger.info(f"气候态温度范围: {temp_clim_computed.min().values:.2f} ~ {temp_clim_computed.max().values:.2f} degC")

    logger.info("\n" + "=" * 60)
    logger.info("2. 非规则网格插值")
    logger.info("=" * 60)

    source_lon = ds.lon.values
    source_lat = ds.lat.values

    target_lon = np.linspace(0, 360, 180, endpoint=False)
    target_lat = np.linspace(-90, 90, 90)

    logger.info(f"原始网格: {len(source_lon)} x {len(source_lat)}")
    logger.info(f"目标网格: {len(target_lon)} x {len(target_lat)}")

    interpolator = RegularGridInterpolator(
        source_lon=source_lon,
        source_lat=source_lat,
        target_lon=target_lon,
        target_lat=target_lat
    )

    temp_data = reader.get_variable("temperature")
    temp_interpolated = interpolator.interpolate_xarray(temp_data, lazy=True)

    logger.info(f"插值后数据维度: {dict(temp_interpolated.dims)}")

    temp_interpolated_computed = reader.compute(temp_interpolated.isel(time=0))
    logger.info("插值完成")

    logger.info("\n" + "=" * 60)
    logger.info("3. EOF分析 (sklearn PCA)")
    logger.info("=" * 60)

    temp_anomaly = reader.anomaly("temperature", lazy=True)

    eof_analysis = EOFAnalysis(temp_anomaly)
    eofs, pcs, eigenvalues = eof_analysis.fit(
        n_modes=10,
        apply_weights=True,
        use_incremental=False,
        lazy=True
    )

    explained_var = eof_analysis.get_explained_variance_ratio()
    logger.info(f"\n前5个模态解释方差:")
    for i, var in enumerate(explained_var[:5], 1):
        logger.info(f"  模式 {i}: {var:.2%}")
    logger.info(f"  前5个模态累计: {explained_var[:5].sum():.2%}")

    reconstructed = eof_analysis.reconstruct(modes=[1, 2, 3], lazy=True)
    logger.info(f"EOF重建完成")

    logger.info("\n" + "=" * 60)
    logger.info("4. 趋势分析 (t检验)")
    logger.info("=" * 60)

    trend_analysis = TrendAnalysis(ds.temperature)
    trend, p_value = trend_analysis.linear_trend(lazy=True)

    sig_percent = (p_value < 0.05).mean().values * 100
    logger.info(f"显著上升/下降趋势的格点比例: {sig_percent:.1f}%")
    logger.info(f"全球平均温度趋势: {trend.mean().values:.2f} degC / 20年")

    t_summary = trend_analysis.t_test_summary(alpha=0.05)
    logger.info(f"\nt检验摘要:")
    logger.info(f"  显著格点比例: {(t_summary.significant).mean().values*100:.1f}%")
    logger.info(f"  平均t统计量: {t_summary.t_statistic.mean().values:.2f}")

    z_stat, mk_p_value, theil_sen_slope = trend_analysis.mann_kendall_test(lazy=True)
    logger.info(f"\nMann-Kendall检验完成")
    logger.info(f"Theil-Sen斜率 (全球平均): {theil_sen_slope.mean().values*12*20:.2f} degC / 20年")

    logger.info("\n" + "=" * 60)
    logger.info("5. 可视化")
    logger.info("=" * 60)

    visualizer = ClimateVisualizer(figsize=(14, 8), dpi=100)

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    logger.info("\n生成气候态热力图...")
    visualizer.plot_heatmap(
        temp_clim_computed,
        title="2000-2019年平均地表温度",
        cmap="RdYlBu_r",
        colorbar_label="Temperature (degC)",
        output_path=str(output_dir / "climatology_temperature.png")
    )

    logger.info("生成趋势显著性图 (t检验)...")
    visualizer.plot_trend_with_significance(
        trend,
        p_value,
        alpha=0.05,
        title="2000-2019年温度趋势 (点表示p<0.05显著, t检验)",
        output_path=str(output_dir / "temperature_trend_t_test.png")
    )

    logger.info("生成EOF模态图...")
    visualizer.plot_eof_modes(
        eofs,
        explained_var,
        n_modes=4,
        output_path=str(output_dir / "eof_modes.png")
    )

    logger.info("生成主成分时间序列...")
    visualizer.plot_pcs(
        pcs,
        explained_var,
        n_modes=4,
        output_path=str(output_dir / "pc_timeseries.png")
    )

    logger.info("生成解释方差图...")
    visualizer.plot_explained_variance(
        explained_var,
        title="EOF各模态解释方差比例",
        output_path=str(output_dir / "explained_variance.png")
    )

    nino34_index = ds.temperature.sel(lat=slice(-5, 5), lon=slice(190, 240)).mean(dim=["lat", "lon"])
    nino34_anomaly = nino34_index - nino34_index.mean()

    logger.info("生成Nino3.4指数时间序列...")
    visualizer.plot_time_series(
        nino34_anomaly,
        title="Nino 3.4 指数距平",
        ylabel="Temperature Anomaly (degC)",
        output_path=str(output_dir / "nino34_index.png")
    )

    logger.info("\n" + "=" * 60)
    logger.info("分析完成！")
    logger.info("=" * 60)
    logger.info(f"\n所有输出文件已保存到: {output_dir.absolute()}")
    logger.info("\n生成的文件:")
    for f in sorted(output_dir.glob("*.png")):
        logger.info(f"  - {f.name}")


if __name__ == "__main__":
    main()
