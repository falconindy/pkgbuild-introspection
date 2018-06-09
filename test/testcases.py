#!/usr/bin/python

import unittest
import testutil

class TestPkgbuildToAurinfo(unittest.TestCase):
    def assertPackageNamesEqual(self, srcinfo, package_names):
        return self.assertCountEqual(srcinfo.keys(), package_names)

    def test_SinglePackage(self):
        pb = testutil.parse_pkgbuild('pkgname=ponies')
        self.assertPackageNamesEqual(pb, ['ponies'])

        pb = testutil.parse_pkgbuild('''
            pkgbase=ponies
            pkgname=('applejack')
        ''')
        self.assertPackageNamesEqual(pb, ['applejack'])

    def test_SkipsEmptyAttrsInPackageOverride(self):
        pb = testutil.parse_pkgbuild('''
            pkgname=(ponies)
            package_ponies() {
                depends+=('derp')
            }
        ''')
        self.assertCountEqual(['derp'], pb['ponies']['depends'])
        self.assertCountEqual

    # curious behavior, but the implementation explicitly supports this.
    def test_SupportsEmptyStringsAsArrayElements(self):
        pb = testutil.parse_pkgbuild('''
            pkgname=(ponies)
            depends=(foo '' bar)
        ''')
        self.assertCountEqual(['', 'foo', 'bar'], pb['ponies']['depends'])

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

    def test_HandlesDeclareInGlobalAttrs(self):
        pb = testutil.parse_pkgbuild('''
            declare pkgbase=ponies
            declare -a pkgname=('applejack' 'pinkiepie')
            declare depends=('foo')
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
            pkgrel=2
            epoch=3
            package() {
              pkgver=2
              pkgrel=3
              epoch=4
            }
        ''')
        self.assertPackageNamesEqual(pb, ['ponies'])
        self.assertEqual("1", pb['ponies']['pkgver'])
        self.assertEqual("2", pb['ponies']['pkgrel'])
        self.assertEqual("3", pb['ponies']['epoch'])

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

    def test_HandlesMultiLineArrays(self):
        pb = testutil.parse_pkgbuild('''
            pkgname=ponies
            depends=(foo
                     bar
                     baz)
        ''')
        self.assertPackageNamesEqual(pb, ['ponies'])
        self.assertEqual(['foo', 'bar', 'baz'], pb['ponies']['depends'])

    @unittest.expectedFailure
    def test_HandlesMultiLineValuesInFunctions(self):
        pb = testutil.parse_pkgbuild('''
            pkgname=ponies
            package_ponies() {
              optdepends=('some:
                           program')
            }
        ''')
        self.assertPackageNamesEqual(pb, ['ponies'])
        self.assertRegex(pb['ponies']['optdepends'][0], 'some:.*program')

    def test_HandlesRegexyPackageNames(self):
        pb = testutil.parse_pkgbuild('''
            pkgname=('ponies+cake')
            pkgver=1.2.3

            package_ponies+cake() {
              depends=('pie' 'apples')
            }
        ''')
        self.assertPackageNamesEqual(pb, ['ponies+cake'])
        self.assertEqual(['pie', 'apples'], pb['ponies+cake']['depends'])
        self.assertEqual('1.2.3', pb['ponies+cake']['pkgver'])

    def test_HandlesQuotedValues(self):
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

    def test_HandlesBraceExpansions(self):
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
    def test_HandlesShellVarInPackageAttr(self):
        pb = testutil.parse_pkgbuild('''
            pkgname=ponies

            package() {
              foo=bar
              depends=("$foo")
            }
        ''')
        self.assertPackageNamesEqual(pb, ['ponies'])
        self.assertEqual(['bar'], pb['ponies']['depends'])

    def test_HandlesMutlivaluedArchSpecific(self):
        pb1 = testutil.parse_pkgbuild('''
            pkgname=ponies
            arch=('x86_64')
            depends_x86_64=('friendship' 'magic')
            source_x86_64=('http://example.com/fooball.tar.gz')
            md5sums_x86_64=('d41d8cd98f00b204e9800998ecf8427e')
        ''')
        self.assertPackageNamesEqual(pb1, ['ponies'])
        self.assertEqual(['friendship', 'magic'], pb1['ponies']['depends_x86_64'])
        self.assertEqual(['http://example.com/fooball.tar.gz'], pb1['ponies']['source_x86_64'])
        self.assertEqual(['d41d8cd98f00b204e9800998ecf8427e'], pb1['ponies']['md5sums_x86_64'])

        pb2 = testutil.parse_pkgbuild('''
            pkgname=ponies
            arch=('x86_64')
            source_x86_64=('http://example.com/fooball.tar.gz')
            md5sums_x86_64=('d41d8cd98f00b204e9800998ecf8427e')
            package() {
              depends_x86_64=('friendship' 'magic')
            }
        ''')
        self.assertDictEqual(pb1, pb2)

    def test_IgnoresUnsupportedArchSpecificOverrideInGlobal(self):
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

    def test_IgnoresUnsupportedArchSpecificOverrideInPackage(self):
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

    def test_IgnoresEmptyGlobalAttributes(self):
        pb = testutil.parse_pkgbuild('''
            pkgname=ponies
            pkgver=1.2.3
            epoch=
            arch=('i686' 'x86_64')

            package() { :; }
        ''')
        self.assertPackageNamesEqual(pb, ['ponies'])
        self.assertEqual('1.2.3', pb['ponies']['pkgver'])
        self.assertNotIn('epoch', pb['ponies'])

    @unittest.expectedFailure
    def test_EmptyPackageAttributeOverridesGlobal(self):
        pb = testutil.parse_pkgbuild('''
            pkgname=ponies
            pkgver=1.2.3
            depends=('foo' 'bar')
            arch=('i686' 'x86_64')
            install=ponies.install

            package() {
              install=
              depends=()
            }
        ''')
        self.assertPackageNamesEqual(pb, ['ponies'])
        self.assertEqual('1.2.3', pb['ponies']['pkgver'])
        self.assertIn('depends', pb['ponies'])
        self.assertListEqual([], pb['ponies']['depends'])
        self.assertIn('install', pb['ponies'])
        self.assertEqual('', pb['ponies']['install'])

    def test_CoverageSmokeTest(self):
        pb = testutil.parse_pkgbuild('''
            pkgname=('gcc' 'gcc-libs' 'gcc-fortran' 'gcc-objc' 'gcc-ada' 'gcc-go')
            pkgver=4.9.1
            _pkgver=4.9
            pkgrel=2
            _snapshot=4.9-20140903
            pkgdesc="The GNU Compiler Collection"
            arch=('i686' 'x86_64')
            license=('GPL' 'LGPL' 'FDL' 'custom')
            url="http://gcc.gnu.org"
            makedepends=('binutils>=2.24' 'libmpc' 'cloog' 'gcc-ada' 'doxygen')
            checkdepends=('dejagnu' 'inetutils')
            options=('!emptydirs')
            source=(ftp://gcc.gnu.org/pub/gcc/snapshots/${_snapshot}/gcc-${_snapshot}.tar.bz2
                    gcc-4.8-filename-output.patch
                    gcc-4.9-isl-0.13-hack.patch)
            md5sums=('24dfd67139fda4746d2deff18182611d'
                     '40cb437805e2f7a006aa0d0c3098ab0f'
                     'f26ae06b9cbc8abe86f5ee4dc5737da8')

            package_gcc-libs() {
              pkgdesc="Runtime libraries shipped by GCC"
              groups=('base')
              depends=('glibc>=2.20')
              options=('!emptydirs' '!strip')
              install=gcc-libs.install
            }

            package_gcc() {
              pkgdesc="The GNU Compiler Collection - C and C++ frontends"
              depends=("gcc-libs=$pkgver-$pkgrel" 'binutils>=2.24' 'libmpc' 'cloog')
              groups=('base-devel')
              options=('staticlibs')
              install=gcc.install
            }

            package_gcc-fortran() {
              pkgdesc="Fortran front-end for GCC"
              depends=("gcc=$pkgver-$pkgrel")
              options=('staticlibs' '!emptydirs')
              install=gcc-fortran.install
            }

            package_gcc-objc() {
              pkgdesc="Objective-C front-end for GCC"
              depends=("gcc=$pkgver-$pkgrel")
            }

            package_gcc-ada() {
              pkgdesc="Ada front-end for GCC (GNAT)"
              depends=("gcc=$pkgver-$pkgrel")
              options=('staticlibs' '!emptydirs')
              install=gcc-ada.install
            }

            package_gcc-go() {
              pkgdesc="Go front-end for GCC"
              depends=("gcc=$pkgver-$pkgrel")
              options=('staticlibs' '!emptydirs')
              install=gcc-go.install
            }
        ''')

        expected_packages = ['gcc', 'gcc-libs', 'gcc-fortran', 'gcc-objc', 'gcc-ada', 'gcc-go']
        self.assertPackageNamesEqual(pb, expected_packages)

        for pkgname in expected_packages:
            pkg = pb[pkgname]
            self.assertEqual('4.9.1', pkg['pkgver'])
            self.assertEqual('2', pkg['pkgrel'])
            self.assertEqual(['i686', 'x86_64'], pkg['arch'])
            self.assertEqual(['GPL', 'LGPL', 'FDL', 'custom'], pkg['license'])
            self.assertEqual('http://gcc.gnu.org', pkg['url'])
            self.assertEqual(['binutils>=2.24','libmpc', 'cloog', 'gcc-ada', 'doxygen'], pkg['makedepends'])
            self.assertEqual(['dejagnu', 'inetutils'], pkg['checkdepends'])
            self.assertEqual(['ftp://gcc.gnu.org/pub/gcc/snapshots/4.9-20140903/gcc-4.9-20140903.tar.bz2',
                              'gcc-4.8-filename-output.patch',
                              'gcc-4.9-isl-0.13-hack.patch'], pkg['source'])
            self.assertEqual(['24dfd67139fda4746d2deff18182611d',
                              '40cb437805e2f7a006aa0d0c3098ab0f',
                              'f26ae06b9cbc8abe86f5ee4dc5737da8'], pkg['md5sums'])

        self.assertEqual('Runtime libraries shipped by GCC', pb['gcc-libs']['pkgdesc'])
        self.assertEqual(['base'], pb['gcc-libs']['groups'])
        self.assertEqual(['glibc>=2.20'], pb['gcc-libs']['depends'])
        self.assertEqual(['!emptydirs', '!strip'], pb['gcc-libs']['options'])
        self.assertEqual('gcc-libs.install', pb['gcc-libs']['install'])

        self.assertEqual('The GNU Compiler Collection - C and C++ frontends', pb['gcc']['pkgdesc'])
        self.assertEqual(['gcc-libs=4.9.1-2', 'binutils>=2.24', 'libmpc', 'cloog'], pb['gcc']['depends'])
        self.assertEqual(['base-devel'], pb['gcc']['groups'])
        self.assertEqual(['staticlibs'], pb['gcc']['options'])
        self.assertEqual('gcc.install', pb['gcc']['install'])

        self.assertEqual('Fortran front-end for GCC', pb['gcc-fortran']['pkgdesc'])
        self.assertEqual(['gcc=4.9.1-2'], pb['gcc-fortran']['depends'])
        self.assertEqual(['staticlibs', '!emptydirs'], pb['gcc-fortran']['options'])
        self.assertEqual('gcc-fortran.install', pb['gcc-fortran']['install'])
        self.assertNotIn('groups', pb['gcc-fortran'])

        self.assertEqual('Objective-C front-end for GCC', pb['gcc-objc']['pkgdesc'])
        self.assertEqual(['gcc=4.9.1-2'], pb['gcc-objc']['depends'])
        self.assertEqual(['!emptydirs'], pb['gcc-objc']['options'])
        self.assertNotIn('install', pb['gcc-objc'])
        self.assertNotIn('groups', pb['gcc-objc'])

        self.assertEqual('Ada front-end for GCC (GNAT)', pb['gcc-ada']['pkgdesc'])
        self.assertEqual(['gcc=4.9.1-2'], pb['gcc-ada']['depends'])
        self.assertEqual(['staticlibs', '!emptydirs'], pb['gcc-ada']['options'])
        self.assertEqual('gcc-ada.install', pb['gcc-ada']['install'])
        self.assertNotIn('groups', pb['gcc-ada'])

        self.assertEqual('Go front-end for GCC', pb['gcc-go']['pkgdesc'])
        self.assertEqual(['gcc=4.9.1-2'], pb['gcc-go']['depends'])
        self.assertEqual(['staticlibs', '!emptydirs'], pb['gcc-go']['options'])
        self.assertEqual('gcc-go.install', pb['gcc-go']['install'])
        self.assertNotIn('groups', pb['gcc-go'])

if __name__ == '__main__':
    unittest.main()
