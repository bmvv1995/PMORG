import os

from odoo.modules.module import get_manifest
from odoo.tests.common import TransactionCase

PMORG_MODELS = (
    "pmorg.identity",
    "pmorg.initiative",
    "pmorg.success.criterion",
    "pmorg.anchor",
    "pmorg.task.run",
    "pmorg.task.event",
    "pmorg.outbox.event",
    "pmorg.command.inbox",
    "project.task",
)

FORBIDDEN_PREFIXES = ("hr.", "stock.")

PROFILE_PATHS = (
    "/mnt/evaluation/profiles/org-min.yaml",
    os.path.join(
        os.path.dirname(__file__), "..", "..", "..",
        "evaluation", "profiles", "org-min.yaml",
    ),
)


class TestStructure(TransactionCase):
    """Testele structurale ADR-013: nucleu agnostic de domeniu."""

    def test_manifest_depends_only_base_and_project(self):
        deps = set(get_manifest("pmorg_core")["depends"])
        self.assertEqual(deps, {"base", "project"})

    def test_no_references_to_optional_models(self):
        for model_name in PMORG_MODELS:
            model = self.env[model_name]
            for fname, field in model._fields.items():
                if getattr(field, "_module", None) != "pmorg_core":
                    continue
                comodel = getattr(field, "comodel_name", None)
                if not comodel:
                    continue
                self.assertFalse(
                    comodel.startswith(FORBIDDEN_PREFIXES),
                    f"{model_name}.{fname} referă modelul opțional {comodel}",
                )

    def test_org_min_profile_manifest(self):
        path = next((p for p in PROFILE_PATHS if os.path.exists(p)), None)
        if not path:
            self.skipTest("org-min.yaml nu este accesibil în acest mediu.")
        with open(path, encoding="utf-8") as handle:
            content = handle.read()
        self.assertIn("profile_id: org-min", content)
        self.assertIn(
            "odoo_revision: 1b8f6802832cfa4d146193a912af1f4445d09f0a", content
        )
        self.assertIn("- base", content)
        self.assertIn("- project", content)
        self.assertIn("anchor_packs: []", content)
        for forbidden in ("hr", "stock"):
            self.assertNotIn(f"- {forbidden}\n", content.split("forbidden_modules")[0])
