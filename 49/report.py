import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np


def load_motion_parameters(par_file: Union[str, Path]) -> np.ndarray:
    """
    Load FSL MCFLIRT motion parameter file (.par file).
    
    MCFLIRT .par files contain 6 columns (6 DOF):
    [rot_x, rot_y, rot_z, trans_x, trans_y, trans_z]
    Angles in radians, translations in mm.
    
    Parameters
    ----------
    par_file : str or Path
        Path to the motion parameter file.
    
    Returns
    -------
    np.ndarray
        Array of shape (n_volumes, 6) containing motion parameters.
    """
    par_path = Path(par_file)
    if not par_path.exists():
        raise FileNotFoundError(f"Motion parameter file not found: {par_file}")
    
    params = np.loadtxt(str(par_path))
    
    if params.ndim == 1:
        params = params.reshape(1, -1)
    
    if params.shape[1] != 6:
        raise ValueError(f"Expected 6 motion parameters, got {params.shape[1]}")
    
    return params


def compute_derivatives(params: np.ndarray) -> np.ndarray:
    """
    Compute temporal derivatives (framewise differences) of motion parameters.
    Used for nuisance regression (motion scrubbing or derivative regression).
    
    Parameters
    ----------
    params : np.ndarray
        Motion parameters array of shape (n_volumes, 6).
    
    Returns
    -------
    np.ndarray
        Derivatives array of shape (n_volumes, 6), with first row zero.
    """
    derivs = np.zeros_like(params)
    derivs[1:, :] = np.diff(params, axis=0)
    return derivs


def compute_framewise_displacement(params: np.ndarray) -> np.ndarray:
    """
    Compute Framewise Displacement (FD) from motion parameters.
    
    FD: Power et al. (2012, NeuroImage)
    FD_t = |Δrot_x| + |Δrot_y| + |Δrot_z| + |Δtrans_x| + |Δtrans_y| + |Δtrans_z|
    
    Rotations are converted from radians to mm displacement on a 50mm sphere.
    
    Parameters
    ----------
    params : np.ndarray
        Motion parameters array of shape (n_volumes, 6).
    
    Returns
    -------
    np.ndarray
        FD array of shape (n_volumes,), with FD[0] = 0.
    """
    delta = np.zeros_like(params)
    delta[1:, :] = np.abs(np.diff(params, axis=0))
    
    radius = 50.0
    delta[:, :3] = delta[:, :3] * radius * (np.pi / 180.0)
    
    fd = np.sum(delta, axis=1)
    return fd


def compute_rms(rms_file: Union[str, Path]) -> np.ndarray:
    """
    Load FSL MCFLIRT RMS displacement file.
    
    MCFLIRT saves:
    - *abs.rms: Absolute RMS displacement from reference volume
    - *rel.rms: Relative RMS displacement from previous volume
    
    Parameters
    ----------
    rms_file : str or Path
        Path to RMS file (*.rms).
    
    Returns
    -------
    np.ndarray
        Array of RMS values.
    """
    rms_path = Path(rms_file)
    if not rms_path.exists():
        raise FileNotFoundError(f"RMS file not found: {rms_file}")
    return np.loadtxt(str(rms_path))


def detect_outliers(
    fd: np.ndarray,
    threshold: float = 0.5
) -> np.ndarray:
    """
    Detect motion outlier volumes based on FD threshold.
    
    Parameters
    ----------
    fd : np.ndarray
        Framewise displacement array.
    threshold : float, optional
        FD threshold in mm (Power et al. 2012 recommends 0.5), by default 0.5.
    
    Returns
    -------
    np.ndarray
        Boolean array where True indicates outlier volume.
    """
    return fd > threshold


