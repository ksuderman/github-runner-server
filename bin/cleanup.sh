#!/usr/bin/env bash

set -eu

if [[ ! -e /var/chroot/$1 ]]; then
  echo "No such chroot: $1"
  exit 1
fi
if [[ -e /run/$1/prefix ]]; then
  prefix=$(cat /run/$1/prefix)
  echo "Deleting cluster $prefix"
  anvil cleanup delete-disks --prefix $prefix
else
  echo "Unable to delete cluster. No prefix found for $1"
fi
for d in $(cat /var/chroot/MOUNTS) ; do
  sudo umount /var/chroot/$1/$d
done
sudo rm -rf /var/chroot/$1

if [[ -e /run/$1 ]]; then
  sudo rm -rf /run/$1
fi

