from pathlib import Path
from pydantic import BaseModel
from os import PathLike

from sitegen.loaders.content import ContentMappingLoader, ContentPathLoader


class ContentMapping(BaseModel):
    content: str
    name: str


class GeneralConfig(BaseModel):
    template_dir: str = "templates"
    output_dir: str = "output"
    static_dir: str = "static"
    content: str | ContentMapping = "content.toml"

    def content_loader(self, project_root=Path('.')):
        if isinstance(self.content, str):
            p = project_root / Path(self.content)
            is_toml = p.suffix == ".toml"
            is_dir = p.is_dir()
            if is_dir or is_toml:
                return ContentPathLoader(p)
            else:
                raise ValueError(
                    f"Invalid content config: {self.content} is not a valid path"
                )
        elif isinstance(self.content, ContentMapping):
            return ContentMappingLoader(self.content)
        else:
            raise ValueError(
                f"Invalid content config: {self.content} is not a valid config"
            )


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
