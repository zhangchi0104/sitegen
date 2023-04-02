from sitegen import ConfigOverrider
from mistune import HTMLRenderer, escape_html
import rich


class MarkdownRender(HTMLRenderer):

    def paragraph(self, text):
        return f"<p>{text}</p>&nbsp;"

    def link(self, link, text=None, title=None):
        if text is None:
            text = link

        s = f'<a href="{self._safe_url(link)}" class="text-fuchsia-600 hover:text-fuchsia-800"'
        if title:
            s += ' title="' + escape_html(title) + '"'
        return s + '>' + (text or link) + '</a>'


def sitegen_overrides(cfg: ConfigOverrider):
    cfg.set_markdown_render(MarkdownRender)
    return cfg