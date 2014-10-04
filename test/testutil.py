#!/usr/bin/python

import aurinfo
import subprocess
import tempfile

def OutputOf(*argv):
    return subprocess.check_output(argv).decode().rstrip().split('\n')

def parse_pkgbuild(pkgbuild_text):
    with tempfile.NamedTemporaryFile() as pkgbuild_file:
        pkgbuild_file.write(pkgbuild_text.encode())
        pkgbuild_file.flush()

        srcinfo_text = OutputOf('./introspect', pkgbuild_file.name)
        srcinfo = aurinfo.ParseAurinfoFromIterable(srcinfo_text)

        pkgnames = srcinfo.GetPackageNames()
        pkgs = map(lambda n: srcinfo.GetMergedPackage(n), pkgnames)

        return dict(zip(pkgnames, pkgs))

