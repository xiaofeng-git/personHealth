from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.middleware.logging import log_request_middleware
from app.config.logging import setup_logging
import logging
import traceback
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from app.routes import router
from dotenv import load_dotenv
import os
from app.models import init_db  # 只导入 init_db
from app.database import SessionLocal, init_test_data, get_db  # 从 database.py 导入 SessionLocal, init_test_data, get_db
from app.init_met_data import init_met_data

# 加载环境变量
load_dotenv()

# 检查必要的环境变量
api_key = os.getenv('QWEN_API_KEY')
if not api_key:
    raise ValueError("Missing QWEN_API_KEY in environment variables")
print(f"成功加载 API Key: {api_key[:8]}...")  # 只打印前8位

# 设置日志配置
setup_logging()

logger = logging.getLogger(__name__)
app = FastAPI()

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加响应头中间件
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
    return response

# 注册日志中间件
app.middleware("http")(log_request_middleware)

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

# 初始化数据库
init_db()

# 初始化测试数据
db = next(get_db())
init_test_data(db)

# 初始化MET数据
db = SessionLocal()
try:
    init_met_data(db)
finally:
    db.close()

app.include_router(router, prefix="/api")

if __name__ == "__main__":
    # 配置uvicorn的日志
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"
    
    # 打印所有环境变量
    #print("Environment Variables:")
    #for key, value in os.environ.items():
    #    print(f"{key}: {value}")
    #port = int(os.environ.get('LC_APP_PORT', 8000))
    #print(f"LC_APP_PORT: {port}")  # 打印端口号
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        log_config=log_config
    ) 