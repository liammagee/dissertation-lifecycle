from __future__ import annotations

from django.core.management.base import BaseCommand

from tracker.models import MilestoneTemplate, TaskTemplate


MILESTONES = [
    {
        "key": "getting-started",
        "name": "Getting Started – Topic Approval",
        "is_phd_only": False,
        "tasks": [
            "Topic",
            "Tentative research question(s)",
            "Tentative outline",
            "Significance and your connection to the topic",
            "Present in Dissertation Session for permission/advice",
        ],
    },
    {
        "key": "reference-db",
        "name": "Starting Reference Database",
        "is_phd_only": False,
        "tasks": [
            "Choose an organization strategy – Mendeley, Zotero, Endnote, etc.",
            "Create a dedicated folder for PDFs",
            "Manage citation data",
        ],
    },
    {
        "key": "chapter2-general",
        "name": "Chapter 2 – General Field Literature Review",
        "is_phd_only": False,
        "tasks": [
            "Examine literature around your topic",
            "Download Dissertation Template; explore formatting",
            "Write Lit Review Introduction – Roadmap/foreshadowing",
            "Start General Field writing (synthesize field)",
            "Definitions (key vocabulary)",
            "Theoretical Framework of topic",
            "Organize thematically: concepts, debates, trends",
            "Provide gaps in literature",
            "Conclusion",
            "Goal – 5000–6000 words",
            "References",
            "Submit for peer review",
            "Revise as needed",
            "Submit for Coordinator review",
            "Revise as needed",
            "Submit for Advisor review",
            "Revise as needed",
            "After permission, submit exam application",
            "General Exam – Passed!",
        ],
    },
    {
        "key": "chapter2-special",
        "name": "Special Field Literature Review",
        "is_phd_only": False,
        "tasks": [
            "Use gaps to determine Special Field direction",
            "Form new tentative question(s) and outline",
            "Appointment with Advisor to discuss Special Field",
            "Examine literature around your Special Field",
            "Write Special Lit Review Introduction",
            "Start Special Field writing (scholarly argument)",
            "Organize thematically: concepts, debates, trends",
            "Include supportive/parallel studies",
            "Provide gaps in literature",
            "Conclusion",
            "Goal – 4000–5000 words",
            "References",
            "Submit for peer review",
            "Revise as needed",
            "Submit for Coordinator review",
            "Revise as needed",
            "Submit for Advisor review",
            "Revise as needed",
            "After permission, submit exam application",
            "Special Exam – Passed!",
        ],
    },
    {
        "key": "chapter3-methodology",
        "name": "Chapter 3 – Methodology",
        "is_phd_only": False,
        "tasks": [
            "Review and choose potential methodology type",
            "Create Logic Model",
            "Present in session for ideas/approval; meet advisor",
            "Begin writing Chapter 3 Methodology",
            "Introduction",
            "Key Research Question(s)",
            "Theoretical Applications/Framework",
            "Theoretical Model (if needed)",
            "Methodology Selection & Defense",
            "Methodological Framework (if combined, how/why)",
            "Methods strengths and weaknesses",
            "Study overview: context, participants",
            "Logic Model",
            "Researcher role",
            "Data sources",
            "Recruitment",
            "Data collection procedures",
            "Ethical considerations (storage & disposal)",
            "Validity (triangulation if needed)",
            "Implementation plan",
            "Data analysis (methods, software)",
            "Methods conclusion",
            "Create instruments (consent, surveys, etc.)",
            "IRB completion & submission",
            "IRB approval",
            "Appendix: compile instruments and IRB",
            "Submit for Peer Review",
            "Revise if needed",
            "Submit for Coordinator Review",
            "Revise if needed",
            "Submit for Advisor Review",
            "Revise if needed",
            "Prelim Prep - Ch1 Introduction",
            "Prelim Prep - Ch1 Background",
            "Prelim Prep - Ch1 Problem Statement",
            "Prelim Prep - Ch1 Research Questions",
            "Prelim Prep - Ch1 Potential Contribution",
            "Prelim Prep - Ch2 Combine General & Special",
            "Combine References",
            "Copy editor (if needed)",
            "Prelim Exam – Slide Deck",
            "Submit manuscript & deck to Coordinator",
            "Prelim Exam scheduling",
            "Prelim Exam – Passed!",
            "Revise if needed",
        ],
    },
    {
        "key": "chapter4-results",
        "name": "Chapter 4 – Results",
        "is_phd_only": False,
        "tasks": [
            "Conduct research according to Chapter 3 plan",
            "Data collection",
            "Assess effectiveness of plan; update if needed",
            "Review manuscript; determine results direction",
            "Brief recap of study’s methodology",
            "Implementation and research site context",
            "Present participants (table if useful)",
            "Present results grouped by theme; triangulate",
            "Use visual representations",
            "Submit manuscript to Coordinator",
            "Revise if needed",
            "Submit manuscript to Advisor",
            "Revise if needed",
        ],
    },
    {
        "key": "chapter5-conclusion",
        "name": "Chapter 5 – Implications, Recommendations, and Conclusion",
        "is_phd_only": False,
        "tasks": [
            "Brief recap of the study’s findings",
            "Implications of findings",
            "Recommendations supported by findings",
            "Study limitations",
            "Suggestions for future research",
            "Conclusions",
            "Re-read manuscript; check for flow",
            "Check references and formatting",
            "Copy edit",
            "Submit to Coordinator for run-through",
            "Revise if needed",
            "Submit to Advisor",
            "Revise until approval to deposit",
            "Contact Coordinator for final steps",
        ],
    },
    {
        "key": "erp-phd",
        "name": "ERP PhD Track",
        "is_phd_only": True,
        "tasks": [
            "One-pager: background, methodology, data sources, timeline",
            "Research proposal (Intro, >=2000w Lit Review, Theory & Methodology design)",
            "Obtain IRB approval",
            "Arrange meeting for approval (coordinator)",
            "ERP proposal oral presentation (15min)",
            "Conduct research study and analyze data",
            "Write up results",
            "Present findings (15min)",
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

            # Clear existing tasks (keep idempotent but simple)
            TaskTemplate.objects.filter(milestone=mt).delete()
            t_order = 1
            for title in m["tasks"]:
                TaskTemplate.objects.create(
                    milestone=mt,
                    key=f"t{t_order}",
                    title=title,
                    description="",
                    order=t_order,
                )
                created_tasks += 1
                t_order += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seeded milestones (new: {created_ms}) and tasks (total: {created_tasks})."
        ))

