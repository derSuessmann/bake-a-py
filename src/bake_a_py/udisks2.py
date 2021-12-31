"""Accessing UDisk2 with D-Bus."""

import time
import dbus

system_bus = dbus.SystemBus()

def resolve_devices(path):
    """Get the udisk2 devices for the path.
    
    """ 
    obj = system_bus.get_object('org.freedesktop.UDisks2', '/org/freedesktop/UDisks2/Manager')
    result = obj.ResolveDevice(dict(path=path), [], dbus_interface="org.freedesktop.UDisks2.Manager")
    return result

def _unmount(device):
    obj = system_bus.get_object('org.freedesktop.UDisks2', device)
    try:
        obj.Unmount([], dbus_interface="org.freedesktop.UDisks2.Filesystem")
    except dbus.exceptions.DBusException as exc:
        if exc.get_dbus_name() != 'org.freedesktop.UDisks2.Error.NotMounted':
            raise exc

def unmount(path):
    """Unmount the device given by path.

    :return: ."""
    device = resolve_devices(path)[0]

    partitions = _get_partitions(device)
    if partitions:
        for part in partitions:
            _unmount(part)
    else:
        _unmount(device)

def _mount(device):
    
    # This method contains an annoying work-around:
    # The method sleep up to ten times a second waiting for the device to
    # get mountable. On my machine one second is sufficient. If not an
    # irritating message (I presume form the D-Bus system) is displayed
    # even though the exception has been caught.

    counter = 10 # wait maximal seconds
    while counter:
        time.sleep(1)
        counter -= 1
        try:
            obj = system_bus.get_object('org.freedesktop.UDisks2', device)
            iface = dbus.Interface(obj, 'org.freedesktop.UDisks2.Filesystem')
            obj.Mount(dict(), dbus_interface="org.freedesktop.UDisks2.Filesystem")
        except dbus.exceptions.DBusException as exc:
            if exc.get_dbus_name() != 'org.freedesktop.UDisks2.Error.AlreadyMounted':
                raise exc
            counter = 0
        except ValueError:
            # Linux needs some time after writing the image to get the system ready 
            # for mounting. D-Bus reacts with a ValueError. We wait a second and try again.
            pass

def mount(path):
    """Mount the device given by path.
    
    :return: mounted path."""
    device = resolve_devices(path)[0]

    partitions = _get_partitions(device)
    if partitions:
        for part in partitions:
            _mount(part)
    else:
        _mount(device)

def _get_uuid(device):
    obj = system_bus.get_object('org.freedesktop.UDisks2', device)
    iface = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
    result = iface.Get('org.freedesktop.UDisks2.Block', 'IdUUID')

    return result

def get_partuuid(path, label):
    device = resolve_devices(path)[0]

    for dev in _get_partitions(device):
        if _get_label(dev) == label:
            return _get_uuid(dev)

    return None

def _get_partitions(device):
    obj = system_bus.get_object('org.freedesktop.UDisks2', device)
    iface = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
    result = iface.Get('org.freedesktop.UDisks2.PartitionTable', 'Partitions')

    return result

def _get_label(device):
    obj = system_bus.get_object('org.freedesktop.UDisks2', device)
    iface = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
    result = iface.Get('org.freedesktop.UDisks2.Block', 'IdLabel')

    return result

def _get_mountpoint(device):
    obj = system_bus.get_object('org.freedesktop.UDisks2', device)
    iface = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
    result = iface.Get('org.freedesktop.UDisks2.Filesystem', 'MountPoints', byte_arrays=True)

    return result[0][:-1].decode('UTF-8')

def find_boot(path):
    device = resolve_devices(path)[0]

    for dev in _get_partitions(device):
        if _get_label(dev) == 'boot':
            return _get_mountpoint(dev)

    return None
