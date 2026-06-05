# Test Plan

## Scope

정적 `Personal Notion Hub`의 기능, localStorage persistence, responsive layout, accessibility baseline, GitHub Pages artifact 배포를 검증한다.

## Functional Checks

- Assistant 화면이 sidebar에서 열린다.
- Assistant input routes에 Slack, Email, SMS, KakaoTalk, Call, Voice memo, My memo, YouTube, Bible verse가 표시된다.
- Assistant manual input을 추가하면 inbox에 표시된다.
- Assistant manual input은 dispatch intent를 선택할 수 있다.
- Assistant dispatch intent가 command type이면 workspace 전송 payload가 `pnh_mobile_command_packet`으로 생성된다.
- Assistant dispatch intent가 `assistant_capture`이면 기존 assistant note 전송 경로가 유지된다.
- Assistant manual input은 paired local companion으로 workspace private inbox에 전송할 수 있다.
- Assistant demo fixture를 불러오면 demo capture와 suggestion이 표시된다.
- Assistant suggestion에서 `Create Task`를 누르면 기존 Tasks에 항목이 생성된다.
- Assistant suggestion에서 `Create Note`를 누르면 기존 Notes에 항목이 생성된다.
- Calendar/Slack-style draft는 실제 전송 없이 copy action만 제공된다.
- 오늘의 성경말씀 widget이 표시된다.
- Dashboard가 첫 화면으로 로드된다.
- Launch 화면이 sidebar에서 열린다.
- Launch brief에서 project title/objective/outcome/constraints를 입력하면 dispatch packet이 생성된다.
- Launch packet은 Discord draft와 GitHub issue draft copy action을 제공한다.
- Launch `Start Locally`는 project와 starter tasks를 생성한다.
- Launch `Start Locally`를 반복 실행해도 starter tasks가 중복 생성되지 않는다.
- Quick Capture로 task, note, project, link를 생성할 수 있다.
- Projects에서 project 생성, 수정, 삭제가 가능하다.
- Tasks에서 inbox/today/upcoming/done 상태가 표시된다.
- Task 완료/재오픈이 가능하다.
- Notes에서 긴 본문을 입력해도 레이아웃이 깨지지 않는다.
- Routines에서 checklist와 complete 상태가 관리된다.
- Links에서 외부 링크가 새 탭으로 열린다.
- Links는 `http`/`https` URL만 저장 가능하다.
- `javascript:`, `data:`, 잘못된 URL은 저장되지 않는다.
- Settings에서 theme toggle이 동작한다.
- Export JSON이 파일을 다운로드한다.
- Import JSON으로 데이터를 복원한다.
- Import 전 기존 데이터 교체 확인 dialog와 pre-import backup 다운로드가 실행된다.
- 잘못된 schema는 import되지 않는다.
- Reset은 `RESET` 입력 없이는 실행되지 않는다.

## localStorage Checks

브라우저 console에서:

```js
localStorage.clear()
location.reload()
```

기대 결과:

- seed 상태로 정상 렌더링된다.
- fatal console error가 없다.

손상 데이터 복구:

```js
localStorage.setItem('personalNotionHubState', '{broken json')
location.reload()
```

기대 결과:

- 앱이 기본 상태로 복구된다.
- recovery toast가 표시된다.
- fatal console error가 없다.

## IndexedDB Assistant Checks

브라우저 console에서:

```js
indexedDB.deleteDatabase('personalNotionHubAssistant')
location.reload()
```

기대 결과:

- Assistant 화면이 정상 렌더링된다.
- IndexedDB가 다시 초기화된다.
- localStorage의 기존 hub 데이터는 손상되지 않는다.

Assistant fixture:

- `Load demo fixture` 클릭
- Inbox와 Suggested Outputs에 demo 항목 표시
- 새로고침 후 assistant inbox 유지

## Local Companion Prototype Checks

The companion fixture preview uses fake fixtures only. It must not handle real contacts, calls, schedules, recordings, transcripts, client data, or secrets.

Run:

```bash
python3 scripts/companion_smoke_check.py
```

Expected:

- health endpoint reports `ok=true`
- mode is fixture-only
- writes are disabled
- schema endpoint lists allowed collections and private-data restrictions
- valid fake fixture returns preview counts
- sensitive-looking fixture is rejected without echoing the sensitive value
- non-loopback host configuration is rejected
- fixture preview does not create new vault, database, private backup, or runtime data files

