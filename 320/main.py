import os
import argparse
from config import Config
from generate_sample_data import generate_sample_data


def run_pipeline(config: Config, args):
    if args.generate_data:
        print("=" * 60)
        print("Generating Sample Data")
        print("=" * 60)
        generate_sample_data(
            output_dir=config.data_dir,
            num_samples=args.num_samples,
            image_size=config.image_size,
        )

    if args.train:
        print("\n" + "=" * 60)
        print("Starting Training")
        print("=" * 60)
        from train import train
        train(config)

    if args.evaluate:
        print("\n" + "=" * 60)
        print("Starting Evaluation")
        print("=" * 60)
        from evaluate import main as evaluate
        evaluate(config)

    if args.predict:
        print("\n" + "=" * 60)
        print("Running Inference")
        print("=" * 60)
        from inference import main as inference
        inference()

    if args.visualize:
        print("\n" + "=" * 60)
        print("Generating Visualizations")
        print("=" * 60)
        from visualize import (
            plot_training_history,
            visualize_results,
        )

        history_path = os.path.join(config.log_dir, "training_history.json")
        if os.path.exists(history_path):
            plot_training_history(
                history_path,
                save_path=os.path.join(config.result_dir, "training_history.png"),
            )

        visualize_results(
            image_dir=config.image_dir,
            label_dir=config.label_dir,
            pred_dir=config.result_dir,
            output_dir=os.path.join(config.result_dir, "visualizations"),
            class_names=config.class_names,
            num_samples=3,
            num_slices=5,
        )

    if args.all:
        print("=" * 60)
        print("Running Full Pipeline: Data -> Train -> Evaluate -> Predict -> Visualize")
        print("=" * 60)

        from generate_sample_data import generate_sample_data
        from train import train
        from evaluate import main as evaluate
        from inference import main as inference
        from visualize import plot_training_history, visualize_results

        print("\n[1/5] Generating sample data...")
        generate_sample_data(
            output_dir=config.data_dir,
            num_samples=args.num_samples,
            image_size=config.image_size,
        )

        print("\n[2/5] Training model...")
        model, history = train(config)

        print("\n[3/5] Evaluating model...")
        evaluate(config)

        print("\n[4/5] Running inference...")
        inference()

        print("\n[5/5] Generating visualizations...")
        history_path = os.path.join(config.log_dir, "training_history.json")
        if os.path.exists(history_path):
            plot_training_history(
                history_path,
                save_path=os.path.join(config.result_dir, "training_history.png"),
            )

        visualize_results(
            image_dir=config.image_dir,
            label_dir=config.label_dir,
            pred_dir=config.result_dir,
            output_dir=os.path.join(config.result_dir, "visualizations"),
            class_names=config.class_names,
            num_samples=3,
            num_slices=5,
        )

        print("\n" + "=" * 60)
        print("Full pipeline completed successfully!")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="3D Medical Image Segmentation Pipeline")
    parser.add_argument("--generate_data", action="store_true", help="Generate sample data")
    parser.add_argument("--train", action="store_true", help="Train the model")
    parser.add_argument("--evaluate", action="store_true", help="Evaluate the model")
    parser.add_argument("--predict", action="store_true", help="Run inference")
    parser.add_argument("--visualize", action="store_true", help="Generate visualizations")
    parser.add_argument("--all", action="store_true", help="Run full pipeline")
    parser.add_argument("--num_samples", type=int, default=10, help="Number of samples to generate")
    parser.add_argument("--num_epochs", type=int, default=None, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=None, help="Batch size")
    parser.add_argument("--num_classes", type=int, default=None, help="Number of classes")

    args = parser.parse_args()

    config = Config()

    if args.num_epochs is not None:
        config.num_epochs = args.num_epochs
    if args.batch_size is not None:
        config.batch_size = args.batch_size
    if args.num_classes is not None:
        config.num_classes = args.num_classes

    if not any([args.generate_data, args.train, args.evaluate, args.predict, args.visualize, args.all]):
        parser.print_help()
        print("\nExample usage:")
        print("  python main.py --all --num_samples 10")
        print("  python main.py --generate_data --train")
        print("  python main.py --evaluate --visualize")
        return

    run_pipeline(config, args)


if __name__ == "__main__":
    main()
