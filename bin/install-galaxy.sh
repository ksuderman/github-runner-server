#!/usr/bin/env bash
set -eu
ID=$1
DIR=/run/$ID
prefix="ks-github-$(cat /dev/urandom | tr -dc 'a-z0-9' | head -c 8)"
anvil cluster disks galaxy --prefix $prefix
mkdir $DIR
cp /root/.kube/config $DIR/kubeconfig
kubectl get svc -n galaxy galaxy -o jsonpath='{.status.loadBalancer.ingress[0].ip}:{.spec.ports[0].port}' > $DIR/ip
echo $prefix > $DIR/prefix
