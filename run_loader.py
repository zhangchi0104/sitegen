from sitegen.build import ProjectRenderer

renderer = ProjectRenderer("site")
templates = renderer._jinja_env.list_templates()
print(templates)