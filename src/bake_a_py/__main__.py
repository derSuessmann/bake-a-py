"""Download and write a RaspiOS image to device and pre-configure it.
"""

import argparse
import json
import os.path
import psutil
import urllib.request

from bake_a_py.helper import eprint, download, extractall, sha256
from bake_a_py.helper import sudo_write, unmount_partitions, mount_partitions
from bake_a_py.helper import customize_rpios

_IMAGINGUTILITY_URL = 'https://downloads.raspberrypi.org/os_list_imagingutility_v2.json'


class Imager:
    """Handle the Raspberry PI images."""

    def __init__(self, cache_folder, verbose, progress):
        """Download the current description of the different images for the
        Raspberry Pi for the imaging utilty. This is the same information the
        rpi-imager uses.
        """
        self.cache_folder = cache_folder
        self.verbose = verbose
        self.progress = progress

        with urllib.request.urlopen(_IMAGINGUTILITY_URL) as f:
            #text = f.read().decode('utf-8')
            self.images = self.flatten(json.load(f)['os_list'])

    def flatten(self, subtree):
        result = []
        for i in subtree:
            if 'subitems' in i:
                result.extend(self.flatten(i['subitems']))
            else:
                result.append(i)
        return result

    def get_raspios_flavors(self):
        """Find all versions/flavors of the official Raspberry Pi OS.

        :return: list with the names"""
        return [i['name'] for i in self.images
                            if 'Raspberry Pi OS' in i['name']]

    def get_all_images(self):
        """Get all images the rpi-imager supports.
        
        :return: list with all the image names."""
        return [i['name'] for i in self.images]

    def get_image_description(self, name):
        return [x for x in self.images if x['name'] == name][0]

    def get_filename(self, url):
        return url.split('/')[-1]

    def write(self, name, output, configuration=None, no_chksum=False):

        description = self.get_image_description(name)

        url = description['url']
        filename = self.get_filename(description['url'])
        extracted = os.path.splitext(filename)[0] + '.img'
        
        path_filename = os.path.join(self.cache_folder, filename)
        path_extracted = os.path.join(self.cache_folder, extracted)

        if not os.path.exists(path_extracted):
            #d = Downloader(self.verbose, self.progress)
            #d.download(url, path_filename)
            download(url, path_filename)

        if not os.path.exists(path_extracted):
            if self.verbose:
                print(f'Extracting {path_filename}')
            extractall(path_filename, self.cache_folder)

        if not no_chksum:      
            if self.verbose:
                print(f'Checking {path_extracted} checksum')
            if description['extract_sha256'] != sha256(path_extracted):
                raise Exception('Extracted file corrupted.')

        if output:
            sudo_write(path_extracted, output)
            if configuration:
                if self.verbose:
                    print(f'Writing firstrun.sh')
                customize_rpios(configuration, output)

def main():
    parser = argparse.ArgumentParser(
        description='create_image.py v0.1',
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('--verbose',
                        action='store_true',
                        help='verbose output')
    parser.add_argument('--progress',
                        action='store_true',
                        help='show progress of longer running operations')
    parser.add_argument('--no-chksum',
                        action='store_true',
                        help='do not calculate checksum')
    parser.add_argument('--list',
                        action='store_true',
                        help='list all available Raspberry Pi OS images')
    parser.add_argument('--list-all',
                        action='store_true',
                        help='list all available images')
    parser.add_argument('--image-cache',
                        default='.',
                        help="select a different folder than the default '.'")
    parser.add_argument('--os',
                        default='Raspberry Pi OS (32-bit)',
                        help="select a os than the default 'Raspberry Pi OS (32-bit)'")
    parser.add_argument('--devices',
                        action='store_true',
                        help="list all possible devices to write to")
    parser.add_argument('--output',
                        help="select the block device to write to")
    parser.add_argument('--configuration',
                        default=None,
                        help="select the (encrypted) configuration for Raspberry Pi OS")

    args = parser.parse_args()

    r = Imager(args.image_cache, args.verbose, args.progress)

    if args.list:
        print('\n'.join(r.get_raspios_flavors()))
    if args.list_all:
        print('\n'.join(r.get_all_images()))

    if not args.list and not args.list_all and not args.devices:
        r.write(args.os, args.output, args.configuration, args.no_chksum)

if __name__ == '__main__':
    main()