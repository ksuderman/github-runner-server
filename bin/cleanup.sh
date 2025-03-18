#!/usr/bin/env bash

set -eu

if [[ ! -e /var/chroot/$1 ]]; then
  echo "No such chroot: $1"
  exit 1
fi
if [[ -e /run/chroot/$1/prefix ]]; then
  prefix=$(cat /run/chroot/$1/prefix)
  echo "Deleting cluster $prefix"
  anvil cleanup delete-disks --prefix $prefix
else
  echo "Unable to delete cluster. No prefix found for $1"
fi
for d in $(cat /home/ubuntu/github-webhook-server/bin//MOUNTS) ; do
  sudo umount /var/chroot/$1/$d
done
sudo rm -r /var/chroot/$1

if [[ -e /run/chroot/$1 ]]; then
  sudo rm -rf /run/chroot/$1
fi

