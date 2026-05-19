import sys
from pathlib import Path
import logging
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from climate_analysis import (
    ClimateDataReader,
    MJOIndex,
    CESMReader,
    SeasonalPredictor,
    CMIP6Downloader,
    CMIP6BiasCorrection,
    CMIP6Ensemble,
    FeatureAttribution,
    ClimateVisualizer
)


def example_mjo_analysis():
    logger.info("=" * 60)
    logger.info("示例 1: MJO (Madden-Julian Oscillation) 指数计算")
    logger.info("=" * 60)

    sample_data_path = Path("sample_data/sample_temperature.nc")
    if not sample_data_path.exists():
        from generate_sample_data import generate_sample_climate_data
        generate_sample_climate_data()

    reader = ClimateDataReader()
    ds = reader.read_netcdf(sample_data_path)

    mjo = MJOIndex()

    olr_data = ds.temperature * 0.1 + 200
    u850_data = ds.temperature * 0.01 - 5
    u200_data = ds.temperature * 0.02 + 10

    try:
        mjo_result = mjo.compute_rmm(
            olr=olr_data,
            u850=u850_data,
            u200=u200_data,
            n_modes=2
        )

        logger.info(f"\nMJO RMM 指数计算完成:")
        logger.info(f"  RMM1 范围: {mjo_result.rmm1.min().values:.3f} ~ {mjo_result.rmm1.max().values:.3f}")
        logger.info(f"  RMM2 范围: {mjo_result.rmm2.min().values:.3f} ~ {mjo_result.rmm2.max().values:.3f}")

        events = mjo.get_mjo_events(amplitude_threshold=1.0, min_duration=5)
        logger.info(f"\n检测到 {len(events)} 个MJO事件")
        if events:
            logger.info(f"  第一个事件: {events[0]['start_time']} 至 {events[0]['end_time']}")

        mjo_composite = mjo.phase_composite(ds.temperature, phase=3)
        logger.info(f"  第3位相合成温度平均值: {mjo_composite.mean().values:.2f}")

    except Exception as e:
        logger.warning(f"MJO计算示例跳过: {e}")


def example_cmip6_download():
    logger.info("\n" + "=" * 60)
    logger.info("示例 2: CMIP6 数据下载与加载")
    logger.info("=" * 60)

    downloader = CMIP6Downloader(download_dir="cmip6_data")

    download_list = [
        {"variable": "tas", "model": "CESM2", "experiment": "historical", "ensemble_member": "r1i1p1f1"},
        {"variable": "tas", "model": "CESM2", "experiment": "ssp585", "ensemble_member": "r1i1p1f1"},
    ]

    downloaded_files = downloader.batch_download(download_list, start_year=2000, end_year=2014)

    logger.info(f"\n下载的文件:")
    for f in downloaded_files:
        logger.info(f"  - {f.name}")

    if downloaded_files:
        ds = downloader.load_downloaded(downloaded_files[0])
        logger.info(f"\n加载的数据维度: {dict(ds.dims)}")
        logger.info(f"  温度范围: {ds.tas.min().values:.2f} ~ {ds.tas.max().values:.2f} K")


def example_seasonal_prediction():
    logger.info("\n" + "=" * 60)
    logger.info("示例 3: 季节预测与集合分析")
    logger.info("=" * 60)

    cesm_reader = CESMReader()
    ensemble_data = cesm_reader.read_ensemble(
        variable="temperature",
        experiment="historical"
    )

    logger.info(f"\n集合数据维度: {dict(ensemble_data.dims)}")

    ensemble_mean = cesm_reader.ensemble_mean(ensemble_data)
    ensemble_spread = cesm_reader.ensemble_spread(ensemble_data)

    logger.info(f"  集合平均温度范围: {ensemble_mean.min().values:.2f} ~ {ensemble_mean.max().values:.2f}")
    logger.info(f"  集合标准差范围: {ensemble_spread.min().values:.2f} ~ {ensemble_spread.max().values:.2f}")

    predictor = SeasonalPredictor()
    predictors, predictand = predictor.prepare_predictors(
        ensemble_mean,
        season="DJF",
        lag_months=1
    )

    try:
        coefficients, intercept = predictor.fit_linear_regression(predictors, predictand)
        logger.info(f"\n线性回归模型训练完成")
        logger.info(f"  系数范围: {coefficients.min().values:.4f} ~ {coefficients.max().values:.4f}")
    except Exception as e:
        logger.warning(f"线性回归训练跳过: {e}")

    visualizer = ClimateVisualizer()
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    try:
        visualizer.plot_heatmap(
            ensemble_mean.isel(time=0) if "time" in ensemble_mean.dims else ensemble_mean,
            title="CESM 集合平均温度",
            output_path=str(output_dir / "cesm_ensemble_mean.png")
        )
        logger.info(f"\n集合平均热力图已保存")
    except Exception as e:
        logger.warning(f"绘图跳过: {e}")


