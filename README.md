# Personal Notion Hub

개인 운영 정보를 한 화면에서 정리하는 정적 Notion-style web hub입니다.

## Purpose

- 프로젝트, task, note, routine, link를 한 브라우저에서 빠르게 관리합니다.
- 모바일에서 프로젝트 개요를 작성하고 팀 착수용 dispatch packet으로 정리합니다.
- 기본 web UI는 서버, API, backend, dependency install 없이 동작합니다.
- 민감 입력은 선택형 local companion encrypted vault로 workspace-local 저장할 수 있습니다.
- 기본 hub 데이터는 브라우저 `localStorage`에 저장됩니다.
- assistant inbox 데이터는 브라우저 `IndexedDB`에 저장됩니다.
- 전체 데이터는 JSON으로 export/import할 수 있습니다.
- 서버, 외부 API, OAuth, cloud sync는 사용하지 않습니다.

## Run Locally

브라우저에서 `index.html`을 직접 열어도 동작합니다.

정적 서버로 확인하려면:

```bash
python3 -m http.server 4173
```

그 다음 접속:

```text
http://127.0.0.1:4173/
```

## Data Policy

이 앱은 public GitHub Pages 배포를 전제로 설계되었습니다.

저장소에 커밋하면 안 되는 것:

- 실제 개인 업무 데이터
- client data
- API key
- token
- credential
- private internal URL
- 민감한 운영 메모

기본 hub 사용 데이터는 사용자의 브라우저 저장소에 저장됩니다. 다른 기기와 자동 동기화되지 않습니다.

민감 입력 MVP는 명시적으로 켠 local companion encrypted vault 모드에서 `companion/private/` 아래 ignored SQLite DB에 암호화 저장됩니다. Plaintext private inbox 모드는 호환성 검증용 transitional mode로만 사용합니다.

Assistant MVP는 수동 입력과 demo fixture만 다룹니다. Slack, email, SMS, KakaoTalk, call, voice memo, YouTube, calendar, Bible verse 같은 입력 경로는 source label일 뿐이며 실제 외부 서비스에 연결하지 않습니다.

## Assistant MVP

`Assistant` 화면은 참고 이미지의 흐름을 local-only 방식으로 구현합니다.

```text
manual input routes
-> local rule processing
-> work log / todo / daily summary / Slack-style draft / calendar draft
```

지원 범위:

- manual paste input
- demo fixture input
- IndexedDB assistant inbox
- local rule-based suggestions
- copyable Slack-style summary draft
- copyable calendar draft
- 오늘의 성경말씀 widget
- paired local companion으로 Assistant input을 workspace private inbox/encrypted vault에 전송

제외 범위:

- 실제 Slack/Google/Notion/Kakao/phone API 연동
- 연락처, 통화기록, 문자, 녹음파일 자동 접근
- OAuth, API key, token, cloud sync
- cloud AI/STT/LLM 처리

Assistant workspace ingress:

```bash
python3 scripts/private_inbox_init.py
python3 companion/server.py \
  --host 127.0.0.1 \
  --port 8765 \
  --enable-private-inbox \
  --enable-browser-bridge \
  --allowed-origin http://127.0.0.1:4173
python3 -m http.server 4173
```

Open `http://127.0.0.1:4173/`, go to `Assistant`, pair with the local
terminal's one-time code, add a synthetic input, and use `Send Latest Input` or
`Send to Workspace`.

Expected:

- browser response is metadata-only
- pairing/session token is not shown or stored in browser persistence
- `scripts/private_inbox_status.py` reports an increased count without printing the body
- in encrypted vault mode, the input is written to `encrypted_mobile_captures`

## Launch MVP

`Launch` 화면은 모바일 project intake를 위한 local-only MVP입니다.

지원 범위:

- project title/objective/outcome/constraints 입력
- dispatch packet 생성
- Discord command draft 복사
- GitHub issue draft 복사
- 기존 Projects/Tasks에 local starter work 생성
- repeated local start 중복 방지

제외 범위:

- 실제 Discord/GitHub/OpenClaw 전송
- API token 또는 secret 저장
- 자동 외부 서비스 연동
- real private data ingest

GitHub ledger bridge:

```bash
python3 scripts/github_ledger_bridge_smoke_check.py
python3 scripts/pnh_dispatch_job_smoke_check.py
```

The bridge defaults to dry-run. Live GitHub Issue creation requires a separate
approval gate, a local runtime `GITHUB_TOKEN`, and explicit apply flags. Raw
private command contents are not included by default.

The dispatch job adds an idempotent local state layer for future
GitHub-Issue-to-Discord/OpenClaw routing. Apply-mode state lives under ignored
`companion/private/` storage.

