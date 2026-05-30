import os
import json
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from flask import Flask, render_template, request, jsonify

from interpolator import run_interpolation, make_grid, ALGORITHMS, KRIGE_VARIogram_MODELS, RBF_FUNCTIONS
from cross_validation import (loocv, kfold_cv, grid_search_cv,
                              auto_select_variogram, compute_station_errors)
from visualizer import (plot_contour, plot_cv_scatter, plot_variogram,
                        plot_error_heatmap, interpolate_error_to_grid, fig_to_base64)
from temporal import (TEMPORAL_METHODS, interpolate_temporal_series,
                      forecast_simple_ar, fit_trend,
                      plot_temporal_interpolation, plot_forecast)
from multivariate import (MULTIVAR_METHODS, interpolate_collocated_cokriging,
                           interpolate_regression_kriging, interpolate_simple_cokriging,
                           plot_cokriging_comparison)
from uncertainty import (compute_confidence_intervals, compute_uncertainty_summary,
                         classify_uncertainty, plot_uncertainty_band,
                         plot_probability_exceedance, generate_uncertainty_report)

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

SAMPLE_DATA_PATH = os.path.join("data", "sample_stations.csv")


SAMPLE_TEMPORAL_PATH = os.path.join("data", "sample_temporal.csv")


def _load_sample_data():
    if os.path.exists(SAMPLE_DATA_PATH):
        return pd.read_csv(SAMPLE_DATA_PATH)
    np.random.seed(42)
    n = 30
    lons = np.round(np.random.uniform(116.0, 117.5, n), 4)
    lats = np.round(np.random.uniform(39.0, 40.5, n), 4)
    temp = np.round(5 + 20 * np.exp(-0.02 * (lats - 39.0) ** 2) + np.random.normal(0, 1.5, n), 1)
    precip = np.round(200 + 300 * (lats - 39.0) / 1.5 + np.random.normal(0, 40, n), 1)
    df = pd.DataFrame({"station_id": [f"S{i+1:02d}" for i in range(n)],
                        "lon": lons, "lat": lats,
                        "temperature": temp, "precipitation": precip})
    os.makedirs(os.path.dirname(SAMPLE_DATA_PATH), exist_ok=True)
    df.to_csv(SAMPLE_DATA_PATH, index=False)
    return df


def _load_sample_temporal_data():
    if os.path.exists(SAMPLE_TEMPORAL_PATH):
        return pd.read_csv(SAMPLE_TEMPORAL_PATH)
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", periods=60, freq="D")
    base_temp = 15 + 10 * np.sin(np.linspace(0, 2 * np.pi, 60))
    temp = base_temp + np.random.normal(0, 2, 60)
    base_precip = 50 + 30 * np.sin(np.linspace(0, 4 * np.pi, 60))
    precip = np.maximum(0, base_precip + np.random.normal(0, 10, 60))
    df = pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "temperature": np.round(temp, 1),
        "precipitation": np.round(precip, 1),
    })
    os.makedirs(os.path.dirname(SAMPLE_TEMPORAL_PATH), exist_ok=True)
    df.to_csv(SAMPLE_TEMPORAL_PATH, index=False)
    return df


