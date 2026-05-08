#!/usr/bin/env python3
"""Interactive student component builder with live diagram preview.

Run:
    python3 student_component_builder.py
Then open:
    http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


HTML_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Student Component Builder</title>
  <style>
    :root {
      color-scheme: light dark;
      --bg: #f7f8fb;
      --card: #ffffff;
      --text: #1f2937;
      --muted: #4b5563;
      --border: #e5e7eb;
      --accent: #2563eb;
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --bg: #0f1115;
        --card: #161a22;
        --text: #f3f4f6;
        --muted: #d1d5db;
        --border: #2a3240;
        --accent: #60a5fa;
      }
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, Segoe UI, Roboto, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    .wrap {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      height: 100vh;
      padding: 14px;
    }
    .panel {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 10px;
      display: flex;
      flex-direction: column;
      min-height: 0;
    }
    .panel h2 {
      margin: 0;
      padding: 14px 14px 10px;
      border-bottom: 1px solid var(--border);
      font-size: 18px;
    }
    .hint {
      margin: 0;
      padding: 10px 14px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.35;
      border-bottom: 1px dashed var(--border);
      white-space: pre-wrap;
    }
    textarea {
      flex: 1;
      margin: 0;
      border: 0;
      border-radius: 0 0 10px 10px;
      resize: none;
      padding: 12px 14px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 14px;
      line-height: 1.4;
      color: var(--text);
      background: transparent;
      outline: none;
    }
    .diagram {
      flex: 1;
      overflow: auto;
      padding: 10px;
    }
    .diagram.hidden {
      display: none;
    }
    .view-toggle {
      display: flex;
      gap: 8px;
      padding: 10px 14px 0;
      flex-wrap: wrap;
    }
    .view-toggle button.active {
      border-color: var(--accent);
      color: var(--accent);
      font-weight: 600;
    }
    .view-toggle .spacer {
      flex: 1 1 auto;
    }
    .view-toggle .mini {
      font-size: 12px;
      padding: 6px 9px;
    }
    .actions {
      display: flex;
      gap: 8px;
      padding: 8px 14px 12px;
      border-top: 1px solid var(--border);
    }
    button {
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--card);
      color: var(--text);
      padding: 7px 10px;
      cursor: pointer;
    }
    button.primary {
      border-color: var(--accent);
      color: var(--accent);
      font-weight: 600;
    }
    .error {
      color: #dc2626;
      font-size: 13px;
      padding: 0 14px 10px;
      min-height: 20px;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="panel">
      <h2>Write Components in English</h2>
      <p class="hint">Use one block per class/component, separated by a blank line.
Example:
Class: Student
Variables: name: string, rollNo: int
Methods: enroll(course), drop(course)
Uses: CourseService, Database
Calls: Student.enroll -> CourseService.getCourse, Student.enroll -> Database.save

Class: CourseService
Variables: courses: list
Methods: addCourse(course), getCourse(id)</p>
      <textarea id="source"></textarea>
      <div class="actions">
        <button class="primary" id="render">Render Diagram</button>
        <button id="example">Load Example</button>
      </div>
      <div class="error" id="error"></div>
    </section>

    <section class="panel">
      <h2>Component Diagram (Live)</h2>
      <div class="view-toggle">
        <button class="active" id="archViewBtn">Class / Architecture</button>
        <button id="flowViewBtn">Flow Diagram</button>
        <button id="orderViewBtn">Block / Ordered Flow</button>
        <span class="spacer"></span>
        <button class="mini" id="connectModeBtn" title="Click two components to connect them">Connect: Off</button>
        <button class="mini" id="orderModeBtn" title="Click components in order to create a flow">Order: Off</button>
        <button class="mini" id="orderUndoBtn" title="Remove last step">Undo</button>
        <button class="mini" id="orderClearBtn" title="Clear order">Clear</button>
      </div>
      <div class="diagram" id="archDiagram"></div>
      <div class="diagram hidden" id="flowDiagram"></div>
      <div class="diagram hidden" id="orderDiagram"></div>
    </section>
  </div>

  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";

    const seedText = `Class: Student
Variables: name: string, rollNo: int
Methods: enroll(course), drop(course), viewGrades()
Uses: CourseService, GradeService
Calls: Student.enroll -> CourseService.getCourse, Student.viewGrades -> GradeService.getGrades

Class: CourseService
Variables: courses: list
Methods: addCourse(course), getCourse(id)
Uses: Database

Class: GradeService
Variables: gradeBook: map
Methods: assignGrade(student, subject, score), getGrades(studentId)
Uses: Database

Class: Database
Variables: connectionString: string
Methods: save(record), query(criteria)`;

    const source = document.getElementById("source");
    const archOutput = document.getElementById("archDiagram");
    const flowOutput = document.getElementById("flowDiagram");
    const orderOutput = document.getElementById("orderDiagram");
    const errorBox = document.getElementById("error");
    const renderBtn = document.getElementById("render");
    const exampleBtn = document.getElementById("example");
    const archViewBtn = document.getElementById("archViewBtn");
    const flowViewBtn = document.getElementById("flowViewBtn");
    const orderViewBtn = document.getElementById("orderViewBtn");
    const connectModeBtn = document.getElementById("connectModeBtn");
    const orderModeBtn = document.getElementById("orderModeBtn");
    const orderUndoBtn = document.getElementById("orderUndoBtn");
    const orderClearBtn = document.getElementById("orderClearBtn");

    let connectMode = false;
    let connectFrom = null;
    let lastArchIdToName = new Map();
    let orderMode = false;
    let orderSteps = [];

    source.value = seedText;

    function normName(text) {
      return text.replace(/[^a-zA-Z0-9_]/g, "_") || "Component";
    }

    function parseList(raw) {
      return raw
        .split(",")
        .map((x) => x.trim())
        .filter(Boolean);
    }

    function escapeLabel(text) {
      return text.replaceAll('"', "&quot;");
    }

    function methodBaseName(signature) {
      const clean = signature.trim();
      const idx = clean.indexOf("(");
      return (idx >= 0 ? clean.slice(0, idx) : clean).trim();
    }

    function parseCallEdge(raw) {
      const arrow = raw.match(/^(.+?)\\s*->\\s*(.+)$/);
      if (!arrow) return null;
      return { from: arrow[1].trim(), to: arrow[2].trim() };
    }

    function getComponentNameFromBlockHeader(headerLine) {
      const first = headerLine.trim();
      const classMatch = first.match(/^(?:class|component)\\s*:\\s*(.+)$/i);
      const sentenceMatch = first.match(/^class\\s+([a-zA-Z_][\\w]*)\\b/i);
      return classMatch ? classMatch[1].trim() : (sentenceMatch ? sentenceMatch[1].trim() : first);
    }

    function parseEnglish(input) {
      const blocks = input
        .split(/\\n\\s*\\n/g)
        .map((b) => b.trim())
        .filter(Boolean);

      const components = [];
      const byName = new Map();

      for (const block of blocks) {
        const lines = block
          .split("\\n")
          .map((l) => l.trim())
          .filter(Boolean);
        if (!lines.length) continue;

        const first = lines[0];
        const classMatch = first.match(/^(?:class|component)\\s*:\\s*(.+)$/i);
        const sentenceMatch = first.match(/^class\\s+([a-zA-Z_][\\w]*)\\b/i);
        const name = classMatch ? classMatch[1].trim() : (sentenceMatch ? sentenceMatch[1].trim() : first);

        const comp = { name, variables: [], methods: [], uses: [], calls: [] };
        for (const line of lines.slice(1)) {
          const variableMatch = line.match(/^variables?\\s*:\\s*(.+)$/i);
          const methodMatch = line.match(/^methods?\\s*:\\s*(.+)$/i);
          const usesMatch = line.match(/^(?:uses|depends\\s+on)\\s*:\\s*(.+)$/i);
          const methodFlowMatch = line.match(/^(?:method\\s+)?(?:flow|calls?)\\s*:\\s*(.+)$/i);

          if (variableMatch) comp.variables.push(...parseList(variableMatch[1]));
          else if (methodMatch) comp.methods.push(...parseList(methodMatch[1]));
          else if (usesMatch) comp.uses.push(...parseList(usesMatch[1]));
          else if (methodFlowMatch) {
            for (const item of parseList(methodFlowMatch[1])) {
              const edge = parseCallEdge(item);
              if (edge) comp.calls.push(edge);
            }
          }
        }

        components.push(comp);
        byName.set(comp.name.toLowerCase(), comp);
      }
      return components;
    }

    function parseGlobalOrder(input) {
      const m = input.match(/^\s*(?:Flow\s*Order|Order)\s*:\s*(.+)\s*$/im);
      if (!m) return [];
      return m[1]
        .split(/->|→/)
        .map((s) => s.trim())
        .filter(Boolean);
    }

    function upsertGlobalOrder(input, steps) {
      const line = `Flow Order: ${steps.join(" -> ")}`;
      if (!steps.length) {
        // Remove existing Flow Order line if present.
        return input.replace(/^\s*(?:Flow\s*Order|Order)\s*:\s*.*\\n?/gim, "").trim() + "\\n";
      }
      if (input.match(/^\s*(?:Flow\s*Order|Order)\s*:\s*.*$/im)) {
        return input.replace(/^\s*(?:Flow\s*Order|Order)\s*:\s*.*$/im, line);
      }
      return `${line}\n\n${input.trim()}\n`;
    }

    function normalizeMethodRef(rawRef, currentCompName) {
      const ref = rawRef.trim();
      if (!ref) return null;
      if (ref.includes(".")) return ref;
      return `${currentCompName}.${methodBaseName(ref)}`;
    }

    function methodNodeId(methodRef) {
      return `m_${normName(methodRef)}`;
    }

    function addUsesInText(sourceText, fromComponent, toComponent) {
      const blocks = sourceText.split(/\\n\\s*\\n/g);
      const updatedBlocks = [];
      let changed = false;

      for (const rawBlock of blocks) {
        const block = rawBlock.trim();
        if (!block) continue;

        const lines = block.split("\\n");
        const header = lines[0] || "";
        const name = getComponentNameFromBlockHeader(header);

        if (name.toLowerCase() !== fromComponent.toLowerCase()) {
          updatedBlocks.push(lines.join("\\n"));
          continue;
        }

        let foundUsesLine = false;
        const outLines = [];
        for (const line of lines) {
          const m = line.match(/^(uses|depends\\s+on)\\s*:\\s*(.*)$/i);
          if (!m) {
            outLines.push(line);
            continue;
          }
          foundUsesLine = true;
          const existing = parseList(m[2] || "");
          const set = new Map(existing.map((x) => [x.toLowerCase(), x]));
          if (!set.has(toComponent.toLowerCase())) {
            existing.push(toComponent);
            changed = true;
          }
          outLines.push(`Uses: ${existing.join(", ")}`);
        }

        if (!foundUsesLine) {
          outLines.push(`Uses: ${toComponent}`);
          changed = true;
        }

        updatedBlocks.push(outLines.join("\\n"));
      }

      // If we didn't find the component block at all, do nothing.
      return changed ? updatedBlocks.join("\\n\\n") : sourceText;
    }

    function toArchitectureMermaid(components) {
      const lines = ["flowchart LR"];
      const existing = new Set(components.map((c) => c.name.toLowerCase()));
      const emittedExternal = new Set();

      for (const comp of components) {
        const vars = comp.variables.length ? comp.variables.join("<br/>") : "None";
        const methods = comp.methods.length ? comp.methods.join("<br/>") : "None";
        const label = `${comp.name}<br/>--- Variables ---<br/>${vars}<br/>--- Methods ---<br/>${methods}`;
        lines.push(`${normName(comp.name)}["${escapeLabel(label)}"]`);
      }

      for (const comp of components) {
        for (const dep of comp.uses) {
          const depName = dep.trim();
          if (!depName) continue;
          const depId = normName(depName);
          if (!existing.has(depName.toLowerCase()) && !emittedExternal.has(depName.toLowerCase())) {
            lines.push(`${depId}["${escapeLabel(depName)}"]`);
            emittedExternal.add(depName.toLowerCase());
          }
          lines.push(`${normName(comp.name)} -->|uses| ${depId}`);
        }
      }
      return lines.join("\\n");
    }

    function buildArchIdToName(components) {
      const map = new Map();
      for (const c of components) map.set(normName(c.name), c.name);
      return map;
    }

    function toFlowMermaid(components) {
      const lines = ["flowchart LR"];
      const methodRefs = new Set();

      for (const comp of components) {
        const compId = normName(comp.name);
        lines.push(`${compId}["${escapeLabel(comp.name)}"]`);
        for (const methodSig of comp.methods) {
          const base = methodBaseName(methodSig);
          if (!base) continue;
          const ref = `${comp.name}.${base}`;
          const nodeId = methodNodeId(ref);
          methodRefs.add(ref.toLowerCase());
          lines.push(`${nodeId}(["${escapeLabel(base + "()")}"])`);
          lines.push(`${compId} -.contains.-> ${nodeId}`);
        }
      }

      let hasCall = false;
      for (const comp of components) {
        for (const call of comp.calls) {
          const fromRef = normalizeMethodRef(call.from, comp.name);
          const toRef = normalizeMethodRef(call.to, comp.name);
          if (!fromRef || !toRef) continue;

          const fromKey = fromRef.toLowerCase();
          const toKey = toRef.toLowerCase();
          const fromId = methodNodeId(fromRef);
          const toId = methodNodeId(toRef);

          if (!methodRefs.has(fromKey)) {
            lines.push(`${fromId}(["${escapeLabel(fromRef)}"])`);
            methodRefs.add(fromKey);
          }
          if (!methodRefs.has(toKey)) {
            lines.push(`${toId}(["${escapeLabel(toRef)}"])`);
            methodRefs.add(toKey);
          }

          lines.push(`${fromId} -->|calls| ${toId}`);
          hasCall = true;

          const fromComp = fromRef.split(".")[0];
          const toComp = toRef.split(".")[0];
          if (fromComp && toComp && fromComp.toLowerCase() !== toComp.toLowerCase()) {
            lines.push(`${normName(fromComp)} -.method flow.-> ${normName(toComp)}`);
          }
        }
      }

      if (!hasCall) {
        lines.push(`NoCalls["No method call flow provided.<br/>Add 'Calls: A.m1 -> B.m2' in input."]`);
      }
      return lines.join("\\n");
    }

    function setView(view) {
      const showArch = view === "arch";
      const showFlow = view === "flow";
      const showOrder = view === "order";

      archOutput.classList.toggle("hidden", !showArch);
      flowOutput.classList.toggle("hidden", !showFlow);
      orderOutput.classList.toggle("hidden", !showOrder);

      archViewBtn.classList.toggle("active", showArch);
      flowViewBtn.classList.toggle("active", showFlow);
      orderViewBtn.classList.toggle("active", showOrder);
    }

    function setConnectMode(on) {
      connectMode = on;
      connectFrom = null;
      connectModeBtn.textContent = `Connect: ${connectMode ? "On" : "Off"}`;
      connectModeBtn.classList.toggle("active", connectMode);
    }

    function setOrderMode(on) {
      orderMode = on;
      orderModeBtn.textContent = `Order: ${orderMode ? "On" : "Off"}`;
      orderModeBtn.classList.toggle("active", orderMode);
      if (!orderMode) errorBox.textContent = "";
    }

    function clearArchSelectionStyles() {
      const svg = archOutput.querySelector("svg");
      if (!svg) return;
      for (const g of svg.querySelectorAll("g.node")) {
        g.classList.remove("selected");
        const shape = g.querySelector("rect, polygon, path");
        if (shape) {
          shape.style.strokeWidth = "";
          shape.style.stroke = "";
          shape.style.fill = "";
        }
      }
    }

    function highlightArchNode(node) {
      clearArchSelectionStyles();
      const shape = node.querySelector("rect, polygon, path");
      if (shape) {
        // Visible selection highlight (works on light/dark themes).
        shape.style.stroke = "#f59e0b";
        shape.style.strokeWidth = "3px";
        shape.style.fill = "rgba(245, 158, 11, 0.15)";
      }
    }

    function wireArchitectureConnectors() {
      const svg = archOutput.querySelector("svg");
      if (!svg) return;

      // Remove any previous handlers by cloning the SVG root.
      const fresh = svg.cloneNode(true);
      svg.replaceWith(fresh);

      // Make nodes clickable in more browsers/themes.
      for (const g of fresh.querySelectorAll("g.node")) {
        g.style.cursor = connectMode ? "crosshair" : "pointer";
        g.style.pointerEvents = "all";
        const shape = g.querySelector("rect, polygon, path");
        if (shape) shape.style.pointerEvents = "all";
        const text = g.querySelector("text");
        if (text) text.style.pointerEvents = "all";
      }

      // Delegate at SVG level; more reliable than attaching to each node.
      fresh.addEventListener("click", (e) => {
        const target = e.target;
        if (!target || typeof target.closest !== "function") return;
        const node = target.closest("g.node");
        if (!node) return;

        e.preventDefault();
        e.stopPropagation();

        function getComponentNameFromSvgNode(gNode) {
          // 1) Try mapping from Mermaid-generated ids.
          const idCandidates = [
            gNode.getAttribute("id") || "",
            gNode.querySelector("[id]")?.getAttribute("id") || ""
          ].filter(Boolean);

          for (const id of idCandidates) {
            for (const [key, value] of lastArchIdToName.entries()) {
              if (id.includes(key)) return value;
            }
          }

          // 2) Try foreignObject (Mermaid sometimes uses HTML labels).
          const foText = (gNode.querySelector("foreignObject")?.textContent || "").trim();
          if (foText) {
            const firstLine = foText.split(/\\r?\\n/).map((s) => s.trim()).filter(Boolean)[0];
            if (firstLine) return firstLine;
          }

          // 3) Try SVG text/tspans.
          const tspans = Array.from(gNode.querySelectorAll("text tspan"))
            .map((t) => (t.textContent || "").trim())
            .filter(Boolean);
          if (tspans.length) return tspans[0];

          const textContent = (gNode.querySelector("text")?.textContent || "").trim();
          if (textContent) return textContent.split(/\s+/)[0];

          const titleContent = (gNode.querySelector("title")?.textContent || "").trim();
          return titleContent || "";
        }

        const name = getComponentNameFromSvgNode(node).trim();
        if (!name) return;

        // Always highlight the clicked component.
        highlightArchNode(node);

        // If connect mode is OFF, just highlight (no edits).
        if (!connectMode) {
          errorBox.textContent = "";
          return;
        }

        if (!connectFrom) {
          connectFrom = name;
          errorBox.textContent = `Connect mode: selected '${connectFrom}'. Now click a target component.`;
          return;
        }

        if (name.toLowerCase() === connectFrom.toLowerCase()) return;

        const updated = addUsesInText(source.value, connectFrom, name);
        source.value = updated;
        connectFrom = null;
        clearArchSelectionStyles();
        errorBox.textContent = "";
        renderDiagram();
      });
    }

    function toOrderMermaid(components, steps) {
      const lines = ["flowchart LR"];
      const compNames = components.map((c) => c.name);
      for (const name of compNames) {
        lines.push(`${normName(name)}["${escapeLabel(name)}"]`);
      }

      if (steps.length >= 2) {
        for (let i = 0; i < steps.length - 1; i++) {
          const a = steps[i];
          const b = steps[i + 1];
          if (!a || !b) continue;
          lines.push(`${normName(a)} ==> ${normName(b)}`);
        }
      } else {
        lines.push(`Hint["Turn on Order mode, then click components in sequence."]`);
      }
      return lines.join("\\n");
    }

    function wireOrderInteractions(components) {
      const svg = orderOutput.querySelector("svg");
      if (!svg) return;

      const fresh = svg.cloneNode(true);
      svg.replaceWith(fresh);

      // Always allow highlighting on click in this view.
      for (const g of fresh.querySelectorAll("g.node")) {
        g.style.cursor = orderMode ? "crosshair" : "pointer";
        g.style.pointerEvents = "all";
        const shape = g.querySelector("rect, polygon, path");
        if (shape) shape.style.pointerEvents = "all";
        const text = g.querySelector("text");
        if (text) text.style.pointerEvents = "all";
      }

      // Reuse a simple id->name map for this diagram too.
      const idToName = new Map();
      for (const c of components) idToName.set(normName(c.name), c.name);

      function getName(gNode) {
        const id = gNode.getAttribute("id") || "";
        for (const [key, value] of idToName.entries()) {
          if (id.includes(key)) return value;
        }
        const foText = (gNode.querySelector("foreignObject")?.textContent || "").trim();
        if (foText) return foText.split(/\\r?\\n/).map((s) => s.trim()).filter(Boolean)[0] || "";
        const tspan = gNode.querySelector("text tspan");
        return (tspan?.textContent || gNode.querySelector("text")?.textContent || "").trim();
      }

      fresh.addEventListener("click", (e) => {
        const target = e.target;
        if (!target || typeof target.closest !== "function") return;
        const node = target.closest("g.node");
        if (!node) return;
        const name = getName(node).trim();
        if (!name) return;

        if (!orderMode) return;

        // Append step if not duplicate of last.
        if (!orderSteps.length || orderSteps[orderSteps.length - 1].toLowerCase() !== name.toLowerCase()) {
          orderSteps.push(name);
          source.value = upsertGlobalOrder(source.value, orderSteps);
          errorBox.textContent = `Order mode: ${orderSteps.join(" → ")}`;
          renderDiagram();
        }
      });
    }

    async function renderTarget(targetEl, mermaidText, prefix) {
      const id = `${prefix}${Date.now()}`;
      const result = await mermaid.render(id, mermaidText);
      targetEl.innerHTML = result.svg;
    }

    async function renderDiagram() {
      errorBox.textContent = "";
      const text = source.value.trim();
      if (!text) {
        const emptyHtml = "<p style='padding:8px;'>Type components on the left to render a diagram.</p>";
        archOutput.innerHTML = emptyHtml;
        flowOutput.innerHTML = emptyHtml;
        orderOutput.innerHTML = emptyHtml;
        return;
      }

      try {
        const components = parseEnglish(text);
        lastArchIdToName = buildArchIdToName(components);
        orderSteps = parseGlobalOrder(text);
        mermaid.initialize({
          startOnLoad: false,
          theme: window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "default",
          securityLevel: "loose"
        });
        await renderTarget(archOutput, toArchitectureMermaid(components), "arch");
        await renderTarget(flowOutput, toFlowMermaid(components), "flow");
        await renderTarget(orderOutput, toOrderMermaid(components, orderSteps), "order");
        wireArchitectureConnectors();
        wireOrderInteractions(components);
      } catch (err) {
        errorBox.textContent = `Could not render diagram: ${err.message}`;
      }
    }

    renderBtn.addEventListener("click", renderDiagram);
    exampleBtn.addEventListener("click", () => {
      source.value = seedText;
      renderDiagram();
    });
    source.addEventListener("input", () => {
      window.clearTimeout(window.__renderTimer);
      window.__renderTimer = window.setTimeout(renderDiagram, 250);
    });
    archViewBtn.addEventListener("click", () => setView("arch"));
    flowViewBtn.addEventListener("click", () => setView("flow"));
    orderViewBtn.addEventListener("click", () => setView("order"));
    connectModeBtn.addEventListener("click", () => {
      setView("arch");
      setConnectMode(!connectMode);
      errorBox.textContent = connectMode ? "Connect mode: click a source component, then a target component." : "";
      renderDiagram();
    });
    orderModeBtn.addEventListener("click", () => {
      setView("order");
      setOrderMode(!orderMode);
      errorBox.textContent = orderMode ? "Order mode: click components in sequence." : "";
      renderDiagram();
    });
    orderUndoBtn.addEventListener("click", () => {
      if (!orderSteps.length) return;
      orderSteps.pop();
      source.value = upsertGlobalOrder(source.value, orderSteps);
      errorBox.textContent = orderSteps.length ? `Order mode: ${orderSteps.join(" → ")}` : "";
      renderDiagram();
    });
    orderClearBtn.addEventListener("click", () => {
      orderSteps = [];
      source.value = upsertGlobalOrder(source.value, orderSteps);
      errorBox.textContent = "";
      renderDiagram();
    });

    setView("arch");
    setConnectMode(false);
    setOrderMode(false);
    renderDiagram();
  </script>
</body>
</html>
"""


class BuilderHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode("utf-8"))

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        # Keep terminal output clean while students use the tool.
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a student component builder with live diagram preview."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), BuilderHandler)
    print(f"Component builder running on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
