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
- assistant demo fixture에 연락처, 전화번호, 이메일, 실제 일정, 녹음 transcript가 없는지 확인
