#!/usr/bin/env bash
set -eu

id=$1
root=/var/chroot
dir=$root/$id
echo "Starting chroot $dir"
mkdir -p $dir/root
cp -r /root/.config /root/.ssh $dir/root/
for d in $(cat $root/MOUNTS) ; do
  mkdir $dir/$d
  mount --bind /$d $dir/$d
done
cp $root/install-galaxy.sh $dir/
chroot $dir install-galaxy.sh $id
#for d in $(cat MOUNTS) ; do
#  umount $dir/$d
#done
#rm -rf $dir
