# 医疗病历生成与分析系统前端

React + Vite + TypeScript 前端，负责用户认证、病例录入、附件选择、异步任务状态展示、AI 结果查看、历史检索、病历复核编辑和报告下载。

## 技术栈

- React 19、TypeScript 5、Vite 7
- Ant Design、Axios、React Router
- Vitest

## 本地运行

```bash
cd frontend
npm install
npm run dev
```

生产构建与测试：

```bash
npm test
npm run build
npm run preview
```

Windows 完整联调推荐直接在仓库根目录双击 `启动答辩演示.cmd`，或运行：

```powershell
.\scripts\start-all.ps1 -EnableDemoUser -OpenBrowser
```

## API 配置

复制 `frontend/.env.example` 为 `frontend/.env.local` 后可修改：

```env
VITE_API_BASE_URL=http://127.0.0.1:8080
VITE_USE_MOCK_API=false
```

真实演示使用 Spring Boot 后端和 Flask AI 服务。`VITE_USE_MOCK_API=true` 仅用于前端离线测试，Mock 结果不代表真实 AI 输出。

前端当前对接的主要流程：

```text
注册 / 登录
  -> multipart 病例与附件提交
  -> 查询异步任务状态
  -> 查看真实 AI 结果
  -> 历史搜索、病历编辑、附件与 DOCX 报告下载
```

页面和报告均保留课程演示免责声明。请只输入虚构或脱敏病例数据。
