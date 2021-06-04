"""Download and write a RaspiOS image to device and pre-configure it.
"""

import json
import os.path
import urllib.request

from . import helper

_IMAGINGUTILITY_URL = 'https://downloads.raspberrypi.org/os_list_imagingutility_v2.json'

class Imager:
    """Handle the Raspberry PI images."""

    def __init__(self, cache_folder='.', verbose=False, progress=False):
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
            helper.download(url, path_filename)

        if not os.path.exists(path_extracted):
            if self.verbose:
                print(f'Extracting {path_filename}')
            helper.extractall(path_filename, self.cache_folder)

        if not no_chksum:      
            if self.verbose:
                print(f'Checking {path_extracted} checksum')
            if description['extract_sha256'] != helper.sha256(path_extracted):
                raise Exception('Extracted file corrupted.')

        if output:
            helper.sudo_write(path_extracted, output)
            if configuration:
                if self.verbose:
                    print(f'Writing firstrun.sh')
                helper.customize_rpios(configuration, output)
