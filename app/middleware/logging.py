import time
from fastapi import Request, Response
import json
import logging
import traceback
from typing import Optional
from starlette.concurrency import iterate_in_threadpool

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def format_headers(headers: dict) -> dict:
    """格式化请求/响应头,去除敏感信息"""
    sensitive_headers = {'authorization', 'cookie', 'set-cookie'}
    return {
        k: v if k.lower() not in sensitive_headers else '[FILTERED]'
        for k, v in headers.items()
    }

def format_json(data: str, max_length: int = 1000) -> str:
    """格式化JSON数据,处理长字符串"""
    try:
        if not data:
            return "empty"
        
        # 尝试解析JSON
        if isinstance(data, str):
            data = json.loads(data)
        
        # 处理特殊字段
        if isinstance(data, dict):
            for key in ['image', 'password', 'token']:
                if key in data:
                    data[key] = f"<{key}_data: {len(str(data[key]))} bytes>"
        
        # 转换回字符串
        result = json.dumps(data, ensure_ascii=False, indent=2)
        
        # 如果太长则截断
        if len(result) > max_length:
            return f"{result[:max_length]}... (truncated)"
        return result
    except:
        if len(str(data)) > max_length:
            return f"<data: {len(str(data))} bytes>"
        return str(data)

async def log_request_middleware(request: Request, call_next) -> Response:
    request_id = str(time.time())
    start_time = time.time()
    
    # 记录请求信息
    try:
        # 对于 GET 请求，不需要读取请求体
        if request.method == "GET":
            body_str = "No body (GET request)"
        else:
            # 保存原始请求体
            body = await request.body()
            # 重新设置请求体，因为FastAPI会消费它
            async def receive():
                return {"type": "http.request", "body": body}
            request._receive = receive
            body_str = format_json(body)

    except Exception as e:
        logger.error(f"Error logging request: {str(e)}\n{traceback.format_exc()}")

    # 处理请求
    try:
        response = await call_next(request)
        
        # 获取响应体
        response_body = [chunk async for chunk in response.body_iterator]
        response.body_iterator = iterate_in_threadpool(iter(response_body))

        # 记录响应信息
        process_time = time.time() - start_time
        response_content = b''.join(response_body)
        try:
            response_str = format_json(response_content.decode())
        except:
            response_str = f"<binary response: {len(response_content)} bytes>"
        
        log_level = logging.ERROR if response.status_code >= 400 else logging.INFO


        return Response(
            content=response_content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )
        
    except Exception as e:
        process_time = time.time() - start_time

        raise 