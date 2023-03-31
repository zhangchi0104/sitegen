from argparse import ArgumentParser
from sitegen.devserver import DevServer
from watchdog.observers import Observer
from rich.logging import RichHandler
from pathlib import Path
from sitegen.config import Config
import logging


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--project_root", "-p", default=".")
    parser.add_argument("--verbose", "-v", action="store_true")
    subparser = parser.add_subparsers(dest="command")
    dev_parser = subparser.add_parser("dev")
    dev_parser.add_argument("--port", "-P", default=8000)
    dev_parser.add_argument("--addr", "-A", default="0.0.0.0")

    return parser.parse_args()


def main(args):
    project_root = Path(args.project_root)
    config = Config.from_toml(project_root / "config.toml")
    if args.verbose:
        logging.basicConfig(handlers=[RichHandler()], level=logging.DEBUG)
    else:
        logging.basicConfig(handlers=[RichHandler()], level=logging.INFO)
    logging.debug(f"Project Root: {args.project_root}")
    if args.command == "dev":
        dev_server = DevServer(
            config=config,
            project_root=Path(args.project_root),
            port=args.port,
            addr=args.addr,
        )
        observer = Observer()
        observer.schedule(dev_server, path=args.project_root, recursive=True)
        observer.start()
        try:
            while True:
                input()
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


if __name__ == "__main__":
    main(parse_args())