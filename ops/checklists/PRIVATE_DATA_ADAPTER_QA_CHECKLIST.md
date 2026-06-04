# Personal Notion Hub Private Data Adapter QA Checklist

이 체크리스트는 Personal Notion Hub의 real-data adapter를 실제 비공개 데이터에 연결하기 전, 감독자가 승인 가능한 증거를 확인하기 위한 QA 기준이다. 모든 검증은 fixture, redacted sample, placeholder 값만 사용한다. 실제 토큰, 계정명, private page title, database ID, user content, client data는 기록하지 않는다.

## 1. Fixture-Only Validation

- [ ] Adapter validation run은 fixture dataset만 사용했다.
- [ ] Fixture에는 실제 Notion workspace, 실제 page/database ID, 실제 사용자 콘텐츠가 포함되지 않는다.
- [ ] Fixture naming은 `fixture-*`, `sample-*`, `redacted-*`처럼 테스트 데이터임을 명확히 드러낸다.
- [ ] Adapter가 fixture input을 읽고 expected normalized output을 생성하는지 확인했다.
- [ ] Empty, malformed, duplicated, archived, permission-denied 형태의 fixture case를 포함했다.
- [ ] Real-data adapter가 fixture mode와 real mode를 명확히 분리하며, fixture mode에서 외부 API 호출을 하지 않는다는 증거를 남겼다.

Evidence:

- Command/manual scenario:
- Artifact path:
- Result:

## 2. No-Secret / No-Private-Value Evidence

- [ ] QA logs, browser screenshots, terminal output, reports, commits에 secret/token/private value가 노출되지 않았다.
- [ ] Notion token, integration secret, session cookie, refresh token, API key, passphrase, encryption key는 어떤 evidence에도 포함하지 않았다.
- [ ] 실제 page title, person name, email, phone, address, private note body, client/project name은 redacted 또는 synthetic value로 대체했다.
- [ ] Error handling 검증 시 stack trace나 debug dump가 private payload를 그대로 출력하지 않는지 확인했다.
- [ ] Evidence에 남은 identifier는 test-only placeholder이거나 hash/truncated value이며 원문 복원이 불가능하다.
- [ ] Secret scan 또는 수동 검색으로 금지 값 패턴이 없는지 확인했다.

Evidence:

- Search/scan command:
- Checked artifacts:
- Result:

## 3. Local Encrypted Vault Path

- [ ] Real-data adapter output은 승인된 local encrypted vault 경로에만 저장되도록 설정되어 있다.
- [ ] Vault path는 placeholder 또는 local test path로만 기록했다. 예: `<LOCAL_ENCRYPTED_VAULT_PATH>/personal-notion-hub/adapter-fixtures/`.
- [ ] 실제 vault 절대 경로, 사용자 private folder name, mounted cloud path는 evidence에 노출하지 않았다.
- [ ] Vault directory가 unencrypted workspace, public web root, Git-tracked content, browser download folder로 설정되지 않았음을 확인했다.
- [ ] Adapter output, cache, temporary files, retry queue, export files가 동일한 encrypted boundary 안에 생성되는지 확인했다.
- [ ] Git status 또는 file listing으로 vault artifacts가 repository에 새로 추가되지 않았음을 확인했다.

Evidence:

- Vault path policy checked:
- Repo artifact check:
- Result:

## 4. Redacted Browser QA

- [ ] Browser QA는 fixture 또는 redacted adapter output만 사용했다.
- [ ] UI에 표시되는 workspace/page/database/content 값은 `REDACTED`, `Sample`, `Fixture`, 또는 synthetic label이다.
- [ ] Screenshot, video, trace, console log, network log에는 실제 private values가 없다.
- [ ] Network panel 또는 app log에서 request/response body가 저장될 경우 redaction이 적용되는지 확인했다.
- [ ] Error, empty state, sync failure, permission failure, rollback state에서도 private payload가 표시되지 않는다.
- [ ] Browser cache, localStorage, IndexedDB, downloaded files에 실제 private values가 남지 않는지 확인했다.

Evidence:

- Browser/device:
- Scenario:
- Screenshot/trace path:
- Result:

## 5. Rollback / Backup Checks

- [ ] Real-data adapter activation 전 현재 vault 상태의 backup 또는 restore point가 준비되어 있다.
- [ ] Backup evidence에는 실제 private content가 포함되지 않으며 backup location도 redacted 되어 있다.
- [ ] Failed adapter run 후 previous known-good fixture state로 되돌리는 절차를 검증했다.
- [ ] Adapter가 partially imported data, temporary files, lock files, failed queue를 정리하거나 격리하는지 확인했다.
- [ ] Rollback 후 UI, local index, vault metadata가 stale 또는 mixed state를 표시하지 않는지 확인했다.
- [ ] Backup/rollback 절차는 supervisor approval 없이 real private data를 삭제하거나 덮어쓰지 않는다.

Evidence:

- Backup/restore scenario:
- Rollback command/manual steps:
- Result:

## 6. Approval Gates

- [ ] Fixture-only validation passed.
- [ ] No-secret/no-private-value evidence passed.
- [ ] Local encrypted vault path check passed.
- [ ] Redacted browser QA passed.
- [ ] Rollback/backup checks passed.
- [ ] Security reviewer 또는 supervisor가 real-data adapter activation scope를 승인했다.
- [ ] Real Notion credential, real vault path, live adapter run은 별도 명시 승인 전까지 실행하지 않는다.

Approval Record:

- Reviewer:
- Date:
- Approved scope:
- Conditions:

## 7. Release-Readiness Verdict

Verdict: `Ready` / `Not Ready` / `Blocked`

Acceptance Matrix:

| ID | Criterion | Method | Expected | Actual | Result | Evidence Ref |
| --- | --- | --- | --- | --- | --- | --- |
| PNH-ADAPTER-QA-001 | Fixture-only adapter validation completes without external private data access. | Automated/manual fixture run | Fixture output matches expected result and no live API call occurs. |  |  |  |
| PNH-ADAPTER-QA-002 | Evidence contains no secret or private value. | Secret/private-value scan and manual review | No credential, token, private content, or real identifier appears. |  |  |  |
| PNH-ADAPTER-QA-003 | Adapter writes only inside approved encrypted local vault boundary. | Config/path review and artifact check | No adapter artifact is written to repo, public path, or unencrypted workspace. |  |  |  |
| PNH-ADAPTER-QA-004 | Browser QA remains redacted across normal and failure states. | Browser scenarios with redacted fixtures | UI, logs, screenshots, traces, and storage contain only redacted/synthetic values. |  |  |  |
| PNH-ADAPTER-QA-005 | Rollback and backup controls are ready before activation. | Backup/restore scenario review | Failed run can return to previous known-good state without private data loss. |  |  |  |
| PNH-ADAPTER-QA-006 | Approval gates are complete before any real-data run. | Supervisor review | Explicit approval exists for scope, credentials, vault path, and live execution. |  |  |  |

Residual QA Risk:

- [ ] No residual blocker.
- [ ] Residual risk documented below.

Notes:
