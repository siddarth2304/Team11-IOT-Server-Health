import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";

import {
  Presentation,
  PresentationFile,
} from "/home/sahith-siddarth/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

function shortFailure(error) {
  const issues = error?.issues ? JSON.stringify(error.issues, null, 2) : "";
  console.error("DECK_BUILD_ERROR", error?.name ?? "Error", error?.message ?? String(error), issues);
  process.exit(1);
}
process.on("uncaughtException", shortFailure);
process.on("unhandledRejection", shortFailure);

const ROOT = "/home/sahith-siddarth/Documents/ChatGPT/IOT";
const BUILD = path.join(ROOT, ".ppt-build");
const PREVIEWS = path.join(BUILD, "previews");
const DRAFT = path.join(BUILD, "Team11_Server_Health_Presentation_draft.pptx");
const FINAL = path.join(ROOT, "artifacts/final/Team11_Server_Health_Presentation_EMQX.pptx");
const SKILL_DIR = "/home/sahith-siddarth/.codex/plugins/cache/openai-primary-runtime/presentations/26.1105.12137/skills/presentations";
const PYTHON = "/home/sahith-siddarth/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3";
process.env.RUNTIME_NODE_MODULES = "/home/sahith-siddarth/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules";

const C = {
  bg: "#F7F6F2",
  white: "#FFFFFF",
  text: "#1F2933",
  muted: "#5F6B76",
  navy: "#17365D",
  blue: "#4B7199",
  pale: "#EAF2F8",
  teal: "#2F6F68",
  green: "#4D7C65",
  gold: "#C58B3A",
  orange: "#B7663E",
  line: "#D9DEE3",
  lavender: "#EEEAF7",
};
const FONT = "Liberation Sans";

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function imageBytes(filePath) {
  const bytes = await fs.readFile(filePath);
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

function shape(slide, left, top, width, height, fill = C.white, line = C.line, radius = false) {
  return slide.shapes.add({
    geometry: radius ? "roundRect" : "rect",
    position: { left, top, width, height },
    fill,
    line: { style: "solid", fill: line, width: line === "none" ? 0 : 1 },
    ...(radius ? { borderRadius: "rounded-xl" } : {}),
  });
}

function text(slide, value, left, top, width, height, options = {}) {
  const item = slide.shapes.add({
    geometry: "textbox",
    position: { left, top, width, height },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  item.text = value;
  item.text.style = {
    typeface: FONT,
    fontSize: options.size ?? 22,
    bold: options.bold ?? false,
    color: options.color ?? C.text,
    alignment: options.align ?? "left",
    verticalAlignment: options.valign ?? "top",
    ...(options.italic ? { italic: true } : {}),
  };
  return item;
}

function line(slide, left, top, width, height = 2, fill = C.line) {
  return shape(slide, left, top, width, height, fill, "none", false);
}

function baseSlide(presentation, number, title, kicker = "TEAM 11 · SERVER HEALTH MONITORING") {
  const slide = presentation.slides.add();
  slide.background.fill = C.bg;
  text(slide, kicker, 66, 38, 560, 24, { size: 12, bold: true, color: C.teal });
  text(slide, title, 66, 72, 1120, 56, { size: 34, bold: true, color: C.text });
  line(slide, 66, 135, 1120, 2, C.line);
  text(slide, String(number).padStart(2, "0"), 1160, 674, 54, 20, { size: 11, bold: true, color: C.muted, align: "right" });
  return slide;
}

function metric(slide, label, value, left, top, width, accent = C.teal) {
  line(slide, left, top, width, 4, accent);
  text(slide, value, left, top + 18, width, 50, { size: 31, bold: true, color: C.text });
  text(slide, label, left, top + 68, width, 34, { size: 14, color: C.muted });
}

function labelBand(slide, label, detail, left, top, width, accent = C.blue) {
  line(slide, left, top + 3, 8, 78, accent);
  text(slide, label, left + 24, top, width - 24, 28, { size: 18, bold: true, color: C.text });
  text(slide, detail, left + 24, top + 32, width - 24, 50, { size: 14, color: C.muted });
}

const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });

// 1. Cover
{
  const slide = presentation.slides.add();
  slide.background.fill = C.bg;
  line(slide, 68, 54, 140, 5, C.teal);
  text(slide, "TEAM 11 · IoT MINI PROJECT", 68, 76, 520, 30, { size: 14, bold: true, color: C.teal });
  text(slide, "Server and IT Infrastructure\nHealth Monitoring", 68, 150, 780, 150, { size: 49, bold: true, color: C.text });
  text(slide, "Software-only sensing, secure cloud MQTT, machine learning, forecasting and safe closed-loop action", 70, 326, 730, 80, { size: 21, color: C.muted });
  line(slide, 70, 442, 660, 2, C.line);
  text(slide, "B.Tech CSE · Semester 7", 70, 466, 380, 34, { size: 18, bold: true, color: C.navy });
  text(slide, "Team members and roll numbers: add before submission", 70, 506, 600, 34, { size: 16, color: C.muted });
  shape(slide, 895, 126, 260, 390, C.pale, "none", true);
  text(slide, "4", 948, 177, 154, 76, { size: 60, bold: true, color: C.navy, align: "center" });
  text(slide, "simulated servers", 925, 253, 200, 32, { size: 17, bold: true, color: C.text, align: "center" });
  line(slide, 938, 316, 174, 2, C.line);
  text(slide, "80,640", 936, 342, 180, 48, { size: 34, bold: true, color: C.teal, align: "center" });
  text(slide, "one-minute readings", 925, 394, 200, 30, { size: 15, color: C.muted, align: "center" });
  text(slide, "99.33%", 936, 446, 180, 42, { size: 30, bold: true, color: C.green, align: "center" });
  text(slide, "selected-model accuracy", 915, 486, 220, 24, { size: 14, color: C.muted, align: "center" });
}

// 2. Problem and objectives
{
  const slide = baseSlide(presentation, 2, "Problem, goal and evaluation boundary");
  text(slide, "Server workloads fluctuate. Static thresholds alone cannot distinguish normal peaks, wasted capacity and true failure.", 70, 166, 520, 94, { size: 22, bold: true, color: C.navy });
  labelBand(slide, "Observe", "CPU, memory, disk, network, temperature, service heartbeat and user activity at one-minute intervals.", 70, 286, 510, C.blue);
  labelBand(slide, "Understand", "Classify normal, underutilized, overloaded and anomalous states; forecast demand 15 minutes ahead.", 70, 396, 510, C.teal);
  labelBand(slide, "Act safely", "Issue auditable recommendations with cooldowns, approval flags and a software digital-twin response.", 70, 506, 510, C.green);
  shape(slide, 650, 180, 520, 405, C.white, C.line, true);
  text(slide, "What this project proves", 688, 214, 450, 34, { size: 22, bold: true, color: C.text });
  const claims = [
    ["End-to-end IoT", "Sensor replay → MQTT → Node-RED → analytics → decision → acknowledgement"],
    ["Fair evaluation", "Chronological train/validation/test split; labels and future targets excluded from features"],
    ["Operational value", "Health score, explanations, capacity headroom, drift and data-quality monitoring"],
    ["Honest boundary", "Synthetic telemetry and simulated actions; no production server is modified"],
  ];
  claims.forEach(([a, b], i) => labelBand(slide, a, b, 688, 275 + i * 76, 440, [C.navy, C.teal, C.green, C.orange][i]));
}

// 3. Architecture
{
  const slide = baseSlide(presentation, 3, "Two-laptop closed-loop architecture");
  const bytes = await imageBytes(path.join(ROOT, "docs/team11_architecture.png"));
  shape(slide, 78, 158, 1124, 474, C.white, C.line, true);
  slide.images.add({
    blob: bytes,
    contentType: "image/png",
    alt: "Two-laptop EMQX Cloud MQTT, Node-RED, analytics and control architecture",
    fit: "contain",
    position: { left: 92, top: 168, width: 1096, height: 442 },
  });
  text(slide, "Other PC: Node-RED + actuator via EMQX Cloud", 80, 646, 520, 25, { size: 14, bold: true, color: C.teal });
  text(slide, "Main laptop: data + ML + database + dashboard", 700, 646, 500, 25, { size: 14, bold: true, color: C.navy, align: "right" });
}

// 4. Dataset
{
  const slide = baseSlide(presentation, 4, "Dataset design: reproducible, time-ordered and leakage-safe");
  metric(slide, "rows", "80,640", 70, 170, 190, C.navy);
  metric(slide, "servers", "4", 290, 170, 150, C.teal);
  metric(slide, "duration", "14 days", 470, 170, 190, C.green);
  metric(slide, "sampling", "60 sec", 690, 170, 190, C.gold);
  metric(slide, "fault families", "6", 910, 170, 210, C.orange);
  text(slide, "Chronological split", 70, 332, 260, 34, { size: 22, bold: true, color: C.text });
  const totalW = 1040;
  const trainW = totalW * 10 / 14;
  const valW = totalW * 2 / 14;
  shape(slide, 70, 386, trainW, 58, C.navy, "none", false);
  shape(slide, 70 + trainW, 386, valW, 58, C.teal, "none", false);
  shape(slide, 70 + trainW + valW, 386, valW, 58, C.gold, "none", false);
  text(slide, "TRAIN · days 1–10 · 57,600", 92, 400, trainW - 30, 30, { size: 16, bold: true, color: C.white, align: "center" });
  text(slide, "VALIDATE\n11,520", 70 + trainW + 6, 393, valW - 12, 44, { size: 13, bold: true, color: C.white, align: "center" });
  text(slide, "TEST\n11,520", 70 + trainW + valW + 6, 393, valW - 12, 44, { size: 13, bold: true, color: C.white, align: "center" });
  labelBand(slide, "Model inputs", "Current telemetry + cyclic hour + weekday", 70, 500, 330, C.blue);
  labelBand(slide, "Offline-only truth", "Condition, fault, scenario and recommended action", 450, 500, 330, C.orange);
  labelBand(slide, "Future targets", "CPU and memory at +15 min never enter classifier features", 830, 500, 350, C.green);
  text(slide, "The CSV is synthetic and scenario-based; it must not be presented as production infrastructure data.", 70, 625, 1080, 34, { size: 16, bold: true, color: C.orange });
}

// 5. Model comparison
{
  const slide = baseSlide(presentation, 5, "Model selection: validation macro-F1 decides");
  slide.charts.add("bar", {
    position: { left: 70, top: 166, width: 735, height: 410 },
    title: "Classifier comparison",
    titleTextStyle: { fontSize: 18, bold: true, fill: C.text },
    categories: ["Gaussian NB", "Random Forest", "MLP 64-32-16"],
    series: [
      { name: "Validation macro-F1", values: [0.810, 0.994, 0.846], fill: C.teal },
      { name: "Test macro-F1", values: [0.838, 0.947, 0.868], fill: C.navy },
    ],
    barOptions: { direction: "column", grouping: "clustered", gapWidth: 60 },
    legend: { position: "bottom", overlay: false },
    yAxis: { min: 0.75, max: 1.0, numberFormatCode: "0.000", majorGridlines: { style: "solid", fill: C.line, width: 1 } },
    xAxis: { textStyle: { fontSize: 12, fill: C.muted } },
    dataLabels: { showValue: true, position: "outEnd", numberFormatCode: "0.000", textStyle: { fontSize: 11, bold: true, fill: C.text } },
    chartFill: C.white,
    chartLine: { style: "solid", fill: C.line, width: 1 },
    plotAreaFill: C.white,
  });
  shape(slide, 845, 170, 330, 404, C.white, C.line, true);
  text(slide, "Selected model", 878, 205, 265, 28, { size: 17, bold: true, color: C.muted });
  text(slide, "Random Forest", 878, 244, 265, 44, { size: 30, bold: true, color: C.navy });
  metric(slide, "test accuracy", "99.33%", 878, 320, 250, C.green);
  metric(slide, "test macro-F1", "0.947", 878, 430, 250, C.teal);
  text(slide, "Why macro-F1? It gives equal weight to rare overload and anomaly classes; accuracy alone can hide weakness.", 70, 610, 1080, 50, { size: 16, color: C.muted });
}

// 6. Per-class performance
{
  const slide = baseSlide(presentation, 6, "Selected-model performance by operating condition");
  slide.charts.add("bar", {
    position: { left: 70, top: 166, width: 770, height: 430 },
    title: "Random Forest test precision, recall and F1",
    titleTextStyle: { fontSize: 18, bold: true, fill: C.text },
    categories: ["Underutilized", "Normal", "Overloaded", "Anomalous"],
    series: [
      { name: "Precision", values: [0.999, 0.997, 0.815, 1.000], fill: C.blue },
      { name: "Recall", values: [0.999, 1.000, 0.959, 0.830], fill: C.teal },
      { name: "F1", values: [0.999, 0.999, 0.881, 0.907], fill: C.gold },
    ],
    barOptions: { direction: "column", grouping: "clustered", gapWidth: 45 },
    legend: { position: "bottom", overlay: false },
    yAxis: { min: 0.75, max: 1.0, numberFormatCode: "0.00", majorGridlines: { style: "solid", fill: C.line, width: 1 } },
    xAxis: { textStyle: { fontSize: 11, fill: C.muted } },
    chartFill: C.white,
    chartLine: { style: "solid", fill: C.line, width: 1 },
    plotAreaFill: C.white,
  });
  shape(slide, 875, 168, 300, 430, C.white, C.line, true);
  text(slide, "Read this honestly", 906, 205, 238, 28, { size: 19, bold: true, color: C.text });
  labelBand(slide, "Strong", "Normal and underutilized states are almost perfectly separated.", 905, 260, 235, C.green);
  labelBand(slide, "Hardest class", "Overloaded precision is 0.815 because some anomaly patterns overlap.", 905, 360, 235, C.orange);
  labelBand(slide, "Safety layer", "Deterministic rules still protect service, thermal, disk, network and error emergencies.", 905, 475, 235, C.navy);
  text(slide, "Test support: 2,967 underutilized · 7,927 normal · 244 overloaded · 382 anomalous", 70, 625, 1100, 30, { size: 15, color: C.muted });
}

// 7. Forecasting
{
  const slide = baseSlide(presentation, 7, "Fifteen-minute resource forecasting");
  slide.charts.add("bar", {
    position: { left: 70, top: 166, width: 720, height: 420 },
    title: "Forecast error in percentage points",
    titleTextStyle: { fontSize: 18, bold: true, fill: C.text },
    categories: ["CPU +15 min", "Memory +15 min"],
    series: [
      { name: "MAE", values: [4.48, 1.93], fill: C.teal },
      { name: "RMSE", values: [5.80, 2.88], fill: C.gold },
    ],
    barOptions: { direction: "column", grouping: "clustered", gapWidth: 70 },
    legend: { position: "bottom", overlay: false },
    yAxis: { min: 0, max: 7, majorGridlines: { style: "solid", fill: C.line, width: 1 } },
    dataLabels: { showValue: true, position: "outEnd", numberFormatCode: "0.00", textStyle: { fontSize: 12, bold: true, fill: C.text } },
    chartFill: C.white,
    chartLine: { style: "solid", fill: C.line, width: 1 },
    plotAreaFill: C.white,
  });
  shape(slide, 835, 168, 340, 420, C.white, C.line, true);
  text(slide, "Forecast quality", 870, 205, 260, 30, { size: 20, bold: true, color: C.text });
  metric(slide, "CPU R²", "0.870", 870, 260, 250, C.blue);
  metric(slide, "Memory R²", "0.939", 870, 374, 250, C.green);
  labelBand(slide, "Capacity headroom", "100 − max(predicted CPU, predicted memory, current disk)", 870, 490, 260, C.teal);
  text(slide, "Ridge regression uses current telemetry and time features. The 15-minute targets are created only for forecast training and evaluation.", 70, 618, 1080, 46, { size: 16, color: C.muted });
}

// 8. Advanced operations
{
  const slide = baseSlide(presentation, 8, "Advanced operational intelligence");
  text(slide, "These features are deterministic or statistical monitors around the classifier—not extra hidden models.", 70, 166, 1050, 44, { size: 20, color: C.navy });
  const features = [
    ["Health score", "0–100 auditable score from resource, thermal, service and error pressure.", "100", C.green],
    ["Local explanation", "Stores the strongest observed pressure factors with each prediction.", "TOP 3", C.blue],
    ["Concept drift", "120-message rolling mean shift against a training-only baseline.", "≥ 2.5", C.orange],
    ["Data quality", "Completeness across critical telemetry, prediction and confidence fields.", "100%", C.teal],
  ];
  features.forEach(([name, detail, value, accent], i) => {
    const y = 248 + i * 92;
    line(slide, 70, y + 5, 10, 70, accent);
    text(slide, value, 105, y, 150, 52, { size: 30, bold: true, color: accent });
    text(slide, name, 270, y, 270, 30, { size: 21, bold: true, color: C.text });
    text(slide, detail, 540, y, 610, 48, { size: 16, color: C.muted });
    if (i < 3) line(slide, 100, y + 82, 1040, 1, C.line);
  });
  text(slide, "Drift states: warming up (<20 messages) · stable (<1.5) · watch (1.5–2.5) · drift (≥2.5)", 70, 635, 1100, 28, { size: 15, bold: true, color: C.orange });
}

// 9. Dashboard
{
  const slide = baseSlide(presentation, 9, "Operator dashboard: mixed fleet state and evidence");
  const bytes = await imageBytes(path.join(ROOT, "docs/dashboard_screenshot.png"));
  shape(slide, 70, 158, 1140, 493, C.white, C.line, true);
  slide.images.add({
    blob: bytes,
    contentType: "image/png",
    alt: "Natural light server health dashboard showing normal, overloaded and underutilized states",
    fit: "contain",
    position: { left: 84, top: 169, width: 1112, height: 465 },
  });
  text(slide, "Live view: measured + forecast trends · health · confidence · explanations · headroom · drift · decision", 90, 652, 1080, 24, { size: 14, bold: true, color: C.teal, align: "center" });
}

// 10. Decision loop
{
  const slide = baseSlide(presentation, 10, "Decision engine and safe control loop");
  const steps = [
    ["1", "Telemetry", "validated current state", C.blue],
    ["2", "Prediction", "class + confidence + forecast", C.teal],
    ["3", "Policy", "rules override model when safety-critical", C.gold],
    ["4", "Command", "UUID + reason + approval + expected effect", C.orange],
    ["5", "Actuator", "simulated post-action state + acknowledgement", C.green],
  ];
  steps.forEach(([n, name, detail, accent], i) => {
    const x = 55 + i * 244;
    shape(slide, x, 210, 210, 190, C.white, C.line, true);
    shape(slide, x + 18, 230, 44, 44, accent, "none", true);
    text(slide, n, x + 18, 237, 44, 28, { size: 18, bold: true, color: C.white, align: "center" });
    text(slide, name, x + 22, 294, 165, 32, { size: 21, bold: true, color: C.text });
    text(slide, detail, x + 22, 336, 165, 54, { size: 14, color: C.muted });
    if (i < 4) text(slide, "→", x + 213, 278, 30, 44, { size: 30, bold: true, color: C.muted, align: "center" });
  });
  labelBand(slide, "Cooldown", "Five minutes per server and action suppresses repeated commands.", 80, 470, 330, C.navy);
  labelBand(slide, "Human control", "Disk cleanup and consolidation remain operator-approved.", 470, 470, 330, C.orange);
  labelBand(slide, "Audit trail", "Telemetry, predictions, explanations, commands and acknowledgements persist in SQLite.", 860, 470, 330, C.green);
  text(slide, "Priority examples: service down → restart · temperature ≥82°C → cooling · disk ≥92% → operator cleanup · overload → redistribute/start standby", 80, 607, 1110, 48, { size: 15, color: C.muted });
}

// 11. Evaluation
{
  const slide = baseSlide(presentation, 11, "Closed-loop evaluation and verification");
  slide.charts.add("bar", {
    position: { left: 70, top: 168, width: 690, height: 400 },
    title: "Operational checks passed",
    titleTextStyle: { fontSize: 18, bold: true, fill: C.text },
    categories: ["Fault coverage", "Control effectiveness", "Normal-state safety", "Telemetry completeness"],
    series: [{ name: "Percent", values: [100, 100, 100, 100], fill: C.teal }],
    barOptions: { direction: "bar", grouping: "clustered", gapWidth: 50 },
    hasLegend: false,
    xAxis: { min: 0, max: 110, numberFormatCode: "0", majorGridlines: { style: "solid", fill: C.line, width: 1 } },
    yAxis: { textStyle: { fontSize: 12, fill: C.muted } },
    dataLabels: { showValue: true, position: "outEnd", numberFormatCode: "0'%'", textStyle: { fontSize: 12, bold: true, fill: C.text } },
    chartFill: C.white,
    chartLine: { style: "solid", fill: C.line, width: 1 },
    plotAreaFill: C.white,
  });
  shape(slide, 800, 168, 375, 400, C.white, C.line, true);
  text(slide, "Untouched test replay", 835, 205, 305, 28, { size: 19, bold: true, color: C.text });
  metric(slide, "messages", "11,520", 835, 255, 140, C.navy);
  metric(slide, "commands", "746", 1000, 255, 140, C.orange);
  metric(slide, "fault families found", "6 / 6", 835, 365, 140, C.green);
  metric(slide, "cooldown suppressions", "2,296", 1000, 365, 140, C.teal);
  text(slide, "Mean policy latency: 0.017 ms", 835, 494, 300, 28, { size: 16, bold: true, color: C.text });
  text(slide, "12 automated tests pass", 835, 526, 300, 28, { size: 16, bold: true, color: C.green });
  text(slide, "Energy potential: 2.25 kWh under a documented simulation assumption—not a production claim.", 70, 612, 1080, 46, { size: 16, color: C.orange });
}

// 12. Demonstration and viva
{
  const slide = baseSlide(presentation, 12, "Live demonstration: two commands, one backup plan");
  shape(slide, 70, 174, 520, 200, C.white, C.line, true);
  text(slide, "OTHER PC · run first", 102, 204, 450, 28, { size: 16, bold: true, color: C.teal });
  shape(slide, 102, 252, 456, 62, C.navy, "none", true);
  text(slide, "./team11.sh cloud-edge", 122, 267, 416, 32, { size: 22, bold: true, color: C.white });
  text(slide, "Node-RED · EMQX TLS · digital-twin actuator", 102, 329, 450, 26, { size: 14, color: C.muted });
  shape(slide, 620, 174, 590, 200, C.white, C.line, true);
  text(slide, "MAIN LAPTOP · training + evaluation + demo", 652, 204, 520, 28, { size: 16, bold: true, color: C.navy });
  shape(slide, 652, 252, 526, 62, C.teal, "none", true);
  text(slide, "./team11.sh cloud-main", 670, 267, 490, 32, { size: 22, bold: true, color: C.white });
  text(slide, "Dataset checks · analysis · models · tests · dashboard · balanced stream", 652, 329, 520, 26, { size: 14, color: C.muted });
  text(slide, "What to demonstrate", 70, 420, 300, 30, { size: 22, bold: true, color: C.text });
  labelBand(slide, "1 · Architecture", "Show Node-RED processing and MQTT topics on the other PC.", 70, 470, 330, C.blue);
  labelBand(slide, "2 · Analytics", "Show model metrics, 15-minute forecast, health score and explanation.", 445, 470, 350, C.teal);
  labelBand(slide, "3 · Closed loop", "Replay mixed states; point out command, cooldown and actuator acknowledgement.", 835, 470, 360, C.green);
  shape(slide, 70, 608, 1140, 48, C.pale, "none", true);
  text(slide, "Cloud dashboard: http://127.0.0.1:8081     Offline backup: ./team11.sh local", 92, 620, 1096, 28, { size: 16, bold: true, color: C.navy, align: "center" });
}

await fs.mkdir(PREVIEWS, { recursive: true });
for (const [index, slide] of presentation.slides.items.entries()) {
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  const png = await presentation.export({ slide, format: "png", scale: 1 });
  await writeBlob(path.join(PREVIEWS, `${stem}.png`), png);
}
const montage = await presentation.export({ format: "webp", montage: true });
await writeBlob(path.join(BUILD, "deck-montage.webp"), montage);

await (await PresentationFile.exportPptx(presentation)).save(DRAFT);

const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href);
const stagingDir = path.join(BUILD, ".codex-finalizer");
await fs.mkdir(stagingDir, { recursive: true });
await fs.mkdir(path.dirname(FINAL), { recursive: true });
const requirements = {
  explicitTotalSlideCount: 12,
  requiredNativeChartOwnerSlides: [5, 6, 7, 11],
  requiredNativeTableOwnerSlides: [],
  materializeLiteralChartWorkbooks: true,
  nativeChartTargetApplication: "powerpoint",
};
const result = await finalizePresentation({
  ...requirements,
  workspaceDir: ROOT,
  candidatePath: DRAFT,
  finalPath: FINAL,
  pythonExecutable: PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", "12192000,6858000",
    "--validate-bullet-geometry",
    "--validate-heading-fit",
  ],
  requiredNativeTableOwnerSlides: [],
  fontPolicy: { basis: "design", families: [FONT, "Arial"] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "Team11_Server_Health_Presentation_EMQX.validation.json"),
});

console.log(JSON.stringify({ final: FINAL, draft: DRAFT, validation: result }, null, 2));
