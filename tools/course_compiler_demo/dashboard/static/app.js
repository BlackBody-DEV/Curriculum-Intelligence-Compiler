const app = document.querySelector("#app");
const state = { runId: null, assessmentId: null };

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
  return run?.status === "source_ready"
    && Boolean(run.source_display_filename)
    && Boolean(run.source_format)
    && Boolean(run.source_sha256)
    && rightsApproved
    && run.privacy_status === "non_private";
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
        <dt>File size</dt><dd>${esc(pdf.file_size_bytes || run.source_file_size_bytes || "unknown")}</dd>
        <dt>Page count</dt><dd>${esc(pdf.page_count || "n/a")}</dd>
        <dt>Pages containing text</dt><dd>${esc(pdf.pages_containing_text || "n/a")}</dd>
        <dt>Source SHA-256</dt><dd>${esc(run.source_sha256 || "none")}</dd>
        <dt>Extraction duration</dt><dd>${esc(pdf.processing_duration_seconds ?? "n/a")}</dd>
        <dt>Raw PDF retained</dt><dd>${yesNo(run.pdf_validation?.raw_pdf_retained)}</dd>
        <dt>Extracted text retained</dt><dd>${yesNo(run.pdf_validation?.extracted_text_retained ?? run.raw_or_normalized_source_retained)}</dd>
        <dt>Ready to compile</dt><dd>${yesNo(ready)}</dd>
      </dl>
      ${ready ? "" : "<p>Upload Source must persist filename, hash, rights, privacy, and source_ready state before Compile is available.</p>"}
    </div>
  `;
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
      <td>${esc(run.assessment_ids.length)}</td>
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
      await source();
    };
  });
}

async function source() {
  const profiles = (await api("/api/profiles")).profiles;
  const run = state.runId ? await api(`/api/runs/${state.runId}`) : null;
  const compileReady = readyToCompile(run);
  render("Source", `
    ${controls(run)}
    <label>Filename <input id="filename" value="source.txt"></label>
    <label>Upload .txt, .md, or text-native .pdf <input id="source-file" type="file" accept=".txt,.md,.pdf"></label>
    <p class="hint">PDF support is local text-native extraction only. No OCR, scanned/image-only PDFs, image conversion, or external PDF services are used. Default limits: 50 MiB upload, 1,500 pages, and larger files may take longer. Raw PDFs are discarded; normalized-source retention is optional.</p>
    <label>Source text <textarea id="content" rows="8">Subject: Physics\nNewton's Second Law states F_net = m a.</textarea></label>
    <label>Rights status <input id="rights" value="approved_local_use"></label>
    <label>Privacy status <input id="privacy" value="non_private"></label>
    <label><input type="checkbox" id="retain"> Retain normalized source in this local run</label>
    <button id="upload">Upload source</button>
    <label>Profile alignment <select id="profile"><option value="">Auto-detect / No profile</option>${profiles.map(p => `<option value="${esc(p.profile_id)}">${esc(p.subject_code)} - ${esc(p.profile_id)}</option>`).join("")}</select></label>
    <button id="confirm">Confirm rights</button>
    <button id="select-profile">Apply optional profile alignment</button>
    <button id="compile" ${compileReady ? "" : "disabled"}>Compile</button>
    ${compileReady ? "" : `<p id="compile-prereq" class="warning">Compile is disabled until Upload Source persists source_ready with rights, privacy, and hash.</p>`}
    <div id="source-output">${run?.compiler_status === "complete" ? "<p>Compilation complete. Open Curriculum to review results.</p>" : `${sourceReadySummary(run)}<pre>${esc(JSON.stringify(run, null, 2))}</pre>`}</div>
  `);
  document.querySelector("#source-file").onchange = async () => {
    const file = document.querySelector("#source-file").files[0];
    if (!file) return;
    document.querySelector("#filename").value = file.name;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      document.querySelector("#content").value = await file.text();
    } else {
      document.querySelector("#content").value = "PDF selected: local text extraction will run after upload.";
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
        const bytes = new Uint8Array(await file.arrayBuffer());
        let binary = "";
        bytes.forEach(byte => { binary += String.fromCharCode(byte); });
        payload.content_base64 = btoa(binary);
      } else {
        payload.content = document.querySelector("#content").value;
      }
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
}

async function advanced() {
  const run = await api(`/api/runs/${state.runId}`);
  render("Advanced", `${controls(run)}<pre>${esc(JSON.stringify(run, null, 2))}</pre>`);
}

document.querySelectorAll("nav button").forEach(button => {
  button.addEventListener("click", () => {
    const views = {runs, source, curriculum, practice, studio, review, validation, exports: exportsView, advanced};
    const fn = views[button.dataset.view] || runs;
    Promise.resolve(fn()).catch(error => render("Error", `<p>${esc(error.message)}</p>`));
  });
});

runs().catch(error => render("Error", `<p>${esc(error.message)}</p>`));
