from dotenv import load_dotenv
from os import getenv
from .logger import api_logger, app_logger
from typing import Dict
import re
from fastapi import HTTPException, Request
import jwt
import base64
import os
from openai import OpenAI  # 只需要 OpenAI 客户端
import aiohttp
import json
from datetime import datetime, timedelta

# 加载环境变量
load_dotenv()

# OpenAI 配置
client = OpenAI(api_key=getenv("QWEN_API_KEY"))

# 微信小程序配置
WX_APP_ID = getenv("WX_APP_ID")
WX_APP_SECRET = getenv("WX_APP_SECRET")

# JWT配置
JWT_SECRET = getenv("JWT_SECRET", "your-super-secret-key")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = int(getenv("JWT_EXPIRE_DAYS", "30"))


async def get_wx_session(code: str):
    """从微信服务器获取session信息"""
    try:
        if not WX_APP_ID or not WX_APP_SECRET:
            api_logger.error("微信配置缺失: APP_ID或APP_SECRET未设置")
            return None
            
        api_logger.info(f"开始获取微信session, code: {code}")
        async with aiohttp.ClientSession() as session:
            url = f"https://api.weixin.qq.com/sns/jscode2session"
            params = {
                "appid": WX_APP_ID,
                "secret": WX_APP_SECRET,
                "js_code": code,
                "grant_type": "authorization_code"
            }
            
            api_logger.debug(f"请求微信服务器，参数：{params}")
            async with session.get(url, params=params) as response:
                # 先获取原始文本
                text = await response.text()
                api_logger.debug(f"微信服务器原始响应：{text}")
                
                try:
                    import json
                    data = json.loads(text)
                except json.JSONDecodeError:
                    api_logger.error(f"解析响应JSON失败：{text}")
                    return None
                
                api_logger.debug(f"解析后的响应数据：{data}")
                
                if "errcode" in data and data["errcode"] != 0:
                    api_logger.error(f"微信登录错误: {data}")
                    return None
                    
                if not data.get("openid") or not data.get("session_key"):
                    api_logger.error("微信返回数据缺少必要字段")
                    return None
                    
                api_logger.info("成功获取微信session")
                return {
                    "openid": data["openid"],
                    "session_key": data["session_key"]
                }
    except Exception as e:
        api_logger.exception(f"获取微信session失败: {str(e)}")
        return None

def create_token(user_id: int, session_key: str) -> str:
    try:
        # 使用更简单的 payload 结构
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(days=30)  # 30天过期
        }
        
        # 使用 HS256 算法，它对环境要求较低
        token = jwt.encode(
            payload,
            os.getenv('JWT_SECRET', 'your-secret-key'),
            algorithm='HS256'
        )
        
        # 处理 PyJWT 新旧版本的兼容性
        if isinstance(token, bytes):
            return token.decode('utf-8')
        return token
        
    except Exception as e:
        api_logger.error(f"生成token失败: {str(e)}")
        return None

def verify_token(token: str) -> dict:
    try:
        # 使用相同的密钥和算法进行解码
        payload = jwt.decode(
            token,
            os.getenv('JWT_SECRET', 'your-secret-key'),
            algorithms=['HS256']
        )
        return payload
    except jwt.ExpiredSignatureError:
        api_logger.error("Token已过期")
        return None
    except jwt.InvalidTokenError as e:
        api_logger.error(f"无效的token: {str(e)}")
        return None
    except Exception as e:
        api_logger.error(f"验证token失败: {str(e)}")
        return None

async def analyze_food_image_openai(image_content: bytes) -> str:
    try:
        base64_image = base64.b64encode(image_content).decode()
        api_key = os.getenv('QWEN_API_KEY')
        print(f"使用 API Key: {api_key[:8]}...")  # 只打印前8位
        
        # 构建 data URL
        data_url = f"data:image/jpeg;base64,{base64_image}"
        print(f"图片 URL: {data_url[:50]}...")  # 只打印前50个字符
        
        client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        
        print("准备发送请求到通义千问API...")
        response = client.chat.completions.create(
            model="qwen2.5-vl-7b-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "请识别并分析图片中的食物，并按以下格式返回信息：\n" +
                                   "食物名称：\n" +
                                   "食物种类：\n" +
                                   "重量（大概）：\n" +
                                   "营养成分分析：\n" +
                                   "1. 总体营养价值\n" +
                                   "2. 主要营养成分（每100克）：\n" +
                                   "- 热量（千卡）：\n" +
                                   "- 蛋白质（克）：\n" +
                                   "- 碳水化合物（克）：\n" +
                                   "- 脂肪（克）：\n" +
                                   "3. 其他营养元素：\n" +
                                   "- 维生素\n" +
                                   "- 矿物质\n\n" +
                                   "健康建议：\n" +
                                   "1. 营养价值分析\n" +
                                   "2. 适合人群\n" +
                                   "3. 食用建议\n" +
                                   "4. 注意事项"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": data_url
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000
        )
        
        print(f"API响应: {response}")
        return response.choices[0].message.content
    except Exception as e:
        print(f"调用通义千问API时出错: {e}")
        raise


def parse_food_info(content: str) -> Dict:
    try:
        return {
            "foodInfo": {
                "name": extract_value(content, "食物名称"),
                "category": extract_value(content, "食物种类"),
                "weight": extract_value(content, "重量"),
                "overallNutrition": extract_section(content, "总体营养价值"),
                "otherNutrients": {
                    "vitamins": extract_section(content, "维生素"),
                    "minerals": extract_section(content, "矿物质")
                }
            },
            "nutritionInfo": {
                "calories": extract_number(content, "热量（千卡）"),
                "protein": extract_number(content, "蛋白质（克）"),
                "carbs": extract_number(content, "碳水化合物（克）"),
                "fat": extract_number(content, "脂肪（克）")
            },
            "healthAdvice": {
                "nutritionAnalysis": extract_section(content, "1. 营养价值分析"),
                "suitableGroups": extract_section(content, "2. 适合人群"),
                "consumptionTips": extract_section(content, "3. 食用建议"),
                "precautions": extract_section(content, "4. 注意事项")
            }
        }
    except Exception as e:
        print(f"解析失败: {e}")
        return None

def extract_value(content: str, key: str) -> str:
    pattern = f"{key}[：:](.*?)(?:\n|$)"
    match = re.search(pattern, content)
    return match.group(1).strip() if match else ""

def extract_section(content: str, section: str) -> str:
    pattern = f"{section}(.*?)(?=\n\n|$)"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else ""

def extract_number(content: str, key: str) -> float:
    value = extract_value(content, key)
    try:
        return float(re.search(r'\d+', value).group())
    except:
        return 0

def get_current_user_id(request: Request = None):
    try:
        # 从请求头获取token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            api_logger.error("未找到Authorization请求头或格式错误")
            return None
        
        token = auth_header.split(" ")[1]
        payload = verify_token(token)
        if not payload:
            api_logger.error("Token验证失败")
            return None
            
        user_id = payload.get("user_id")
        if not user_id:
            api_logger.error("Token中未找到user_id")
            return None
            
        return user_id
    except Exception as e:
        api_logger.error(f"获取用户ID失败: {str(e)}")
        return None 