#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# === This file is part of Calamares - <http://github.com/calamares> ===
#
#   Copyright 2015, Teo Mrnjavac <teo@kde.org>
#   Copyright 2017, Adriaan de Groot <groot@kde.org>
#
#   Calamares is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   Calamares is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with Calamares. If not, see <http://www.gnu.org/licenses/>.

# === Deploy Calamares ===
#
#   This script installs the build-dependencies of Calamares (a
#   compiler, cmake, etc.), then clones Calamares from GitHub
#   and builds it.
#
#   The script is tested and used on:
#       - Manjaro (primary platform)
#       - Netrunner (experimental phase)
#
#   The script should work on most distro's using yaourt or pacman.

import argparse
import os
import sys
import shutil
import subprocess


BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

#following from Python cookbook, #475186
def has_colours(stream):
    if not hasattr(stream, "isatty"):
        return False
    if not stream.isatty():
        return False # auto color only on TTYs
    try:
        import curses
        curses.setupterm()
        return curses.tigetnum("colors") > 2
    except:
        # guess false in case of error
        return False


has_colours = has_colours(sys.stdout)


def printout(text, colour=WHITE):
    if has_colours:
        seq = "\x1b[1;%dm" % (30+colour) + text + "\x1b[0m"
        return seq
    else:
        return text


def message(msg):
    sys.stdout.write(printout("==> ", GREEN) + printout(msg, WHITE) + "\n")

def warning(msg):
    sys.stdout.write(printout("==> ", YELLOW) + printout("Warning: " + msg, WHITE) + "\n")

def bail(msg):
    sys.stdout.write(printout("==> ", RED) + printout("Fatal error: " + msg + "\n", WHITE))
    sys.exit(1)


if sys.version_info.major != 3:
    bail("deploycala needs Python 3")
if not callable(getattr(shutil, "which", None)):
    bail("deploycala needs shutil.which")


if shutil.which("curl"):
    def fetch(url, target):
        fetcher = shutil.which("curl")
        return os.system(fetcher + " --create-dirs -o " + target + " -L " + url)
elif shutil.which("wget"):
    def fetch(url, target):
        fetcher = shutil.which("wget")
        r = os.system(fetcher + " --backups=1 " + target + " " + url)
        if r > 255:
            r &= 0xff
        if r:
            os.rename(target+".1", target)
        return r
else:
    bail("deploycala needs curl or wget")


def update_self():
    message("Updating deployment script...")
    thisfile = os.path.realpath(__file__)
    if fetch("https://calamares.io/deploycala.py", thisfile) != 0:
        bail("Self-update failed")

    os.system("chmod +x " + thisfile)

    myargs = sys.argv[:]
    message('Update complete, restarting %s' % ' '.join(myargs))

    myargs.insert(0, sys.executable)
    myargs.append('--noupdate')

    os.execv(sys.executable, myargs)

def pacman_mirrors():
    if shutil.which("pacman-mirrors"):
        os.system("sudo pacman-mirrors -c Germany")


def yaourt_update(noupgrade):
    packages = ["autoconf", "automake", "binutils", "bison", "fakeroot", "git",
                "flex", "gcc-multilib", "gcc-libs-multilib", "libtool", "m4", "make",
                "patch", "cmake", "extra-cmake-modules", "boost", "qt5-tools",
                "kiconthemes", "kservice", "kio", "kparts", "qtcreator", "ack",
                "qt5-webengine"]
    aurpackages = ["icecream"]
    if noupgrade:
        subprocess.call(["yaourt -Sy --noconfirm --needed --force " + " ".join(packages)], shell=True)
    else:
        subprocess.call(["yaourt -Syu --noconfirm --needed --force " + " ".join(packages)], shell=True)

    subprocess.call(["yaourt -S --aur --noconfirm --needed --force " + " ".join(aurpackages)], shell=True)


def pacman_update(noupgrade):
    packages = ["autoconf", "automake", "binutils", "bison", "fakeroot", "git",
                "flex", "gcc", "gcc-libs-multilib", "libtool", "m4", "make",
                "patch", "cmake", "extra-cmake-modules", "boost", "qt5-tools",
                "kiconthemes", "kservice", "kio", "kparts", "qtcreator", "ack",
                "qt5-webengine", "kpmcore", "qt5-location", "icu", "qt5-declarative",
                "qt5-translations", "qt5-xmlpatterns"]
    if noupgrade:
        os.system("sudo pacman -Sy --noconfirm --needed --force " + " ".join(packages))
    else:
        os.system("sudo pacman -Syu --noconfirm --needed --force " + " ".join(packages))