## Local Private Inbox Checks

The private inbox proves that phone-like input can reach workspace-local private storage.

Run fixture-based private inbox validation:

```bash
python3 scripts/private_inbox_smoke_check.py
```

Expected:

- non-loopback host configuration is rejected
- private inbox health reports writes enabled
- write endpoint rejects missing auth
- write endpoint rejects wrong token
- valid bearer token can store a synthetic capture
- stdin mobile-like sender can store an additional synthetic capture without echoing the body
- API response does not echo title/body private values
- simulated mobile sender rejects non-loopback base URLs before reading the token
- private inbox init rejects DB/token paths outside `companion/private/`
- status command does not create a missing DB
- summary reports two synthetic captures during smoke validation
- recent list is redacted and omits body text
- SQLite summary confirms persistence

Run real local private inbox setup:

```bash
python3 scripts/private_inbox_init.py
python3 companion/server.py --host 127.0.0.1 --port 8765 --enable-private-inbox
```

Then, in a second terminal:

```bash
python3 scripts/simulate_mobile_capture.py \
  --title "Synthetic mobile project brief" \
  --body "Synthetic private note for workspace ingress validation."
python3 scripts/private_inbox_status.py
```

Optional stdin/mobile-like capture:

```bash
printf "Synthetic mobile project brief body." | python3 scripts/simulate_mobile_capture.py \
  --source mobile_web \
  --kind project_brief \
  --title "Synthetic mobile project brief" \
  --body-file -
python3 scripts/private_inbox_status.py
```

Expected:

- token value is not printed
- capture POST returns metadata only
- `private_inbox_status.py` shows total capture count
- private values are not printed in status output
- `companion/private/` remains untracked/ignored

## Browser Companion Bridge Checks

The browser bridge validates the approved local-only path from Launch UI to the private inbox. Use synthetic launch packets only.

Run:

```bash
python3 scripts/browser_bridge_smoke_check.py
```

Expected:

- unsafe bridge configs are rejected
- bridge is unavailable unless explicitly enabled
- CORS preflight accepts only the configured `http://127.0.0.1:<port>` origin
- wildcard, `localhost`, `null`, path-bearing, and bad-origin requests are rejected
- long-lived file token cannot be used as a pairing code
- one-time pairing code cannot be replayed
- browser session token can write one synthetic launch-style capture
- browser session token can write one synthetic assistant-style capture
- API responses do not echo title/body, file token, pairing code, or browser session token
- existing script bearer-token private inbox path remains compatible
- static smoke allows `fetch` only in `assets/js/companion-bridge.js`

Manual local bridge run:

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

Manual scenario:

- Open `http://127.0.0.1:4173/`.
- Open `Launch`.
- Check companion status.
- Enter the one-time pairing code from the local companion terminal. Do not record the code in evidence.
- Create or load a synthetic launch packet.
- Turn on `Redact Screen` before screenshots.
- Send Latest Packet.
- Confirm `scripts/private_inbox_status.py` reports an increased count without printing private values.

Assistant workspace ingress scenario:

- Open `Assistant`.
- Check companion status from `Workspace ingress`.
- Enter the one-time pairing code from the local companion terminal. Do not record the code in evidence.
- Add a synthetic manual input.
- Use `Send Latest Input` or the capture card's `Send to Workspace`.
- Confirm `scripts/private_inbox_status.py` reports an increased count without printing private values.
- Confirm browser response and toast do not show title/body, file token, pairing code, or browser session token.

## Phone Ingress Checks

Run:

```bash
python3 scripts/phone_ingress_smoke_check.py
```

Expected:

- non-loopback bind is rejected unless `--enable-phone-ingress` is set
- phone ingress requires browser bridge mode
- wildcard, public IP, `localhost`, and `0.0.0.0` origins are rejected
- private LAN origin shape is accepted
- companion can serve the PNH static UI in phone ingress mode
- one-time pairing still gates browser writes
- synthetic phone-style capture writes to private inbox
- API response does not echo synthetic title/body

Manual phone scenario:

