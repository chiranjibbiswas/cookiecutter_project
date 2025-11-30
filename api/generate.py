# api/generate.py
# Vercel Serverless Python (NO FLASK)

import os
import shutil
import uuid
import zipfile
import requests
import base64
import json
from cookiecutter.main import cookiecutter

TMP_ROOT = "/tmp"

def handler(request):
    try:
        payload = request.get_json()

        template_url = payload.get("template_url")
        extra_context = payload.get("extra_context") or {}

        if not template_url:
            return {
                "statusCode": 400,
                "body": "template_url is required"
            }

        # Create workspace
        work_id = str(uuid.uuid4())
        workdir = os.path.join(TMP_ROOT, f"w_{work_id}")
        templatedir = os.path.join(workdir, "template")
        outdir = os.path.join(workdir, "output")
        zip_path = os.path.join(workdir, "project.zip")

        os.makedirs(templatedir, exist_ok=True)
        os.makedirs(outdir, exist_ok=True)

        # Build zip url
        base = template_url.rstrip("/").replace(".git", "")
        zip_url = base + "/archive/refs/heads/main.zip"

        # Download template zip
        zfile = os.path.join(workdir, "template.zip")
        r = requests.get(zip_url)

        if r.status_code != 200:
            return {
                "statusCode": 500,
                "body": f"Failed to download template: {zip_url}"
            }

        with open(zfile, "wb") as f:
            f.write(r.content)

        shutil.unpack_archive(zfile, templatedir)

        # Locate inner folder
        inner = os.listdir(templatedir)
        if not inner:
            return {"statusCode": 500, "body": "Empty template ZIP"}

        template_root = os.path.join(templatedir, inner[0])

        # Run cookiecutter
        cookiecutter(
            template_root,
            no_input=True,
            extra_context=extra_context,
            output_dir=outdir
        )

        # Zip output
        generated = os.listdir(outdir)
        if not generated:
            return {"statusCode": 500, "body": "No files generated"}

        project_folder = os.path.join(outdir, generated[0])

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for root, dirs, files in os.walk(project_folder):
                for file in files:
                    fp = os.path.join(root, file)
                    arcname = os.path.relpath(fp, outdir)
                    z.write(fp, arcname)

        # Read zip as base64 (Vercel requires this)
        with open(zip_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/zip",
                "Content-Disposition": "attachment; filename=project.zip"
            },
            "body": encoded,
            "isBase64Encoded": True
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": "Error: " + str(e)
        }
