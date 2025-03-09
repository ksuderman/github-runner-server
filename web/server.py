from flask import Flask, request, jsonify
import subprocess
import os
import threading
from jinja2 import Template

from pprint import pprint

app = Flask(__name__)

repository_whitelist = ['ksuderman', 'galaxyproject', 'cloudve', 'anvilproject']

# OpenStack configuration
OS_IMAGE = "Featured-Ubuntu24"
OS_NETWORK = "auto_allocated_network"
OS_SECURITY_GROUP = "exosphere"
OS_KEY_NAME = "ks-cluster"
OS_FLAVOR = "m3.large"

def render_template(template, values):
    if not os.path.exists(template):
        print(f"ERROR: Template not found: {template}")
        return
    with open(template, "r") as f:
        t = Template(f.read())
    return t.render(**values)


def generate_runner_init_script(id_value, repo, owner, labels=None):
    # Get the GitHub personal access token from the github.token file
    with open("/home/ubuntu/github-webhook-server/github.token", "r") as token_file:
        github_token = token_file.read().strip()
    # Read the runnin-init.sh template
    with open("../runner-init.sh.j2", "r") as template_file:
        template = template_file.read()
    # Replace the placeholders with the actual values
    values = {
        "token": github_token,
        "owner": owner,
        "repo": repo,
        "vm": id_value,
        "labels": labels,
    }
    script = render_template(template, values)
    # script = template.replace("__GITHUB_TOKEN__", github_token)
    # script = script.replace("__GITHUB_OWNER__", owner)
    # script = script.replace("__GITHUB_REPO__", repo)
    # script = script.replace("__VM_NAME__", id_value)
    # if labels is not None:
    #     label = ",".join(labels)
    #     script = script.replace("__LABELS__", label)
    # Write the script to a file and return the file name
    filename = f"{id_value}.sh"
    with open(filename, "w") as script_file:
        script_file.write(script)
    return filename


@app.route("/", methods=["GET"])
def index():
    return "Hello, World!"

@app.route("/webhook", methods=["POST"])
def github_webhook():
    data = request.json
    #pprint(data)
    action = data.get("action")
    if action == "queued":
        runner_label = data["workflow_job"]["labels"]

        # Check if the job requires a self-hosted runner
        label=None
        if "self-hosted" in runner_label:
            fullname = data["repository"]["full_name"]
            owner, repo = fullname.split("/")
            if owner not in repository_whitelist:
                return jsonify({"message": "Invalid repository"}), 403
            if "8core" in runner_label:
                OS_FLAVOR = "m3.medium"
            elif "16core" in runner_label:
                OS_FLAVOR = "m3.large"
            elif "32core" in runner_label:
                OS_FLAVOR = "m3.xl"
            elif "64core" in runner_label:
                OS_FLAVOR = "m3.2xl"
            else:
                OS_FLAVOR = "m3.medium"

            # Generate a random name for the job runner to prevent name conflicts if
            # multiple jobs are queued at the same time
            runner_name = f"github-runner-{os.urandom(2).hex()}-{os.urandom(2).hex()}"

            print(f"Spawning OpenStack {OS_FLAVOR} VM for GitHub Actions runner {runner_name}")
            init_script = generate_runner_init_script(runner_name, repo, runner_label)
            # OpenStack command to launch a VM
            command = f"""
            openstack server create --image {OS_IMAGE} --flavor {OS_FLAVOR} \
                --network {OS_NETWORK} --security-group {OS_SECURITY_GROUP} \
                --key-name {OS_KEY_NAME} --user-data {init_script} {runner_name}
            """
            subprocess.run(command, shell=True)
            os.remove(init_script)
            return jsonify({"message": "Runner VM spawned"}), 200
    return jsonify({"message": "No action taken"}), 200

@app.route("/cleanup/<runner_id>", methods=["DELETE"])
def cleanup_runner(runner_id):
    print(f"Received a cleanup request for runner VM {runner_id}")
    # Start a thread that waits 30 seconds and then deletes the runner VM
    def _threaded_cleanup():
        import time
        try:
            # Give the runner time to deregister itself and shut down.
            time.sleep(30)
            print(f"Cleaning up runner VM {runner_id}...")
            subprocess.run(f"openstack server delete {runner_id}", shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error deleting server: {e}")
            print("Error output:", e.stderr)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
    t = threading.Thread(target=_threaded_cleanup)
    t.start()
    return jsonify({"message": f"Runner VM {runner_id} scheduled for deletion"}), 200

def test():
    values = {
        "token": "badf00d",
        "owner": "ksuderman",
        "repo": "examble",
        "vm": "foo",
        "labels": "self-hosted,8core",
    }
    script = render_template("runner-init.sh.j2", values)
    print(script)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    # test()