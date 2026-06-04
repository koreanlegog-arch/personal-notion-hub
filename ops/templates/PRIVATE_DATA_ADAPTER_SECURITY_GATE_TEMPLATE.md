# Private Data Adapter Security Gate Template

이 문서는 `Personal_Notion_Hub`에서 실제 private data를 읽거나 동기화하는 adapter를 승인하기 전 supervisor가 검토할 security gate template이다.

실제 private data, token, credential, account identifier, 원문 payload를 이 문서에 기록하지 않는다. 필요한 경우 placeholder나 분류명만 사용한다.

## Adapter Summary

| Field | Entry |
| --- | --- |
| Adapter Name |  |
| Data Source |  |
| Data Types |  |
| Sensitivity Classification | Public / Internal / Private / Restricted 중 선택 |
| Owner |  |
| Review Date |  |
| Reviewer |  |

## Consent And Legal Review

| Field | Entry |
| --- | --- |
| Consent/Legal Notes | 데이터 사용 권한, 동의 범위, 보관 제한, 삭제 요청 처리 기준을 요약 |
| Data Subject Scope | 개인, 가족, 고객, 제3자 등 범위만 기입 |
| Prohibited Data | 수집 또는 저장하면 안 되는 데이터 유형 기입 |

## Data Handling Requirements

| Field | Required Decision |
| --- | --- |
| Storage Mode | No storage / Approved local encrypted vault / Disabled 중 선택 |
| Encryption Requirement | 저장 시 암호화 필요 여부와 적용 위치 기입 |
| Redaction Requirement | UI, logs, exports, reports에서 masking/redaction 대상 기입 |
| Logging Prohibitions | log에 남기면 안 되는 필드, payload, identifier 기입 |
| External Services | 사용 여부, 서비스명, 전송 데이터 범위, 승인 상태 기입 |

`Local cache`, `Local database`, `Export file`은 기본 승인 대상이 아니다. 필요한 경우 approved local encrypted vault boundary 내부에서만 허용하거나 별도 supervisor/security approval을 받아야 한다.

## Approval Gates

아래 항목이 모두 충족되기 전에는 real-data adapter를 활성화하지 않는다.

| Gate | Status | Evidence |
| --- | --- | --- |
| Data source 접근 권한 확인 | Pending / Approved / Blocked |  |
| Consent/Legal Notes 검토 완료 | Pending / Approved / Blocked |  |
| Storage Mode 승인 | Pending / Approved / Blocked |  |
| Encryption Requirement 충족 | Pending / Approved / Blocked |  |
| Redaction Requirement 충족 | Pending / Approved / Blocked |  |
| Logging Prohibitions 검토 완료 | Pending / Approved / Blocked |  |
| External Services 승인 | Pending / Approved / Blocked / N/A |  |
| Validation Plan 통과 | Pending / Approved / Blocked |  |
| Rollback Plan 확인 | Pending / Approved / Blocked |  |

## Validation Plan

adapter 활성화 전 다음 검증을 기록한다.

- Dry-run command:
- Test dataset source: synthetic / fixture / redacted sample 중 선택
- Expected records handled:
- Sensitive field redaction check:
- Storage location check:
- Encryption check:
- Logging check:
- External transfer check:
- Failure handling check:
- Reviewer sign-off:

## Rollback Plan

- Disable switch or config path:
- Cache/database cleanup steps:
- Generated file cleanup steps:
- External service revocation steps:
- User-facing recovery note:
- Rollback verification command:

## Residual Risks

승인 후에도 남는 위험과 감수 사유를 간결히 기록한다.

| Risk | Impact | Mitigation | Accepted By |
| --- | --- | --- | --- |
|  |  |  |  |

## Final Approval

| Field | Entry |
| --- | --- |
| Approval Decision | Approved / Rejected / Needs Changes |
| Approval Gates Complete | Yes / No |
| Approved By |  |
| Approval Date |  |
| Notes |  |
