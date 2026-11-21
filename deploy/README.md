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
