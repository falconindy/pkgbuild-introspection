#!/usr/bin/python

import unittest
import testutil

class TestPkgbuildToAurinfo(unittest.TestCase):
    def assertPackageNamesEqual(self, srcinfo, package_names):
        return self.assertListEqual(sorted(srcinfo.keys()), sorted(package_names))

    def test_SinglePackage(self):
        pb = testutil.parse_pkgbuild('pkgname=ponies')
        self.assertPackageNamesEqual(pb, ['ponies'])

        pb = testutil.parse_pkgbuild('''
            pkgbase=ponies
            pkgname=('applejack')
        ''')
        self.assertPackageNamesEqual(pb, ['applejack'])

    def test_SplitPackageNames(self):
        pb = testutil.parse_pkgbuild('''
            pkgbase=ponies
            pkgname=('applejack' 'rainbowdash' 'pinkiepie')
        ''')
        self.assertPackageNamesEqual(pb, ['applejack', 'rainbowdash', 'pinkiepie'])

    def test_RepeatGlobalDecls(self):
        pb = testutil.parse_pkgbuild('''
            pkgbase=ponies
            pkgname=('applejack')
            pkgname=('pinkiepie')
            pkgname=('applejack')
            pkgname+=('pinkiepie')
            pkgname=('applejack')
            pkgname+=('pinkiepie')
        ''')
        self.assertPackageNamesEqual(pb, ['applejack', 'pinkiepie'])

    def test_PackageAttributeOverrides(self):
        pb = testutil.parse_pkgbuild('''
            pkgbase=ponies
            pkgname=('applejack' 'pinkiepie')
            depends=('foo')
            package_applejack() {
              depends=('bar')
            }
        ''')
        self.assertPackageNamesEqual(pb, ['applejack', 'pinkiepie'])
        self.assertEqual(['bar'], pb['applejack']['depends'])
        self.assertEqual(['foo'], pb['pinkiepie']['depends'])

    def test_PackageAttributeAppends(self):
        pb = testutil.parse_pkgbuild('''
            pkgbase=ponies
            pkgname=('applejack' 'pinkiepie')
            depends=('foo')
            package_applejack() {
              depends+=('bar')
            }
        ''')
        self.assertPackageNamesEqual(pb, ['applejack', 'pinkiepie'])
        self.assertEqual(['foo', 'bar'], pb['applejack']['depends'])
        self.assertEqual(['foo'], pb['pinkiepie']['depends'])

    def test_NestedBashVariables(self):
        pb = testutil.parse_pkgbuild('''
            pkgname=ponies-git
            provides=("${pkgname%-git}")
        ''')
        self.assertPackageNamesEqual(pb, ['ponies-git'])
        self.assertEqual(['ponies'], pb['ponies-git']['provides'])

    @unittest.expectedFailure
    def test_MultipleAttributesOnOneLine(self):
        pb = testutil.parse_pkgbuild('''
            pkgname=ponies
            package() {
              depends=('foo') provides=('bar')
            }
        ''')
        self.assertEqual(['foo'], pb['ponies']['depends'])
        self.assertEqual(['bar'], pb['ponies']['provides'])

    def test_PackagesCannotOverridePkgver(self):
        pb = testutil.parse_pkgbuild('''
            pkgname=ponies
            pkgver=1
            package() {
              pkgver=2
            }
        ''')
        self.assertPackageNamesEqual(pb, ['ponies'])
        self.assertEqual("1", pb['ponies']['pkgver'])


if __name__ == '__main__':
    unittest.main()
