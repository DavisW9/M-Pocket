# Security Policy

## Supported versions

Security fixes target the latest M-Pocket release or beta. Please update to the newest available version before reporting an issue. Older versions may no longer receive fixes.

## Reporting a vulnerability

Please report suspected vulnerabilities privately through GitHub’s **Report a vulnerability** option on this repository’s **Security** tab. Do not open a public issue or pull request for an unpatched vulnerability.

Include the affected version, Cardputer Zero firmware version, steps to reproduce, and any relevant sanitized logs. Please do not include passwords, access tokens, QR codes, authorization codes, session links, or private account content.

I’ll acknowledge reports as soon as I can and coordinate a fix and disclosure with the reporter. Please allow time for investigation before sharing details publicly.

## Security notes

- M-Pocket communicates with the selected Mastodon server over HTTPS for feeds and account actions.
- QR sign-in uses the M-Pocket callback service to complete pairing. It handles short-lived pairing state and authorization codes; account passwords and access tokens are not sent to that service.
- Access tokens are saved on the device in `~/.config/m-pocket/session.json` with restrictive file permissions. They are not encrypted, so someone with access to the device account or its unencrypted storage may be able to read them.
- If you believe a token may have been exposed, revoke M-Pocket’s access from your Mastodon server and sign in again.
