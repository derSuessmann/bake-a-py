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

def get_devices():
    """Get all block devices.

    The function calls the lsblk command.

    :return: list of names."""
    result = subprocess.run(['lsblk', '--json'], capture_output=True)
    d = json.loads(result.stdout)

    return [i['name'] for i in d['blockdevices']]

def get_partitions(device):
    """Get all partitions on the block device.

    The function calls the lsblk command.
    
    :return: list of names."""
    result = subprocess.run(['lsblk', '--json', device], capture_output=True)
    d = json.loads(result.stdout)

    return d['blockdevices'][0]['children']

def unmount(partition):
    """Unmount the partition given by name.

    The function calls the udisksctl command.
    
    :return: subprocess.Result."""
    result = subprocess.run(['udisksctl', 'unmount', '-b', f'/dev/{partition}'],
                            capture_output=True)
    return result

def unmount_partitions(device):
    """Unmount all partitions on device.

    The function calls the udisksctl command.
    
    :return: list of subprocess.Result for all partitions."""
    result = []
    for part in get_partitions(device):
        if part['type'] == 'part' and part['mountpoint']:
            result.append(unmount(part['name']))
    return result

def mount(partition):
    """Mount the partition given by name.

    The function calls the udisksctl command.
    
    :return: subprocess.Result."""
    result = subprocess.run(['udisksctl', 'mount', '-b', f'/dev/{partition}'],
                            capture_output=True)
    return result

def mount_partitions(device):
    """Mount all partitions on device.

    The function calls the udisksctl command.
    
    :return: list of subprocess.Result for all partitions."""
    result = []
    for part in get_partitions(device):
        if part['type'] == 'part' and not part['mountpoint']:
            result.append(mount(part['name']))
    return result

def customize_rpios(conf_fname, device):
    result = subprocess.run(['gpg', '-d', '-o', '-', conf_fname], capture_output=True)

    yaml=ruamel.yaml.YAML(typ='safe')
    d = yaml.load(result.stdout)

    loader = jinja2.FileSystemLoader(["/home/sue/git/quiche-lorraine/ansible/templates", "/default/templates"])
    env = jinja2.Environment(loader=loader).get_template('firstrun.sh.j2')
    firstrun_script = env.render(d)

    for part in get_partitions(device):
        mountpoint = pathlib.Path(part['mountpoint'])

        if mountpoint.parts[-1] == 'boot':
            with open(mountpoint.joinpath('firstrun.sh'), 'w') as fout:
                print(firstrun_script, file=fout)

def write(src, dest):
    with open(src, 'rb') as fin, tqdm.wrapattr(
        open(dest, 'wb'), 'write',
        unit='B', unit_scale=True, unit_divisor=1024, miniters=1,
        desc="Writing image", total=pathlib.Path(src).stat().st_size
        ) as fout:
        chunk = fin.read(4096)
        while chunk:
            fout.write(chunk)
            chunk = fin.read(4096)

def sudo_write(src, dest):
    """Acquire super user privilege with sudo and write src to a dest."""
    subprocess.run(['sudo', sys.executable, __file__, 
        pathlib.Path(src).absolute(), pathlib.Path(dest).absolute()])

if __name__ == '__main__':
    write(sys.argv[1], sys.argv[2])