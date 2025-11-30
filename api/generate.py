# api/generate.py
# Vercel-Compatible Python Serverless Function (WSGI with Flask)

import os
import tempfile
import shutil
import zipfile
from pathlib import Path
from http import HTTPStatus

from flask import Flask, request, send_file, Response
from cookiecutter.main import cookiecutter

app = Flask(__name__)

@app.route("/api/generate", methods=["POST"])
def generate():
    try:
        payload = request.get_json(force=True)
    except Exception:
        return Response("Invalid JSON body", status=HTTPStatus.BAD_REQUEST)

    template_url = payload.get("template_url")
    extra_context = payload.get("extra_context") or {}

    if not template_url:
        return Response("`template_url` is required", status=HTTPStatus.BAD_REQUEST)

    # Create isolated temp directories
    workdir = tempfile.mkdtemp(prefix="genwork_")
    outdir = tempfile.mkdtemp(prefix="genout_")

    try:
        # Run cookiecutter non-interactively
        try:
            cookiecutter(
                template_url,
                no_input=True,
                extra_context=extra_context,
                output_dir=outdir
            )
        except Exception as e:
            return Response(
                "Cookiecutter failed: " + str(e),
                status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        # Identify generated folder(s)
        entries = list(Path(outdir).iterdir())
        if not entries:
            return Response("Cookiecutter produced no files", status=500)

        # Create zip file
        zip_path = Path(workdir) / "project.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for entry in entries:
                if entry.is_dir():
                    for root, dirs, files in os.walk(entry):
                        for file in files:
                            file_path = Path(root) / file
                            arcname = file_path.relative_to(outdir)
                            zf.write(file_path, arcname)
                else:
                    arcname = entry.relative_to(outdir)
                    zf.write(entry, arcname)

        # Send ZIP to client
        return send_file(
            str(zip_path),
            mimetype="application/zip",
            as_attachment=True,
            download_name="project.zip"
        )

    finally:
        # Ensure cleanup
        shutil.rmtree(workdir, ignore_errors=True)
        shutil.rmtree(outdir, ignore_errors=True)


# For development testing (not used in Vercel)
if __name__ == "__main__":
    app.run(port=8000, debug=True)