장기 방향:

- `docs/MOBILE_PROJECT_LAUNCH_AUTOMATION_ROADMAP.md`
- `docs/GITHUB_LEDGER_BRIDGE_DESIGN.md`

## Long-Term Private Data Direction

민감 개인정보, 통화 내용, 녹음 transcript, 일정, 연락처를 장기적으로 다루려면 browser storage만으로는 부족합니다.

채택한 장기 방향:

```text
Personal_Notion_Hub web UI
-> local companion script/service
-> encrypted SQLite or encrypted local vault
```

관련 문서:

- `docs/LOCAL_COMPANION_ARCHITECTURE.md`
- `docs/PRIVATE_DATA_POLICY.md`
- `docs/adr-0001-local-companion-vault.md`

## Local Companion Prototype

`companion/` contains a loopback-only local companion. It keeps fixture preview mode for public-safe QA, a transitional authenticated plaintext private inbox, and an explicit encrypted vault mode for sensitive local capture.

Current limits:

- `127.0.0.1` loopback only
- no real contacts, schedules, calls, recordings, transcripts, or private notes
- no file write from import preview mode
- browser UI bridge is local-only and disabled unless the companion is started with explicit bridge flags
- no phone/contact/calendar/recording adapters yet
- encrypted backup/restore/delete scripts are available for encrypted capture rows
- plaintext migration apply is available behind an explicit backup and confirmation gate
- prompt-first passphrase input is available
- `windows-dpapi-file` local passphrase storage is available for approved Windows + WSL use

Dependency boundary:

- No package install is performed by this project setup.
- Encrypted vault mode uses the already-installed Python `cryptography` package when available.
- If `cryptography` or the required passphrase input is missing, encrypted vault startup fails closed.

Run the companion smoke check:

```bash
python3 scripts/companion_smoke_check.py
```

Run the local API manually:

```bash
python3 companion/server.py --host 127.0.0.1 --port 8765
```

Then inspect:

```text
http://127.0.0.1:8765/api/health
http://127.0.0.1:8765/api/schema
```

Actual phone/contact/calendar/recording adapters, external dispatch, non-loopback access, plaintext migration apply, OS keychain storage/retrieval, and packaging remain separate approval gates.

## Browser Companion Bridge

The Launch page can connect to the local companion in private bridge mode.

Run private inbox plus browser bridge:

```bash
python3 scripts/private_inbox_init.py
python3 companion/server.py \
  --host 127.0.0.1 \
  --port 8765 \
  --enable-private-inbox \
  --enable-browser-bridge \
  --allowed-origin http://127.0.0.1:4173
```

Then serve the static UI:

```bash
python3 -m http.server 4173
```

Open:

```text
http://127.0.0.1:4173/
```

Use the one-time `browser_pairing_code` printed by the companion terminal to pair the Launch page. Do not paste that code into chat, screenshots, docs, or committed files.

Bridge boundaries:

- browser bridge is disabled by default
- browser bridge requires private inbox mode
- CORS allowlist is exact-origin only
- CSP allows `connect-src 'self' http://127.0.0.1:8765`
- browser session token is kept in JS memory only
- long-lived file token is not sent to the browser
- Launch packet writes require explicit user action
- Assistant input writes require explicit user action
- API response remains metadata-only
- Launch 화면에는 screenshot redaction toggle이 있으며 민감 launch text와 pairing input을 캡처 전에 가릴 수 있습니다.
- real sensitive data should use encrypted vault mode, not plaintext private inbox mode

## Phone Ingress MVP

Phone ingress lets a phone browser on the same trusted private LAN open the PNH
UI and explicitly send Assistant/Launch captures to the workspace companion.

Default stance:

- disabled by default
- private LAN only
- exact-origin only
- one-time pairing required
- synthetic or low-risk input first

Find LAN candidates and commands:

```bash
python3 scripts/phone_ingress_lan_info.py
```

Run synthetic/low-risk phone ingress:

```bash
python3 scripts/private_inbox_init.py
python3 companion/server.py \
  --host 0.0.0.0 \
  --port 8765 \
  --enable-private-inbox \
  --enable-browser-bridge \
  --enable-phone-ingress \
  --allowed-origin http://<LAN_IP>:8765
```

Open on phone:

```text
http://<LAN_IP>:8765/
```

Sensitive input should use encrypted vault mode:

```bash
python3 companion/server.py \
  --host 0.0.0.0 \
  --port 8765 \
  --enable-private-inbox \
  --enable-encrypted-vault \
  --vault-passphrase-provider windows-dpapi-file \
  --enable-browser-bridge \
  --enable-phone-ingress \
  --allowed-origin http://<LAN_IP>:8765
```

