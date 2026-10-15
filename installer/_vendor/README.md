# Bundled installer renderer

These pure-Python packages are vendored inside the **repository** so `./install.sh --plan`
can render a full Rich UI on the very first invocation, without network access or any
global packages. No global configuration is modified.

| Package | Version | License |
| --- | --- | --- |
| rich | 15.0.0 | MIT |
| markdown-it-py | 4.2.0 | MIT |
| mdurl | 0.1.2 | MIT |
| Pygments | 2.20.0 | BSD-2-Clause |

See `licenses/` for the upstream license texts. Do not use this folder as an application
dependency. These files exist only to render the Exelia installer interface.
