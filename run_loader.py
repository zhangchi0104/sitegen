from sitegen.loaders.content import ContentPathLoader
from rich.pretty import pprint
import logging

logging.basicConfig(level=logging.DEBUG)
loader = ContentPathLoader("tomls")
loader.load()
pprint(loader._inner)
# pprint(loader['bar.baz'])