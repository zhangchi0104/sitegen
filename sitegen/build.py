from os import PathLike
from .config import Config
from . import ConfigOverrider
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from .extensions.template import MarkdownRender, AutoRefreshListener
import sys
import importlib
from .utils import LoggerMixin, build_keypath_from_relative_path
from shutil import copy, copytree


class ProjectRenderer(LoggerMixin):

    def __init__(self, project_dir: PathLike):
        super().__init__(name="sitegen:build")
        self._project_dir = project_dir if isinstance(
            project_dir, Path) else Path(project_dir)
        self._config = Config.from_toml(self._project_dir / 'config.toml')

        self._output_dir = self._project_dir / self._config.general.output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._content_loader = self._config.general.content_loader(
            self._project_dir)
        self._template_loader = FileSystemLoader(
            self._project_dir / self._config.general.template_dir)
        self._jinja_env = Environment(
            loader=self._template_loader,
            extensions=[MarkdownRender, AutoRefreshListener],
            autoescape=select_autoescape(['html', 'xml']),
        )
        self._merge_overrides()

    def handle_templates_dir(self):
        for template_path in self._template_loader.list_templates():
            p = Path(template_path)
            self.debug(f"Found file {template_path} in template dir")
            if not p.name.startswith("_") and p.name.endswith(".jinja"):
                self.info(f"Rendering {template_path}")
                template = self._jinja_env.get_template(template_path)
                keypath = build_keypath_from_relative_path(p)
                content = self._content_loader[keypath]
                rendered = template.render(**content)
                output_path = self._output_dir / p
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path = output_path.absolute().as_posix().removesuffix(
                    ".jinja")
                self.debug(f"Writing template to {output_path}")
                with open(output_path, 'w') as f:
                    f.write(rendered)
            elif not p.name.startswith("_"):
                src = p.absolute().as_posix()
                dst = (self._output_dir / p).absolute()
                dst.parent.mkdir(parents=True, exist_ok=True)
                self.debug(f"Copying {src} to {dst}")
                copy(src, dst.as_posix())

    def handle_static_dir(self):
        src = self._project_dir / self._config.general.static_dir
        dst = self._output_dir / self._config.general.static_dir
        dst.parent.mkdir(parents=True, exist_ok=True)
        self.debug(f"Copying static dir ('{src.as_posix()}') to {dst}")
        copytree(src.as_posix(), dst.as_posix())

    def _merge_overrides(self):
        sys.path.insert(1, self._project_dir.as_posix())
        try:
            overrides = importlib.import_module('overrides')
            overrider = ConfigOverrider()
            overrider: 'ConfigOverrider' = overrides.sitegen_overrides(
                overrider)
            self._jinja_env.markdown_render = overrider._markdown_render
        except ModuleNotFoundError:
            self.info(f"No overrides found in {self._project_dir}")

    def build(self):
        self.handle_templates_dir()
        self.handle_static_dir()
