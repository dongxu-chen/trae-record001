"""Command-line interface for headless calibration.

Mono calibration (single camera)::

    python -m camera_calib.cli mono --images ./calib_images/ \\
        --pattern 9 6 --spacing 25.0 \\
        --pattern-type chessboard --output calibration.json

Stereo (binocular) calibration::

    python -m camera_calib.cli stereo \\
        --left ./left/ --right ./right/ \\
        --pattern 9 6 --spacing 25.0 \\
        --output stereo_calibration.json
"""

from __future__ import annotations

import argparse
import os
import sys

from .calibrator import (
    CameraCalibrator,
    PatternType,
    StereoCalibrator,
    SUPPORTED_EXT,
)


PATTERN_CHOICES = {m.value for m in PatternType}


def _collect_paths(entries):
    paths = []
    for entry in entries:
        if os.path.isdir(entry):
            paths.extend(
                os.path.join(entry, f)
                for f in sorted(os.listdir(entry))
                if os.path.splitext(f)[1].lower() in SUPPORTED_EXT
            )
        else:
            paths.append(entry)
    return paths


def _pattern_type(value: str) -> PatternType:
    if value not in PATTERN_CHOICES:
        raise argparse.ArgumentTypeError(
            f"Unknown pattern type {value!r}; expected one of "
            f"{sorted(PATTERN_CHOICES)}"
        )
    return PatternType(value)


# ----------------------------------------------------------------------
# Mono subcommand
# ----------------------------------------------------------------------


def build_mono_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mono",
        description="Single-camera calibration using a chessboard or circle-grid.",
    )
    parser.add_argument(
        "--images", "-i", nargs="+", required=True,
        help="One or more image paths or directories containing images.",
    )
    parser.add_argument(
        "--pattern", "-p", type=int, nargs=2, metavar=("NX", "NY"),
        default=(9, 6),
        help="Number of inner corners / circles along X and Y (default: 9 6).",
    )
    parser.add_argument(
        "--spacing", "-s", dest="spacing", type=float, default=25.0,
        help="Physical square / circle spacing in mm (default: 25.0).",
    )
    parser.add_argument(
        "--pattern-type", "-t", type=_pattern_type,
        default=PatternType.CHESSBOARD,
        help="Target geometry: chessboard, circles_symmetric, or "
             "circles_asymmetric (default: chessboard).",
    )
    parser.add_argument(
        "--no-clahe", action="store_true",
        help="Disable CLAHE adaptive histogram equalization.",
    )
    parser.add_argument(
        "--clahe-clip", type=float, default=2.0,
        help="CLAHE clip limit (default: 2.0).",
    )
    parser.add_argument(
        "--clahe-grid", type=int, default=8,
        help="CLAHE tile grid size in pixels (default: 8).",
    )
    parser.add_argument(
        "--alpha", type=float, default=0.5,
        help="FOV balance for undistortion: 0 = crop to valid pixels, "
             "1 = full FOV, 0.5 = balanced (default: 0.5).",
    )
    parser.add_argument(
        "--output", "-o", default="calibration.json",
        help="Path for the JSON result file.",
    )
    parser.add_argument(
        "--plot", default=None,
        help="Optional path for the reprojection-error PNG plot.",
    )
    parser.add_argument(
        "--report", default=None,
        help="Optional path for the quality-report text file.",
    )
    return parser


def run_mono(args) -> int:
    if not (0.0 <= args.alpha <= 1.0):
        print("ERROR: --alpha must be between 0 and 1.", file=sys.stderr)
        return 2

    grid = int(args.clahe_grid)
    calibrator = CameraCalibrator(
        pattern_size=tuple(args.pattern),
        square_size=args.spacing,
        use_clahe=not args.no_clahe,
        clahe_clip=args.clahe_clip,
        clahe_grid=(grid, grid),
        pattern_type=args.pattern_type,
    )

    paths = _collect_paths(args.images)

    print(f"[{args.pattern_type.value}] Processing {len(paths)} image(s)...")
    for p, ok, msg in calibrator.add_images(paths):
        status = "OK" if ok else f"SKIP ({msg})"
        print(f"  {status:40s}  {p}")

    if calibrator.num_valid_images < 2:
        print("ERROR: need at least 2 images with detected pattern features.",
              file=sys.stderr)
        return 1

    result = calibrator.calibrate(alpha=args.alpha)
    print(f"\nRMS reprojection error: {result.reprojection_error:.4f} px")
    print(f"Intrinsics (fx, fy, cx, cy): "
          f"{result.focal_lengths_px[0]:.4f}, "
          f"{result.focal_lengths_px[1]:.4f}, "
          f"{result.principal_point_px[0]:.4f}, "
          f"{result.principal_point_px[1]:.4f}")
    print(f"Distortion: {result.dist_coeffs.ravel().tolist()}")

    report = result.quality_report()
    print(report.format_text())

    result.save(args.output)
    print(f"Saved calibration to {args.output}")

    if args.plot:
        from .visualizer import plot_reprojection_errors
        plot_reprojection_errors(result, save_path=args.plot)
        print(f"Saved error plot to {args.plot}")

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(report.format_text() + "\n")
        print(f"Saved quality report to {args.report}")

    return 0


