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

当前前端已完成演示闭环；真实病例生成、认证、文件上传和 AI 推理尚未接入。
