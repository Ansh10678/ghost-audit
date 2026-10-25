import argparse
import sys
from pathlib import Path

# Add code/ to sys.path
CODE_DIR = Path(__file__).resolve().parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from src.config import Config
from src.pipeline import AuditPipeline


def run_audit(input_path: str, output_path: str, dataset_dir: str):
    pipeline = AuditPipeline(dataset_dir=dataset_dir)
    pipeline.process_file(input_csv=input_path, output_csv=output_path)


def run_eval(dataset_dir: str):
    from evaluation.main import run_evaluation

    run_evaluation(dataset_dir=dataset_dir)


def main():
    parser = argparse.ArgumentParser(description="Northstar Shop Deletion Audit Agent CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Run subparser
    run_parser = subparsers.add_parser("run", help="Run deletion audit on requests")
    run_parser.add_argument(
        "--input",
        "-i",
        default=str(Config.DEFAULT_INPUT),
        help="Path to input deletion requests CSV",
    )
    run_parser.add_argument(
        "--output",
        "-o",
        default=str(Config.DEFAULT_OUTPUT),
        help="Path where output.csv should be written",
    )
    run_parser.add_argument(
        "--dataset-dir", "-d", default=str(Config.DATASET_DIR), help="Path to dataset directory"
    )

    # Eval subparser
    eval_parser = subparsers.add_parser("eval", help="Run evaluation on sample requests")
    eval_parser.add_argument(
        "--dataset-dir", "-d", default=str(Config.DATASET_DIR), help="Path to dataset directory"
    )

    args = parser.parse_args()

    # Default to run if no command specified
    if not args.command:
        run_audit(
            input_path=str(Config.DEFAULT_INPUT),
            output_path=str(Config.DEFAULT_OUTPUT),
            dataset_dir=str(Config.DATASET_DIR),
        )
    elif args.command == "run":
        run_audit(
            input_path=args.input,
            output_path=args.output,
            dataset_dir=args.dataset_dir,
        )
    elif args.command == "eval":
        run_eval(dataset_dir=args.dataset_dir)


if __name__ == "__main__":
    main()
