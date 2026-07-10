import os
from uuid import uuid4

from flask import Flask, jsonify, request

try:
    from flask_cors import CORS
except ImportError:
    def CORS(app, resources=None):
        return app

from src.schema import ValidationError
from src.service import MedicalAIService


def create_app(service: MedicalAIService | None = None) -> Flask:
    app = Flask(__name__)
    app.json.ensure_ascii = False
    app.config["MAX_CONTENT_LENGTH"] = 1_048_576
    CORS(
        app,
        resources={
            r"/nlp/*": {
                "origins": [
                    "http://localhost:3000",
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                ]
            }
        },
    )
    ai_service = service or MedicalAIService()

    @app.after_request
    def ensure_json_utf8(response):
        if response.mimetype == "application/json":
            response.headers["Content-Type"] = "application/json; charset=utf-8"
        return response

    @app.get("/health")
    def health():
        return jsonify(ai_service.status)

    @app.get("/metadata")
    def metadata():
        return jsonify(ai_service.metadata)

    @app.post("/nlp/analyze")
    def analyze():
        try:
            payload = request.get_json(silent=False)
            result = ai_service.analyze(payload)
            return jsonify(result.to_dict())
        except ValidationError as error:
            return jsonify({"code": 400, "message": str(error), "data": None}), 400
        except Exception:
            app.logger.exception("AI analysis failed")
            return (
                jsonify(
                    {
                        "code": 500,
                        "message": "AI 分析服务内部错误",
                        "data": None,
                    }
                ),
                500,
            )

    @app.post("/nlp/analyze/frontend")
    def analyze_frontend():
        request_id = f"req_{uuid4().hex[:12]}"
        try:
            payload = request.get_json(silent=False)
            return jsonify(ai_service.analyze_frontend(payload))
        except ValidationError as error:
            return (
                jsonify(
                    {
                        "code": "VALIDATION_ERROR",
                        "message": str(error),
                        "fieldErrors": error.field_errors,
                        "requestId": request_id,
                    }
                ),
                400,
            )
        except Exception:
            app.logger.exception("Frontend-compatible AI analysis failed")
            return (
                jsonify(
                    {
                        "code": "AI_PROCESSING_FAILED",
                        "message": "AI 分析失败，请稍后重试",
                        "fieldErrors": {},
                        "requestId": request_id,
                    }
                ),
                500,
            )

    @app.errorhandler(400)
    def bad_request(_error):
        return jsonify({"code": 400, "message": "请求体必须是有效 JSON", "data": None}), 400

    @app.errorhandler(413)
    def request_too_large(_error):
        return (
            jsonify(
                {
                    "code": "FILE_TOO_LARGE",
                    "message": "请求体不能超过 1 MB",
                    "fieldErrors": {},
                    "requestId": f"req_{uuid4().hex[:12]}",
                }
            ),
            413,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.getenv("AI_HOST", "0.0.0.0"),
        port=int(os.getenv("AI_PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )
