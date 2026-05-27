import numpy as np


def compute_epe(pred_flow: np.ndarray, gt_flow: np.ndarray) -> np.ndarray:
    """
    计算端点误差 (Endpoint Error, EPE)

    EPE 是预测光流与真实光流之间的欧氏距离, 逐像素计算。
    EPE = sqrt((u_pred - u_gt)^2 + (v_pred - v_gt)^2)

    参数:
        pred_flow: 预测光流 (H, W, 2)
        gt_flow: 真实光流 (H, W, 2)

    返回:
        逐像素 EPE (H, W)
    """
    diff = pred_flow - gt_flow
    epe = np.sqrt(diff[..., 0] ** 2 + diff[..., 1] ** 2)
    return epe


def compute_aee(pred_flow: np.ndarray, gt_flow: np.ndarray, valid_mask: np.ndarray | None = None) -> float:
    """
    计算平均端点误差 (Average Endpoint Error, AEE)

    AEE 是所有有效像素的 EPE 的平均值。

    参数:
        pred_flow: 预测光流 (H, W, 2)
        gt_flow: 真实光流 (H, W, 2)
        valid_mask: 有效像素掩码 (H, W), 1 表示有效, 0 表示无效

    返回:
        AEE 标量值
    """
    epe = compute_epe(pred_flow, gt_flow)

    if valid_mask is not None:
        mask = valid_mask.astype(bool)
        if mask.sum() == 0:
            return 0.0
        return float(epe[mask].mean())
    else:
        return float(epe.mean())


def compute_angular_error(pred_flow: np.ndarray, gt_flow: np.ndarray) -> np.ndarray:
    """
    计算角度误差 (Angular Error)

    角度误差衡量光流方向的差异, 不受幅度影响。
    AE = arccos((u1*u2 + v1*v2 + 1) / sqrt((u1^2+v1^2+1)*(u2^2+v2^2+1)))

    参数:
        pred_flow: 预测光流 (H, W, 2)
        gt_flow: 真实光流 (H, W, 2)

    返回:
        逐像素角度误差 (弧度) (H, W)
    """
    u1, v1 = pred_flow[..., 0], pred_flow[..., 1]
    u2, v2 = gt_flow[..., 0], gt_flow[..., 1]

    numerator = u1 * u2 + v1 * v2 + 1.0
    denom = np.sqrt((u1 ** 2 + v1 ** 2 + 1.0) * (u2 ** 2 + v2 ** 2 + 1.0))
    denom = np.clip(denom, 1e-8, None)
    cosine = np.clip(numerator / denom, -1.0, 1.0)
    angular_error = np.arccos(cosine)
    return angular_error


def compute_aae(pred_flow: np.ndarray, gt_flow: np.ndarray, valid_mask: np.ndarray | None = None) -> float:
    """
    计算平均角度误差 (Average Angular Error, AAE)

    参数:
        pred_flow: 预测光流 (H, W, 2)
        gt_flow: 真实光流 (H, W, 2)
        valid_mask: 有效像素掩码

    返回:
        AAE 标量值 (度)
    """
    ae = compute_angular_error(pred_flow, gt_flow)

    if valid_mask is not None:
        mask = valid_mask.astype(bool)
        if mask.sum() == 0:
            return 0.0
        return float(np.degrees(ae[mask].mean()))
    else:
        return float(np.degrees(ae.mean()))


def compute_fl_error(pred_flow: np.ndarray, gt_flow: np.ndarray, threshold: float = 3.0) -> float:
    """
    计算 KITTI 风格的 Fl 错误率

    Fl 错误率: EPE > 阈值 或 EPE/gt_magnitude > 0.05 的像素占比

    参数:
        pred_flow: 预测光流 (H, W, 2)
        gt_flow: 真实光流 (H, W, 2)
        threshold: 绝对误差阈值 (像素)

    返回:
        Fl 错误率 [0, 1]
    """
    epe = compute_epe(pred_flow, gt_flow)
    gt_mag = np.sqrt(gt_flow[..., 0] ** 2 + gt_flow[..., 1] ** 2)

    fl_error = (epe > threshold) & (epe / (gt_mag + 1e-8) > 0.05)
    return float(fl_error.mean())


def compute_metrics(pred_flow: np.ndarray, gt_flow: np.ndarray, valid_mask: np.ndarray | None = None) -> dict:
    """
    计算所有评估指标

    参数:
        pred_flow: 预测光流 (H, W, 2)
        gt_flow: 真实光流 (H, W, 2)
        valid_mask: 有效像素掩码

    返回:
        包含所有指标的字典
    """
    return {
        'AEE': compute_aee(pred_flow, gt_flow, valid_mask),
        'AAE': compute_aae(pred_flow, gt_flow, valid_mask),
        'EPE_mean': float(compute_epe(pred_flow, gt_flow).mean()),
        'EPE_median': float(np.median(compute_epe(pred_flow, gt_flow))),
        'Fl_error': compute_fl_error(pred_flow, gt_flow),
    }