def summarize_motion(par_file: Union[str, Path]) -> Dict:
    """
    Generate a summary of motion statistics.
    
    Parameters
    ----------
    par_file : str or Path
        Path to the motion parameter file.
    
    Returns
    -------
    dict
        Dictionary containing:
        - n_volumes: number of volumes
        - params_means: mean of each motion parameter
        - params_stds: std of each motion parameter
        - params_maxabs: max absolute of each parameter
        - fd_mean: mean framewise displacement
        - fd_max: max framewise displacement
        - fd_median: median framewise displacement
        - fd_gt_05: number of volumes with FD > 0.5mm
        - fd_gt_05_pct: percentage of volumes with FD > 0.5mm
    """
    params = load_motion_parameters(par_file)
    fd = compute_framewise_displacement(params)
    
    stats = {
        'n_volumes': len(params),
        'params_means': params.mean(axis=0).tolist(),
        'params_stds': params.std(axis=0).tolist(),
        'params_maxabs': np.max(np.abs(params), axis=0).tolist(),
        'fd_mean': float(fd.mean()),
        'fd_max': float(fd.max()),
        'fd_median': float(np.median(fd)),
        'fd_gt_05': int(np.sum(fd > 0.5)),
        'fd_gt_05_pct': float(np.mean(fd > 0.5) * 100),
        'fd_gt_1': int(np.sum(fd > 1.0)),
        'fd_gt_1_pct': float(np.mean(fd > 1.0) * 100)
    }
    
    return stats


def _fd_plot_to_html(fd: np.ndarray, title: str = 'Framewise Displacement') -> str:
    """
    Generate a simple HTML-based FD plot (no external dependencies).
    Uses SVG for rendering.
    """
    n = len(fd)
    if n == 0:
        return '<p>No data available</p>'
    
    max_fd = max(fd.max(), 1.0)
    width = 800
    height = 300
    padding_x = 60
    padding_y = 40
    
    plot_width = width - 2 * padding_x
    plot_height = height - 2 * padding_y
    
    def normalize_y(val, max_val):
        return height - padding_y - (val / max_val) * plot_height
    
    def normalize_x(idx, total):
        return padding_x + (idx / max(1, total - 1)) * plot_width
    
    points = []
    for i, val in enumerate(fd):
        x = normalize_x(i, n)
        y = normalize_y(val, max_fd)
        points.append(f"{x},{y}")
    
    threshold_y_05 = normalize_y(0.5, max_fd)
    threshold_y_1 = normalize_y(1.0, max_fd)
    
    svg = f'''<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="fdGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:#3498db;stop-opacity:0.9" />
                <stop offset="100%" style="stop-color:#2980b9;stop-opacity:0.6" />
            </linearGradient>
        </defs>
        
        <rect x="{padding_x}" y="{padding_y}" width="{plot_width}" height="{plot_height}" 
              fill="#f8f9fa" stroke="#dee2e6" />
        
        <line x1="{padding_x}" y1="{threshold_y_05}" 
              x2="{width - padding_x}" y2="{threshold_y_05}" 
              stroke="#e74c3c" stroke-width="1" stroke-dasharray="5,5" />
        <text x="{width - padding_x + 5}" y="{threshold_y_05 + 4}" 
              fill="#e74c3c" font-size="10">FD = 0.5mm</text>
        
        <line x1="{padding_x}" y1="{threshold_y_1}" 
              x2="{width - padding_x}" y2="{threshold_y_1}" 
              stroke="#f39c12" stroke-width="1" stroke-dasharray="3,3" />
        <text x="{width - padding_x + 5}" y="{threshold_y_1 + 4}" 
              fill="#f39c12" font-size="10">FD = 1.0mm</text>
        
        <polyline points="{' '.join(points)}" fill="none" stroke="#3498db" stroke-width="1.5" />
        
        <text x="{width / 2}" y="20" text-anchor="middle" 
              font-size="14" font-weight="bold" fill="#2c3e50">{title}</text>
        <text x="{width / 2}" y="{height - 5}" text-anchor="middle" 
              font-size="11" fill="#7f8c8d">Volume</text>
        <text x="15" y="{height / 2}" text-anchor="middle" transform="rotate(-90, 15, {height / 2})"
              font-size="11" fill="#7f8c8d">FD (mm)</text>
        
        <text x="{padding_x}" y="{height - padding_y + 15}" 
              font-size="9" fill="#95a5a6">0</text>
        <text x="{width - padding_x - 15}" y="{height - padding_y + 15}" 
              font-size="9" fill="#95a5a6">{n}</text>
        <text x="{padding_x - 5}" y="{height - padding_y}" 
              text-anchor="end" font-size="9" fill="#95a5a6">0</text>
        <text x="{padding_x - 5}" y="{padding_y + 5}" 
              text-anchor="end" font-size="9" fill="#95a5a6">{max_fd:.1f}</text>
    </svg>'''
    
    return svg


