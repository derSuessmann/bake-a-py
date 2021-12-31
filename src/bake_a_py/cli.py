import sys
import traceback
import click

from . import imaging_utility as iu
from . import provisioning
from . import __version__

def eprint(msg, show):
    if show:
        traceback.print_exc()
        print(file=sys.stderr)
    click.echo(msg, file=sys.stderr)


@click.group()
@click.version_option(__version__)
@click.option('--traceback', is_flag=True,
    help='Show the full python exception if an error occurs.')
@click.pass_context
def cli(ctx, traceback):
    ctx.ensure_object(dict)

    ctx.obj['TRACEBACK'] = traceback

@cli.command()
@click.option('--hidden/--plain', default=True,
    help='Hide or show password input.')
@click.pass_context
def create(ctx, hidden):
    """Create a provisioning configuration."""
    try:
        provisioning.create(hidden)
    except Exception as exc:
        eprint(f'Creating provisioning configuration failed ({exc}).',
               ctx.obj['TRACEBACK'])

@cli.command()
@click.argument('os')
@click.option('--image-cache',
    type=click.Path(file_okay=False), 
    default='~/.cache/bake-a-py',
    help='Path where the downloaded image is stored.')
@click.option('-o', '--output',
    help='Device path to write the OS image to.')
@click.option('--chksum/--no-chksum', '-c/ ', default=False,
    help='Check the checksum of the OS image before writing.')
@click.option('--target', '-t', 
    help='Name of the configuration file.')
@click.option('--become', '-b', is_flag=True, 
    help='Run the writing of the image as super user.')
@click.option('--remove', '-r', is_flag=True,
    help='Remove the image file after writing.')
@click.option('--keep', '-k', is_flag=True,
    help='Keep the downloaded archive.')
@click.option('--encrypted/--decrypted', ' /-d', default=True,
    help='Force usage of encrypted or decrypted provisioning configuration.')
@click.pass_context
def write(ctx, os, image_cache, output, chksum, target, become, remove, keep,
          encrypted):
    """Write the image.
    
    OS is the image name (one of the results of the list command).

    This command download, extracts, checks integrity, writes and provisions
    if neccessary.
    """
    try:
        iu.write(os, image_cache, output, target, chksum, become, remove, keep,
                 encrypted)
    except Exception as exc:
        eprint(f'Writing failed ({exc}).',
               ctx.obj['TRACEBACK'])

@cli.command()
@click.argument('target')
@click.option('-o', '--output',
    help='Device path to write the OS image to.')
@click.option('--encrypted/--decrypted', ' /-d', default=True,
    help='Force usage of encrypted or decrypted provisioning configuration.')
@click.pass_context
def provision(ctx, target, output, encrypted):
    """Provision the os on OUTPUT for TARGET.
    
    TARGET is the name of the configuration file.
    """
    try:
        iu.provision(target, output, encrypted)
    except Exception as exc:
        eprint(f'Provisioning failed ({exc}).',
               ctx.obj['TRACEBACK'])

@cli.command()
@click.argument('device')
@click.pass_context
def mount(ctx, device):
    """Mount all partitions on DEVICE."""
    try:
        iu.udisks2.mount(device)
    except Exception as exc:
        eprint(f'Mounting {device} failed ({exc}).',
               ctx.obj['TRACEBACK'])

@cli.command()
@click.argument('device')
@click.pass_context
def unmount(ctx, device):
    """Unmount all partitions on DEVICE."""
    try:
        iu.udisks2.unmount(device)
    except Exception as exc:
        eprint(f'Unmounting {device} failed ({exc}).',
               ctx.obj['TRACEBACK'])

@cli.command()
@click.option('-a', '--all', is_flag=True, 
    help='All available images (not only Raspberry Pi OS images).')
@click.pass_context
def list(ctx, all):
    """List available OS images."""
    try:
        if all:
            result = iu.get_all_images()
        else:
            result = iu.get_raspios_flavors()
        click.echo('\n'.join(result))
    except Exception as exc:
        eprint(f'Listing OS images failed ({exc}).',
               ctx.obj['TRACEBACK'])

@cli.command()
@click.option('--verbose', '-v', is_flag=True,
    help='Show the complete description of the os image.')
@click.argument('name')
@click.pass_context
def describe(ctx, name, verbose):
    """Display the description of the OS image NAME.
    """
    try:
        desc = iu.get_image_description(name)
        if verbose:
            click.echo(desc)
        else:
            click.echo(desc['description'])
    except Exception as exc:
        eprint(f'Displaying description of {name} failed ({exc}).',
               ctx.obj['TRACEBACK'])

if __name__ == '__main__':
    cli(obj={})