# Personal Notion Hub

개인 운영 정보를 한 화면에서 정리하는 정적 Notion-style web hub입니다.

## Purpose

- 프로젝트, task, note, routine, link를 한 브라우저에서 빠르게 관리합니다.
- 서버, API, backend, dependency install 없이 동작합니다.
- 데이터는 브라우저 `localStorage`에 저장됩니다.
- 전체 데이터는 JSON으로 export/import할 수 있습니다.

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

실제 사용 데이터는 사용자의 브라우저 `localStorage`에만 저장됩니다. 다른 기기와 자동 동기화되지 않습니다.

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
- `data/seed.json`: demo-only schema note
- `docs/TEST_PLAN.md`: manual QA plan
- `docs/SECURITY_NOTES.md`: public deployment and localStorage risk notes

## Limitations

- 서버 저장 없음
- 계정/auth 없음
- 다중 기기 sync 없음
- collaboration 없음
- localStorage 기반이므로 브라우저/기기 보안에 의존
