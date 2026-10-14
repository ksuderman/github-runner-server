# GitHub Webhook Server

A small Flask application that provisions cloud infrastructure on demand. It has two independent features:

1. **GitHub Actions runners on Jetstream2.** GitHub sends a `workflow_job` webhook when a job is queued. The server launches a Jetstream2 (OpenStack) VM that registers itself as an ephemeral self-hosted runner, runs the single job, deregisters, and shuts itself down.
2. **Galaxy clusters on GKE (the `anvil` API).** An authenticated REST API that creates a Google Kubernetes Engine cluster, installs Galaxy with the `galaxykubeman` Helm chart, reports the status and URL of the deployment, and tears everything down on request.

## Repository layout

| Path | Purpose |
|------|---------|
| `web/server.py` | The Flask application. Served by Gunicorn on port 5000. |
| `runner-init.sh.j2` | Jinja2 template for the `cloud-init` script passed to new Jetstream2 runner VMs. |
| `templates/anvil-values.yml.j2` | Jinja2 template for the Helm values file used when installing Galaxy on GKE. |
| `gunicorn.service` | systemd unit for the Flask application. |
| `watcher.service` | systemd unit for the background process that creates and destroys GKE clusters. |
| `bin/setup.sh` | One time server setup: creates directories, installs `gcloud`, `kubectl`, and `helm`, and installs the systemd units. |
| `bin/watcher.sh` | Polls `/run/jobs/create` and `/run/jobs/shutdown` for work queued by the API. |
| `bin/install-galaxy.sh` | Runs inside a chroot to create a cluster, create disks, and install Galaxy. |
| `bin/cleanup.sh` | Deletes a cluster and its disks. |
| `bin/anvil` | Command line tool that wraps `gcloud`, `kubectl`, and `helm` to provision an AnVIL style Galaxy cluster. |
| `bin/timer.sh` | Helper sourced by `bin/anvil` to report elapsed time. |
| `bin/MOUNTS` | List of host directories bind mounted into each chroot. |
| `bin/start`, `bin/stop`, `bin/status`, `bin/bounce` | Convenience wrappers around `systemctl` for the Gunicorn service. `bounce` also pulls the latest code. |

## Requirements

The server can be any Linux host that is reachable from the internet. It does not need to run on Jetstream2 and a single core VM is sufficient. The instructions below assume Ubuntu with a user named `ubuntu`. All paths in the code and systemd units are hardcoded to `/home/ubuntu/github-webhook-server`, so clone the repository to that location.

You will need:

- Python 3.12 or later.
- For the Jetstream2 runner feature: the `openstack` command line client and an `openrc.sh` file for your Jetstream2 allocation.
- For the `anvil` feature: a Google Cloud project with GKE enabled and credentials for an account that can create clusters and disks. The `bin/setup.sh` script installs `gcloud`, `kubectl`, and `helm`.

## Installation

1. Clone the repository to the expected location.

   ```bash
   git clone https://github.com/ksuderman/github-runner-server.git /home/ubuntu/github-webhook-server
   cd /home/ubuntu/github-webhook-server
   ```

2. Create a virtual environment and install the Python dependencies. The systemd unit expects the virtual environment at `/home/ubuntu/github-webhook-server/.venv`.

   ```bash
   python3 -m venv .venv
   .venv/bin/pip install flask gunicorn jinja2 python-openstackclient
   ```

3. Run the setup script as root. It creates the working directories, installs the Google Cloud tooling, adds the `anvil` Helm repository, copies `bin/anvil` and `bin/timer.sh` to `/usr/local/bin`, copies the Helm values template to `/etc/templates`, and installs both systemd units.

   ```bash
   sudo bin/setup.sh
   ```

   If you only need the Jetstream2 runner feature you can skip this step and copy `gunicorn.service` to `/etc/systemd/system` by hand.

