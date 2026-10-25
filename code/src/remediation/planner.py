from ..models.step import AuditStep, DeletionStatus, sort_and_renumber_steps


class RemediationPlanner:
    @staticmethod
    def plan(
        status: DeletionStatus,
        findings: list[AuditStep],
        remediations: list[AuditStep],
        verifications: list[AuditStep],
    ) -> list[AuditStep]:
        """
        Creates the ordered step plan:
        - For NOT_APPLICABLE: empty list
        - For COMPLETE: verification steps only, citing evidence_id
        - For INCOMPLETE: findings + remediations + future verifications
        Steps are canonically sorted by:
        1. Phase order (FINDING -> REMEDIATION -> VERIFICATION)
        2. Operation priority
        3. system_id ascending
        4. resource_id ascending
        """
        if status == DeletionStatus.NOT_APPLICABLE:
            return []

        if status == DeletionStatus.COMPLETE:
            return sort_and_renumber_steps(verifications)

        # For INCOMPLETE: future remediation and post-remediation verifications have empty evidence_id
        clean_remediations = []
        for r in remediations:
            r_copy = r.model_copy(update={"evidence_id": ""})
            clean_remediations.append(r_copy)

        clean_verifications = []
        for v in verifications:
            v_copy = v.model_copy(update={"evidence_id": ""})
            clean_verifications.append(v_copy)

        combined = findings + clean_remediations + clean_verifications
        return sort_and_renumber_steps(combined)
