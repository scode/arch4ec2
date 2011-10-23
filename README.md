Automated bootstrapping of Arch Linux AMI:s for EC2. Inspired by
https://github.com/yejun/ec2build but updated and aiming to be a bit
more complete.

## Current status

Only 32 bit supported. 64 bit would probably work with minor
modifications; the known issue is that the kernel config must be
modified. Unteste.d

NOTE: Documentation is currently very minimal. Should be improved.

## How to create an AMI

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
EC2.
