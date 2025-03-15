#!/usr/bin/env bash
set -eu

id=$1
root=/var/chroot
dir=$root/$id
echo "Starting chroot $dir"
mkdir -p $dir
for d in $(cat $root/MOUNTS) ; do
  mkdir $dir/$d
  mount --bind /$d $dir/$d
done
cp /var/chroot/install-galaxy.sh $dir/
chroot $dir install-galaxy.sh $id
#for d in $(cat MOUNTS) ; do
#  umount $dir/$d
#done
#rm -rf $dir
