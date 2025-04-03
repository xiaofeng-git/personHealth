import requests
import time
import json
import uuid
import base64
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography import x509
from os import getenv
from fastapi import FastAPI, Request, HTTPException
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from .models import UserOrder
from cryptography.x509 import load_pem_x509_certificate
from wechatpayv3 import WeChatPay, WeChatPayType
from pathlib import Path
from .logger import api_logger
import re
MCHID = getenv("WX_MCH_ID")
APPID = getenv("WX_APP_ID")
API_V3_KEY = getenv("WX_API_KEY")
CERT_PATH = "app/certs/apiclient_cert.pem"
KEY_PATH = "app/certs/apiclient_key.pem"
PLATFORM_PATH = "app/certs/wechatpay_platform.pem"
NOTIFY_URL = "https://symmetrical-palm-tree-pjrj9vj74vqpf9rr4-8000.app.github.dev/api/wxpay-notify"
def get_serial_number(cert_path):
    with open(cert_path, "rb") as cert_file:
        cert_data = cert_file.read()
    cert = x509.load_pem_x509_certificate(cert_data, default_backend())
    raw_serial = str(cert.serial_number)
    print(f"商户证书编号:{raw_serial}")
    return format(cert.serial_number, "X")
with open(PLATFORM_PATH) as f:
    PUBLIC_KEY = f.read()
PUBLIC_KEY_ID = 'PUB_KEY_ID_0117121705482025032800338900002843'
# 初始化微信支付
wxpay = WeChatPay(
    wechatpay_type=WeChatPayType.JSAPI,  
    mchid=MCHID,
    private_key=open(KEY_PATH).read(),
    cert_serial_no=get_serial_number(CERT_PATH),
    apiv3_key=API_V3_KEY,
    appid=APPID,
    notify_url=NOTIFY_URL,
    logger=api_logger,
    partner_mode=False,
    proxy=None,
    timeout=(10, 30) ,
    public_key=PUBLIC_KEY,
    public_key_id=PUBLIC_KEY_ID
)
# 获取证书序列号

# 读取商户私钥
def load_private_key(key_path):
    with open(key_path, "rb") as key_file:
        return load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()  # ✅ 这里需要 backend 参数
        )
# 读取微信支付公钥
def load_wechatpay_public_key(cert_path):
    with open(cert_path, "rb") as cert_file:
        return cert_file.read()