def _parse_params(algorithm, raw_params):
    params = {}
    if algorithm == "idw":
        params["power"] = float(raw_params.get("power", 2.0))
        params["max_neighbors"] = int(raw_params.get("max_neighbors", 12))
    elif algorithm == "ordinary_kriging":
        auto_model = str(raw_params.get("auto_variogram", "false")).lower() == "true"
        params["auto_variogram"] = auto_model
        if not auto_model:
            params["variogram_model"] = raw_params.get("variogram_model", "linear")
        params["nlags"] = int(raw_params.get("nlags", 6))
        params["weight"] = raw_params.get("weight", "true").lower() == "true"
        params["anisotropy_angle"] = float(raw_params.get("anisotropy_angle", 0.0))
        params["anisotropy_scaling"] = float(raw_params.get("anisotropy_scaling", 1.0))
    elif algorithm == "universal_kriging":
        auto_model = str(raw_params.get("auto_variogram", "false")).lower() == "true"
        params["auto_variogram"] = auto_model
        if not auto_model:
            params["variogram_model"] = raw_params.get("variogram_model", "linear")
        drift = raw_params.get("drift_terms", "regional_linear")
        params["drift_terms"] = [d.strip() for d in drift.split(",") if d.strip()]
        params["nlags"] = int(raw_params.get("nlags", 6))
        params["weight"] = raw_params.get("weight", "true").lower() == "true"
    elif algorithm == "rbf":
        params["function"] = raw_params.get("rbf_function", "multiquadric")
        eps = raw_params.get("epsilon", "")
        params["epsilon"] = float(eps) if eps else None
        params["smooth"] = float(raw_params.get("smooth", 0.0))

    params["adaptive_smooth_level"] = float(raw_params.get("adaptive_smooth_level", 0.0))
    params["preserve_extrema"] = str(raw_params.get("preserve_extrema", "true")).lower() == "true"
    params["show_error_heatmap"] = str(raw_params.get("show_error_heatmap", "false")).lower() == "true"
    return params


def _get_df(request_obj):
    if "file" in request_obj.files and request_obj.files["file"].filename:
        f = request_obj.files["file"]
        path = os.path.join(app.config["UPLOAD_FOLDER"], f.filename)
        f.save(path)
        ext = os.path.splitext(f.filename)[1].lower()
        if ext == ".csv":
            return pd.read_csv(path)
        elif ext in (".xlsx", ".xls"):
            return pd.read_excel(path)
        elif ext == ".geojson":
            gdf = gpd.read_file(path)
            gdf["lon"] = gdf.geometry.x
            gdf["lat"] = gdf.geometry.y
            return pd.DataFrame(gdf.drop(columns="geometry"))
        elif ext == ".shp":
            gdf = gpd.read_file(path)
            gdf["lon"] = gdf.geometry.x
            gdf["lat"] = gdf.geometry.y
            return pd.DataFrame(gdf.drop(columns="geometry"))
    return _load_sample_data()


def _get_temporal_df(request_obj):
    if "file" in request_obj.files and request_obj.files["file"].filename:
        f = request_obj.files["file"]
        path = os.path.join(app.config["UPLOAD_FOLDER"], f.filename)
        f.save(path)
        ext = os.path.splitext(f.filename)[1].lower()
        if ext == ".csv":
            return pd.read_csv(path)
        elif ext in (".xlsx", ".xls"):
            return pd.read_excel(path)
    return _load_sample_temporal_data()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/algorithms", methods=["GET"])
def get_algorithms():
    return jsonify({
        "algorithms": ALGORITHMS,
        "variogram_models": KRIGE_VARIogram_MODELS,
        "rbf_functions": RBF_FUNCTIONS,
        "temporal_methods": TEMPORAL_METHODS,
        "multivar_methods": MULTIVAR_METHODS,
    })


@app.route("/api/sample-data", methods=["GET"])
def get_sample_data():
    df = _load_sample_data()
    return jsonify(df.to_dict(orient="records"))


@app.route("/api/auto-select-variogram", methods=["POST"])
def api_auto_select_variogram():
    try:
        raw = request.form if request.form else request.get_json(force=True)
        if raw is None:
            raw = {}

        df = _get_df(request)
        algorithm = raw.get("algorithm", "ordinary_kriging")
        variable = raw.get("variable", "temperature")
        lon_col = raw.get("lon_col", "lon")
        lat_col = raw.get("lat_col", "lat")
        cv_method = raw.get("cv_method", "loocv")
        k = int(raw.get("k", 5))

        df_clean = df.dropna(subset=[lon_col, lat_col, variable])
        x = df_clean[lon_col].values.astype(float)
        y = df_clean[lat_col].values.astype(float)
        z = df_clean[variable].values.astype(float)

        base_params = _parse_params(algorithm, raw)
        extra_params = {}
        for kk in ["nlags", "weight", "anisotropy_angle", "anisotropy_scaling", "drift_terms"]:
            if kk in base_params:
                extra_params[kk] = base_params[kk]

        result = auto_select_variogram(x, y, z, algorithm=algorithm,
                                        cv_method=cv_method, k=k,
                                        extra_params=extra_params)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/interpolate", methods=["POST"])
