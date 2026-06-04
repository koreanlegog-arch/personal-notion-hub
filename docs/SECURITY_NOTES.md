# Security Notes

## Public Deployment Assumption

이 프로젝트는 GitHub Pages public artifact로 노출될 수 있다는 전제로 설계한다.

Repository와 배포 artifact에는 demo data만 포함한다.

금지:

- secret
- API key
- token
- credential
- client data
- private internal URL
- 실제 개인 업무 메모

## localStorage

앱 데이터는 브라우저 `localStorage`에 저장된다.

주의:

- 암호화 저장소가 아니다.
- 같은 origin의 JavaScript가 접근할 수 있다.
- 기기/브라우저를 바꾸면 자동 동기화되지 않는다.
- 민감 정보 저장에 적합하지 않다.

## IndexedDB Assistant Store

Assistant MVP는 browser `IndexedDB`에 manual capture를 저장한다.

주의:

- 암호화 저장소가 아니다.
- 같은 origin의 JavaScript가 접근할 수 있다.
- public GitHub Pages artifact에는 demo 코드만 포함되어야 한다.
- 실제 연락처, 통화기록, 문자, 녹음, transcript, 일정, client data, token은 저장소와 evidence에 금지한다.

허용:

- 사용자가 브라우저에서 직접 입력한 demo/manual capture
- local rule-based suggestion
- copyable summary/calendar draft

금지:

- Slack, Google, Notion, Kakao, phone, email API 연결
- OAuth/token/API key 저장
- 녹음파일 자동 수집 또는 cloud transcription
- 실제 개인 데이터 fixture commit

## Long-Term Private Data Direction

민감 개인정보, 통화 내용, 녹음 transcript, 일정, 연락처를 장기적으로 다루려면 browser storage가 아니라 local companion과 encrypted local vault를 사용한다.

Default stance:

- public GitHub Pages는 demo shell only
- 실제 private data는 repo, Pages artifact, logs, screenshots, evidence에 금지
- cloud sync는 기본 금지
- real-data adapter는 별도 승인 전 금지
- 평문 JSON export는 민감 모드에서 금지
- clipboard/screenshot은 민감 모드에서 별도 redaction/warning 정책 필요

See:

- `docs/LOCAL_COMPANION_ARCHITECTURE.md`
- `docs/PRIVATE_DATA_POLICY.md`
- `docs/adr-0001-local-companion-vault.md`

## Launch Packet Boundary

The Launch MVP creates local dispatch packets and copyable drafts only.

Allowed:

- local project brief entry
- local dispatch packet generation
- local Project/Task creation
- clipboard copy of Discord/GitHub drafts
- JSON export controlled by the user

Forbidden before separate approval:

- automatic Discord message send
- automatic GitHub issue creation
- OpenClaw command execution
- external API call
- token storage
- private client data in public launch packet
- browser-to-companion `fetch` integration outside the approved local bridge mode

If launch briefs include sensitive business, client, or private information, they must be treated like private data and kept out of public repo artifacts, screenshots, logs, and QA evidence.

## Local Companion Prototype Security Boundary

The companion keeps fixture-only preview mode, adds authenticated plaintext private inbox mode, and now supports explicit encrypted vault mode for sensitive local captures.

Preview mode allowed:

- bind to `127.0.0.1`
- health/schema/import-preview checks
- fake fixture payloads
- validation errors, counts, and sanitized summaries
- no writes

Private inbox mode allowed:

- local bearer-token authenticated write/read endpoints
- workspace-local ignored SQLite inbox
- synthetic or supervisor-approved private capture testing
- metadata-only API responses
- redacted status output
- browser bridge only when explicitly enabled with exact `http://127.0.0.1:<port>` origin
- short-lived one-time pairing code issued in local terminal only
- short-lived browser session token held in JS memory only

Encrypted vault mode allowed:

- explicit `--enable-encrypted-vault` startup only
- passphrase loaded from no-echo local prompt or a configured environment variable name
- prompt confirmation available for initialization and backup creation
- keychain readiness audit reports capability flags without storing or printing secrets
- `windows-dpapi-file` stores a DPAPI-protected passphrase blob for approved Windows + WSL use
- passphrase rotation requires explicit confirmation and an existing encrypted backup path
- plaintext migration apply requires explicit confirmation and an existing encrypted backup path
- private title/body/payload encryption before SQLite persistence
- AES-GCM authenticated encryption through installed `cryptography`
- PBKDF2-HMAC-SHA256 key derivation with per-vault salt
- metadata-only API responses and redacted default status output
- synthetic or supervisor-approved sensitive local testing

Forbidden in all modes:

- real contacts, phone numbers, emails, call logs, schedules, recordings, transcripts, client data, tokens, credentials, or private notes in plaintext mode, public artifacts, logs, screenshots, evidence, or tracked files
- request body logging
- external API calls
- browser UI `fetch` integration outside the approved bridge module
- wildcard CORS
- non-loopback bind address
- committed private inbox files
- persistent browser storage of token, pairing code, or session token
- passing vault passphrases as CLI values or printing them in evidence

Current private inbox protections:

- token file lives in `companion/private/auth_token`
- token value must never be printed
- database lives in `companion/private/pnh_private_inbox.sqlite`
- both paths are ignored by Git
- custom DB/token paths outside `companion/private/` are rejected by default
- simulated mobile capture only sends to `http://127.0.0.1:<port>` and rejects redirects
- status command is read-only and does not create a missing database
- scripts use best-effort restrictive file permissions
- responses do not echo submitted title/body
- browser bridge is disabled by default and requires `--enable-browser-bridge`
- browser bridge startup requires `--enable-private-inbox`
- `--allowed-origin` accepts only exact `http://127.0.0.1:<port>` origins
- CSP restricts browser connection to `connect-src 'self' http://127.0.0.1:8765`
- Launch UI provides a screenshot redaction toggle for sensitive launch text and pairing input
- encrypted vault mode stores private fields in `encrypted_mobile_captures`
- encrypted vault mode fails closed if `cryptography` or required passphrase input is missing
- encrypted vault smoke test checks wrong passphrase rejection, tamper rejection, redacted responses, and plaintext absence in SQLite bytes
- passphrase provider smoke test checks env/prompt behavior, confirmation mismatch rejection, short passphrase rejection, and no secret output
- DPAPI file backend smoke test checks synthetic store/status/retrieve/delete without printing the secret
- rotation smoke test checks backup gate, old-passphrase rejection after rotation, new-passphrase decrypt, audit event, and no secret output
- plaintext migration apply smoke test checks backup gate, confirmation gate, plaintext row deletion, encrypted readback, and no private value output
- redacted browser QA check validates screenshot masking contracts and token persistence boundaries

Residual risks:

- plaintext private inbox mode is not encrypted at rest and should not be used for routine high-sensitivity storage
- token file security depends on the local OS account
- encrypted vault passphrase recovery is not possible without the passphrase or a valid operator-managed backup/recovery copy
- `windows-dpapi-file` is tied to the current Windows user/machine and is not a cross-device recovery mechanism
- existing plaintext private inbox rows are not migrated automatically; apply requires backup and explicit confirmation
- encrypted capture backup/restore/delete/rotation exists, but forensic secure erase and encrypted attachment/audio export are not implemented
- browser session token is memory-only, so reload requires re-pairing
- screenshot redaction is best-effort UI masking, not a substitute for fake-fixture QA

Encrypted vault mode with prompt-first passphrase handling, optional
`windows-dpapi-file` storage, backup-gated rotation, backup-gated plaintext
migration apply, and redacted browser QA static checks is the minimum local path
for supervisor-approved sensitive testing. Adapter-specific data policies,
passphrase recovery drills, real browser screenshot evidence, and packaged
operator UX remain release blockers before routine high-sensitivity operation
or distribution.

## XSS Mitigation

- 사용자 입력은 text node로 렌더링한다.
- Markdown/HTML preview 기능은 초기 범위에서 제외한다.
- 외부 링크는 `rel="noopener noreferrer"`를 사용한다.
- 외부 링크 URL은 `http:`와 `https:`만 허용한다.
- JS/CSS는 별도 파일로 분리한다.
- `index.html`에는 meta CSP를 둔다.

Residual risk:

- meta CSP는 서버 header CSP보다 약하다.
- 사용자가 악성 URL을 직접 입력하면 외부 링크 클릭 시 위험이 남는다.

## GitHub Actions

Workflow는 dependency install 없이 static artifact만 업로드한다.

권한:

```yaml
permissions:
  contents: read
  pages: write
  id-token: write
```

외부 action은 공식 GitHub Pages actions만 사용한다.

## Pre-Publish Gate

공개 배포 전 확인:

- `rg -n "token|secret|api[_-]?key|credential|password" .`
- `git status --short`
- artifact에 local backup JSON이 포함되지 않는지 확인
- Pages URL에서 실제 개인 데이터가 없는지 확인
- `assets/js/assistant-*.js`에 `fetch`, OAuth, token flow, external API가 없는지 확인
- `assets/js/companion-bridge.js` 외의 browser JS에 `fetch`가 없는지 확인
- assistant demo fixture에 연락처, 전화번호, 이메일, 실제 일정, 녹음 transcript가 없는지 확인
- companion fixtures contain fake data only
- no `*.vault`, `*.sqlite`, `*.db`, `companion/private/`, `companion/runtime/`, or `companion/logs/` artifact is committed