4. Create the secrets the server reads at runtime. Neither file should be committed to version control.

   | File | Contents |
   |------|----------|
   | `/home/ubuntu/github-webhook-server/github.token` | A GitHub Personal Access Token with the `repo` scope. Add `admin:org` if runners will be registered at the organization level. Used to request runner registration tokens. |
   | `/home/ubuntu/github-webhook-server/server.token` | An arbitrary secret string. Clients must send it in the `api-token` header when calling the `anvil` endpoints. |
   | `/root/openstack-rc.sh` | The `OS_*` environment variables from the `openrc.sh` file provided by Jetstream2. Loaded by `gunicorn.service` through `EnvironmentFile`. |

   Generate a server token with, for example:

   ```bash
   openssl rand -hex 32 > /home/ubuntu/github-webhook-server/server.token
   ```

   The `EnvironmentFile` directive does not run a shell, so `/root/openstack-rc.sh` must contain plain `KEY=value` lines without `export` or command substitution. If your `openrc.sh` prompts for a password, put the password in the file as `OS_PASSWORD=...`.

5. Authenticate `gcloud` as root if you are using the `anvil` feature. The watcher runs as root and copies `/root/.config`, `/root/.ssh`, and `/root/.cache` into each chroot so the tools inside have credentials.

   ```bash
   sudo gcloud auth login
   sudo gcloud config set project YOUR_PROJECT
   ```

6. Enable and start the services.

   ```bash
   sudo systemctl enable --now gunicorn
   sudo systemctl enable --now watcher   # anvil feature only
   ```

   Check that the server is up:

   ```bash
   curl http://localhost:5000/
   ```

7. Open port 5000 in the host firewall or security group so GitHub and API clients can reach the server.

## Feature 1: GitHub Actions runners on Jetstream2

### How it works

