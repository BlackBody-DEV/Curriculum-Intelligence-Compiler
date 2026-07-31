const app = document.querySelector("#app");
const state = { runId: null, assessmentId: null, intakeJobId: null, intakeXhr: null };
const SOURCE_READY_STATUSES = new Set([
  "source_ready",
  "compiling",
  "compiled",
  "assessment_review_pending",
  "assessment_ready",
  "failed",
]);

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  }[char]));
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {"Content-Type": "application/json", ...(options.headers || {})},
  });
  const data = await response.json();
  if (!response.ok || data.error) throw new Error(data.error || response.statusText);
  return data;
}

function render(title, body) {
  app.innerHTML = `<section class="panel"><h2>${esc(title)}</h2>${body}</section>`;
  app.focus();
}

function controls(run) {
  const id = run?.run_id || state.runId || "";
  return `<p class="current">Current run: <strong>${esc(id || "none")}</strong></p>`;
}

function yesNo(value) {
  return value ? "Yes" : "No";
}

function readyToCompile(run) {
  const rightsApproved = run?.rights_status === "approved_local_use" || run?.rights_status === "owned_by_axiomiq";
  return SOURCE_READY_STATUSES.has(run?.status)
    && Boolean(run.source_display_filename)
    && Boolean(run.source_format)
    && Boolean(run.source_sha256)
    && rightsApproved
    && run.privacy_status === "non_private";
}

async function ensureAssessmentId(run = null) {
  if (state.assessmentId) return state.assessmentId;
  const current = run || (state.runId ? await api(`/api/runs/${state.runId}`) : null);
  const ids = current?.assessment_ids || [];
  if (ids.length) {
    state.assessmentId = ids[0];
    return state.assessmentId;
  }
  throw new Error("No assessment is available for the selected run.");
}

function formatBytes(value) {
  const n = Number(value || 0);
  if (!Number.isFinite(n)) return "unknown";
  return String(n);
}

function uploadProgressSummary(job) {
  const received = Number(job.received_bytes || 0);
  const expected = Number(job.expected_source_bytes || job.file_size_bytes || job.declared_upload_bytes || 0);
  const maximum = Number(job.maximum_bytes || 0);
  const uploadComplete = Boolean(job.upload_complete) || (expected > 0 && received >= expected);
  const uploadPercentage = expected > 0
    ? `${Math.min(100, Math.floor(((uploadComplete ? expected : received) / expected) * 100))}%`
    : null;
  const capacityUsed = maximum > 0
    ? `${Math.min(100, Math.floor((received / maximum) * 100))}%`
    : "n/a";
  return {
    uploadComplete,
    uploadPercentage,
    uploadState: uploadPercentage ? null : "indeterminate",
    capacityUsed,
  };
}

function sourceReadySummary(run) {
  if (!run) return "";
  const ready = readyToCompile(run);
  const pdf = run.pdf_validation || {};
  return `
    <div class="${ready ? "success" : "warning"}">
      <h3>${ready ? "Source uploaded successfully" : "Source not ready to compile"}</h3>
      <dl class="summary-grid">
        <dt>Filename</dt><dd>${esc(run.source_display_filename || "none")}</dd>
        <dt>Run ID</dt><dd>${esc(run.run_id || "")}</dd>
        <dt>File size</dt><dd>${esc(formatBytes(pdf.file_size_bytes || run.source_file_size_bytes || "unknown"))}</dd>
        <dt>Page count</dt><dd>${esc(pdf.page_count || "n/a")}</dd>
        <dt>Pages containing text</dt><dd>${esc(pdf.pages_containing_text || "n/a")}</dd>
        <dt>Source SHA-256</dt><dd>${esc(run.source_sha256 || "none")}</dd>
        <dt>Extracted-text SHA-256</dt><dd>${esc(pdf.extracted_text_sha256 || run.extracted_text_sha256 || "n/a")}</dd>
        <dt>Extraction duration</dt><dd>${esc(pdf.processing_duration_seconds ?? "n/a")}</dd>
        <dt>Raw PDF retained</dt><dd>${yesNo(Boolean(run.pdf_validation?.raw_pdf_retained))}</dd>
        <dt>Extracted text retained</dt><dd>${yesNo(run.pdf_validation?.extracted_text_retained ?? run.raw_or_normalized_source_retained)}</dd>
        <dt>Ready to compile</dt><dd>${yesNo(ready)}</dd>
      </dl>
      ${ready ? "" : "<p>Upload Source must persist filename, hash, rights, privacy, and source_ready state before Compile is available.</p>"}
    </div>
  `;
}

