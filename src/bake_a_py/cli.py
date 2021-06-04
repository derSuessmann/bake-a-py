import sys
import click

from . import imaging_utility as iu
from . import provisioning

def eprint(msg):
    click.echo(msg, file=sys.stderr)

@click.group()
def cli():
    pass

@cli.command()
@click.option('--hidden/--plain', default=True,
    help='hide or show password input')
def create(hidden):
    """create a provisioning configuration"""
    try:
        provisioning.create(hidden)
    except Exception as exc:
        eprint(f'creating provisioning configuration failed ({exc})')

@cli.command()
@click.argument('os')
@click.option('--image-cache',
    type=click.Path(exists=True, file_okay=False), 
    default='.',
    help='path where the downloaded image is stored')
@click.option('-o', '--output',
    help='device path to write the OS image to')
@click.option('--chksum/--no-chksum', '-c/ ', default=False,
    help='check the checksum of the OS image before writing')
@click.option('--target', '-t', 
    help='name of the configuration file')
@click.option('--become', '-b', is_flag=True, 
    help='run the writing of the image as super user')
@click.option('--remove', '-r', default=False,
    help='Remove the image file after writing')
@click.option('--keep', '-k', is_flag=True,
    help='keep the downloaded archive')
@click.option('--encrypted/--decrypted', ' /-d', default=True,
    help='force usage of encrypted or decrypted provisioning configuration')
def write(os, image_cache, output, chksum, target, become, remove, keep,
          encrypted):
    """write the OS image
    
    OS image name (one of the results of the list command)
    """
    try:
        iu.write(os, image_cache, output, target, chksum, become, remove, keep,
                 encrypted)
    except Exception as exc:
        eprint(f'writing failed ({exc})')

@cli.command()
@click.argument('target')
@click.option('-o', '--output',
    help='device path to write the OS image to')
@click.option('--encrypted/--decrypted', ' /-d', default=True,
    help='force usage of encrypted or decrypted provisioning configuration')
def provision(target, output, encrypted):
    """provision the os on OUTPUT for TARGET
    
    TARGET name of the configuration file
    """
    try:
        iu.provision(target, output, encrypted)
    except Exception as exc:
        eprint(f'provisioning failed ({exc})')

@cli.command()
@click.argument('device')
def mount(device):
    """mount all partitions on DEVICE"""
    try:
        iu.helper.mount_partitions(device)
    except Exception as exc:
        eprint(f'mounting {device} failed ({exc})')

@cli.command()
@click.argument('device')
def unmount(device):
    """unmount all partitions on DEVICE"""
    try:
        iu.helper.unmount_partitions(device)
    except Exception as exc:
        eprint(f'unmounting {device} failed ({exc})')

@cli.command()
@click.option('-a', '--all', is_flag=True, 
    help='all available image / not only Raspberry Pi OS images')
def list(all):
    """list available OS images"""
    try:
        if all:
            result = iu.get_all_images()
        else:
            result = iu.get_raspios_flavors()
        click.echo('\n'.join(result))
    except Exception as exc:
        eprint(f'listing OS images failed ({exc})')

@cli.command()
@click.option('--verbose', '-v', is_flag=True)
@click.argument('name')
def describe(name, verbose):
    """display the description of the OS image NAME
    
    NAME of the OS to describe
    """
    try:
        desc = iu.get_image_description(name)
        if verbose:
            click.echo(desc)
        else:
            click.echo(desc['description'])
    except Exception as exc:
        eprint(f'displaying description of {name} failed ({exc})')

if __name__ == '__main__':
    cli()