```bash
python3 scripts/private_inbox_init.py
python3 scripts/phone_ingress_lan_info.py
python3 companion/server.py \
  --host 0.0.0.0 \
  --port 8765 \
  --enable-private-inbox \
  --enable-browser-bridge \
  --enable-phone-ingress \
  --allowed-origin http://<LAN_IP>:8765
```

- Open `http://<LAN_IP>:8765/` on the phone.
- Pair using the local WSL terminal code. Do not record the code in evidence.
- Send a synthetic Assistant input.
- Confirm `python3 scripts/private_inbox_status.py` reports an increased count without printing private values.

## Local Encrypted Vault Checks

Encrypted vault mode validates the minimum local path for supervisor-approved sensitive testing. Use synthetic data only in automated checks.

Run:

```bash
python3 scripts/encrypted_vault_smoke_check.py
```

Expected:

- encrypted vault mode is explicit and disabled by default
- `--enable-encrypted-vault` without private inbox fails closed
- missing required passphrase input fails closed
- prompt passphrase input fails closed on missing, short, or mismatched values
- simulated missing `cryptography` fails closed
- AES-GCM encrypted records are written to `encrypted_mobile_captures`
- wrong passphrase cannot decrypt
- tampered ciphertext cannot decrypt
- nonces are unique across synthetic captures
- API responses do not echo submitted title/body/payload private values
- default status/list output returns metadata-only redacted values
- synthetic private title/body/payload strings do not appear in SQLite DB bytes
- existing private inbox and browser bridge smoke checks still pass

Manual encrypted local run:

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

Supervisor notes:

- do not record the passphrase in chat, screenshots, docs, logs, or evidence

## Vault Secret Backend Checks

Use only synthetic secrets in automated validation.

Run:

```bash
python3 scripts/vault_secret_smoke_check.py
```

Expected:

- `windows-dpapi-file` smoke is skipped when PowerShell/DPAPI bridge is unavailable
- synthetic passphrase is stored as a DPAPI-protected file under Windows LocalAppData
- status reports provider/name/set flags only
- retrieve is validated in-process without printing the secret
- delete requires `DELETE_VAULT_SECRET`
- stdout/stderr do not include the synthetic secret value

Manual approved operator flow:

```bash
python3 scripts/vault_secret_store.py --provider windows-dpapi-file --prompt
python3 scripts/vault_secret_status.py --provider windows-dpapi-file
python3 companion/server.py \
  --host 127.0.0.1 \
  --port 8765 \
  --enable-private-inbox \
  --enable-encrypted-vault \
  --vault-passphrase-provider windows-dpapi-file
```

## Plaintext Migration Apply Checks

Use only synthetic data in automated validation.

Run:

```bash
python3 scripts/plaintext_migration_apply_smoke_check.py
```

Expected:

- dry-run does not mutate plaintext rows
- apply fails without an existing encrypted backup path
- apply requires `MIGRATE_PLAINTEXT_TO_ENCRYPTED`
- encrypted insert, plaintext delete, and audit event are transaction-scoped
- plaintext rows are encrypted and then removed
- encrypted records decrypt with the vault passphrase
- synthetic private values are absent from DB bytes after apply
- stdout/stderr do not include private values

Manual approved operator flow:

```bash
python3 scripts/plaintext_migration_audit.py --fail-on-plaintext
python3 scripts/encrypted_vault_backup.py \
  --out companion/private/backups/pnh-YYYYMMDD.pnhbackup \
  --prompt-vault-passphrase \
  --prompt-backup-passphrase \
  --confirm-backup-passphrase
python3 scripts/plaintext_migration_apply.py \
  --preflight-backup companion/private/backups/pnh-YYYYMMDD.pnhbackup \
  --confirm MIGRATE_PLAINTEXT_TO_ENCRYPTED \
  --prompt-vault-passphrase
```

## Redacted Browser QA Checks

Run:

```bash
python3 scripts/redacted_browser_qa_check.py
bash scripts/run_playwright_redacted_ui_qa.sh
```

Expected:

- screenshot-redaction CSS masks `data-sensitive="true"` values
- Launch UI contains redaction controls
- Assistant Workspace ingress UI contains redaction controls
- companion bridge keeps session token in memory only
- bridge does not use persistent browser token storage
- CSP remains loopback-scoped for companion access
- no real private values are required for this check
- Playwright runner uses existing local tooling only and reports blocked if Chromium is unavailable