# ----------------------------------------------------------------------
# Stereo subcommand
# ----------------------------------------------------------------------


def build_stereo_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stereo",
        description="Stereo (binocular) camera calibration.",
    )
    parser.add_argument(
        "--left", nargs="+", required=True,
        help="Left-camera image paths / directories.",
    )
    parser.add_argument(
        "--right", nargs="+", required=True,
        help="Right-camera image paths / directories.",
    )
    parser.add_argument(
        "--pattern", "-p", type=int, nargs=2, metavar=("NX", "NY"),
        default=(9, 6),
        help="Number of inner corners / circles along X and Y (default: 9 6).",
    )
    parser.add_argument(
        "--spacing", "-s", dest="spacing", type=float, default=25.0,
        help="Physical square / circle spacing in mm (default: 25.0).",
    )
    parser.add_argument(
        "--pattern-type", "-t", type=_pattern_type,
        default=PatternType.CHESSBOARD,
        help="Target geometry (default: chessboard).",
    )
    parser.add_argument(
        "--no-clahe", action="store_true",
        help="Disable CLAHE.",
    )
    parser.add_argument(
        "--clahe-clip", type=float, default=2.0,
    )
    parser.add_argument(
        "--clahe-grid", type=int, default=8,
    )
    parser.add_argument(
        "--alpha", type=float, default=0.5,
        help="Mono undistortion alpha (default: 0.5).",
    )
    parser.add_argument(
        "--rectify-alpha", type=float, default=0.0,
        help="Stereo rectify alpha: 0 = crop (default), 1 = full FOV.",
    )
    parser.add_argument(
        "--output", "-o", default="stereo_calibration.json",
        help="Path for the stereo JSON result file.",
    )
    return parser


def _pair_files(left_paths, right_paths):
    n = min(len(left_paths), len(right_paths))
    if len(left_paths) != len(right_paths):
        print(
            f"WARNING: left has {len(left_paths)} files, right has "
            f"{len(right_paths)}; using first {n} from each.",
            file=sys.stderr,
        )
    return list(zip(left_paths[:n], right_paths[:n]))


def run_stereo(args) -> int:
    if not (0.0 <= args.alpha <= 1.0):
        print("ERROR: --alpha must be between 0 and 1.", file=sys.stderr)
        return 2

    left_paths = _collect_paths(args.left)
    right_paths = _collect_paths(args.right)
    pairs = _pair_files(left_paths, right_paths)
    if len(pairs) < 2:
        print("ERROR: need at least 2 valid stereo pairs.", file=sys.stderr)
        return 1

    grid = int(args.clahe_grid)
    stereo = StereoCalibrator(
        pattern_size=tuple(args.pattern),
        square_size=args.spacing,
        use_clahe=not args.no_clahe,
        clahe_clip=args.clahe_clip,
        clahe_grid=(grid, grid),
        pattern_type=args.pattern_type,
    )

    print(f"[{args.pattern_type.value}] Processing {len(pairs)} stereo pair(s)...")
    results = stereo.add_image_pairs(pairs)
    for l, r, ok, msg in results:
        status = "OK" if ok else f"SKIP ({msg})"
        print(f"  {status:40s}  L={os.path.basename(l):20s}  R={os.path.basename(r)}")

    if stereo.num_valid_pairs < 2:
        print("ERROR: need at least 2 valid stereo pairs with detected features.",
              file=sys.stderr)
        return 1

    result = stereo.calibrate(alpha=args.alpha, rectify_alpha=args.rectify_alpha)
    print(f"\nStereo RMS       : {result.rms:.4f} px")
    print(f"Left mono RMS    : {result.left.reprojection_error:.4f} px")
    print(f"Right mono RMS   : {result.right.reprojection_error:.4f} px")
    print(f"Baseline         : {result.baseline_mm:.3f} mm")
    print(f"f_left  (rect.)  : {result.focal_length_left_px:.4f} px")
    print(f"f_right (rect.)  : {result.focal_length_right_px:.4f} px")
    print(f"Depth formula    : Z = f * {result.baseline_mm:.2f} / d  (mm)")

    report = result.left.quality_report()
    print("\nLeft camera quality:")
    print(report.format_text())
    report_r = result.right.quality_report()
    print("\nRight camera quality:")
    print(report_r.format_text())

    result.save(args.output)
    print(f"Saved stereo calibration to {args.output}")
    return 0


# ----------------------------------------------------------------------
# Top-level entry
# ----------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Camera calibration using chessboard / circle-grid targets.",
    )
    sub = parser.add_subparsers(dest="mode")
    sub.required = True

    mono_p = build_mono_parser()
    sub.add_parser("mono", parents=[mono_p], add_help=False,
                   help="Single-camera calibration.")

    stereo_p = build_stereo_parser()
    sub.add_parser("stereo", parents=[stereo_p], add_help=False,
                   help="Stereo (binocular) calibration.")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.mode == "mono":
        return run_mono(args)
    if args.mode == "stereo":
        return run_stereo(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