function intakeProgressHtml(job, filename) {
  const maxBytes = Number(job.maximum_bytes || 0);
  const received = Number(job.received_bytes || 0);
  const progress = uploadProgressSummary(job);
  const pages = job.page_count == null ? "?" : job.page_count;
  return `
    <div class="success">
      <h3>PDF intake in progress</h3>
      <dl class="summary-grid">
        <dt>Selected filename</dt><dd>${esc(filename || job.display_filename || "")}</dd>
        <dt>Uploaded bytes</dt><dd>${esc(received)}</dd>
        <dt>Maximum bytes</dt><dd>${esc(maxBytes)}</dd>
        ${progress.uploadPercentage
          ? `<dt>Upload percentage</dt><dd>${esc(progress.uploadPercentage)}</dd>`
          : `<dt>Upload state</dt><dd>${esc(progress.uploadState)}</dd>`}
        <dt>Maximum capacity used</dt><dd>${esc(progress.capacityUsed)}</dd>
        <dt>Current stage</dt><dd>${esc(job.current_stage || "")}</dd>
        <dt>Processed pages</dt><dd>${esc(job.processed_page_count || 0)} / ${esc(pages)}</dd>
        <dt>Text-bearing pages</dt><dd>${esc(job.pages_containing_text || 0)}</dd>
        <dt>Extracted characters</dt><dd>${esc(job.extracted_character_count || 0)}</dd>
        <dt>Elapsed seconds</dt><dd>${esc(job.elapsed_seconds ?? 0)}</dd>
      </dl>
      <button id="cancel-intake">Cancel intake</button>
    </div>
  `;
}

function uploadPdfStreaming(runId, file, metadata, onProgress) {
  return new Promise(async (resolve, reject) => {
    let job;
    try {
      job = await api(`/api/runs/${runId}/intake-jobs`, {method: "POST", body: JSON.stringify(metadata)});
    } catch (error) {
      reject(error);
      return;
    }
    const form = new FormData();
    form.append("rights_status", metadata.rights_status || "");
    form.append("privacy_status", metadata.privacy_status || "");
    form.append("retain_normalized_source", metadata.retain_normalized_source ? "true" : "false");
    if (metadata.profile_id) form.append("profile_id", metadata.profile_id);
    if (metadata.source_title) form.append("source_title", metadata.source_title);
    form.append("file", file, file.name);
    const xhr = new XMLHttpRequest();
    state.intakeXhr = xhr;
    state.intakeJobId = job.job_id;
    xhr.open("POST", `/api/runs/${encodeURIComponent(runId)}/intake-jobs/${encodeURIComponent(job.job_id)}/upload`);
    xhr.setRequestHeader("X-Declared-Upload-Bytes", String(file.size));
    xhr.upload.onprogress = (event) => {
      if (onProgress) {
        onProgress({
          ...job,
          received_bytes: event.loaded,
          expected_source_bytes: file.size,
          maximum_bytes: job.maximum_bytes,
          current_stage: "receiving",
          upload_complete: false,
        });
      }
    };
    xhr.onload = async () => {
      state.intakeXhr = null;
      let payload = {};
      try { payload = JSON.parse(xhr.responseText || "{}"); } catch (_error) { payload = {}; }
      if (xhr.status >= 400 || payload.error) {
        reject(new Error(payload.error || xhr.statusText || "upload failed"));
        return;
      }
      try {
        const finalJob = await pollIntakeJob(runId, job.job_id, onProgress);
        resolve(finalJob);
      } catch (error) {
        reject(error);
      }
    };
    xhr.onerror = () => {
      state.intakeXhr = null;
      reject(new Error("upload failed"));
    };
    xhr.onabort = () => {
      state.intakeXhr = null;
      reject(new Error("cancelled"));
    };
    xhr.send(form);
  });
}

async function pollIntakeJob(runId, jobId, onProgress) {
  for (;;) {
    const job = await api(`/api/runs/${runId}/intake-jobs/${jobId}`);
    if (onProgress) onProgress(job);
    if (job.current_stage === "ready_to_compile" && job.ready_to_compile) return job;
    if (["failed", "cancelled", "interrupted"].includes(job.current_stage)) {
      throw new Error(job.last_error || job.current_stage);
    }
    await new Promise((resolve) => setTimeout(resolve, 400));
  }
}

function namedList(items, emptyText) {
  if (!items.length) return `<p class="warning">${esc(emptyText)}</p>`;
  return `<ul>${items.map(item => `<li><strong>${esc(item.name || item.code || item.candidate_id)}</strong>${item.code ? ` <span class="muted">(${esc(item.code)})</span>` : ""}</li>`).join("")}</ul>`;
}

