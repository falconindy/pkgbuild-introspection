#!/usr/bin/python

import subprocess
import tempfile

from srcinfo import parse as srcinfo_parse
from srcinfo import utils as srcinfo_utils

def OutputOf(*argv):
    return subprocess.check_output(
            argv, stderr=subprocess.DEVNULL).decode()

def parse_pkgbuild(pkgbuild_text):
    with tempfile.NamedTemporaryFile() as pkgbuild_file:
        pkgbuild_file.write(pkgbuild_text.encode())
        pkgbuild_file.flush()

        srcinfo, _ = srcinfo_parse.parse_srcinfo(
                OutputOf('./introspect', pkgbuild_file.name))

        pkgnames = srcinfo_utils.get_package_names(srcinfo)
        pkgs = map(lambda n: srcinfo_utils.get_merged_package(n, srcinfo),
                pkgnames)

        return dict(zip(pkgnames, pkgs))

