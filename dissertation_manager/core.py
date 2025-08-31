from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from . import SECTIONS


# Project layout constants
CONFIG_DIRNAME = ".dissertation"
CONFIG_FILENAME = "config.json"
SECTIONS_DIRNAME = "sections"
NOTES_DIRNAME = "notes"
EXPORTS_DIRNAME = "exports"


DEFAULT_SECTION_TEMPLATES: Dict[str, str] = {
    "introduction": """# Introduction\n\n- Context: Set the scene and research problem.\n- Rationale: Why this topic matters.\n- Aim & Objectives: What you will achieve.\n- Scope: What is and isn’t covered.\n- Structure: Brief overview of chapters.\n\n""",
    "literature_review": """# Literature Review\n\n- Key themes and frameworks in the field.\n- Seminal works and recent advances.\n- Gaps, tensions, and debates.\n- Theoretical lens you adopt.\n- Synthesis leading to research questions/hypotheses.\n\n""",
    "methodology": """# Methodology\n\n- Research design and justification.\n- Data sources and sampling.\n- Instruments/measures and procedures.\n- Analysis methods.\n- Ethics and limitations.\n\n""",
    "findings": """# Findings\n\n- Report results aligned to objectives.\n- Tables/figures summaries.\n- Patterns, anomalies, robustness checks.\n- Brief interpretation (leave deep interpretation for Discussion).\n\n""",
    "conclusion": """# Conclusion\n\n- Summarize contributions and key insights.\n- Answer the research questions.\n- Implications (theory, practice, policy).\n- Limitations and future work.\n\n""",
}


DEFAULT_SECTION_TARGETS: Dict[str, int] = {
    "introduction": 1500,
    "literature_review": 4000,
    "methodology": 2500,
    "findings": 2500,
    "conclusion": 1500,
}

# Default lifecycle phases tracked within each section
LIFECYCLE_PHASES: List[str] = [
    "Plan",
    "Collect",
    "Synthesize",
    "Draft",
    "Revise",
    "Finalize",
]


@dataclass
class ProjectConfig:
    title: str
    author: str
    supervisor: Optional[str] = None
    degree: Optional[str] = None
    institution: Optional[str] = None
    section_targets: Dict[str, int] = None
    lifecycle_phases: List[str] = None
    lifecycle_progress: Dict[str, Dict[str, int]] = None  # section -> phase -> percent (0-100)
    progress_weights: Dict[str, int] = None  # {"words": 70, "lifecycle": 30}

    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "author": self.author,
            "supervisor": self.supervisor,
            "degree": self.degree,
            "institution": self.institution,
            "section_targets": self.section_targets or DEFAULT_SECTION_TARGETS,
            "lifecycle_phases": self.lifecycle_phases or LIFECYCLE_PHASES,
            "lifecycle_progress": self.lifecycle_progress or {},
            "progress_weights": self.progress_weights or {"words": 70, "lifecycle": 30},
        }

    @staticmethod
    def from_dict(d: Dict) -> "ProjectConfig":
        return ProjectConfig(
            title=d.get("title", "Untitled Dissertation"),
            author=d.get("author", "Unknown"),
            supervisor=d.get("supervisor"),
            degree=d.get("degree"),
            institution=d.get("institution"),
            section_targets=d.get("section_targets", DEFAULT_SECTION_TARGETS.copy()),
            lifecycle_phases=d.get("lifecycle_phases", LIFECYCLE_PHASES.copy()),
            lifecycle_progress=d.get("lifecycle_progress", {}),
            progress_weights=d.get("progress_weights", {"words": 70, "lifecycle": 30}),
        )


def _project_paths(root: Path) -> Dict[str, Path]:
    cfg_dir = root / CONFIG_DIRNAME
    cfg = cfg_dir / CONFIG_FILENAME
    sections_dir = root / SECTIONS_DIRNAME
    notes_dir = root / NOTES_DIRNAME
    exports_dir = root / EXPORTS_DIRNAME
    return {
        "root": root,
        "config_dir": cfg_dir,
        "config": cfg,
        "sections_dir": sections_dir,
        "notes_dir": notes_dir,
        "exports_dir": exports_dir,
    }


