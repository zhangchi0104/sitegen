from pydantic import BaseModel
from os import PathLike


class GeneralConfig(BaseModel):
    template_dir: str = "templates"
    output_dir: str = "output"
    static_dir: str = "static"
    content_file: str = "content.toml"


class DeployConfig(BaseModel):
    branch: str = "gh-pages"


class Route(BaseModel):
    path: str
    template: str

    @property
    def name(self):
        return self.path[1:]


class RouterConfig(BaseModel):
    routes: list[Route] = []
    hash_route = False


class Config(BaseModel):
    general: GeneralConfig
    deploy: DeployConfig

    @classmethod
    def from_toml(cls, path: "PathLike") -> "Config":
        from tomli import load
        with open(path, "rb") as f:
            return cls(**load(f))
