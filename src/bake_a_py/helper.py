import sys
import hashlib
import urllib.request
import urllib.error
import os
import sys
import subprocess
import shutil
import time
import json
import jinja2
import ruamel.yaml
from tqdm.auto import tqdm
from tqdm.utils import CallbackIOWrapper
import requests
import pathlib
from zipfile import ZipFile

from . import udisks2

def eprint(*args, **kwargs):
    """Print error messages to stderr."""
    print(*args, file=sys.stderr, **kwargs)

def download(url, dest):
    
    response = requests.get(url, stream=True)
    with tqdm.wrapattr(
        open(dest, "wb"), "write",
        unit='B', unit_scale=True, unit_divisor=1024, miniters=1,
        desc="Downloading", total=int(response.headers.get('content-length', 0))
        ) as fout:
        for chunk in response.iter_content(chunk_size=4096):
            fout.write(chunk)

def sha256(fname):
    hash = hashlib.sha256()
    with tqdm.wrapattr(
        open(fname, "rb"), "read",
        unit='B', unit_scale=True, unit_divisor=1024, miniters=1,
        desc="Calculating checksum", total=pathlib.Path(fname).stat().st_size
        ) as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash.update(chunk)
    return hash.hexdigest()

def extractall(archive, dest, desc="Extracting"):
    dest = pathlib.Path(dest).expanduser()
    with ZipFile(archive) as zip_file, tqdm(
        desc=desc, unit="B", unit_scale=True, unit_divisor=1024,
        total=sum(getattr(i, "file_size", 0) for i in zip_file.infolist()),
    ) as pbar:
        for i in zip_file.infolist():
            if not getattr(i, "file_size", 0):  # directory
                zip_file.extract(i, os.fspath(dest))
            else:
                with zip_file.open(i) as fi, open(os.fspath(dest / i.filename), "wb") as fo:
                    shutil.copyfileobj(CallbackIOWrapper(pbar.update, fi), fo)


def write_customisation(device, mountpoint, firstrun_script):
    with open(mountpoint.joinpath('firstrun.sh'), 'w') as fout:
        print(firstrun_script, file=fout)
    with open(mountpoint.joinpath('cmdline.txt'), 'w') as fout:
        partuuid = udisks2.get_partuuid(device, 'rootfs')
        print(f'console=serial0,115200 console=tty1 root=PARTUUID={partuuid} rootfstype=ext4 elevator=deadline fsck.repair=yes rootwait quiet init=/usr/lib/raspi-config/init_resize.sh systemd.run=/boot/firstrun.sh systemd.run_success_action=reboot systemd.unit=kernel-command-line.target', file=fout)

def customize_rpios(conf_fname, device, encrypted=True):
    if encrypted:
        result = subprocess.run(['gpg', '-d', '-o', '-', conf_fname],
                                capture_output=True)
        if result.returncode != 0:
            raise Exception(f'can not decrypt {conf_fname}')
        config = result.stdout
    else:
        with open(conf_fname, 'r') as fin:
            config = fin.read()

    yaml=ruamel.yaml.YAML(typ='safe')
    d = yaml.load(config)

    loader = jinja2.FileSystemLoader([
        pathlib.Path('~/.bake_a_py/').expanduser(),
        '.',
        pathlib.Path(__file__).parent])
    env = jinja2.Environment(loader=loader).get_template('firstrun.sh.j2')
    firstrun_script = env.render(d)

    boot = pathlib.Path(udisks2.find_boot(device))
    if boot:
        write_customisation(device, boot, firstrun_script)
    else:
        raise Exception(f'no partition mounted as boot on {device}')
