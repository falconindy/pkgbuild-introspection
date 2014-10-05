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

    def test_GlobalVariableInPackage(self):
        pb = testutil.parse_pkgbuild('''
            pkgname=ponies-git
            package_ponies-git() {
              provides=("${pkgname%-git}")
            }
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

    def test_PackagesCannotOverrideMakedepends(self):
        pb = testutil.parse_pkgbuild('''
            pkgname=ponies
            pkgver=1
            makedepends=(friendship magic)
            package() {
              makedepends=(ignore me)
            }
        ''')
        self.assertPackageNamesEqual(pb, ['ponies'])
        self.assertEqual(['friendship', 'magic'], pb['ponies']['makedepends'])

    def test_MultiLineArrays(self):
        pb = testutil.parse_pkgbuild('''
            pkgname=ponies
            depends=(foo
                     bar
                     baz)
        ''')
        self.assertPackageNamesEqual(pb, ['ponies'])
        self.assertEqual(['foo', 'bar', 'baz'], pb['ponies']['depends'])

    def test_QuotedValues(self):
        pb = testutil.parse_pkgbuild('''
            pkgname=ponies
            optdepends=("foo: for bar'ing baz")

            package_ponies() {
              license=('custom: PGL'
                       'custom: EGL')
            }
        ''')
        self.assertPackageNamesEqual(pb, ['ponies'])
        self.assertEqual(['foo: for bar\'ing baz'], pb['ponies']['optdepends'])
        self.assertEqual(['custom: PGL', 'custom: EGL'], pb['ponies']['license'])

    def test_BraceExpansions(self):
        pb = testutil.parse_pkgbuild('''
            pkgname=ponies
            depends=({magic,friendship})

            package_ponies() {
              provides=({applejack,pinkiepie}-pony)
            }
        ''')
        self.assertPackageNamesEqual(pb, ['ponies'])
        self.assertEqual(['magic', 'friendship'], pb['ponies']['depends'])
        self.assertEqual(['applejack-pony', 'pinkiepie-pony'], pb['ponies']['provides'])

    @unittest.expectedFailure
    def test_NonAttrVariableInPackageAttr(self):
        pb = testutil.parse_pkgbuild('''
            pkgname=ponies

            package() {
              foo=bar
              depends=("$foo")
            }
        ''')
        self.assertPackageNamesEqual(pb, ['ponies'])
        self.assertEqual(['bar'], pb['ponies']['depends'])

    def test_ArchSpecificMultivalued(self):
        pb1 = testutil.parse_pkgbuild('''
            pkgname=ponies
            arch=('x86_64')
            depends_x86_64=('friendship' 'magic')
        ''')
        self.assertPackageNamesEqual(pb1, ['ponies'])
        self.assertEqual(['friendship', 'magic'], pb1['ponies']['depends_x86_64'])

        pb2 = testutil.parse_pkgbuild('''
            pkgname=ponies
            arch=('x86_64')
            package() {
              depends_x86_64=('friendship' 'magic')
            }
        ''')
        self.assertDictEqual(pb1, pb2)

    def test_IgnoresArchSpecificForUnsupportedArches(self):
        pb = testutil.parse_pkgbuild('''
            pkgname=ponies
            arch=('x86_64')
            depends=('friendship' 'magic')
            depends_armv7h=('pain' 'suffering')
        ''')
        self.assertPackageNamesEqual(pb, ['ponies'])
        self.assertEqual(['x86_64'], pb['ponies']['arch'])
        self.assertEqual(['friendship', 'magic'], pb['ponies']['depends'])
        self.assertNotIn('depends_armv7h', pb['ponies'])

    def test_ArchOverrideInPackage(self):
        pb = testutil.parse_pkgbuild('''
            pkgname=ponies
            arch=('i686' 'x86_64')
            depends=('friendship' 'magic')

            package() {
              arch=('any')
              depends_x86_64=('ignore' 'me')
            }
        ''')
        self.assertPackageNamesEqual(pb, ['ponies'])
        self.assertEqual(['friendship', 'magic'], pb['ponies']['depends'])
        self.assertNotIn('depends_x86_64', pb['ponies'])


if __name__ == '__main__':
    unittest.main()
