from flask import Flask, request, jsonify
import subprocess
import os
import threading
from pprint import pprint

app = Flask(__name__)

# OpenStack credentials (set as environment variables)
OS_IMAGE = "Featured-Ubuntu24"
OS_FLAVOR = "m3.large"
OS_NETWORK = "auto_allocated_network"
OS_SECURITY_GROUP = "exosphere"
OS_KEY_NAME = "ks-cluster"

def get_flavor(cores):
    if cores == 8:
        return "m3.medium"
    elif cores == 16:
        return "m3.large"
    elif cores == 32:
        return "m3.xl"
    elif cores == 64:
        return "m3.2xl"
    else:
        raise ValueError("Unsupported number of cores")

def generate_runner_init_script(id_value, repo, labels=None):
    # Get the GitHub personal access token from the github.token file
    with open("/home/ubuntu/github.token", "r") as token_file:
        github_token = token_file.read().strip()
    # Read the runnin-init.sh template
    with open("../runner-init.sh.template", "r") as template_file:
        template = template_file.read()
    # Replace the placeholder with the actual GitHub token
    script = template.replace("__GITHUB_TOKEN__", github_token)
    script = script.replace("__GITHUB_REPO__", repo)
    script = script.replace("__VM_NAME__", id_value)
    if labels is not None:
        label = ",".join(labels)
        print(f"Adding label {label} to runner")
        script = script.replace("__LABELS__", label)
    filename = f"{id_value}.sh"
    # Write the script to a file
    with open(filename, "w") as script_file:
        script_file.write(script)
        print(f"Wrote init script to {filename}")
        print(script)
    return filename


@app.route("/", methods=["GET"])
def index():
    return "Hello, World!"

@app.route("/webhook", methods=["POST"])
def github_webhook():
    data = request.json
    pprint(data)
    action = data.get("action")
    if action == "queued":
        runner_label = data["workflow_job"]["labels"]

        # Check if the job requires a self-hosted runner
        label=None
        if "self-hosted" in runner_label:
            if "8core" in runner_label:
                OS_FLAVOR = "m3.medium"
                label="8core"
            elif "16core" in runner_label:
                OS_FLAVOR = "m3.large"
                label="16core"
            elif "32core" in runner_label:
                OS_FLAVOR = "m3.xl"
                label="32core"
            elif "64core" in runner_label:
                OS_FLAVOR = "m3.2xl"
                label="64core"
            else:
                OS_FLAVOR = "m3.medium"

            repo=data["repository"]["name"]
            # Generate a name for the job runner
            id_value = f"github-runner-{os.urandom(2).hex()}-{os.urandom(2).hex()}"

            print(f"Spawning OpenStack {OS_FLAVOR} VM for GitHub Actions runner {id_value}")
            init_script = generate_runner_init_script(id_value, repo, runner_label)
            # OpenStack command to launch a VM
            command = f"""
            openstack server create --image {OS_IMAGE} --flavor {OS_FLAVOR} \
                --network {OS_NETWORK} --security-group {OS_SECURITY_GROUP} \
                --key-name {OS_KEY_NAME} --user-data {init_script} {id_value}
            """
            subprocess.run(command, shell=True)
            return jsonify({"message": "Runner VM spawned"}), 200
    return jsonify({"message": "No action taken"}), 200

@app.route("/cleanup/<runner_id>", methods=["DELETE"])
def cleanup_runner(runner_id):
    print(f"Received a cleanup request for runner VM {runner_id}...")
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
