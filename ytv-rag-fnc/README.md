# YouTube Viral Radar 인증·개인화 RAG Function

Supabase 인증과 Cosmos DB 기반 채널 개인화 RAG를 제공하는 Python 3.11 Azure Function입니다.

## 동작 흐름

```text
회원가입 채널명
→ channels.channel_title 정확 일치 검색(대소문자 무시)
→ 일치하면 channel_id 연결, 없으면 null

로그인 토큰
→ Supabase Auth로 토큰 확인 후 user_profiles에서 role 확인
→ 일반 사용자는 user_profiles.channel_id 범위만 Cosmos 조회
→ 질문을 10개 분석 카테고리로 분류하고 채널·영상·기간·지표 추출
→ 질문에 명시된 다른 채널은 DB 조회 전에 거부
→ 조회 근거만 Azure OpenAI에 전달
```

질문 분류는 Azure OpenAI Structured Outputs를 사용합니다. 분류 호출이 일시적으로 실패하면
규칙 기반 분류기로 대체하여 기존 채팅 전체가 중단되지 않게 합니다.

## 카테고리별 데이터 조회

분류 결과에 따라 필요한 컨테이너만 조회합니다.

```text
channel_growth               → channels, channel_snapshots, videos
video_list                   → 현재 채널의 videos 목록
video_performance            → videos, 선택 영상의 video_snapshots
prediction_score             → videos, 선택 영상의 predictions
shap_factors                 → videos, 선택 영상의 predictions
prediction_vs_actual         → videos, predictions, video_snapshots, labels
video_ranking                → videos, predictions, labels, video_snapshots
channel_baseline_comparison  → 선택 영상 자료 + 같은 채널 비교 자료
data_status                  → 채널 내 수집·예측·라벨 문서 존재 상태
glossary_model               → 운영 데이터 조회 없이 설명 지식만 검색
```

채널 단위 목록 조회도 항상 `channel_id` 조건을 사용합니다. 영상 단위 조회는 조회 후 영상의
`channel_id`가 로그인 사용자의 범위와 같은지 다시 검사합니다.

일반 회원가입은 요청 내용과 관계없이 항상 `role=user`로 저장됩니다. `channel_id=null`인 사용자는 로그인만 가능하고 채널 RAG를 사용할 수 없습니다.

## 엔드포인트

```text
GET  /api/health
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
GET  /api/channel/summary
GET  /api/channel/videos
GET  /api/dashboard/admin-overview
POST /api/chat
POST /api/rag/index
```

`auth/me`, 채널·관리자 조회 API와 `chat`은 `Authorization: Bearer <token>` 헤더가 필요합니다. 일반 사용자 채널 조회 범위는 요청 파라미터가 아니라 로그인 계정의 `channel_id`로 확정합니다. Function App 자체는 Function 인증 수준을 유지하며, 공개 웹에서는 Cloudflare Worker가 Function Key를 추가합니다.

연속 질문에서 `이 영상`, `그 영상`을 사용하려면 이전 `/api/chat` 응답의 `selected_video_id`를 다음 요청의 `context_video_id`로 전달합니다. 웹 화면은 이 값을 자동으로 이어서 보냅니다.

## Cosmos DB

```text
Account: ytv-cosdb
Database: ytv-db
```

사용자 계정과 RAG 문서는 Supabase를 사용하고, 채널 운영 데이터만 Cosmos DB를 사용합니다.

기존 데이터 컨테이너는 `channels`, `videos`, `video_snapshots`, `channel_snapshots`, `predictions`, `labels`를 사용합니다.

## 필수 환경 변수

```text
AZURE_OPENAI_ENDPOINT=https://ytv-azoai.openai.azure.com
AZURE_OPENAI_CHAT_DEPLOYMENT=ytv-predict-gpt
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=ytv-text-embedding
COSMOS_DB_ENDPOINT=https://ytv-cosdb.documents.azure.com:443/
COSMOS_DB_DATABASE=ytv-db
SUPABASE_URL=https://YOUR-PROJECT-REF.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_REPLACE_ME
SUPABASE_SECRET_KEY=sb_secret_REPLACE_ME
```

