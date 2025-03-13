import logging
import os
from logging.handlers import RotatingFileHandler

# 确保日志目录存在
os.makedirs('logs', exist_ok=True)

def setup_logger(name, log_file, level=logging.INFO):
    """设置日志记录器"""
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 文件处理器
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# 创建两个日志记录器
api_logger = setup_logger('api', 'logs/api.log')
app_logger = setup_logger('app', 'logs/app.log')

# 使用示例：
# api_logger.info("API 调用信息")
# app_logger.error("应用程序错误") 