See `docs/PHONE_INGRESS_SECURITY.md`.

## Local Encrypted Vault MVP

The encrypted vault proves this higher-sensitivity path:

```text
virtual mobile input
-> 127.0.0.1 local companion
-> bearer-token protected endpoint
-> AES-GCM encrypted local SQLite record
-> redacted metadata/status output
```

Set the vault passphrase locally before running encrypted mode. Do not paste this value into chat, screenshots, logs, docs, or committed files.

Prompt mode is preferred for manual local sessions because it avoids shell history and stale environment values:

```bash
python3 scripts/keychain_readiness.py
python3 scripts/private_inbox_init.py \
  --enable-encrypted-vault \
  --prompt-vault-passphrase \
  --confirm-vault-passphrase
python3 companion/server.py \
  --host 127.0.0.1 \
  --port 8765 \
  --enable-private-inbox \
  --enable-encrypted-vault \
  --prompt-vault-passphrase
```

Environment variable mode remains available for non-interactive local runs:

```bash
read -rsp "PNH vault passphrase: " PNH_VAULT_PASSPHRASE
export PNH_VAULT_PASSPHRASE
python3 scripts/private_inbox_init.py --enable-encrypted-vault
```

Windows + WSL DPAPI file mode is available after storing the passphrase locally:

```bash
python3 scripts/vault_secret_store.py \
  --provider windows-dpapi-file \
  --name vault-passphrase \
  --prompt

python3 scripts/vault_secret_status.py --provider windows-dpapi-file

python3 companion/server.py \
  --host 127.0.0.1 \
  --port 8765 \
  --enable-private-inbox \
  --enable-encrypted-vault \
  --vault-passphrase-provider windows-dpapi-file
```

Run the encrypted vault smoke check:

```bash
python3 scripts/encrypted_vault_smoke_check.py
```

Encrypted backup/restore/delete/rotation lifecycle scripts:

```bash
python3 scripts/encrypted_vault_backup.py \
  --out companion/private/backups/pnh-$(date +%Y%m%d).pnhbackup \
  --prompt-vault-passphrase \
  --prompt-backup-passphrase \
  --confirm-backup-passphrase

python3 scripts/encrypted_vault_restore.py \
  --backup companion/private/backups/pnh-YYYYMMDD.pnhbackup \
  --prompt-vault-passphrase \
  --prompt-backup-passphrase

python3 scripts/encrypted_vault_delete.py \
  --capture-id capture-id-to-delete \
  --confirm DELETE_CAPTURE \
  --prompt-vault-passphrase

python3 scripts/encrypted_vault_rotate_passphrase.py \
  --preflight-backup companion/private/backups/pnh-YYYYMMDD.pnhbackup \
  --confirm ROTATE_VAULT_PASSPHRASE \
  --prompt-vault-passphrase \
  --prompt-new-vault-passphrase \
  --confirm-new-vault-passphrase

python3 scripts/plaintext_migration_audit.py --fail-on-plaintext

python3 scripts/plaintext_migration_apply.py \
  --preflight-backup companion/private/backups/pnh-YYYYMMDD.pnhbackup \
  --confirm MIGRATE_PLAINTEXT_TO_ENCRYPTED \
  --prompt-vault-passphrase
```

Run lifecycle smoke checks:

```bash
python3 scripts/encrypted_vault_backup_restore_smoke_check.py
python3 scripts/encrypted_vault_delete_smoke_check.py
python3 scripts/encrypted_vault_rotation_smoke_check.py
python3 scripts/plaintext_migration_audit_smoke_check.py
python3 scripts/plaintext_migration_apply_smoke_check.py
python3 scripts/vault_secret_smoke_check.py
python3 scripts/redacted_browser_qa_check.py
```

Encrypted vault boundaries:

- encrypted vault mode is disabled by default
- passphrase is read from prompt or environment variable name, not from a CLI value
- prompt mode uses no-echo terminal input and can require confirmation for initialization/backup
- `scripts/keychain_readiness.py` reports host readiness without storing or printing secrets
- private title/body/payload values are encrypted before SQLite persistence
- API responses and default status output are metadata-only
- wrong passphrase and tampered ciphertext are rejected
- existing plaintext private inbox rows are not migrated automatically
- encrypted backups are encrypted envelope files, not plaintext JSON exports
- restore skips duplicate IDs unless `--replace` is explicitly provided
- delete requires `--confirm DELETE_CAPTURE`
- passphrase rotation requires `--confirm ROTATE_VAULT_PASSPHRASE` and an existing encrypted backup path
- plaintext migration audit reports counts only and does not mutate the DB
- plaintext migration apply requires `--confirm MIGRATE_PLAINTEXT_TO_ENCRYPTED` and an existing encrypted backup path
- `windows-dpapi-file` stores a DPAPI-protected blob under the current Windows user's LocalAppData path
- passphrase recovery is policy-only; there is no cryptographic recovery mechanism
- real-data adapter ingestion and forensic secure erase are not implemented yet

