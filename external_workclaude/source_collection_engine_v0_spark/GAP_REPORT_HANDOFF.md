## Not implemented
- news_c (news_society_economy): skipped with skip_reason `collector_not_implemented`.

## Fallback only
- news_a (news_society_economy, entertainment_news): collected only via fallback method signals (`settings_keyword_fallback`).

## Recommended: Spark vs Claude next
- Prioritize Spark for `news_c` to implement shallow collector where missing; this has no explicit blocked/login pattern and affects lane coverage.
- Delegate fallback-dominant sources like `news_a` to Claude for source-specific method hardening and fallback-reduction follow-up.
