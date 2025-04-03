import requests
import json
import uuid
import time
import base64
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from os import getenv, getcwd

# 配置你的商户信息
MCHID = getenv("WX_MCH_ID")
API_V3_KEY = b"xiaofengwangyufeng2025wangyufeng"  # 32字节的密钥
CERT_PATH = "app/certs/apiclient_cert.pem"
KEY_PATH = "app/certs/apiclient_key.pem"
PLATFORM_CERT_PATH = "app/certs/platform_cert.pem"

# 读取商户证书并获取序列号
def get_serial_number(cert_path):
    with open(cert_path, "rb") as cert_file:
        cert_data = cert_file.read()
    cert = x509.load_pem_x509_certificate(cert_data, default_backend())
    return format(cert.serial_number, "X")  # 转换为十六进制

# 读取商户私钥
def load_private_key(key_path):
    with open(key_path, "rb") as key_file:
        private_key = load_pem_private_key(key_file.read(), password=None)
    return private_key

# 生成签名
def sign_message(private_key, message):
    signature = private_key.sign(
        message.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode("utf-8")

# 解密微信支付平台证书
def decrypt_certificate(api_v3_key, encrypted_data):
    """ 使用 APIv3 密钥解密 AES-GCM 加密的证书 """
    associated_data = encrypted_data["associated_data"]
    nonce = encrypted_data["nonce"]
    ciphertext = encrypted_data["ciphertext"]

    cipher = Cipher(algorithms.AES(api_v3_key), modes.GCM(base64.b64decode(nonce)), backend=default_backend())
    decryptor = cipher.decryptor()
    decryptor.authenticate_additional_data(associated_data.encode("utf-8"))

    decrypted_cert = decryptor.update(base64.b64decode(ciphertext)) + decryptor.finalize()
    return decrypted_cert
def get_wechatpay_cert():
    # 1️⃣ 获取 `apiclient_cert.pem` 的 `serial_no`
    serial_no = get_serial_number(CERT_PATH)
    print("证书序列号:", serial_no)

    # 2️⃣ 读取商户私钥
    private_key = load_private_key(KEY_PATH)
    print("商户私钥读取成功")
    # 3️⃣ 生成 HTTP 头部签名
    nonce_str = uuid.uuid4().hex  # 这里建议使用 UUID 或随机生成
    timestamp = str(int(time.time()))
    message = f"GET\n/v3/certificates\n{timestamp}\n{nonce_str}\n"
    print(f"签名消息: {message}")
    signature = sign_message(private_key, message)
    print(f"生成的签名: {signature}")  # 打印生成的签名
    headers = {
        "Authorization": f'WECHATPAY2-SHA256-RSA2048 mchid="{MCHID}",serial_no="{serial_no}",nonce_str="{nonce_str}",timestamp="{timestamp}",signature="{signature}"',
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    # 4️⃣ 发送请求获取微信支付平台证书
    response = requests.get("https://api.mch.weixin.qq.com/v3/certificates", headers=headers)

    if response.status_code == 200:
        certs_data = response.json()
        for cert in certs_data["data"]:
            encrypted_cert = cert["encrypt_certificate"]
            
            # 5️⃣ 解密平台证书
            decrypted_cert = decrypt_certificate(API_V3_KEY, encrypted_cert)
            
            # 6️⃣ 保存到 `platform_cert.pem`
            with open(PLATFORM_CERT_PATH, "wb") as cert_file:
                cert_file.write(decrypted_cert)

            print("✅ 微信支付平台证书已成功获取并保存！")
    else:
        print(f"❌ 获取微信支付平台证书失败: {response.status_code} - {response.text}")
