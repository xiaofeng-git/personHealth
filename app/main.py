from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .middleware.logging import log_request_middleware
from .config.logging import setup_logging
import logging
import traceback
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
from .models import init_db
from .logger import logger
from .database import init_test_data, get_db

# 设置日志配置
setup_logging()

logger = logging.getLogger(__name__)
app = FastAPI()

# 注册日志中间件
app.middleware("http")(log_request_middleware)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # 添加以下响应头以支持 SharedArrayBuffer
    expose_headers=["*"],
    add_headers={
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Embedder-Policy": "require-corp"
    }
)

# 初始化数据库
init_db()

# 初始化测试数据
db = next(get_db())
init_test_data(db)

# 添加路由
app.include_router(router, prefix="/api")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"""
Unhandled Exception:
  URL: {request.method} {request.url}
  Error: {str(exc)}
  Traceback: {traceback.format_exc()}
""")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"}
    )

@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.exception("请求处理失败")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "服务器内部错误，请稍后重试"
            }
        )

# ... 其他路由和配置 ... 