def setup_sudo_gdb():
    os.system("sudo touch /usr/bin/sudo-gdb")
    os.system("sudo chmod a+rwx /usr/bin/sudo-gdb")
    file = open('/usr/bin/sudo-gdb','w+')
    file.write('#!/bin/bash\nsudo gdb $@\n')
    file.close()

def inplace_change(filename, old_string, new_string):
    if os.path.exists(filename):
        s=open(filename).read()
        if old_string in s:
                s=s.replace(old_string, new_string)
                f=open(filename, 'w')
                f.write(s)
                f.flush()
                f.close()

def get_file_if_not_exists(source, target):
    if not os.path.exists(target):
        if fetch(source, target) == 0:
            message('Fetched ' + target)
        else:
            warning('cannot fetch ' + target)
    else:
        message('File ' + target + ' already exists, won\'t update.')

def setup_qtcreator():
    os.chdir(os.path.expanduser('~'))
    prefix = 'https://calamares.io/deploycala.d/'
    getfiles = dict([
    (prefix + 'CMakeLists.txt.user', 'calamares/CMakeLists.txt.user'),
    (prefix + 'debuggers.xml', '.config/QtProject/qtcreator/debuggers.xml'),
    (prefix + 'QtCreator.ini', '.config/QtProject/QtCreator.ini'),
    (prefix + 'default.qws', '.config/QtProject/qtcreator/default.qws'),
    (prefix + 'profiles.xml', '.config/QtProject/qtcreator/profiles.xml'),
    (prefix + 'cmaketools.xml', '.config/QtProject/qtcreator/cmaketools.xml'),
    (prefix + 'toolchains.xml', '.config/QtProject/qtcreator/toolchains.xml')])

    for src, dest in getfiles.items():
        get_file_if_not_exists(src, dest)
        inplace_change(dest, "/home/netrunner", os.path.expanduser('~'))

def setup_icecream():
    os.system('bash -c \'echo "export PATH=/usr/lib/icecream/libexec/icecc/bin:$PATH" >> ~/.bashrc\'')
    os.system('bash -c \'source ~/.bashrc\'')
    os.system('sudo systemctl enable icecream.service')
    os.system('sudo systemctl start icecream.service')
    path = os.environ["PATH"]
    os.environ["PATH"] = "/usr/lib/icecream/libexec/icecc/bin:" + path
    os.system('which gcc')
    os.system('which g++')
    has_icecream = "icecream" in str(subprocess.check_output(["which", "g++"])).strip()
    return has_icecream

