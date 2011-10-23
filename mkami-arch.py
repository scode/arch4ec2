#!/usr/bin/env python

# Why Python? Right now it's a pretty good question. If I spend the
# effort I want to make it a bit more non-trivial and I wanted Python
# for that. Plus, good use-case for Python 3 that I normally can't
# use.

from __future__ import with_statement
from __future__ import absolute_import

import argparse
import io
import logging
import os
import subprocess
import sys
import tempfile

# Not that we NEED python 3. But hey, taking the opportunity to target
# Python 3 since for once I can, not having to worry about supporting
# old software, since arch is up-to-date.
assert (sys.version_info.major, sys.version_info.minor) >= (3,2), "python 3.2+ required - should not be a problem since you're on arch, right? :)"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('mkarmi-arch')

EC2_ARCHS = { 'i686': 'i386' }
ARCH_ARCHS = { 'i686': 'i686' }

PACKAGES = [
        'base-devel',
        'abs',
        'base-devel',
        'bash-completion',
        'btrfs-progs-unstable',
        'ca-certificates',
        'ca-certificates',
        'coreutils',
        'cpio',
        'curl',
        'devtools',
        'dhcpcd',
        'dnsutils',
        'ec2-metadata',
        'filesystem',
        'groff',
        'initscripts',
        'iproute2',
        'iputils',
        'less',
        'lesspipe',
        'linux-arch4ec2',
        'linux-arch4ec2-headers',
        'logrotate',
        'mailx',
        'nano',
        'net-tools',
        'openssh',
        'pacman',
        'procps',
        'psmisc',
        'screen',
        'sed',
        'srcpac',
        'ssmtp',
        'sudo',
        'syslog-ng',
        'tar',
        'vi',
        'vim',
        'vim-colorsamplerpack',
        'vimpager',
        'wget',
        'which',
        'zsh',
]

class ShellCommandFailed(Exception):
    pass

def escape(s):
    """
    Escape s in such a way that it is safe for s to contain arbitrary
    content, and then put in between two single quotes in shell.
    """
    def esc_chr(c):
        if c == "'":
            return "'\''"
        elif c == '\\':
            return '\\\\'
        else:
            return c
    return ''.join((esc_chr(c) for c in s))

def zsh(cmd, collect_stdout=False, collect_stderr=False, stdin=None, env=None):
    """
    Return something callable to which you can give args/kwargs in the same fashion as str.format. All args (whether positional or
    keyword based) will be escaped with escape().

      zsh("mv '{0}' '{dst}'")(src_dir, dst=dst_dir)

    The callable can be re-used if desired. It will return (returncode, stdout, stderr).

    @param cmd Shell command to be executed as if typed at shell. Any parameters for format expansion should be enclosed in single-quotes.
    """
    if isinstance(stdin, str):
        stdin = stdin.encode()

    def f(*args, **kwargs):
        eargs = [ escape(arg) for arg in args]
        ekwargs = dict((((key, escape(val)) for key, val in kwargs.items())))

        escaped_cmd = cmd.format(*eargs, **ekwargs)

        args = ["/usr/bin/env", "zsh", "-c"] + [escaped_cmd]
        log.info('exec: %s', args)
        p = subprocess.Popen(args,
                             stdout=subprocess.PIPE if collect_stdout else None,
                             stderr=subprocess.PIPE if collect_stderr else None,
                             stdin=subprocess.PIPE if stdin else None,
                             env=env)
        stdout, stderr = p.communicate(input=stdin)
        r = p.wait()

        # TODO: augment to support expecting failure
        if r != 0:
            raise ShellCommandFailed(escaped_cmd, r)

        return (r, stdout, stderr)
    return f

def uname(flag):
    _, stdout, _  = zsh('uname -{0}', collect_stdout=True, collect_stderr=True)(flag)
    return stdout.strip().decode('ASCII')

def machine_arch():
    return uname('m')

def parse_args():
    parser = argparse.ArgumentParser(description='Create an Arch Linux EC2 EBS AMI')
    parser.add_argument('--target-ebs-device', type=str, default=None,
                        help='The device path (e.g., /dev/xvdj) of the EBS volume on which to create the AMI.')
    parser.add_argument('--mount-point', type=str, default=None,
                        help='The path to the directory on which to mount the root file system during bootstrap.')
    parser.add_argument('--temp-dir', type=str, default='/var/tmp',
                        help='The directory in which to allocate the temporary directory used for bootstrapping.')

    return parser.parse_args()

def fdisk(device):
    stdin = """n
p


+100M
n
p



w
"""
    zsh("fdisk '{device}'", stdin=stdin)(device=device)

def barf(fname, contents):
    with file(fname, 'w') as f:
        f.write(contents)

def slurp(fname):
    with file(fname, 'r') as f:
        return f.read()

def blkid_of_device(path):
    r, stdout, stderr = zsh("blkid -c /dev/null -s UUID -o export '{path}'", collect_stdout=True)(path=path)

    ret = stdout.decode('utf-8')
    ret = ret.strip()
    assert ret.find('\n') == -1, 'expected single line of output from blkid'
    return ret

