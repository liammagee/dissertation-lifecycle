from __future__ import annotations

from django.core.management.base import BaseCommand

from tracker.models import MilestoneTemplate, TaskTemplate


MILESTONES = [
    {
        "key": "core-literature-review-general",
        "name": "Literature Review - General Field",
        "is_phd_only": False,
        "tasks": [
            {"title": "Plan Literature Review (General)", "tips": "Define scope and inclusion criteria. Map key themes, theories, and landmark works. Draft a structured outline by themes or debates."},
            {"title": "Draft Literature Review (General)", "tips": "Synthesize (don’t summarize). Group sources by theme, contrast viewpoints, and identify gaps tied to your research questions. Cite consistently."},
            {"title": "Revise Literature Review (General)", "tips": "Tighten argument and flow. Ensure each subsection supports your questions. Check transitions and remove redundancy; verify citations."},
        ],
    },
    {
        "key": "core-literature-review-special",
        "name": "Literature Review - Special Field",
        "is_phd_only": False,
        "tasks": [
            {"title": "Plan Literature Review (Special)", "tips": "Narrow to your specific sub‑field. Select search terms/databases and define what evidence you will weigh most."},
            {"title": "Draft Literature Review (Special)", "tips": "Build a scholarly argument that motivates your study. Compare/contrast findings and methods; justify your angle."},
            {"title": "Revise Literature Review (Special)", "tips": "Strengthen the narrative and critical stance. Check coverage and ensure clear link to methodology and questions."},
        ],
    },
    {
        "key": "core-introduction",
        "name": "Introduction",
        "is_phd_only": False,
        "tasks": [
            {"title": "Plan Introduction", "tips": "Outline problem context, significance, and research questions. Add a roadmap of chapters."},
            {"title": "Draft Introduction", "tips": "Hook the reader; present problem, purpose, and RQs. Include brief rationale and scope; preview structure."},
            {"title": "Revise Introduction", "tips": "Align with current chapters; refine claims and scope; ensure terms and contributions are clear."},
        ],
    },
    {
        "key": "core-methodology",
        "name": "Methodology",
        "is_phd_only": False,
        "tasks": [
            {"title": "Design Methodology", "tips": "Select approach; define participants, instruments, procedures, ethics, and analysis plan. Justify choices with literature."},
            {"title": "Draft Methodology", "tips": "Write detailed subsections (context, sampling, data collection, validity, analysis). Include timelines and limitations."},
            {"title": "Review Methodology", "tips": "Check feasibility, alignment with RQs, and replication clarity. Verify consent/storage procedures."},
        ],
    },
    {
        "key": "core-irb-application",
        "name": "Internal Review Board Application",
        "is_phd_only": False,
        "tasks": [
            {"title": "Prepare IRB Materials", "tips": "Draft protocol, consent forms, recruitment text, and instruments. Plan anonymization and secure storage."},
            {"title": "Submit IRB Application", "tips": "Confirm required attachments and CITI/training. Build in review timelines (2–6 weeks)."},
            {"title": "Address IRB Feedback", "tips": "Respond to conditions. Update materials and resubmit promptly; document changes in protocol versioning."},
        ],
    },
    {
        "key": "core-preliminary-exam",
        "name": "Preliminary Exam",
        "is_phd_only": False,
        "tasks": [
            {"title": "Prepare Preliminary Exam Materials", "tips": "Assemble required chapters and a 10–12 slide deck (problem, method, expected contributions)."},
            {"title": "Present Preliminary Exam", "tips": "Rehearse timing; anticipate questions on method and feasibility. Keep slides clean and legible."},
            {"title": "Revise Based on Exam Feedback", "tips": "Capture committee notes; triage into must/should/could. Update chapters and plan next steps."},
        ],
    },
    {
        "key": "core-findings",
        "name": "Findings",
        "is_phd_only": False,
        "tasks": [
            {"title": "Analyze Data", "tips": "Execute analysis plan; maintain a clear audit trail (code/notes). Validate with checks or triangulation."},
            {"title": "Draft Findings", "tips": "Organize by themes or research questions. Present evidence concisely with tables/figures as needed."},
            {"title": "Revise Findings", "tips": "Clarify claims vs. evidence; improve visuals; ensure findings answer RQs and set up discussion."},
        ],
    },
    {
        "key": "core-conclusion",
        "name": "Conclusion",
        "is_phd_only": False,
        "tasks": [
            {"title": "Plan Conclusion", "tips": "Outline implications, recommendations, limitations, and future work. Revisit contributions."},
            {"title": "Draft Conclusion", "tips": "Synthesize key findings; articulate implications and practical recommendations."},
            {"title": "Revise Conclusion", "tips": "Tighten prose; ensure claims are supported; align recommendations with evidence."},
        ],
    },
    {
        "key": "core-final-defence",
        "name": "Final Defence",
        "is_phd_only": False,
        "tasks": [
            {"title": "Prepare Defence Materials", "tips": "Finalize manuscript formatting; prepare 15–20 slide deck; confirm deadlines and submission steps."},
            {"title": "Defend Dissertation", "tips": "Schedule committee and room/tech. Rehearse; plan backup slides for methods and limitations."},
            {"title": "Submit Final Revisions", "tips": "Implement committee changes; update references/formatting; deposit per institutional guidelines."},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed milestone and task templates from the dissertation outline"

    def handle(self, *args, **options):
        created_ms = 0
        created_tasks = 0
        order = 1
        for m in MILESTONES:
            mt, ms_created = MilestoneTemplate.objects.get_or_create(
                key=m["key"],
                defaults={
                    "name": m["name"],
                    "description": "",
                    "order": order,
                    "is_phd_only": m["is_phd_only"],
                },
            )
            if not ms_created:
                # Update name/flags/order to latest
                mt.name = m["name"]
                mt.is_phd_only = m["is_phd_only"]
                mt.order = order
                mt.save()
            else:
                created_ms += 1
            order += 1

            # Clear existing tasks, then create default seed tasks (3 per milestone)
            TaskTemplate.objects.filter(milestone=mt).delete()
            t_order = 1
            for item in m["tasks"]:
                if isinstance(item, dict):
                    title = item.get("title", "").strip()
                    tips = item.get("tips", "").strip()
                    url = item.get("url", "").strip() if item.get("url") else ""
                else:
                    title = str(item)
                    tips = ""
                    url = ""
                tt = TaskTemplate.objects.create(
                    milestone=mt,
                    key=f"t{t_order}",
                    title=title,
                    description="",
                    order=t_order,
                    guidance_tips=tips,
                    guidance_url=url,
                )
                created_tasks += 1
                t_order += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded milestones (new: {created_ms}) and tasks (total: {created_tasks})."
        ))
