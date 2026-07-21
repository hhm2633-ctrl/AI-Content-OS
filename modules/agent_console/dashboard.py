"""Single-file local dashboard renderer for Agent Console state."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Mapping


def _safe(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


def render_dashboard(state: Mapping[str, Any], output_path: str | Path) -> Path:
    jobs = state.get("jobs", []) if isinstance(state.get("jobs"), list) else []
    agents = state.get("agents", []) if isinstance(state.get("agents"), list) else []
    counts = {
        status: 0
        for status in (
            "awaiting_second_stage",
            "queued",
            "running",
            "completed",
            "failed",
            "blocked",
        )
    }
    for job in jobs:
        status = str(job.get("status", "")) if isinstance(job, Mapping) else ""
        if status in counts:
            counts[status] += 1

    rows = []
    for job in jobs:
        if not isinstance(job, Mapping):
            continue
        handoff = job.get("handoff") if isinstance(job.get("handoff"), Mapping) else {}
        rows.append(
            "<tr>"
            f"<td>{_safe(job.get('category'))}</td>"
            f"<td>{_safe(job.get('title'))}</td>"
            f"<td>{_safe(job.get('agent_id') or '-')}</td>"
            f"<td><span class='pill {_safe(job.get('status'))}'>{_safe(job.get('status'))}</span></td>"
            f"<td>{_safe(job.get('steps_used', 0))}/{_safe(job.get('max_steps', '-'))}</td>"
            f"<td>{_safe(handoff.get('summary') or job.get('last_error') or '-')}</td>"
            "</tr>"
        )

    raw_state = json.dumps(state, ensure_ascii=False).replace("</", "<\\/")
    agent_text = " · ".join(
        f"{_safe(agent.get('category'))}:{_safe(agent.get('backend'))}"
        for agent in agents
        if isinstance(agent, Mapping)
    ) or "등록된 담당 없음"
    document = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI-Content-OS Agent Console</title>
<style>
:root{{--bg:#0d1015;--panel:#171b22;--line:#2b313b;--text:#f4f6f8;--muted:#9aa6b2;--accent:#c9ff39}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);font-family:Arial,'Noto Sans KR',sans-serif}}
main{{max-width:1480px;margin:auto;padding:32px}} h1{{font-size:30px;margin:0 0 8px}} .sub{{color:var(--muted);margin-bottom:24px}}
.cards{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin:20px 0}} .card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px}}
.num{{font-size:28px;font-weight:800;margin-top:8px}} .label{{color:var(--muted);font-size:13px}} table{{width:100%;border-collapse:collapse;background:var(--panel);border-radius:14px;overflow:hidden}}
th,td{{padding:14px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}} th{{font-size:12px;color:var(--muted);text-transform:uppercase}} td{{font-size:14px}}
.pill{{padding:4px 8px;border-radius:999px;background:#303640}} .completed{{color:var(--accent)}} .failed{{color:#ff7777}} .running{{color:#7cc7ff}} .queued{{color:#f6cf65}} .awaiting_second_stage{{color:#c4a7ff}}
.empty{{padding:40px;text-align:center;color:var(--muted)}} @media(max-width:800px){{.cards{{grid-template-columns:repeat(2,1fr)}} main{{padding:16px}} table{{display:block;overflow:auto}}}}
</style></head><body><main>
<h1>Agent Console v1</h1><div class="sub">{agent_text}</div>
<section class="cards">{''.join(f'<div class="card"><div class="label">{k}</div><div class="num">{v}</div></div>' for k,v in counts.items())}</section>
<table><thead><tr><th>담당</th><th>작업</th><th>에이전트</th><th>상태</th><th>단계</th><th>짧은 결과</th></tr></thead><tbody>
{''.join(rows) if rows else '<tr><td colspan="6" class="empty">대기 중인 작업이 없습니다.</td></tr>'}
</tbody></table><script id="agent-console-state" type="application/json">{raw_state}</script>
</main></body></html>"""
    resolved = Path(output_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(document, encoding="utf-8")
    return resolved


__all__ = ["render_dashboard"]
