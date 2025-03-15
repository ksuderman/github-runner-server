#!/usr/bin/env bash
ID=$1
prefix="ks-github-$(cat /dev/urandom | tr -dc 'a-z0-9' | head -c 8)"
anvil cluster disks galaxy --prefix $prefix
mkdir /tmp/$ID
cp /root/.kube/config /tmp/$ID/kubeconfig
kubectl get svc -n galaxy galaxy -o jsonpath='{.status.loadBalancer.ingress[0].ip}:{.spec.ports[0].port}' > /tmp/$ID/ip
echo $prefix > /tmp/$ID/prefix