def load_config(project_root: Path) -> ProjectConfig:
    paths = _project_paths(project_root)
    if not paths["config"].exists():
        raise FileNotFoundError(
            f"No project found at {project_root}. Run 'init' first."
        )
    data = json.loads(paths["config"].read_text(encoding="utf-8"))
    return ProjectConfig.from_dict(data)


def save_config(project_root: Path, config: ProjectConfig) -> None:
    paths = _project_paths(project_root)
    paths["config_dir"].mkdir(parents=True, exist_ok=True)
    paths["config"].write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")


def init_project(
    project_root: Path,
    *,
    title: str,
    author: str,
    supervisor: Optional[str] = None,
    degree: Optional[str] = None,
    institution: Optional[str] = None,
    section_targets: Optional[Dict[str, int]] = None,
    overwrite: bool = False,
) -> None:
    paths = _project_paths(project_root)
    section_targets = section_targets or DEFAULT_SECTION_TARGETS

    # Create directories
    paths["config_dir"].mkdir(parents=True, exist_ok=True)
    paths["sections_dir"].mkdir(parents=True, exist_ok=True)
    paths["notes_dir"].mkdir(parents=True, exist_ok=True)
    paths["exports_dir"].mkdir(parents=True, exist_ok=True)

    # Write config
    cfg = ProjectConfig(
        title=title,
        author=author,
        supervisor=supervisor,
        degree=degree,
        institution=institution,
        section_targets=section_targets,
    )
    if paths["config"].exists() and not overwrite:
        raise FileExistsError(f"Config already exists at {paths['config']} (use --overwrite)")
    save_config(project_root, cfg)

    # Seed section files if not present
    for section in SECTIONS:
        fp = paths["sections_dir"] / f"{section}.md"
        if overwrite or not fp.exists():
            fp.write_text(DEFAULT_SECTION_TEMPLATES[section], encoding="utf-8")

    # Seed notes/todo
    todo = paths["notes_dir"] / "todo.md"
    if overwrite or not todo.exists():
        todo.write_text(
            """# TODOs\n\n- [ ] Outline scope and aims\n- [ ] Collect key papers\n- [ ] Draft methodology\n""",
            encoding="utf-8",
        )


def section_file(project_root: Path, section: str) -> Path:
    if section not in SECTIONS:
        raise ValueError(f"Unknown section: {section}. Valid: {', '.join(SECTIONS)}")
    return _project_paths(project_root)["sections_dir"] / f"{section}.md"


def import_section_from_file(project_root: Path, section: str, source: Path) -> None:
    dest = section_file(project_root, section)
    dest.write_text(Path(source).read_text(encoding="utf-8"), encoding="utf-8")


def word_count(text: str) -> int:
    # Simple whitespace tokenization
    return len([t for t in text.split() if t.strip()])


def section_lifecycle_percent(cfg: ProjectConfig, section: str) -> int:
    phases = cfg.lifecycle_phases or LIFECYCLE_PHASES
    progress = (cfg.lifecycle_progress or {}).get(section, {})
    if not phases:
        return 0
    vals = [int(progress.get(p, 0)) for p in phases]
    return int(round(sum(vals) / max(1, len(vals))))


def combine_progress(words_percent: int, lifecycle_percent: int, weights: Dict[str, int]) -> int:
    w_words = int(weights.get("words", 70))
    w_life = int(weights.get("lifecycle", 30))
    denom = max(1, w_words + w_life)
    combined = (w_words * words_percent + w_life * lifecycle_percent) / denom
    return int(round(combined))


