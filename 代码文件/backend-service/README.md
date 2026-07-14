# 医疗病历生成与分析系统后端

Spring Boot 后端负责登录、病例管理、异步 AI 分析、MongoDB 持久化、附件文本提取和 DOCX 报告下载。默认调用真实 Flask AI；Mock 仅在显式设置 `AI_MODE=mock` 时启用。

## 技术栈

- Java 21、Spring Boot 3.5.16、Maven Wrapper
- Spring Web、Validation、Security、Data MongoDB
- JWT Bearer Token、WebClient
- Apache POI、PDFBox、springdoc-openapi
- MongoDB Community 8.0

## 快速启动

Windows 推荐在项目根目录运行：

```powershell
.\scripts\start-all.ps1
```

服务地址：

- API：`http://localhost:8080/api/v1`
- 健康检查：`http://localhost:8080/actuator/health`
- Swagger UI / OpenAPI：默认关闭；仅在可信本地环境显式设置 `SPRINGDOC_ENABLED=true` 后启用，且仍需登录

默认不创建固定演示账号，请在前端注册。如确需演示账号，在项目根目录运行：

```powershell
.\scripts\start-all.ps1 -EnableDemoUser
```

第一次运行 Maven Wrapper 时需要联网下载依赖。也可以分别启动：

```bash
./scripts/start-mongodb.sh
./scripts/run-backend.sh
```

## 运行测试

```bash
./scripts/run-tests.sh
```

当前测试覆盖字段校验、JWT、Mock AI、Flask 响应映射与超时、异步状态、附件路径安全和 DOCX 内容。

## 配置

配置模板见 [`.env.example`](.env.example)。Spring Boot 直接读取环境变量，不会自动读取 `.env` 文件；可在 IDE 中配置，或启动前导出：

```bash
export AI_MODE=remote
export AI_BASE_URL=http://127.0.0.1:5000
./scripts/start-all.sh
```

关键变量：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `SERVER_PORT` | `8080` | 后端端口 |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | 允许跨域的前端地址 |
| `FRONTEND_ORIGIN_ALT` | `http://127.0.0.1:5173` | 备用前端来源 |
| `MONGODB_URI` | `mongodb://127.0.0.1:27017/medical_records` | MongoDB 连接串 |
| `JWT_SECRET` | 无 | 必填；根目录启动脚本会生成并保存在 `.runtime/` |
| `AI_MODE` | `remote` | `remote` 或仅测试使用的 `mock` |
| `AI_BASE_URL` | `http://127.0.0.1:5000` | Flask 服务地址 |
| `AI_ENDPOINT` | `/nlp/analyze` | Flask 分析路径 |
| `AI_TIMEOUT` | `20s` | 单次 AI 调用超时 |
| `UPLOAD_DIR` | `./data/uploads` | 附件目录 |
| `REPORT_DIR` | `./data/reports` | 报告目录 |
| `DEMO_USER_ENABLED` | `false` | 是否显式创建演示账号 |
| `SPRINGDOC_ENABLED` | `false` | 是否显式启用接口文档 |

## 核心流程

```text
POST /api/v1/cases
  -> 202 { caseId, jobId, status: queued }
  -> 后台线程调用 Mock/Flask
  -> GET /api/v1/jobs/{jobId}
  -> GET /api/v1/cases/{caseId}/result
```

前端建议每秒轮询一次任务，遇到 `completed` 后获取结果；遇到 `failed` 时展示 `errorCode/errorMessage` 并提供重试按钮。

## 数据与文件

- `users`：账号、BCrypt 密码和角色。
- `cases`：原始输入、AI 结果、人工编辑内容、附件和报告元数据。
- `jobs`：任务状态、进度和稳定失败码。
- `revoked_tokens`：已注销 JWT 的哈希及 TTL 过期时间。
- `data/uploads/{caseId}`：实际附件。
- `data/reports/{caseId}`：按编辑版本缓存的 DOCX。

所有病例、任务、附件和报告接口都验证 JWT 用户所有权。日志只记录请求 ID、方法、路径和异常，不记录完整病历、密码、Token 或文件内容。

PDF、DOC、DOCX 会在保存后提取正文并作为辅助检查上下文送入 AI；图片在未配置 OCR 时明确标记为 `metadata_only`。历史记录的 `keyword` 搜索在 MongoDB 端执行，不受当前分页限制。

## 交接材料

- [接口文档](docs/api_document.md)
- [Flask AI 契约](docs/flask_contract.md)
- [演示病例 JSON](docs/demo-case.json)
- [Postman 集合](docs/medical-record-backend.postman_collection.json)

课程演示数据必须使用虚构或脱敏内容。所有结果固定声明：仅供辅助整理与课程演示，不替代执业医师判断。