function renderCompileSummary(summary) {
  const success = summary.status === "compilation_complete";
  return `
    <div class="${success ? "success" : "warning"}">
      <h3>${esc(summary.operator_message)}</h3>
      <dl class="summary-grid">
        <dt>Run ID</dt><dd>${esc(summary.run_id)}</dd>
        <dt>Source title</dt><dd>${esc(summary.source_title || "Untitled source")}</dd>
        <dt>Document type</dt><dd>${esc(summary.document_type || "review required")}</dd>
        <dt>Source filename</dt><dd>${esc(summary.source_display_filename || "none")}</dd>
        <dt>Detected subject</dt><dd>${esc(summary.detected_subject || "review required")}</dd>
        <dt>Detected course level</dt><dd>${esc(summary.detected_course_level || "review required")}</dd>
        <dt>Selected profile</dt><dd>${esc(summary.selected_profile_id || "none")}</dd>
        <dt>Profile alignment</dt><dd>${esc(summary.profile_alignment_status || "review required")}</dd>
        <dt>Practice potential</dt><dd>${esc(summary.practice_potential || "review required")}</dd>
        <dt>Assessment potential</dt><dd>${esc(summary.assessment_potential || "review required")}</dd>
        <dt>Review status</dt><dd>${esc(summary.review_status || "pending")}</dd>
        <dt>Raw PDF retained</dt><dd>${yesNo(summary.retention?.raw_pdf_retained)}</dd>
        <dt>Extracted text retained</dt><dd>${yesNo(summary.retention?.extracted_text_retained)}</dd>
        <dt>Run saved to dashboard history</dt><dd>${yesNo(summary.persistence?.run_saved_to_dashboard_history)}</dd>
      </dl>
      <h4>Topics (${esc(summary.topic_count)})</h4>
      ${namedList(summary.topics || [], "No topics were produced. Review the source and rerun compilation.")}
      <h4>Micro-skills (${esc(summary.micro_skill_count)})</h4>
      ${namedList(summary.micro_skills || [], "No micro-skills were produced. Review the source and rerun compilation.")}
      <h4>Content gaps</h4>
      ${(summary.content_gaps || []).length ? `<ul>${summary.content_gaps.map(gap => `<li>${esc(gap.severity || "review")}: ${esc(gap.description || gap.gap_id)}</li>`).join("")}</ul>` : "<p>No blocking content gaps reported.</p>"}
      ${summary.assessment_content_gap ? `<p class="warning">${esc(summary.assessment_content_gap)}</p>` : ""}
      ${summary.profile_alignment_warning ? `<p class="warning">${esc(summary.profile_alignment_warning)}</p>` : ""}
      <h4>Next action</h4>
      <ol>${(summary.next_steps || []).map(step => `<li>${esc(step)}</li>`).join("")}</ol>
      <button id="go-curriculum">Review Curriculum</button>
      <button id="go-practice" ${summary.review_status === "accepted_for_local_use" ? "" : "disabled"}>Generate Practice</button>
      <button id="go-assessment" ${summary.review_status === "accepted_for_local_use" ? "" : "disabled"}>Configure Assessment</button>
      ${summary.review_status === "accepted_for_local_use" ? "" : `<p class="hint">Configure Assessment is enabled after curriculum-review decisions are saved.</p>`}
    </div>
  `;
}

async function runs() {
  const data = await api("/api/runs");
  const rows = data.runs.map(run => `
    <tr>
      <td><button class="linkish" data-run="${esc(run.run_id)}">${esc(run.run_id)}</button></td>
      <td>${esc(run.source_title || "")}</td>
      <td>${esc(run.detected_subject || "")}</td>
      <td>${esc(run.status)}</td>
      <td>${esc((run.assessment_ids || []).length)}</td>
      <td>${esc(run.updated_at)}</td>
    </tr>`).join("");
  render("Runs", `
    ${controls()}
    <label>Source title <input id="source-title" value="Untitled source"></label>
    <button id="new-run">New run</button>
    <table><thead><tr><th>Run ID</th><th>Source</th><th>Subject</th><th>Status</th><th>Assessments</th><th>Updated</th></tr></thead><tbody>${rows}</tbody></table>
  `);
  document.querySelector("#new-run").onclick = async () => {
    const run = await api("/api/runs", {method: "POST", body: JSON.stringify({source_title: document.querySelector("#source-title").value})});
    state.runId = run.run_id;
    await source();
  };
  document.querySelectorAll("[data-run]").forEach(button => {
    button.onclick = async () => {
      state.runId = button.dataset.run;
      const run = await api(`/api/runs/${state.runId}`);
      state.assessmentId = (run.assessment_ids || [])[0] || null;
      await source();
    };
  });
}