def interpolate():
    try:
        raw = request.form if request.form else request.get_json(force=True)
        if raw is None:
            raw = {}

        df = _get_df(request)
        algorithm = raw.get("algorithm", "ordinary_kriging")
        variable = raw.get("variable", "temperature")
        lon_col = raw.get("lon_col", "lon")
        lat_col = raw.get("lat_col", "lat")

        if variable not in df.columns:
            return jsonify({"error": f"Column '{variable}' not found. Available: {list(df.columns)}"}), 400

        df_clean = df.dropna(subset=[lon_col, lat_col, variable])
        x = df_clean[lon_col].values.astype(float)
        y = df_clean[lat_col].values.astype(float)
        z = df_clean[variable].values.astype(float)

        nx = int(raw.get("nx", 100))
        ny = int(raw.get("ny", 100))

        margin_x = (x.max() - x.min()) * 0.05
        margin_y = (y.max() - y.min()) * 0.05
        grid_x, grid_y = make_grid(
            x.min() - margin_x, x.max() + margin_x,
            y.min() - margin_y, y.max() + margin_y,
            nx=nx, ny=ny,
        )

        params = _parse_params(algorithm, raw)
        smooth_level = params.pop("adaptive_smooth_level", 0.0)
        preserve_extrema = params.pop("preserve_extrema", True)
        show_error = params.pop("show_error_heatmap", False)
        auto_variogram = params.pop("auto_variogram", False)

        auto_result = None
        if auto_variogram and algorithm in ["ordinary_kriging", "universal_kriging"]:
            extra = {}
            for kk in ["nlags", "weight", "anisotropy_angle", "anisotropy_scaling", "drift_terms"]:
                if kk in params:
                    extra[kk] = params[kk]
            auto_result = auto_select_variogram(x, y, z, algorithm=algorithm,
                                                 cv_method="loocv", k=5,
                                                 extra_params=extra)
            params["variogram_model"] = auto_result["best_model"]

        grid_z, grid_var = run_interpolation(algorithm, x, y, z, grid_x, grid_y, **params)

        unit = "°C" if variable == "temperature" else "mm"
        label = f"{variable} ({unit})" if unit else variable

        fig = plot_contour(grid_x, grid_y, grid_z, x, y, z,
                           title=f"{algorithm} - {variable}",
                           label=label,
                           adaptive_smooth_level=smooth_level,
                           preserve_extrema=preserve_extrema)
        contour_b64 = fig_to_base64(fig)

        var_b64 = None
        if grid_var is not None and not np.all(np.isnan(grid_var)):
            fig_v = plot_variogram(grid_x, grid_y, grid_var, x, y,
                                   title=f"{algorithm} - Variance")
            var_b64 = fig_to_base64(fig_v)

        error_b64 = None
        error_grid = None
        if show_error:
            cv_params = {kk: vv for kk, vv in params.items()
                         if kk not in ["adaptive_smooth_level", "preserve_extrema"]}
            station_err = compute_station_errors(x, y, z, algorithm,
                                                  cv_method="loocv", k=5, **cv_params)
            error_grid = interpolate_error_to_grid(grid_x, grid_y,
                                                    station_err["x"],
                                                    station_err["y"],
                                                    station_err["absolute_error"])
            fig_err = plot_error_heatmap(grid_x, grid_y, error_grid,
                                          station_x=station_err["x"],
                                          station_y=station_err["y"],
                                          station_error=station_err["absolute_error"],
                                          title=f"Error Distribution - {algorithm} - {variable}",
                                          label=f"Absolute Error ({unit})")
            error_b64 = fig_to_base64(fig_err)

        response = {
            "algorithm": algorithm,
            "variable": variable,
            "params": {k: (v if not isinstance(v, np.integer) else int(v))
                        for k, v in params.items()
                        if k not in ["auto_variogram"]},
            "statistics": {
                "min": round(float(np.nanmin(grid_z)), 4),
                "max": round(float(np.nanmax(grid_z)), 4),
                "mean": round(float(np.nanmean(grid_z)), 4),
                "std": round(float(np.nanstd(grid_z)), 4),
            },
            "contour_image": contour_b64,
            "variance_image": var_b64,
            "error_image": error_b64,
        }
        if auto_result is not None:
            response["auto_variogram_result"] = auto_result

        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/cross-validate", methods=["POST"])
