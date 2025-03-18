#!/usr/bin/env bash
set -eu
ID=$1
DIR=/run/chroot/$ID
mkdir $DIR
status_file=$DIR/status
prefix="ks-github-$(cat /dev/urandom | tr -dc 'a-z0-9' | head -c 8)"
echo -n $prefix > $DIR/prefix
echo -n "Creating cluster" > $status_file
anvil cluster  --prefix $prefix
echo -m "Creating disks" > $status_file
anvil disks --prefix $prefix
echo -n "Installing Galaxy" > $status_file
anvil galaxy --prefix $prefix
cp /root/.kube/config $DIR/kubeconfig
chown ubuntu:ubuntu $DIR/kubeconfig
service=$(kubectl get svc -n galaxy | grep nginx | awk '{print $1}')
ip=$(kubectl get svc -n galaxy $service -o jsonpath='{.status.loadBalancer.ingress[0].ip}:{.spec.ports[0].port}')
echo -n $ip > $DIR/ip
echo -n f"http://{ip}/galaxy" > $DIR/url
echo -n "Ready" > $status_file