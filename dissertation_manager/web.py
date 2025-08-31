from __future__ import annotations

import urllib.parse
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Tuple

from . import SECTIONS
from .core import (
    DEFAULT_SECTION_TARGETS,
    LIFECYCLE_PHASES,
    export_markdown,
    get_status,
    get_section_lifecycle,
    section_lifecycle_percent,
    import_section_from_file,
    init_project,
    load_config,
    set_section_lifecycle,
    save_config,
    section_file,
)


def html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def slugify(text: str) -> str:
    s = ''.join(ch.lower() if ch.isalnum() else '-' for ch in text.strip())
    while '--' in s:
        s = s.replace('--', '-')
    return s.strip('-') or 'student'


def layout(title: str, body: str, nav_html: str | None = None) -> str:
    nav_html = nav_html or """
        <a href=\"/\">Dashboard</a>
        <a href=\"/targets\">Targets</a>
        <a href=\"/export\" class=\"btn\">Export</a>
    """
    return f"""
<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{html_escape(title)}</title>
  <style>
    :root {{ --fg:#111; --bg:#fff; --muted:#666; --accent:#0b6; --err:#b00; font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; }}
    body {{ margin: 2rem auto; max-width: 900px; padding: 0 1rem; color: var(--fg); background: var(--bg); }}
    a {{ color: var(--accent); text-decoration: none; }}
    header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem; }}
    nav a {{ margin-right: 1rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid #eee; padding: .5rem; text-align: left; }}
    .muted {{ color: var(--muted); }}
    .btn {{ display:inline-block; padding:.4rem .7rem; border:1px solid #ddd; border-radius:6px; }}
    .grid {{ display:grid; grid-template-columns: 1fr 1fr; gap:1rem; }}
    textarea {{ width:100%; height: 60vh; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace; font-size: 14px; }}
    input[type=text] {{ width:100%; padding:.4rem; }}
    input[type=number] {{ width:100%; padding:.4rem; }}
    form {{ margin: 0; }}
    .right {{ text-align:right; }}
    .ok {{ color: #0a7; }}
    .donut {{ display:inline-block; position: relative; }}
    .donut svg {{ display:block; }}
    .donut .label {{ position:absolute; inset:0; display:flex; align-items:center; justify-content:center; font-size: .9rem; }}
  </style>
  <link rel=\"icon\" href=\"data:,\" />
  <meta name=\"color-scheme\" content=\"light dark\" />
  <script>
  // Simple client-side navigation helpers
  function post(path, data) {{
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = path;
    for (const [k, v] of Object.entries(data)) {{
      const input = document.createElement('input');
      input.type = 'hidden'; input.name = k; input.value = v;
      form.appendChild(input);
    }}
    document.body.appendChild(form); form.submit();
  }}
  </script>
  </head>
  <body>
    <header>
      <div><strong>Dissertation Manager</strong></div>
      <nav>
        {nav_html}
      </nav>
    </header>
    {body}
  </body>
</html>
"""


def decode_post(body: bytes) -> Dict[str, str]:
    data = urllib.parse.parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return {k: v[-1] if v else "" for k, v in data.items()}


def project_exists(root: Path) -> bool:
    return (root / ".dissertation" / "config.json").exists()