1. GitHub POSTs a [workflow_job](https://docs.github.com/en/webhooks/webhook-events-and-payloads#workflow_job) payload to `/webhook`.
2. If the action is `queued` and the job's labels include `self-hosted`, the server checks that the repository owner is in the allow list. Requests from other owners are rejected with HTTP 403.
3. The server renders `runner-init.sh.j2` with the GitHub token, repository owner and name, a random VM name, and the job's labels, and launches an OpenStack VM with the rendered script as `user-data`.
4. On boot the VM installs the [GitHub Actions Runner](https://github.com/actions/runner), requests a registration token from the GitHub API, registers as an ephemeral runner with the job's labels, and runs `run.sh`.
5. Because the runner is ephemeral it picks up exactly one job. When the job finishes the runner deregisters itself and the VM shuts down.

### Configuring the webhook in GitHub

In the repository or organization settings, go to **Settings > Webhooks > Add webhook** and use:

| Setting | Value |
|---------|-------|
| Payload URL | `http://YOUR_SERVER:5000/webhook` |
| Content type | `application/json` |
| Events | Select **Let me select individual events** and check **Workflow jobs** only |

### Allowed repositories

Only repositories owned by the accounts in the `repository_whitelist` list at the top of `web/server.py` are served. Edit that list to add your own user or organization and restart the Gunicorn service.

### Selecting a VM size

Add one of the following labels to the `runs-on` list in your workflow to choose the VM flavor. Jobs with no size label get `m3.medium`.

| Label | Jetstream2 flavor |
|-------|-------------------|
| `8core` | `m3.medium` |
| `16core` | `m3.large` |
| `32core` | `m3.xl` |
| `64core` | `m3.2xl` |

The image, network, security group, and SSH key name used for new VMs are set in the `OS_*` constants at the top of `web/server.py`. The runner version is set by `DOWNLOAD_URL` in `runner-init.sh.j2`.

### Example workflow

```yaml
jobs:
  build:
    runs-on: [self-hosted, 16core]
    steps:
      - uses: actions/checkout@v4
      - run: make test
```

### Deleting a VM manually

The runner VM normally shuts itself down. To remove a VM by name through the server:

```bash
curl -X DELETE http://YOUR_SERVER:5000/cleanup/github-runner-abcd-1234
```

The server waits 30 seconds and then runs `openstack server delete` for that name.

## Feature 2: Galaxy clusters on GKE (the anvil API)

### How it works

The Flask application never calls `gcloud` directly. Each API call writes a marker file that `bin/watcher.sh`, running as root, picks up on its 30 second polling loop.

1. `POST /anvil` generates a UUID, writes it to `/run/jobs/create/<id>`, and returns the id.
2. The watcher creates `/var/chroot/<id>`, copies root's `gcloud`, SSH, and cache directories into it, bind mounts the directories listed in `bin/MOUNTS`, and runs `bin/install-galaxy.sh` inside the chroot. A chroot is used so each job gets its own `~/.kube/config` and does not interfere with concurrent jobs.
3. `install-galaxy.sh` picks a random cluster prefix and runs `anvil cluster`, `anvil disks`, and `anvil galaxy`. As it progresses it writes `status`, `prefix`, `kubeconfig`, `ip`, and `url` files to `/run/chroot/<id>`. The status moves through `Creating cluster`, `Creating disks`, `Installing Galaxy`, and finally `Ready`.
4. `GET /anvil/<name>?id=<id>` returns the contents of `/run/chroot/<id>/<name>`.
5. `DELETE /anvil?id=<id>` writes `/run/jobs/shutdown/<id>`. The watcher runs `bin/cleanup.sh`, which sets the status to `Deleting`, deletes the cluster and disks, and removes `/run/chroot/<id>`.

Provisioning a cluster and installing Galaxy typically takes 10 to 20 minutes. Poll the `status` endpoint until it returns `Ready`.

### Endpoints

All `anvil` endpoints require the `api-token` header. Its value must match the contents of `server.token`.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/anvil` | Queue a new cluster. Returns `{"status": "queued", "id": "<uuid>"}`. |
| `GET` | `/anvil/status?id=<id>` | Current status string. |
| `GET` | `/anvil/url?id=<id>` | The Galaxy URL once the status is `Ready`. |
| `GET` | `/anvil/ip?id=<id>` | The `ip:port` of the Galaxy ingress. |
| `GET` | `/anvil/prefix?id=<id>` | The prefix used to name the GKE cluster and disks. |
| `GET` | `/anvil/kubeconfig?id=<id>` | The kubeconfig for the cluster. |
| `DELETE` | `/anvil?id=<id>` | Queue the cluster for deletion. |

A `GET` for a file that has not been written yet returns HTTP 404. A missing or wrong token returns HTTP 400 or 401 respectively. All errors are returned as JSON.

### Example session

```bash
SERVER=http://YOUR_SERVER:5000
TOKEN=$(cat server.token)

# Create a cluster and capture its id
ID=$(curl -s -X POST -H "api-token: $TOKEN" $SERVER/anvil | jq -r .id)

# Poll until Galaxy is ready
until [[ $(curl -s -H "api-token: $TOKEN" "$SERVER/anvil/status?id=$ID" | jq -r .status) == "Ready" ]]; do
  sleep 60
done

# Get the URL and kubeconfig
curl -s -H "api-token: $TOKEN" "$SERVER/anvil/url?id=$ID" | jq -r .url
curl -s -H "api-token: $TOKEN" "$SERVER/anvil/kubeconfig?id=$ID" | jq -r .kubeconfig > kubeconfig.yml

# Tear everything down
curl -s -X DELETE -H "api-token: $TOKEN" "$SERVER/anvil?id=$ID"
```

### Customizing the Galaxy deployment

The cluster size, GKE version, zone, Galaxy image, and Helm chart are controlled by variables and options in `bin/anvil`. Run `anvil help` for the full list. The Helm values are rendered from `/etc/templates/anvil-values.yml.j2`. Edit the copy in `templates/` and rerun `bin/setup.sh`, or copy it to `/etc/templates` by hand, to change the deployment.

The `anvil` script can also be used directly from a shell to create and destroy clusters outside the web server:

```bash
anvil --prefix my-test cluster disks galaxy
anvil --prefix my-test cleanup delete-disks
```

## Operations

```bash
bin/status     # systemctl status gunicorn
bin/stop       # stop the web server
bin/start      # start the web server
bin/bounce     # stop, git pull, start
sudo journalctl -u gunicorn -f   # web server logs
sudo journalctl -u watcher -f    # cluster provisioning logs
```

The chroot directories under `/var/chroot/<id>` are not removed automatically after a cluster is deleted. Unmount the bind mounts listed in `bin/MOUNTS` before removing a chroot directory, otherwise `rm -rf` will delete files on the host.

## Running locally for development

```bash
cd web
../.venv/bin/python server.py
```

The development server listens on port 5000. Note that the token and template paths are hardcoded to `/home/ubuntu/github-webhook-server`, so the webhook and `anvil` endpoints will fail unless those files exist.

## License

See [LICENSE](LICENSE).
