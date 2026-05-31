import numpy as np
import argparse
import os
from medical_registration import RegistrationPipeline, RigidTransform, BSplineTransform


def generate_synthetic_ct(shape=(256, 256)):
    ct = np.zeros(shape, dtype=np.float64)
    rows, cols = shape
    cy, cx = rows // 2, cols // 2

    y, x = np.ogrid[:rows, :cols]
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)

    ct[r < 80] = -200
    ct[r < 70] = 50
    ct[r < 60] = 200
    ct[r < 20] = 800
    ct[r < 10] = 1000

    ct += np.random.normal(0, 15, shape)
    return ct


def generate_synthetic_mri(shape=(256, 256), angle=0.1, tx=5, ty=-3):
    mri = np.zeros(shape, dtype=np.float64)
    rows, cols = shape
    cy, cx = rows // 2, cols // 2

    cos_a = np.cos(angle)
    sin_a = np.sin(angle)

    y_coords, x_coords = np.mgrid[:rows, :cols]
    x_shifted = x_coords - cx - tx
    y_shifted = y_coords - cy - ty

    x_rot = cos_a * x_shifted + sin_a * y_shifted + cx
    y_rot = -sin_a * x_shifted + cos_a * y_shifted + cy

    r = np.sqrt((x_rot - cx) ** 2 + (y_rot - cy) ** 2)

    mri[r < 80] = 20
    mri[r < 70] = 100
    mri[r < 60] = 180
    mri[r < 20] = 250
    mri[r < 10] = 280

    mri += np.random.normal(0, 10, shape)
    return mri


def generate_synthetic_deformed_mri(shape=(256, 256), angle=0.1, tx=5, ty=-3,
                                    bspline_grid_spacing=32, bspline_order=3,
                                    max_displacement=3.0):
    rows, cols = shape
    cy, cx = rows // 2, cols // 2

    gt_transform = RigidTransform(dim=2, image_shape=shape)
    gt_params = np.array([angle, tx, ty])

    y, x = np.mgrid[:rows, :cols]
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)

    mask = r < 75

    mri = np.zeros(shape, dtype=np.float64)
    mri[r < 80] = 20
    mri[r < 70] = 100
    mri[r < 60] = 180
    mri[r < 20] = 250
    mri[r < 10] = 280

    from scipy.ndimage import map_coordinates
    coords = np.stack([y.ravel(), x.ravel()], axis=0)
    ones = np.ones((1, coords.shape[1]))
    homogeneous = np.vstack([coords, ones])
    M_inv = np.linalg.inv(gt_transform.get_matrix(gt_params))
    src_coords = M_inv @ homogeneous
    warped = map_coordinates(
        mri, [src_coords[0], src_coords[1]], order=1, mode="constant", cval=0.0
    ).reshape(shape)

    if bspline_grid_spacing > 0:
        gt_bspline = BSplineTransform(
            dim=2, image_shape=shape,
            grid_spacing=bspline_grid_spacing, order=bspline_order
        )
        num_params = gt_bspline.get_num_params()
        np.random.seed(42)
        gt_bspline_params = np.random.normal(0, max_displacement, num_params)

        warped = gt_bspline.apply_to_image(warped, gt_bspline_params)
        gt_transform = gt_bspline
        gt_params = gt_bspline_params
    else:
        gt_bspline_params = None

    warped += np.random.normal(0, 10, shape)

    return warped, gt_transform, gt_params