async function source() {
  const profiles = (await api("/api/profiles")).profiles;
  const limits = await api("/api/limits").catch(() => ({max_upload_label: "512 MiB", max_pdf_pages: 5000}));
  const run = state.runId ? await api(`/api/runs/${state.runId}`) : null;
  const compileReady = readyToCompile(run);
  const filenameValue = run?.source_display_filename || "";
  const persistedSourceNotice = run
    ? `Selected run ${run.run_id} is loaded from persisted dashboard state. Choose a file or enter text only to replace this run's source.`
    : "Create or reopen a run before uploading source content.";
  const profileOptions = profiles.map(p => {
    const selected = p.profile_id === run?.selected_profile_id ? " selected" : "";
    return `<option value="${esc(p.profile_id)}"${selected}>${esc(p.subject_code)} - ${esc(p.profile_id)}</option>`;
  }).join("");
  render("Source", `
    ${controls(run)}
    <label>Filename <input id="filename" value="${esc(filenameValue)}"></label>
    <label>Upload .txt, .md, or text-native .pdf <input id="source-file" type="file" accept=".txt,.md,.pdf"></label>
    <p class="hint">PDF support is local text-native extraction only. No OCR, scanned/image-only PDFs, image conversion, or external PDF services are used. Maximum PDF size: ${esc(limits.max_upload_label || "512 MiB")}. Maximum pages: ${esc(Number(limits.max_pdf_pages || 5000).toLocaleString("en-US"))}. Text-native PDF only: No OCR or scanned-image interpretation. Raw PDFs are discarded; normalized-source retention is optional.</p>
    <label>Source text <textarea id="content" rows="8">${esc(persistedSourceNotice)}</textarea></label>
    <label>Rights status <input id="rights" value="${esc(run?.rights_status || "approved_local_use")}"></label>
    <label>Privacy status <input id="privacy" value="${esc(run?.privacy_status || "non_private")}"></label>
    <label><input type="checkbox" id="retain" ${run?.raw_or_normalized_source_retained ? "checked" : ""}> Retain normalized source in this local run</label>
    <button id="upload">Upload source</button>
    <label>Profile alignment <select id="profile"><option value=""${run?.selected_profile_id ? "" : " selected"}>Auto-detect / No profile</option>${profileOptions}</select></label>
    <button id="confirm">Confirm rights</button>
    <button id="select-profile">Apply optional profile alignment</button>
    <button id="compile" ${compileReady ? "" : "disabled"}>Compile</button>
    ${compileReady ? "" : `<p id="compile-prereq" class="warning">Compile is disabled until Upload Source persists source_ready with rights, privacy, and hash.</p>`}
    <div id="source-output">
      ${sourceReadySummary(run)}
      ${run?.compiler_status === "complete" ? "<p class=\"success\">Compilation complete. Open Curriculum to review results.</p>" : ""}
      <pre>${esc(JSON.stringify(run, null, 2))}</pre>
    </div>
  `);
  document.querySelector("#source-file").onchange = async () => {
    const file = document.querySelector("#source-file").files[0];
    if (!file) return;
    document.querySelector("#filename").value = file.name;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      document.querySelector("#content").value = await file.text();
    } else {
      document.querySelector("#content").value = "PDF selected: streaming upload and local text extraction will run after upload.";
    }
  };
  document.querySelector("#upload").onclick = async () => {
    const file = document.querySelector("#source-file").files[0];
    const payload = {
      filename: document.querySelector("#filename").value,
      rights_status: document.querySelector("#rights").value,
      privacy_status: document.querySelector("#privacy").value,
      retain_normalized_source: document.querySelector("#retain").checked,
    };
    const selectedProfile = document.querySelector("#profile").value;
    if (selectedProfile) payload.profile_id = selectedProfile;
    try {
      if (file && file.name.toLowerCase().endsWith(".pdf")) {
        const output = document.querySelector("#source-output");
        const renderJob = (job) => {
          output.innerHTML = intakeProgressHtml(job, file.name);
          const cancel = document.querySelector("#cancel-intake");
          if (cancel) {
            cancel.onclick = async () => {
              if (state.intakeJobId) {
                await api(`/api/runs/${state.runId}/intake-jobs/${state.intakeJobId}/cancel`, {method: "POST", body: "{}"}).catch(() => ({}));
              }
              if (state.intakeXhr) state.intakeXhr.abort();
            };
          }
        };
        await uploadPdfStreaming(state.runId, file, payload, renderJob);
        const updated = await api(`/api/runs/${state.runId}`);
        output.innerHTML = `${sourceReadySummary(updated)}<pre>${esc(JSON.stringify(updated, null, 2))}</pre>`;
        document.querySelector("#compile").disabled = !readyToCompile(updated);
        const prereq = document.querySelector("#compile-prereq");
        if (prereq && readyToCompile(updated)) prereq.remove();
        return;
      }
      payload.content = document.querySelector("#content").value;
      const updated = await api(`/api/runs/${state.runId}/source`, {method: "POST", body: JSON.stringify(payload)});
      document.querySelector("#source-output").innerHTML = `${sourceReadySummary(updated)}<pre>${esc(JSON.stringify(updated, null, 2))}</pre>`;
      document.querySelector("#compile").disabled = !readyToCompile(updated);
      const prereq = document.querySelector("#compile-prereq");
      if (prereq && readyToCompile(updated)) prereq.remove();
    } catch (error) {
      document.querySelector("#source-output").innerHTML = `<div class="warning"><h3>Upload failed</h3><p>Recovery: choose a supported .txt, .md, or text-native .pdf source, then press Upload Source again.</p><p>${esc(error.message)}</p></div>`;
    }
  };
  document.querySelector("#confirm").onclick = async () => {
    const updated = await api(`/api/runs/${state.runId}/rights`, {method: "POST", body: JSON.stringify({rights_status: document.querySelector("#rights").value, privacy_status: document.querySelector("#privacy").value})});
    document.querySelector("#source-output").innerHTML = `${sourceReadySummary(updated)}<pre>${esc(JSON.stringify(updated, null, 2))}</pre>`;
    document.querySelector("#compile").disabled = !readyToCompile(updated);
  };
  document.querySelector("#select-profile").onclick = async () => {
    const selectedProfile = document.querySelector("#profile").value;
    if (!selectedProfile) {
      document.querySelector("#source-output").innerHTML = `<div class="success"><h3>Auto-detect profile alignment selected</h3><p>No profile is required before compilation.</p></div>`;
      return;
    }
    const updated = await api(`/api/runs/${state.runId}/profile`, {method: "POST", body: JSON.stringify({profile_id: selectedProfile})});
    document.querySelector("#source-output").innerHTML = `${sourceReadySummary(updated)}<pre>${esc(JSON.stringify(updated, null, 2))}</pre>`;
    document.querySelector("#compile").disabled = !readyToCompile(updated);
  };
  document.querySelector("#compile").onclick = async () => {
    try {
      const updated = await api(`/api/runs/${state.runId}/compile`, {method: "POST", body: JSON.stringify({})});
      if (updated.compiler_status !== "complete") {
        document.querySelector("#source-output").innerHTML = `<div class="warning"><h3>Compilation failed</h3><p>Stage: compiler execution</p><p>Recovery: review the source upload, rights and privacy status, then compile again.</p><pre>${esc(JSON.stringify(updated, null, 2))}</pre></div>`;
        return;
      }
      const summary = await api(`/api/runs/${state.runId}/compile-summary`);
      document.querySelector("#source-output").innerHTML = renderCompileSummary(summary);
      document.querySelector("#go-curriculum").onclick = curriculum;
      const assessmentButton = document.querySelector("#go-assessment");
      if (assessmentButton && !assessmentButton.disabled) assessmentButton.onclick = studio;
      const practiceButton = document.querySelector("#go-practice");
      if (practiceButton && !practiceButton.disabled) practiceButton.onclick = practice;
    } catch (error) {
      document.querySelector("#source-output").innerHTML = `<div class="warning"><h3>Compile request blocked</h3><p>${esc(error.message)}</p><p>Recovery: upload a source successfully and confirm the run shows Ready to compile: Yes.</p></div>`;
    }
  };
}

