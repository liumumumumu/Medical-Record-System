# Medical-Record-System

Medical Record Generation and Analysis System.

医疗病历生成与分析系统是一个面向课程演示的病例录入、结构化生成与结果分析工作台。

## Repository Structure

- `frontend/`: React + Vite + TypeScript 前端。前端同学只在此目录开发。
- `docs/knowledge-base/医疗病历生成与分析系统/`: 项目状态、需求、任务、AI 接手和联调规范。

后端、数据处理和 AI 模块后续应分别建立独立目录，避免与 `frontend/` 混放。

## Frontend

```bash
cd frontend
npm install
npm run dev
```

生产构建：

```bash
cd frontend
npm run build
```

## Integration Guide

后端、数据处理和 AI 同学开始联调前，请阅读：

- [`docs/knowledge-base/医疗病历生成与分析系统/前后端与AI交接规范.md`](docs/knowledge-base/医疗病历生成与分析系统/前后端与AI交接规范.md)

## API Connection

前端默认连接 Spring Boot 服务 `http://127.0.0.1:8080`，并使用以下接口：

- `POST /api/v1/auth/login`、`GET /api/v1/auth/me`、`POST /api/v1/auth/logout`
- `POST /api/v1/cases`
- `GET /api/records`、`GET /api/records/{id}`、`PUT /api/records/{id}`
- `GET /api/reports/{id}/download`

在 `frontend/` 复制 `.env.example` 为 `.env.local` 后，可按需修改：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8080
VITE_USE_MOCK_API=false
```

`VITE_USE_MOCK_API=true` 仅用于没有服务时的前端独立演示；模拟登录账号为 `doctor / demo123`，模拟结果不代表真实 AI 输出。真实运行应启动 Spring Boot 与 AI 服务，并使用后端配置的账号。

当前未接入真实附件二进制上传。前端仅保留附件文件名元数据，待后端确定 `multipart/form-data` 协议、文件大小、MIME 白名单、存储与解析状态后再接入。
