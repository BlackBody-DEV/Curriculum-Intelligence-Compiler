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
  render("Source", `
    ${controls(run)}
    <label>Filename <input id="filename" value="source.txt"></label>
    <label>Source text <textarea id="content" rows="8">Subject: Physics\nNewton's Second Law states F_net = m a.</textarea></label>
    <label>Rights status <input id="rights" value="approved_local_use"></label>
    <label>Privacy status <input id="privacy" value="non_private"></label>
    <label><input type="checkbox" id="retain"> Retain normalized source in this local run</label>
    <button id="upload">Upload source</button>
    <label>Profile <select id="profile">${profiles.map(p => `<option value="${esc(p.profile_id)}">${esc(p.subject_code)} - ${esc(p.profile_id)}</option>`).join("")}</select></label>
    <label>Selected micro-skill <input id="micro-skill" value="apply_newtons_second_law_1d"></label>
    <button id="confirm">Confirm rights</button>
    <button id="select-profile">Select profile</button>
    <button id="compile">Compile</button>
    <pre id="source-output">${esc(JSON.stringify(run, null, 2))}</pre>
  `);
  document.querySelector("#upload").onclick = async () => {
    const payload = {
      filename: document.querySelector("#filename").value,
      content: document.querySelector("#content").value,
      rights_status: document.querySelector("#rights").value,
      privacy_status: document.querySelector("#privacy").value,
      retain_normalized_source: document.querySelector("#retain").checked,
    };
    const updated = await api(`/api/runs/${state.runId}/source`, {method: "POST", body: JSON.stringify(payload)});
    document.querySelector("#source-output").textContent = JSON.stringify(updated, null, 2);
  };
  document.querySelector("#confirm").onclick = async () => {
    const updated = await api(`/api/runs/${state.runId}/rights`, {method: "POST", body: JSON.stringify({rights_status: document.querySelector("#rights").value, privacy_status: document.querySelector("#privacy").value})});
    document.querySelector("#source-output").textContent = JSON.stringify(updated, null, 2);
  };
  document.querySelector("#select-profile").onclick = async () => {
    const updated = await api(`/api/runs/${state.runId}/profile`, {method: "POST", body: JSON.stringify({profile_id: document.querySelector("#profile").value})});
    document.querySelector("#source-output").textContent = JSON.stringify(updated, null, 2);
  };
  document.querySelector("#compile").onclick = async () => {
    const updated = await api(`/api/runs/${state.runId}/compile`, {method: "POST", body: JSON.stringify({selected_micro_skill: document.querySelector("#micro-skill").value})});
    document.querySelector("#source-output").textContent = JSON.stringify(updated, null, 2);
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
    <button id="accept-skills">Accept visible micro-skills for local assessment</button>
    <pre id="review-output"></pre>
  `);
  document.querySelector("#accept-skills").onclick = async () => {
    const decisions = skills.map(skill => ({
      candidate_id: skill.candidate_id || skill.micro_skill_code,
      candidate_type: "micro_skill",
      decision: "accepted",
    }));
    const reviewed = await api(`/api/runs/${state.runId}/curriculum-review`, {method: "POST", body: JSON.stringify({decisions})});
    document.querySelector("#review-output").textContent = JSON.stringify(reviewed, null, 2);
  };
}

async function studio() {
  const families = (await api("/api/generation-families")).generation_families;
  render("Assessment Studio", `
    ${controls()}
    <label>Assessment ID <input id="assessment-id" value="ASSESSMENT_LOCAL"></label>
    <label>Generation family <select id="family">${families.map(f => `<option value="${esc(f.generation_family_id)}">${esc(f.target_micro_skill_code)} - ${esc(f.generation_family_id)}</option>`).join("")}</select></label>
    <label>Question count <input id="count" type="number" min="1" max="20" value="10"></label>
    <label>Random seed <input id="seed" type="number" value="20260718"></label>
    <button id="create-assessment">Create blueprint</button>
    <button id="generate-assessment">Generate assessment</button>
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
    const views = {runs, source, curriculum, studio, review, validation, exports: exportsView, advanced};
    const fn = views[button.dataset.view] || runs;
    Promise.resolve(fn()).catch(error => render("Error", `<p>${esc(error.message)}</p>`));
  });
});

runs().catch(error => render("Error", `<p>${esc(error.message)}</p>`));
