# Nimbus Storage API - Error Reference

This page lists every error code returned by the Nimbus Storage API v3. Each error is returned as JSON with the fields `code`, `message` and `request_id`.

## Authentication errors

### NMB-401-TOKEN_EXPIRED
The access token sent in the `Authorization` header has expired. Access tokens are valid for 3600 seconds. Request a new token from the `/oauth/token` endpoint using your refresh token. Refresh tokens are valid for 30 days.

### NMB-401-TOKEN_INVALID
The token could not be decoded. This usually means the token was truncated when copied, or that a token from the staging environment was used against production. Staging tokens always start with the prefix `stg_`.

### NMB-403-SCOPE_MISSING
The token is valid but does not carry the scope required by the endpoint. For example, deleting a bucket requires the `buckets:admin` scope, while listing objects only requires `objects:read`.

## Rate limiting

### NMB-429-RATE_LIMITED
The client sent too many requests. The default limit is 600 requests per minute per API key, and 50 requests per minute for the `/v3/search` endpoint. The response includes a `Retry-After` header in seconds. Clients should back off exponentially, starting at 2 seconds and capping at 64 seconds.

## Storage errors

### NMB-404-OBJECT_NOT_FOUND
The object key does not exist in the bucket. Note that object keys are case sensitive: `Report.pdf` and `report.pdf` are two different objects.

### NMB-409-BUCKET_NOT_EMPTY
A bucket can only be deleted when it contains zero objects and zero incomplete multipart uploads. Use `nimbus bucket purge` to remove both before deleting.

### NMB-413-OBJECT_TOO_LARGE
A single PUT request accepts objects up to 5 GB. Larger objects must use multipart upload, with parts between 5 MB and 512 MB. The maximum object size with multipart upload is 5 TB.

### NMB-507-QUOTA_EXCEEDED
The account has reached its storage quota. Free accounts have 10 GB, Team accounts have 2 TB, and Enterprise quotas are set by contract. Writes are rejected but reads keep working.

## Server errors

### NMB-500-INTERNAL
An unexpected error happened on our side. Retry the request once. If it fails again, contact support and give the `request_id`.

### NMB-503-REGION_DEGRADED
The region is in degraded mode, usually during a failover. Writes may be paused for up to 15 minutes while reads are served from the replica. The status page at status.nimbus.example shows the current state of each region.
