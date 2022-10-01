import json
import os.path
import pathlib
import urllib.request
import time

from . import helper
from . import udisks2
from . import sudo

_IMAGINGUTILITY_URL = 'https://downloads.raspberrypi.org/os_list_imagingutility_v3.json'

def flatten(tree):
    result = []
    for i in tree:
        if 'subitems' in i:
            result.extend(flatten(i['subitems']))
        else:
            result.append(i)
    return result

def get_information():
    with urllib.request.urlopen(_IMAGINGUTILITY_URL) as f:
        #text = f.read().decode('utf-8')
        return flatten(json.load(f)['os_list'])


def get_raspios_flavors():
    """Find all versions/flavors of the official Raspberry Pi OS.

    :return: list with the names"""
    return [i['name'] for i in get_information()
                        if 'Raspberry Pi OS' in i['name']]

def get_all_images():
    """Get all images the rpi-imager supports.
    
    :return: list with all the image names."""
    return [i['name'] for i in get_information()]

def get_image_description(name):
    if name == 'lite':
        name = 'Raspberry Pi OS Lite (32-bit)'
    if name == 'desktop':
        name = 'Raspberry Pi OS (32-bit)'
    if name == 'full':
        name = 'Raspberry Pi OS Full (32-bit)'
    return [x for x in get_information() if x['name'] == name][0]

def get_filename(url):
    return pathlib.Path(url.split('/')[-1])

def write(name, cache_folder, output, configuration=None, chksum=False,
    become=False, remove=False, keep=False, encrypted=True):
    """Write a OS image to disk.

    This method downloads the OS image given by name into the cache folder.
    Afterwards it extracts the archive and writes it to disk.

    :param name: name of the OS image
    :param cache_folder: path of a folder to keep the downloaded OS image
    :param output: path of the disk (should be a the device of a SD card or USB drive)
    :param configuration: path of a provisioning configuration file
    :param chksum: check the integrity of the download
    :param become: write as super user
    :param remove: remove the extracted image after writing to disk
    :param keep: keep the downloaded compressed file
    :param encrypted: the provisioning configuration file is encrypted wit gpg
    """
    
    description = get_image_description(name)

    url = description['url']
    filename = get_filename(description['url'])
    extracted = filename.stem
    
    cache_path = pathlib.Path(cache_folder).expanduser()
    cache_path.mkdir(parents=True, exist_ok=True)

    path_filename = cache_path.joinpath(filename)
    path_extracted = cache_path.joinpath(extracted).with_suffix('.img')

    if not path_extracted.exists() and not path_filename.exists():
        helper.download(url, path_filename)

    if not path_extracted.exists():
        helper.extract_all(path_filename, cache_folder)

    if chksum:      
        if description['extract_sha256'] != helper.sha256(path_extracted):
            raise Exception('Extracted file corrupted.')

    if not keep:
        path_filename.unlink(True)

    if output:
        udisks2.unmount(output)
        sudo.write(path_extracted, output, become)

        os.sync()

        if remove:
            path_extracted.unlink(True)

        if configuration:
            provision(configuration, output, encrypted)

def provision(target, output, encrypted):
    udisks2.mount(output)

    print(f'Provisioning {target} on {output}')
    helper.customize_rpios(target, output, encrypted)