Supabase를 사용할 때 `JWT_SECRET`과 Cosmos의 `users`, `rag_documents` 컨테이너는 사용하지 않습니다. 먼저 Supabase SQL Editor에서 `infrastructure/supabase_migration.sql`을 실행한 뒤, 배포된 Function의 `POST /api/rag/index`를 한 번 호출해 내장 지식 문서를 임베딩과 함께 Supabase에 채웁니다.

Function 관리 ID에는 `Cognitive Services OpenAI User`와 Cosmos DB 데이터 읽기·쓰기 권한이 필요합니다.

## 관리자 생성

Supabase Auth에서 사용자를 만든 뒤 `user_profiles.role`을 SQL Editor에서 `admin`으로 변경합니다. Secret Key나 비밀번호는 코드와 Git에 저장하지 않습니다.

## 테스트와 배포

```powershell
python -m unittest discover -s tests -v
func azure functionapp publish ytv-rag-fnc --python
```

## 설명 한계

현재 `predictions.input_features`는 모델 입력값만 제공합니다. 영상별 SHAP 기여도가 저장되기 전에는 RAG가 각 피처의 점수 상승·하락 기여량을 단정하지 않습니다.

## Python 계산 및 검증 규칙

Cosmos DB 문서는 `shared/data_adapter.py`에서 공통 형식으로 변환한 뒤
`shared/metrics.py`에서 계산합니다. DB 필드명이 바뀌면 변환기만 수정하고 계산식은
유지하는 구조입니다.

- DB에 이미 계산된 값이 있으면 `source=stored`로 사용합니다.
- 저장된 값이 없고 원본 값이 충분하면 Python으로 계산하고 `source=calculated`로 표시합니다.
- 값이 부족하거나 0으로 나눠야 하면 임의로 0을 만들지 않고 `available=false`, `value=null`을 반환합니다.
- 모든 계산 결과에 `formula`, `formula_version`, `inputs`, `unit`을 함께 기록합니다.
- 현재 계산식 버전은 `v1`이며 계산 결과는 RAG 답변 컨텍스트에만 사용하고 Cosmos DB에는 쓰지 않습니다.

계산 대상은 채널 구독자·조회수 성장률, 영상 조회 증가율·참여율·시간당 조회수,
예측과 실제 점수의 오차, 채널 내 순위·중앙값 비교, 영상별 예측·라벨·스냅샷
데이터 충족률입니다.

## 임베딩 검색

Supabase `rag_documents` 테이블에는 피처·지표 설명과 Azure OpenAI 임베딩을 함께 저장합니다.
질문을 `ytv-text-embedding`으로 임베딩한 뒤 로그인 사용자의 `channel_id` 문서와
`GLOBAL` 공통 문서만 읽고, Python에서 코사인 유사도를 계산해 상위 5개 설명을
답변 근거로 사용합니다.

별도의 벡터 DB나 pgvector 인덱스 없이 Supabase에서 문서 목록만 읽어 Python으로
코사인 유사도를 계산합니다. 설명 문서가 수십 개뿐인 발표용 MVP에서는 이 방식이
단순하고 추가 인프라 비용이 없습니다. 검색 또는 인덱스가 실패하면 내장 단어 검색으로
자동 전환됩니다.

```text
질문 → 질문 임베딩
     → Supabase에서 GLOBAL + 로그인 채널 문서만 조회
     → Python 코사인 유사도 계산
     → 관련 설명 상위 5개
     → 계산 결과·채널 데이터와 함께 Azure OpenAI에 전달
```

`POST /api/rag/index`는 내장 설명 문서를 한 번의 배치 임베딩 요청으로 생성하고
Supabase에 upsert합니다. 설명 내용이나 버전을 변경한 뒤에만 다시 실행하면 됩니다.

## 최종 답변 생성

최종 Azure OpenAI 호출 전 `evidence_summary`를 생성해 질문 카테고리, 사용한 데이터
소스, 선택 영상, 계산 가능·불가능 지표, 임베딩 검색 문서를 기록합니다. API 응답에도
이 값을 포함하므로 어떤 근거가 답변에 사용됐는지 확인할 수 있습니다.

답변은 `직접 답변 → 사용한 수치와 데이터 근거 → 주의사항 또는 부족한 데이터` 순서를
따릅니다. 임베딩 유사도는 검색 관련도일 뿐 바이럴 점수가 아니며, 데이터에 없는 수치,
다른 채널 정보, SHAP 인과관계는 생성하지 않도록 제한합니다.
