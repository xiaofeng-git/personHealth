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
#图片上传
UPLOAD_FOLDER  = getenv("UPLOAD_FOLDER")
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
        api_logger.info(f"开始创建token，用户ID: {user_id}")
        if not user_id:
            api_logger.error("用户ID为空")
            return None
            
        if not JWT_SECRET:
            api_logger.error("JWT_SECRET未设置")
            return None
            
        # 设置token过期时间为30天
        expire_days = int(os.getenv("JWT_EXPIRE_DAYS", "30"))
        expire = datetime.utcnow() + timedelta(days=expire_days)
        
        # 创建payload
        payload = {
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        # 生成token
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        api_logger.info(f"token创建成功: {token[:10]}...")  # 只记录token的前10个字符
        return token
    except Exception as e:
        api_logger.exception(f"创建token时发生错误: {str(e)}")
        return None
def verify_token(token: str) -> dict:
    try:
        api_logger.info(f"开始验证token: {token[:10]}...")  # 只记录token的前10个字符
        if not token:
            api_logger.warning("token为空")
            return None
            
        if not JWT_SECRET:
            api_logger.error("JWT_SECRET未设置")
            return None
            
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            api_logger.info(f"token验证成功，payload: {payload}")
            return payload
        except jwt.ExpiredSignatureError:
            api_logger.warning("token已过期")
            return None
        except jwt.InvalidTokenError as e:
            api_logger.warning(f"token无效: {str(e)}")
            return None
    except Exception as e:
        api_logger.exception(f"验证token时发生错误: {str(e)}")
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
        
        
        app_logger.info(f"同义千问API响应: {response.choices[0].message.content}")
        return response.choices[0].message.content
    except Exception as e:
        app_logger.info(f"调用通义千问API时出错: {e}")
        print(f"调用通义千问API时出错: {e}")
        raise


def parse_food_info(content: str) -> Dict:
    try:
        calories = 245.0 if extract_number(content, "热量（千卡）") == 0 else extract_number(content, "热量（千卡）")
        protein = 20.0 if extract_number(content, "蛋白质（克）") == 0 else extract_number(content, "蛋白质（克）")
        carbs = 10.0 if extract_number(content, "碳水化合物（克）") == 0 else extract_number(content, "碳水化合物（克）")
        fat = 15.0 if extract_number(content, "脂肪（克）") == 0 else extract_number(content, "脂肪（克）")
        return {
            "foodInfo": {
                "name": extract_value(content, "食物名称"),
                "category": extract_value(content, "食物种类") == 0,
                "weight": extract_value(content, "重量"),
                "overallNutrition": extract_section(content, "总体营养价值"),
                "otherNutrients": {
                    "vitamins": extract_section(content, "维生素"),
                    "minerals": extract_section(content, "矿物质")
                }
            },
            "nutritionInfo": {
                "calories": calories,
                "protein": protein,
                "carbs": carbs,
                "fat": fat
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
        # 防止 request 为 None
        if request is None:
            api_logger.error("请求对象为None")
            return None
            
        # 从请求头获取token
        auth_header = request.headers.get("Authorization", "")
        api_logger.info(f"收到的Authorization头: {auth_header}")  # 添加日志
        
        if not auth_header or not auth_header.startswith("Bearer "):
            api_logger.warning(f"未找到Authorization请求头或格式错误: {auth_header}")
            # 尝试从cookie获取
            try:
                token = request.cookies.get("token", "")
                api_logger.info(f"从cookie获取token: {token}")  # 添加日志
            except Exception as e:
                token = ""
                api_logger.error(f"从cookie获取token时出错: {str(e)}")
                
            if not token:
                # 尝试从query参数获取
                try:
                    token = request.query_params.get("token", "")
                    api_logger.info(f"从query参数获取token: {token}")  # 添加日志
                except Exception as e:
                    token = ""
                    api_logger.error(f"从query参数获取token时出错: {str(e)}")
                    
            if not token:
                api_logger.warning("未能找到有效的token")
                return None
        else:
            token = auth_header.split(" ")[1]
            
        # 验证token
        if not token:
            api_logger.warning("token为空")
            return None
            
        payload = verify_token(token)
        if not payload:
            api_logger.warning("token验证失败")
            return None
            
        user_id = payload.get("user_id")
        if not user_id:
            api_logger.warning("未找到用户ID")
            return None
            
        api_logger.info(f"成功获取用户ID: {user_id}")  # 添加日志
        return user_id
    except Exception as e:
        api_logger.exception(f"获取用户ID时发生错误: {str(e)}")
        return None
def save_image(image_content: bytes):

    # 下载临时图片
    image_data = image_content
    filename = f"{UPLOAD_FOLDER}/{int(datetime.time())}.jpg"

    # 保存图片到服务器
    with open(filename, "wb") as file:
        file.write(image_data)

    # 生成长期访问的 URL（这里直接返回文件路径，生产环境建议上传到云存储）
    long_term_url = f"{UPLOAD_FOLDER}/{filename}"
    