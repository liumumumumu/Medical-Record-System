# Medical Record System

课程演示用的医疗病历录入、结构化生成与分析系统。

## Repository Structure

- `frontend/`: React + Vite + TypeScript 前端。前端同学只在此目录开发。
- `docs/knowledge-base/医疗病历生成与分析系统/`: 项目状态、需求、任务、AI 接手和联调规范。

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

后端、数据处理和 AI 同学在开始联调前，请阅读：

- [`docs/knowledge-base/医疗病历生成与分析系统/前后端与AI交接规范.md`](docs/knowledge-base/医疗病历生成与分析系统/前后端与AI交接规范.md)

当前前端是演示闭环；真实病例生成、认证、文件上传和 AI 推理尚未接入。
