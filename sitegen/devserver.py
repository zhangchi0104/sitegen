import logging
from watchdog.events import FileSystemEventHandler
from .config import Config
from flask import Flask, render_template
import multiprocess as mp
from pathlib import Path
from tomli import load
from types import FunctionType


class DevServer(FileSystemEventHandler):

    def __init__(
            self,
            config: Config,
            project_root=Path("."),
            port=8000,
            addr="127.0.0.1",
    ):
        super().__init__()
        self._logger = logging.getLogger("sitegen.devserver")
        self._config = config
        if self._config.router.hash_route:
            self._logger.info(
                "In dev server, hash routing is replaced with normal routing",
            )
        self._port = port
        self._addr = addr
        self._project_root = project_root if isinstance(
            project_root, Path) else Path(project_root)
        self._logger.debug(f"template_dir: {self.template_dir}")
        self._server = Flask(
            __name__,
            template_folder=self.template_dir.absolute().as_posix(),
        )
        self._content = None
        self._process = None

        self._logger.debug(f"Loading content from file '{self.content_file}'")
        with open(self.content_file, "rb") as f:
            self._content = load(f)
        # setup routes
        with self._server.app_context():
            for route in self._config.router.routes:
                self._logger.debug(
                    f"Adding route: GET {route.path} -> template: {self.template_dir / route.template}"
                )
                self._server.add_url_rule(
                    route.path,
                    view_func=self._create_view_func(
                        route.name,
                        route.template,
                        **self._content.get(route.name, {}),
                    ),
                )

        self._restart_server()

    @property
    def template_dir(self):
        return self._project_root / self._config.general.template_dir

    @property
    def content_file(self):
        return self._project_root / self._config.general.content_file

    def _restart_server(self):
        if self._process is None:

            self._process = self._create_process()
            self._process.start()
            self._logger.info(
                f"Dev server istening on http://{self._addr}:{self._port}")
        else:
            self._logger.info("Restarting dev server")
            self.terminate()
            self._process = self._create_process()
            self._logger.info(
                f"Dev server istening on http://{self._addr}:{self._port}")
            self._process.start()

    @staticmethod
    def _create_view_func(prefix, path: str, **context):

        def view_func():
            return render_template(path, **context)

        fn = FunctionType(
            view_func.__code__,
            view_func.__globals__,
            f"{prefix}_view_func",
            view_func.__defaults__,
            view_func.__closure__,
        )
        return fn

    def _create_process(self):
        return mp.Process(
            target=self._server.run,
            kwargs={
                "host": self._addr,
                "port": self._port,
                "debug": False
            },
        )

    def terminate(self):
        if self._process is not None and self._process.is_alive():

            self._process.terminate()
            self._process.join()
            self._process = None

    def on_moved(self, event):
        self._restart_server()

    def on_deleted(self, event):
        self._restart_server()

    def on_modified(self, event):
        self._restart_server()

    def on_created(self, event):
        self._restart_server()
