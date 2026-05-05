#!/usr/bin/env python3
"""
详细调试QQ音乐短链接
"""
import sys
import requests

def debug_full_html(url):
    """详细调试QQ音乐链接"""
    print("=" * 80)
    print(f"原始链接: {url}")
    print("=" * 80)

    print("\n【步骤1】尝试访问链接...")
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 QQMusic/12.3.5"
        })

        response = session.get(url, timeout=10, allow_redirects=True)
        print(f"   最终URL: {response.url}")
        print(f"   状态码: {response.status_code}")
        print(f"   响应长度: {len(response.content)} 字节")

        print("\n【步骤2】查找HTML中的关键信息...")
        html = response.text

        # 查找所有包含数字的地方
        import re
        print("\n   a. 查找 window.dissid / dissid / dissId...")
        patterns = [
            r"window\.dissid\s*[:=]\s*['\"](.+?)['\"]",
            r"disstid\s*[:=]\s*['\"](.+?)['\"]",
            r"dissId\s*[:=]\s*['\"](.+?)['\"]",
        ]
        for i, pattern in enumerate(patterns):
            matches = re.findall(pattern, html)
            if matches:
                print(f"      模式{i+1}匹配成功: {matches}")

        # 打印HTML前2000字符
        print("\n【步骤3】HTML内容（前2000字符）:")
        print(html[:2000])

        # 保存完整HTML到文件以便检查
        with open("/tmp/qqmusic.html", "w") as f:
            f.write(html)
        print("\n   完整HTML已保存到 /tmp/qqmusic.html")

        return html

    except Exception as e:
        print(f"   失败: {e}")
        return None


if __name__ == "__main__":
    test_url = "https://c6.y.qq.com/base/fcgi-bin/u?__=oQqoGYP0MHkq"
    if len(sys.argv) > 1:
        test_url = sys.argv[1]

    debug_full_html(test_url)
