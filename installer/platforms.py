"""Platform discovery (no writes)."""
from __future__ import annotations
import os, platform, shutil, subprocess, sys
from pathlib import Path


def _which(binary: str) -> str | None:
    return shutil.which(binary)


def detect() -> dict:
    name = platform.system().lower()
    arch = platform.machine().lower()
    wsl = False
    if name == 'linux':
        for p in (Path('/proc/sys/kernel/osrelease'), Path('/proc/version')):
            try:
                if 'microsoft' in p.read_text().lower():
                    wsl = True
                    break
            except OSError:
                pass
    distro = 'unknown'
    if name == 'linux':
        try:
            for line in Path('/etc/os-release').read_text().splitlines():
                if line.startswith('ID='):
                    distro = line.partition('=')[2].strip('"')
                    break
        except OSError:
            pass
    pkg_manager = next((x for x in (('brew',) if name == 'darwin' else ('apt-get','dnf','yum','pacman')) if _which(x)), None)
    docker_context = None
    if _which('docker'):
        try:
            r = subprocess.run(['docker', 'context', 'show'], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                docker_context = r.stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            pass
    orbstack = name == 'darwin' and (bool(_which('orb')) or Path('/Applications/OrbStack.app').exists())
    try:
        disk_free_gb=round(shutil.disk_usage(Path.cwd()).free/(1024**3),1)
    except OSError:
        disk_free_gb=None
    ram_gb=None
    if name=='darwin':
        try:
            m=subprocess.run(['sysctl','-n','hw.memsize'],capture_output=True,text=True,timeout=4)
            if m.returncode==0:ram_gb=round(int(m.stdout.strip())/(1024**3),1)
        except (OSError,ValueError,subprocess.TimeoutExpired):pass
    elif name=='linux':
        try:
            for line in Path('/proc/meminfo').read_text().splitlines():
                if line.startswith('MemTotal:'):
                    ram_gb=round(int(line.split()[1])*1024/(1024**3),1)
                    break
        except (OSError,ValueError):pass
    return {
        'disk_free_gb':disk_free_gb, 'ram_gb':ram_gb,
        'os': name, 'architecture': arch, 'distro': distro, 'wsl': wsl,
        'package_manager': pkg_manager, 'shell': os.environ.get('SHELL', ''),
        'python': sys.version.split()[0], 'orbstack_installed': bool(orbstack),
        'docker_context': docker_context,
        'supported': name in ('darwin','linux'),
        'notes': ('Run from WSL2 Linux, not PowerShell.' if name == 'windows' else
                  'OrbStack is macOS-only.' if name == 'darwin' else
                  'WSL2 Docker integration must be configured.' if wsl else
                  'Docker Engine is used instead of OrbStack.'),
    }
