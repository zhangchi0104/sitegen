from flask.templating import Environment
from watchdog.events import FileSystemEventHandler
from .extensions.template import MarkdownRender

from sitegen.extensions import ConfigOverrider
from .config import Config
from flask import Flask, render_template
import multiprocess as mp
from pathlib import Path
from tomli import load
from types import FunctionType
from .utils import LoggerMixin


class DevEnvironment(Environment):

    def __init__(self, *args, **kwargs):
        post_init_callback = kwargs.pop('post_init_callback', None)
        super().__init__(*args, **kwargs)
        if post_init_callback is not None:
            post_init_callback(self)


class DevServer(FileSystemEventHandler, LoggerMixin):

    def __init__(
            self,
            config: Config,
            project_root=Path("."),
            port=8000,
            addr="127.0.0.1",
    ):

        super().__init__(name="sitgen:DevServer")
        self._config = config
        Flask.jinja_environment = DevEnvironment

        self._port = port
        self._addr = addr
        self._project_root = project_root if isinstance(
            project_root, Path) else Path(project_root)
        self.debug(f"Using config: {config}")
        self.debug(f"static_dir = {self.static_dir.absolute().as_posix()}")
        self._setup_jinja()
        self._reset_server()
        # setup routes
        self.start_server()

    def load_context(self):
        self.debug(f"Loading content from file '{self.content_file}'")
        with open(self.content_file, "rb") as f:
            self._content = load(f)

    @property
    def static_dir(self):
        return self._project_root / self._config.general.static_dir

    @property
    def template_dir(self):
        return self._project_root / self._config.general.template_dir

    def _reset_server(self):
        self._server = Flask(
            __name__,
            template_folder=self.template_dir.absolute().as_posix(),
            static_folder=self.static_dir.absolute().as_posix(),
            static_url_path="/static",
        )
        self.load_context()
        self._routes_lookup(self.template_dir)

    def lookup_context(self, url_path: str):
        if url_path == "/":
            return self._content.get("index", {})
        else:
            parts = url_path.strip("/").rstrip("/index").split("/")
            res = self._content
            for part in parts:
                res = res.get(part, {})
                if len(res) == 0:
                    return res
            return res

    def _setup_jinja(self):
        import sys
        import importlib
        sys.path.insert(1, self._project_root.as_posix())
        mod = importlib.import_module("overrides")
        Flask.jinja_options['extensions'] = [MarkdownRender]
        self._merge_overrides(mod.sitegen_overrides(ConfigOverrider()))

    @property
    def content_file(self):
        return self._project_root / self._config.general.content_file

    def _restart_server(self):
        if self._process is None:
            self.start_server()
        else:
            self.info("Restarting dev server")
            self.terminate_server()
            self._reset_server()
            self.start_server()

    def start_server(self):
        self._process = self._create_process()
        self._process.start()
        self.info(f"Dev server istening on http://{self._addr}:{self._port}")

    def _routes_lookup(self, routes_dir: str, prefix: str = ""):
        with self._server.app_context():
            for path in Path(routes_dir).iterdir():
                if path.is_dir():
                    self._routes_lookup(path, prefix + f"/{path.name}")
                elif path.as_posix().endswith(
                        ".html.jinja") and not path.stem.startswith("_"):
                    url_path = prefix if path.stem.startswith(
                        "index.") else f"{prefix}/{path.stem.split('.')[0]}"
                    if url_path == "":
                        url_path = "/"
                    context = self.lookup_context(url_path)
                    context["SITEGEN_ENV"] = "dev"
                    self._server.add_url_rule(
                        url_path,
                        view_func=self._create_view_func(
                            url_path.replace("/", "_"),
                            path.relative_to(self.template_dir).as_posix(),
                            **context,
                        ),
                    )
                    self.info(
                        f"Adding route: GET {url_path} -> {path.as_posix()} with context {context}"
                    )

    def _merge_overrides(self, overrides: ConfigOverrider):

        def callback(env: DevEnvironment):
            env.markdown_render = overrides._markdown_render

        Flask.jinja_options['post_init_callback'] = callback

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
                "debug": False,
            },
        )

    def terminate_server(self):
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


class ConfigOverrides:

    def __init__(self):
        pass