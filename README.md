## Description

Mostly automated creation/bootstrapping of an Arch Linux AMI for EC2,
without relying on any external "magic" other than that provided by
EC2, Arch Linux, and the contents of this repository.

Inspired by https://github.com/yejun/ec2build but updated and aiming
to be a bit more complete.

## Current status

Only 32 bit supported. 64 bit would probably work with minor
modifications; the known issue is that the kernel config must be
modified. Untested.

## Pre-created AMI:s

(NOTE: These lack /boot mounted when they start up, due to issue #3. I
will fix that and create new images at some point.)

* 2011-10-23: eu-west-1: ami-51625f25 / arch4ec2-32bit-20111023-3
* 2011-10-23: us-west-1: ami-f9b3efbc / arch4ec2-uswest-32bit-20111023-1

The dates indicate when they were created, and thus should reflect
arch as it appeared on that day (with appropriate fuzz depending on
mirror latencies).

(Want other regions/64 bit? Let me know. Else I'll do it when I get around to it.)

## How to create an AMI

I recommend *against* running this on a system that you use for
anything other than bootstrapping. The script is not treating 'root'
as a dangerous user (e.g., uses makepkg --asroot and rm -rf:es some
stuff, and if you specify the wrong EBS device you'll nuke something
you did not intend to nuke). Use of a virtualized environment of some
kind is highly recommended.

One way to get started is to use the pre-build AMI:s listed
above. Another way is to make a clean installation of Arch in
e.g. VirtualBox.

Firest, install dependencies, including zsh, xmlto, docbook-xsl and
probably others (I have yet to test on a truly minimalistic system).

Secondly, build the ec2-metadata and kernel packages and create the
arch repository (for use by pacman) by:

    ./makerepo.sh

After that, bootstrap the AMI on one of your devices (assuming
/dev/xvdb is the one):

    ./mkami-arch.py --target-ebs-device=/dev/xvdb --mount-point=/mnt/ami

Then snapshot your device (like this, or in the management console):

    ec2-create-snapshot -d 'my-ami-snapshot' vol-XXXXXXX

Then register your AMI using the snapshot just created:

    ec2-register --debug -s snap-XXXXXXXX --root-device-name /dev/sda -n my-arch-ami --kernel AKI

Where AKI is (see http://ec2-downloads.s3.amazonaws.com/user_specified_kernels.pdf):

* For eu-west-1: aki-47eec433
* For us-west-1: aki-9da0f1d8
* For us-east-1: aki-4c7d9525
* For ap-southeast-1: aki-6fd5aa3d

Note that the use of /dev/sda (rather than /dev/xvda) is intentional,
as that is how it appears to the early pv-grub boot environment at
EC2. The aki in the example is the 32 bit pv-grub aki supplied by
amazon for use on volumes with root fs on the first partition.

## The kernel

Since a customly configured kernel is necessary, and to avoid future
upgrades switching to a stock compiled kernel, the kernel package used
is specifically named after arch4ec2. This means that it should be
safe to upgrade all packages on the bootstrapped instances at any time
without risking switching to a kernel that won't boot.

Ideally, I should set up a repository for people to use. If you are
interested and would use it, let me know.
