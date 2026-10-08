"""Command-line interface; all paths and input units are explicit."""

import argparse
import json
import sys

from . import __version__


def main(argv=None):
    parser = argparse.ArgumentParser(prog="g1spei")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    verify = sub.add_parser("verify-parameters", help="Read every parameter and verify SHA-256")
    verify.add_argument("--parameters", required=True)
    run = sub.add_parser("run", help="Produce one month with bounded memory")
    run.add_argument("--parameters", required=True)
    run.add_argument("--precipitation", required=True)
    run.add_argument("--temperature", required=True)
    run.add_argument("--output", required=True)
    run.add_argument("--year", type=int, required=True)
    run.add_argument("--month", type=int, required=True)
    run.add_argument(
        "--precipitation-unit", choices=["m_month", "mm_month", "m_day", "mm_day"], required=True
    )
    run.add_argument("--temperature-unit", choices=["K", "C"], required=True)
    run.add_argument("--profile", choices=["guarded", "reference"], default="guarded")
    run.add_argument(
        "--min-std",
        type=float,
        default=None,
        help="Minimum coarse P standard deviation in mm/month",
    )
    run.add_argument(
        "--coastal-distance",
        type=float,
        default=2,
        help="IDW search radius in coarse pixels; 0 disables",
    )
    run.add_argument("--tile-size", type=int, default=512)
    run.add_argument("--window", nargs=4, type=int, metavar=("XOFF", "YOFF", "WIDTH", "HEIGHT"))
    args = vars(parser.parse_args(argv))
    command = args.pop("command")
    try:
        if command == "verify-parameters":
            from .parameters import verify

            result = verify(args["parameters"])
        else:
            from .pipeline import run

            result = run(**args)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, RuntimeError, FileNotFoundError, FileExistsError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
