#!/usr/bin/env python

import collections
import os
import subprocess
import sys
import tarfile

from multiprocessing import Pool

import parse_aurinfo

SECTION_TO_ATTR_MAP = {
    '%NAME%': ('pkgname', False),
    '%VERSION%': ('pkgver', False),
    '%DESC%': ('pkgdesc', False),
    '%LICENSE%': ('license', True),
    '%URL%': ('url', False),
    '%GROUPS%': ('groups', True),
    '%MAKEDEPENDS%': ('makedepends', True),
    '%CHECKDEPENDS%': ('checkdepends', True),
    '%DEPENDS%': ('depends', True),
    '%OPTDEPENDS%': ('optdepends', True),
    '%PROVIDES%': ('provides', True),
    '%CONFLICTS%': ('conflicts', True),
    '%REPLACES%': ('replaces', True),
}


class DiffCounter(object):
    def __init__(self):
        self._diffcount = 0

    def Count(self):
        return self._diffcount

    def Report(self, pkgname, attrname, repovalue, parsedvalue):
        print('DIFF(%s|%s):\n  repo   : %s\n  AURINFO: %s\n' % (
            pkgname, attrname, repovalue, parsedvalue))
        self.Increment()

    def Increment(self):
        self._diffcount += 1


def SectionToPkgattr(section):
    return SECTION_TO_ATTR_MAP.get(section)


def IsSection(line):
    return len(line) > 2 and line[0] == '%' and line[-1] == '%'


def DbentryToDict(dbentry):
    section = None
    attrs = collections.defaultdict(list)

    for line in dbentry:
        line = line.decode().strip()
        if not line:
            section = None
            continue

        if IsSection(line):
            section = SectionToPkgattr(line)
            continue

        if not section:
            # this might be an error, but it's far more likely that it's
            # just a section we don't care about.
            continue

        if section[1]:
            # multi-valued
            attrs[section[0]].append(line)
        else:
            # single-valued
            attrs[section[0]] = line

    return attrs


def AlpmDbToDict(reponame):
    path = '/var/lib/pacman/sync/%s.db' % reponame

    packages = collections.defaultdict(dict)

    with tarfile.open(path, 'r') as repotar:
        for tarinfo in repotar:
            if '/' not in tarinfo.name:
                continue

            pkgname, _, _ = tarinfo.name.rsplit('-', 2)

            entries = DbentryToDict(repotar.extractfile(tarinfo))
            packages[pkgname].update(entries)

    return packages


def output_of(argv, envp=None):
    return subprocess.check_output(argv).decode().rstrip().split('\n')


def strip_soarch(deplist):
    sanitized = []

    for dep in deplist:
        # hacky but effective for 64 bit systems
        if '=' in dep and dep.endswith('-64'):
            sanitized.append(dep.split('=', 1)[0])
        else:
            sanitized.append(dep)

    return sanitized


def ReportDiff(pkgname, attrname, repovalue, parsedvalue):
    print('DIFF(%s|%s):\n  repo   : %s\n  AURINFO: %s\n' % (
        pkgname, attrname, repovalue, parsedvalue))


def compare(repo_package, package):
    assert 'pkgname' in package
    pkgname = package['pkgname']

    diffcount = DiffCounter()
    for k, v in repo_package.items():
        if k not in package:
            diffcount.Increment()
            print("DIFF(%s): attribute %s in repo, not in AURINFO" % (pkgname, k))
            print('          repo   : %s' % v)
            continue

        if v == 'None' and package[k]:
            diffcount.Increment()
            print('DIFF(%s): attribute %s in AURINFO, not in repo' % (pkgname, k))
            print('          AURINFO: %s' % package[k])
            continue

        # The simplest case
        if v == package[k]:
            continue

        # Reconstruct the epoch:pkgver-pkgrel to compare against the DB value
        if k == 'pkgver':
            epoch = package.get('epoch')
            if epoch:
                fullver = '%s:%s-%s' % (epoch, package['pkgver'], package['pkgrel'])
            else:
                fullver = '%s-%s' % (package['pkgver'], package['pkgrel'])
            if v != fullver:
                diffcount.Report(pkgname, k, v, fullver)
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

        diffcount.Report(pkgname, k, v, package[k])

    return diffcount.Count()

def CompareOne(reponame, alpmdb, pkgname):
    # parse the PKGBUILD into .AURINFO
    aurinfo = output_of(['./introspect', '%s/%s' % (reponame, pkgname)])

    # i'm misunderstanding the pythonic way of doing this....
    parsed_aurinfo = parse_aurinfo.ParseAurinfoFromIterable(aurinfo)

    diffs, total_attrs = 0, 0

    for p in parsed_aurinfo.GetPackageNames():
        package = parsed_aurinfo.GetMergedPackage(p)
        diffs += compare(alpmdb.get(p), package)
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
    def __init__(self, reponame, alpmdb):
        self._alpmdb = alpmdb
        self._reponame = reponame
    def __call__(self, pkgname):
        return CompareOne(self._reponame, self._alpmdb, pkgname)


class PkgbuildExists(object):
    def __init__(self, repo):
        self._repo = repo
    def __call__(self, pkg):
        return os.access("/var/abs/%s/%s/PKGBUILD" % (self._repo, pkg), os.R_OK)

def main(argv):
    subjects = []
    reponame = argv[1]

    alpmdb = AlpmDbToDict(reponame)
    subjects = alpmdb.keys()

    pkgs = filter(PkgbuildExists(reponame), subjects)
    if not pkgs:
        sys.exit(1)

    pool = Pool(20)
    diffstats = pool.map(Comparator(reponame, alpmdb), pkgs)
    pool.close()
    pool.join()

    PrintStatistics(diffstats)


if __name__ == '__main__':
    main(sys.argv)
