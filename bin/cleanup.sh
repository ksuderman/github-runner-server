#!/usr/bin/env bash

set -eu

if [[ ! -e /var/chroot/$1 ]]; then
  echo "No such chroot: $1"
  exit 1
fi
for d in $(cat /var/chroot/MOUNTS) ; do
  sudo umount /var/chroot/$1/$d
done
sudo rm -rf /var/chroot/$1
