#!/usr/bin/env python3
"""
调试QQ音乐链接 - 测试重定向和ID提取
"""
import sys
import requests
import re

def debug_short_link(url):
    """调试短链接重定向"""
    print("=" * 60)
    print(f"原始链接: {url}")
    print("=" * 60)

    # 1. 尝试获取重定向地址
    print("\n1. 尝试获取重定向地址...")
    session = requests.Session()
    session.max_redirects = 0
    try:
        response = session.get(url, allow_redirects=False, timeout=10)
        print(f"   状态码: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        location = response.headers.get("Location")
        print(f"   Location: {location}")
        if location:
            print(f"\n2. 重定向后的链接: {location}")
            return location
    except Exception as e:
        print(f"   失败: {e}")

    # 2. 打印response content的前500字符
    try:
        response = requests.get(url, timeout=10)
        print(f"\n3. 直接访问Response状态码: {response.status_code}")
        print(f"   Response内容（前500字符）: {response.text[:500]}")
    except Exception as e:
        print(f"   直接访问失败: {e}")

    return None


def extract_id_from_url(url):
    """从链接中提取ID"""
    print(f"\n4. 尝试从链接中提取ID: {url}")

    # 尝试各种模式
    patterns = [
        (r"playlist/(\d+)", "playlist/数字"),
        (r"id=(\d+)", "id=数字参数"),
        (r"taoge/(\d+)", "taoge/数字"),
    ]

    for pattern, name in patterns:
        match = re.search(pattern, url)
        if match:
            print(f"   ✅ {name} 匹配成功: {match.group(1)}")
            return int(match.group(1))
        else:
            print(f"   ❌ {name} 未匹配")

    print("   ❌ 所有模式均未匹配")
    return None


if __name__ == "__main__":
    test_url = "https://c6.y.qq.com/base/fcgi-bin/u?__=oQqoGYP0MHkq"
    if len(sys.argv) > 1:
        test_url = sys.argv[1]

    redirected_url = debug_short_link(test_url)

    if redirected_url:
        tid = extract_id_from_url(redirected_url)
        if not tid:
            tid = extract_id_from_url(test_url)
    else:
        tid = extract_id_from_url(test_url)

    print(f"\n最终结果: {'成功' if tid else '失败'}，提取到的ID: {tid}")
