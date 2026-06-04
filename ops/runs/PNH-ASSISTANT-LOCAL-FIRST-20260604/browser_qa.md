# Browser QA Evidence - PNH Assistant Local-First Readiness

Run ID: `PNH-ASSISTANT-LOCAL-FIRST-20260604`
Date: 2026-06-04
Scope: static web shell and Assistant MVP browser-facing readiness

## 1. QA Mode

Automated browser screenshot/viewport QA: blocked.

Reason:

- No Playwright project/config is present.
- No browser binary was available in WSL for `google-chrome`, `chromium`, `chromium-browser`, `firefox`, or `microsoft-edge`.
- No new browser tooling was installed because dependency/tool installation requires separate approval.

Substitute checks performed:

- static contract smoke check
- local loopback HTTP server asset checks
- CSS responsive/media-query static review
- manual scenario matrix for future browser run

## 2. Commands Run

```bash
python3 scripts/smoke_check.py
python3 -m http.server 4173 --bind 127.0.0.1
curl -I --max-time 5 http://127.0.0.1:4173/
curl -I --max-time 5 http://127.0.0.1:4173/assets/css/styles.css
curl -I --max-time 5 http://127.0.0.1:4173/assets/js/app.js
curl -I --max-time 5 http://127.0.0.1:4173/assets/js/assistant-storage.js
curl -I --max-time 5 http://127.0.0.1:4173/assets/js/assistant-import.js
curl -I --max-time 5 http://127.0.0.1:4173/assets/js/assistant-rules.js
curl -I --max-time 5 http://127.0.0.1:4173/favicon.ico
curl -I --max-time 5 http://127.0.0.1:4173/assets/img/workspace-visual.png
```

## 3. Results

| Check | Result | Evidence |
| --- | --- | --- |
| Static smoke | Pass | `smoke_check_pass=true` |
| Root HTML | Pass | HTTP `200 OK`, `Content-type: text/html` |
| CSS asset | Pass | HTTP `200 OK`, `Content-type: text/css` |
| Main app JS | Pass | HTTP `200 OK`, `Content-type: text/javascript` |
| Assistant storage JS | Pass | HTTP `200 OK`, `Content-type: text/javascript` |
| Assistant import JS | Pass | HTTP `200 OK`, `Content-type: text/javascript` |
| Assistant rules JS | Pass | HTTP `200 OK`, `Content-type: text/javascript` |
| Favicon | Pass | HTTP `200 OK` |
| Workspace image | Pass | HTTP `200 OK`, `Content-type: image/png` |

## 4. Static UI Findings

- `index.html` includes a Content Security Policy meta tag.
- Required CSS/JS/image assets exist and load over loopback static server.
- `scripts/smoke_check.py` verifies no inline event handlers and checks forbidden JS tokens such as `innerHTML`, `fetch(`, and `XMLHttpRequest(`.
- `assets/css/styles.css` includes responsive breakpoints at `1180px`, `860px`, and `560px`.
- Browser storage model remains local: `localStorage` for hub state and `IndexedDB` for assistant captures.

## 5. Viewport Matrix

| Viewport | Automated result | Current status |
| --- | --- | --- |
| `360x640` | Not run | Manual/browser tooling required |
| `390x844` | Not run | Manual/browser tooling required |
| `768x1024` | Not run | Manual/browser tooling required |
| `1366x768` | Not run | Manual/browser tooling required |
| `1920x1080` | Not run | Manual/browser tooling required |

## 6. Manual Scenarios For Next Browser Run

Run these after either opening `index.html` directly or serving with `python3 -m http.server 4173 --bind 127.0.0.1`:

- Dashboard loads without fatal console errors.
- Assistant navigation opens the Assistant view.
- `Load demo fixture` creates demo assistant captures and suggestions.
- Manual Assistant input creates a capture without external network calls.
- `Create Task` from a suggestion adds a task in Tasks.
- `Create Note` from a suggestion adds a note in Notes.
- Today's Bible verse widget is visible.
- Export works and does not include real private data in repository artifacts.
- Import rejects invalid schema.
- Mobile menu works at narrow viewport.
- Inspector panel does not overflow off-screen.

## 7. Residual Risk

- No screenshot evidence was produced.
- No viewport automation was run.
- No deployed GitHub Pages endpoint was checked.
- Playwright or equivalent browser QA should be added later only after explicit dependency/tooling approval.
