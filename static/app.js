// Convert GitHub URL → raw.githubusercontent.com URL
function convertToRawUrl(repoUrl) {
  try {
    const u = new URL(repoUrl);

    if (u.hostname === "github.com") {
      // pattern: /owner/repo or /owner/repo/
      const parts = u.pathname.split("/").filter(Boolean);
      const owner = parts[0];
      const repo = parts[1];

      // assume cookiecutter.json is in root
      return `https://raw.githubusercontent.com/${owner}/${repo}/main/cookiecutter.json`;
    }
  } catch (e) {
    console.warn("Invalid URL", e);
  }
  return repoUrl;
}

// Fetch cookiecutter.json
async function fetchCookiecutterJson(rawUrl) {
  try {
    const res = await fetch(rawUrl);
    if (!res.ok) return null;
    return await res.json();
  } catch (e) {
    console.warn("Failed to fetch cookiecutter.json", e);
    return null;
  }
}

// Build input element for each cookiecutter field
function buildInput(key, value) {
  const wrapper = document.createElement("div");
  wrapper.style.marginTop = "16px";

  const label = document.createElement("label");
  label.textContent = key;
  label.style.fontWeight = "600";

  const input = document.createElement("input");
  input.type = "text";
  input.name = key;
  input.value = typeof value === "string" ? value : "";

  wrapper.appendChild(label);
  wrapper.appendChild(input);
  return wrapper;
}

// Load cookiecutter.json and populate form
async function loadForm() {
  const templateUrl = document.getElementById("templateUrl").value.trim();
  if (!templateUrl) return;

  const rawUrl = convertToRawUrl(templateUrl);
  const json = await fetchCookiecutterJson(rawUrl);

  const form = document.getElementById("dynamicForm");
  form.innerHTML = "";

  if (!json) {
    const label = document.createElement("label");
    label.textContent = "extra_context (JSON)";

    const textarea = document.createElement("textarea");
    textarea.id = "extra_context";
    textarea.rows = 8;
    textarea.placeholder = '{"project_name": "my_app"}';

    form.appendChild(label);
    form.appendChild(textarea);
    return;
  }

  Object.entries(json).forEach(([key, value]) => {
    form.appendChild(buildInput(key, value));
  });
}

// On page load
window.addEventListener("DOMContentLoaded", () => {
  const templateUrlInput = document.getElementById("templateUrl");
  templateUrlInput.addEventListener("change", loadForm);

  // Generate ZIP handler
  document.getElementById("generateBtn").addEventListener("click", async () => {
    const status = document.getElementById("status");
    status.textContent = "Generating project…";

    const templateUrl = document.getElementById("templateUrl").value.trim();
    if (!templateUrl) {
      alert("Please enter a template URL first!");
      return;
    }

    const form = document.getElementById("dynamicForm");
    const data = { template_url: templateUrl };

    const inputs = form.querySelectorAll("input");
    if (inputs.length > 0) {
      data.extra_context = {};
      inputs.forEach((i) => (data.extra_context[i.name] = i.value));
    } else {
      const ta = document.getElementById("extra_context");
      if (ta.value.trim()) {
        try {
          data.extra_context = JSON.parse(ta.value);
        } catch (e) {
          alert("Invalid JSON in extra_context");
          return;
        }
      } else {
        data.extra_context = {};
      }
    }

    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      if (!res.ok) {
        status.textContent = "Error: " + (await res.text());
        return;
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = "project.zip";
      document.body.appendChild(a);
      a.click();
      a.remove();

      URL.revokeObjectURL(url);

      status.textContent = "Download complete.";
    } catch (err) {
      console.error(err);
      status.textContent = "Generation failed: " + err.message;
    }
  });
});
