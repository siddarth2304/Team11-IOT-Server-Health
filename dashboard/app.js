const $ = selector => document.querySelector(selector);
let selectedServer = "";

const get = async url => {
  const response = await fetch(url);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
};
const pct = value => `${(100 * Number(value)).toFixed(1)}%`;
const n = value => Number(value).toFixed(1);
const label = value => String(value || "unknown").replaceAll("_", " ");
const esc = value => String(value ?? "").replace(/[&<>"']/g, character => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[character]);

function serverRow(row) {
  const condition = row.predicted_condition || "unknown";
  const action = row.action === "none" ? "No action" : label(row.action);
  let explanations = [];
  try { explanations = JSON.parse(row.explanation_json || "[]"); } catch (_) { explanations = []; }
  const primaryFactor = explanations[0]?.factor || "Assessment pending";
  return `<tr>
    <td><b>${esc(row.server_id)}</b></td>
    <td><span class="status-badge ${esc(condition)}">${esc(label(condition))}</span><small class="explanation">${esc(primaryFactor)}</small></td>
    <td><b class="health-score ${esc(row.risk_level)}">${n(row.health_score)}</b><small class="explanation">${esc(label(row.risk_level))} risk</small></td>
    <td>${pct(row.confidence)}</td>
    <td>${n(row.cpu_pct)}%</td><td>${n(row.predicted_cpu_15m)}%</td>
    <td>${n(row.memory_pct)}%</td><td>${n(row.predicted_memory_15m)}%</td>
    <td>${n(row.temperature_c)}°C</td><td>${n(row.capacity_headroom_pct)}%</td>
    <td><span class="drift-label ${esc(row.drift_status)}">${esc(label(row.drift_status))}</span></td>
    <td class="decision-cell" title="${esc(row.reason)}">${esc(action)}</td>
  </tr>`;
}

function aggregateFleetRows(rows) {
  const keys = ["cpu_pct", "predicted_cpu_15m", "memory_pct", "predicted_memory_15m", "temperature_c"];
  const grouped = new Map();
  for (const row of rows) {
    if (!grouped.has(row.event_time)) grouped.set(row.event_time, {event_time: row.event_time, count: 0, sums: Object.fromEntries(keys.map(key => [key, 0]))});
    const group = grouped.get(row.event_time);
    group.count += 1;
    keys.forEach(key => { group.sums[key] += Number(row[key]) || 0; });
  }
  return [...grouped.values()].map(group => ({event_time: group.event_time, ...Object.fromEntries(keys.map(key => [key, group.sums[key] / group.count]))}));
}

function draw(rows) {
  const chartRows = selectedServer ? rows : aggregateFleetRows(rows);
  const canvas = $("#trend");
  const dpr = window.devicePixelRatio || 1;
  const width = Math.max(canvas.clientWidth, 320);
  const height = 280;
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  const context = canvas.getContext("2d");
  context.scale(dpr, dpr);
  context.clearRect(0, 0, width, height);
  context.font = "11px system-ui";
  context.fillStyle = "#667085";
  context.strokeStyle = "#e4e7ec";
  context.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = 18 + i * (height - 48) / 4;
    context.beginPath(); context.moveTo(42, y); context.lineTo(width - 10, y); context.stroke();
    context.fillText(String(100 - i * 25), 8, y + 4);
  }
  if (chartRows.length < 2) {
    context.fillStyle = "#667085"; context.font = "13px system-ui"; context.textAlign = "center";
    context.fillText("Waiting for at least two telemetry readings", width / 2, height / 2); context.textAlign = "start";
    return;
  }
  const series = [
    {key: "cpu_pct", color: "#1570ef"},
    {key: "predicted_cpu_15m", color: "#1570ef", dash: [7, 5]},
    {key: "memory_pct", color: "#7f56d9"},
    {key: "predicted_memory_15m", color: "#7f56d9", dash: [7, 5]},
    {key: "temperature_c", color: "#dc6803"}
  ];
  for (const {key, color, dash = []} of series) {
    context.beginPath(); context.strokeStyle = color; context.lineWidth = dash.length ? 1.5 : 2; context.setLineDash(dash);
    let started = false;
    chartRows.forEach((row, index) => {
      const value = Number(row[key]);
      if (!Number.isFinite(value)) return;
      const x = 42 + index * (width - 55) / (chartRows.length - 1);
      const y = 18 + (100 - value) * (height - 48) / 100;
      started ? context.lineTo(x, y) : context.moveTo(x, y); started = true;
    });
    context.stroke(); context.setLineDash([]);
  }
  context.fillStyle = "#667085"; context.font = "10px system-ui";
  const first = chartRows[0].event_time.slice(11, 16), last = chartRows.at(-1).event_time.slice(11, 16);
  context.fillText(first, 42, height - 4); context.textAlign = "right"; context.fillText(last, width - 10, height - 4); context.textAlign = "start";
  $("#chartSubtitle").textContent = `${selectedServer || "Fleet average"} · ${chartRows.length} timestamps · UTC`;
}

async function refresh() {
  try {
    const [summary, evaluation, comparison, closedLoop, actions, advanced] = await Promise.all([
      get("/api/summary"), get("/api/evaluation"), get("/api/model-comparison"), get("/api/closed-loop"), get("/api/actions"), get("/api/advanced")
    ]);
    const latest = summary.latest_servers || [];
    const eventLabel = summary.latest_event ? summary.latest_event.replace("T", " ").slice(0, 16) + " UTC" : "No readings";
    $("#updated").textContent = eventLabel;
    $("#latestEvent").textContent = `Latest event: ${eventLabel}`;
    $("#fleetCount").textContent = latest.length;
    $("#normalCount").textContent = latest.filter(row => row.predicted_condition === "normal").length;
    $("#attentionCount").textContent = latest.filter(row => ["overloaded", "anomalous"].includes(row.predicted_condition) || row.service_up === 0).length;
    $("#fleetHealth").textContent = advanced.fleet_health_score == null ? "—" : advanced.fleet_health_score.toFixed(1);
    $("#dataQuality").textContent = pct(advanced.data_completeness);
    $("#driftState").textContent = `${label(advanced.drift_status)} (${Number(advanced.drift_score || 0).toFixed(2)})`;
    $("#driftMetric").textContent = label(advanced.drift_metric);
    $("#averageHeadroom").textContent = advanced.average_headroom_pct == null ? "—" : `${advanced.average_headroom_pct.toFixed(1)}%`;
    $("#serverRows").innerHTML = latest.map(serverRow).join("") || '<tr><td colspan="12" class="empty">No telemetry received yet.</td></tr>';

    const filter = $("#serverFilter");
    if (filter.options.length === 1) latest.forEach(row => filter.add(new Option(row.server_id, row.server_id)));

    const chosenModel = comparison.models[comparison.selected_model];
    const test = chosenModel.test;
    const matrix = test.confusion_matrix;
    let normalCases = 0, falseAnomalies = 0;
    Object.keys(matrix).filter(key => key !== "anomalous").forEach(key => {
      normalCases += Object.values(matrix[key]).reduce((sum, value) => sum + value, 0);
      falseAnomalies += matrix[key].anomalous;
    });
    $("#selectedModel").textContent = label(comparison.selected_model);
    $("#accuracy").textContent = pct(test.accuracy);
    $("#macroF1").textContent = test.macro_f1.toFixed(3);
    $("#falseAlarm").textContent = pct(falseAnomalies / normalCases);
    $("#cpuMae").textContent = `${evaluation.forecast_test.cpu.mae.toFixed(2)} pts`;
    $("#modelRows").innerHTML = Object.entries(comparison.models).map(([name, value]) => `<tr class="${name === comparison.selected_model ? "selected" : ""}">
      <td>${value.family}${name === comparison.selected_model ? '<span class="selected-tag">Selected</span>' : ""}</td>
      <td>${pct(value.test.accuracy)}</td><td>${value.test.macro_precision.toFixed(3)}</td><td>${value.test.macro_recall.toFixed(3)}</td><td>${value.test.macro_f1.toFixed(3)}</td>
      <td>${value.computational_performance.training_wall_seconds.toFixed(2)} s</td><td>${value.test.inference_ms_per_record.toFixed(3)} ms</td><td>${value.computational_performance.serialized_model_mb.toFixed(2)} MB</td>
    </tr>`).join("");

    $("#controlEffect").textContent = pct(closedLoop.simulated_control_effectiveness);
    $("#scenarioDetection").textContent = `${closedLoop.fault_scenarios_detected}/${closedLoop.fault_scenarios_total}`;
    $("#decisionLatency").textContent = `${closedLoop.mean_decision_latency_ms.toFixed(2)} ms`;
    $("#cooldownCount").textContent = closedLoop.cooldown_suppressions.toLocaleString();
    $("#unnecessaryRate").textContent = pct(closedLoop.unnecessary_command_rate_on_normal_rows);
    $("#energySaving").textContent = `${closedLoop.estimated_energy_saving_kwh.toFixed(2)} kWh`;

    const total = summary.condition_counts.reduce((sum, row) => sum + row.count, 0);
    $("#conditionBars").innerHTML = summary.condition_counts.map(row => `<div class="bar-row"><span>${label(row.condition)}</span><div class="bar-track"><div class="bar-fill ${row.condition}" style="width:${100 * row.count / total}%"></div></div><b>${pct(row.count / total)}</b></div>`).join("");
    $("#actions").innerHTML = actions.slice(0, 8).map(row => `<div class="action"><div><b>${esc(row.server_id)}</b><time>${esc(row.event_time.slice(5, 16).replace("T", " "))}</time></div><div><strong>${esc(label(row.action))}</strong><small>${esc(row.reason)}</small></div><span class="severity ${esc(row.severity)}">${esc(row.severity)}</span></div>`).join("") || '<p class="empty">No actions recorded yet.</p>';

    const history = await get(`/api/history?limit=240${selectedServer ? `&server=${encodeURIComponent(selectedServer)}` : ""}`);
    draw(history);
  } catch (error) {
    $("#updated").textContent = "API unavailable";
    console.error(error);
  }
}

$("#serverFilter").addEventListener("change", event => { selectedServer = event.target.value; refresh(); });
window.addEventListener("resize", () => refresh());
refresh();
setInterval(refresh, 5000);
