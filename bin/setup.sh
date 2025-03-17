#!/usr/bin/env bash
set -eu

if [[ $(id -u) -ne 0 ]]; then
    echo "Please run as root"
    exit 1
fi

for dir in /var/chroot /run/jobs/create /run/jobs/shutdown /run/chroot /etc/templates ; do
  if [[ ! -d $dir ]]; then
      mkdir -p $dir
  fi
done
chown -R ubuntu:ubuntu /run/jobs
cp bin/anvil /usr/local/bin
cp bin/timer.sh /usr/local/bin
cp templates/anvil-values.yml.j2 /etc/templates
cp gunicorn.service /etc/systemd/system
cp watcher.service /etc/systemd/system
systemctl daemon-reload
systemctl enable gunicorn
