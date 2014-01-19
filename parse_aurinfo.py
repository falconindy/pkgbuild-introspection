#!/usr/bin/env python

from copy import deepcopy
import pprint

MULTIVALUED_ATTRS = set([
    'arch',
    'groups',
    'makedepends',
    'checkdepends',
    'optdepends',
    'depends',
    'provides',
    'conflicts',
    'replaces',
    'options',
    'license',
    'source',
    'noextract',
    'backup',
])

def IsMultiValued(attr):
    return attr in MULTIVALUED_ATTRS


class AurInfo(object):
    def __init__(self):
        self._pkgbase = {}
        self._packages = {}

    def GetPackageNames(self):
        return self._packages.keys()

    def GetMergedPackage(self, pkgname):
        package = deepcopy(self._pkgbase)
        package['pkgname'] = pkgname
        for k, v in self._packages.get(pkgname).items():
            package[k] = deepcopy(v)
        return package

    def AddPackage(self, pkgname):
        self._packages[pkgname] = {}
        return self._packages[pkgname]

    def SetPkgbase(self, pkgbasename):
        self._pkgbase = {'pkgname' : pkgbasename}
        return self._pkgbase

def ParseAurinfoFromIterable(iterable):
    aurinfo = AurInfo()

    current_package = None

    for line in iterable:
        line = line.rstrip()

        if not line:
            # end of package
            current_package = None
            continue

        if not line.startswith('\t'):
            # start of new package
            try:
                key, value = line.split(' = ', 1)
            except ValueError:
                print('ERROR: unexpected header format: section=%s, line=%s' % (
                    current_package['pkgname'], line))
                continue

            if key == 'pkgbase':
                current_package = aurinfo.SetPkgbase(value)
            else:
                current_package = aurinfo.AddPackage(value)
        else:
            if current_package is None:
                print('ERROR: package attribute found outside of a package section')
                continue

            # package attribute
            try:
                key, value = line.lstrip('\t').split(' = ', 1)
            except ValueError:
                print('ERROR: unexpected attribute format: section=%s, line=%s' % (
                    current_package['pkgname'], line))

            if IsMultiValued(key):
                if not current_package.get(key):
                    current_package[key] = []
                current_package[key].append(value)
            else:
                if not current_package.get(key):
                    current_package[key] = value
                else:
                    print('WARNING: overwriting attribute %s: %s -> %s' % (
                        key, current_package[key], value))

    return aurinfo


def ParseAurinfo(filename='.AURINFO'):
    with open(filename) as f:
        return ParseAurinfoFromIterable(f)


if __name__ == '__main__':
    pp = pprint.PrettyPrinter(indent=4)
    aurinfo = ParseAurinfo()
    for pkgname in aurinfo.GetPackageNames():
        print(">>> merged package: %s" % pkgname)
        pp.pprint(aurinfo.GetMergedPackage(pkgname))
        print()