def cross_validate():
    try:
        raw = request.form if request.form else request.get_json(force=True)
        if raw is None:
            raw = {}

        df = _get_df(request)
        algorithm = raw.get("algorithm", "ordinary_kriging")
        variable = raw.get("variable", "temperature")
        lon_col = raw.get("lon_col", "lon")
        lat_col = raw.get("lat_col", "lat")
        cv_method = raw.get("cv_method", "loocv")
        k = int(raw.get("k", 5))

        df_clean = df.dropna(subset=[lon_col, lat_col, variable])
        x = df_clean[lon_col].values.astype(float)
        y = df_clean[lat_col].values.astype(float)
        z = df_clean[variable].values.astype(float)

        params = _parse_params(algorithm, raw)
        params.pop("adaptive_smooth_level", None)
        params.pop("preserve_extrema", None)
        params.pop("show_error_heatmap", None)
        auto_variogram = params.pop("auto_variogram", False)

        if auto_variogram and algorithm in ["ordinary_kriging", "universal_kriging"]:
            extra = {}
            for kk in ["nlags", "weight", "anisotropy_angle", "anisotropy_scaling", "drift_terms"]:
                if kk in params:
                    extra[kk] = params[kk]
            auto_result = auto_select_variogram(x, y, z, algorithm=algorithm,
                                                 cv_method=cv_method, k=k,
                                                 extra_params=extra)
            params["variogram_model"] = auto_result["best_model"]

        if cv_method == "loocv":
            result = loocv(x, y, z, algorithm, **params)
        else:
            result = kfold_cv(x, y, z, algorithm, k=k, **params)

        obs = result.pop("observed", [])
        pred = result.pop("predicted", [])

        fig = plot_cv_scatter(obs, pred, title=f"CV ({cv_method}) - {algorithm} - {variable}")
        scatter_b64 = fig_to_base64(fig)

        result["scatter_image"] = scatter_b64
        if auto_variogram and algorithm in ["ordinary_kriging", "universal_kriging"]:
            result["auto_variogram_result"] = auto_result
            result["params"] = params

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/grid-search", methods=["POST"])
def grid_search():
    try:
        raw = request.form if request.form else request.get_json(force=True)
        if raw is None:
            raw = {}

        df = _get_df(request)
        algorithm = raw.get("algorithm", "ordinary_kriging")
        variable = raw.get("variable", "temperature")
        lon_col = raw.get("lon_col", "lon")
        lat_col = raw.get("lat_col", "lat")
        cv_method = raw.get("cv_method", "loocv")
        param_grid_json = raw.get("param_grid", "{}")

        df_clean = df.dropna(subset=[lon_col, lat_col, variable])
        x = df_clean[lon_col].values.astype(float)
        y = df_clean[lat_col].values.astype(float)
        z = df_clean[variable].values.astype(float)

        if isinstance(param_grid_json, str):
            param_grid = json.loads(param_grid_json)
        else:
            param_grid = param_grid_json

        result = grid_search_cv(x, y, z, algorithm, param_grid, cv_method=cv_method)
        for r in result.get("all_results", []):
            r.pop("predicted", None)
            r.pop("observed", None)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/export-geojson", methods=["POST"])
