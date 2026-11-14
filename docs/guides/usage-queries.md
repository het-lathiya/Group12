# Daily generation usage

UTC day boundaries are bound parameters; include queued, failed and completed attempts. Explicit rule-based runs do not count; fallback after an AI attempt does (IMD-43).

```sql
SELECT count(*) FILTER (WHERE user_id = :user_id) AS user_count,
       count(*) AS global_count
FROM public.ai_generations
WHERE created_at >= :utc_day_start AND created_at < :next_utc_midnight
  AND model_id <> 'rule_based_planner_v1';
```

IMP-511 checks before insert and job submission, serialised by the single-process quota lock (IMD-12). The existing user/day index serves user usage, and retention_until is indexed for daily purge. No provider calls occur inside this transaction. Multi-instance deployment requires a shared concurrency mechanism first.

The scheduler deletes expired generation rows at startup and every 24 hours. Existing ON DELETE SET NULL references preserve itinerary days and versions. No prompt, key or response body is recorded here.
