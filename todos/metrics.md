# metrics: a reminder to re-export, and liveness

## Opening prompt

> Give smoked-paprika the metrics the cluster needs to remind Will when the
> export is stale and to notice when the service is down. Read
> `todos/metrics.md`. The alert rules live in the deployment repository; this
> spec is the service half.

## Why

The collection is only as fresh as the last share-sheet export, and nothing
automatic refreshes it (design, *Freshness*). Forgetting is the expected
failure, so the reminder is the feature. In the deployment repository's
spirit, "alert on the absence of recent success".

## Scope

- A `/metrics` endpoint, kept off the public hostname or behind the deployment's
  metrics scraping.
- Timestamps rather than ages, so a rule's `time() - x` is exact: last
  successful upload, the current export's own time, and the last refused upload
  with the reason as a label.
- Recipe count.
- Check how the deployment's existing rules measure the same thing for scheduled
  jobs and backups, and match them.

The deployment half: a `ServiceMonitor` or `PodMonitor`, a staleness rule with a
threshold Will picks, and a liveness rule.

## Done when

- Each rule's expression returns data in Prometheus, queried rather than
  inferred: a metric name can exist and still have no series.
- The staleness rule was made to fire once, by lowering its threshold, and then
  to clear on an upload.