Playwright redacted UI QA expected when Chromium is available:

- synthetic Assistant input is visible before redaction
- `Redact Screen` applies `body.screenshot-redaction`
- `data-sensitive="true"` elements are masked before screenshot capture
- localStorage/sessionStorage do not contain pairing/session token material
- desktop and mobile core views do not horizontally overflow
- screenshot artifact contains synthetic/redacted evidence only
- use environment variable mode only for non-interactive local runs where shell history and process evidence are controlled
- use `scripts/private_inbox_status.py` without `--include-decrypted` for evidence

Run Launch status sync browser QA when Chromium is available:

```bash
bash scripts/run_playwright_launch_status_sync_qa.sh
```

Expected:

- synthetic Launch packet can refresh metadata-only dispatch state
- `Confirm Mapping` stores GitHub/Discord IDs in browser-local Launch metadata
- `Confirm Task Status` stores worker/evidence metadata in browser-local Launch metadata
- Projects and Tasks receive a `dispatch-progress` task with `worker_done` status context
- no raw private command body, token, or secret value is required

## Local Encrypted Vault Lifecycle Checks

Run:

```bash
python3 scripts/encrypted_vault_backup_restore_smoke_check.py
python3 scripts/encrypted_vault_delete_smoke_check.py
python3 scripts/encrypted_vault_rotation_smoke_check.py
python3 scripts/plaintext_migration_audit_smoke_check.py
python3 scripts/passphrase_provider_smoke_check.py
```

Expected:

- encrypted backup file contains no synthetic private plaintext
- backup envelope declares schema, kind, algorithm, KDF, salt, nonce, and ciphertext
- correct backup passphrase restores encrypted captures into a fresh vault
- wrong backup passphrase fails closed
- tampered backup ciphertext fails closed
- unsupported backup algorithm/KDF/schema fails closed
- duplicate restore skips existing IDs unless replace is explicit
- delete requires `--confirm DELETE_CAPTURE`
- delete removes the encrypted row and redacted list entry
- delete audit stores no title/body/payload/private values
- rotation requires `--confirm ROTATE_VAULT_PASSPHRASE` and an existing encrypted backup path
- old passphrase cannot decrypt after rotation
- new passphrase can decrypt after rotation
- rotation audit stores no title/body/payload/private values
- plaintext migration audit detects plaintext row count without printing values
- plaintext migration audit does not mutate the DB

## Responsive Viewports

- `360x640`
- `390x844`
- `768x1024`
- `1366x768`
- `1920x1080`

확인 기준:

- 가로 스크롤 없음
- sidebar/mobile menu가 동작
- inspector panel이 화면 밖으로 고정되지 않음
- 버튼과 입력창이 겹치지 않음
- board columns가 모바일에서 단일 column으로 접힘

## Accessibility Baseline

- `Tab`으로 주요 버튼, navigation, search, forms에 접근 가능
- focus ring이 보임
- icon-only button에 `aria-label`이 있음
- 버튼은 `<button>` 사용
- 외부 링크는 `<a>` 사용
- 주요 화면 title이 heading으로 렌더링됨
- 색상만으로 상태를 구분하지 않음

## Deployment Checks

- GitHub Pages URL 접속 가능
- CSS/JS asset 404 없음
- localStorage 저장/복원 정상
- 새로고침 후 화면 유지
- secret/API key/client data 포함 없음
- 실제 개인정보/연락처/통화기록/녹음/transcript fixture 없음
- Workflow permissions가 최소 권한 유지
- companion prototype is not deployed as part of GitHub Pages
- Launch packet은 실제 Discord/GitHub/OpenClaw dispatch를 수행하지 않고 copy/export draft만 제공한다.
- local private inbox files are not included in public Pages artifacts

## Residual Risk

Playwright redacted UI QA runner exists, but execution depends on an installed Playwright Chromium browser binary.

Local companion UI integration is implemented only for explicit loopback bridge mode. Mobile LAN, public Pages remote sync, and real private data adapters remain separate phases.

Plaintext private inbox mode is not encrypted at rest. Routine high-sensitivity use should stay on encrypted vault mode and still requires adapter-specific privacy policy and successful redacted browser QA in the target runtime.
