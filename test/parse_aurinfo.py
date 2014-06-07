#!/usr/bin/env python

from copy import copy, deepcopy
import pprint
import sys

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


class StderrECatcher(object):
    def Catch(self, lineno, error):
        print('ERROR[%d]: %s' % (lineno, error), file=sys.stderr)


class CollectionECatcher(object):
    def __init__(self):
        self._errors = []

    def Catch(self, lineno, error):
        self._errors.append((lineno, error))

    def HasErrors(self):
        return len(self._errors) > 0

    def Errors(self):
        return copy(self._errors)


def ParseAurinfoFromIterable(iterable, ecatcher=None):
    aurinfo = AurInfo()

    if ecatcher is None:
        ecatcher = StderrECatcher()

    current_package = None
    lineno = 0

    for line in iterable:
        lineno += 1

        if not line.strip():
            # end of package
            current_package = None
            continue

        if not line.startswith('\t'):
            # start of new package
            try:
                key, value = map(lambda s: s.strip(), line.split('=', 1))
            except ValueError:
                ecatcher.Catch(lineno, 'unexpected header format in section=%s' %
                    current_package['pkgname'])
                continue

            if key == 'pkgbase':
                current_package = aurinfo.SetPkgbase(value)
            else:
                current_package = aurinfo.AddPackage(value)
        else:
            # package attribute
            if current_package is None:
                ecatcher.Catch(lineno, 'package attribute found outside of '
                               'a package section')
                continue

            try:
                key, value = map(lambda s: s.strip(), line.split('=', 1))
            except ValueError:
                ecatcher.Catch(lineno, 'unexpected attribute format in '
                               'section=%s' % current_package['pkgname'])

            if IsMultiValued(key):
                if not current_package.get(key):
                    current_package[key] = []
                current_package[key].append(value)
            else:
                if not current_package.get(key):
                    current_package[key] = value
                else:
                    ecatcher.Catch(lineno, 'overwriting attribute '
                                   '%s: %s -> %s' % (key, current_package[key],
                                                     value))

    return aurinfo


def ParseAurinfo(filename='.AURINFO', ecatcher=None):
    with open(filename) as f:
        return ParseAurinfoFromIterable(f, ecatcher)


def ValidateAurinfo(filename='.AURINFO'):
    ecatcher = CollectionECatcher()
    ParseAurinfo(filename, ecatcher)
    errors = ecatcher.Errors()
    for error in errors:
        print('error on line %d: %s' % error, file=sys.stderr)
    return not errors


if __name__ == '__main__':
    pp = pprint.PrettyPrinter(indent=4)

    if len(sys.argv) == 1:
        print('error: not enough arguments')
        sys.exit(1)
    elif len(sys.argv) == 2:
        action = sys.argv[1]
        filename = '.AURINFO'
    else:
        action, filename = sys.argv[1:3]

    if action == 'parse':
        aurinfo = ParseAurinfo()
        for pkgname in aurinfo.GetPackageNames():
            print(">>> merged package: %s" % pkgname)
            pp.pprint(aurinfo.GetMergedPackage(pkgname))
            print()
    elif action == 'validate':
        sys.exit(not ValidateAurinfo(filename))
    else:
        print('unknown action: %s' % action)
        sys.exit(1)

# vim: set et ts=4 sw=4:
