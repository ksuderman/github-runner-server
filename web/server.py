from flask import Flask, request, jsonify
import subprocess
import os

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

def generate_runner_init_script():
    # Get the GitHub personal access token from the github.token file
    with open("github.token", "r") as token_file:
        github_token = token_file.read().strip()
    # Read the runnin-init.sh template
    with open("runner-init.sh.template", "r") as template_file:
        template = template_file.read()
    # Replace the placeholder with the actual GitHub token
    script = template.replace("__GITHUB_TOKEN__", github_token)
    # Write the script to a file
    with open("runner-init.sh", "w") as script_file:
        script_file.write(script)


@app.route("/webhook", methods=["POST"])
def github_webhook():
    data = request.json
    print(jsonify(data))
    action = data.get("action")
    if action == "queued":
        runner_label = data["workflow_job"]["labels"]

        # Check if the job requires a self-hosted runner
        if "self-hosted" in runner_label:
            print("Spawning OpenStack VM for GitHub Actions runner...")

            # OpenStack command to launch a VM
            command = f"""
            openstack server create --image {OS_IMAGE} --flavor {OS_FLAVOR} \
                --network {OS_NETWORK} --security-group {OS_SECURITY_GROUP} \
                --key-name {OS_KEY_NAME} --user-data runner-init.sh github-runner
            """
            subprocess.run(command, shell=True)
            return jsonify({"message": "Runner VM spawned"}), 200
    return jsonify({"message": "No action taken"}), 200

if __name__ == "__main__":
    generate_runner_init_script()
    app.run(host="0.0.0.0", port=5000)
