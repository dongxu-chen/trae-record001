import argparse
import torch
from gan_framework.config import TrainConfig
from gan_framework.trainer import GANTrainer
from gan_framework.models import build_models


def parse_args():
    parser = argparse.ArgumentParser(description="GAN Training Framework")

    parser.add_argument("--architecture", type=str, default="dcgan",
                        choices=["dcgan", "wgan-gp", "stylegan2"],
                        help="GAN architecture to use")
    parser.add_argument("--dataset", type=str, default="cifar10",
                        choices=["cifar10", "mnist", "stl10", "folder"],
                        help="Dataset to train on")
    parser.add_argument("--data_root", type=str, default="./data")
    parser.add_argument("--img_size", type=int, default=32)
    parser.add_argument("--img_channels", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=64)
    parser.add_argument("--num_workers", type=int, default=4)
    parser.add_argument("--z_dim", type=int, default=128)
    parser.add_argument("--g_lr", type=float, default=2e-4)
    parser.add_argument("--d_lr", type=float, default=2e-4)
    parser.add_argument("--beta1", type=float, default=0.0)
    parser.add_argument("--beta2", type=float, default=0.999)
    parser.add_argument("--num_epochs", type=int, default=200)
    parser.add_argument("--n_critic", type=int, default=1)
    parser.add_argument("--lambda_gp", type=float, default=10.0)
    parser.add_argument("--d_spectral_norm", action="store_true")
    parser.add_argument("--g_spectral_norm", action="store_true")
    parser.add_argument("--style_dim", type=int, default=512)
    parser.add_argument("--n_layers_style", type=int, default=8)
    parser.add_argument("--checkpoint_dir", type=str, default="./checkpoints")
    parser.add_argument("--sample_dir", type=str, default="./samples")
    parser.add_argument("--log_dir", type=str, default="./runs")
    parser.add_argument("--sample_interval", type=int, default=1000)
    parser.add_argument("--checkpoint_interval", type=int, default=5000)
    parser.add_argument("--num_sample_images", type=int, default=64)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--use_ema", action="store_true")
    parser.add_argument("--ema_decay", type=float, default=0.999)
    parser.add_argument("--g_base_channels", type=int, default=64)
    parser.add_argument("--d_base_channels", type=int, default=64)
    parser.add_argument("--lazy_reg_interval", type=int, default=16)
    parser.add_argument("--stylegan2_r1_gamma", type=float, default=10.0)
    parser.add_argument("--stylegan2_path_reg_gamma", type=float, default=2.0)
    parser.add_argument("--gp_edge_ratio", type=float, default=0.3)
    parser.add_argument("--gp_edge_threshold", type=float, default=0.15)
    parser.add_argument("--gp_edge_weight", type=float, default=2.0)
    parser.add_argument("--mapping_dropout", type=float, default=0.2)
    parser.add_argument("--checkpoint_max_keep", type=int, default=5)
    parser.add_argument("--checkpoint_expire_seconds", type=float, default=86400.0)
    parser.add_argument("--use_amp", action="store_true")
    parser.add_argument("--fid_kid_enabled", action="store_true")
    parser.add_argument("--fid_num_samples", type=int, default=10000)
    parser.add_argument("--fid_batch_size", type=int, default=128)
    parser.add_argument("--kid_subset_size", type=int, default=1000)
    parser.add_argument("--kid_subsets", type=int, default=100)
    parser.add_argument("--interpolation_frames", type=int, default=120)
    parser.add_argument("--interpolation_fps", type=int, default=30)
    parser.add_argument("--num_eval_images", type=int, default=50000)

    subparsers = parser.add_subparsers(dest="command")

    gen_parser = subparsers.add_parser("generate", help="Generate samples from a checkpoint")
    gen_parser.add_argument("--checkpoint", type=str, required=True, help="Path to checkpoint")
    gen_parser.add_argument("--output", type=str, default="./generated.png", help="Output image path")
    gen_parser.add_argument("--num_images", type=int, default=64, help="Number of images to generate")
    gen_parser.add_argument("--nrow", type=int, default=8, help="Number of images per row")

    interp_parser = subparsers.add_parser("interpolate", help="Generate latent space interpolation video")
    interp_parser.add_argument("--checkpoint", type=str, required=True, help="Path to checkpoint")
    interp_parser.add_argument("--output", type=str, default="./interpolation.mp4", help="Output video path")
    interp_parser.add_argument("--num_samples", type=int, default=16, help="Number of images per frame")
    interp_parser.add_argument("--num_frames", type=int, default=120, help="Number of frames")
    interp_parser.add_argument("--fps", type=int, default=30, help="Frames per second")
    interp_parser.add_argument("--use_slerp", action="store_true", default=True, help="Use spherical interpolation")
    interp_parser.add_argument("--gif", action="store_true", help="Output GIF instead of MP4")

    return parser.parse_args()


def train(args):
    config = TrainConfig.from_args(args)
    torch.manual_seed(config.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(config.seed)

    config.save(f"{config.checkpoint_dir}/config.json")

    trainer = GANTrainer(config)
    trainer.train()


def generate(args):
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    config = TrainConfig(**checkpoint["config"])

    g, _ = build_models(config)
    g.load_state_dict(checkpoint["g_state_dict"])
    g.eval()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    g.to(device)

    z = torch.randn(args.num_images, config.z_dim, device=device)
    with torch.no_grad():
        samples = g(z)

    from torchvision.utils import save_image, make_grid

    grid = make_grid(samples, nrow=args.nrow, normalize=True, value_range=(-1, 1))
    save_image(grid, args.output)
    print(f"Generated {args.num_images} images saved to {args.output}")


def interpolate(args):
    from gan_framework.utils.interpolation import LatentInterpolationAnimator

    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    config = TrainConfig(**checkpoint["config"])

    g, _ = build_models(config)
    g.load_state_dict(checkpoint["g_state_dict"])
    g.eval()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    g.to(device)

    animator = LatentInterpolationAnimator(config, device, output_dir="./")
    output_path = args.output

    if args.gif:
        if not output_path.endswith(".gif"):
            output_path = output_path.replace(".mp4", ".gif")
        final_path = animator.generate_interpolation_gif(
            g,
            num_samples=args.num_samples,
            num_frames=args.num_frames,
            fps=args.fps,
            output_path=output_path,
        )
    else:
        final_path = animator.generate_interpolation_video(
            g,
            num_samples=args.num_samples,
            num_frames=args.num_frames,
            fps=args.fps,
            output_path=output_path,
            use_slerp=args.use_slerp,
        )
    print(f"Interpolation animation saved to {final_path}")


def main():
    args = parse_args()

    if args.command == "generate":
        generate(args)
    elif args.command == "interpolate":
        interpolate(args)
    else:
        train(args)


if __name__ == "__main__":
    main()