def example_bias_correction():
    logger.info("\n" + "=" * 60)
    logger.info("示例 4: CMIP6 偏差校正")
    logger.info("=" * 60)

    downloader = CMIP6Downloader(download_dir="cmip6_data")
    model_file = downloader.download_from_esgf(
        variable="tas",
        model="CESM2",
        experiment="historical",
        start_year=2000,
        end_year=2014
    )

    model_ds = downloader.load_downloaded(model_file)
    model_data = model_ds.tas

    obs_data = model_data + np.random.randn(*model_data.shape) * 0.5 - 0.3

    bias_corrector = CMIP6BiasCorrection()

    corrected_mean = bias_corrector.mean_adjustment(model_data, obs_data)
    corrected_qm = bias_corrector.quantile_mapping(model_data, obs_data, n_quantiles=100)

    original_bias = (model_data - obs_data).mean().values
    corrected_bias_mean = (corrected_mean - obs_data).mean().values
    corrected_bias_qm = (corrected_qm - obs_data).mean().values

    logger.info(f"\n偏差校正结果:")
    logger.info(f"  原始偏差: {original_bias:.4f} K")
    logger.info(f"  均值调整后偏差: {corrected_bias_mean:.4f} K")
    logger.info(f"  分位数映射后偏差: {corrected_bias_qm:.4f} K")


def example_feature_attribution():
    logger.info("\n" + "=" * 60)
    logger.info("示例 5: 特征归因分析")
    logger.info("=" * 60)

    sample_data_path = Path("sample_data/sample_temperature.nc")
    reader = ClimateDataReader()
    ds = reader.read_netcdf(sample_data_path)

    predictor_data = ds.temperature.isel(time=slice(0, -1))
    predictand_data = ds.temperature.isel(time=slice(1, None)).mean(dim=["lat", "lon"])

    if len(predictor_data.time) != len(predictand_data.time):
        predictor_data = predictor_data.isel(time=slice(0, len(predictand_data.time)))

    attribution = FeatureAttribution()

    try:
        corr_attribution = attribution.correlation_attribution(predictor_data, predictand_data)
        logger.info(f"\n相关系数归因完成")
        logger.info(f"  相关系数范围: {corr_attribution.min().values:.4f} ~ {corr_attribution.max().values:.4f}")
    except Exception as e:
        logger.warning(f"相关系数归因跳过: {e}")

    try:
        linear_attribution = attribution.linear_attribution(predictor_data, predictand_data)
        logger.info(f"\n线性回归归因完成")
        logger.info(f"  回归系数范围: {linear_attribution.min().values:.4f} ~ {linear_attribution.max().values:.4f}")
    except Exception as e:
        logger.warning(f"线性回归归因跳过: {e}")


def example_ensemble_analysis():
    logger.info("\n" + "=" * 60)
    logger.info("示例 6: 多成员集合分析")
    logger.info("=" * 60)

    downloader = CMIP6Downloader(download_dir="cmip6_data")

    ensemble = CMIP6Ensemble()

    for member_id in ["r1i1p1f1", "r2i1p1f1", "r3i1p1f1"]:
        member_file = downloader.download_from_esgf(
            variable="tas",
            model="CESM2",
            experiment="historical",
            ensemble_member=member_id,
            start_year=2000,
            end_year=2010
        )
        ds = downloader.load_downloaded(member_file)
        ensemble.add_member(ds.tas, member_id)

    ensemble_stats = ensemble.compute_ensemble_stats()

    logger.info(f"\n集合统计完成:")
    logger.info(f"  集合平均维度: {dict(ensemble_stats.ensemble_mean.dims)}")
    logger.info(f"  集合标准差范围: {ensemble_stats.ensemble_std.min().values:.4f} ~ {ensemble_stats.ensemble_std.max().values:.4f}")

    warming_threshold = 273.15 + 1.5
    prob_warming = ensemble.get_probability(warming_threshold, comparison="greater")
    logger.info(f"  超过 {warming_threshold-273.15:.1f}°C 的概率范围: {prob_warming.min().values:.2%} ~ {prob_warming.max().values:.2%}")


def main():
    logger.info("=" * 60)
    logger.info("气候数据分析库 - 高级功能示例")
    logger.info("=" * 60)

    try:
        example_mjo_analysis()
    except Exception as e:
        logger.error(f"MJO分析示例失败: {e}")

    try:
        example_cmip6_download()
    except Exception as e:
        logger.error(f"CMIP6下载示例失败: {e}")

    try:
        example_seasonal_prediction()
    except Exception as e:
        logger.error(f"季节预测示例失败: {e}")

    try:
        example_bias_correction()
    except Exception as e:
        logger.error(f"偏差校正示例失败: {e}")

    try:
        example_feature_attribution()
    except Exception as e:
        logger.error(f"特征归因示例失败: {e}")

    try:
        example_ensemble_analysis()
    except Exception as e:
        logger.error(f"集合分析示例失败: {e}")

    logger.info("\n" + "=" * 60)
    logger.info("所有示例执行完成!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
