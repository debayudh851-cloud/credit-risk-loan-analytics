# Version 2 verification summary

The full datasets were loaded into private PostgreSQL 18 and the portable SQLite fallback. Both model workflows are trained independently. No original source file was modified and no loan request is generated for customers lacking applications.

| Check | Evidence |
|---|---|
| Entity rows | 5,000 customers; 5,000 bureau; 7,500 applications; 40,079 transactions |
| Score coverage | 7,500 request-time application scores and 5,000 actual-profile customer scores |
| Unit and dashboard checks | Twenty passed: five availability, twelve core and three dashboard checks |
| Future data isolation | Strict features work with only loan request and transaction tables; appended future transactions cannot alter old requests |
| Database constraints | Orphan, out-of-range, invalid-target and reversed-date operations rejected in PostgreSQL and SQLite |
| Analytical SQL | All ten queries execute with correct denominators and customer/application grains |
| Reuse | Both saved models reproduce their full saved probability arrays |
| Explanations | All applicant and customer SHAP rows reconstruct base outputs; scale conversion and sigmoid mapping reconstruct final probability |
| Privacy | No direct personal contacts or birth dates in dashboard inputs; exporter admits only source/aggregate documentation and clears notebook outputs |
| Notebooks | All four notebooks executed against the v2 pipeline outputs; execution evidence recorded locally |
| Repeatability | Two complete v2 runs reproduce both algorithms, thresholds, test metrics, score probabilities and risk bands |
| Recall target | Passed: applicant 78.62%, customer 81.74% |
| AUC target | Not met: applicant 0.6670, customer 0.6709 |
| Training budget | Total training across both four-model workflows is below five minutes; actual run_manifest.json records timing |

The first v2 pipeline took 304 seconds including serial full-customer SHAP computation. Parallel exact customer SHAP computation reduced the repeat run to approximately 171 seconds without changing model outputs. Explainability time is separate from the 92-second total training time in the first run.

The borrower-disjoint and fixed-calendar audits are sensitivity checks. Genuine future prediction validation still needs dated bureau/profile history, outcome events, observation ends and a fixed default horizon. The AUC development investigation was confined to the frozen training partition; its CV estimate is not a held-out success metric.

Local evidence is in artifacts/verification.json, reproducibility.json, notebook_verification.json, sql_timings.json, metrics.json, customer_model/metrics.json and acceptance_status.json. Git publication provenance is recorded separately in documentation/git_handover.md and local handover evidence.
