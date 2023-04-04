from argparse import ArgumentParser
from sitegen.devserver import FileWatcher
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


async def main(args):
    project_root = Path(args.project_root)
    if args.verbose:
        logging.basicConfig(handlers=[RichHandler()], level=logging.DEBUG)
    else:
        logging.basicConfig(handlers=[RichHandler()], level=logging.INFO)
    logging.debug(f"Project Root: {args.project_root}")
    if args.command == "dev":
        dev_server = FileWatcher(
            project_root=project_root,
            port=args.port,
            addr=args.addr,
        )
        observer = Observer()
        observer.schedule(dev_server, path=args.project_root, recursive=True)
        observer.start()
        try:
            await dev_server._ws_server._server_task
        except KeyboardInterrupt:
            observer.stop()
            dev_server.terminate()
        observer.join()


if __name__ == "__main__":
    import asyncio as aio
    aio.run(main(parse_args()))