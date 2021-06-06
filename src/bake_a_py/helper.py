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
    result = subprocess.run(['lsblk', '--json', '-O', device],
                            capture_output=True)
    if result.returncode != 0:
        raise Exception(f'lsblk returned error ({result.returncode})')
    d = json.loads(result.stdout)

    return d['blockdevices'][0]['children']

def get_partuuid(device, mountpoint):
    for partdesc in get_partitions(device):
        try: 
            if pathlib.Path(partdesc['mountpoint']).name == mountpoint:
                return partdesc['partuuid']
        except KeyError:
            if mountpoint in [pathlib.Path(p).name
                              for p in partdesc['mountpoints']]:
                return partdesc['partuuid']
    return None

def is_partition(partdesc):
    return partdesc['type'] == 'part'

def is_mounted(partdesc):
    try: 
        return partdesc['mountpoint'] != None
    except KeyError:
        return not (None in partdesc['mountpoints'])

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
        if is_partition(part) and is_mounted(part):
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
        if is_partition(part) and not is_mounted(part):
            result.append(mount(part['name']))
    return result

def write_customisation(device, mountpoint, firstrun_script):
    with open(mountpoint.joinpath('firstrun.sh'), 'w') as fout:
        print(firstrun_script, file=fout)
    with open(mountpoint.joinpath('cmdline.txt'), 'w') as fout:
        partuuid = get_partuuid(device, 'rootfs')
        print(f'console=serial0,115200 console=tty1 root=PARTUUID={partuuid} rootfstype=ext4 elevator=deadline fsck.repair=yes rootwait quiet init=/usr/lib/raspi-config/init_resize.sh systemd.run=/boot/firstrun.sh systemd.run_success_action=reboot systemd.unit=kernel-command-line.target', file=fout)

def find_boot(device):
    for partdesc in get_partitions(device):
        if is_partition(partdesc) and is_mounted(partdesc):
            if 'mountpoint' in partdesc:
                # older interface, not tested
                path = pathlib.Path(partdesc['mountpoint'])
                if path.parts[-1] == 'boot':
                    return path
            elif 'mountpoints' in partdesc:
                for p in partdesc['mountpoints']:
                    if p:
                        path = pathlib.Path(p)
                        if path.parts[-1] == 'boot':
                            return path
    return None

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

    boot = find_boot(device)
    if boot:
        write_customisation(device, boot, firstrun_script)
    else:
        raise Exception(f'no partition mounted as boot on {device}')