# Courtesy of phihag on Stack Overflow,
# http://stackoverflow.com/questions/1006289/how-to-find-out-the-number-of-cpus-using-python
def available_cpu_count():
    # Python 3.4+
    try:
        import multiprocessing
        return multiprocessing.cpu_count()
    except (ImportError, NotImplementedError):
        pass

    # POSIX
    try:
        res = int(os.sysconf('SC_NPROCESSORS_ONLN'))

        if res > 0:
            return res
    except (AttributeError, ValueError):
        pass

    # Linux
    try:
        res = open('/proc/cpuinfo').read().count('processor\t:')

        if res > 0:
            return res
    except IOError:
        pass

    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("branch", nargs="?", default="master",
                        help="the branch to checkout and build")
    parser.add_argument("-n", "--noupgrade", action="store_true", dest="noupgrade",
                        help="do not upgrade all the packages on the system before building")
    parser.add_argument("-p", "--nopull", action="store_true", dest="nopull",
                        help="do not pull before building (only applies if a clone already exists)")
    parser.add_argument("-i", "--incremental", action="store_true", dest="incremental",
                        help="do incremental builds, i.e. don't clear the build directory before building, if found")
    parser.add_argument("--noupdate", action="store_true", dest="noupdate", help=argparse.SUPPRESS)
    parser.add_argument("-u", "--url", nargs=1, default="https://github.com/calamares/calamares.git",
                        dest="url", help="change the remote URL we clone Calamares from.")
    args = parser.parse_args()

    if not args.noupdate:
        update_self()

    cwd = os.getcwd()

    message("Backing up Calamares configuration and resources...")
    if os.path.isdir("/usr/share/calamares.backup"):
        os.system("sudo rm -rf /usr/share/calamares.backup")
    os.system("sudo cp -R /usr/share/calamares /usr/share/calamares.backup")
    if os.path.isdir("/etc/calamares.backup"):
        os.system("sudo rm -rf /etc/calamares.backup")
    os.system("sudo cp -R /etc/calamares /etc/calamares.backup")

    if args.noupgrade:
        message("Updating build dependencies but skipping full upgrade...")
    else:
        message("Updating build dependencies and performing full system upgrade...")

    has_icecream = False
    if shutil.which("yaourt"):
        pacman_mirrors()
        message("\tusing yaourt.")
        yaourt_update(args.noupgrade)

        message("Setting up icecream...")
        has_icecream = setup_icecream()
    elif shutil.which("pacman"):
        pacman_mirrors()
        os.system("sudo pacman -Sy --noconfirm --needed --force yaourt || true")
        if shutil.which("yaourt"):
            message("\tusing yaourt.")
            yaourt_update(args.noupgrade)

            message("Setting up icecream...")
            has_icecream = setup_icecream()
        else:
            message("\tusing pacman.")
            pacman_update(args.noupgrade)
    elif shutil.which("apt-get"):
        message("\tusing apt-get.")
        os.system("sudo apt-get -y update")
        if not args.noupgrade:
            os.system("sudo apt-get -q -y upgrade")
        _P = (
            "cmake",
            "git",
            "gettext",
            "qtbase5-dev",
            "qtwebengine5-dev",
            "qtdeclarative5-dev",
            "libqt5svg5-dev",
            "libyaml-cpp-dev",
            "libpolkit-qt5-1-dev",
            "extra-cmake-modules",
            "libkf5parts-dev",
            "libkpmcore-dev",
            "libparted-dev",
            "libatasmart-dev",
            "libboost-dev",
            )
        os.system("sudo apt-get -q -y install " + " ".join(_P))
    else:
        bail("no package manager found.")

    branch = args.branch;
    if not branch:
        branch = "master"

    if os.path.isdir("calamares"):
        if args.nopull:
            message("Clone found, building without pulling...")
            os.chdir("calamares")
        else:
            message("Clone found, checking out " + branch + " branch...")
            os.chdir("calamares")
            os.system("git checkout --track origin/" + branch + " -b " + branch)
            os.system("git checkout " + branch)
            os.system("git pull --rebase")
            os.system("git submodule update")
            os.system("git submodule sync")
        if os.path.isdir("build") and not args.incremental:
            shutil.rmtree("build", ignore_errors=True)
            os.mkdir("build")
        elif not os.path.exists("build"):
            os.mkdir("build")

    else:
        if args.nopull:
            bail("existing clone not found, can't build without pulling.")

        message("Cloning and checking out " + branch + " branch...")
        os.system("git clone %s" % args.url)
        os.chdir("calamares")
        os.system("git checkout --track origin/"+ branch +" -b " + branch)
        os.system("git submodule init")
        os.system("git submodule update")
        os.system("git submodule sync")
        os.mkdir("build")

    if args.incremental:
        message("Will do an incremental build if a previous build exists.")
    else:
        message("Will do a clean build even if a previous build exists.")

    os.chdir("build")

    cpu_count = available_cpu_count()
    if not cpu_count > 0:
        cpu_count = 4

    job_count = cpu_count

    if has_icecream:
        job_count = 32
        message("Found " + str(cpu_count) + " local CPU cores, building with icecream (" + str(job_count) + " simultaneous tasks)...")
    else:
        message("Found " + str(cpu_count) + " local CPU cores, building...")

    os.system("cmake -DCMAKE_BUILD_TYPE=Debug -DCMAKE_INSTALL_PREFIX=/usr -DWITH_PARTITIONMANAGER=1 -DWITH_PYTHONQT=ON .. && " +
              "make -j" + str(job_count) + " && " +
              "sudo make install")
    os.chdir(cwd)

    message("Restoring Calamares configuration and resources...")
    os.system("sudo cp -R /usr/share/calamares.backup/* /usr/share/calamares/")
    os.system("sudo cp -R /etc/calamares.backup/* /etc/calamares/")

    message("Setting up sudo-gdb...")
    setup_sudo_gdb()

    message("Setting up QtCreator configuration...")
    setup_qtcreator()

    message("All done.")
    os.chdir(cwd)
    os.chdir("calamares")
    message("Calamares branch " +
    printout(str(subprocess.check_output(["git", "symbolic-ref", "--short", "HEAD"]).strip())[1:].strip("'"), YELLOW) +
    printout(" is at commit\n    ", WHITE) +
    str(subprocess.check_output(["git", "log", "-1", "--oneline"]).strip())[1:].strip("'"))

if __name__ == "__main__":
    sys.exit(main())
