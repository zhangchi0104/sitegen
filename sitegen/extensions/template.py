from jinja2.ext import Extension
from mistune import HTMLRenderer, create_markdown
from jinja2 import Environment, nodes
from jinja2.parser import Parser

from sitegen.utils import LoggerMixin


class AutoRefreshListener(Extension, LoggerMixin):
    tags = {"autorefresh"}

    def __init__(self, environment: Environment):
        super().__init__(environment)
        LoggerMixin.__init__(self, name="sitegen:AutoRefreshListener")

    def parse(self, parser: Parser):
        lineno = next(parser.stream).lineno
        args = [parser.parse_expression()]
        print(args)
        return nodes.CallBlock(self.call_method("_render_autorefresh", args),
                               [], [], []).set_lineno(lineno)

    def _render_autorefresh(self, port, caller):
        return f"""
        <script>
            var socket = new WebSocket("ws://localhost:{port}");
            socket.onmessage = function(event) {{
                console.log(event.data);
                if (event.data == "RELOAD") {{
                    location.reload();
                }}
            }}
            socket.onopen = (() => socket.send("REIGSTER"));
        
        </script>
        """


class MarkdownRender(Extension, LoggerMixin):
    tags = {"markdown"}

    def __init__(self, environment: Environment):
        super().__init__(environment)
        LoggerMixin.__init__(self, name="sitegen:MarkdownRender")
        environment.extend(markdown_render=HTMLRenderer)

    def parse(self, parser: Parser):
        lineno = next(parser.stream).lineno

        body = parser.parse_statements(["name:endmarkdown"], drop_needle=True)

        return nodes.CallBlock(self.call_method("_render_markdown", []), [],
                               [], body).set_lineno(lineno)

    def _render_markdown(self, caller):
        renderer: HTMLRenderer = self.environment.markdown_render()
        markdown = create_markdown(renderer=renderer)

        body = caller()
        html = markdown(body.strip())
        return html
