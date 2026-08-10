# CLAUDE.md — youtube-viral-web

## 1. 절대규칙 (Absolute Rules)

- `ytv-rag-fnc`(백엔드) 코드는 **절대 수정하지 않는다.** 이 문서의 API 명세를 그대로 따르는 연동만 한다.
- 디자인/컴포넌트/페이지 구조는 참고할 기존 프론트엔드가 **없다고 간주**하고 새로 설계한다. 과거 프로젝트 구조를 베끼지 않는다.
- 색상 아이덴티티만 고정: **라이트 모드 = 흰색 배경 + 빨강 accent**, **다크 모드 = 검은색 배경 + 빨강 accent**. 그 외 시각 디자인(레이아웃, 컴포넌트, 타이포그래피 등)은 자유롭게 새로 설계한다.
- 라우팅은 **react-router**를 사용한다 (직접 구현한 history 기반 라우팅 금지).
- Azure Function key 등 민감 정보는 브라우저에 절대 노출하지 않는다 — 반드시 서버사이드(프록시)를 경유한다.
- `POST /api/rag/index` 같은 비용이 발생하는 백엔드 호출은 사용자 승인 없이 실행하지 않는다.
- 이 서비스는 **로컬호스트가 아니라 실제 웹에 배포되어 실시간으로 운영되는 상태**임을 항상 전제한다 — "로컬에서만 동작하면 됨" 같은 가정으로 작업하지 않는다.
- 의미 없는 장식용 문구/안내 카피, 텅 빈 느낌을 채우기 위한 컨테이너·라벨을 넣지 않는다. 정보를 보여줄 거면 크고 명확하게, 아니면 아예 넣지 않는다.

## 2. 아키텍처

- **프론트엔드**: Vite + React 19 (JavaScript, TypeScript 아님), react-router.
- **백엔드**: 별도 저장소 `C:\Users\heyyo\Documents\MS_1_project\ytv-rag-fnc` (Python Azure Function) — 이 프로젝트에서 관리하지 않으며, API만 소비한다.
- **인증 흐름**:
  1. `POST /api/auth/login` → `{access_token, user}` 수신
  2. 이후 모든 인증 필요 요청에 `Authorization: Bearer <access_token>` 헤더 첨부
  3. 서버는 PBKDF2 해시 + HMAC 서명 토큰을 사용 (커스텀 구현이지만 구조는 표준 JWT와 동일: header.payload.signature, `exp` 포함)
- **배포 인프라 제약**: Azure Function이 Function-level auth(함수 키 필요)이므로 브라우저가 직접 호출하면 안 된다. 프록시(예: Cloudflare Worker)가 함수 키를 서버사이드에서 주입해 중계하는 구조가 필요하다. 프론트엔드는 `/api/*` 상대경로로만 호출하고, 프록시가 실제 Azure Function URL + 키로 전달하는 패턴을 전제로 설계한다.
- **CORS**: 백엔드 코드상 명시적 설정 없음 — 로컬 개발 시 문제가 될 수 있어 프록시/로컬 설정이 필요할 수 있다.
- **에셋**: 로고는 `src/assets/logo.png` (투명 배경, 검정+빨강 텍스트에 흰색 테두리 처리되어 있어 라이트/다크 배경 모두에서 사용 가능). 랜딩 히어로 배경 이미지는 `src/assets/hero-bg.png`.

## 3. 빌드/테스트 명령어

```bash
npm run dev       # Vite 개발 서버
npm run build     # 프로덕션 빌드
npm run preview   # 빌드 결과 로컬 미리보기
npm run lint      # ESLint (flat config, react-hooks/react-refresh 플러그인 포함)
```

테스트 프레임워크는 아직 설정되어 있지 않다 (필요 시 별도 논의 후 추가).

## 4. 도메인 컨텍스트

**서비스 개요**: 먹방 유튜브 채널의 성과를 분석/예측해 보여주는 프레젠테이션용 MVP.

**사용자 유형**:
- 일반 사용자 — 자신의 `channel_id`에만 스코프됨
- 관리자 — 전체 채널/사용자 데이터 조회 가능

**핵심 도메인 모델**: `channels`, `videos`, `channel_snapshots` / `video_snapshots`, `predictions`, `labels`, `viral_score`, `performance_multiplier`.

**백엔드 API 전체 명세** (조사 시점 기준 — 실제 연동 전 `ytv-rag-fnc`에서 변경 여부 재확인 권장):