class Handler(BaseHTTPRequestHandler):
    server_version = "DissertationManager/0.1"

    @property
    def root(self) -> Path:
        return Path(getattr(self.server, "project_root", Path.cwd()))

    @property
    def advisor_root(self) -> Path | None:
        ar = getattr(self.server, "advisor_root", None)
        return Path(ar) if ar else None

    def is_advisor(self) -> bool:
        return self.advisor_root is not None

    # Build top navigation depending on mode and path
    def build_nav(self) -> str:
        if self.is_advisor():
            # If inside a specific student page, add a Report link
            nav = [
                "<a href='/' >Dashboard</a>",
                "<a href='/overview'>Overview</a>",
                "<a href='/summary'>Summary</a>",
                f"<a href='/heatmap?section={urllib.parse.quote(SECTIONS[0])}'>Heatmap</a>",
                "<a href='/signup'>Sign Up</a>",
                "<a href='/export.json'>Export JSON</a>",
                "<a href='/export.csv' class='btn'>Export CSV</a>",
            ]
            if self.path.startswith("/student/"):
                nav.insert(1, f"<a href='{html_escape(self.path.split('?')[0].rstrip('/'))}/report'>Student Report</a>")
            return "\n".join(nav)
        else:
            return "\n".join([
                "<a href='/' >Dashboard</a>",
                "<a href='/targets'>Targets</a>",
                "<a href='/report'>Report</a>",
                "<a href='/export' class='btn'>Export</a>",
            ])

    def do_GET(self) -> None:  # noqa: N802
        try:
            self.route_get()
        except Exception as e:  # pragma: no cover - keep server resilient
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, explain=str(e))

    def do_POST(self) -> None:  # noqa: N802
        try:
            self.route_post()
        except Exception as e:  # pragma: no cover
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, explain=str(e))

    # Routing
    def route_get(self) -> None:
        path, _, query = self.path.partition("?")
        q = urllib.parse.parse_qs(query)
        if self.is_advisor():
            if path == "/":
                return self.page_advisor()
            if path == "/summary":
                return self.page_advisor_summary()
            if path == "/overview":
                return self.page_advisor_overview()
            if path == "/signup":
                return self.page_signup()
            if path == "/export.json":
                return self.page_advisor_export_json()
            if path == "/export.csv":
                return self.page_advisor_export_csv()
            if path == "/heatmap":
                section = (q.get("section", [SECTIONS[1] if len(SECTIONS) > 1 else SECTIONS[0]])[0])
                return self.page_advisor_heatmap(section)
            if path.startswith("/student/"):
                return self.route_student_get(path)
            return self.send_error(HTTPStatus.NOT_FOUND, explain="Not found")
        if path == "/":
            self.page_dashboard()
        elif path.startswith("/sections/"):
            parts = path.split("/", 4)
            section = parts[2]
            if len(parts) >= 4 and parts[3] == "lifecycle":
                self.page_lifecycle(section)
            else:
                self.page_edit_section(section)
        elif path == "/targets":
            self.page_targets()
        elif path == "/report":
            self.page_report()
        elif path == "/export":
            self.page_export()
        else:
            self.send_error(HTTPStatus.NOT_FOUND, explain="Not found")

    def route_post(self) -> None:
        path, _, _ = self.path.partition("?")
        length = int(self.headers.get("Content-Length", "0"))
        data = decode_post(self.rfile.read(length)) if length else {}
        if self.is_advisor():
            if path.startswith("/student/"):
                return self.route_student_post(path, data)
            if path == "/signup":
                return self.post_signup(data)
            return self.send_error(HTTPStatus.NOT_FOUND, explain="Not found")
        if path == "/init":
            self.post_init(data)
        elif path.startswith("/sections/"):
            parts = path.split("/", 4)
            section = parts[2]
            if len(parts) >= 4 and parts[3] == "lifecycle":
                self.post_lifecycle(section, data)
            else:
                self.post_save_section(section, data)
        elif path == "/targets":
            self.post_targets(data)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, explain="Not found")

    # Pages
    def page_dashboard(self) -> None:
        if not project_exists(self.root):
            body = self.render_init_form()
            return self._html(body)
        st = get_status(self.root)
        # Overall donut
        overall = svg_donut(st.get("percent_total", 0), size=120, stroke=14, label=f"{st.get('percent_total',0)}%")
        rows = []
        for sec in st["sections"]:
            prog = f"{sec['words']} / {sec['target']}" if sec["target"] else str(sec["words"])
            donut = svg_donut(sec.get("percent", 0), size=60, stroke=8, label=f"{sec.get('percent',0)}%")
            rows.append(
                f"<tr>"
                f"<td style='width:84px'>{donut}</td>"
                f"<td><a href='/sections/{sec['section']}'>{html_escape(sec['section'].replace('_',' ').title())}</a><br>"
                f"<span class='muted'><a href='/sections/{sec['section']}/lifecycle'>Lifecycle</a></span></td>"
                f"<td>{prog}</td><td class='muted'>{html_escape(sec['file'])}</td>"
                f"</tr>"
            )
        total = (
            f"{st['total_words']} / {st['total_target']}"
            if st["total_target"]
            else str(st["total_words"])
        )
        meta = [
            f"<div><strong>{html_escape(st['title'])}</strong></div>" +
            f"<div class='muted'>By {html_escape(st['author'])}</div>"
        ]
        if st.get("degree") or st.get("institution"):
            extras = []
            if st.get("degree"):
                extras.append(f"Degree: {html_escape(st['degree'])}")
            if st.get("institution"):
                extras.append(f"Institution: {html_escape(st['institution'])}")
            meta.append("<div class='muted'>" + " | ".join(extras) + "</div>")
        if st.get("supervisor"):
            meta.append(f"<div class='muted'>Supervisor: {html_escape(st['supervisor'])}</div>")

        body = f"""
        <section>
          <div style='display:flex; align-items:center; gap:1rem;'>
            <div class='donut'>{overall}</div>
            <div>{''.join(meta)}</div>
          </div>
        </section>
        <section>
          <h3>Sections</h3>
          <table>
            <thead><tr><th>Progress</th><th>Section</th><th>Words</th><th>Path</th></tr></thead>
            <tbody>
              {''.join(rows)}
            </tbody>
          </table>
          <div class='right muted' style='margin-top:.5rem;'>Total: {html_escape(total)}</div>
        </section>
        """
        self._html(body)

    # Advisor: list students under advisor_root
    def page_advisor(self) -> None:
        ar = self.advisor_root
        assert ar is not None
        rows = []
        if ar.exists() and ar.is_dir():
            for child in sorted(ar.iterdir()):
                if not child.is_dir() or not project_exists(child):
                    continue
                try:
                    st = get_status(child)
                except Exception:
                    continue
                slug = urllib.parse.quote(child.name)
                donut = svg_donut(st.get("percent_total", 0), size=60, stroke=8, label=f"{st.get('percent_total',0)}%")
                rows.append(
                    f"<tr>"
                    f"<td style='width:84px'>{donut}</td>"
                    f"<td><a href='/student/{slug}/'>{html_escape(st['author'])}</a><br><span class='muted'>{html_escape(st['title'])}</span></td>"
                    f"<td class='muted'>{html_escape(str(child))}</td>"
                    f"</tr>"
                )
        body = f"""
        <h3>Advisor Dashboard</h3>
        <div class='right' style='margin-bottom:.5rem;'>
          <a class='btn' href='/signup'>New Student</a>
        </div>
        <table>
          <thead><tr><th>Progress</th><th>Student</th><th>Path</th></tr></thead>
          <tbody>
            {''.join(rows) if rows else '<tr><td colspan="3" class="muted">No student projects found.</td></tr>'}
          </tbody>
        </table>
        """
        self._html(body)

    def page_signup(self) -> None:
        ar = self.advisor_root
        assert ar is not None
        body = f"""
        <h3>Student Sign Up</h3>
        <form method='post' action='/signup' class='grid'>
          <div>
            <label>Student name (author)<br><input type='text' name='author' required></label>
          </div>
          <div>
            <label>Slug (optional)<br><input type='text' name='slug' placeholder='e.g. j-doe'></label>
          </div>
          <div>
            <label>Title<br><input type='text' name='title' required></label>
          </div>
          <div>
            <label>Degree<br><input type='text' name='degree'></label>
          </div>
          <div>
            <label>Institution<br><input type='text' name='institution'></label>
          </div>
          <div>
            <label>Supervisor<br><input type='text' name='supervisor'></label>
          </div>
          <div>
            <label>Initial targets (optional)<br><input type='text' name='targets' placeholder='introduction=1500,literature_review=4000,...'></label>
          </div>
          <div class='right'>
            <button class='btn' type='submit'>Create Project</button>
          </div>
        </form>
        <div class='muted' style='margin-top:.5rem;'>Projects are created under: {html_escape(str(ar))}</div>
        """
        self._html(body)

    def post_signup(self, data: Dict[str, str]) -> None:
        ar = self.advisor_root
        assert ar is not None
        author = (data.get('author') or '').strip()
        title = (data.get('title') or '').strip()
        degree = (data.get('degree') or '').strip() or None
        institution = (data.get('institution') or '').strip() or None
        supervisor = (data.get('supervisor') or '').strip() or None
        slug = (data.get('slug') or '').strip() or slugify(author or 'student')
        targets_str = (data.get('targets') or '').strip()
        targets = DEFAULT_SECTION_TARGETS.copy()
        if targets_str:
            for pair in targets_str.split(','):
                if not pair.strip() or '=' not in pair:
                    continue
                k, v = pair.split('=', 1)
                if k.strip() in SECTIONS:
                    try:
                        targets[k.strip()] = int(v)
                    except Exception:
                        pass
        if not author or not title:
            return self.send_error(HTTPStatus.BAD_REQUEST, explain='Author and Title are required')
        # Ensure unique slug
        base = slugify(slug)
        candidate = base
        i = 2
        while (ar / candidate).exists():
            candidate = f"{base}-{i}"
            i += 1
        project_dir = ar / candidate
        project_dir.mkdir(parents=True, exist_ok=False)
        init_project(
            project_dir,
            title=title,
            author=author,
            supervisor=supervisor,
            degree=degree,
            institution=institution,
            section_targets=targets,
            overwrite=False,
        )
        self.redirect(f"/student/{urllib.parse.quote(candidate)}/")

    def page_advisor_summary(self) -> None:
        ar = self.advisor_root
        assert ar is not None
        # Build table: Student vs sections, cells show lifecycle percent donuts
        headers = ''.join([f"<th>{html_escape(s.replace('_',' ').title())}</th>" for s in SECTIONS])
        rows_html = []
        if ar.exists() and ar.is_dir():
            for child in sorted(ar.iterdir()):
                if not child.is_dir() or not project_exists(child):
                    continue
                try:
                    cfg = load_config(child)
                except Exception:
                    continue
                cells = []
                for s in SECTIONS:
                    try:
                        p = section_lifecycle_percent(cfg, s)
                    except Exception:
                        p = 0
                    cells.append(f"<td style='width:72px'>{svg_donut(p, size=48, stroke=7, label=str(p)+'%')}</td>")
                name = html_escape(cfg.author)
                slug = urllib.parse.quote(child.name)
                rows_html.append(f"<tr><td><a href='/student/{slug}/'>{name}</a></td>{''.join(cells)}</tr>")
        body = f"""
        <h3>Advisor Summary: Lifecycle by Section</h3>
        <div class='muted' style='margin:.5rem 0;'>Each cell shows the average lifecycle progress for that student's section.</div>
        <table>
          <thead><tr><th>Student</th>{headers}</tr></thead>
          <tbody>
            {''.join(rows_html) if rows_html else '<tr><td class="muted" colspan="6">No student projects found.</td></tr>'}
          </tbody>
        </table>
        """
        self._html(body)

    def page_advisor_overview(self) -> None:
        ar = self.advisor_root
        assert ar is not None
        # Compute averages over students
        students = []
        if ar.exists() and ar.is_dir():
            for child in sorted(ar.iterdir()):
                if not child.is_dir() or not project_exists(child):
                    continue
                try:
                    st = get_status(child)
                except Exception:
                    continue
                students.append(st)
        n = len(students)
        if n == 0:
            return self._html("<p class='muted'>No student projects found.</p>")
        # Overall averages
        avg_total = round(sum(s.get('percent_total', 0) for s in students) / n)
        avg_words = round(sum(s.get('percent_total_words', 0) for s in students) / n)
        avg_life = round(sum(s.get('percent_total_lifecycle', 0) for s in students) / n)
        donut = svg_donut(avg_total, size=120, stroke=14, label=f"{avg_total}%")
        # Per-section averages
        sec_rows = []
        for sec_name in SECTIONS:
            words_list = []
            life_list = []
            comb_list = []
            for s in students:
                for sec in s.get('sections', []):
                    if sec.get('section') == sec_name:
                        words_list.append(sec.get('percent_words', 0))
                        life_list.append(sec.get('percent_lifecycle', 0))
                        comb_list.append(sec.get('percent', 0))
                        break
            if words_list:
                aw = round(sum(words_list)/len(words_list))
                al = round(sum(life_list)/len(life_list))
                ac = round(sum(comb_list)/len(comb_list))
            else:
                aw = al = ac = 0
            sec_rows.append(
                f"<tr><td>{html_escape(sec_name.replace('_',' ').title())}</td>"
                f"<td style='width:84px'>{svg_donut(aw, size=60, stroke=8, label=str(aw)+'%')}</td>"
                f"<td style='width:84px'>{svg_donut(al, size=60, stroke=8, label=str(al)+'%')}</td>"
                f"<td style='width:84px'>{svg_donut(ac, size=60, stroke=8, label=str(ac)+'%')}</td></tr>"
            )
        body = f"""
        <h3>Advisor Overview</h3>
        <div style='display:flex; align-items:center; gap:1rem;'>
          <div class='donut'>{donut}</div>
          <div>
            <div><strong>Average Combined Progress</strong></div>
            <div class='muted'>Across {n} students — words avg: {avg_words}%, lifecycle avg: {avg_life}%</div>
          </div>
        </div>
        <h4 style='margin-top:1rem;'>Per-Section Averages</h4>
        <table>
          <thead><tr><th>Section</th><th>Words%</th><th>Lifecycle%</th><th>Combined%</th></tr></thead>
          <tbody>
            {''.join(sec_rows)}
          </tbody>
        </table>
        """
        self._html(body)

    def page_advisor_heatmap(self, section: str) -> None:
        ar = self.advisor_root
        assert ar is not None
        # Canonical phases (from first project if available)
        phases = None
        students = []
        if ar.exists() and ar.is_dir():
            for child in sorted(ar.iterdir()):
                if not child.is_dir() or not project_exists(child):
                    continue
                try:
                    cfg = load_config(child)
                except Exception:
                    continue
                if phases is None:
                    phases = cfg.lifecycle_phases or LIFECYCLE_PHASES
                values = (cfg.lifecycle_progress or {}).get(section, {})
                students.append((child.name, cfg.author, values))
        phases = phases or LIFECYCLE_PHASES
        # Build header and rows
        header = ''.join([f"<th>{html_escape(p)}</th>" for p in phases])
        rows = []
        for slug, name, values in students:
            cells = []
            for p in phases:
                v = int(values.get(p, 0))
                cells.append(f"<td style='width:72px'>{svg_donut(v, size=44, stroke=7, label=str(v)+'%')}</td>")
            rows.append(
                f"<tr><td><a href='/student/{urllib.parse.quote(slug)}/sections/{html_escape(section)}/lifecycle'>{html_escape(name)}</a></td>" + ''.join(cells) + "</tr>"
            )
        # Section chooser
        options = []
        for s in SECTIONS:
            sel = " selected" if s == section else ""
            options.append(f"<option value='{html_escape(s)}'{sel}>{html_escape(s.replace('_',' ').title())}</option>")
        body = f"""
        <h3>Lifecycle Heatmap</h3>
        <form method='get' action='/heatmap' style='margin:.5rem 0;'>
          <label>Section
            <select name='section' onchange='this.form.submit()'>
              {''.join(options)}
            </select>
          </label>
        </form>
        <table>
          <thead><tr><th>Student</th>{header}</tr></thead>
          <tbody>
            {''.join(rows) if rows else '<tr><td class="muted" colspan="7">No student projects found.</td></tr>'}
          </tbody>
        </table>
        """
        self._html(body)

    def page_advisor_export_json(self) -> None:
        import json
        ar = self.advisor_root
        assert ar is not None
        out = []
        if ar.exists() and ar.is_dir():
            for child in sorted(ar.iterdir()):
                if not child.is_dir() or not project_exists(child):
                    continue
                try:
                    st = get_status(child)
                except Exception:
                    continue
                out.append(st)
        data = json.dumps(out, indent=2).encode('utf-8')
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def page_advisor_export_csv(self) -> None:
        import io, csv
        ar = self.advisor_root
        assert ar is not None
        buf = io.StringIO()
        writer = csv.writer(buf)
        # Header includes per-section combined percent and words
        section_percent_cols = [f'{s}_percent' for s in SECTIONS]
        section_word_cols = [f'{s}_words' for s in SECTIONS]
        header = [
            'author','title','degree','institution','supervisor',
            'total_words','total_target','percent_total','percent_total_words','percent_total_lifecycle'
        ] + section_percent_cols + section_word_cols
        writer.writerow(header)
        if ar.exists() and ar.is_dir():
            for child in sorted(ar.iterdir()):
                if not child.is_dir() or not project_exists(child):
                    continue
                try:
                    st = get_status(child)
                except Exception:
                    continue
                row = [
                    st.get('author'), st.get('title'), st.get('degree'), st.get('institution'), st.get('supervisor'),
                    st.get('total_words'), st.get('total_target'), st.get('percent_total'), st.get('percent_total_words'), st.get('percent_total_lifecycle')
                ]
                per_percent = []
                per_words = []
                for sec in st.get('sections', []):
                    per_percent.append(sec.get('percent'))
                    per_words.append(sec.get('words'))
                writer.writerow(row + per_percent + per_words)
        data = buf.getvalue().encode('utf-8')
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', 'text/csv; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Content-Disposition', 'attachment; filename=advisor_rollup.csv')
        self.end_headers()
        self.wfile.write(data)

    def page_dashboard_for(self, project_root: Path, base_prefix: str) -> None:
        if not project_exists(project_root):
            return self.redirect("/")
        st = get_status(project_root)
        overall = svg_donut(st.get("percent_total", 0), size=120, stroke=14, label=f"{st.get('percent_total',0)}%")
        rows = []
        for sec in st["sections"]:
            prog = f"{sec['words']} / {sec['target']}" if sec["target"] else str(sec["words"])
            donut = svg_donut(sec.get("percent", 0), size=60, stroke=8, label=f"{sec.get('percent',0)}%")
            rows.append(
                f"<tr>"
                f"<td style='width:84px'>{donut}</td>"
                f"<td><a href='{base_prefix}/sections/{sec['section']}'>{html_escape(sec['section'].replace('_',' ').title())}</a><br>"
                f"<span class='muted'><a href='{base_prefix}/sections/{sec['section']}/lifecycle'>Lifecycle</a></span></td>"
                f"<td>{prog}</td><td class='muted'>{html_escape(sec['file'])}</td>"
                f"</tr>"
            )
        total = (
            f"{st['total_words']} / {st['total_target']}"
            if st["total_target"]
            else str(st["total_words"])
        )
        meta = [
            f"<div><strong>{html_escape(st['title'])}</strong></div>" +
            f"<div class='muted'>By {html_escape(st['author'])}</div>"
        ]
        if st.get("degree") or st.get("institution"):
            extras = []
            if st.get("degree"):
                extras.append(f"Degree: {html_escape(st['degree'])}")
            if st.get("institution"):
                extras.append(f"Institution: {html_escape(st['institution'])}")
            meta.append("<div class='muted'>" + " | ".join(extras) + "</div>")
        if st.get("supervisor"):
            meta.append(f"<div class='muted'>Supervisor: {html_escape(st['supervisor'])}</div>")
        body = f"""
        <section>
          <div style='display:flex; align-items:center; gap:1rem;'>
            <div class='donut'>{overall}</div>
            <div>{''.join(meta)}</div>
          </div>
        </section>
        <section>
          <h3>Sections</h3>
          <table>
            <thead><tr><th>Progress</th><th>Section</th><th>Words</th><th>Path</th></tr></thead>
            <tbody>
              {''.join(rows)}
            </tbody>
          </table>
          <div class='right muted' style='margin-top:.5rem;'>Total: {html_escape(total)}</div>
        </section>
        """
        self._html(body)

    def route_student_get(self, path: str) -> None:
        parts = path.split("/", 4)
        if len(parts) < 3:
            return self.send_error(HTTPStatus.NOT_FOUND)
        slug = urllib.parse.unquote(parts[2])
        ar = self.advisor_root
        pr = (ar / slug) if ar else None
        if pr is None or not project_exists(pr):
            return self.send_error(HTTPStatus.NOT_FOUND)
        if len(parts) == 3 or parts[3] == "":
            return self.page_dashboard_for(pr, f"/student/{urllib.parse.quote(slug)}")
        sub = "/" + parts[3]
        if sub.startswith("/sections/"):
            subparts = sub.split("/", 4)
            section = subparts[2]
            if len(subparts) >= 4 and subparts[3] == "lifecycle":
                return self.page_lifecycle(section, project_root=pr)
            return self.page_edit_section(section, project_root=pr)
        if sub == "/targets":
            return self.page_targets_for(pr)
        if sub == "/export":
            return self.page_export_for(pr)
        if sub == "/report":
            return self.page_report_for(pr)
        return self.send_error(HTTPStatus.NOT_FOUND)

    def route_student_post(self, path: str, data: Dict[str, str]) -> None:
        parts = path.split("/", 4)
        if len(parts) < 3:
            return self.send_error(HTTPStatus.NOT_FOUND)
        slug = urllib.parse.unquote(parts[2])
        ar = self.advisor_root
        pr = (ar / slug) if ar else None
        if pr is None or not project_exists(pr):
            return self.send_error(HTTPStatus.NOT_FOUND)
        sub = "/" + (parts[3] if len(parts) >= 4 else "")
        if sub.startswith("/sections/"):
            subparts = sub.split("/", 4)
            section = subparts[2]
            if len(subparts) >= 4 and subparts[3] == "lifecycle":
                return self.post_lifecycle(section, data, project_root=pr)
            return self.post_save_section(section, data, project_root=pr)
        if sub == "/targets":
            return self.post_targets(data, project_root=pr)
        return self.send_error(HTTPStatus.NOT_FOUND)

    def render_init_form(self) -> str:
        return f"""
        <h3>Initialize Dissertation Project</h3>
        <form method='post' action='/init' class='grid'>
          <div>
            <label>Title<br><input type='text' name='title' required></label>
          </div>
          <div>
            <label>Author<br><input type='text' name='author' required></label>
          </div>
          <div>
            <label>Supervisor<br><input type='text' name='supervisor'></label>
          </div>
          <div>
            <label>Degree<br><input type='text' name='degree'></label>
          </div>
          <div>
            <label>Institution<br><input type='text' name='institution'></label>
          </div>
          <div>
            <label>Seed targets (optional)<br>
              <input type='text' name='targets' placeholder='introduction=1500,literature_review=4000,...'>
            </label>
          </div>
          <div class='right'>
            <button class='btn' type='submit'>Create Project</button>
          </div>
        </form>
        """

    def page_edit_section(self, section: str, project_root: Path | None = None) -> None:
        if section not in SECTIONS:
            self.send_error(HTTPStatus.NOT_FOUND, explain="Unknown section")
            return
        root = project_root or self.root
        if not project_exists(root):
            self.redirect("/")
            return
        fp = section_file(root, section)
        text = fp.read_text(encoding="utf-8") if fp.exists() else ""
        body = f"""
        <h3>Edit: {html_escape(section.replace('_',' ').title())}</h3>
        <form method='post' action='{html_escape(self.path)}'>
          <textarea name='content'>{html_escape(text)}</textarea>
          <div class='right' style='margin-top:.5rem;'>
            <button class='btn' type='submit'>Save</button>
            <a class='btn' href='/'>Back</a>
          </div>
        </form>
        """
        self._html(body)

    def page_targets(self) -> None:
        if not project_exists(self.root):
            self.redirect("/")
            return
        cfg = load_config(self.root)
        rows = []
        for s in SECTIONS:
            current = (cfg.section_targets or DEFAULT_SECTION_TARGETS).get(s, 0)
            rows.append(
                f"<tr><td>{html_escape(s.replace('_',' ').title())}</td>"
                f"<td><input type='number' name='{html_escape(s)}' value='{current}' min='0'></td></tr>"
            )
        w_words = int((cfg.progress_weights or {}).get("words", 70))
        w_life = int((cfg.progress_weights or {}).get("lifecycle", 30))
        body = f"""
        <h3>Section Targets</h3>
        <form method='post' action='/targets'>
          <table>
            <thead><tr><th>Section</th><th>Target (words)</th></tr></thead>
            <tbody>
              {''.join(rows)}
            </tbody>
          </table>
          <h4 style='margin-top:1rem;'>Progress Weights</h4>
          <div class='grid'>
            <label>Words weight (%)<br><input type='number' name='weight_words' value='{w_words}' min='0'></label>
            <label>Lifecycle weight (%)<br><input type='number' name='weight_lifecycle' value='{w_life}' min='0'></label>
          </div>
          <div class='muted' style='margin:.5rem 0;'>Weights combine words and lifecycle into the donuts by averaging with these weights.</div>
          <div class='right' style='margin-top:.5rem;'>
            <button class='btn' type='submit'>Save Targets</button>
            <a class='btn' href='/'>Back</a>
          </div>
        </form>
        """
        self._html(body)

    def page_targets_for(self, project_root: Path) -> None:
        if not project_exists(project_root):
            return self.redirect("/")
        cfg = load_config(project_root)
        rows = []
        for s in SECTIONS:
            current = (cfg.section_targets or DEFAULT_SECTION_TARGETS).get(s, 0)
            rows.append(
                f"<tr><td>{html_escape(s.replace('_',' ').title())}</td>"
                f"<td><input type='number' name='{html_escape(s)}' value='{current}' min='0'></td></tr>"
            )
        w_words = int((cfg.progress_weights or {}).get("words", 70))
        w_life = int((cfg.progress_weights or {}).get("lifecycle", 30))
        body = f"""
        <h3>Section Targets</h3>
        <form method='post' action='{html_escape(self.path)}'>
          <table>
            <thead><tr><th>Section</th><th>Target (words)</th></tr></thead>
            <tbody>
              {''.join(rows)}
            </tbody>
          </table>
          <h4 style='margin-top:1rem;'>Progress Weights</h4>
          <div class='grid'>
            <label>Words weight (%)<br><input type='number' name='weight_words' value='{w_words}' min='0'></label>
            <label>Lifecycle weight (%)<br><input type='number' name='weight_lifecycle' value='{w_life}' min='0'></label>
          </div>
          <div class='muted' style='margin:.5rem 0;'>Weights combine words and lifecycle into the donuts by averaging with these weights.</div>
          <div class='right' style='margin-top:.5rem;'>
            <button class='btn' type='submit'>Save Targets</button>
            <a class='btn' href='/'>Back</a>
          </div>
        </form>
        """
        self._html(body)

    def page_lifecycle(self, section: str, project_root: Path | None = None) -> None:
        if section not in SECTIONS:
            self.send_error(HTTPStatus.NOT_FOUND, explain="Unknown section")
            return
        root = project_root or self.root
        if not project_exists(root):
            self.redirect("/")
            return
        cfg = load_config(root)
        phases = cfg.lifecycle_phases or []
        values = get_section_lifecycle(root, section)
        rows = []
        for p in phases:
            val = int(values.get(p, 0))
            donut = svg_donut(val, size=60, stroke=8, label=f"{val}%")
            rows.append(
                f"<tr>"
                f"<td style='width:84px'>{donut}</td>"
                f"<td>{html_escape(p)}</td>"
                f"<td style='min-width:200px'>"
                f"<input type='range' name='{html_escape(p)}' value='{val}' min='0' max='100' oninput=\"document.getElementById('n_{html_escape(p)}').value=this.value\">"
                f"</td>"
                f"<td style='width:90px'><input id='n_{html_escape(p)}' type='number' name='{html_escape(p)}' value='{val}' min='0' max='100'></td>"
                f"</tr>"
            )
        body = f"""
        <h3>Lifecycle: {html_escape(section.replace('_',' ').title())}</h3>
        <form method='post' action='{html_escape(self.path)}'>
          <table>
            <thead><tr><th>Progress</th><th>Phase</th><th>Adjust</th><th>%</th></tr></thead>
            <tbody>
              {''.join(rows)}
            </tbody>
          </table>
          <div class='right' style='margin-top:.5rem;'>
            <button class='btn' type='submit'>Save Lifecycle</button>
            <a class='btn' href='/'>Back</a>
          </div>
        </form>
        """
        self._html(body)

    def page_export(self) -> None:
        if not project_exists(self.root):
            self.redirect("/")
            return
        out = self.root / "exports" / "dissertation.md"
        export_markdown(self.root, out)
        data = out.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", "attachment; filename=dissertation.md")
        self.end_headers()
        self.wfile.write(data)

    def page_report(self) -> None:
        if not project_exists(self.root):
            return self.redirect("/")
        body = self.render_report(self.root)
        self._html(body)

    def page_export_for(self, project_root: Path) -> None:
        if not project_exists(project_root):
            return self.redirect("/")
        out = project_root / "exports" / "dissertation.md"
        export_markdown(project_root, out)
        data = out.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", "attachment; filename=dissertation.md")
        self.end_headers()
        self.wfile.write(data)

    def page_report_for(self, project_root: Path) -> None:
        if not project_exists(project_root):
            return self.redirect("/")
        body = self.render_report(project_root)
        self._html(body)

    def render_report(self, project_root: Path) -> str:
        import datetime
        st = get_status(project_root)
        cfg = load_config(project_root)
        overall = svg_donut(st.get("percent_total", 0), size=140, stroke=16, label=f"{st.get('percent_total',0)}%")
        # Sections table
        sec_rows = []
        for sec in st.get("sections", []):
            donut = svg_donut(sec.get("percent", 0), size=60, stroke=8, label=f"{sec.get('percent',0)}%")
            words = f"{sec.get('words',0)} / {sec.get('target',0)}" if sec.get('target') else str(sec.get('words',0))
            sec_rows.append(
                f"<tr><td style='width:84px'>{donut}</td>"
                f"<td>{html_escape(sec.get('section','').replace('_',' ').title())}</td>"
                f"<td>{words}</td>"
                f"<td class='muted'>{html_escape(sec.get('file',''))}</td></tr>"
            )
        # Lifecycle phases per section
        life_blocks = []
        for s in SECTIONS:
            values = get_section_lifecycle(project_root, s)
            items = []
            for p, val in values.items():
                items.append(
                    f"<div style='display:flex;align-items:center;gap:.5rem;margin:.2rem 0;'>"
                    f"{svg_donut(int(val), size=44, stroke=7, label=str(int(val))+'%')}"
                    f"<div class='muted'>{html_escape(p)}</div>"
                    f"</div>"
                )
            life_blocks.append(
                f"<div style='margin:.5rem 0 1rem;'>"
                f"<div><strong>{html_escape(s.replace('_',' ').title())}</strong></div>"
                f"{''.join(items)}"
                f"</div>"
            )
        today = datetime.date.today().isoformat()
        info_lines = []
        for label, val in (
            ("Author", st.get("author")),
            ("Degree", st.get("degree")),
            ("Institution", st.get("institution")),
            ("Supervisor", st.get("supervisor")),
        ):
            if val:
                info_lines.append(f"<div class='muted'>{html_escape(label)}: {html_escape(str(val))}</div>")
        weights = st.get("progress_weights", {"words":70, "lifecycle":30})
        body = f"""
        <section>
          <div class='right' style='margin-bottom:.5rem;'>
            <button class='btn' onclick='window.print()'>Print</button>
          </div>
          <div style='display:flex; align-items:center; gap:1rem;'>
            <div class='donut'>{overall}</div>
            <div>
              <div><strong>{html_escape(st.get('title',''))}</strong></div>
              {''.join(info_lines)}
              <div class='muted'>Report date: {today}</div>
              <div class='muted'>Weights — Words: {int(weights.get('words',70))}%, Lifecycle: {int(weights.get('lifecycle',30))}%</div>
            </div>
          </div>
        </section>
        <section>
          <h3>Sections</h3>
          <table>
            <thead><tr><th>Progress</th><th>Section</th><th>Words</th><th>Path</th></tr></thead>
            <tbody>
              {''.join(sec_rows)}
            </tbody>
          </table>
        </section>
        <section>
          <h3>Lifecycle Phases</h3>
          {''.join(life_blocks)}
        </section>
        """
        return body

    # POST handlers
    def post_init(self, data: Dict[str, str]) -> None:
        title = data.get("title", "").strip()
        author = data.get("author", "").strip()
        supervisor = data.get("supervisor") or None
        degree = data.get("degree") or None
        institution = data.get("institution") or None
        targets_str = data.get("targets", "").strip()
        targets = DEFAULT_SECTION_TARGETS.copy()
        if targets_str:
            for pair in targets_str.split(","):
                if not pair.strip():
                    continue
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    if k.strip() in SECTIONS:
                        try:
                            targets[k.strip()] = int(v)
                        except ValueError:
                            pass
        if not title or not author:
            self.send_error(HTTPStatus.BAD_REQUEST, explain="Title and author required")
            return
        init_project(
            self.root,
            title=title,
            author=author,
            supervisor=supervisor,
            degree=degree,
            institution=institution,
            section_targets=targets,
            overwrite=False,
        )
        self.redirect("/")

    def post_save_section(self, section: str, data: Dict[str, str], project_root: Path | None = None) -> None:
        if section not in SECTIONS:
            self.send_error(HTTPStatus.NOT_FOUND, explain="Unknown section")
            return
        content = data.get("content", "")
        root = project_root or self.root
        tmp_src = root / ".dissertation" / f".{section}.tmp.md"
        tmp_src.parent.mkdir(parents=True, exist_ok=True)
        tmp_src.write_text(content, encoding="utf-8")
        import_section_from_file(root, section, tmp_src)
        try:
            tmp_src.unlink()
        except OSError:
            pass
        self.redirect(self.path)

    def post_lifecycle(self, section: str, data: Dict[str, str], project_root: Path | None = None) -> None:
        if section not in SECTIONS:
            self.send_error(HTTPStatus.NOT_FOUND, explain="Unknown section")
            return
        updates: Dict[str, int] = {}
        # Parse each key as a phase
        for k, v in data.items():
            try:
                updates[k] = int(v)
            except Exception:
                continue
        root = project_root or self.root
        set_section_lifecycle(root, section, updates)
        self.redirect(self.path)

    def post_targets(self, data: Dict[str, str], project_root: Path | None = None) -> None:
        root = project_root or self.root
        cfg = load_config(root)
        new_targets = (cfg.section_targets or {}).copy()
        for s in SECTIONS:
            val = data.get(s, "").strip()
            if val:
                try:
                    new_targets[s] = int(val)
                except ValueError:
                    continue
        cfg.section_targets = new_targets
        # Update weights if provided
        w_words = data.get('weight_words')
        w_life = data.get('weight_lifecycle')
        try:
            ww = int(w_words) if w_words is not None else int((cfg.progress_weights or {}).get('words', 70))
        except Exception:
            ww = int((cfg.progress_weights or {}).get('words', 70))
        try:
            wl = int(w_life) if w_life is not None else int((cfg.progress_weights or {}).get('lifecycle', 30))
        except Exception:
            wl = int((cfg.progress_weights or {}).get('lifecycle', 30))
        cfg.progress_weights = {'words': ww, 'lifecycle': wl}
        save_config(root, cfg)
        self.redirect(self.path)

    # Helpers
    def _html(self, body: str, status: int = 200) -> None:
        page = layout("Dissertation Manager", body, nav_html=self.build_nav())
        data = page.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, location: str, status: int = 303) -> None:
        self.send_response(status)
        self.send_header("Location", location)
        self.end_headers()


