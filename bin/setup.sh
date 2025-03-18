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
apt update
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list
apt update
apt install -y google-cloud-cli google-cloud-cli-gke-gcloud-auth-plugin

curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm repo add anvil https://github.com/cloudve/helm-charts/raw/anvil

git clone --branch chroot https://github.com/ksuderman/github-runner-server.git /home/ubuntu/github-webhook-server
chown -R ubuntu:ubuntu /home/ubuntu/github-webhook-server

cp bin/anvil /usr/local/bin
cp bin/timer.sh /usr/local/bin
cp templates/anvil-values.yml.j2 /etc/templates
cp gunicorn.service /etc/systemd/system
cp watcher.service /etc/systemd/system
systemctl daemon-reload
#systemctl enable gunicorn