async function curriculum() {
  const results = await api(`/api/runs/${state.runId}/results`);
  const skills = results.micro_skills || [];
  render("Curriculum", `
    ${controls(results.run)}
    <h3>Topics</h3>
    <pre>${esc(JSON.stringify(results.topics, null, 2))}</pre>
    <h3>Micro-skills</h3>
    <pre>${esc(JSON.stringify(skills, null, 2))}</pre>
    <h3>Procedure candidates</h3>
    <pre>${esc(JSON.stringify(results.procedure_candidates || [], null, 2))}</pre>
    <button id="accept-skills">Save Review Decisions</button>
    <pre id="review-output"></pre>
  `);
  document.querySelector("#accept-skills").onclick = async () => {
    const decisions = skills.map(skill => ({
      candidate_id: skill.candidate_id || skill.micro_skill_code,
      candidate_type: "micro_skill",
      decision: "accepted",
    }));
    const reviewed = await api(`/api/runs/${state.runId}/curriculum-review`, {method: "POST", body: JSON.stringify({decisions})});
    document.querySelector("#review-output").innerHTML = `<div class="success"><h3>Review decisions saved</h3><p>Next action: Generate Practice, then Configure Assessment → Generate Questions.</p><button id="go-practice-after-review">Generate Practice</button><button id="go-studio-after-review">Configure Assessment</button></div><pre>${esc(JSON.stringify(reviewed, null, 2))}</pre>`;
    document.querySelector("#go-practice-after-review").onclick = practice;
    document.querySelector("#go-studio-after-review").onclick = studio;
  };
}

async function practice() {
  const run = await api(`/api/runs/${state.runId}`);
  render("Practice", `
    ${controls(run)}
    <p class="hint">Practice packages are dashboard-local, demo-unverified, noncanonical, and student_visible=false.</p>
    <button id="generate-practice">Generate Practice</button>
    <pre id="practice-output"></pre>
  `);
  document.querySelector("#generate-practice").onclick = async () => {
    try {
      const generated = await api(`/api/runs/${state.runId}/practice`, {method: "POST", body: JSON.stringify({})});
      document.querySelector("#practice-output").innerHTML = `<div class="success"><h3>Practice package generated</h3><p>Package ID: ${esc(generated.practice_package_id)}</p><p>Item count: ${esc(generated.practice_item_count)}</p></div><pre>${esc(JSON.stringify(generated, null, 2))}</pre>`;
    } catch (error) {
      document.querySelector("#practice-output").innerHTML = `<div class="warning"><h3>Practice generation blocked</h3><p>${esc(error.message)}</p></div>`;
    }
  };
}

async function studio() {
  const run = state.runId ? await api(`/api/runs/${state.runId}`) : null;
  const familyData = state.runId ? await api(`/api/runs/${state.runId}/generation-families`) : {generation_families: []};
  const families = familyData.generation_families || [];
  const canConfigure = run?.status === "assessment_ready" || run?.status === "assessment_review_pending";
  const hasCompatibleFamilies = families.length > 0;
  const unmet = "Save curriculum-review decisions before configuring an assessment.";
  render("Assessment Studio", `
    ${controls(run)}
    ${canConfigure ? "" : `<p class="warning">${esc(unmet)}</p>`}
    ${hasCompatibleFamilies ? "" : `<p class="warning">${esc(familyData.content_gap || "No compatible assessment generation family is available for the accepted curriculum. Assessment generation remains a content gap.")}</p>`}
    <label>Assessment ID <input id="assessment-id" value="ASSESSMENT_LOCAL"></label>
    <label>Generation family <select id="family">${families.map(f => `<option value="${esc(f.generation_family_id)}">${esc(f.target_micro_skill_code)} - ${esc(f.generation_family_id)}</option>`).join("")}</select></label>
    <label>Question count <input id="count" type="number" min="1" max="20" value="10"></label>
    <label>Random seed <input id="seed" type="number" value="20260718"></label>
    <button id="create-assessment" ${canConfigure && hasCompatibleFamilies ? "" : "disabled"}>Create blueprint</button>
    <button id="generate-assessment" disabled>Generate Questions</button>
    <p id="assessment-prereq" class="hint">${canConfigure && hasCompatibleFamilies ? "Generate Questions is enabled after a valid assessment blueprint is created." : esc(hasCompatibleFamilies ? unmet : "Assessment generation is disabled until a compatible generation family exists.")}</p>
    <pre id="studio-output"></pre>
  `);
  document.querySelector("#create-assessment").onclick = async () => {
    const count = Number(document.querySelector("#count").value);
    const blueprint = await api(`/api/runs/${state.runId}/assessments`, {
      method: "POST",
      body: JSON.stringify({
        assessment_id: document.querySelector("#assessment-id").value,
        generation_family_id: document.querySelector("#family").value,
        question_count: count,
        random_seed: Number(document.querySelector("#seed").value),
      }),
    });
    state.assessmentId = blueprint.assessment_id;
    document.querySelector("#studio-output").textContent = JSON.stringify(blueprint, null, 2);
    document.querySelector("#generate-assessment").disabled = false;
    document.querySelector("#assessment-prereq").textContent = "Assessment blueprint saved. Generate Questions is available.";
  };
  document.querySelector("#generate-assessment").onclick = async () => {
    state.assessmentId = state.assessmentId || document.querySelector("#assessment-id").value;
    const generated = await api(`/api/runs/${state.runId}/assessments/${state.assessmentId}/generate`, {method: "POST", body: JSON.stringify({})});
    document.querySelector("#studio-output").textContent = JSON.stringify(generated.validation_report, null, 2);
  };
}

