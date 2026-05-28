const state = {
  schema: null,
  reports: [],
  dashboard: null,
  tableSorts: {},
};

const $ = (id) => document.getElementById(id);

const COLUMN_LABELS = {
  business_date: "Дата",
  organization_name: "Филиал",
  category_name: "Категория",
  product_name: "Товар",
  payment_type: "Тип оплаты",
  payment_group: "Группа оплаты",
  net_revenue: "Выручка",
  gross_revenue: "Валовая выручка",
  orders: "Заказы",
  orders_count: "Заказы",
  avg_check: "Средний чек",
  quantity: "Количество",
  payment_sum: "Сумма оплат",
  deliveries: "Доставки",
  late_deliveries: "Опоздания",
  late_rate: "Доля опозданий",
  avg_delivery_minutes: "Среднее время",
  selected_products_count: "Товаров найдено",
  selected_products: "Товары",
  selected_categories: "Категории",
  selected_orders_lifetime: "Покупок lifetime",
  selected_qty_lifetime: "Кол-во lifetime",
  selected_revenue_lifetime: "Выручка lifetime",
  orders_in_period: "Заказов за период",
  revenue_in_period: "Выручка за период",
  first_order_in_period: "Первый заказ",
  last_order_in_period: "Последний заказ",
  customer_orders_lifetime: "Заказов всего",
  customer_revenue_lifetime: "Выручка всего",
  guest_name: "Гость",
  customer_type: "Тип гостя",
  birthdate: "Дата рождения",
  gender: "Пол",
};

async function api(path, payload = null) {
  const options = payload
    ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }
    : {};
  const response = await fetch(path, options);
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return response.json();
}

function option(value, label) {
  const el = document.createElement("option");
  el.value = value;
  el.textContent = label;
  return el;
}

function setStatus(id, text, isError = false) {
  const el = $(id);
  el.textContent = text;
  el.style.color = isError ? "#b42318" : "#657282";
}

function formatValue(value, format = "") {
  if (value === null || value === undefined || value === "") return "—";
  const num = Number(value);
  if (!Number.isFinite(num)) return String(value);
  if (format === "money") {
    return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(num) + " ₽";
  }
  if (format === "percent") {
    return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(num * 100) + "%";
  }
  if (format === "integer") {
    return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(num);
  }
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(num);
}

