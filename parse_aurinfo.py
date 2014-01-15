#!/usr/bin/env python

from copy import deepcopy
import pprint

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
        elif not line.startswith('\t'):
            # start of new package
            key, value = line.split(' = ', 1)
            if key == 'pkgbase':
                current_package = aurinfo.SetPkgbase(value)
            else:
                current_package = aurinfo.AddPackage(value)
        else:
            # package attribute
            key, value = line.lstrip('\t').split(' = ', 1)

            # XXX: This isn't really correct, since it forces all attributes to
            # be multi-valued. A proper parser would maintain a descriptor of
            # the attributes and the allowed values.
            if not current_package.get(key):
                current_package[key] = []
            current_package[key].append(value)

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

