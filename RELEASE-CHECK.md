# Device beta 0.2.0-beta3 verification

The beta 3 ARM64 package was installed on a physical Cardputer Zero. The device owner reports testing it; detailed test results and coverage have not been documented.

Host-side tests cover service behavior, search, content warnings, replies, boosts, scrolling, and settings. Live QR sign-in, server compatibility, and all social actions should be checked on the target device and account.

Saved access tokens are stored in a file restricted to the Linux user; device storage is not encrypted by the app. See README.md for installation, controls, and beta limitations.
