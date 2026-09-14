#!/usr/bin/env python3
"""Tests du classifieur Gmail (stdlib uniquement, aucun secret)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from classer import classify, load_rules, should_alert


class ClasserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = load_rules()
        cls.rules["self_domain"] = "example.com"
        cls.rules["aliases"] = ["moi@example.com"]

    def decide(self, from_addr: str, subject: str, snippet: str = ""):
        return classify(from_addr, subject, snippet, self.rules)

    def test_langsmith_humain_alerte_et_reste_inbox(self) -> None:
        d = self.decide(
            "amada@langchain.dev",
            "Re: Your LangSmith Credits",
            "Which link did you use?",
        )
        self.assertEqual(d.rule_id, "langchain-humain")
        self.assertFalse(d.archive)
        self.assertTrue(should_alert(d))
        self.assertIn("Label_42", d.label_ids)
        self.assertIn("Label_55", d.label_ids)

    def test_langsmith_auto_archive_sans_alerte(self) -> None:
        d = self.decide(
            "noreply+automations@airtableemail.com",
            "Your LangSmith Credits",
        )
        self.assertEqual(d.rule_id, "langsmith-auto")
        self.assertTrue(d.archive)
        self.assertFalse(should_alert(d))

    def test_alex_ooo_jamais_alerte(self) -> None:
        d = self.decide(
            "alex@protectedseas.net",
            "Out of Office Re: Request for REST API Key",
            "returning Oct. 5",
        )
        self.assertEqual(d.rule_id, "protectedseas-ooo")
        self.assertTrue(d.archive)
        self.assertFalse(should_alert(d))

    def test_protectedseas_humain_alerte(self) -> None:
        d = self.decide(
            "alex@protectedseas.net",
            "Re: Request for REST API Key / Production Access",
            "the API V2 is public",
        )
        self.assertEqual(d.rule_id, "protectedseas-humain")
        self.assertTrue(should_alert(d))

    def test_dileep_equipe_alerte_inbox(self) -> None:
        d = self.decide(
            "dileepchoudhary1008@gmail.com",
            "Re: Dileep",
            "Acknowledged sir",
        )
        self.assertEqual(d.rule_id, "equipe-dileep")
        self.assertFalse(d.archive)
        self.assertTrue(should_alert(d))
        self.assertIn("Label_26", d.label_ids)

    def test_github_pr_archive(self) -> None:
        d = self.decide(
            "notifications@github.com",
            "Re: [NAVIGUIDE-for-Berry-Mappemonde/Blue-Intelligence-Map] feat(climatology) (PR #130)",
        )
        self.assertEqual(d.rule_id, "github-pr")
        self.assertTrue(d.archive)
        self.assertFalse(should_alert(d))
        self.assertIn("Label_46", d.label_ids)

    def test_github_pat_alerte(self) -> None:
        d = self.decide(
            "noreply@github.com",
            "[GitHub] A personal access token (classic) has been added to your account",
        )
        self.assertEqual(d.rule_id, "github-pat")
        self.assertFalse(d.archive)
        self.assertTrue(should_alert(d))
        self.assertIn("Label_43", d.label_ids)
        self.assertIn("Label_48", d.label_ids)

    def test_github_invitation_alerte(self) -> None:
        d = self.decide(
            "notifications@github.com",
            "dileep53matrix invited you to dileep53matrix/naviguid-backend",
        )
        self.assertEqual(d.rule_id, "github-invitation")
        self.assertFalse(d.archive)
        self.assertTrue(should_alert(d))

    def test_paymentlabs_paiement_alerte(self) -> None:
        d = self.decide(
            "support@paymentlabs.io",
            "HackerEarth - Your payment for TinyFish Pre-Accelerator Hackathon",
            "A payment of $25.00 was sent",
        )
        self.assertEqual(d.rule_id, "paymentlabs-paiement")
        self.assertTrue(should_alert(d))
        self.assertFalse(d.archive)

    def test_paymentlabs_2fa_archive(self) -> None:
        d = self.decide("support@paymentlabs.io", "Two-Factor Code: 323249")
        self.assertEqual(d.rule_id, "paymentlabs-codes")
        self.assertTrue(d.archive)
        self.assertFalse(should_alert(d))

    def test_api_data_gov_alerte(self) -> None:
        d = self.decide("noreply@api.data.gov", "Your API key")
        self.assertEqual(d.rule_id, "api-data-gov")
        self.assertTrue(should_alert(d))

    def test_earthdata_reset_alerte(self) -> None:
        d = self.decide("noreply@nasa.gov", "Earthdata Login Password Reset")
        self.assertEqual(d.rule_id, "earthdata-reset")
        self.assertTrue(should_alert(d))

    def test_qonto_marketing_archive(self) -> None:
        d = self.decide("hello@qonto.com", "Protégez votre compte au maximum face à la fraude")
        self.assertEqual(d.rule_id, "qonto-marketing")
        self.assertTrue(d.archive)

    def test_schoolmaker_archive(self) -> None:
        d = self.decide(
            "noreply@schoolmaker.co",
            "“Je ne sais pas faire l'exercice ” - Nouveau post de Paty KTR",
        )
        self.assertEqual(d.rule_id, "schoolmaker")
        self.assertTrue(d.archive)

    def test_cloudflare_routine_archive(self) -> None:
        d = self.decide(
            "noreply@notify.cloudflare.com",
            "[Confirmation] example.com is active (Free plan)",
        )
        self.assertEqual(d.rule_id, "cloudflare-info")
        self.assertTrue(d.archive)

    def test_nebius_support_alerte(self) -> None:
        d = self.decide(
            "ai-studio-support@nebius.com",
            "AISTUDIOSUP-1752 Inquiry regarding $25 Token Factory credits",
        )
        self.assertEqual(d.rule_id, "nebius-support")
        self.assertTrue(should_alert(d))

    def test_bounce_alerte(self) -> None:
        d = self.decide(
            "mailer-daemon@googlemail.com",
            "Delivery Status Notification (Failure)",
        )
        self.assertEqual(d.rule_id, "bounce")
        self.assertTrue(should_alert(d))

    def test_self_jamais_alerte(self) -> None:
        d = self.decide(
            "moi@example.com",
            "Blue Intelligence + NAVIGUIDE — docs pack (EN) shared with you",
        )
        self.assertTrue(d.from_self)
        self.assertFalse(should_alert(d))

    def test_inconnue_reste_inbox_sans_alerte(self) -> None:
        d = self.decide("quelquun@example.org", "Proposition de partenariat")
        self.assertTrue(d.unmatched)
        self.assertFalse(d.archive)
        self.assertFalse(should_alert(d))

    def test_label_ids_stables(self) -> None:
        self.assertEqual(self.rules["labels"]["Pertinence/À répondre"], "Label_42")
        self.assertEqual(self.rules["labels"]["Pertinence/Action requise"], "Label_43")
        self.assertEqual(self.rules["labels"]["Correspondants/GitHub"], "Label_10")


if __name__ == "__main__":
    unittest.main()
