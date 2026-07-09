"""
认证模块

提供基于 HMAC 签名的 token 认证：
- /api/auth/login: 验证密码，签发 token
- /api/auth/check: 校验当前 token 是否有效
- before_request 钩子: 拦截所有 /api/* 请求（白名单除外）

token 格式: {expire_timestamp}.{hmac_signature}
不依赖任何持久化，服务重启后旧 token 仍有效（密钥不变的前提下）
"""

import os
import hmac
import hashlib
import time
import logging
import yaml
from pathlib import Path
from functools import wraps
from flask import request, jsonify, g

logger = logging.getLogger(__name__)

# 全局缓存
_auth_config = None
_secret_key = None


def _load_auth_config() -> dict:
    """加载 auth.yaml 配置"""
    global _auth_config

    if _auth_config is not None:
        return _auth_config

    config_path = Path(__file__).parent.parent / 'auth.yaml'
    if not config_path.exists():
        logger.warning("auth.yaml 不存在，认证功能未启用")
        _auth_config = {"enabled": False}
        return _auth_config

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            raw = yaml.safe_load(f) or {}
        password = raw.get('password', '').strip()
        if not password:
            logger.warning("auth.yaml 中 password 为空，认证功能未启用")
            _auth_config = {"enabled": False}
        else:
            expire = raw.get('token_expire', 604800)
            _auth_config = {
                "enabled": True,
                "password": password,
                "token_expire": int(expire),
            }
            logger.info("认证功能已启用")
    except Exception as e:
        logger.error(f"加载 auth.yaml 失败，认证功能未启用: {e}")
        _auth_config = {"enabled": False}

    return _auth_config


def _get_secret_key() -> bytes:
    """获取用于签名的密钥（密码本身）"""
    global _secret_key
    if _secret_key is None:
        config = _load_auth_config()
        _secret_key = (config.get("password", "default") + "|redink").encode('utf-8')
    return _secret_key


def is_auth_enabled() -> bool:
    """认证功能是否启用"""
    return _load_auth_config().get("enabled", False)


def generate_token() -> str:
    """签发 token"""
    config = _load_auth_config()
    expire_seconds = config.get("token_expire", 604800)
    expire_ts = int(time.time()) + expire_seconds
    payload = str(expire_ts).encode('utf-8')
    signature = hmac.new(_get_secret_key(), payload, hashlib.sha256).hexdigest()
    return f"{expire_ts}.{signature}"


def verify_token(token: str) -> bool:
    """校验 token"""
    if not token or '.' not in token:
        return False
    parts = token.split('.', 1)
    if len(parts) != 2:
        return False
    try:
        expire_ts = int(parts[0])
    except ValueError:
        return False
    if time.time() > expire_ts:
        return False
    payload = parts[0].encode('utf-8')
    expected_sig = hmac.new(_get_secret_key(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(parts[1], expected_sig)


def extract_token() -> str | None:
    """从请求中提取 token，优先 Authorization header，其次 cookie"""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    return request.cookies.get('auth_token')


def require_auth(f):
    """装饰器：要求认证通过才能访问"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_auth_enabled():
            return f(*args, **kwargs)
        token = extract_token()
        if not token or not verify_token(token):
            return jsonify({"success": False, "error": "未授权访问"}), 401
        return f(*args, **kwargs)
    return decorated
