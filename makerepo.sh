#!/usr/bin/env zsh

set -e
set -x

# In order to faciliate re-running this script cleanly, perform builds in a copy.
rm -rf packages.build
(cd packages && find . -depth -print | cpio -pdmv --sparse ../packages.build)
(cd packages/ec2-metadata && makepkg --asroot)
(cd packages/linux-arch4ec2 && makepkg --asroot)

mkdir -p repo
cp packages.build/ec2-metadata/*.pkg.tar.xz repo
cp packages.build/linux-arch4ec2/*.pkg.tar.xz repo

(cd repo && repo-add arch4ec2.tar.gz *.pkg.tar.xz)