def main():
    args = parse_args()

    if not args.target_ebs_device or not args.mount_point:
        log.error('must specify at least --target-ebs-device and --mount-point (see --help)')
        sys.exit(1)

    filenames = []
    fds = []
    files = []
    mounted = []
    tmpdirs = []
    btrfs_subvolumes = []
    try:
        zsh("dd if=/dev/zero of='{}' bs=512 count=1")(args.target_ebs_device)
        fdisk(args.target_ebs_device)
        zsh("mkfs.ext3 '{0}'1")(args.target_ebs_device)
        zsh("mkfs.btrfs '{0}'2")(args.target_ebs_device)
        zsh("mkdir -p '{0}'")(args.mount_point)
        zsh("mount -o compress '{0}'2 '{1}'")(args.target_ebs_device, args.mount_point)
        mounted.append(args.mount_point)
        zsh("chmod 755 '{0}'")(args.mount_point)
        zsh("mkdir '{0}/boot'")(args.mount_point)
        zsh("mount '{0}'1 '{1}'/boot")(args.target_ebs_device, args.mount_point)
        mounted.append(os.path.join(args.mount_point, 'boot'))
        zsh("btrfs subvolume create '{0}'/home")(args.mount_point)
        zsh("btrfs subvolume create '{0}'/etc")(args.mount_point)
        zsh("btrfs subvolume create '{0}'/srv")(args.mount_point)
        zsh("btrfs subvolume create '{0}'/var")(args.mount_point)
        zsh("btrfs subvolume create '{0}'/opt")(args.mount_point)
        zsh("btrfs subvolume create '{0}'/usr")(args.mount_point)

        fd, pacman_conf = tempfile.mkstemp('pacman.conf')
        fds.append(fd)
        filenames.append(pacman_conf)
        with io.open(fd, 'w', closefd=False, encoding='utf-8') as f:
            f.write("[options]\n")
            f.write("HoldPkg     = pacman glibc\n")
            f.write("SyncFirst   = pacman\n")
            f.write("Architecture = {0}\n".format(ARCH_ARCHS[machine_arch()]))
            f.write("[arch4ec2]\n")
            f.write("Server = file://{repo_path}\n".format(repo_path=os.path.join(os.getcwd(), 'repo')))
            f.write("[core]\n")
            f.write("Include = /etc/pacman.d/mirrorlist\n")
            f.write("[extra]\n")
            f.write("Include = /etc/pacman.d/mirrorlist\n")
            f.write("[community]\n")
            f.write("Include = /etc/pacman.d/mirrorlist\n")


        tmprootparent = tempfile.mkdtemp('archtmprootpraent')
        tmpdirs.append(tmprootparent)

        tmproot = os.path.join(tmprootparent, 'rootfs')
        btrfs_subvolumes.append(tmproot) # mkarchroot creates a btrfs subvolume

        package_string = ' '.join(("'{0}'".format(escape(pkg)) for pkg in PACKAGES))
        zsh("/usr/sbin/mkarchroot -C '{0}' '{1}' " + package_string, env=dict(LC_ALL='C'))(pacman_conf, tmproot)

        # sorry, switching style in the middle :)
        subs = {'ROOT': tmproot,
                'NEWROOT': args.mount_point,
                'ARCH_ARCH': ARCH_ARCHS[machine_arch()]}
        def zsub(cmd):
            zsh(cmd)(**subs)

        zsub("mv {ROOT}/etc/pacman.d/mirrorlist {ROOT}/etc/pacman.d/mirrorlist.pacorig")
        with io.open('{ROOT}/etc/pacman.d/mirrorlist'.format(**subs), 'w') as f:
            f.write("Server = http://mirrors.kernel.org/archlinux/$repo/os/{ARCH_ARCH}\n")
            f.write("Server = ftp://ftp.archlinux.org/$repo/os/{ARCH_ARCH}\n")

        zsub("chmod 666 {ROOT}/dev/null")
        zsub("mknod -m 666 {ROOT}/dev/ranom c 1 8")
        zsub("mknod -m 666 {ROOT}/dev/urandom c 1 9")
        zsub("mkdir -m 755 {ROOT}/dev/pts")
        zsub("mkdir -m 1777 {ROOT}/dev/shm")
        zsub("mv {ROOT}/etc/rc.conf {ROOT}/etc/rc.conf.pacorig")
        # TODO: configurable timezone, locale
        with io.open('{ROOT}/etc/inittab'.format(**subs), 'w') as f:
            f.write('LOCALE="en_US.UTF-8"\n')
            f.write('TIMEZONE="UTC"\n')
            f.write('MOD_AUTOLOAD="no"\n')
            f.write('USECOLOR="yes"\n')
            f.write('USELVM="no"\n')
            f.write('DAEMONS=(syslog-ng network sshd crond ec2)\n')
            f.write('interface=eth0\n')
            f.write('address=\n')
            f.write('gateway=\n')
            f.write('netmask=\n')
            f.write('broadcast=\n')
        zsub("mv {ROOT}/etc/inittab {ROOT}/etc/inittab.pacorig")

        with io.open('{ROOT}/etc/inittab'.format(**subs), 'w') as f:
            f.write("id:3:initdefault:\n")
            f.write("rc::sysinit:/etc/rc.sysinit\n")
            f.write("rs:S1:wait:/etc/rc.single\n")
            f.write("rm:2345:wait:/etc/rc.multi\n")
            f.write("rh:06:wait:/etc/rc.shutdown\n")
            f.write("su:S:wait:/sbin/sulogin -p\n")
            f.write("ca::ctrlaltdel:/sbin/shutdown -t3 -r now\n")
            f.write("# This will enable the system log.\n")
            f.write("c0:12345:respawn:/sbin/agetty 38400 hvc0 linux\n")

        with io.open('{ROOT}/etc/hosts.deny'.format(**subs), 'w') as f:
            f.write("#\n")
            f.write("# /etc/hosts.deny\n")
            f.write("#\n")

        zsub("mkdir -p {ROOT}/boot/boot/grub")
        with io.open('{ROOT}/boot/boot/grub/menu.lst'.format(**subs), 'w') as f:
            f.write("default 0\n")
            f.write("timeout 1\n")
            f.write("\n")
            f.write("title  Arch Linux\n")
            f.write("	root   (hd0,0)\n")
            f.write("	kernel /vmlinuz-linux-arch4ec2 root=/dev/xvda2 console=hvc0 ip=dhcp spinlock=tickless ro\n")
            f.write("	initrd /initramfs-linux-arch4ec2.img\n")

        zsub("cd {ROOT}/boot && ln -s boot/grub .")
        zsub("sed -i.pacorig -e 's/#PasswordAuthentication yes/PasswordAuthentication no/' "
             "-e 's/#UseDNS yes/UseDNS no/' {ROOT}/etc/ssh/sshd_config")

        zsub("cp {ROOT}/etc/skel/.bash* {ROOT}/root")
        zsub("cp {ROOT}/etc/skel/.screenrc {ROOT}/root")
        zsub("mv {ROOT}/etc/fstab {ROOT}/etc/fstab.pacorig")

        with io.open('{ROOT}/etc/fstab'.format(**subs), 'w') as f:
            f.write("{root_blkid} /     auto    defaults,compress,relatime 0 1\n".format(root_blkid=blkid_of_device(args.target_ebs_device + '2')))
            f.write("{boot_blkid} /boot auto    defaults,noauto,relatime 0 0\n".format(boot_blkid=blkid_of_device(args.target_ebs_device + '1')))
            f.write("/dev/xvdb /tmp  auto    defaults,relatime 0 0\n")
            f.write("/dev/xvda3 swap  swap   defaults 0 0\n")
            f.write("none      /proc proc    nodev,noexec,nosuid 0 0\n")
            f.write("none /dev/pts devpts defaults 0 0\n")
            f.write("none /dev/shm tmpfs nodev,nosuid 0 0\n")

        zsub("mkdir {ROOT}/opt/sources")
        zsub("mkdir {ROOT}/opt/packages")
        zsub("mkdir {ROOT}/opt/srcpackages")
        zsub("chmod 1777 {ROOT}/opt/sources")
        zsub("chmod 1777 {ROOT}/opt/packages")
        zsub("chmod 1777 {ROOT}/opt/srcpackages")

        zsub("mv {ROOT}/etc/resolv.conf {ROOT}/etc/resolv.conf.pacorig")
        with io.open('{ROOT}/etc/resolv.conf'.format(**subs), 'w') as f:
            f.write("nameserver 172.16.0.23\n")
        zsub("touch {ROOT}/root/firstboot")

        #TODO: copy repo

        zsub("cd {ROOT} && find . -depth -print | cpio -pdmv --sparse {NEWROOT}")
    except Exception as e:
        log.exception('failure')
        raise
    finally:
        print('press enter to cleanup')
        sys.stdin.readline()
        for subvol in reversed(btrfs_subvolumes):
            try:
                zsh("btrfs subvolume delete '{0}'")(subvol)
            except:
                log.error('failed to delete btrfs subvolume at %s', subvol)
        for mpoint in reversed(mounted):
            try:
                zsh("umount '{0}'")(mpoint)
            except:
                log.error('failed to umount %s', mpoint)
        for filename in filenames:
            try:
                os.unlink(filename)
            except:
                log.error('failed to unlink %s', filename)
        for fd in fds:
            try:
                os.close(fd)
            except:
                log.error('failed to close fd %d', fd)
        for f in files:
            try:
                f.close()
            except:
                log.error('failed to close file like object')
        for tmpdir in tmpdirs:
            print("WOULD HAVE REMOVED TEMPDIR: {0}".format(tmpdir))
            continue
            try:
                zsh("rm -rf '{0}'")(tmpdir)
            except:
                log.error('failed to remove tempdir')

if __name__ == '__main__':
    main()
