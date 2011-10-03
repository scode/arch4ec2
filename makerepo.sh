#!/usr/bin/env zsh

set -x

(cd packages/ec2-metadata && makepkg --asroot)
(cd packages/linux-arch4ec2 && makepkg --asroot)

mkdir -p repo
cp packages/ec2-metadata/*.pkg.tar.xz repo
cp packages/linux-arch4ec2/*.pkg.tar.xz repo

(cd repo && repo-add arch4ec2.tar.gz *.pkg.tar.xz)


