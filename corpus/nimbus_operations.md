# Nimbus Operations Handbook (internal)

## Regions

Nimbus runs in three regions: `eu-west` in Paris, `eu-central` in Frankfurt, and `us-east` in Virginia. Every object is stored in three copies inside its region. Cross-region replication is optional and must be enabled per bucket.

## On-call

The on-call rotation changes every Monday at 10:00 Paris time. Each rotation has one primary and one secondary engineer. The primary must acknowledge a page within 5 minutes. If the primary does not acknowledge within 5 minutes, the page escalates to the secondary, and after 15 minutes to the engineering manager.

## Incident severity

- SEV1: data loss, or a full region unavailable. The incident commander is the on-call primary, and a public status page update is required within 15 minutes.
- SEV2: a degraded region, or errors above 5% on any API endpoint for more than 10 minutes. Status page update within 30 minutes.
- SEV3: a single customer affected, or an internal tool unavailable. No status page update.

## Postmortems

Every SEV1 and SEV2 incident requires a written postmortem within 5 business days. Postmortems are blameless: they describe what the system allowed to happen, not who made the mistake. Each postmortem lists action items with an owner and a due date.

## Deployments

Production deployments happen Monday to Thursday, between 09:00 and 16:00 Paris time. No deployments on Fridays, on weekends, or during the end-of-year freeze from December 20 to January 3. Every deployment goes first to `eu-central`, then waits 30 minutes before going to the other regions. A deployment can be rolled back with `nimbus-deploy rollback --to previous`.

## Backups

Metadata databases are backed up every hour, and backups are kept for 35 days. A restore test is run on the first Tuesday of each month. The last restore test result is posted in the #ops-backups channel.
