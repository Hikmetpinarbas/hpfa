from __future__ import annotations

"""Content-based TEAM admission bridge for the CSV surface CLI.

This adapts the already-existing content-source-role structural rule without
promoting filenames, provider labels, or embedded prefixes to validated team
identity. It only allows the CSV reader to treat the provider's documented
no-direct-team-column TEAM surface as a TEAM surface candidate when the
existing exact `code = <prefix> - <action>` evidence is present.
"""

from typing import Any


def install_content_team_binding(reader_module: Any) -> None:
    if getattr(reader_module, "_hpfa_content_team_binding_installed", False):
        return

    original = reader_module.team_binding_audit
    team_surface_role = reader_module.TEAM_SURFACE_ROLE

    def content_team_binding_audit(
        rows: list[list[str]],
        headers: list[str],
        indexes: dict[str, int | None],
        source_role: str,
    ) -> dict[str, Any]:
        direct = original(rows, headers, indexes, source_role)
        if direct.get("binding_status") != "UNRESOLVED":
            return direct
        if indexes.get("team") is not None:
            return direct

        # ADAPT_NOT_COPY from Content Source Role Resolver Lite V1:
        # no direct team column + exact embedded `<prefix> - <action>` support
        # admits TEAM_SURFACE_CANDIDATE only. The prefix itself remains a raw
        # provider/team candidate and is never promoted to validated identity.
        embedded = original(rows, headers, indexes, team_surface_role)
        if embedded.get("binding_status") != "EMBEDDED_CODE_TEAM_CANDIDATE":
            return direct

        evidence = dict(embedded.get("binding_evidence") or {})
        evidence.update(
            {
                "content_role_bridge": "CONTENT_EMBEDDED_TEAM_CANDIDATE",
                "filename_support_used_for_admission": False,
                "validated_team_identity": False,
            }
        )
        embedded["binding_evidence"] = evidence
        embedded["resolved_source_role_candidate"] = team_surface_role
        embedded["validated_team_identity"] = False
        return embedded

    reader_module.team_binding_audit = content_team_binding_audit
    reader_module._hpfa_content_team_binding_installed = True
