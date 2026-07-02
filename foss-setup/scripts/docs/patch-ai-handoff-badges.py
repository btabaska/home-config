#!/usr/bin/env python3
"""Inject AI handoff map + badge/filter UI into foss-setup/docs/index.html."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "docs" / "index.html"
MAP = Path(__file__).resolve().parent / "ai-handoff-map.json"

CSS = """
  .b-ai-auto { background:rgba(167,139,250,.16); color:#c4b5fd; border-color:rgba(167,139,250,.4); }
  .b-ai-auto::before { content:"\\2699"; margin-right:4px; }
  .b-ai-assisted { background:rgba(45,212,191,.12); color:var(--done); border-color:rgba(45,212,191,.35); }
  .b-ai-assisted::before { content:"\\2699"; margin-right:4px; }
"""

def main() -> None:
    data = json.loads(MAP.read_text())
    compact = json.dumps({"auto": data["auto"], "assisted": data["assisted"]}, separators=(",", ":"))
    text = HTML.read_text()

    if 'id="aiHandoffMap"' not in text:
        text = text.replace(
            '<script type="application/json" id="taskData">',
            f'<script type="application/json" id="aiHandoffMap">{compact}</script>\n<script type="application/json" id="taskData">',
            1,
        )

    if ".b-ai-auto" not in text:
        text = text.replace("  .b-req::before { content:\"\\2605\"; margin-right:4px; }", "  .b-req::before { content:\"\\2605\"; margin-right:4px; }" + CSS)

    if 'id="aiHandoffFilter"' not in text:
        text = text.replace(
            '    <button id="reqFilter" class="req-toggle"',
            '    <button id="aiHandoffFilter" class="req-toggle" aria-pressed="false" title="Show only tasks an AI agent can run with SSH/sudo (full handoff or brief spot-check)">AI handoff only</button>\n    <button id="reqFilter" class="req-toggle"',
            1,
        )

    legend = (
        '      <span><i class="dot" style="background:#c4b5fd"></i> <b>AI handoff</b> — agent can run via SSH/sudo with minimal input</span>\n'
        '      <span><i class="dot" style="background:var(--done)"></i> <b>AI + you</b> — agent does bulk work; you provide a key, OAuth, or spot-check</span>\n'
    )
    if "AI handoff" not in text:
        text = text.replace(
            '      <span><i class="dot" style="background:#ff7b72"></i> <b>Required</b>',
            legend + '      <span><i class="dot" style="background:#ff7b72"></i> <b>Required</b>',
            1,
        )

    # Refresh embedded map if script re-run
    block = f'<script type="application/json" id="aiHandoffMap">{compact}</script>'
    if 'id="aiHandoffMap"' in text:
        text = re.sub(
            r'<script type="application/json" id="aiHandoffMap">.*?</script>',
            lambda _m: block,
            text,
            count=1,
            flags=re.S,
        )

  # JS hooks — idempotent single-pass patches
    if "const aiHandoff" not in text:
        text = text.replace(
            '  const tasks = JSON.parse(document.getElementById("taskData").textContent);',
            '  const tasks = JSON.parse(document.getElementById("taskData").textContent);\n'
            '  const aiHandoff = JSON.parse(document.getElementById("aiHandoffMap").textContent);',
            1,
        )

    if "function aiTier" not in text:
        text = text.replace(
            "  const isRequired = t => !!t.required;",
            "  const isRequired = t => !!t.required;\n"
            "  function aiTier(id){ if(aiHandoff.auto[id]) return 'auto'; if(aiHandoff.assisted[id]) return 'assisted'; return ''; }\n"
            "  function aiBadge(id){ const tier=aiTier(id); if(tier==='auto') return badge('b-ai-auto','AI handoff'); if(tier==='assisted') return badge('b-ai-assisted','AI + you'); return ''; }",
            1,
        )

    if "data-ai-handoff" not in text:
        text = text.replace(
            '${hw}\n          </div>',
            "${hw}\n            ${aiBadge(t.id)}\n          </div>",
            1,
        )
        text = text.replace(
            'data-required="${isRequired(t)?\'1\':\'0\'}"',
            'data-required="${isRequired(t)?\'1\':\'0\'}" data-ai-handoff="${aiTier(t.id)}"',
            1,
        )

    if "fAiHandoff" not in text:
        text = text.replace(
            '  let fType = "all", fHost = "all", fDone = "all", fReq = false;',
            '  let fType = "all", fHost = "all", fDone = "all", fReq = false, fAiHandoff = false;',
            1,
        )
        text = text.replace(
            "      const okReq = !fReq || card.dataset.required===\"1\";\n"
            "      card.classList.toggle(\"hide\", !(okType&&okHost&&okDone&&okReq));",
            "      const okReq = !fReq || card.dataset.required===\"1\";\n"
            "      const okAi = !fAiHandoff || (card.dataset.aiHandoff === 'auto' || card.dataset.aiHandoff === 'assisted');\n"
            "      card.classList.toggle(\"hide\", !(okType&&okHost&&okDone&&okReq&&okAi));",
            1,
        )
        text = text.replace(
            '  document.getElementById("reqFilter").addEventListener("click", e=>{',
            '  document.getElementById("aiHandoffFilter").addEventListener("click", e=>{\n'
            "    fAiHandoff = !fAiHandoff;\n"
            '    e.target.classList.toggle("on", fAiHandoff);\n'
            '    e.target.setAttribute("aria-pressed", fAiHandoff ? "true" : "false");\n'
            "    applyFilters();\n"
            "  });\n"
            '  document.getElementById("reqFilter").addEventListener("click", e=>{',
            1,
        )

    HTML.write_text(text)
    auto_n = len(data["auto"])
    assisted_n = len(data["assisted"])
    print(f"Patched {HTML.name}: {auto_n} AI handoff + {assisted_n} AI + you badges")


if __name__ == "__main__":
    main()