| Method | Path | 인증 | 설명 |
|---|---|---|---|
| GET | `/api/health` | 불필요 | 헬스체크. `{status, service, features}` 반환 |
| POST | `/api/auth/register` | 불필요 | body `{email, password, password_confirm, name, channel_name}`. `channel_name`은 Cosmos `channels` 컨테이너의 실제 채널명과 매칭되어야 함. 에러코드: `EMAIL_EXISTS`(409), `WEAK_PASSWORD`(400), `INVALID_EMAIL`(400) |
| POST | `/api/auth/login` | 불필요 | body `{email, password}` → `{access_token, user}`. 에러: `INVALID_CREDENTIALS`(401), `ACCOUNT_DISABLED`(403) |
| GET | `/api/auth/me` | 필요 | 현재 로그인 유저 정보 반환 |
| GET | `/api/channel/summary?channel_id=` | 필요 | 일반 유저는 자기 채널로 자동 스코프, 관리자는 `channel_id` 필수. 구독자/조회수/성장률/참여도 + `recent_videos`(상위 8개) |
| GET | `/api/channel/videos?channel_id=` | 필요 | 채널의 영상별 `viral_score`, `performance_multiplier`, `rank`, `label_score` 등 |
| GET | `/api/dashboard/admin-overview` | 필요 (관리자 전용) | 전체 통계, 카테고리, 파이프라인 상태, 유저 목록. 비관리자는 `ADMIN_REQUIRED`(403) |
| POST | `/api/chat` | 필요 | RAG 질의응답. body `{question, channel_id?, video_id?, context_video_id?}` (관리자는 `channel_id` 필수, 일반 유저는 자기 채널로 자동 스코프). 응답의 `selected_video_id`를 다음 요청의 `context_video_id`로 넘기면 "이 영상", "그 영상" 같은 follow-up 질문을 지원. `question`은 최대 8000자 |
| POST | `/api/rag/index` | 필요 | 1회성 지식베이스 인덱싱. **Azure OpenAI 임베딩 비용 발생 — 실행 전 반드시 사용자 승인 필요.** 관리자용 시딩 호출 |

**미확정 사항**: "predict" 관련 기능은 `ytv-rag-fnc`에서 대응 엔드포인트가 확인되지 않았다. 별도 Azure Function App(다른 base URL/key)일 가능성이 있으므로, 예측 기능을 연동하기 전 백엔드 담당자/저장소를 다시 확인해야 한다.

## 5. 코딩 컨벤션

- 함수형 컴포넌트 + hooks 사용, JavaScript(TS 아님).
- 라우팅: react-router 표준 패턴(`createBrowserRouter` 등) 사용. 보호 라우트는 react-router의 loader 또는 wrapper 컴포넌트 관례로 구현.
- API 호출은 공용 client 모듈로 일원화 — fetch 래퍼에서 Bearer 토큰 자동 첨부, 백엔드의 `{error, code}` 응답 형태를 일관되게 파싱/에러 처리하는 패턴을 권장.
- 테마: CSS custom properties + `data-theme` 속성으로 라이트/다크 전환. 색상 값은 절대규칙의 흰색+빨강(라이트) / 검은색+빨강(다크)만 고정, 나머지 토큰(spacing, radius, font 등)은 자유 설계.
- 민감한 값(Function key 등)은 `.env`/클라이언트 번들에 넣지 않고 서버사이드 프록시에서만 다룬다.

## 6. UI/UX 원칙 (팀 피드백 반영, 2026-08-10 팀 회의 기준)

이전 버전에 대한 팀 리뷰에서 나온 지적들을 일반화한 원칙. 이전 버전 자체를 참고하라는 뜻이 아니라, 같은 실수를 반복하지 않기 위한 규칙으로 취급한다.

- **폰트 통일**: 한글/영문 폰트가 서로 다른 스타일로 섞여 어색해지지 않도록, 프로젝트 전체에 하나의 폰트 패밀리(한/영 모두 커버)를 지정해 통일한다.
- **모서리(radius) 통일**: 컴포넌트마다 제각각의 radius를 쓰지 말고, 하나의 radius 토큰 스케일을 정해 전체에 일관 적용한다. 로고가 검정/빨강의 각진 느낌이라, 지나치게 둥근(pill) 처리보다는 절제된 각진 스타일 쪽을 기본값으로 우선 검토한다 (확정 요구사항은 아니고, 가능하면 반영).
- **장식용 카피/컨테이너 금지**: "카테고리 오버뷰", "파워 BI" 같은 의미 없는 라벨이나 존재감만 채우는 문구를 넣지 않는다. 채널명·날짜 등 정보를 보여줄 거면 크고 밝게 확실히, 아니면 그냥 삭제한다. 촌스럽거나 맥락 없는 카피("오늘의 신", "다시 신호를 확인하세요" 류)는 쓰지 않는다.
- **표기 정확성**: "바이럴(viral)"을 정확히 쓴다 — "바이탈" 오타 금지.
- **랭킹/순위 표현**: TOP N 같은 랭킹은 가로 나열보다 세로 랭킹 형태를 우선 고려하고, 순위별로 금/은/동 등 색상 위계를 줘서 한눈에 구분되게 한다.
- **점수 표현**: 점수는 100점 만점 + 소수점 1자리로 통일하고, 게이지 등 시각화와 함께 퀀타일 기반 등급 텍스트(예: 굿/베리굿/배드/베리배드)를 같이 보여준다.
- **입력 흐름 단순화**: 입력 → 로딩 → 결과만 표시, 이렇게 화면 단계를 단순하게 끊어가고, 결과 화면에는 재시도를 위한 "처음으로" 버튼을 둔다. 입력 필드는 중앙 정렬, 불필요한 안내문구는 넣지 않는다. 카테고리처럼 항목이 늘어날 수 있는 선택지는 드롭다운으로 처리한다.
- **로그인/회원가입 화면**: 좌측에 큰 텍스트/설명 블록을 두지 않는다. 로고를 크고 중앙에 반응형으로 배치하고, 그 아래 슬로건 한 줄만 남긴다. 배경은 색이 뚝 끊기는 하드한 경계 없이 화면 전체가 자연스럽게 하나로 이어지도록 만든다.
- **카드/썸네일 배색**: 브랜드 팔레트(검정/흰색+빨강) 밖의 어울리지 않는 배색(흰 배경에 초록 등)을 피하고, 팔레트 안에서 정리한다.