def _params_plot_to_html(params: np.ndarray, title: str = 'Motion Parameters') -> str:
    """
    Generate HTML-based motion parameters plot.
    """
    n = len(params)
    if n == 0:
        return '<p>No data available</p>'
    
    labels = ['Rot X', 'Rot Y', 'Rot Z', 'Trans X', 'Trans Y', 'Trans Z']
    colors = ['#e74c3c', '#e67e22', '#f1c40f', '#3498db', '#2ecc71', '#9b59b6']
    units = ['rad', 'rad', 'rad', 'mm', 'mm', 'mm']
    
    subplot_height = 100
    total_height = subplot_height * 6 + 60
    width = 800
    padding_x = 70
    padding_y = 30
    plot_width = width - 2 * padding_x
    plot_height = subplot_height - 15
    
    def normalize_x(idx, total):
        return padding_x + (idx / max(1, total - 1)) * plot_width
    
    svgs = []
    
    for p_idx in range(6):
        values = params[:, p_idx]
        min_val = values.min()
        max_val = values.max()
        val_range = max(max_val - min_val, 1e-6)
        
        y_offsets = [p_idx * subplot_height + 40 for _ in range(n)]
        points = []
        
        for i, val in enumerate(values):
            x = normalize_x(i, n)
            y_norm = (val - min_val) / val_range
            y = y_offsets[0] + (1 - y_norm) * (plot_height - 5)
            points.append(f"{x},{y}")
        
        svgs.append(f'''
        <text x="10" y="{y_offsets[0] + plot_height / 2 + 5}" 
              fill="{colors[p_idx]}" font-size="10" font-weight="bold">
            {labels[p_idx]} ({units[p_idx]})
        </text>
        <rect x="{padding_x}" y="{y_offsets[0]}" 
              width="{plot_width}" height="{plot_height}" 
              fill="#fafafa" stroke="#dee2e6" />
        <polyline points="{' '.join(points)}" 
                  fill="none" stroke="{colors[p_idx]}" stroke-width="1.2" />
        <line x1="{padding_x}" y1="{y_offsets[0] + plot_height / 2}" 
              x2="{width - padding_x}" y2="{y_offsets[0] + plot_height / 2}" 
              stroke="#bdc3c7" stroke-width="0.5" stroke-dasharray="2,2" />
        ''')
    
    return f'''<svg width="{width}" height="{total_height}" xmlns="http://www.w3.org/2000/svg">
        <text x="{width / 2}" y="20" text-anchor="middle" 
              font-size="14" font-weight="bold" fill="#2c3e50">{title}</text>
        {''.join(svgs)}
        <text x="{width / 2}" y="{total_height - 5}" text-anchor="middle" 
              font-size="11" fill="#7f8c8d">Volume</text>
    </svg>'''


