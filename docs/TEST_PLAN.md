# Test Plan

## Scope

정적 `Personal Notion Hub`의 기능, localStorage persistence, responsive layout, accessibility baseline, GitHub Pages artifact 배포를 검증한다.

## Functional Checks

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
- Workflow permissions가 최소 권한 유지

## Residual Risk

자동 브라우저 회귀 테스트는 아직 없다. UI 변경이 잦아지면 Playwright smoke test를 추가하는 것이 적절하다.