## Local Private Inbox MVP

The plaintext private inbox remains available as a transitional compatibility path:

```text
virtual mobile input
-> 127.0.0.1 local companion
-> bearer-token protected endpoint
-> ignored workspace SQLite inbox
```

Initialize the local private inbox:

```bash
python3 scripts/private_inbox_init.py
```

Run the companion with private inbox writes enabled:

```bash
python3 companion/server.py --host 127.0.0.1 --port 8765 --enable-private-inbox
```

In another terminal, simulate a mobile capture:

```bash
python3 scripts/simulate_mobile_capture.py \
  --title "Synthetic mobile project brief" \
  --body "Synthetic private note for workspace ingress validation."
```

Or paste mobile-like body text through stdin without storing the text in shell history:

```bash
printf "Synthetic mobile project brief body." | python3 scripts/simulate_mobile_capture.py \
  --source mobile_web \
  --kind project_brief \
  --title "Synthetic mobile project brief" \
  --body-file -
```

Check that the capture reached the workspace-local inbox without printing private values:

```bash
python3 scripts/private_inbox_status.py
```

Security boundary:

- token value is never printed by the scripts
- write endpoint requires `Authorization: Bearer ...`
- server binds to `127.0.0.1` only
- capture sender accepts only `http://127.0.0.1:<port>` and blocks redirects
- private DB and token paths must remain under `companion/private/`
- raw capture body is not echoed in API responses
- `companion/private/` is ignored and must not be committed

Current protection is local-only binding, bearer-token auth, repository ignore rules, and best-effort file permissions. Do not use plaintext private inbox mode for routine high-sensitivity records; use `--enable-encrypted-vault`.

## Backup

`Settings -> Export JSON`으로 현재 브라우저 데이터를 백업합니다.

복구할 때는 `Settings -> Import JSON`을 사용합니다.

백업 파일은 개인 데이터일 수 있으므로 저장소에 커밋하지 마세요.

## Deploy

GitHub Pages는 `.github/workflows/pages.yml`을 사용합니다.

Workflow 특징:

- dependency install 없음
- static artifact만 업로드
- permissions 최소화: `contents: read`, `pages: write`, `id-token: write`
- `main` push 또는 manual dispatch에서 실행

GitHub Pages custom workflow 사용은 repository Pages settings에서 GitHub Actions source를 활성화해야 할 수 있습니다.

## Files

- `index.html`: app entry
- `assets/css/styles.css`: layout, theme, responsive UI
- `assets/js/app.js`: localStorage state, rendering, interactions
- `assets/js/assistant-storage.js`: IndexedDB assistant inbox adapter
- `assets/js/assistant-import.js`: manual/fixture input normalizer
- `assets/js/assistant-rules.js`: local rule assistant
- `data/seed.json`: demo-only schema note
- `docs/TEST_PLAN.md`: manual QA plan
- `docs/SECURITY_NOTES.md`: public deployment and localStorage risk notes
- `docs/LOCAL_COMPANION_ARCHITECTURE.md`: long-term local companion and encrypted vault architecture
- `docs/MOBILE_PROJECT_LAUNCH_AUTOMATION_ROADMAP.md`: mobile project intake to automated team dispatch roadmap
- `docs/PRIVATE_DATA_POLICY.md`: private data handling rules
- `docs/adr-0001-local-companion-vault.md`: architecture decision record
- `companion/`: local companion, encrypted vault, private inbox storage, and fake import fixtures

## Limitations

- 기본 web UI에는 서버 저장 없음
- 기본 web UI에는 계정/auth 없음
- companion private inbox에는 local bearer token auth 사용
- encrypted vault mode는 no-echo prompt 또는 local passphrase 환경변수와 application-level AES-GCM encryption 사용
- encrypted backup/restore/delete lifecycle scripts are local-only and metadata-only in output
- `windows-dpapi-file` can store the vault passphrase locally for approved Windows + WSL use
- 다중 기기 sync 없음
- collaboration 없음
- localStorage와 IndexedDB 기반이므로 브라우저/기기 보안에 의존
- assistant output은 rule-based draft이며 실제 일정 등록이나 메시지 전송은 하지 않음
- launch output은 local packet/copy draft이며 실제 Discord/GitHub/OpenClaw 실행은 하지 않음
- plaintext local private inbox는 encrypted vault가 아니며, 장기 민감 보관 전 encrypted mode와 backup/delete workflow가 필요함
