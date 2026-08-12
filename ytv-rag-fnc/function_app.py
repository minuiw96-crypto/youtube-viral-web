"""Azure Functions entry point for the personalized YouTube RAG service."""

import json
import logging

import azure.functions as func

from shared.auth_service import AuthError, AuthService, public_user
from shared.dashboard_service import DashboardAccessError, DashboardService
from shared.rag_service import ChannelAccessError, RagService
from shared.settings import Settings
from shared.user_repository import UserRepository


app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
LOGGER = logging.getLogger(__name__)


# 공통 JSON 응답을 생성하는 헬퍼 함수
def json_response(body: dict, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(body, ensure_ascii=False),
        status_code=status_code,
        mimetype="application/json",
        charset="utf-8",
        headers={"Cache-Control": "no-store"},
    )


# 요청 본문을 JSON 딕셔너리로 파싱하는 헬퍼 함수
def request_json(req: func.HttpRequest) -> dict:
    body = req.get_json()
    if not isinstance(body, dict):
        raise AuthError("올바른 JSON 요청이 아닙니다.")
    return body


# 인증 서비스 인스턴스를 생성하는 헬퍼 함수
def auth_service() -> AuthService:
    settings = Settings.from_environment()
    return AuthService(UserRepository(settings), settings)


# 요청 헤더의 인증 정보를 바탕으로 현재 사용자를 조회하는 헬퍼 함수
def authenticated_user(req: func.HttpRequest) -> dict:
    return auth_service().authenticate(req.headers.get("Authorization", ""))


# 서비스 상태를 확인하는 헬스 체크 엔드포인트
@app.function_name(name="health")
@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    settings = Settings.from_environment()
    missing = []
    if not settings.azure_openai_endpoint:
        missing.append("AZURE_OPENAI_ENDPOINT")
    if not settings.chat_deployment:
        missing.append("AZURE_OPENAI_CHAT_DEPLOYMENT")
    if not settings.cosmos_endpoint and not settings.cosmos_connection_string:
        missing.append("COSMOS_DB_ENDPOINT")
    if not settings.auth_ready:
        missing.append("JWT_SECRET")
    if missing:
        return json_response(
            {"status": "configuration_required", "missing": missing},
            status_code=503,
        )
    return json_response(
        {
            "status": "ok",
            "service": "ytv-rag-fnc",
            "features": {
                "chat": True,
                "cosmos": settings.cosmos_ready,
                "vector_search": settings.vector_search_ready,
                "vector_search_backend": "cosmos_documents_python_cosine",
                "embedding_model": settings.embedding_deployment or None,
                "authentication": settings.auth_ready,
            },
        }
    )


# 회원가입 요청을 처리하는 인증 엔드포인트
@app.function_name(name="auth_register")
@app.route(route="auth/register", methods=["POST"])
def auth_register(req: func.HttpRequest) -> func.HttpResponse:
    try:
        user = auth_service().register(request_json(req))
        return json_response(
            {
                "status": "created",
                "user": user,
                "message": (
                    "회원가입이 완료되었습니다."
                    if user.get("channel_id")
                    else "회원가입은 완료됐지만 등록된 채널을 찾지 못했습니다."
                ),
            },
            status_code=201,
        )
    except AuthError as exc:
        return json_response(
            {"error": str(exc), "code": exc.code}, status_code=exc.status_code
        )
    except ValueError:
        return json_response(
            {"error": "올바른 JSON 요청이 아닙니다.", "code": "INVALID_JSON"},
            status_code=400,
        )
    except Exception:
        LOGGER.exception("Registration failed.")
        return json_response(
            {"error": "회원가입 처리 중 오류가 발생했습니다."}, status_code=500
        )


# 로그인 요청을 처리하는 인증 엔드포인트
@app.function_name(name="auth_login")
@app.route(route="auth/login", methods=["POST"])
def auth_login(req: func.HttpRequest) -> func.HttpResponse:
    try:
        return json_response(auth_service().login(request_json(req)))
    except AuthError as exc:
        return json_response(
            {"error": str(exc), "code": exc.code}, status_code=exc.status_code
        )
    except ValueError:
        return json_response(
            {"error": "올바른 JSON 요청이 아닙니다.", "code": "INVALID_JSON"},
            status_code=400,
        )
    except Exception:
        LOGGER.exception("Login failed.")
        return json_response(
            {"error": "로그인 처리 중 오류가 발생했습니다."}, status_code=500
        )


