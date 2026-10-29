# Nimbus Account and Security Guide

## Credential recovery

If a user can no longer sign in, they must go through the credential recovery flow. The flow starts from the sign-in page with the link "Trouble signing in". The user enters the email address of the account and receives a recovery link valid for 20 minutes. A recovery link can only be used once.

If two-factor authentication is enabled, the user must also enter one of the ten backup codes generated when 2FA was activated. Each backup code works only once. If the user has lost both their device and their backup codes, recovery requires an identity check by the support team, which takes up to 3 business days.

## Two-factor authentication

Nimbus supports two second factors: time-based one-time passwords (TOTP) from an authenticator app, and hardware security keys using WebAuthn. SMS codes are not supported since March 2024 because of SIM swap attacks. Organisation owners can make 2FA mandatory for every member in Settings > Security > Enforce 2FA. Members without 2FA are then given 7 days to enable it before their access is suspended.

## API keys

API keys are created per project. A key is shown only once, at creation. Nimbus stores only a hash of the key, so a lost key cannot be recovered and must be rotated. Keys that have not been used for 180 days are automatically disabled, and the project owner receives an email 14 days before.

## Sessions

Web sessions expire after 12 hours of inactivity. Signing out from Settings > Sessions > Sign out everywhere revokes all web sessions and all refresh tokens, but does not revoke API keys.

## Audit log

Every security event is recorded in the audit log: sign-ins, failed sign-ins, 2FA changes, API key creation and deletion, and role changes. Team accounts keep the audit log for 90 days, Enterprise accounts for 2 years. The audit log can be exported as CSV.