def run_demo(transform_type="rigid", use_gpu=False, output_dir="output",
             grid_spacing=32, bspline_order=3, regularization_weight=0.01):
    print("=" * 60)
    print("Medical Image Registration Demo")
    print("CT-MRI Multi-Modal Registration")
    print("=" * 60)

    print("\n[Step 1] Generating synthetic CT and MRI images...")
    ct_image = generate_synthetic_ct(shape=(256, 256))

    gt_bspline = transform_type == "bspline"
    bspline_gs = 32 if gt_bspline else 0

    mri_image, gt_transform, gt_params = generate_synthetic_deformed_mri(
        shape=(256, 256), angle=0.1, tx=5, ty=-3,
        bspline_grid_spacing=bspline_gs, max_displacement=2.0
    )

    print(f"  CT shape: {ct_image.shape}, range: [{ct_image.min():.1f}, {ct_image.max():.1f}]")
    print(f"  MRI shape: {mri_image.shape}, range: [{mri_image.min():.1f}, {mri_image.max():.1f}]")
    print(f"  Ground truth transform type: {type(gt_transform).__name__}")
    if not gt_bspline:
        print(f"  Ground truth params (angle, tx, ty): {gt_params}")

    print("\n[Step 2] Setting up registration pipeline...")
    pipeline = RegistrationPipeline(
        transform_type=transform_type,
        dim=2,
        metric="nmi",
        optimizer="lbfgsb",
        num_bins=64,
        max_iter=200,
        tol=1e-6,
        use_gpu=use_gpu,
        multi_resolution=True,
        num_levels=3,
        verbose=True,
        grid_spacing=grid_spacing,
        bspline_order=bspline_order,
        regularization_weight=regularization_weight,
    )

    gpu_info = pipeline.gpu.gpu_info()
    print(f"  GPU Info: {gpu_info}")

    print("\n[Step 3] Running registration with TRE evaluation...")
    result = pipeline.register(
        ct_image, mri_image, output_dir=output_dir,
        ground_truth_transform=gt_transform,
        ground_truth_params=gt_params,
        compute_tre=True,
        num_landmarks=50,
    )

    print("\n[Step 4] Registration complete!")
    print(f"  Final MI: {result['metric_value']:.6f}")
    if transform_type == "bspline":
        print(f"  Number of B-spline params: {len(result['params'])}")
        print(f"  Grid size: {pipeline.transform._grid_size}")
    else:
        print(f"  Transform params: {result['params']}")
        print(f"  Transform matrix:\n{result['matrix']}")
    print(f"  Iterations: {result['iterations']}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Medical Image Registration Tool")
    parser.add_argument(
        "--fixed", type=str, default=None, help="Path to fixed image (CT)"
    )
    parser.add_argument(
        "--moving", type=str, default=None, help="Path to moving image (MRI)"
    )
    parser.add_argument(
        "--transform",
        type=str,
        default="rigid",
        choices=["rigid", "affine", "bspline"],
        help="Transformation type",
    )
    parser.add_argument(
        "--metric",
        type=str,
        default="nmi",
        choices=["mi", "nmi"],
        help="Similarity metric",
    )
    parser.add_argument(
        "--optimizer",
        type=str,
        default="lbfgsb",
        choices=["lbfgsb", "powell", "neldermead", "de"],

        help="Optimization algorithm",
    )
    parser.add_argument("--max-iter", type=int, default=200, help="Maximum iterations")
    parser.add_argument("--tol", type=float, default=1e-6, help="Convergence tolerance")
    parser.add_argument("--num-bins", type=int, default=64, help="Histogram bins for MI")
    parser.add_argument("--gpu", action="store_true", help="Enable GPU acceleration")
    parser.add_argument(
        "--no-multi-res", action="store_true", help="Disable multi-resolution"
    )
    parser.add_argument("--grid-spacing", type=int, default=32, help="B-spline grid spacing")
    parser.add_argument("--bspline-order", type=int, default=3, help="B-spline order")
    parser.add_argument("--reg-weight", type=float, default=0.01, help="Regularization weight for B-spline")
    parser.add_argument("--no-tre", action="store_true", help="Disable TRE computation")
    parser.add_argument("--num-landmarks", type=int, default=50, help="Number of landmark points for TRE")
    parser.add_argument("--output", type=str, default="output", help="Output directory")
    parser.add_argument("--demo", action="store_true", help="Run demo with synthetic data")

    args = parser.parse_args()

    if args.demo or (args.fixed is None and args.moving is None):
        print("Running demo mode with synthetic CT and MRI images...\n")
        run_demo(
            transform_type=args.transform,
            use_gpu=args.gpu,
            output_dir=args.output,
            grid_spacing=args.grid_spacing,
            bspline_order=args.bspline_order,
            regularization_weight=args.reg_weight,
        )
        return

    if args.fixed is None or args.moving is None:
        print("Error: Both --fixed and --moving must be provided for file-based registration.")
        return

    pipeline = RegistrationPipeline(
        transform_type=args.transform,
        dim=2,
        metric=args.metric,
        optimizer=args.optimizer,
        num_bins=args.num_bins,
        max_iter=args.max_iter,
        tol=args.tol,
        use_gpu=args.gpu,
        multi_resolution=not args.no_multi_res,
        num_levels=args.levels,
        verbose=True,
        grid_spacing=args.grid_spacing,
        bspline_order=args.bspline_order,
        regularization_weight=args.reg_weight,
    )

    result = pipeline.register_sitk(
        args.fixed, args.moving, output_dir=args.output,
        compute_tre=not args.no_tre,
        num_landmarks=args.num_landmarks,
    )

    print(f"\nFinal MI: {result['metric_value']:.6f}")
    if "tre" in result and result["tre"] is not None:
        print(f"TRE Mean: {result['tre']['mean']:.4f}, Median: {result['tre']['median']:.4f}")
    print(f"Transform params (first 10): {result['params'][:10]}")


if __name__ == "__main__":
    main()