async function review() {
  await ensureAssessmentId();
  const data = await api(`/api/runs/${state.runId}/assessments/${state.assessmentId}`);
  const rows = data.assessment.questions.map((q, index) => `
    <tr><td>${esc(q.question_id)}</td><td>${esc(q.difficulty_level)}</td><td>${esc(q.question_type)}</td><td>${index === 0 ? "lock candidate" : ""}</td></tr>
  `).join("");
  render("Assessment Review", `
    ${controls()}
    <p>Assessment: <strong>${esc(state.assessmentId)}</strong></p>
    <button id="accept-all">Accept all and lock first</button>
    <button id="regen-second">Regenerate second slot</button>
    <table><tbody>${rows}</tbody></table>
    <pre id="review-assessment-output"></pre>
  `);
  document.querySelector("#accept-all").onclick = async () => {
    const records = data.assessment.questions.map((q, index) => ({question_id: q.question_id, decision: "accepted", locked: index === 0}));
    const reviewed = await api(`/api/runs/${state.runId}/assessments/${state.assessmentId}/review`, {method: "POST", body: JSON.stringify({review_records: records})});
    document.querySelector("#review-assessment-output").textContent = JSON.stringify(reviewed, null, 2);
  };
  document.querySelector("#regen-second").onclick = async () => {
    const slot = data.assessment.questions[1]?.slot_id;
    const regenerated = await api(`/api/runs/${state.runId}/assessments/${state.assessmentId}/regenerate`, {method: "POST", body: JSON.stringify({slot_id: slot, child_seed: 20260719})});
    document.querySelector("#review-assessment-output").textContent = JSON.stringify(regenerated, null, 2);
  };
}

async function validation() {
  const gate = await api(`/api/runs/${state.runId}/artifacts/run_summary`).catch(() => ({artifact: "No run summary artifact yet."}));
  render("Validation", `${controls()}<pre>${esc(JSON.stringify(gate, null, 2))}</pre>`);
}

function exportsView() {
  ensureAssessmentId().then(() => {
  const base = `/api/runs/${encodeURIComponent(state.runId)}/assessments/${encodeURIComponent(state.assessmentId)}/exports`;
  render("Exports", `
    ${controls()}
    <p>Assessment: <strong>${esc(state.assessmentId || "")}</strong></p>
    <ul>
      <li><a href="${base}/student_json">Student JSON</a></li>
      <li><a href="${base}/student_markdown">Student Markdown</a></li>
      <li><a href="${base}/instructor_json">Instructor JSON</a></li>
      <li><a href="${base}/instructor_markdown">Instructor Markdown</a></li>
    </ul>
  `);
  }).catch(error => render("Error", `<p>${esc(error.message)}</p>`));
}

async function advanced() {
  const run = await api(`/api/runs/${state.runId}`);
  render("Advanced", `${controls(run)}<pre>${esc(JSON.stringify(run, null, 2))}</pre>`);
}

