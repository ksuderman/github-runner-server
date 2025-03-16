#!/usr/bin/env bash
set -eu
ID=$1
DIR=/run/chroot/$ID
mkdir $DIR
prefix="ks-github-$(cat /dev/urandom | tr -dc 'a-z0-9' | head -c 8)"
echo $prefix > $DIR/prefix
anvil cluster disks galaxy --prefix $prefix
mkdir $DIR
cp /root/.kube/config $DIR/kubeconfig
service=$(kubectl get svc -n galaxy | grep nginx | awk '{print $1}')
kubectl get svc -n galaxy $service -o jsonpath='{.status.loadBalancer.ingress[0].ip}:{.spec.ports[0].port}' > $DIR/ip
