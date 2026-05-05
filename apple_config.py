#!/usr/bin/env python3
"""
Apple Music配置文件
请填入您的Apple Music API密钥信息
"""

# Apple Developer配置
# 请访问 https://developer.apple.com 获取以下信息

# Team ID（在开发者账号页面可以看到）
APPLE_TEAM_ID = ""

# MusicKit Key ID（创建MusicKit密钥时获得）
APPLE_KEY_ID = ""

# MusicKit私钥内容（.p8文件的内容，包括BEGIN和END行）
APPLE_PRIVATE_KEY = """
-----BEGIN PRIVATE KEY-----
（将您的.p8文件内容粘贴到这里）
-----END PRIVATE KEY-----
"""

# 如果没有配置以上信息，将使用模拟模式
# 模拟模式下，用户可以直接用Apple ID登录授权