def generate_html_report(
    par_file: Union[str, Path],
    output_html: Union[str, Path],
    subject_id: str = 'unknown',
    rms_file: Optional[Union[str, Path]] = None,
    fd_threshold: float = 0.5
) -> str:
    """
    Generate an HTML quality control report for motion correction.
    
    Parameters
    ----------
    par_file : str or Path
        Path to MCFLIRT .par motion parameter file.
    output_html : str or Path
        Path to save the HTML report.
    subject_id : str, optional
        Subject identifier for the report header, by default 'unknown'.
    rms_file : str or Path, optional
        Path to RMS displacement file, by default None.
    fd_threshold : float, optional
        FD threshold for outlier detection, by default 0.5.
    
    Returns
    -------
    str
        Path to the generated HTML report.
    """
    par_path = Path(par_file)
    output_path = Path(output_html)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    params = load_motion_parameters(par_path)
    fd = compute_framewise_displacement(params)
    summary = summarize_motion(par_path)
    outliers = detect_outliers(fd, fd_threshold)
    
    fd_html = _fd_plot_to_html(fd, 'Framewise Displacement (FD)')
    params_html = _params_plot_to_html(params, 'Motion Parameters (6 DOF)')
    
    status_class = 'success'
    status_text = 'PASS'
    if summary['fd_gt_05_pct'] > 20:
        status_class = 'warning'
        status_text = 'WARNING'
    if summary['fd_gt_05_pct'] > 50:
        status_class = 'danger'
        status_text = 'FAIL'
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Motion QC Report - {subject_id}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #ecf0f1;
            color: #2c3e50;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        .header {{
            background: linear-gradient(135deg, #2c3e50, #34495e);
            color: white;
            padding: 25px 30px;
            border-radius: 8px 8px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{ font-size: 20px; font-weight: 500; }}
        .status {{
            padding: 6px 16px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 13px;
        }}
        .status.success {{ background: #27ae60; }}
        .status.warning {{ background: #f39c12; }}
        .status.danger {{ background: #e74c3c; }}
        
        .section {{
            background: white;
            margin: 1px 0;
            padding: 25px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .section:last-child {{ border-radius: 0 0 8px 8px; }}
        .section h2 {{
            font-size: 16px;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 1px solid #ecf0f1;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 15px;
        }}
        .stat-card {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            border-left: 3px solid #3498db;
        }}
        .stat-label {{
            font-size: 11px;
            color: #7f8c8d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .stat-value {{
            font-size: 20px;
            font-weight: 600;
            color: #2c3e50;
            margin-top: 4px;
        }}
        
        .table-wrapper {{ overflow-x: auto; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #ecf0f1; }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #7f8c8d;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        tr:hover {{ background: #fafafa; }}
        
        .plot-container {{ text-align: center; }}
        .plot-container svg {{ max-width: 100%; height: auto; }}
        
        .footer {{
            text-align: center;
            margin-top: 20px;
            color: #95a5a6;
            font-size: 12px;
        }}
        
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: 500;
        }}
        .badge.warning {{ background: #fef3e2; color: #d68910; }}
        .badge.danger {{ background: #fadbd8; color: #c0392b; }}
        .badge.info {{ background: #d6eaf8; color: #2874a6; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 fMRI Motion QC Report</h1>
            <div class="status {status_class}">{status_text}</div>
        </div>
        
        <div class="section">
            <h2>📋 Subject Information</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Subject ID</div>
                    <div class="stat-value" style="font-size: 16px;">{subject_id}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Volumes</div>
                    <div class="stat-value">{summary['n_volumes']}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Mean FD (mm)</div>
                    <div class="stat-value">{summary['fd_mean']:.3f}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Max FD (mm)</div>
                    <div class="stat-value">{summary['fd_max']:.3f}</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>📈 Framewise Displacement</h2>
            <div class="plot-container">{fd_html}</div>
        </div>
        
        <div class="section">
            <h2>⚠️ Outlier Summary (FD > {fd_threshold}mm)</h2>
            <div class="stats-grid">
                <div class="stat-card" style="border-left-color: {'#e74c3c' if summary['fd_gt_05'] > 0 else '#27ae60'}">
                    <div class="stat-label">Outliers (FD > 0.5mm)</div>
                    <div class="stat-value">{summary['fd_gt_05']} <span style="font-size: 12px; color: #7f8c8d;">({summary['fd_gt_05_pct']:.1f}%)</span></div>
                </div>
                <div class="stat-card" style="border-left-color: {'#e74c3c' if summary['fd_gt_1'] > 0 else '#27ae60'}">
                    <div class="stat-label">Outliers (FD > 1.0mm)</div>
                    <div class="stat-value">{summary['fd_gt_1']} <span style="font-size: 12px; color: #7f8c8d;">({summary['fd_gt_1_pct']:.1f}%)</span></div>
                </div>
            </div>
            <p style="margin-top: 15px; font-size: 12px; color: #7f8c8d;">
                <span class="badge info">Recommendation:</span> 
                Consider censoring volumes with FD > {fd_threshold}mm, or using motion scrubbing.
            </p>
        </div>
        
        <div class="section">
            <h2>🔄 Motion Parameters (6 DOF)</h2>
            <div class="plot-container">{params_html}</div>
        </div>
        
        <div class="section">
            <h2>📊 Parameter Statistics</h2>
            <div class="table-wrapper">
                <table>
                    <tr>
                        <th>Parameter</th>
                        <th>Mean</th>
                        <th>Std</th>
                        <th>Max |Abs|</th>
                    </tr>
                    <tr><td>Rot X (rad)</td><td>{summary['params_means'][0]:.4f}</td><td>{summary['params_stds'][0]:.4f}</td><td>{summary['params_maxabs'][0]:.4f}</td></tr>
                    <tr><td>Rot Y (rad)</td><td>{summary['params_means'][1]:.4f}</td><td>{summary['params_stds'][1]:.4f}</td><td>{summary['params_maxabs'][1]:.4f}</td></tr>
                    <tr><td>Rot Z (rad)</td><td>{summary['params_means'][2]:.4f}</td><td>{summary['params_stds'][2]:.4f}</td><td>{summary['params_maxabs'][2]:.4f}</td></tr>
                    <tr><td>Trans X (mm)</td><td>{summary['params_means'][3]:.4f}</td><td>{summary['params_stds'][3]:.4f}</td><td>{summary['params_maxabs'][3]:.4f}</td></tr>
                    <tr><td>Trans Y (mm)</td><td>{summary['params_means'][4]:.4f}</td><td>{summary['params_stds'][4]:.4f}</td><td>{summary['params_maxabs'][4]:.4f}</td></tr>
                    <tr><td>Trans Z (mm)</td><td>{summary['params_means'][5]:.4f}</td><td>{summary['params_stds'][5]:.4f}</td><td>{summary['params_maxabs'][5]:.4f}</td></tr>
                </table>
            </div>
        </div>
        
        <div class="footer">
            Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
            Power FD (2012) | MCFLIRT
        </div>
    </div>
</body>
</html>'''
    
    output_path.write_text(html, encoding='utf-8')
    return str(output_path)


def generate_group_report(
    subjects: Dict[str, Union[str, Dict]],
    output_html: Union[str, Path]
) -> str:
    """
    Generate a group-level HTML report summarizing motion across subjects.
    
    Parameters
    ----------
    subjects : dict
        Dictionary mapping subject IDs to either:
        - Path to motion parameter file (.par)
        - Dictionary with 'par_file' key and optional 'rms_file'
    output_html : str or Path
        Path to save the group HTML report.
    
    Returns
    -------
    str
        Path to the generated HTML report.
    """
    output_path = Path(output_html)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    group_stats = {}
    for subject_id, info in subjects.items():
        try:
            if isinstance(info, dict):
                par_file = info.get('par_file')
            else:
                par_file = info
            
            if par_file and Path(par_file).exists():
                group_stats[subject_id] = summarize_motion(par_file)
        except Exception:
            group_stats[subject_id] = {'error': 'Failed to process'}
    
    if not group_stats:
        raise RuntimeError("No valid subject data for group report")
    
    valid_stats = [s for s in group_stats.values() if 'error' not in s]
    if valid_stats:
        mean_fd_values = [s['fd_mean'] for s in valid_stats]
        outlier_pcts = [s['fd_gt_05_pct'] for s in valid_stats]
        
        group_summary = {
            'n_subjects': len(valid_stats),
            'group_mean_fd': float(np.mean(mean_fd_values)),
            'group_std_fd': float(np.std(mean_fd_values)),
            'group_median_fd': float(np.median(mean_fd_values)),
            'group_mean_outliers': float(np.mean(outlier_pcts)),
            'group_std_outliers': float(np.std(outlier_pcts))
        }
    else:
        group_summary = {'n_subjects': 0}
    
    subject_rows = []
    for subject_id, stats in sorted(group_stats.items()):
        if 'error' in stats:
            row = f'''
            <tr>
                <td>{subject_id}</td>
                <td colspan="6" style="color: #e74c3c; text-align: center;">{stats['error']}</td>
            </tr>'''
        else:
            outlier_class = ''
            if stats['fd_gt_05_pct'] > 20:
                outlier_class = " class='warning'"
            if stats['fd_gt_05_pct'] > 50:
                outlier_class = " class='danger'"
            
            row = f'''
            <tr{outlier_class}>
                <td style="font-weight: 500;">{subject_id}</td>
                <td>{stats['n_volumes']}</td>
                <td>{stats['fd_mean']:.3f}</td>
                <td>{stats['fd_max']:.3f}</td>
                <td>{stats['fd_median']:.3f}</td>
                <td>{stats['fd_gt_05']}</td>
                <td>{stats['fd_gt_05_pct']:.1f}%</td>
            </tr>'''
        subject_rows.append(row)
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Group Motion QC Report</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #ecf0f1;
            color: #2c3e50;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        .header {{
            background: linear-gradient(135deg, #2c3e50, #34495e);
            color: white;
            padding: 25px 30px;
            border-radius: 8px 8px 0 0;
        }}
        .header h1 {{ font-size: 20px; font-weight: 500; }}
        .section {{
            background: white;
            margin: 1px 0;
            padding: 25px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .section:last-child {{ border-radius: 0 0 8px 8px; }}
        .section h2 {{
            font-size: 16px;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 1px solid #ecf0f1;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 15px;
        }}
        .stat-card {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            border-left: 3px solid #3498db;
        }}
        .stat-label {{
            font-size: 11px;
            color: #7f8c8d;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .stat-value {{
            font-size: 20px;
            font-weight: 600;
            color: #2c3e50;
            margin-top: 4px;
        }}
        .table-wrapper {{ overflow-x: auto; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #ecf0f1; }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #7f8c8d;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        tr:hover {{ background: #fafafa; }}
        tr.warning {{ background: #fef9e7; }}
        tr.danger {{ background: #fadbd8; }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            color: #95a5a6;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 Group fMRI Motion QC Report</h1>
        </div>
        
        <div class="section">
            <h2>📊 Group Summary</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Subjects</div>
                    <div class="stat-value">{group_summary.get('n_subjects', 0)}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Group Mean FD (mm)</div>
                    <div class="stat-value">{group_summary.get('group_mean_fd', 0):.3f}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Group Median FD (mm)</div>
                    <div class="stat-value">{group_summary.get('group_median_fd', 0):.3f}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Mean Outliers (%)</div>
                    <div class="stat-value">{group_summary.get('group_mean_outliers', 0):.1f}%</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>👥 Individual Subjects</h2>
            <div class="table-wrapper">
                <table>
                    <tr>
                        <th>Subject</th>
                        <th>Volumes</th>
                        <th>Mean FD (mm)</th>
                        <th>Max FD (mm)</th>
                        <th>Median FD (mm)</th>
                        <th>Outliers (FD>0.5)</th>
                        <th>Outliers (%)</th>
                    </tr>
                    {''.join(subject_rows)}
                </table>
            </div>
        </div>
        
        <div class="footer">
            Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>'''
    
    output_path.write_text(html, encoding='utf-8')
    return str(output_path)
