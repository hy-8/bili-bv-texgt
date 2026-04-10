@echo off
chcp 65001 >nul 2>&1
title 导出B站Cookie
cd /d "%~dp0"

echo ========================================
echo   导出B站Cookie到 cookies.txt
echo ========================================
echo.
echo 方法一：浏览器插件导出（推荐）
echo   1. 安装 Chrome 插件 "Get cookies.txt LOCALLY"
echo      https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc
echo   2. 打开 bilibili.com 并登录
echo   3. 点击插件图标，导出 cookies
echo   4. 保存为 cookies.txt 到本项目目录
echo.
echo 方法二：手动复制
echo   1. 打开 bilibili.com 并登录
echo   2. 按 F12 打开开发者工具
echo   3. 切到 Application -^> Cookies -^> https://www.bilibili.com
echo   4. 找到 SESSDATA 的值，复制到 config.env 的 BILIBILI_COOKIE
echo      格式: BILIBILI_COOKIE=SESSDATA=你的值
echo.
echo ========================================
echo.

REM 尝试自动导出（需要管理员权限）
echo 正在尝试从浏览器自动提取...
.net\Scripts\python.exe -c "
import browser_cookie3, sys, os
sys.stdout.reconfigure(encoding='utf-8')

browsers = [
    ('Chrome', lambda: browser_cookie3.chrome(domain_name='.bilibili.com')),
    ('Edge', lambda: browser_cookie3.edge(domain_name='.bilibili.com')),
    ('Firefox', lambda: browser_cookie3.firefox(domain_name='.bilibili.com')),
]

for name, loader in browsers:
    try:
        cj = loader()
        count = len(list(cj))
        if count > 0:
            with open('cookies.txt', 'w', encoding='utf-8') as f:
                f.write('# Netscape HTTP Cookie File\n')
                for cookie in cj:
                    secure = 'TRUE' if cookie.secure else 'FALSE'
                    expire = str(int(cookie.expires)) if cookie.expires else '0'
                    f.write(f'.{cookie.domain}\tTRUE\t{cookie.path}\t{secure}\t{expire}\t{cookie.name}\t{cookie.value}\n')
            print(f'{name} Cookie 导出成功! 共 {count} 条')
            sys.exit(0)
    except Exception:
        continue

print('自动提取失败，请使用上方手动方法导出 cookies.txt')
sys.exit(1)
"

if %errorlevel% equ 0 (
    echo.
    echo Cookie 导出成功！可以重新运行 start.bat 下载视频了
) else (
    echo.
    echo 自动提取失败，请按照上方说明手动导出
)

echo.
pause
