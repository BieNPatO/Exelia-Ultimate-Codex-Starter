# Rollback / repair

`./install.sh --rollback` restores only local configuration snapshots tracked in `.exelia-install/journal.json` if the file has not changed since the installer wrote it. It does not remove any existing Git commits or unrelated user work.

Project-local third-party tool packages are under ignored `.exelia-tools/`; they can be reconstructed with `./install.sh --resume`. The installer does not remove external skills as part of automatic rollback: inspect project files first.

On interrupted installation run `./install.sh --plan`, inspect `.exelia-install/logs/` and use `./install.sh --resume`. No global plugin, npm package, Homebrew package or Git config is changed by this release.
