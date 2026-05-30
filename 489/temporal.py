import numpy as np
import pandas as pd
from scipy.interpolate import interp1d, splrep, splev
from scipy.ndimage import gaussian_filter1d
import warnings
warnings.filterwarnings("ignore")

TEMPORAL_METHODS = [
    "linear",
    "spline",
    "polynomial",
    "rolling_mean",
    "gaussian",
    "akima",
]


def interpolate_temporal_series(dates, values, target_dates, method="linear", **kwargs):
    dates = pd.to_datetime(dates)
    target_dates = pd.to_datetime(target_dates)

    t_ordinal = np.array([d.toordinal() for d in dates])
    t_target = np.array([d.toordinal() for d in target_dates])

    sort_idx = np.argsort(t_ordinal)
    t_sorted = t_ordinal[sort_idx]
    v_sorted = np.array(values)[sort_idx]

    valid_mask = ~np.isnan(v_sorted)
    t_valid = t_sorted[valid_mask]
    v_valid = v_sorted[valid_mask]

    if len(t_valid) < 2:
        raise ValueError("Need at least 2 valid points for temporal interpolation")

    result = np.full(len(target_dates), np.nan)

    if method == "linear":
        f = interp1d(t_valid, v_valid, kind="linear",
                     fill_value="extrapolate", bounds_error=False)
        result = f(t_target)

    elif method == "spline":
        k = min(3, len(t_valid) - 1)
        try:
            tck = splrep(t_valid, v_valid, k=k)
            result = splev(t_target, tck)
        except Exception:
            f = interp1d(t_valid, v_valid, kind="linear",
                         fill_value="extrapolate", bounds_error=False)
            result = f(t_target)

    elif method == "polynomial":
        degree = kwargs.get("degree", 3)
        degree = min(degree, len(t_valid) - 1)
        coeffs = np.polyfit(t_valid - t_valid.mean(), v_valid, degree)
        result = np.polyval(coeffs, t_target - t_valid.mean())

    elif method == "rolling_mean":
        window = kwargs.get("window", 3)
        f = interp1d(t_valid, v_valid, kind="linear",
                     fill_value="extrapolate", bounds_error=False)
        dense_t = np.linspace(t_valid.min(), t_valid.max(), 1000)
        dense_v = f(dense_t)
        smoothed = gaussian_filter1d(dense_v, sigma=window)
        f_smooth = interp1d(dense_t, smoothed, kind="linear",
                            fill_value="extrapolate", bounds_error=False)
        result = f_smooth(t_target)

    elif method == "gaussian":
        sigma = kwargs.get("sigma", 1.0)
        result = np.zeros(len(t_target))
        for i, tt in enumerate(t_target):
            weights = np.exp(-((t_valid - tt)**2) / (2 * sigma**2))
            weights = weights / weights.sum()
            result[i] = np.sum(weights * v_valid)

    elif method == "akima":
        try:
            from scipy.interpolate import Akima1DInterpolator
            f = Akima1DInterpolator(t_valid, v_valid)
            result = f(t_target)
        except Exception:
            f = interp1d(t_valid, v_valid, kind="linear",
                         fill_value="extrapolate", bounds_error=False)
            result = f(t_target)

    return result


def fit_trend(dates, values, method="linear"):
    dates = pd.to_datetime(dates)
    t_ordinal = np.array([d.toordinal() for d in dates])
    values = np.array(values)

    valid_mask = ~np.isnan(values)
    t_valid = t_ordinal[valid_mask]
    v_valid = values[valid_mask]

    if method == "linear":
        coeffs = np.polyfit(t_valid, v_valid, 1)
        return {
            "slope": float(coeffs[0]),
            "intercept": float(coeffs[1]),
            "method": "linear"
        }
    elif method == "exponential":
        log_v = np.log(np.maximum(v_valid, 0.001))
        coeffs = np.polyfit(t_valid, log_v, 1)
        return {
            "growth_rate": float(np.exp(coeffs[0]) - 1),
            "initial": float(np.exp(coeffs[1])),
            "method": "exponential"
        }
    return None


def forecast_simple_ar(dates, values, steps=3, method="drift"):
    dates = pd.to_datetime(dates)
    values = np.array(values)
    valid_mask = ~np.isnan(values)
    valid_values = values[valid_mask]

    last_date = dates.max()
    future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=steps)

    if method == "drift":
        if len(valid_values) < 2:
            forecast = np.full(steps, valid_values[-1] if len(valid_values) else np.nan)
        else:
            last_val = valid_values[-1]
            first_val = valid_values[0]
            drift = (last_val - first_val) / max(len(valid_values) - 1, 1)
            forecast = last_val + np.arange(1, steps + 1) * drift

    elif method == "mean":
        forecast = np.full(steps, np.mean(valid_values))

    elif method == "last":
        forecast = np.full(steps, valid_values[-1] if len(valid_values) else np.nan)

    return {
        "forecast_dates": [d.strftime("%Y-%m-%d") for d in future_dates],
        "forecast_values": forecast.tolist(),
        "method": method
    }


def plot_temporal_interpolation(dates, values, target_dates, interpolated,
                                title="Temporal Interpolation",
                                figsize=(12, 5), dpi=120):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    dates = pd.to_datetime(dates)
    target_dates = pd.to_datetime(target_dates)

    ax.scatter(dates, values, c="steelblue", s=40, edgecolors="white",
               linewidths=1, zorder=5, label="Observed")
    ax.plot(target_dates, interpolated, "r-", lw=2, label="Interpolated", alpha=0.8)

    ax.set_xlabel("Date", fontsize=11)
    ax.set_ylabel("Value", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def plot_forecast(dates, values, forecast_dates, forecast_values,
                  forecast_lower=None, forecast_upper=None,
                  title="Time Series Forecast",
                  figsize=(12, 5), dpi=120):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    dates = pd.to_datetime(dates)
    forecast_dates = pd.to_datetime(forecast_dates)

    ax.plot(dates, values, "b-", lw=2, label="Historical", alpha=0.8)
    ax.plot(forecast_dates, forecast_values, "r-", lw=2, label="Forecast", alpha=0.8)
    ax.scatter(forecast_dates, forecast_values, c="red", s=40, zorder=5)

    if forecast_lower is not None and forecast_upper is not None:
        ax.fill_between(forecast_dates, forecast_lower, forecast_upper,
                        color="red", alpha=0.2, label="Confidence Interval")

    ax.set_xlabel("Date", fontsize=11)
    ax.set_ylabel("Value", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig
