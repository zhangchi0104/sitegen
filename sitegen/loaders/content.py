import os
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Any

from tomli import load

from benedict import benedict

from sitegen.utils import LoggerMixin


def get_dict_val_by_level(val: dict, path: str):
    parts = path.split('.')
    res = val
    for part in parts:
        res = res[part]
    return res


class _ContentUrlIndexer(object):

    def __init__(self, data: benedict | None):
        self._data = data

    def __getitem__(self, item: str):
        path = self._convert_url_to_dotpath(item)
        res = self._data[path]
        res["__globals__"] = self._data.get("__globals__", {})
        return res

    def get(self, key, default=None):
        path = self._convert_url_to_dotpath(key)
        res = self._data.get(path, default)
        res["__globals__"] = self._data.get("__globals__", {})
        return res

    @staticmethod
    def _convert_url_to_dotpath(path: str):
        if path == "/":
            return "index"
        return path.strip('/').replace('/', '.')


class ContentLoader(metaclass=ABCMeta):

    def __init__(self, p: str | Path | Any):
        self._inner: benedict | None = None
        self._content_cfg = p
        self._url_indexer = _ContentUrlIndexer(self._inner)

    @abstractmethod
    def load(self):
        raise NotImplementedError()

    def __getitem__(self, item: str):
        result = None

        try:
            result = self._inner[item]
            result["__globals__"] = self._inner.get("__globals__", {})
            return result
        except KeyError:
            if item.endswith('.index'):
                result = self._inner[item.removesuffix('.index')]
                result["__globals__"] = self._inner.get("__globals__", {})
                return result

    def get(self, key, default=None):
        self._inner.get(key, default)

    @property
    def url_indexer(self) -> _ContentUrlIndexer:
        return self._url_indexer


class ContentPathLoader(ContentLoader, LoggerMixin):

    def __init__(self, p):
        ContentLoader.__init__(self, p)
        LoggerMixin.__init__(self, "ContentDirLoader")
        self.load()

    def load(self):
        p = Path(self._content_cfg) if not isinstance(
            self._content_cfg, Path) else self._content_cfg
        if p.is_file() and p.suffix == ".toml":
            with open(p, 'rb') as f:
                self._inner = benedict(load(f))
        elif p.is_dir():
            self._recursive_load(p)
        self._url_indexer = _ContentUrlIndexer(self._inner)

    def _recursive_load(self, path: Path):
        queue = [path]
        res = benedict()
        while len(queue) > 0:
            print(queue)
            p = queue.pop()
            content = None
            if p.is_file() and p.name.endswith(".toml"):
                with open(p, 'rb') as f:
                    content = benedict(load(f))
            elif p.is_dir():
                queue.extend(list(p.iterdir()))
            if content is not None:
                suffixes = p.suffixes
                full_path = p.relative_to(path).as_posix()
                for suffix in suffixes:
                    full_path = full_path.removesuffix(suffix)
                if full_path == ".":
                    full_path = "index"

                full_path = full_path.replace('/', '.')
                self.debug(f"Adding {full_path} to {content}")
                if full_path in res:
                    raise KeyError(f"Duplicate key {full_path}")
                res[full_path] = content
        self._inner = res


class ContentMappingLoader(ContentLoader):

    def __init__(self, p: Any):
        ContentLoader.__init__(self, p)
        self.load()

    def load(self):
        for cfg in self._content_cfg:
            keypath = self.url_to_benedict_keypath(cfg.name)
            self._inner[keypath] = cfg.content
        self._url_indexer = _ContentUrlIndexer(self._inner)

    @staticmethod
    def url_to_benedict_keypath(key: str):
        if key == "/":
            return "index"
        else:
            return key.strip('/').replace('/', '.')