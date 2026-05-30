import numpy as np
import warnings
warnings.filterwarnings("ignore")

CONFIDENCE_LEVELS = [0.68, 0.90, 0.95, 0.99]


def compute_confidence_intervals(grid_z, grid_var, confidence=0.95):
    from scipy import stats

    z = np.array(grid_z)
    var = np.array(grid_var)

    z_scores = {
        0.68: 1.0,
        0.90: 1.645,
        0.95: 1.96,
        0.99: 2.576,
    }

    z_score = z_scores.get(confidence, 1.96)

    std = np.sqrt(np.maximum(var, 0))
    lower = z - z_score * std
    upper = z + z_score * std

    return {
        "mean": z,
        "std": std,
        "lower": lower,
        "upper": upper,
        "confidence": confidence,
        "z_score": z_score,
        "ci_width": 2 * z_score * std,
    }


def compute_uncertainty_summary(grid_z, grid_var):
    z = np.array(grid_z)
    var = np.array(grid_var)
    std = np.sqrt(np.maximum(var, 0))

    cv = std / np.abs(z)
    cv[np.abs(z) < 1e-10] = np.nan

    ci95 = compute_confidence_intervals(z, var, 0.95)

    return {
        "mean_value": float(np.nanmean(z)),
        "std_mean": float(np.nanmean(std)),
        "std_min": float(np.nanmin(std)),
        "std_max": float(np.nanmax(std)),
        "cv_mean": float(np.nanmean(cv)),
        "ci95_width_mean": float(np.nanmean(ci95["ci_width"])),
        "high_uncertainty_ratio": float(np.mean(std > np.nanmean(std) * 1.5)),
    }


def classify_uncertainty(grid_var, levels=3):
    std = np.sqrt(np.maximum(grid_var, 0))
    q_levels = np.linspace(0, 100, levels + 1)[1:-1]
    thresholds = np.percentile(std[~np.isnan(std)], q_levels)

    classes = np.zeros_like(std, dtype=int)
    for i, thresh in enumerate(reversed(thresholds)):
        classes[std > thresh] = i + 1

    labels = ["Low", "Medium", "High"] if levels == 3 else [f"Level {i+1}" for i in range(levels)]

    return {
        "classes": classes,
        "thresholds": thresholds.tolist(),
        "labels": labels,
    }


def plot_uncertainty_band(grid_x, grid_y, grid_z, grid_var,
                          confidence=0.95,
                          title="Uncertainty Assessment",
                          label="Value",
                          figsize=(16, 6), dpi=120):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ci = compute_confidence_intervals(grid_z, grid_var, confidence)

    fig, axes = plt.subplots(1, 3, figsize=figsize, dpi=dpi)

    z_min, z_max = np.nanmin(grid_z), np.nanmax(grid_z)
    std_min, std_max = np.nanmin(ci["std"]), np.nanmax(ci["std"])
    width_min, width_max = np.nanmin(ci["ci_width"]), np.nanmax(ci["ci_width"])

    cf1 = axes[0].contourf(grid_x, grid_y, grid_z, levels=15,
                           cmap="RdYlBu_r", extend="both")
    axes[0].set_title("Interpolated Value", fontsize=11, fontweight="bold")
    fig.colorbar(cf1, ax=axes[0], label=label)

    cf2 = axes[1].contourf(grid_x, grid_y, ci["std"], levels=15,
                           cmap="YlOrRd", extend="max")
    axes[1].set_title("Standard Deviation", fontsize=11, fontweight="bold")
    fig.colorbar(cf2, ax=axes[1], label="Std Dev")

    cf3 = axes[2].contourf(grid_x, grid_y, ci["ci_width"], levels=15,
                           cmap="YlOrRd", extend="max")
    axes[2].set_title(f"{int(confidence*100)}% CI Width", fontsize=11, fontweight="bold")
    fig.colorbar(cf3, ax=axes[2], label="CI Width")

    fig.suptitle(title, fontsize=13, fontweight="bold")
    fig.tight_layout()
    return fig


def plot_probability_exceedance(grid_x, grid_y, grid_z, grid_var,
                                 thresholds,
                                 title="Probability of Exceedance",
                                 figsize=(14, 5), dpi=120):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy import stats

    n_thresh = len(thresholds)
    fig, axes = plt.subplots(1, n_thresh, figsize=figsize, dpi=dpi)
    if n_thresh == 1:
        axes = [axes]

    std = np.sqrt(np.maximum(grid_var, 0))

    for i, thresh in enumerate(thresholds):
        z_scores = (thresh - grid_z) / (std + 1e-10)
        prob_exceed = 1 - stats.norm.cdf(z_scores)

        cf = axes[i].contourf(grid_x, grid_y, prob_exceed * 100,
                               levels=np.linspace(0, 100, 11),
                               cmap="RdYlGn_r", extend="both")
        axes[i].set_title(f"P(Value > {thresh})", fontsize=11, fontweight="bold")
        fig.colorbar(cf, ax=axes[i], label="Probability (%)")

    fig.suptitle(title, fontsize=13, fontweight="bold")
    fig.tight_layout()
    return fig


def generate_uncertainty_report(grid_z, grid_var, variable_name="Value"):
    summary = compute_uncertainty_summary(grid_z, grid_var)
    ci95 = compute_confidence_intervals(grid_z, grid_var, 0.95)
    ci68 = compute_confidence_intervals(grid_z, grid_var, 0.68)

    report = []
    report.append(f"=== Uncertainty Report for {variable_name} ===")
    report.append("")
    report.append(f"Mean Value: {summary['mean_value']:.4f}")
    report.append("")
    report.append("Standard Deviation:")
    report.append(f"  Mean: {summary['std_mean']:.4f}")
    report.append(f"  Min:  {summary['std_min']:.4f}")
    report.append(f"  Max:  {summary['std_max']:.4f}")
    report.append("")
    report.append("Confidence Intervals:")
    report.append(f"  68% CI Mean Width: {2*np.nanmean(ci68['std']):.4f} (±1σ)")
    report.append(f"  95% CI Mean Width: {np.nanmean(ci95['ci_width']):.4f} (±1.96σ)")
    report.append("")
    report.append(f"Coefficient of Variation (CV): {summary['cv_mean']:.2%}")
    report.append(f"High Uncertainty Areas: {summary['high_uncertainty_ratio']:.1%}")
    report.append("")
    report.append("Spatial Pattern:")
    if summary["std_max"] / summary["std_mean"] > 3:
        report.append("  - High spatial variability in uncertainty")
    else:
        report.append("  - Relatively uniform uncertainty distribution")

    return "\n".join(report)
