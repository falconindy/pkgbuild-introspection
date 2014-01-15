#!/usr/bin/env python

import string
import subprocess
import sys

import parse_aurinfo

TEST_KEYS = {
    'Name': (False, 'pkgname'),
    'Description': (False, 'pkgdesc'),
    'URL': (False, 'url'),
    'Licenses': (True, 'license'),
    'Groups': (True, 'groups'),
    'Provides': (True, 'provides'),
    'Depends On': (True, 'depends'),
    'Conflicts With': (True, 'conflicts'),
    'Replaces': (True, 'replaces'),
}

def package_from_repo(repo, pkgname):
    repo_package = {}

    pacout = subprocess.check_output([
        '/usr/bin/pacman', '-Si', '%s/%s' % (repo, pkgname)], env={'LC_ALL': 'C'}
        ).decode().rstrip().split('\n')

    for line in pacout:
        # lines not starting with a capital letter are probaly stupid optdeps
        if line[0] not in string.ascii_uppercase:
            continue

        key, value = line.split(':', 1)
        key = key.strip()

        if key not in TEST_KEYS:
            continue

        values = value.strip()
        if values == 'None':
            continue

        # maybe split...
        if TEST_KEYS[key][0]:
            values = values.split()

        if  None:
            continue

        repo_package[TEST_KEYS[key][1]] = values

    return repo_package


def strip_soarch(deplist):
    sanitized = []

    for dep in deplist:
        # hacky but effective for 64 bit systems
        if '=' in dep and dep.endswith('-64'):
            sanitized.append(dep.split('=', 1)[0])
        else:
            sanitized.append(dep)

    return sanitized


def compare(repo, package):
    assert 'pkgname' in package
    pkgname = package['pkgname']

    repo_package = package_from_repo(repo, pkgname)

    for k, v in repo_package.items():
        if k not in package:
            print("DIFF(%s): attribute %s in repo, not in AURINFO" % (pkgname, k))
            print('          repo   : %s' % v)
            continue

        if v == 'None' and package[k]:
            print('DIFF(%s): attribute %s in AURINFO, not in repo' % (pkgname, k))
            print('          AURINFO: %s' % package[k])
            continue

        # in the simplest case, they're both equal
        if v == package[k]:
            continue

        # hmmm, maybe this is a single valued attribute...
        if len(package[k]) == 1 and package[k][0] == v:
            continue

        # depends and provides might have soname architectures
        if k in ('depends', 'provides'):
            if strip_soarch(v) == package[k]:
                continue

        # license field can be tricky since each name can contain space
        # this is a decent approximation, but relies on ordering.
        if k == 'license':
            if ' '.join(v) == ' '.join(package[k]):
                continue

        print('DIFF(%s):\n  repo   : %s\n  AURINFO: %s\n' % (pkgname, v, package[k]))


def main(argv):
    repo = argv[1]
    pkgname = argv[2]

    # parse the PKGBUILD into .AURINFO
    aurinfo = subprocess.check_output(['./reflect', '%s/%s' % (repo, pkgname)]).decode()

    # i'm misunderstanding the pythonic way of doing this....
    parsed_aurinfo = parse_aurinfo.ParseAurinfoFromIterable(aurinfo.split('\n'))

    for p in parsed_aurinfo.GetPackageNames():
        package = parsed_aurinfo.GetMergedPackage(p)
        compare(repo, package)


if __name__ == '__main__':
    main(sys.argv)
