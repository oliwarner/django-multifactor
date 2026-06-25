"""Sphinx configuration for django-multifactor documentation."""

from datetime import date

project = "django-multifactor"
author = "Oli Warner, Steve Mapes"
copyright = f"{date.today().year}, {author}"

# The full version is intentionally not pinned here — Read the Docs builds
# the docs from a checkout of the repository and the package is released via
# poetry-dynamic-versioning, so there is no static version string to import.
release = ""
version = ""

extensions = [
    "myst_parser",
    "sphinxcontrib.mermaid",
    "sphinx_copybutton",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosectionlabel",
]

# MyST extensions — keep this list in sync with the markdown we author.
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "tasklist",
    "linkify",
    "substitution",
    "attrs_inline",
]

# Markdown is our primary source format; .rst is still allowed but unused.
source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}

master_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
templates_path = ["_templates"]

# autosectionlabel: prefix labels with the document name so duplicate
# headings (e.g. multiple "Overview" sections) do not collide.
autosectionlabel_prefix_document = True
autosectionlabel_maxdepth = 3

# Generate anchor slugs for h1..h3 in MyST docs so cross-document hash
# links like [text](other.md#some-heading) resolve.
myst_heading_anchors = 3

# Theme — Furo is the modern default for Python projects.
html_theme = "furo"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_title = "django-multifactor documentation"
html_short_title = "django-multifactor"
html_logo = None  # set to "_static/logo.png" once a doc-friendly logo is added.

html_theme_options = {
    "source_repository": "https://github.com/oliwarner/django-multifactor/",
    "source_branch": "main",
    "source_directory": "docs/",
    "sidebar_hide_name": False,
    "navigation_with_keys": True,
}

# Intersphinx — link Django and Python docs by reference.
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "django": (
        "https://docs.djangoproject.com/en/stable/",
        "https://docs.djangoproject.com/en/stable/_objects/",
    ),
}

# Mermaid — pin a version so output is reproducible across RTD rebuilds.
mermaid_version = "10.9.1"
mermaid_output_format = "raw"

# Copy-button — exclude common prompts so users can paste examples cleanly.
copybutton_prompt_text = r">>> |\.\.\. |\$ |# "
copybutton_prompt_is_regexp = True
