#!/bin/sh
# Build Peter Miller's ucsd-psystem-xc, the fast tier of task 7.
#
# This is the host-side Pascal compiler for the UCSD p-System. It is NOT
# Apple's compiler and is not evidence about Apple; it is a way to compile
# reconstructed source in seconds instead of booting an emulator. Finding 55
# measures how close it gets: on both GOTOXY programs, where Apple's own
# compiled output is on the same disk, it reproduces the p-code byte for byte
# apart from one alignment byte per procedure.
#
# Run it under WSL or any Linux with libboost-dev, libexplain-dev and a C++
# compiler. It writes bin/ucsdpsys_compile and bin/ucsdpsys_disassemble under
# $PREFIX/ucsd-psystem-xc-0.13.
#
#   sh build.sh [destination-directory]
#
# The upstream 0.13 tarball is beside this script, and came from
# https://ucsd-psystem-xc.sourceforge.net/ucsd-psystem-xc-0.13.tar.gz
# It is GPL. Three things stop it building with a 2020s toolchain, all fixed
# here and none of them touching the compiler's behaviour:
#
#   1. sources.patch -- lib/bitmap/png.cc needs <cstring> and <zlib.h> that
#      newer libpng no longer drags in, and three `is_a` predicates return a
#      boost::shared_ptr where a bool is wanted, because newer Boost made the
#      bool conversion explicit.
#   2. Bison 3.8 emits a `YYerror` token into the token enum. The Makefile
#      renames every `yy`/`YY` to a per-grammar prefix with sed, which turns
#      that token into `pascal_grammar_error` -- colliding with the yyerror
#      function of the same name. Renaming the token before the substitution
#      keeps both.
#   3. The Makefile compiles to `foo.o` in the current directory and then
#      moves it into place, so a parallel make races on the many source files
#      named compile.cc. It has to be built with -j1.
set -e

here=$(cd "$(dirname "$0")" && pwd)
dest=${1:-$HOME/xcbuild}
mkdir -p "$dest"
cd "$dest"
rm -rf ucsd-psystem-xc-0.13
tar xzf "$here/ucsd-psystem-xc-0.13.tar.gz"
cd ucsd-psystem-xc-0.13

patch -p2 < "$here/sources.patch"

# Bison 3.8's YYerror token, renamed before the yy -> prefix substitution.
sed -i "s|sed -e 's/\[yY\]\[yY\]/|sed -e 's/YYerror/YYERRTOK/g' -e 's/[yY][yY]/|g" \
    Makefile.in

./configure --quiet --prefix="$dest/xc"
make -j1 bin/ucsdpsys_compile bin/ucsdpsys_disassemble     # -j1: see note 3

ls -l bin/ucsdpsys_compile bin/ucsdpsys_disassemble
