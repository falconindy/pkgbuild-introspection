#!/usr/bin/env python

import glob
import os
import string
import subprocess
import sys

from multiprocessing import Pool

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

def output_of(argv, envp=None):
    env = envp or os.environ
    return subprocess.check_output(argv, env=env).decode().rstrip().split('\n')

def package_from_repo(repo, pkgname):
    repo_package = {}

    pacout = output_of(['/usr/bin/pacman', '-Si', '%s/%s' % (repo, pkgname)],
            envp={'LC_ALL': 'C'})

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

    diffcount = 0
    for k, v in repo_package.items():
        if k not in package:
            diffcount += 1
            print("DIFF(%s): attribute %s in repo, not in AURINFO" % (pkgname, k))
            print('          repo   : %s' % v)
            continue

        if v == 'None' and package[k]:
            diffcount += 1
            print('DIFF(%s): attribute %s in AURINFO, not in repo' % (pkgname, k))
            print('          AURINFO: %s' % package[k])
            continue

        # The simplest case
        if v == package[k]:
            continue

        # Depends and provides might have soname architectures which won't
        # appear in the PKGBUILD.
        if k in ('depends', 'provides'):
            if strip_soarch(v) == package[k]:
                continue

        # The license field can be tricky since each name can contain space.
        # If we stringify the values, we can avoid some false positives.
        if k == 'license':
            if ' '.join(v) == ' '.join(package[k]):
                continue

        print('DIFF(%s|%s):\n  repo   : %s\n  AURINFO: %s\n' % (pkgname, k, v, package[k]))
        diffcount += 1

    return diffcount

def CompareOne(repo, pkgname):
    # parse the PKGBUILD into .AURINFO
    aurinfo = output_of(['./reflect', '%s/%s' % (repo, pkgname)])

    # i'm misunderstanding the pythonic way of doing this....
    parsed_aurinfo = parse_aurinfo.ParseAurinfoFromIterable(aurinfo)

    diffs, total_attrs = 0, 0

    for p in parsed_aurinfo.GetPackageNames():
        package = parsed_aurinfo.GetMergedPackage(p)
        diffs += compare(repo, package)
        total_attrs += len(package)

    return diffs, total_attrs


def PrintStatistics(stats):
    total_diffs = sum(s[0] for s in stats)
    total_attrs = sum(s[1] for s in stats)
    diff_pkg_count = sum(bool(s[0]) for s in stats)

    print()
    print('Total PKGBUILDs read: %d' % len(stats))
    print('Total attributes checked: %d' % total_attrs)
    print('Total differences found: %d' % total_diffs)
    print('Average attributes per PKGBUILD: %.2f' % (total_attrs / len(stats)))
    print('Accuracy across PKGBUILDs: %.3f%%' % (
        100 - (diff_pkg_count / len(stats) * 100)))

    if total_diffs:
        print('Total PKGBUILDs with differences: %d' % diff_pkg_count)
        print('Average differences per PKGBUILD: %.3f' % (
            total_diffs / total_attrs))


class Comparator(object):
    def __init__(self, repo):
        self._repo = repo
    def __call__(self, pkg):
        return CompareOne(self._repo, pkg)


class PkgbuildExists(object):
    def __init__(self, repo):
        self._repo = repo
    def __call__(self, pkg):
        return os.access("/var/abs/%s/%s/PKGBUILD" % (self._repo, pkg), os.R_OK)

def main(argv):
    subjects = []
    if '/' in argv[1]:
        repo, pkg = argv[1].split('/')
        subjects.append(pkg)
    else:
        repo = argv[1]
        subjects = output_of(['pacman', '-Slq', repo])

    pkgs = filter(PkgbuildExists(repo), subjects)
    if not pkgs:
        sys.exit(1)

    pool = Pool(20)
    diffstats = pool.map(Comparator(repo), pkgs)
    pool.close()
    pool.join()

    PrintStatistics(diffstats)


if __name__ == '__main__':
    main(sys.argv)
