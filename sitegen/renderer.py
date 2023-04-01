from pathlib import Path


class Render:

    def __init__(self, projecct_dir: str):
        pass

    @property
    def output_dir(self):
        return Path(self._conf.output_dir)

    @property
    def static_dir(self):
        return Path(self._conf.output_dir)

    @property
    def template_dir(self):
        return Path(self._conf.template_dir)