function shiftDate(isoDate, days) {
  const date = new Date(`${isoDate}T00:00:00`);
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

function setQuickRange(range) {
  const latest = state.dashboard?.date_to || $("dashboardDateTo").value;
  if (!latest) return;
  let from = latest;
  let to = latest;
  if (range === "yesterday") {
    from = shiftDate(latest, -1);
    to = from;
  } else if (range === "7d") {
    from = shiftDate(latest, -6);
  } else if (range === "30d") {
    from = shiftDate(latest, -29);
  }
  $("dashboardDateFrom").value = from;
  $("dashboardDateTo").value = to;
  $("reportDateFrom").value = from;
  $("reportDateTo").value = to;
  document.querySelectorAll(".quick").forEach((button) => button.classList.toggle("active", button.dataset.range === range));
  loadDashboard();
}

function renderTable(containerId, columns, rows, maxRows = null) {
  const wrap = $(containerId);
  wrap.innerHTML = "";
  if (!rows || !rows.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "Нет строк под выбранные условия";
    wrap.append(empty);
    return;
  }
  const sort = state.tableSorts[containerId] || { column: null, dir: null };
  const sortedRows = [...rows];
  if (sort.column && sort.dir) {
    const dir = sort.dir === "desc" ? -1 : 1;
    sortedRows.sort((a, b) => {
      const left = a[sort.column];
      const right = b[sort.column];
      if (left === right) return 0;
      if (left === null || left === undefined || left === "") return 1;
      if (right === null || right === undefined || right === "") return -1;
      const leftNum = Number(left);
      const rightNum = Number(right);
      if (Number.isFinite(leftNum) && Number.isFinite(rightNum)) return (leftNum - rightNum) * dir;
      return String(left).localeCompare(String(right), "ru", { numeric: true, sensitivity: "base" }) * dir;
    });
  }
  const visibleRows = maxRows ? sortedRows.slice(0, maxRows) : sortedRows;
  const table = document.createElement("table");
  const numericColumns = new Set(columns.filter((col) => rows.some((row) => {
    const value = row[col];
    return value !== null && value !== "" && Number.isFinite(Number(value));
  })));
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  columns.forEach((col) => {
    const th = document.createElement("th");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "sort-head";
    const nextDir = sort.column !== col || !sort.dir ? "desc" : sort.dir === "desc" ? "asc" : null;
    const sortMark = sort.column === col && sort.dir ? (sort.dir === "desc" ? " ↓" : " ↑") : "";
    button.textContent = `${COLUMN_LABELS[col] || col}${sortMark}`;
    button.title = nextDir === "desc" ? "Сортировать по убыванию" : nextDir === "asc" ? "Сортировать по возрастанию" : "Сбросить сортировку";
    button.addEventListener("click", () => {
      state.tableSorts[containerId] = { column: nextDir ? col : null, dir: nextDir };
      renderTable(containerId, columns, rows, maxRows);
    });
    th.append(button);
    if (numericColumns.has(col)) th.className = "num";
    headRow.append(th);
  });
  thead.append(headRow);
  const tbody = document.createElement("tbody");
  visibleRows.forEach((row) => {
    const tr = document.createElement("tr");
    columns.forEach((col) => {
      const td = document.createElement("td");
      const value = row[col];
      td.textContent = value === null || value === undefined ? "" : value;
      if (numericColumns.has(col)) td.className = "num";
      tr.append(td);
    });
    tbody.append(tr);
  });
  table.append(thead, tbody);
  wrap.append(table);
}

function objectColumns(rows) {
  return rows && rows[0] ? Object.keys(rows[0]) : [];
}

function renderMiniBars(container, rows, labelKey, valueKey) {
  container.innerHTML = "";
  const values = rows.map((row) => Math.abs(Number(row[valueKey]))).filter(Number.isFinite);
  const max = Math.max(...values, 0);
  rows.slice(0, 8).forEach((row) => {
    const item = document.createElement("div");
    item.className = "mini-row";
    const label = document.createElement("span");
    label.textContent = row[labelKey] || "—";
    label.title = row[labelKey] || "";
    const value = document.createElement("strong");
    value.textContent = formatValue(row[valueKey]);
    const track = document.createElement("div");
    track.className = "mini-track";
    const fill = document.createElement("div");
    fill.className = "mini-fill";
    fill.style.width = max ? `${Math.max(3, Math.round((Math.abs(Number(row[valueKey])) / max) * 100))}%` : "0";
    track.append(fill);
    item.append(label, value, track);
    container.append(item);
  });
}

async function loadDashboard() {
  $("kpiGrid").innerHTML = '<div class="empty">Загрузка...</div>';
  const query = new URLSearchParams();
  if ($("dashboardDateFrom")?.value) query.set("date_from", $("dashboardDateFrom").value);
  if ($("dashboardDateTo")?.value) query.set("date_to", $("dashboardDateTo").value);
  const data = await api(`/api/dashboard${query.toString() ? `?${query}` : ""}`);
  state.dashboard = data;
  if (data.date_from && !$("dashboardDateFrom").value) $("dashboardDateFrom").value = data.date_from;
  if (data.date_to && !$("dashboardDateTo").value) $("dashboardDateTo").value = data.date_to;
  if (data.date_from && !$("reportDateFrom").value) $("reportDateFrom").value = data.date_from;
  if (data.date_to && !$("reportDateTo").value) $("reportDateTo").value = data.date_to;
  $("dashboardPeriod").textContent = data.date_from && data.date_to ? `Период: ${data.date_from} — ${data.date_to}` : "Нет данных";

  const kpiGrid = $("kpiGrid");
  kpiGrid.innerHTML = "";
  data.kpis.forEach((kpi) => {
    const card = document.createElement("article");
    card.className = "kpi-card";
    card.innerHTML = `<span>${kpi.label}</span><strong>${formatValue(kpi.value, kpi.format)}</strong>`;
    kpiGrid.append(card);
  });

  const widgetGrid = $("widgetGrid");
  widgetGrid.innerHTML = "";
  data.widgets.forEach((widget) => {
    const card = document.createElement("article");
    card.className = "widget-card";
    const head = document.createElement("div");
    head.className = "widget-head";
    head.innerHTML = `<h3>${widget.title}</h3>`;
    const body = document.createElement("div");
    body.className = "widget-body";
    if (widget.type === "line") {
      renderMiniBars(body, widget.rows, widget.label, widget.metric);
    } else {
      const tableBox = document.createElement("div");
      tableBox.className = "compact-table";
      tableBox.id = `widget-${widget.id}`;
      body.append(tableBox);
      setTimeout(() => renderTable(tableBox.id, objectColumns(widget.rows), widget.rows, 8), 0);
    }
    card.append(head, body);
    widgetGrid.append(card);
  });
}

function renderSavedReports() {
  const wrap = $("savedReports");
  wrap.innerHTML = "";
  state.reports.forEach((report) => {
    const card = document.createElement("article");
    card.className = "saved-card";
    card.innerHTML = `
      <div>
        <span class="tag">${report.kind}</span>
        <h3>${report.name}</h3>
        <p>${report.description}</p>
      </div>
    `;
    const actions = document.createElement("div");
    actions.className = "actions";
    const open = document.createElement("button");
    open.type = "button";
    open.textContent = "Открыть в конструкторе";
    open.addEventListener("click", () => openReport(report));
    actions.append(open);
    card.append(actions);
    wrap.append(card);
  });
}

function checkedValues(containerId) {
  return [...$(containerId).querySelectorAll("input:checked")].map((input) => input.value);
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

function currentSubject() {
  return state.schema.subjects[$("subject").value];
}

function labelForField(key) {
  const subject = currentSubject();
  return subject.dimensions[key] || subject.metrics[key] || subject.filters[key] || COLUMN_LABELS[key] || key;
}

function renderSubject(config = null) {
  const subject = currentSubject();
  $("subjectDescription").textContent = subject.description || "";
  const metricKeys = Object.keys(subject.metrics);
  const defaultMetrics = metricKeys.includes("net_revenue")
    ? ["net_revenue", ...(metricKeys.includes("orders") ? ["orders"] : [])]
    : metricKeys.slice(0, 2);
  const dimensions = config?.dimensions || (subject.dimensions.business_date ? ["business_date"] : Object.keys(subject.dimensions).slice(0, 1));
  const metrics = config?.metrics || defaultMetrics;
  renderChecks("dimensions", subject.dimensions, dimensions);
  renderChecks("metrics", subject.metrics, metrics);
  $("filters").innerHTML = "";
  $("limit").value = config?.limit || 50;
  $("orderDir").value = config?.order_dir || "desc";
  renderOrderOptions(config?.order_by);
}

function renderOrderOptions(selected = null) {
  const orderBy = $("orderBy");
  const subject = currentSubject();
  orderBy.innerHTML = "";
  checkedValues("dimensions").forEach((key) => orderBy.append(option(key, subject.dimensions[key] || key)));
  checkedValues("metrics").forEach((key) => orderBy.append(option(key, subject.metrics[key] || key)));
  if (selected && [...orderBy.options].some((opt) => opt.value === selected)) orderBy.value = selected;
}

function addFilterRow(initial = {}) {
  const subject = currentSubject();
  const row = document.createElement("div");
  row.className = "filter-row";
  const field = document.createElement("select");
  Object.entries(subject.filters).forEach(([key, label]) => field.append(option(key, label)));
  field.value = initial.field || Object.keys(subject.filters)[0];
  const op = document.createElement("select");
  [["eq", "="], ["neq", "!="], ["contains", "содержит"], ["not_contains", "не содержит"], ["gte", ">="], ["lte", "<="], ["gt", ">"], ["lt", "<"], ["between", "между"], ["is_null", "пусто"], ["not_null", "не пусто"]].forEach(([value, label]) => op.append(option(value, label)));
  op.value = initial.op || "eq";
  const value = document.createElement("input");
  value.type = "text";
  value.placeholder = "значение или от..до";
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
  const filters = [...$("filters").querySelectorAll(".filter-row")].map((row) => {
    const [field, op, value] = row.querySelectorAll("select, input");
    const result = { field: field.value, op: op.value, value: value.value };
    if (op.value === "between") {
      const parts = value.value.split("..").map((part) => part.trim());
      result.value = parts[0] || "";
      result.value2 = parts[1] || "";
    }
    return result;
  });
  const subject = currentSubject();
  const dateFrom = $("reportDateFrom").value;
  const dateTo = $("reportDateTo").value;
  if (subject.filters.business_date && dateFrom && dateTo) {
    filters.push({ field: "business_date", op: "between", value: dateFrom, value2: dateTo });
  } else if (subject.filters.business_date && dateFrom) {
    filters.push({ field: "business_date", op: "gte", value: dateFrom });
  } else if (subject.filters.business_date && dateTo) {
    filters.push({ field: "business_date", op: "lte", value: dateTo });
  }
  return filters;
}

function reportPayload() {
  return {
    subject: $("subject").value,
    dimensions: checkedValues("dimensions"),
    metrics: checkedValues("metrics"),
    filters: collectFilters(),
    order_by: $("orderBy").value,
    order_dir: $("orderDir").value,
    limit: Number($("limit").value || 50),
  };
}

async function runReport() {
  setStatus("status", "Выполняется...");
  try {
    const data = await api("/api/report", reportPayload());
    const dateFrom = $("reportDateFrom").value || "начало";
    const dateTo = $("reportDateTo").value || "сейчас";
    const dimensions = checkedValues("dimensions").map(labelForField).join(", ") || "без группировки";
    $("resultMeta").textContent = `${$("subject").selectedOptions[0].textContent}: ${dimensions} · период ${dateFrom} — ${dateTo}`;
    renderTable("tableWrap", data.columns, data.rows);
    setStatus("status", `${data.rows.length} строк`);
  } catch (error) {
    setStatus("status", error.message, true);
  }
}

async function downloadCsv(path, payload, name) {
  const response = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
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

function switchTab(tabName) {
  document.querySelectorAll(".tab").forEach((el) => el.classList.toggle("active", el.dataset.tab === tabName));
  document.querySelectorAll(".page").forEach((el) => el.classList.toggle("active-page", el.id === tabName));
}

function openReport(report) {
  const config = report.config || report;
  $("subject").value = config.subject || "sales";
  if (!$("reportDateFrom").value && $("dashboardDateFrom").value) $("reportDateFrom").value = $("dashboardDateFrom").value;
  if (!$("reportDateTo").value && $("dashboardDateTo").value) $("reportDateTo").value = $("dashboardDateTo").value;
  $("builderContext").textContent = report.name ? `Открыт отчет: ${report.name}` : "Настройте период, группировки, метрики и фильтры.";
  renderSubject(config);
  switchTab("builder");
  runReport();
}

async function init() {
  const [schema, reports] = await Promise.all([api("/api/schema"), api("/api/saved-reports")]);
  state.schema = schema;
  state.reports = reports.reports || [];

  Object.entries(state.schema.subjects).forEach(([key, cfg]) => $("subject").append(option(key, cfg.label)));
  $("subject").value = "sales";
  renderSubject();
  renderSavedReports();
  await loadDashboard();

  $("refreshDashboard").addEventListener("click", loadDashboard);
  ["dashboardDateFrom", "dashboardDateTo"].forEach((id) => $(id).addEventListener("change", () => {
    document.querySelectorAll(".quick").forEach((button) => button.classList.remove("active"));
  }));
  document.querySelectorAll(".quick").forEach((button) => button.addEventListener("click", () => setQuickRange(button.dataset.range)));
  $("subject").addEventListener("change", () => renderSubject());
  $("dimensions").addEventListener("change", () => renderOrderOptions());
  $("metrics").addEventListener("change", () => renderOrderOptions());
  $("addFilter").addEventListener("click", () => addFilterRow());
  $("runReport").addEventListener("click", runReport);
  $("exportReport").addEventListener("click", async () => {
    setStatus("status", "Готовлю CSV...");
    try {
      await downloadCsv("/api/export.csv", reportPayload(), "report.csv");
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
  document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => switchTab(tab.dataset.tab)));
}

init().catch((error) => {
  document.body.innerHTML = `<main><div class="empty">${error.message}</div></main>`;
});
