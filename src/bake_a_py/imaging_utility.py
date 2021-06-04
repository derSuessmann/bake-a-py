import json
import os.path
import pathlib
import urllib.request
import time

from . import helper

_IMAGINGUTILITY_URL = 'https://downloads.raspberrypi.org/os_list_imagingutility_v2.json'

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

    description = get_image_description(name)

    url = description['url']
    filename = get_filename(description['url'])
    extracted = filename.stem
    
    path_filename = pathlib.Path(cache_folder).joinpath(filename)
    path_extracted = pathlib.Path(cache_folder
        ).joinpath(extracted).with_suffix('.img')

    if not path_extracted.exists():
        helper.download(url, path_filename)

    if not path_extracted.exists():
        helper.extractall(path_filename, cache_folder)

    if chksum:      
        if description['extract_sha256'] != helper.sha256(path_extracted):
            raise Exception('Extracted file corrupted.')

    if not keep:
        path_filename.unlink(True)

    if output:
        helper.unmount_partitions(output)
        if become:
            helper.sudo_write(path_extracted, output)
        else:
            helper.write(path_extracted, output)

        os.sync()

        if remove:
            path_extracted.unlink(True)

        if configuration:
            provision(configuration, output, encrypted)

def provision(target, output, encrypted):
    result = [process for process in helper.mount_partitions(output) if process.returncode != 0]
    count = 1
    while result and count < 10:
        time.sleep(1)
        result = [process for process in helper.mount_partitions(output) if process.returncode != 0]
        count += 1

    print(f'Provisioning {target} on {output}')
    helper.customize_rpios(target, output, encrypted)
