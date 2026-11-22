#!/usr/bin/env python3
"""Add Nokia SR Linux support to an installed SuzieQ.

SuzieQ has no SR Linux support. This script runs while the image is built and:
  * teaches the poller to detect SR Linux and adds a node class for it,
  * adds the "srlinux" command and parser definitions for the device, interfaces, bgp and
    routes services,
  * installs the cleaners that turn SR Linux's data into SuzieQ's tables.

Every change must match exactly once, so the build fails instead of silently producing a
half-patched SuzieQ if the installed version differs from the one this was written for (0.25.0).
"""
import importlib.util
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
PACKAGE = pathlib.Path(importlib.util.find_spec('suzieq').submodule_search_locations[0])
SERVICES = PACKAGE / 'poller' / 'worker' / 'services'
NODE = PACKAGE / 'poller' / 'worker' / 'nodes' / 'node.py'

# service -> (service class, cleaner function in cleaners.py)
CLEANERS = {
    'device': ('DeviceService', 'clean_device'),
    'interfaces': ('InterfaceService', 'clean_interfaces'),
    'bgp': ('BgpService', 'clean_bgp'),
    'routes': ('RoutesService', 'clean_routes'),
}


def replace_once(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        sys.exit(f'{path}: expected exactly one match for {old!r}, found {text.count(old)}')
    path.write_text(text.replace(old, new))


def patch_poller():
    replace_once(PACKAGE / 'shared' / 'utils.py',
                 "'linux', 'nxos', 'sonic', 'panos'])",
                 "'linux', 'nxos', 'sonic', 'panos', 'srlinux'])")
    replace_once(NODE,
                 '            elif "SONiC" in data:\n',
                 '            elif "SR Linux" in data:\n'
                 '                devtype = "srlinux"\n'
                 '            elif "SONiC" in data:\n')
    replace_once(NODE,
                 '            elif self.devtype == "linux":\n'
                 '                self.__class__ = LinuxNode\n',
                 '            elif self.devtype == "linux":\n'
                 '                self.__class__ = LinuxNode\n'
                 '            elif self.devtype == "srlinux":\n'
                 '                self.__class__ = SrlinuxNode\n')
    with NODE.open('a') as node_file:
        node_file.write((HERE / 'node.py').read_text())


def patch_services():
    shutil.copy(HERE / 'cleaners.py', SERVICES / 'srlinux_cleaners.py')
    for service, (service_class, cleaner) in CLEANERS.items():
        # The service definitions are keyed by device type under "apply:"
        replace_once(PACKAGE / 'config' / f'{service}.yml',
                     '\napply:\n',
                     '\napply:\n' + (HERE / 'services' / f'{service}.yml').read_text())
        with (SERVICES / f'{service}.py').open('a') as module:
            module.write(
                '\n\nfrom suzieq.poller.worker.services import srlinux_cleaners  # noqa: E402\n\n'
                f'{service_class}._clean_srlinux_data = srlinux_cleaners.{cleaner}\n')


if __name__ == '__main__':
    patch_poller()
    patch_services()
    print('SuzieQ patched for SR Linux')
