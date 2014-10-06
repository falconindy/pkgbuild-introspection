shopt -s extglob

array_build() {
  local dest=$1 src=$2 i keys values

  # it's an error to try to copy a value which doesn't exist.
  declare -p "$2" &>/dev/null || return 1

  # Build an array of the indicies of the source array.
  eval "keys=(\"\${!$2[@]}\")"

  # Read values indirectly via their index. This approach gives us support
  # for associative arrays, sparse arrays, and empty strings as elements.
  for i in "${keys[@]}"; do
    values+=("printf -v '$dest[$i]' %s \"\${$src[$i]}\";")
  done

  eval "${values[*]}"
}

funcgrep() {
  { declare -f "$1" || declare -f package; } 2>/dev/null | grep -E "$2"
}

extract_global_var() {
  # $1: variable name
  # $2: multivalued
  # $3: name of output var

  local attr=$1 isarray=$2 outputvar=$3

  if (( isarray )); then
    declare -n ref=$attr
    # Still need to use array_build here because we can't handle the scoping
    # semantics that would be included with the use of 'declare -n'.
    [[ ${ref[@]} ]] && array_build "$outputvar" "$attr"
  else
    [[ -v $attr ]] && printf -v "$outputvar" %s "${!attr}"
  fi
}

extract_function_var() {
  # $1: function name
  # $2: variable name
  # $3: multivalued
  # $4: name of output var

  local funcname=$1 attr=$2 isarray=$3 outputvar=$4 attr_regex= decl= r=1

  if (( isarray )); then
    printf -v attr_regex '^[[:space:]]*(declare( -[[:alpha:]])*)? %q\+?=\(' "$2"
  else
    printf -v attr_regex '^[[:space:]]*(declare( -[[:alpha:]])*)? %q\+?=[^(]' "$2"
  fi

  while read -r; do
    # strip leading whitespace and any usage of declare
    decl=${REPLY##*([[:space:]])?(declare +(-+([[:alpha:]]) ))}
    eval "${decl/#$attr/$outputvar}"

    # entering this loop at all means we found a match, so notify the caller.
    r=0
  done < <(funcgrep "$funcname" "$attr_regex")

  return $r
}

pkgbuild_get_attribute() {
  # $1: package name
  # $2: attribute name
  # $3: name of output var
  # $4: multivalued

  local pkgname=$1 attrname=$2 outputvar=$3 isarray=$4

  printf -v "$outputvar" %s ''

  if [[ $pkgname ]]; then
    extract_global_var "$attrname" "$isarray" "$outputvar"
    extract_function_var "package_$pkgname" "$attrname" "$isarray" "$outputvar"
  else
    extract_global_var "$attrname" "$isarray" "$outputvar"
  fi
}

srcinfo_open_section() {
  printf '%s = %s\n' "$1" "$2"
}

srcinfo_close_section() {
  echo
}

srcinfo_write_attr() {
  # $1: attr name
  # $2: attr values

  local attrname=$1 attrvalues=("${@:2}")

  # normalize whitespace, strip leading and trailing
  attrvalues=("${attrvalues[@]//+([[:space:]])/ }")
  attrvalues=("${attrvalues[@]#[[:space:]]}")
  attrvalues=("${attrvalues[@]%[[:space:]]}")

  printf "\t$attrname = %s\n" "${attrvalues[@]}"
}

pkgbuild_extract_to_srcinfo() {
  # $1: pkgname
  # $2: attr name
  # $3: multivalued

  local pkgname=$1 attrname=$2 isarray=$3 outvalue=

  if pkgbuild_get_attribute "$pkgname" "$attrname" 'outvalue' "$isarray"; then
    srcinfo_write_attr "$attrname" "${outvalue[@]}"
  fi
}

srcinfo_write_section_details() {
  local attr package_arch a
  local arch_specific_attrs=(source provides conflicts depends replaces
                             optdepends makedepends checkdepends)

  for attr in "${singlevalued[@]}"; do
    pkgbuild_extract_to_srcinfo "$1" "$attr" 0
  done

  for attr in "${multivalued[@]}"; do
    pkgbuild_extract_to_srcinfo "$1" "$attr" 1
  done

  pkgbuild_get_attribute "$1" 'arch' 'package_arch' 1
  for a in "${package_arch[@]}"; do
    # any is special -- if you want e.g. 'depends_any', you're really looking
    # for 'depends'.
    [[ $a = any ]] && continue

    # XXX: It's only by coincidence that we can blindly mark all these attrs as
    # multivalued. Be careful if/when more are added.
    for attr in "${arch_specific_attrs[@]}"; do
      pkgbuild_extract_to_srcinfo "$1" "${attr}_$a" 1
    done
  done
}

srcinfo_write_global() {
  local multivalued=(arch groups license checkdepends makedepends
                     depends optdepends provides conflicts replaces
                     noextract options backup
                     source {md5,sha{1,224,256,384,512}}sums)

  srcinfo_open_section 'pkgbase' "${pkgbase:-$pkgname}"
  srcinfo_write_section_details ''
  srcinfo_close_section
}

srcinfo_write_package() {
  local singlevalued=(pkgdesc url install changelog)
  local multivalued=(arch groups license checkdepends depends optdepends
                     provides conflicts replaces options backup)

  srcinfo_open_section 'pkgname' "$1"
  srcinfo_write_section_details "$1"
  srcinfo_close_section
}

srcinfo_write() {
  local pkg singlevalued=(pkgdesc pkgver pkgrel epoch url install changelog)

  srcinfo_write_global

  for pkg in "${pkgname[@]}"; do
    srcinfo_write_package "$pkg"
  done
}

clear_environment() {
  local environ

  mapfile -t environ < <(compgen -A variable |
      grep -xvF "$(printf '%s\n' "$@")")

  # expect that some variables marked read only will complain here
  unset -v "${environ[@]}" 2>/dev/null
}

srcinfo_write_from_pkgbuild() {(
  clear_environment PATH

  shopt -u extglob
  . "$1" || exit 1
  shopt -s extglob
  srcinfo_write
)}
