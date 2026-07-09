"""
认证相关 API 路由

- POST /api/auth/login: 验证密码，返回 token
- GET /api/auth/check: 检查当前 token 是否有效
- GET /api/auth/status: 检查认证功能是否启用（无需 token）
"""

import logging
from flask import Blueprint, request, jsonify, make_response

from backend.auth import (
    is_auth_enabled,
    verify_token,
    generate_token,
    _load_auth_config,
)

logger = logging.getLogger(__name__)


def create_auth_blueprint():
    """创建认证路由蓝图"""
    auth_bp = Blueprint('auth', __name__)

    @auth_bp.route('/auth/login', methods=['POST'])
    def login():
        """验证密码并签发 token"""
        data = request.get_json() or {}
        password = data.get('password', '')

        config = _load_auth_config()
        if not config.get("enabled"):
            # 认证未启用，直接返回成功 + 空 token
            return jsonify({"success": True, "token": "", "auth_enabled": False})

        expected = config.get("password", "")
        if password == expected:
            token = generate_token()
            logger.info("登录成功")
            return jsonify({"success": True, "token": token, "auth_enabled": True})
        else:
            logger.warning("登录失败：密码错误")
            return jsonify({"success": False, "error": "密码错误"}), 401

    @auth_bp.route('/auth/check', methods=['GET'])
    def check():
        """检查当前 token 是否有效"""
        if not is_auth_enabled():
            return jsonify({"valid": True, "auth_enabled": False})

        auth_header = request.headers.get('Authorization', '')
        token = auth_header[7:] if auth_header.startswith('Bearer ') else request.cookies.get('auth_token', '')

        valid = bool(token) and verify_token(token)
        return jsonify({"valid": valid, "auth_enabled": True})

    @auth_bp.route('/auth/status', methods=['GET'])
    def status():
        """检查认证功能是否启用（公开接口，无需 token）"""
        return jsonify({"auth_enabled": is_auth_enabled()})

    return auth_bp
