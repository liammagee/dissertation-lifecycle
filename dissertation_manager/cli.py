from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict

from . import SECTIONS
from .core import (
    DEFAULT_SECTION_TARGETS,
    export_markdown,
    get_status,
    import_section_from_file,
    init_project,
    load_config,
    save_config,
)
from .web import serve as serve_web, serve_advisor as serve_web_advisor


def parse_section_targets(value: str) -> Dict[str, int]:
    # Format: "introduction=1500,literature_review=4000,..."
    targets: Dict[str, int] = {}
    if not value:
        return targets
    for pair in value.split(","):
        if not pair.strip():
            continue
        if "=" not in pair:
            raise argparse.ArgumentTypeError(
                f"Invalid target '{pair}'. Use section=number,comma-separated."
            )
        k, v = pair.split("=", 1)
        k = k.strip()
        if k not in SECTIONS:
            raise argparse.ArgumentTypeError(
                f"Unknown section '{k}'. Valid: {', '.join(SECTIONS)}"
            )
        try:
            targets[k] = int(v)
        except ValueError as e:
            raise argparse.ArgumentTypeError(f"Invalid number for '{k}': {v}") from e
    return targets


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    targets = DEFAULT_SECTION_TARGETS.copy()
    if args.targets:
        targets.update(parse_section_targets(args.targets))
    init_project(
        root,
        title=args.title,
        author=args.author,
        supervisor=args.supervisor,
        degree=args.degree,
        institution=args.institution,
        section_targets=targets,
        overwrite=args.overwrite,
    )
    print(f"Initialized dissertation project at {root}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    st = get_status(root)
    print(f"Project: {st['title']} ({st['author']})\nRoot: {st['project_root']}")
    if st.get("degree") or st.get("institution"):
        extra = []
        if st.get("degree"):
            extra.append(f"Degree: {st['degree']}")
        if st.get("institution"):
            extra.append(f"Institution: {st['institution']}")
        print(" | ".join(extra))
    if st.get("supervisor"):
        print(f"Supervisor: {st['supervisor']}")
    print()
    print("Sections:")
    for sec in st["sections"]:
        mark = "✓" if sec["exists"] else "✗"
        tgt = f"/{sec['target']}" if sec["target"] else ""
        print(f"  {mark} {sec['section']:<18} {sec['words']:>5}{tgt} words  -> {sec['file']}")
    if st["total_target"]:
        print(
            f"\nTotal: {st['total_words']} / {st['total_target']} words ({round((st['total_words']/st['total_target'])*100,1)}%)"
        )
    else:
        print(f"\nTotal: {st['total_words']} words")
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    import_section_from_file(root, args.section, Path(args.file))
    print(f"Updated section '{args.section}' from {args.file}")
    return 0


def cmd_targets(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    cfg = load_config(root)
    # Update targets if provided
    if args.targets:
        new_targets = cfg.section_targets.copy() if cfg.section_targets else {}
        new_targets.update(parse_section_targets(args.targets))
        cfg.section_targets = new_targets
        save_config(root, cfg)
        print("Updated section targets.")
    # Print current targets
    print("Section targets:")
    for s in SECTIONS:
        val = (cfg.section_targets or {}).get(s, 0)
        print(f"  {s:<18} {val:>5}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    out = Path(args.out).resolve() if args.out else (root / "exports" / "dissertation.md")
    p = export_markdown(root, out)
    print(f"Exported to {p}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dissertation",
        description="Manage a dissertation project: sections, targets, and exports.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # init
    sp = sub.add_parser("init", help="Initialize a new dissertation project")
    sp.add_argument("path", nargs="?", default=".", help="Project directory (default: .)")
    sp.add_argument("--title", required=True)
    sp.add_argument("--author", required=True)
    sp.add_argument("--supervisor")
    sp.add_argument("--degree")
    sp.add_argument("--institution")
    sp.add_argument(
        "--targets",
        help="Section targets as 'section=words,section=words'",
    )
    sp.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    sp.set_defaults(func=cmd_init)

    # status
    sp = sub.add_parser("status", help="Show progress and file paths")
    sp.add_argument("path", nargs="?", default=".")
    sp.set_defaults(func=cmd_status)

    # set/import
    sp = sub.add_parser("set", help="Import/replace a section from a file")
    sp.add_argument("section", choices=SECTIONS)
    sp.add_argument("file", help="Path to source Markdown file")
    sp.add_argument("path", nargs="?", default=".", help="Project directory")
    sp.set_defaults(func=cmd_set)

    # targets
    sp = sub.add_parser("targets", help="Show or update section word targets")
    sp.add_argument("path", nargs="?", default=".")
    sp.add_argument("--targets", help="Update targets 'section=words,section=words'")
    sp.set_defaults(func=cmd_targets)

    # export
    sp = sub.add_parser("export", help="Export combined Markdown document")
    sp.add_argument("path", nargs="?", default=".")
    sp.add_argument("--out", help="Output Markdown file path")
    sp.set_defaults(func=cmd_export)

    # web
    def cmd_web(args: argparse.Namespace) -> int:
        host = args.host
        port = args.port
        print(f"Serving on http://{host}:{port} (Ctrl+C to stop)")
        try:
            # Consolidated mode if --data-root is provided
            data_root = getattr(args, "data_root", None)
            serve_web(args.path, host, port, data_root=data_root)
        except KeyboardInterrupt:
            print("\nStopped.")
        return 0

    sp = sub.add_parser("web", help="Run the web app")
    sp.add_argument("path", nargs="?", default=".", help="Single project directory (default: .)")
    sp.add_argument("--data-root", help="Enable consolidated mode; folder containing all student projects")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8000)
    sp.set_defaults(func=cmd_web)

    # web-advisor
    def cmd_web_advisor(args: argparse.Namespace) -> int:
        host = args.host
        port = args.port
        print(f"Advisor server on http://{host}:{port} (Ctrl+C to stop)")
        try:
            serve_web_advisor(args.path, host, port)
        except KeyboardInterrupt:
            print("\nStopped.")
        return 0

    sp = sub.add_parser("web-advisor", help="Run advisor dashboard for multiple students")
    sp.add_argument("path", nargs="?", default=".", help="Folder containing student projects")
    sp.add_argument("--host", default="127.0.0.1")
    sp.add_argument("--port", type=int, default=8000)
    sp.set_defaults(func=cmd_web_advisor)

    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
