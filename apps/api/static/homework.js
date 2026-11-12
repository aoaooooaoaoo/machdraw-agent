"use strict";

const STORAGE_KEY = "rp.homework.v1";
const $ = (id) => document.getElementById(id);
const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[char]);
const status = (message) => { $("status").textContent = message; };
let local = { custom: [], responses: {} };
let builtIn = [];
let abilities = new Map();
let assignmentId = "";
let responseId = "";
let criterionSequence = 0;
let scanController = null;

function assignment() {
  return [...builtIn, ...local.custom].find((item) => item.id === assignmentId);
}

function records() {
  return local.responses[assignmentId] ?? [];
}

function persist(next) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    local = next;
    return true;
  } catch {
    status("浏览器无法保存记录，请检查存储空间或浏览器设置。");
    return false;
  }
}

function setRecords(rows) {
  return persist({ ...local, responses: { ...local.responses, [assignmentId]: rows } });
}

function renderTable(columns, rows) {
  return `<table><thead><tr>${columns.map((label) => `<th scope="col">${escapeHTML(label)}</th>`).join("")}</tr></thead>
    <tbody>${rows.map((row) => `<tr>${row.map((value) => `<td>${escapeHTML(value)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
}

function render() {
  const options = [...builtIn, ...local.custom];
  $("assignment").replaceChildren(...options.map((item) => new Option(item.title, item.id)));
  if (!options.some((item) => item.id === assignmentId)) assignmentId = options[0]?.id ?? "";
  $("assignment").value = assignmentId;
  const item = assignment();
  $("question").textContent = item?.question ?? "请新建题目和量规。";
  $("case-data").innerHTML = item?.table ? `<p>${escapeHTML(item.context)}</p>${renderTable(item.table.columns, item.table.rows)}
    <div class="actions">
      <a href="/?view=course&amp;tab=cases&amp;case=${encodeURIComponent(item.id)}">打开学生案例</a>
      ${item.question_ids.map((id) => `<a href="/?view=course&amp;tab=question&amp;question=${encodeURIComponent(id)}">问题图谱 ${escapeHTML(id)}</a>`).join("")}
    </div>` : "";
  const rows = records();
  if (!rows.some((row) => row.id === responseId)) {
    responseId = (rows.find((row) => !row.review) ?? rows[0])?.id ?? "";
  }
  $("response").replaceChildren(...rows.map((row) => new Option(
    `${row.id} · ${row.review ? "已确认" : "待批阅"}`, row.id,
  )));
  $("response").value = responseId;
  $("add").querySelector("button").disabled = !item;
  $("batch").querySelector("button").disabled = !item;
  $("fill-demo").disabled = !item?.demo_responses?.length;
  $("export").disabled = !options.length;
  renderReview();
  renderStats();
  renderCandidates();
}

function confirmedPatterns(confirmed) {
  const labels = new Map((assignment()?.rubric ?? []).flatMap((row) => row.errors.map((error) => [error.id, error.label])));
  const byName = new Map();
  for (const row of confirmed) {
    const names = new Set([
      ...row.review.items.flatMap((result) => result.error_ids.map((id) => labels.get(id)).filter(Boolean)),
      ...row.review.extra,
    ]);
    for (const name of names) {
      if (!byName.has(name)) byName.set(name, []);
      byName.get(name).push(row);
    }
  }
  return [...byName].sort(([a, n], [b, m]) => m.length - n.length || a.localeCompare(b, "zh-CN"))
    .map(([name, related]) => ({ name, related, ratio: `${(related.length * 100 / confirmed.length).toFixed(1)}%` }));
}

function renderStats() {
  const rows = records();
  const confirmed = rows.filter((row) => row.review);
  $("summary").textContent = `已确认 ${confirmed.length} / ${rows.length} 份。比例以已确认的作答为分母，同一份作答中的同一错因只计一次。`;
  const results = confirmedPatterns(confirmed);
  $("export-report").disabled = !confirmed.length;
  $("patterns").innerHTML = results.length ? `<table><thead><tr><th>错因或出错方式</th><th>涉及作答</th><th>占已确认作答</th></tr></thead>
    <tbody>${results.map(({ name, related, ratio }) => `<tr><td><details><summary>${escapeHTML(name)}</summary><div class="actions">
        ${related.map((row) => `<button type="button" data-response="${escapeHTML(row.id)}">${escapeHTML(row.id)}</button>`).join("")}
        </div></details></td><td>${related.length}</td><td>${ratio}</td></tr>`).join("")}</tbody></table>`
    : "<p class='muted'>暂无已确认的错因记录。</p>";
}

function renderReview(suggestion = null) {
  const item = assignment();
  const response = records().find((row) => row.id === responseId);
  if (!item || !response) {
    $("review").textContent = "请先导入作答。";
    return;
  }
  const max = item.rubric.reduce((sum, row) => sum + row.points, 0);
  const prior = response.review;
  if (!suggestion && !prior && response.analysis?.source === "model") suggestion = response.analysis;
  const current = suggestion?.items ?? prior?.items ?? [];
  $("review").innerHTML = `
    <h3>作答 ${escapeHTML(response.id)}</h3>
    <pre>${escapeHTML(response.answer)}</pre>
    <div class="actions">
      <button type="button" id="suggest">${suggestion ? "重新获取模型建议" : "获取模型评阅建议"}</button>
      <span class="muted">${suggestion ? `模型建议 ${suggestion.total} / ${max} 分 · 请逐项核对`
        : prior ? `已确认 ${prior.items.reduce((sum, row) => sum + row.score, 0)} / ${max} 分` : `本题满分 ${max}`}</span>
    </div>
    <form id="mark">
      ${item.rubric.map((criterion, index) => {
        const value = current.find((row) => row.id === criterion.id);
        const hints = suggestion && value ? `<p class="muted">建议 ${value.score} 分 · ${escapeHTML(value.feedback)}
          ${value.quote ? `（依据「${escapeHTML(value.quote)}」）` : ""}</p>` : "";
        return `<fieldset>
          <legend>${escapeHTML(criterion.title)} · ${criterion.points} 分</legend>
          <p>${escapeHTML(criterion.expected)}</p>
          ${abilities.has(criterion.ability_id) ? `<p class="muted">考查能力 <a href="/?view=course&amp;tab=ability&amp;ability=${encodeURIComponent(criterion.ability_id)}">${escapeHTML(abilities.get(criterion.ability_id))}</a></p>` : ""}
          ${hints}
          <label>得分 <input name="score-${index}" type="number" min="0" max="${criterion.points}" step="1" value="${value?.score ?? ""}" required></label>
          ${criterion.errors.map((error) => `<label>
            <input type="checkbox" name="error-${index}" value="${escapeHTML(error.id)}" ${value?.error_ids.includes(error.id) ? "checked" : ""}>
            ${escapeHTML(error.label)} <span class="muted">· ${escapeHTML(error.detail)}</span>
          </label>`).join("")}
        </fieldset>`;
      }).join("")}
      <label>实际发现的其他错因（每行一项）<textarea name="extra" rows="2" maxlength="1000">${escapeHTML((prior?.extra ?? response.groupTags ?? []).join("\n"))}</textarea></label>
      <label>教师评语 <textarea name="feedback" rows="2" maxlength="2000">${escapeHTML(prior?.feedback)}</textarea></label>
      <button class="primary">确认并继续批阅</button>
    </form>`;

  $("suggest").addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    status("正在获取模型评阅建议…");
    try {
      const payload = item.table ? { case_id: item.id } : { question: item.question, rubric: item.rubric };
      const res = await fetch("/api/teaching/review", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, answer: response.answer }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "模型评阅失败，请核对量规。");
      if (button.isConnected) {
        renderReview(data);
        status("建议已载入。确认后才会计入本题错因统计。");
      }
    } catch (error) {
      if (button.isConnected) status(error.message);
    } finally {
      button.disabled = false;
    }
  });

  $("mark").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const extra = [...new Set(String(form.get("extra")).split(/\r?\n/).map((line) => line.trim()).filter(Boolean))];
    const review = {
      items: item.rubric.map((row, index) => ({
        id: row.id, score: Number(form.get(`score-${index}`)), error_ids: form.getAll(`error-${index}`),
      })),
      extra,
      feedback: String(form.get("feedback")).trim(),
      evidence: [...(prior?.evidence ?? []), ...(response.groupEvidence ?? [])]
        .filter((entry) => extra.includes(entry.label) && response.answer.includes(entry.quote)),
    };
    for (const diagnosis of (suggestion ?? response.analysis)?.diagnoses ?? []) {
      if (review.items.some((item) => item.id === diagnosis.criterion_id && item.error_ids.includes(diagnosis.error_id))) {
        review.evidence.push({ label: diagnosis.label, quote: diagnosis.quote });
      }
    }
    const rows = records().map((row) => row.id === response.id
      ? { ...row, review, groupTags: [], groupEvidence: [] } : row);
    if (setRecords(rows)) {
      responseId = rows.find((row) => !row.review)?.id ?? response.id;
      render();
      status(`已确认 ${response.id} 的评阅。`);
    }
  });
}

function appendResponses(rows) {
  if (!assignment()) return false;
  const existing = records();
  const seen = new Set(existing.map((row) => row.id));
  for (const row of rows) {
    if (!row.id || row.id.length > 100 || !row.answer || row.answer.length > 6000) {
      status("请检查匿名编号与作答是否为空或超出长度。");
      return false;
    }
    if (seen.has(row.id)) {
      status(`编号 ${row.id} 已存在，请修正后重新导入。`);
      return false;
    }
    seen.add(row.id);
  }
  if (!rows.length || !setRecords([...existing, ...rows])) return false;
  responseId = rows[0].id;
  render();
  status(`已导入 ${rows.length} 份作答。`);
  return true;
}

function parseCSV(input) {
  const rows = [];
  let row = [], field = "", quoted = false;
  for (let i = 0; i < input.length; i++) {
    const char = input[i];
    if (char === '"') {
      if (quoted && input[i + 1] === '"') {
        field += '"';
        i++;
      } else if (quoted || !field) {
        quoted = !quoted;
      } else {
        throw new Error("CSV 中包含未转义的双引号。");
      }
    } else if (!quoted && (char === "," || char === "\n" || char === "\r")) {
      row.push(field);
      field = "";
      if (char !== ",") {
        if (char === "\r" && input[i + 1] === "\n") i++;
        if (row.some((cell) => cell.trim())) rows.push(row);
        row = [];
      }
    } else {
      field += char;
    }
  }
  if (quoted) throw new Error("CSV 有未闭合的引号。");
  row.push(field);
  if (row.some((cell) => cell.trim())) rows.push(row);
  const headers = rows.shift()?.map((cell) => cell.trim().toLowerCase());
  const id = headers?.findIndex((name) => name === "id" || name === "匿名编号") ?? -1;
  const answer = headers?.findIndex((name) => name === "answer" || name === "作答") ?? -1;
  if (id < 0 || answer < 0 || !rows.length || rows.some((cells) => cells.length !== headers.length)) {
    throw new Error("CSV 应有「匿名编号,作答」或「id,answer」表头，且各行列数一致。");
  }
  return rows.map((cells) => ({ id: cells[id].trim(), answer: cells[answer].trim() }));
}

function candidateGroups(rows) {
  const groups = new Map();
  for (const row of rows) {
    if (row.review) continue;
    for (const diagnosis of row.analysis?.diagnoses ?? []) {
      const label = diagnosis.label.trim();
      const key = diagnosis.error_id || `${diagnosis.criterion_id}:${label.normalize("NFKC").toLowerCase().replace(/[\s\p{P}]/gu, "")}`;
      if (!groups.has(key)) groups.set(key, { label, members: new Map() });
      const members = groups.get(key).members;
      if (!members.has(row.id)) members.set(row.id, { id: row.id, ...diagnosis });
    }
  }
  return [...groups.values()].sort((a, b) => b.members.size - a.members.size);
}

function renderCandidates() {
  const rows = records();
  const pending = rows.filter((row) => !row.review);
  const scanned = pending.filter((row) => row.analysis).length;
  $("scan-examples").disabled = !!scanController || !pending.length;
  $("scan-model").disabled = !!scanController || !pending.length;
  $("stop-scan").disabled = !scanController;
  $("scan-summary").textContent = `待批阅 ${pending.length} 份，已生成诊断 ${scanned} 份。`;
  const groups = candidateGroups(rows);
  $("candidates").innerHTML = groups.length ? groups.map((group, index) => `<details class="candidate" ${index === 0 ? "open" : ""}>
    <summary>${escapeHTML(group.label)} · ${group.members.size} 份候选作答</summary>
    <form class="candidate-form" data-index="${index}">
      <label>确认用的错因名称 <input name="label" value="${escapeHTML(group.label)}" required maxlength="80"></label>
      ${[...group.members.values()].map((member) => `<div>
        <label><input type="checkbox" name="response" value="${escapeHTML(member.id)}"
          ${rows.find((row) => row.id === member.id)?.groupTags?.includes(group.label) ? "checked" : ""}>
          ${escapeHTML(member.id)} · ${escapeHTML(member.reason)}
          <button type="button" data-response="${escapeHTML(member.id)}">查看原答卷</button>
        </label>
        <blockquote>「${escapeHTML(member.quote)}」</blockquote>
      </div>`).join("")}
      <button>把勾选的错因加入批阅</button>
    </form>
  </details>`).join("") : "<p class='muted'>暂无可复核的候选错因。</p>";
}

async function scanResponses(useModel) {
  if (scanController) return;
  const item = assignment();
  const pending = records().filter((row) => !row.review
    && row.analysis?.source !== "model" && (useModel || !row.analysis));
  if (!item || !pending.length) {
    status("当前没有需要扫描的待批阅作答。");
    return;
  }
  const controller = new AbortController();
  scanController = controller;
  renderCandidates();
  let done = 0;
  try {
    for (const response of pending) {
      if (controller.signal.aborted) break;
      status(`正在分析 ${done + 1} / ${pending.length} 份 · ${item.title}`);
      const payload = item.table ? { case_id: item.id } : { question: item.question, rubric: item.rubric };
      const res = await fetch("/api/teaching/diagnose", {
        method: "POST", headers: { "Content-Type": "application/json" },
        signal: controller.signal, body: JSON.stringify({ ...payload, answer: response.answer, use_model: useModel }),
      });
      const result = await res.json();
      if (!res.ok) throw new Error(typeof result.detail === "string" ? result.detail : "诊断请求失败。");
      const current = local.responses[item.id] ?? [];
      const updated = current.map((row) => row.id === response.id && !row.review
        ? { ...row, analysis: result } : row);
      if (!persist({ ...local, responses: { ...local.responses, [item.id]: updated } })) return;
      done++;
    }
    status(`已保存 ${done} / ${pending.length} 份候选诊断。`);
  } catch (error) {
    status(controller.signal.aborted ? `已停止，保留 ${done} 份已完成的结果。` : `${error.message} 已保存 ${done} 份。`);
  } finally {
    scanController = null;
    renderCandidates();
    if (!$("mark")) renderReview();
  }
}

function addCriterion() {
  const id = ++criterionSequence;
  const field = document.createElement("fieldset");
  field.dataset.id = String(id);
  field.innerHTML = `<legend>评分项</legend>
    <label>名称 <input name="title-${id}" required maxlength="100"></label>
    <label>满分 <input name="points-${id}" type="number" required min="1" max="100" value="5"></label>
    <label>得分要点 <textarea name="expected-${id}" required maxlength="800" rows="2"></textarea></label>
    <label>预设错因（每行一条，可用「错因｜错答原话」附一个示例） <textarea name="errors-${id}" maxlength="1200" rows="2"></textarea></label>
    <button type="button">移除此项</button>`;
  field.querySelector("button").onclick = () => {
    if ($("criteria").children.length > 1) field.remove();
  };
  $("criteria").append(field);
}

$("assignment").addEventListener("change", (event) => {
  assignmentId = event.target.value;
  responseId = "";
  status("");
  render();
});
$("response").addEventListener("change", (event) => {
  responseId = event.target.value;
  status("");
  renderReview();
});
$("add").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  if (appendResponses([{ id: form.get("id").trim(), answer: form.get("answer").trim() }])) event.currentTarget.reset();
});
$("batch").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const lines = form.get("rows").split(/\r?\n/).filter((line) => line.trim());
  const parsed = lines.map((line) => line.split("\t"));
  if (parsed.some((row) => row.length !== 2)) {
    status("每行应为两列，用一个制表符分隔匿名编号与作答。");
    return;
  }
  if (appendResponses(parsed.map(([id, answer]) => ({ id: id.trim(), answer: answer.trim() })))) event.currentTarget.reset();
});
$("fill-demo").onclick = () => {
  $("batch").elements.rows.value = assignment().demo_responses.map((row) => row.join("\t")).join("\n");
  status("已填入教学演示作答，点击批量导入后才会进入本题队列。");
};
$("response-file").addEventListener("change", async (event) => {
  const input = event.currentTarget;
  const file = input.files[0];
  const target = assignmentId;
  if (!file) return;
  try {
    const rows = parseCSV(await file.text());
    if (target === assignmentId) appendResponses(rows);
    else status("题目已切换。请选择要导入的题目后重试。");
  } catch (error) {
    status(error.message);
  } finally {
    input.value = "";
  }
});
$("scan-examples").onclick = () => void scanResponses(false);
$("scan-model").onclick = () => void scanResponses(true);
$("stop-scan").onclick = () => scanController?.abort();

for (const area of [$("candidates"), $("patterns")]) {
  area.addEventListener("click", (event) => {
    const id = event.target.closest("button[data-response]")?.dataset.response;
    if (!id) return;
    responseId = id;
    $("response").value = id;
    renderReview();
    $("review").scrollIntoView({ block: "start" });
  });
}
$("candidates").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const group = candidateGroups(records())[Number(event.target.dataset.index)];
  const label = String(form.get("label") ?? "").trim();
  const selected = new Set(form.getAll("response"));
  if (!label || !selected.size || !group) {
    status("请输入错因名称并勾选适用的作答。");
    return;
  }
  if (setRecords(records().map((row) => {
    const match = group.members.get(row.id);
    if (!selected.has(row.id) || row.review || !match) return row;
    const evidence = (row.groupEvidence ?? []).filter((entry) => entry.label !== label);
    return { ...row, groupTags: [...new Set([...(row.groupTags ?? []), label])],
      groupEvidence: [...evidence, { label, quote: match.quote }] };
  }))) {
    renderReview();
    renderCandidates();
    status(`已把「${label}」加入 ${selected.size} 份待确认批阅。`);
  }
});
$("add-criterion").onclick = () => {
  if ($("criteria").children.length < 12) addCriterion();
  else status("每题最多 12 个评分项。");
};
$("create").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const text = (name) => String(form.get(name) ?? "").trim();
  const rubric = [...$("criteria").children].map((field, index) => {
    const id = field.dataset.id;
    const criterionId = `C${index + 1}`;
    const labels = [...new Set(text(`errors-${id}`).split(/\r?\n/).map((line) => line.trim()).filter(Boolean))];
    return {
      id: criterionId,
      title: text(`title-${id}`),
      points: Number(form.get(`points-${id}`)),
      expected: text(`expected-${id}`),
      errors: labels.map((line, n) => {
        const [label, ...examples] = line.split("｜").map((part) => part.trim());
        return { id: `${criterionId}-E${n + 1}`, label, detail: "", examples: examples.filter(Boolean).slice(0, 12) };
      }),
    };
  });
  if (!text("title") || !text("question") || rubric.some((row) => !row.title || !row.expected
    || row.errors.length > 12 || row.errors.some((error) => !error.label || error.label.length > 100
      || error.examples.some((example) => example.length > 100)))) {
    status("请填写名称、题目与得分要点。每个评分项最多 12 个错因，每项最多 100 字。");
    return;
  }
  const item = { id: `local-${Date.now()}-${Math.random().toString(36).slice(2)}`, title: text("title"), question: text("question"), rubric };
  if (persist({ ...local, custom: [...local.custom, item] })) {
    assignmentId = item.id;
    responseId = "";
    event.currentTarget.reset();
    event.currentTarget.closest("details").open = false;
    $("criteria").replaceChildren();
    addCriterion();
    render();
    status("已保存量规，可以导入本题作答。");
  }
});

function download(text, name, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

$("export").onclick = () => download(JSON.stringify({ version: 1, ...local }, null, 2), "堆物理-主观题批阅备份.json", "application/json");
$("export-report").onclick = () => {
  const rows = records();
  const confirmed = rows.filter((row) => row.review);
  const lines = [assignment().title, `已确认 ${confirmed.length} / ${rows.length} 份`, ""];
  for (const { name, related, ratio } of confirmedPatterns(confirmed)) {
    lines.push(`${name} · ${related.length} 份 · ${ratio}`);
    lines.push(`匿名编号 · ${related.map((row) => row.id).join("、")}`);
    const example = related.find((row) => row.review.evidence?.some((entry) => entry.label === name));
    if (example) {
      const evidence = example.review.evidence.find((entry) => entry.label === name);
      lines.push(`代表作答 ${example.id} · 「${evidence.quote}」`);
    }
    lines.push("");
  }
  download(lines.join("\r\n"), "堆物理-错因复盘.txt", "text/plain;charset=utf-8");
};

function loadBackup(data) {
  if (data?.version !== 1 || !Array.isArray(data.custom) || !data.responses || Array.isArray(data.responses)
    || typeof data.responses !== "object") throw new Error("备份格式无效。");
  const validRubric = (rubric) => Array.isArray(rubric) && rubric.length && rubric.every((row) =>
    typeof row?.id === "string" && typeof row.title === "string" && typeof row.expected === "string"
    && Number.isInteger(row.points) && row.points > 0 && row.points <= 100
    && Array.isArray(row.errors) && row.errors.every((error) => typeof error?.id === "string" && typeof error.label === "string"));
  if (data.custom.some((item) => typeof item?.id !== "string" || !item.id.startsWith("local-")
    || typeof item.title !== "string" || typeof item.question !== "string" || !validRubric(item.rubric))) {
    throw new Error("备份中的量规无效。");
  }
  const validReview = (review) => !review || (Array.isArray(review.items) && Array.isArray(review.extra)
    && review.extra.every((label) => typeof label === "string") && typeof review.feedback === "string"
    && review.items.every((row) => typeof row?.id === "string" && Number.isInteger(row.score)
      && row.score >= 0 && row.score <= 100 && Array.isArray(row.error_ids)));
  const validEvidence = (value) => value === undefined || (Array.isArray(value) && value.every((entry) =>
    typeof entry?.label === "string" && typeof entry.quote === "string"));
  const validAnalysis = (value) => value === undefined || (
    ["examples", "model"].includes(value?.source) && Array.isArray(value.items)
    && value.items.every((entry) => typeof entry?.id === "string" && Number.isInteger(entry.score)
      && entry.score >= 0 && entry.score <= 100 && Array.isArray(entry.error_ids))
    && Array.isArray(value.diagnoses) && validEvidence(value.diagnoses)
    && value.diagnoses.every((entry) => typeof entry.criterion_id === "string" && typeof entry.error_id === "string")
  );
  if (Object.values(data.responses).some((rows) => !Array.isArray(rows) || rows.some((row) =>
    typeof row?.id !== "string" || typeof row.answer !== "string" || !validReview(row.review)
    || !validEvidence(row.review?.evidence) || !validEvidence(row.groupEvidence) || !validAnalysis(row.analysis)
    || (row.groupTags !== undefined && (!Array.isArray(row.groupTags) || row.groupTags.some((tag) => typeof tag !== "string")))))) {
    throw new Error("备份中的批阅记录无效。");
  }
  return {
    custom: data.custom.map(({ id, title, question, rubric }) => ({ id, title, question, rubric })),
    responses: data.responses,
  };
}

$("restore").addEventListener("change", async (event) => {
  const input = event.currentTarget;
  const file = input.files[0];
  if (!file) return;
  try {
    const data = loadBackup(JSON.parse(await file.text()));
    const custom = [...local.custom, ...data.custom.filter((item) => !local.custom.some((saved) => saved.id === item.id))];
    const responses = { ...local.responses };
    for (const [id, incoming] of Object.entries(data.responses)) {
      if (![...builtIn, ...custom].some((item) => item.id === id)) continue;
      const saved = new Map((responses[id] ?? []).map((row) => [row.id, row]));
      for (const row of incoming) {
        const current = saved.get(row.id);
        if (!current || (!current.review && row.review && current.answer === row.answer)) saved.set(row.id, row);
      }
      responses[id] = [...saved.values()];
    }
    if (persist({ custom, responses })) {
      render();
      status("已合并备份，保留本机已有的确认记录。");
    }
  } catch (error) {
    status(error.message);
  } finally {
    input.value = "";
  }
});

try {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) local = loadBackup({ version: 1, ...JSON.parse(saved) });
} catch (error) {
  status(error.message);
}
addCriterion();
render();
fetch("/api/teaching/course").then(async (res) => {
  if (!res.ok) throw new Error("课程案例加载失败。");
  const data = await res.json();
  builtIn = data.cases;
  abilities = new Map(data.abilities.map((item) => [item.id, item.title]));
  render();
}).catch((error) => status(error.message));
