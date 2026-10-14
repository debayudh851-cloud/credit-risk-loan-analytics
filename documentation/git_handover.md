# Git handover

Destination: https://github.com/debayudh851-cloud/credit-risk-loan-analytics. The user approved repository creation and source upload, then explicitly requested public visibility. The handover contains code, input-free notebooks and aggregate documentation. Raw borrower CSVs, the original contact-bearing seed SQL, PRD copies, private database files, model binaries and per-record scored/SHAP output are excluded. Final publication revisions and visibility are verified and recorded locally in artifacts/git_handover.json.

The local parent repository retains the project under its 2nd project folder. The handover commit is restricted to this project; unrelated project changes are excluded. Public-facing repository files are flattened to the project root, and notebook execution output is stripped by scripts/export_source.py. Recorded local and remote revisions are stored in artifacts/git_handover.json after successful verification.

The source contains documented unresolved acceptance: applicant AUC 0.6670 against the requested 0.80 target, and missing history/mature outcome records for prospective validation. Publication does not imply those targets have been achieved. The repository README explains how to provide the original data locally and rerun the complete workflow.
