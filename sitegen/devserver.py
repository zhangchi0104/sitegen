from types import FunctionType
from flask.templating import Environment
from watchdog.events import FileSystemEventHandler
from .extensions.template import AutoRefreshListener, MarkdownRender

from sitegen.extensions import ConfigOverrider
from .config import Config
from flask import Flask, render_template
import multiprocess as mp
from pathlib import Path
from websockets.server import serve, WebSocketServerProtocol
from websockets import broadcast
import asyncio as aio
from .utils import LoggerMixin
import typing as t
import os


class DevEnvironment(Environment):

    def __init__(self, *args, **kwargs):
        post_init_callback = kwargs.pop('post_init_callback', None)
        super().__init__(*args, **kwargs)
        if post_init_callback is not None:
            post_init_callback(self)


class WebSocketNotifier(LoggerMixin):

    def __init__(self, port, addr="0.0.0.0"):
        super().__init__(name="sitgen:WebSocketNotifier")
        self._server = serve(self._register_conn, addr, port)
        self._addr = addr
        self._port = port
        self._conns = set()

        self._queue = aio.Queue()
        self._server_task = None

    async def _register_conn(self, websocket: WebSocketServerProtocol):
        self._conns.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            self._conns.remove(websocket)

    async def _init_server(self):
        async with self._server:
            print(
                f"WebSocketNotifier listening on ws://{self._addr}:{self._port}"
            )

            await aio.Future()

    def run_in_background(self):
        if self._server_task is None:
            self._server_task = aio.create_task(self._init_server())

        else:
            raise RuntimeError("Server already running")

    async def run(self):
        if self._server_task is None:
            self.run_in_background()
            await self._server_task
        else:
            raise RuntimeError("Server already running")

    def terminate(self):
        if self._server_task is not None:
            self._server_task.cancel()
            self._server_task = None
        self._server.shutdown()

    def send_update_notification(self):
        self.debug("Sending update notification")
        broadcast(self._conns, "RELOAD")


class FileWatcher(FileSystemEventHandler, LoggerMixin):

    def __init__(
            self,
            project_root=Path("."),
            port=8000,
            addr="127.0.0.1",
            ws_port=8088,
    ):

        super().__init__(name="sitgen:ProjectWatcher")
        self._port = port
        self._addr = addr
        self._project_root = project_root if isinstance(
            project_root, Path) else Path(project_root)
        self._server = DevServer(__name__, project_root=self._project_root)
        self._ws_server = WebSocketNotifier(ws_port)
        self._ws_server.run_in_background()
        self.start_server()

    def terminate(self):
        self._ws_server.terminate()
        self.terminate_server()

    def _restart_server(self):
        if self._process is not None:
            self.info("Restarting dev server")
            self.terminate_server()
            self._server = DevServer(__name__, project_root=self._project_root)
        self.start_server()
        if self._process is not None:
            self._ws_server.send_update_notification()

    def start_server(self):
        self._process = self._create_process()
        self._process.start()
        self.info(f"Dev server istening on http://{self._addr}:{self._port}")

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
        if self._process is not None:
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


class DevServer(Flask, LoggerMixin):
    jinja_environment = DevEnvironment

    def __init__(
        self,
        import_name: str,
        static_url_path: t.Optional[str] = None,
        static_host: t.Optional[str] = None,
        host_matching: bool = False,
        subdomain_matching: bool = False,
        project_root: t.Optional[t.Union[str, os.PathLike]] = Path("."),
        instance_path: t.Optional[str] = None,
        instance_relative_config: bool = False,
        root_path: t.Optional[str] = None,
    ):
        LoggerMixin.__init__(self, name="sitegen:DevServer")
        self.jinja_options['extensions'] = [
            MarkdownRender, AutoRefreshListener
        ]
        self._project_root = Path(project_root) if not isinstance(
            project_root, str) else project_root
        self._logger.debug(f"Using project root: {self._project_root}")
        self._project_config = Config.from_toml(self._project_root /
                                                "config.toml")
        static_dir = self._project_root / Path(
            self._project_config.general.static_dir)
        template_dir = self._project_root / Path(
            self._project_config.general.template_dir)

        super().__init__(import_name, static_url_path,
                         static_dir.absolute().as_posix(), static_host,
                         host_matching, subdomain_matching,
                         template_dir.absolute().as_posix(), instance_path,
                         instance_relative_config, root_path)

        self._template_content = None
        self.derive_routes_from_dir()
        self._merge_overrides()

    def restart(self):
        self.reload_template_content()
        self.derive_routes_from_dir()
        self._merge_overrides()

    @property
    def template_content(self):
        if self._template_content is None:
            from tomli import load
            self.info(f"Loading template content from '{self.content_file}'")
            with open(self.content_file, "rb") as f:
                self._template_content = load(f)
        return self._template_content

    def reload_template_content(self):
        from tomli import load
        self.info(f"Loading template content from '{self.content_file}'")
        with open(self.content_file, "rb") as f:
            self._template_content = load(f)

    @property
    def content_file(self):
        return self._project_root / Path(
            self._project_config.general.content_file)

    def derive_routes_from_dir(self):
        for path in Path(self.template_folder).iterdir():
            if path.is_dir():
                self.derive_routes_from_dir()
            elif path.as_posix().endswith(
                    ".html.jinja") and not path.stem.startswith("_"):
                url_path = "/" if path.stem.startswith(
                    "index.") else f"/{path.stem.split('.')[0]}"
                context = self.lookup_context(url_path)
                context["SITEGEN_ENV"] = "dev"
                self.add_url_rule(
                    url_path,
                    endpoint=url_path,
                    view_func=self._create_view_func(
                        url_path.replace("/", "_"),
                        path.relative_to(self.template_folder).as_posix(),
                        **context,
                    ),
                )
                self.info(f"Added route '{url_path}' -> '{path}'")
                self._logger.debug(f"route '{url_path}' context: {context}")

    def lookup_context(self, url_path: str):
        res = None
        if url_path == "/":
            res = self.template_content.get("index", {})
        else:
            parts = url_path.strip("/").rstrip("/index").split("/")
            res = self.template_content
            for part in parts:
                res = res.get(part, {})
                if len(res) == 0:
                    break

        res['__globals__'] = self.template_content.get("__globals__", {})
        return res

    def _set_jinja_callback(self, overrides: ConfigOverrider):

        def callback(env: DevEnvironment):
            env.markdown_render = overrides._markdown_render

        self.jinja_options['post_init_callback'] = callback

    def _merge_overrides(self):
        import sys
        import importlib
        sys.path.insert(1, self._project_root.as_posix())
        mod = importlib.import_module("overrides")
        self._set_jinja_callback(mod.sitegen_overrides(ConfigOverrider()))

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
