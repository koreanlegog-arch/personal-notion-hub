# Test Plan

## Scope

정적 `Personal Notion Hub`의 기능, localStorage persistence, responsive layout, accessibility baseline, GitHub Pages artifact 배포를 검증한다.

## Functional Checks

- Assistant 화면이 sidebar에서 열린다.
- Assistant input routes에 Slack, Email, SMS, KakaoTalk, Call, Voice memo, My memo, YouTube, Bible verse가 표시된다.
- Assistant manual input을 추가하면 inbox에 표시된다.
- Assistant demo fixture를 불러오면 demo capture와 suggestion이 표시된다.
- Assistant suggestion에서 `Create Task`를 누르면 기존 Tasks에 항목이 생성된다.
- Assistant suggestion에서 `Create Note`를 누르면 기존 Notes에 항목이 생성된다.
- Calendar/Slack-style draft는 실제 전송 없이 copy action만 제공된다.
- 오늘의 성경말씀 widget이 표시된다.
- Dashboard가 첫 화면으로 로드된다.
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

The companion prototype uses fake fixtures only. It must not handle real contacts, calls, schedules, recordings, transcripts, client data, or secrets.

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
- no vault, database, private backup, or runtime data file is created

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

## Residual Risk

자동 브라우저 회귀 테스트는 아직 없다. UI 변경이 잦아지면 Playwright smoke test를 추가하는 것이 적절하다.

Local companion UI integration is not implemented yet. Before adding browser `fetch`, define pairing/session token, CORS, CSP, and localhost origin policy.
