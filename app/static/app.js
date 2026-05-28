const state = {
  schema: null,
  subject: null,
};

const $ = (id) => document.getElementById(id);

function setStatus(id, text, isError = false) {
  const el = $(id);
  el.textContent = text;
  el.style.color = isError ? "#b42318" : "#657282";
}

async function api(path, payload = null) {
  const options = payload
    ? {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }
    : {};
  const response = await fetch(path, options);
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const data = await response.json();
      message = data.error || message;
    } catch (_) {
      // ignore
    }
    throw new Error(message);
  }
  return response.json();
}

function option(value, label) {
  const el = document.createElement("option");
  el.value = value;
  el.textContent = label;
  return el;
}

function renderChecks(containerId, values, selected = []) {
  const container = $(containerId);
  container.innerHTML = "";
  Object.entries(values).forEach(([key, label]) => {
    const row = document.createElement("label");
    row.className = "check-row";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = key;
    input.checked = selected.includes(key);
    const span = document.createElement("span");
    span.textContent = label;
    row.append(input, span);
    container.append(row);
  });
}

function checkedValues(containerId) {
  return [...$(containerId).querySelectorAll("input:checked")].map((input) => input.value);
}

function currentSubject() {
  return state.schema.subjects[$("subject").value];
}

function renderSubject() {
  const key = $("subject").value;
  state.subject = key;
  const subject = currentSubject();
  $("subjectDescription").textContent = subject.description || "";

  const defaultDims = subject.dimensions.business_date ? ["business_date"] : Object.keys(subject.dimensions).slice(0, 1);
  const defaultMetrics = Object.keys(subject.metrics).slice(0, 2);
  renderChecks("dimensions", subject.dimensions, defaultDims);
  renderChecks("metrics", subject.metrics, defaultMetrics);
  renderOrderOptions();
  $("filters").innerHTML = "";
}

function renderOrderOptions() {
  const orderBy = $("orderBy");
  const subject = currentSubject();
  orderBy.innerHTML = "";
  checkedValues("dimensions").forEach((key) => orderBy.append(option(key, subject.dimensions[key] || key)));
  checkedValues("metrics").forEach((key) => orderBy.append(option(key, subject.metrics[key] || key)));
}

function addFilterRow(initial = {}) {
  const subject = currentSubject();
  const row = document.createElement("div");
  row.className = "filter-row";

  const field = document.createElement("select");
  Object.entries(subject.filters).forEach(([key, label]) => field.append(option(key, label)));
  field.value = initial.field || Object.keys(subject.filters)[0];

  const op = document.createElement("select");
  [
    ["eq", "="],
    ["neq", "!="],
    ["contains", "contains"],
    ["not_contains", "not contains"],
    ["gte", ">="],
    ["lte", "<="],
    ["gt", ">"],
    ["lt", "<"],
    ["between", "between"],
    ["is_null", "is null"],
    ["not_null", "not null"],
  ].forEach(([value, label]) => op.append(option(value, label)));
  op.value = initial.op || "eq";

  const value = document.createElement("input");
  value.type = "text";
  value.placeholder = "value";
  value.value = initial.value || "";

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "remove";
  remove.textContent = "×";
  remove.addEventListener("click", () => row.remove());

  row.append(field, op, value, remove);
  $("filters").append(row);
}

function collectFilters() {
  return [...$("filters").querySelectorAll(".filter-row")].map((row) => {
    const [field, op, value] = row.querySelectorAll("select, input");
    const result = { field: field.value, op: op.value, value: value.value };
    if (op.value === "between") {
      const parts = value.value.split("..").map((part) => part.trim());
      result.value = parts[0] || "";
      result.value2 = parts[1] || "";
    }
    return result;
  });
}

function reportPayload() {
  return {
    subject: $("subject").value,
    dimensions: checkedValues("dimensions"),
    metrics: checkedValues("metrics"),
    filters: collectFilters(),
    order_by: $("orderBy").value,
    order_dir: $("orderDir").value,
    limit: Number($("limit").value || 500),
  };
}

function renderTable(containerId, columns, rows) {
  const wrap = $(containerId);
  wrap.innerHTML = "";
  if (!rows.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "Нет строк под выбранные условия";
    wrap.append(empty);
    return;
  }
  const table = document.createElement("table");
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  columns.forEach((col) => {
    const th = document.createElement("th");
    th.textContent = col;
    headRow.append(th);
  });
  thead.append(headRow);
  const tbody = document.createElement("tbody");
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    columns.forEach((col) => {
      const td = document.createElement("td");
      const value = row[col];
      td.textContent = value === null || value === undefined ? "" : value;
      if (typeof value === "number" || /^-?\d+(\.\d+)?$/.test(String(value))) {
        td.className = "num";
      }
      tr.append(td);
    });
    tbody.append(tr);
  });
  table.append(thead, tbody);
  wrap.append(table);
}

async function runReport() {
  setStatus("status", "Выполняется...");
  try {
    const data = await api("/api/report", reportPayload());
    renderTable("tableWrap", data.columns, data.rows);
    setStatus("status", `${data.rows.length} строк`);
  } catch (error) {
    setStatus("status", error.message, true);
  }
}

async function downloadCsv(path, payload, name) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  const blob = await response.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(link.href);
}

function segmentPayload() {
  return {
    mode: $("segmentMode").value,
    term: $("segmentTerm").value,
    lifetime_op: $("segmentLifetimeOp").value,
    lifetime_count: Number($("segmentLifetimeCount").value || 1),
    date_from: $("segmentDateFrom").value,
    date_to: $("segmentDateTo").value,
    min_orders: Number($("segmentMinOrders").value || 1),
    limit: Number($("segmentLimit").value || 500),
  };
}

async function runSegment() {
  setStatus("segmentStatus", "Выполняется...");
  try {
    const data = await api("/api/customer-segment", segmentPayload());
    renderTable("segmentTableWrap", data.columns, data.rows);
    setStatus("segmentStatus", `${data.rows.length} строк`);
  } catch (error) {
    setStatus("segmentStatus", error.message, true);
  }
}

async function init() {
  state.schema = await api("/api/schema");
  const subject = $("subject");
  Object.entries(state.schema.subjects).forEach(([key, cfg]) => {
    subject.append(option(key, cfg.label));
  });
  subject.value = "sales";
  renderSubject();

  subject.addEventListener("change", renderSubject);
  $("dimensions").addEventListener("change", renderOrderOptions);
  $("metrics").addEventListener("change", renderOrderOptions);
  $("addFilter").addEventListener("click", () => addFilterRow());
  $("runReport").addEventListener("click", runReport);
  $("exportReport").addEventListener("click", async () => {
    setStatus("status", "Готовлю CSV...");
    try {
      await downloadCsv("/api/export.csv", reportPayload(), "olap_report.csv");
      setStatus("status", "CSV готов");
    } catch (error) {
      setStatus("status", error.message, true);
    }
  });

  $("runSegment").addEventListener("click", runSegment);
  $("exportSegment").addEventListener("click", async () => {
    setStatus("segmentStatus", "Готовлю CSV...");
    try {
      await downloadCsv("/api/customer-segment.csv", segmentPayload(), "customer_segment.csv");
      setStatus("segmentStatus", "CSV готов");
    } catch (error) {
      setStatus("segmentStatus", error.message, true);
    }
  });

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((el) => el.classList.remove("active"));
      document.querySelectorAll(".panel").forEach((el) => el.classList.remove("active-panel"));
      tab.classList.add("active");
      document.getElementById(tab.dataset.tab).classList.add("active-panel");
    });
  });

  await runReport();
}

init().catch((error) => {
  setStatus("status", error.message, true);
});
