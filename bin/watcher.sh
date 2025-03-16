#!/usr/bin/env bash
set -eu

WATCH_DIR=/run/jobs

while true; do
  for job in $(ls $WATCH_DIR); do
    if [[ -e $WATCH_DIR/$job ]]; then
      echo "Launching cluster for job $job"
      /home/ubuntu/github-webhook-server/bin/start-chroot.sh $job &
      rm -f $WATCH_DIR/$job
    fi
  done
  sleep 30
done