# 生成签名
def sign_message(private_key, message):
    signature = private_key.sign(
        message.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode("utf-8")
def generate_pay_sign(params, private_key):
    """ 生成支付签名 """
    # 拼接参数字符串
    params_str = '&'.join([f"{key}={value}" for key, value in sorted(params.items())])
    # 拼接商户API密钥
    message = f"{params_str}&key={API_V3_KEY}"

    # 使用私钥对参数进行签名
    return sign_message(private_key, message)

def build_sign_message(timestamp, nonce, body):
    return f"{timestamp}\n{nonce}\n{body}\n".encode("utf-8")

def verify_wechatpay_signature(wechatpay_public_key_pem, timestamp, nonce, body, signature):
    public_key = load_pem_x509_certificate(wechatpay_public_key_pem).public_key()
    message = build_sign_message(timestamp, nonce, body)
    signature_bytes = base64.b64decode(signature)

    try:
        public_key.verify(
            signature_bytes,
            message,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except Exception as e:
        print(f"❌ 验签失败: {e}")
        return False
# 生成支付订单
def create_order_pay(db_record: UserOrder):
    
    print(f"✅ 创建订单并设定请求参数")
    # url = "https://api.mch.weixin.qq.com/v3/pay/transactions/jsapi"
    # serial_no = get_serial_number(CERT_PATH)
    # print("✅ 证书序列号:", serial_no)
    # private_key = load_private_key(KEY_PATH)
    # print(f"✅ 商户私钥位数: {private_key.key_size} bits")
    # 请求参数
    payload = {
        "appid": APPID,
        "mchid": MCHID,
        "description": f"健康助手-{db_record.plan_name}",
        "out_trade_no": db_record.order_id,
        "notify_url": NOTIFY_URL,
        "amount": {
            "total": int(db_record.price * 100),
            "currency": "CNY"
        },
        "payer": {
            "openid": db_record.openid
        }
    }
    
    code,content = wxpay.pay(
            **payload,
            pay_type=WeChatPayType.JSAPI
        )
    print(f"✅微信支付订单创建后返回结果：{content}")
    result = json.loads(content)
    if code in range(200, 300):
        prepay_id = result.get('prepay_id')
        timestamp = str(int(time.time()))
        noncestr = str(uuid.uuid4()).replace('-', '')
        package = 'prepay_id=' + prepay_id
        sign = wxpay.sign([APPID, timestamp, noncestr, package])
        signtype = 'RSA'
        return {
            "success": True,
            "data": {
                'appId': APPID,
                "timeStamp": str(int(time.time())),
                "nonceStr": noncestr,
                "package": 'prepay_id=%s' % prepay_id,
                "signType": signtype,
                "paySign": sign,
                "orderId": db_record.order_id
            }
    }
    else:
        return {'code': -1, 'result': {'reason': result.get('code')}}

    # # 生成签名
    # nonce_str = uuid.uuid4().hex
    # timestamp = str(int(time.time()))
    # message = f"POST\n/v3/pay/transactions/jsapi\n{timestamp}\n{nonce_str}\n{json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n"
    # if not message.endswith("\n"):
    #     message += "\n"
    # print("✅ 签名前的 message:")
    # print(repr(message)) 
    # signature = sign_message(private_key, message)
    # print("✅ 生成的签名:", signature)
    # headers = {
    #     "Authorization": f'WECHATPAY2-SHA256-RSA2048 mchid="{MCHID}",serial_no="{serial_no}",nonce_str="{nonce_str}",timestamp="{timestamp}",signature="{signature}"',
    #     "Content-Type": "application/json"
    # }

    # response = requests.post(url, headers=headers, json=payload)
    # if code == 200:
        
    #     if "prepay_id" in content:
    #         # 小程序支付，返回 prepay_id
    #         return {
    #             "prepay_id": content["prepay_id"],
    #             "pay_params": {
    #                 "timeStamp": str(int(time.time())),
    #                 "nonceStr": nonce_str,
    #                 "package": f'prepay_id={content["prepay_id"]}',
    #                 "signType": "RSA",
    #                 "paySign": signature
    #             }
    #         }
    #     else:
    #         raise HTTPException(status_code=500, detail=f"订单创建失败: {result}")
    # else:
    #     print(f"❌ 创建订单失败,失败原因: {response.text}")
    #     raise HTTPException(status_code=500, detail=f"订单创建失败: {result}")
def decrypt_wechat_notify(resource):
    ciphertext = resource["ciphertext"]
    nonce = resource["nonce"]
    associated_data = resource.get("associated_data", "")

    cipher = Cipher(algorithms.AES(API_V3_KEY), modes.GCM(base64.b64decode(nonce)), backend=default_backend())
    decryptor = cipher.decryptor()
    decryptor.authenticate_additional_data(associated_data.encode("utf-8"))

    decrypted_data = decryptor.update(base64.b64decode(ciphertext)) + decryptor.finalize()
    return json.loads(decrypted_data.decode("utf-8"))
# 处理微信支付成功的回调
def wechatpay_callback(request: Request):
    try:
        
        print("✅微信支付订单开始回调")
        # 获取 HTTP 头部的签名信息
        headers = request.headers
        body = request.data.decode('utf-8')
        # timestamp = headers.get("Wechatpay-Timestamp")
        # nonce = headers.get("Wechatpay-Nonce")
        # signature = headers.get("Wechatpay-Signature")

        # print("🔔 收到微信支付HTTP 头部的签名信息-Wechatpay-Timestamp:", timestamp)
        # print("🔔 收到微信支付HTTP 头部的签名信息-Wechatpay-Nonce:", nonce)
        # print("🔔 收到微信支付HTTP 头部的签名信息-Wechatpay-Signature:", signature)
        # # 读取微信支付公钥
        # wechatpay_public_key_pem = load_wechatpay_public_key(PLATFORM_PATH)
        # print("🔔 微信支付公钥信息:", wechatpay_public_key_pem)
        # data = request.json()
        # print("🔔 收到微信支付回调:", json.dumps(data, indent=2, ensure_ascii=False))
        # # 获取回调原始 JSON 字符串
        # body = request.data.decode("utf-8")  
        # # 1️⃣ **先验签**
        # if not verify_wechatpay_signature(wechatpay_public_key_pem, timestamp, nonce, body, signature):
        #     print("❌ 微信支付回调验签失败")
        #     return {"code": 400, "message": "验签失败"}, 400

        # print("✅ 微信支付回调验签成功")
        # # 获取加密数据
        # encrypted_data = data["resource"]

        # # 解密回调数据
        # decrypted_data = decrypt_wechat_notify(
        #     API_V3_KEY,
        #     encrypted_data["nonce"],
        #     encrypted_data["ciphertext"],
        #     encrypted_data["associated_data"]
        # )
        result = wxpay.callback_handler(headers, body) 
        print("✅ 支付通知:", result)

        return result
        
    except Exception as e:
        print("❌ 处理支付回调失败:", str(e))