# api/generate.py
# Fully Vercel-Compatible Cookiecutter Generator

import os
import shutil
import uuid
import zipfile
import requests
from pathlib import Path
from flask import Flask, request, send_file, Response
from cookiecutter.main import cookiecutter
from http import HTTPStatus

app = Flask(__name__)

TMP_ROOT = "/tmp"

@app.route("/api/generate", methods=["POST"])
def generate():
    payload = request.get_json(force=True)

    template_url = payload.get("template_url")
    extra_context = payload.get("extra_context") or {}

    if not template_url:
        return Response("`template_url` is required", status=HTTPStatus.BAD_REQUEST)

    # Create isolated workspace inside /tmp
    work_id = str(uuid.uuid4())
    workdir = os.path.join(TMP_ROOT, f"w_{work_id}")
    templatedir = os.path.join(workdir, "template")
    outdir = os.path.join(workdir, "output")
    zip_path = os.path.join(workdir, "project.zip")

    os.makedirs(templatedir, exist_ok=True)
    os.makedirs(outdir, exist_ok=True)

    try:
        # ------------------------------------------------------
        # 1. Convert GitHub repo URL → ZIP download URL
        # ------------------------------------------------------
        # Supports both:
        # https://github.com/user/repo
        # https://github.com/user/repo.git
        base = template_url.rstrip("/").replace(".git", "")
        zip_url = base + "/archive/refs/heads/main.zip"

        # ------------------------------------------------------
        # 2. Download ZIP into /tmp
        # ------------------------------------------------------
        zip_file = os.path.join(workdir, "template.zip")
        r = requests.get(zip_url)
        if r.status_code != 200:
            return Response(f"Cannot download template ZIP from {zip_url}", status=500)

        with open(zip_file, "wb") as f:
            f.write(r.content)

        # ------------------------------------------------------
        # 3. Unzip into /tmp/template
        # ------------------------------------------------------
        shutil.unpack_archive(zip_file, templatedir)

        # Find root folder inside extracted template
        inner_folders = os.listdir(templatedir)
        if not inner_folders:
            return Response("Bad template: ZIP is empty", 500)

        template_root = os.path.join(templatedir, inner_folders[0])

        # ------------------------------------------------------
        # 4. Run cookiecutter non-interactively (no git required)
        # ------------------------------------------------------
        cookiecutter(
            template_root,
            no_input=True,
            extra_context=extra_context,
            output_dir=outdir
        )

        # ------------------------------------------------------
        # 5. Zip the generated project
        # ------------------------------------------------------
        generated = os.listdir(outdir)
        if not generated:
            return Response("Cookiecutter produced no files", 500)

        project_folder = os.path.join(outdir, generated[0])

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for root, dirs, files in os.walk(project_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, outdir)
                    z.write(file_path, arcname)

        # ------------------------------------------------------
        # 6. Return the zip
        # ------------------------------------------------------
        return send_file(
            zip_path,
            mimetype="application/zip",
            as_attachment=True,
            download_name="project.zip"
        )

    except Exception as e:
        return Response(str(e), 500)
