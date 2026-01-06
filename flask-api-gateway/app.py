from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

ODK_BASE = "https://odk.zanzibar.openg2p.org"

# Get token from env
ODK_BEARER_TOKEN = os.getenv("ODK_BEARER_TOKEN", "")

@app.route("/v1/sessions", methods=["POST"])
def login():
    data = request.json
    headers = {
        "Content-Type": "application/json"
    }
    resp = requests.post(f"{ODK_BASE}/v1/sessions", json=data, headers=headers, verify=True)
    return jsonify(resp.json()), resp.status_code

@app.route("/v1/projects/<int:project_id>/forms/<form_id>/submissions", methods=["GET", "POST"])
def submissions(project_id, form_id):
    method = request.method
    headers = {
        "Authorization": f"Bearer {ODK_BEARER_TOKEN}"
    }

    url = f"{ODK_BASE}/v1/projects/{project_id}/forms/{form_id}/submissions"

    if method == "GET":
        resp = requests.get(url, headers=headers, params=request.args, verify=True)
    else:
        resp = requests.post(url, headers=headers, json=request.json, verify=True)

    return jsonify(resp.json()), resp.status_code

@app.route("/v1/projects/<int:project_id>/forms/<form_id>/submissions/<submission_id>", methods=["GET"])
def submission_detail(project_id, form_id, submission_id):
    headers = {
        "Authorization": f"Bearer {ODK_BEARER_TOKEN}"
    }
    url = f"{ODK_BASE}/v1/projects/{project_id}/forms/{form_id}/submissions/{submission_id}"
    resp = requests.get(url, headers=headers, verify=True)
    return resp.content, resp.status_code, resp.headers.items()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
