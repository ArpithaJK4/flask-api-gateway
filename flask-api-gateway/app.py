from flask import Flask, request, jsonify, Response
import requests
import os
import re

app = Flask(__name__)

ODK_BASE = "https://odk.zanzibar.openg2p.org"


# -----------------------------
# Helper function for auth
# -----------------------------
def get_auth_headers():
    """
    Get authentication from either Cookie or Authorization header.
    Returns a dict with the appropriate header for forwarding to ODK.
    """
    auth_cookie = request.headers.get("Cookie")
    auth_bearer = request.headers.get("Authorization")
    
    if auth_cookie:
        return {"Cookie": auth_cookie}
    elif auth_bearer:
        return {"Authorization": auth_bearer}
    else:
        return None


# -----------------------------
# Health check
# -----------------------------
@app.route("/health")
def health():
    return {"status": "ok"}, 200


# -----------------------------
# Login
# -----------------------------
@app.route("/v1/sessions", methods=["POST"])
def login():
    try:
        resp = requests.post(
            f"{ODK_BASE}/v1/sessions",
            json=request.json,
            headers={"Content-Type": "application/json"},
            verify=True
        )
        # Forward response (including cookies) to client
        response = Response(resp.content, status=resp.status_code)
        # Copy all Set-Cookie headers from ODK
        if "set-cookie" in resp.headers:
            response.headers["Set-Cookie"] = resp.headers["set-cookie"]
        return response
    except Exception as e:
        return {"error": str(e)}, 502


# -----------------------------
# List submissions
# -----------------------------
@app.route("/v1/projects/3/forms/zups_beneficiary_form/submissions", methods=["GET"])
def list_submissions():
    auth = get_auth_headers()
    if not auth:
        return {"error": "Authorization missing (provide Cookie or Authorization header)"}, 401

    try:
        resp = requests.get(
            f"{ODK_BASE}/v1/projects/3/forms/zups_beneficiary_form/submissions",
            headers=auth,
            params=request.args,
            verify=True
        )
        return Response(resp.content, status=resp.status_code, content_type=resp.headers.get("Content-Type"))
    except Exception as e:
        return {"error": str(e)}, 502


# -----------------------------
# Single submission (supports .xml suffix)
# -----------------------------
@app.route("/v1/projects/3/forms/zups_beneficiary_form/submissions/<submission_id>", methods=["GET"])
def single_submission(submission_id):
    auth = get_auth_headers()
    if not auth:
        return {"error": "Authorization missing (provide Cookie or Authorization header)"}, 401

    try:
        resp = requests.get(
            f"{ODK_BASE}/v1/projects/3/forms/zups_beneficiary_form/submissions/{submission_id}",
            headers=auth,
            verify=True
        )
        return Response(resp.content, status=resp.status_code, content_type=resp.headers.get("Content-Type"))
    except Exception as e:
        return {"error": str(e)}, 502


# -----------------------------
# GET attachment (images/files)
# -----------------------------
@app.route("/v1/projects/3/forms/zups_beneficiary_form/submissions/<submission_id>/attachments/<filename>", methods=["GET"])
def get_attachment(submission_id, filename):
    auth = get_auth_headers()
    if not auth:
        return {"error": "Authorization missing (provide Cookie or Authorization header)"}, 401

    try:
        resp = requests.get(
            f"{ODK_BASE}/v1/projects/3/forms/zups_beneficiary_form/submissions/{submission_id}/attachments/{filename}",
            headers=auth,
            verify=True,
            stream=True
        )
        
        # Forward the response with appropriate content type
        return Response(
            resp.content,
            status=resp.status_code,
            content_type=resp.headers.get("Content-Type", "application/octet-stream")
        )
    except Exception as e:
        return {"error": str(e)}, 502


# -----------------------------
# POST submission (XML + attachments)
# -----------------------------
@app.route("/v1/projects/3/forms/zups_beneficiary_form/submissions", methods=["POST"])
def post_submission():
    auth = get_auth_headers()
    if not auth:
        return {"error": "Authorization missing (provide Cookie or Authorization header)"}, 401

    try:
        # Check if request is multipart/form-data
        if request.content_type and request.content_type.startswith("multipart/form-data"):
            files = {}
            xml_file = None
            for key in request.files:
                f = request.files[key]
                if key == "xml_submission_file":
                    xml_file = (f.filename, f.read(), f.content_type)
                else:
                    files[key] = (f.filename, f.read(), f.content_type)

            if not xml_file:
                return {"error": "Missing xml_submission_file"}, 400

            # Step 1: Submit XML
            resp = requests.post(
                f"{ODK_BASE}/v1/projects/3/forms/zups_beneficiary_form/submissions",
                files={"xml_submission_file": xml_file},
                headers=auth,
                verify=True
            )
            if resp.status_code >= 400:
                return Response(resp.content, status=resp.status_code)

            # Extract instanceID from XML
            xml_content = xml_file[1].decode("utf-8")
            instance_match = re.search(r"<instanceID>([^<]+)</instanceID>", xml_content)
            if not instance_match:
                return {"error": "Cannot find instanceID in XML"}, 400
            instance_id = instance_match.group(1)

            # Step 2: Upload attachments
            for key, value in files.items():
                attachment_headers = {**auth, "Content-Type": value[2]}
                requests.post(
                    f"{ODK_BASE}/v1/projects/3/forms/zups_beneficiary_form/submissions/{instance_id}/attachments/{value[0]}",
                    data=value[1],
                    headers=attachment_headers,
                    verify=True
                )

            return Response(resp.content, status=resp.status_code)

        else:
            # Plain XML
            xml_data = request.data
            xml_headers = {**auth, "Content-Type": "application/xml"}
            resp = requests.post(
                f"{ODK_BASE}/v1/projects/3/forms/zups_beneficiary_form/submissions",
                data=xml_data,
                headers=xml_headers,
                verify=True
            )
            return Response(resp.content, status=resp.status_code)
    except Exception as e:
        return {"error": str(e)}, 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)