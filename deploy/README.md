# deploy · 容器化演示配置

| 文件 | 说明 |
|---|---|
| `Dockerfile.backend` | Python 3.11 镜像，启动前自动执行 ETL，再运行 Uvicorn |
| `Dockerfile.frontend` | Node 构建 + Nginx 运行静态站点 |
| `docker-compose.yml` | 前端 5173、后端 8765，SQLite 持久化到命名卷 |
| `nginx.conf` | 静态资源与 `/api`、`/health`、`/docs` 反向代理 |

## 使用方式

```bash
cp .env.example .env
# 至少修改 MEDICAL_SECRET_KEY 与 MEDICAL_HASH_SALT
docker compose -f deploy/docker-compose.yml build
docker compose -f deploy/docker-compose.yml up -d
```

## 边界说明

- 配置已完成，但当前开发环境没有 Docker，**未做容器实机验证**；课程验收以本地运行结果为准。
- 后端容器首次启动会执行六源 ETL，第一次启动时间取决于机器性能。
- 容器内数据库位于命名卷，删除卷会丢失 ETL 与上传数据。
- 对外部署前必须完成 HTTPS、凭据治理、限流、备份恢复与安全测试。

## 端口与健康检查

| 服务 | 端口 | 检查方式 |
|---|---:|---|
| 前端 Nginx | 5173 | `http://127.0.0.1:5173/login` |
| 后端 API | 8765 | `http://127.0.0.1:8765/health` |
| Swagger | 8765 | `http://127.0.0.1:8765/docs` |

Compose 依赖根目录 `.env` 做变量替换。至少需要设置：

```dotenv
MEDICAL_SECRET_KEY=<长度足够的随机串>
MEDICAL_HASH_SALT=<固定的患者散列盐>
```

`MEDICAL_HASH_SALT` 一旦用于 ETL 就不应修改，否则同一患者会生成新的 `patient_key`。
