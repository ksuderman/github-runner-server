#!/usr/bin/env bash
set -eu

id=$1
root=/var/chroot
server=/home/ubuntu/github-webhook-server
dir=$root/$id
echo "Starting chroot $dir"
mkdir -p $dir/root
cp -r /root/.config /root/.ssh /root/.cache $dir/root/
for d in $(cat $server/bin/MOUNTS) ; do
  echo "Mounting $dir/$d"
  mkdir $dir/$d
  mount --bind /$d $dir/$d
done
cp $server/bin/install-galaxy.sh $dir/
chroot $dir /install-galaxy.sh $id
for d in $(cat $server/bin/MOUNTS) ; do
  umount $dir/$d
done
rm -rf $dir