def export_geojson():
    try:
        raw = request.form if request.form else request.get_json(force=True)
        if raw is None:
            raw = {}

        df = _get_df(request)
        algorithm = raw.get("algorithm", "ordinary_kriging")
        variable = raw.get("variable", "temperature")
        lon_col = raw.get("lon_col", "lon")
        lat_col = raw.get("lat_col", "lat")
        nx = int(raw.get("nx", 50))
        ny = int(raw.get("ny", 50))

        df_clean = df.dropna(subset=[lon_col, lat_col, variable])
        x = df_clean[lon_col].values.astype(float)
        y = df_clean[lat_col].values.astype(float)
        z = df_clean[variable].values.astype(float)

        margin_x = (x.max() - x.min()) * 0.05
        margin_y = (y.max() - y.min()) * 0.05
        grid_x, grid_y = make_grid(
            x.min() - margin_x, x.max() + margin_x,
            y.min() - margin_y, y.max() + margin_y,
            nx=nx, ny=ny,
        )

        params = _parse_params(algorithm, raw)
        params.pop("adaptive_smooth_level", None)
        params.pop("preserve_extrema", None)
        params.pop("show_error_heatmap", None)
        auto_variogram = params.pop("auto_variogram", False)

        if auto_variogram and algorithm in ["ordinary_kriging", "universal_kriging"]:
            extra = {}
            for kk in ["nlags", "weight", "anisotropy_angle", "anisotropy_scaling", "drift_terms"]:
                if kk in params:
                    extra[kk] = params[kk]
            auto_result = auto_select_variogram(x, y, z, algorithm=algorithm,
                                                 cv_method="loocv", k=5,
                                                 extra_params=extra)
            params["variogram_model"] = auto_result["best_model"]

        grid_z, _ = run_interpolation(algorithm, x, y, z, grid_x, grid_y, **params)

        features = []
        for i in range(grid_x.shape[0]):
            for j in range(grid_x.shape[1]):
                val = grid_z[i, j]
                if np.isnan(val):
                    continue
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [float(grid_x[i, j]), float(grid_y[i, j])]},
                    "properties": {variable: round(float(val), 4)},
                })

        geojson = {"type": "FeatureCollection", "features": features}
        return jsonify(geojson)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/temporal-interpolate", methods=["POST"])
