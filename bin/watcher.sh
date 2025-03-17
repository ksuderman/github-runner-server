#!/usr/bin/env bash
set -eu

echo "Staring the Watcher service"
CREATE_DIR=/run/jobs/create
SHUTDOWN_DIR=/run/jobs/shutdown
while true; do
  for job in $(ls $CREATE_DIR); do
    if [[ -e $CREATE_DIR/$job ]]; then
      echo "Launching cluster for job $job"
      rm -f $CREATE_DIR/$job
      /home/ubuntu/github-webhook-server/bin/start-chroot.sh $job &
    fi
  done
  for job in $(ls $SHUTDOWN_DIR); do
    if [[ -e $SHUTDOWN_DIR/$job ]]; then
      echo "Stopping cluster for job $job"
      rm -f $SHUTDOWN_DIR/$job
      /home/ubuntu/github-webhook-server/bin/cleanup.sh $job &
    fi
  done
  sleep 30
done
echo "Stopping the Watcher service"