# 현재 로그인한 사용자 정보를 조회하는 인증 엔드포인트
@app.function_name(name="auth_me")
@app.route(route="auth/me", methods=["GET"])
def auth_me(req: func.HttpRequest) -> func.HttpResponse:
    try:
        return json_response({"user": public_user(authenticated_user(req))})
    except AuthError as exc:
        return json_response(
            {"error": str(exc), "code": exc.code}, status_code=exc.status_code
        )


def _dashboard_response(callback) -> func.HttpResponse:
    try:
        return json_response(callback())
    except AuthError as exc:
        return json_response(
            {"error": str(exc), "code": exc.code}, status_code=exc.status_code
        )
    except DashboardAccessError as exc:
        return json_response(
            {"error": str(exc), "code": exc.code}, status_code=exc.status_code
        )
    except Exception:
        LOGGER.exception("Dashboard data request failed.")
        return json_response(
            {"error": "화면 데이터를 불러오는 중 오류가 발생했습니다."},
            status_code=500,
        )


@app.function_name(name="channel_summary")
@app.route(route="channel/summary", methods=["GET"])
def channel_summary(req: func.HttpRequest) -> func.HttpResponse:
    return _dashboard_response(
        lambda: DashboardService().channel_summary(
            authenticated_user(req), req.params.get("channel_id", "")
        )
    )


@app.function_name(name="channel_videos")
@app.route(route="channel/videos", methods=["GET"])
def channel_videos(req: func.HttpRequest) -> func.HttpResponse:
    return _dashboard_response(
        lambda: DashboardService().videos(
            authenticated_user(req), req.params.get("channel_id", "")
        )
    )


@app.function_name(name="video_metadata")
@app.route(route="video/metadata", methods=["GET"])
def video_metadata(req: func.HttpRequest) -> func.HttpResponse:
    def load_metadata() -> dict:
        authenticated_user(req)
        return DashboardService().video_metadata(req.params.get("video_id", ""))

    return _dashboard_response(load_metadata)


@app.function_name(name="admin_overview")
@app.route(route="dashboard/admin-overview", methods=["GET"])
def admin_overview(req: func.HttpRequest) -> func.HttpResponse:
    return _dashboard_response(
        lambda: DashboardService().admin_overview(authenticated_user(req))
    )


# 사용자 질문에 대한 RAG 기반 답변을 생성하는 채팅 엔드포인트
@app.function_name(name="chat")
@app.route(route="chat", methods=["POST"])
def chat(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = request_json(req)
        question = body.get("question", "") if isinstance(body, dict) else ""
        if not isinstance(question, str) or not question.strip():
            return json_response({"error": "질문을 입력해 주세요."}, status_code=400)
        if len(question) > 8000:
            return json_response({"error": "질문이 너무 깁니다."}, status_code=400)

        return json_response(RagService().answer(body, authenticated_user(req)))
    except AuthError as exc:
        return json_response(
            {"error": str(exc), "code": exc.code}, status_code=exc.status_code
        )
    except ChannelAccessError as exc:
        return json_response(
            {"error": str(exc), "code": exc.code}, status_code=403
        )
    except ValueError as exc:
        return json_response({"error": str(exc) or "올바른 JSON 요청이 아닙니다."}, status_code=400)
    except Exception:
        LOGGER.exception("Chat request failed.")
        return json_response(
            {"error": "답변 생성 중 오류가 발생했습니다."},
            status_code=502,
        )


# RAG 지식베이스를 색인하는 엔드포인트
@app.function_name(name="rag_index")
@app.route(route="rag/index", methods=["POST"])
def rag_index(req: func.HttpRequest) -> func.HttpResponse:
    """Embed and upsert the built-in feature dictionary into Cosmos DB (ytv-app-db)."""
    try:
        return json_response(RagService().index_seed_knowledge(), status_code=200)
    except Exception:
        LOGGER.exception("RAG seed indexing failed.")
        return json_response(
            {"error": "RAG 문서 색인 중 오류가 발생했습니다."},
            status_code=502,
        )