def temporal_interpolate():
    try:
        raw = request.form if request.form else request.get_json(force=True)
        if raw is None:
            raw = {}

        df = _get_temporal_df(request)
        variable = raw.get("variable", "temperature")
        date_col = raw.get("date_col", "date")
        value_col = raw.get("value_col", variable)
        method = raw.get("temporal_method", "linear")
        target_start = raw.get("target_start", "")
        target_end = raw.get("target_end", "")
        steps = int(raw.get("steps", 10))

        if date_col not in df.columns:
            return jsonify({"error": f"Date column '{date_col}' not found. Available: {list(df.columns)}"}), 400
        if variable not in df.columns:
            return jsonify({"error": f"Variable column '{variable}' not found. Available: {list(df.columns)}"}), 400

        df_sorted = df.sort_values(date_col)
        dates = df_sorted[date_col].values
        values = df_sorted[variable].values.astype(float)

        if target_start and target_end:
            target_dates = pd.date_range(start=target_start, end=target_end, periods=steps)
        else:
            last_date = pd.to_datetime(dates).max()
            target_dates = pd.date_range(start=last_date, periods=steps + 1)[1:]

        interpolated = interpolate_temporal_series(dates, values, target_dates, method=method)

        fig = plot_temporal_interpolation(dates, values, target_dates, interpolated,
                                          title=f"Temporal Interpolation ({method}) - {variable}")
        plot_b64 = fig_to_base64(fig)

        trend = fit_trend(dates, values, method="linear")

        return jsonify({
            "method": method,
            "variable": variable,
            "trend": trend,
            "original_dates": [str(d) for d in dates],
            "original_values": [float(v) for v in values],
            "target_dates": [d.strftime("%Y-%m-%d") for d in target_dates],
            "interpolated_values": [float(v) for v in interpolated],
            "plot_image": plot_b64,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/forecast", methods=["POST"])
def forecast():
    try:
        raw = request.form if request.form else request.get_json(force=True)
        if raw is None:
            raw = {}

        df = _get_temporal_df(request)
        variable = raw.get("variable", "temperature")
        date_col = raw.get("date_col", "date")
        method = raw.get("forecast_method", "drift")
        steps = int(raw.get("steps", 5))

        if variable not in df.columns:
            return jsonify({"error": f"Variable column '{variable}' not found. Available: {list(df.columns)}"}), 400

        if date_col in df.columns:
            df_sorted = df.sort_values(date_col)
            dates = df_sorted[date_col].values
            values = df_sorted[variable].values.astype(float)
        else:
            dates = pd.date_range(start="2024-01-01", periods=len(df))
            values = df[variable].values.astype(float)

        forecast_result = forecast_simple_ar(dates, values, steps=steps, method=method)

        fig = plot_forecast(dates, values,
                            forecast_result["forecast_dates"],
                            forecast_result["forecast_values"],
                            title=f"Forecast ({method}) - {variable}")
        plot_b64 = fig_to_base64(fig)

        return jsonify({
            "method": method,
            "variable": variable,
            "forecast_dates": forecast_result["forecast_dates"],
            "forecast_values": [float(v) for v in forecast_result["forecast_values"]],
            "plot_image": plot_b64,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/cokriging", methods=["POST"])
def cokriging():
    try:
        raw = request.form if request.form else request.get_json(force=True)
        if raw is None:
            raw = {}

        df = _get_df(request)
        primary_var = raw.get("primary_variable", "temperature")
        secondary_var = raw.get("secondary_variable", "precipitation")
        method = raw.get("cokriging_method", "collocated_cokriging")
        lon_col = raw.get("lon_col", "lon")
        lat_col = raw.get("lat_col", "lat")
        variogram_model = raw.get("variogram_model", "linear")
        nx = int(raw.get("nx", 50))
        ny = int(raw.get("ny", 50))

        for v in [primary_var, secondary_var]:
            if v not in df.columns:
                return jsonify({"error": f"Column '{v}' not found"}), 400

        df_clean = df.dropna(subset=[lon_col, lat_col, primary_var, secondary_var])
        x = df_clean[lon_col].values.astype(float)
        y = df_clean[lat_col].values.astype(float)
        z_prim = df_clean[primary_var].values.astype(float)
        z_sec = df_clean[secondary_var].values.astype(float)

        margin_x = (x.max() - x.min()) * 0.05
        margin_y = (y.max() - y.min()) * 0.05
        grid_x, grid_y = make_grid(
            x.min() - margin_x, x.max() + margin_x,
            y.min() - margin_y, y.max() + margin_y,
            nx=nx, ny=ny,
        )

        if method == "collocated_cokriging":
            z_co, var_co, z_prim_grid, z_sec_grid = interpolate_collocated_cokriging(
                x, y, z_prim, x, y, z_sec,
                grid_x, grid_y,
                variogram_model=variogram_model
            )
        elif method == "regression_kriging":
            z_co, var_co, z_prim_grid, z_sec_grid = interpolate_collocated_cokriging(
                x, y, z_prim, x, y, z_sec,
                grid_x, grid_y,
                variogram_model=variogram_model
            )
            z_co_rk, var_co_rk = interpolate_regression_kriging(
                x, y, z_prim, x, y, z_sec,
                grid_x, grid_y,
                variogram_model=variogram_model
            )
            z_co, var_co = z_co_rk, var_co_rk
        else:
            z_co, var_co, z_prim_grid, z_sec_grid = interpolate_collocated_cokriging(
                x, y, z_prim, x, y, z_sec,
                grid_x, grid_y,
                variogram_model=variogram_model
            )

        fig = plot_cokriging_comparison(grid_x, grid_y, z_prim_grid, z_sec_grid, z_co,
                                         title=f"Co-Kriging ({method})",
                                         label_primary=primary_var,
                                         label_secondary=secondary_var)
        comp_b64 = fig_to_base64(fig)

        min_len = min(len(z_prim), len(z_sec))
        correlation = float(np.corrcoef(z_prim[:min_len], z_sec[:min_len])[0, 1])

        return jsonify({
            "method": method,
            "primary_variable": primary_var,
            "secondary_variable": secondary_var,
            "correlation": round(correlation, 4),
            "variogram_model": variogram_model,
            "statistics": {
                "primary": {
                    "min": round(float(np.nanmin(z_prim_grid)), 4),
                    "max": round(float(np.nanmax(z_prim_grid)), 4),
                    "mean": round(float(np.nanmean(z_prim_grid)), 4),
                },
                "cokriged": {
                    "min": round(float(np.nanmin(z_co)), 4),
                    "max": round(float(np.nanmax(z_co)), 4),
                    "mean": round(float(np.nanmean(z_co)), 4),
                }
            },
            "comparison_image": comp_b64,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/uncertainty", methods=["POST"])
def uncertainty():
    try:
        raw = request.form if request.form else request.get_json(force=True)
        if raw is None:
            raw = {}

        df = _get_df(request)
        algorithm = raw.get("algorithm", "ordinary_kriging")
        variable = raw.get("variable", "temperature")
        lon_col = raw.get("lon_col", "lon")
        lat_col = raw.get("lat_col", "lat")
        confidence = float(raw.get("confidence", 0.95))
        nx = int(raw.get("nx", 50))
        ny = int(raw.get("ny", 50))

        df_clean = df.dropna(subset=[lon_col, lat_col, variable])
        x = df_clean[lon_col].values.astype(float)
        y = df_clean[lat_col].values.astype(float)
        z = df_clean[variable].values.astype(float)

        margin_x = (x.max() - x.min()) * 0.05
        margin_y = (y.max() - y.min()) * 0.05
        grid_x, grid_y = make_grid(
            x.min() - margin_x, x.max() + margin_x,
            y.min() - margin_y, y.max() + margin_y,
            nx=nx, ny=ny,
        )

        params = _parse_params(algorithm, raw)
        params.pop("adaptive_smooth_level", None)
        params.pop("preserve_extrema", None)
        params.pop("show_error_heatmap", None)
        params.pop("auto_variogram", None)

        grid_z, grid_var = run_interpolation(algorithm, x, y, z, grid_x, grid_y, **params)

        if grid_var is None:
            grid_var = np.full(grid_z.shape, np.nanstd(z) ** 2)

        ci = compute_confidence_intervals(grid_z, grid_var, confidence=confidence)
        summary = compute_uncertainty_summary(grid_z, grid_var)

        fig = plot_uncertainty_band(grid_x, grid_y, grid_z, grid_var,
                                     confidence=confidence,
                                     title=f"Uncertainty - {algorithm} - {variable}")
        band_b64 = fig_to_base64(fig)

        unit = "°C" if variable == "temperature" else "mm"
        thresh1 = np.nanmean(grid_z) + np.nanstd(grid_z)
        thresh2 = np.nanmean(grid_z)
        fig_prob = plot_probability_exceedance(grid_x, grid_y, grid_z, grid_var,
                                                [thresh1, thresh2],
                                                title="Probability of Exceedance")
        prob_b64 = fig_to_base64(fig_prob)

        report = generate_uncertainty_report(grid_z, grid_var, variable)

        return jsonify({
            "algorithm": algorithm,
            "variable": variable,
            "confidence": confidence,
            "summary": summary,
            "ci": {
                "std_mean": round(float(np.nanmean(ci["std"])), 4),
                "ci_width_mean": round(float(np.nanmean(ci["ci_width"])), 4),
                "unit": unit,
            },
            "report": report,
            "uncertainty_image": band_b64,
            "probability_image": prob_b64,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False)