function candidateCard(entry) {
  const reports = entry.reports || {};
  const curriculum = entry.curriculum_linkage || {};
  const procedure = entry.procedure_linkage || {};
  return `
    <article class="candidate-card" data-candidate="${esc(entry.external_preparation_id)}">
      <h3>${esc(entry.external_preparation_id)}</h3>
      <dl class="summary-grid">
        <dt>Source pathway</dt><dd>${esc(entry.source_type)}</dd>
        <dt>Source adapter</dt><dd>${esc(entry.source_adapter)}</dd>
        <dt>Candidate identity</dt><dd>${esc(entry.candidate_identity)}</dd>
        <dt>Micro-skill</dt><dd>${esc(curriculum.primary_micro_skill_code)}</dd>
        <dt>Procedure</dt><dd>${esc(procedure.procedure_id)}</dd>
        <dt>Procedure verified</dt><dd>${yesNo(procedure.verified)}</dd>
        <dt>Status</dt><dd>${esc(entry.packet_status)}</dd>
        <dt>Review verdict</dt><dd>${esc(entry.review_action)}</dd>
        <dt>System recommendation</dt><dd>${esc(entry.system_recommendation)}</dd>
        <dt>Human action explicit</dt><dd>${yesNo(entry.human_review_action?.explicit)}</dd>
        <dt>Validation</dt><dd>${esc(entry.validation_status)}</dd>
        <dt>Independent derivation</dt><dd>${esc(entry.independent_derivation_status)}</dd>
        <dt>Grading validation</dt><dd>${esc(entry.grading_validation)}</dd>
        <dt>Failure-signal validation</dt><dd>${esc(entry.failure_signal_validation)}</dd>
        <dt>Rights/provenance</dt><dd>${esc(entry.rights_provenance_classification)}</dd>
        <dt>Asset status</dt><dd>${esc(entry.asset_status)}</dd>
        <dt>Duplicate classification</dt><dd>${esc(entry.duplicate_classification)}</dd>
        <dt>Blockers</dt><dd>${esc((entry.unresolved_blockers || []).join(", ") || "none")}</dd>
        <dt>Export state</dt><dd>${esc(entry.packet_path)}</dd>
      </dl>
      <p class="hint">Procedure evidence, independent derivation, grading validation, failure-signal validation, fingerprints, duplicate report, rights/provenance report, asset report, blockers, and review lineage are preserved in the packet and linked reports.</p>
      <pre>${esc(JSON.stringify({source_identity: entry.source_identity, source_hashes: entry.source_hashes, rights_provenance: entry.rights_provenance_evidence, duplicate_comparison: entry.duplicate_evidence, computed_validation: {derivation: entry.independent_derivation_evidence, grading: entry.grading_evidence, failure_signals: entry.failure_signal_evidence}, human_review_action: entry.human_review_action, unresolved_blockers: entry.unresolved_blockers, packet_path: entry.packet_path, reports}, null, 2))}</pre>
    </article>
  `;
}

async function canonicalPromotion() {
  const mode = await api("/api/canonical-promotion/mode");
  const legacyPilotRunId = "CANONICAL_PROMOTION_PREPARATION_PILOT_020";
  const defaultRunId = "CANONICAL_PROMOTION_UNIVERSAL_RECONCILIATION_045";
  let reopened = null;
  let error = null;
  try {
    reopened = await api(`/api/canonical-promotion/runs/${defaultRunId}`);
  } catch (caught) {
    error = caught;
  }
  const summary = reopened || {};
  const status = mode.status_labels || {};
  render("Canonical Promotion Preparation", `
    <div class="success">
      <h3>${esc(mode.mode_identifier)}</h3>
      <p>Preparation-only mode. Separate from document compiler, Phase E manifest-driven production, live workflows, and canonical workflows.</p>
      <dl class="summary-grid">
        <dt>Execution profile</dt><dd>${esc((mode.execution_profiles || []).join(", "))}</dd>
        <dt>Noncanonical</dt><dd>${yesNo(status.noncanonical)}</dd>
        <dt>Human review required</dt><dd>${yesNo(status.human_review_required)}</dd>
        <dt>Student visible</dt><dd>${yesNo(status.student_visible)}</dd>
        <dt>Alpha import eligible</dt><dd>${yesNo(status.eligible_for_alpha_import)}</dd>
        <dt>Canonical promotion authorized</dt><dd>${yesNo(status.canonical_promotion_authorized)}</dd>
        <dt>Database write authorized</dt><dd>${yesNo(status.database_write_authorized)}</dd>
      </dl>
    </div>
    <label>Pilot run ID <input id="canonical-promotion-run-id" value="${esc(defaultRunId)}"></label>
    <button id="canonical-promotion-run">Run reconciliation</button>
    <button id="canonical-promotion-reopen">Reopen run</button>
    <div id="canonical-promotion-output">
      ${error ? `<p class="warning">${esc(error.message)}</p>` : canonicalPromotionSummary(summary)}
    </div>
  `);
  document.querySelector("#canonical-promotion-run").onclick = async () => {
    const runId = document.querySelector("#canonical-promotion-run-id").value;
    const endpoint = runId === legacyPilotRunId
      ? "/api/canonical-promotion/pilot"
      : "/api/canonical-promotion/universal-reconciliation";
    const data = await api(endpoint, {method: "POST", body: JSON.stringify({run_id: runId})});
    document.querySelector("#canonical-promotion-output").innerHTML = canonicalPromotionSummary(data);
  };
  document.querySelector("#canonical-promotion-reopen").onclick = async () => {
    const runId = document.querySelector("#canonical-promotion-run-id").value;
    const data = await api(`/api/canonical-promotion/runs/${encodeURIComponent(runId)}`);
    document.querySelector("#canonical-promotion-output").innerHTML = canonicalPromotionSummary(data);
  };
}