def get_status(project_root: Path) -> Dict:
    cfg = load_config(project_root)
    paths = _project_paths(project_root)
    sec_dir = paths["sections_dir"]

    stats: List[Dict] = []
    total_words = 0
    total_target = 0
    lifecycle_percents: List[int] = []
    for s in SECTIONS:
        fp = sec_dir / f"{s}.md"
        exists = fp.exists()
        text = fp.read_text(encoding="utf-8") if exists else ""
        wc = word_count(text)
        target = (cfg.section_targets or {}).get(s, 0)
        total_words += wc
        total_target += target
        p_words = 0 if target <= 0 else min(100, round((wc / max(1, target)) * 100))
        p_life = section_lifecycle_percent(cfg, s)
        lifecycle_percents.append(p_life)
        combined = combine_progress(p_words, p_life, cfg.progress_weights or {"words": 70, "lifecycle": 30})
        stats.append(
            {
                "section": s,
                "file": str(fp),
                "exists": exists,
                "words": wc,
                "target": target,
                "percent_words": p_words,
                "percent_lifecycle": p_life,
                "percent": combined,
            }
        )

    overall_words_percent = 0 if total_target <= 0 else min(100, round((total_words / max(1, total_target)) * 100))
    overall_lifecycle_percent = int(round(sum(lifecycle_percents) / max(1, len(lifecycle_percents))))
    overall_combined = combine_progress(
        overall_words_percent,
        overall_lifecycle_percent,
        cfg.progress_weights or {"words": 70, "lifecycle": 30},
    )

    return {
        "title": cfg.title,
        "author": cfg.author,
        "supervisor": cfg.supervisor,
        "degree": cfg.degree,
        "institution": cfg.institution,
        "sections": stats,
        "total_words": total_words,
        "total_target": total_target,
        "percent_total_words": overall_words_percent,
        "percent_total_lifecycle": overall_lifecycle_percent,
        "percent_total": overall_combined,
        "project_root": str(project_root),
        "progress_weights": cfg.progress_weights or {"words": 70, "lifecycle": 30},
    }


def get_section_lifecycle(project_root: Path, section: str) -> Dict[str, int]:
    cfg = load_config(project_root)
    if section not in SECTIONS:
        raise ValueError(f"Unknown section: {section}")
    phases = cfg.lifecycle_phases or LIFECYCLE_PHASES
    progress = (cfg.lifecycle_progress or {}).get(section, {})
    # Ensure all phases present
    return {p: int(progress.get(p, 0)) for p in phases}


def set_section_lifecycle(project_root: Path, section: str, updates: Dict[str, int]) -> None:
    cfg = load_config(project_root)
    if section not in SECTIONS:
        raise ValueError(f"Unknown section: {section}")
    if cfg.lifecycle_progress is None:
        cfg.lifecycle_progress = {}
    cur = cfg.lifecycle_progress.get(section, {})
    for k, v in updates.items():
        try:
            iv = int(v)
        except Exception:
            continue
        iv = max(0, min(100, iv))
        cur[k] = iv
    cfg.lifecycle_progress[section] = cur
    save_config(project_root, cfg)


def export_markdown(project_root: Path, out_file: Path) -> Path:
    cfg = load_config(project_root)
    parts: List[str] = []
    # Title page
    parts.append(f"# {cfg.title}\n\n")
    subtitle = []
    subtitle.append(f"Author: {cfg.author}")
    if cfg.degree:
        subtitle.append(f"Degree: {cfg.degree}")
    if cfg.institution:
        subtitle.append(f"Institution: {cfg.institution}")
    if cfg.supervisor:
        subtitle.append(f"Supervisor: {cfg.supervisor}")
    if subtitle:
        parts.append("\n".join(subtitle) + "\n\n---\n\n")

    # Sections
    for s in SECTIONS:
        fp = section_file(project_root, s)
        if fp.exists():
            # Ensure each section starts with a level-1 heading
            text = fp.read_text(encoding="utf-8")
            if not text.lstrip().startswith("# "):
                heading = s.replace("_", " ").title()
                parts.append(f"# {heading}\n\n")
            parts.append(text.rstrip() + "\n\n")

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("".join(parts), encoding="utf-8")
    return out_file