def serve(project_root: str | Path = ".", host: str = "127.0.0.1", port: int = 8000, data_root: str | Path | None = None) -> Tuple[str, int]:
    server_address = (host, port)
    httpd = HTTPServer(server_address, Handler)
    if project_root is not None:
        httpd.project_root = str(Path(project_root).resolve())  # type: ignore[attr-defined]
    if data_root is not None:
        httpd.advisor_root = str(Path(data_root).resolve())  # type: ignore[attr-defined]
    httpd.serve_forever()
    return host, port


def serve_advisor(advisor_root: str | Path, host: str = "127.0.0.1", port: int = 8000) -> Tuple[str, int]:
    server_address = (host, port)
    httpd = HTTPServer(server_address, Handler)
    httpd.advisor_root = str(Path(advisor_root).resolve())  # type: ignore[attr-defined]
    httpd.serve_forever()
    return host, port


def svg_donut(percent: int, *, size: int = 80, stroke: int = 10, label: str | None = None) -> str:
    p = max(0, min(100, int(percent or 0)))
    r = (size - stroke) / 2
    c = 2 * 3.141592653589793 * r
    dash = c * (p / 100.0)
    gap = c - dash
    # SVG rotated -90deg so progress starts at 12 o'clock
    svg = f"""
    <div class='donut' style='width:{size}px;height:{size}px;'>
      <svg width='{size}' height='{size}' viewBox='0 0 {size} {size}'>
        <g transform='rotate(-90 {size/2} {size/2})'>
          <circle cx='{size/2}' cy='{size/2}' r='{r}' fill='none' stroke='#eee' stroke-width='{stroke}' />
          <circle cx='{size/2}' cy='{size/2}' r='{r}' fill='none' stroke='url(#grad)' stroke-width='{stroke}'
                  stroke-linecap='round' stroke-dasharray='{dash} {gap}' />
        </g>
        <defs>
          <linearGradient id='grad' x1='0%' y1='0%' x2='100%' y2='0%'>
            <stop offset='0%' stop-color='#0b6' />
            <stop offset='100%' stop-color='#09a' />
          </linearGradient>
        </defs>
      </svg>
      <div class='label'>{html_escape(label if label is not None else str(p) + '%')}</div>
    </div>
    """
    return svg


def main(argv: list[str] | None = None) -> int:  # pragma: no cover
    import argparse, sys

    parser = argparse.ArgumentParser(description="Run the Dissertation Manager web app")
    parser.add_argument("path", nargs="?", default=".", help="Project directory (default: .)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    print(f"Serving on http://{args.host}:{args.port} (Ctrl+C to stop)")
    serve(args.path, args.host, args.port)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
