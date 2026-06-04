# Implementation Plan

1. Add passphrase provider module with env, prompt, confirmation, and readiness reporting.
2. Wire provider into init, server, backup, restore, delete, and decrypted status scripts.
3. Add readiness CLI and provider smoke check.
4. Update static smoke contracts and supervisor-facing docs.
5. Run regression smoke suite and private artifact checks.
6. Record evidence and harness efficiency score.
