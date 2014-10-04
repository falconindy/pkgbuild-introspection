This is a proof of concept used to extract metadata from PKGBUILDs.

  - pkgbuild_introspection: the actual work is done here
  - introspect: a test driver for `pkgbuild_introspection`
  - mkaurball: creates a source tarball (ala `makepkg --source`) with a
    generated `.AURINFO` file
  - aurinfo.py: an implementation of an `.AURINFO` parser
  - smoketest: compares `AURINFO` to repo data
  - regtest: a regression tester tool

End users should only really be interested in `mkaurball`. The remainder of these
tools are intended for development and debugging purposes.
