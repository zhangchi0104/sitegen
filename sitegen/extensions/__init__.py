from sitegen.extensions.template import HTMLRenderer
from typing import Type


class ConfigOverrider:

    def __init__(self):
        self._markdown_render = HTMLRenderer

    def set_markdown_render(self, renderer_cls: Type[HTMLRenderer]):
        if not issubclass(renderer_cls, HTMLRenderer):
            raise TypeError(
                f"{renderer_cls} is not a subclass of HTMLRenderer")
        self._markdown_render = renderer_cls
