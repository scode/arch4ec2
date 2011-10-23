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

## How to create an AMI

I recommend *against* running this on a system that you use for
anything other than bootstrapping. The script is not treating 'root'
as a dangerous user (e.g., uses makepkg --asroot and rm -rf:es some
stuff, and if you specify the wrong EBS device you'll nuke something
you did not intend to nuke). Use of a virtualized environment of some
kind is highly recommended.

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

  ec2-register --debug -s snap-XXXXXXXX --root-device-name /dev/sda -n my-arch-ami --kernel aki-47eec433

Note that the use of /dev/sda (rather than /dev/xvda) is intentional,
as that is how it appears to the early pv-grub boot environment at
EC2. The aki in the example is the 32 bit pv-grub aki supplised by
amazon for use on volumes with root fs on the first partition.