function canonicalPromotionSummary(data) {
  const packets = data.packets || [];
  return `
    <dl class="summary-grid">
      <dt>Run ID</dt><dd>${esc(data.run_id || "")}</dd>
      <dt>External preparation root</dt><dd>${esc(data.preparation_root || "restored from external state")}</dd>
      <dt>Total candidates</dt><dd>${esc(data.candidate_count ?? data.packet_count ?? "n/a")}</dd>
      <dt>Document-driven</dt><dd>${esc(data.document_driven_count ?? "5")}</dd>
      <dt>Phase E</dt><dd>${esc(data.phase_e_count ?? "5")}</dd>
      <dt>Prepared</dt><dd>${esc(data.prepared_count ?? "n/a")}</dd>
      <dt>Blocked</dt><dd>${esc(data.blocked_count ?? "n/a")}</dd>
      <dt>Rights/provenance blockers</dt><dd>${esc(data.rights_or_provenance_blockers ?? "at least 1")}</dd>
      <dt>Asset blockers</dt><dd>${esc(data.asset_or_governance_blockers ?? "at least 1")}</dd>
      <dt>Duplicate-review cases</dt><dd>${esc(data.duplicate_review_cases ?? "at least 1")}</dd>
      <dt>Returned for correction</dt><dd>${esc(data.returned_for_correction ?? "2")}</dd>
      <dt>Rejected/regenerated</dt><dd>${esc(data.rejected_or_regenerated ?? "1")}</dd>
      <dt>Canonical IDs assigned</dt><dd>${esc(data.canonical_ids_assigned ?? 0)}</dd>
      <dt>Canonical paths written</dt><dd>${esc(data.canonical_paths_written ?? 0)}</dd>
      <dt>Database access</dt><dd>${esc(data.database_access || "none")}</dd>
    </dl>
    ${packets.length ? packets.map(candidateCard).join("") : `<pre>${esc(JSON.stringify(data, null, 2))}</pre>`}
  `;
}

function canonicalProjectionSummary(data) {
  const counts = data.counts || {};
  const safety = data.safety || data.status_labels || {};
  return `
    <dl class="summary-grid">
      <dt>Run ID</dt><dd>${esc(data.run_id || "")}</dd>
      <dt>Status</dt><dd>${esc(data.status || data.mode_identifier || "")}</dd>
      <dt>Records</dt><dd>${esc(counts.records ?? "n/a")}</dd>
      <dt>Creates</dt><dd>${esc(counts.creates ?? "n/a")}</dd>
      <dt>Revisions</dt><dd>${esc(counts.revisions ?? "n/a")}</dd>
      <dt>Idempotent no-ops</dt><dd>${esc(counts.idempotent_noops ?? "n/a")}</dd>
      <dt>Beta references</dt><dd>${esc(counts.beta_references ?? "n/a")}</dd>
      <dt>Assessments</dt><dd>${esc(counts.assessments ?? "n/a")}</dd>
      <dt>Noncanonical</dt><dd>${yesNo(safety.noncanonical)}</dd>
      <dt>Human review required</dt><dd>${yesNo(safety.human_review_required)}</dd>
      <dt>Database write</dt><dd>${yesNo(safety.database_write)}</dd>
      <dt>Promotion authorized</dt><dd>${yesNo(safety.promotion_authorized)}</dd>
      <dt>Student visible</dt><dd>${yesNo(safety.student_visible)}</dd>
    </dl>
    <pre>${esc(JSON.stringify(data, null, 2))}</pre>
  `;
}

async function canonicalProjection() {
  const mode = await api("/api/canonical-projection/mode");
  render("Canonical Execution and Beta Projection Planning", `
    <div class="success">
      <h3>${esc(mode.mode_identifier)}</h3>
      <p>Database-neutral external staging only. Every result requires human review and cannot promote, import, publish, or write a database.</p>
      ${canonicalProjectionSummary(mode)}
    </div>
    <label>Projection request JSON
      <textarea id="canonical-projection-payload" rows="12">${esc(JSON.stringify({run_id: "CANONICAL_PROJECTION_REVIEW", candidates: [], beta_export: {}, assessments: [], previous_records: []}, null, 2))}</textarea>
    </label>
    <button id="canonical-projection-plan">Validate and stage plan</button>
    <label>Run ID to reopen <input id="canonical-projection-run-id" value="CANONICAL_PROJECTION_REVIEW"></label>
    <button id="canonical-projection-reopen">Reopen persisted plan</button>
    <div id="canonical-projection-output"></div>
  `);
  document.querySelector("#canonical-projection-plan").onclick = async () => {
    const payload = JSON.parse(document.querySelector("#canonical-projection-payload").value);
    const data = await api("/api/canonical-projection/plan", {method: "POST", body: JSON.stringify(payload)});
    document.querySelector("#canonical-projection-output").innerHTML = canonicalProjectionSummary(data);
  };
  document.querySelector("#canonical-projection-reopen").onclick = async () => {
    const runId = document.querySelector("#canonical-projection-run-id").value;
    const data = await api(`/api/canonical-projection/runs/${encodeURIComponent(runId)}`);
    document.querySelector("#canonical-projection-output").innerHTML = canonicalProjectionSummary(data);
  };
}

document.querySelectorAll("nav button").forEach(button => {
  button.addEventListener("click", () => {
    const views = {runs, source, curriculum, practice, studio, review, validation, exports: exportsView, canonicalPromotion, canonicalProjection, advanced};
    const fn = views[button.dataset.view] || runs;
    Promise.resolve(fn()).catch(error => render("Error", `<p>${esc(error.message)}</p>`));
  });
});

runs().catch(error => render("Error", `<p>${esc(error.message)}</p>`));
