import asyncio
import sys
import json
import logging
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from chatbot.utils.config import Config
from chatbot.utils.logger import get_logger

logger = get_logger(__name__)

class MessageSender:
    def __init__(self):
        self.config = Config()
        self.driver = None
        self.init_browser()
        
    def init_browser(self):
        """初始化浏览器"""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # 注入 JavaScript 来绕过检测
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })
            
            logger.info("Browser initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing browser: {str(e)}")
            return False
            
    async def login(self) -> bool:
        """登录微博"""
        try:
            self.driver.get('https://passport.weibo.com/sso/signin')
            
            wait = WebDriverWait(self.driver, 10)
            
            try:
                # 切换到账号登录如果需要
                account_login_spans = wait.until(
                    EC.presence_of_all_elements_located((By.XPATH, "//span[contains(text(),'账号密码登录') or contains(text(),'账号登录')]"))
                )
                
                if account_login_spans:
                    account_login_spans[0].find_element(By.XPATH, "..").click()
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error switching login method: {str(e)}")
                
            logger.info("Please complete manual login...")
            
            try:
                # 等待登录完成，最多等待5分钟
                wait = WebDriverWait(self.driver, 300)
                wait.until(lambda driver: 
                    driver.current_url and
                    'passport.weibo.com' not in driver.current_url and 
                    ('weibo.com' in driver.current_url or 'www.weibo.com' in driver.current_url)
                )
                logger.info("Login successful!")
                return True
                
            except TimeoutException:
                logger.error("Login timeout")
                return False
                
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return False
            
    async def send_message(self, content: str) -> bool:
        """发送消息到微博群聊"""
        try:
            if not self.driver:
                logger.error("Browser not initialized")
                return False
                
            # 确保已登录
            if not await self.login():
                return False
                
            # 从配置获取聊天相关信息
            weibo_config = self.config.get_weibo_config()
            chat_url = weibo_config.get('chat_url', 'https://api.weibo.com/chat#/chat')
            group_name = weibo_config.get('group_name')
            group_id = weibo_config.get('group_id')
            
            if not group_id:
                logger.error("Group ID not found in config")
                return False
                
            # 打开聊天页面
            self.driver.get(chat_url)
            await asyncio.sleep(2)  # 等待页面基本加载
            
            # 等待页面加载
            wait = WebDriverWait(self.driver, 10)
            
            # 等待并点击群聊
            group_div = wait.until(
                EC.presence_of_element_located((By.XPATH, f"//div[contains(text(), '{group_name}')]"))
            )
            await asyncio.sleep(1)  # 等待元素完全可交互
            group_div.click()
            await asyncio.sleep(2)  # 等待群聊窗口加载
            
            # 等待输入框出现并确保它是可交互的
            textarea = wait.until(
                EC.element_to_be_clickable((By.TAG_NAME, "textarea"))
            )
            await asyncio.sleep(1)  # 等待输入框完全准备好
            
            # 输入消息
            textarea.clear()
            await asyncio.sleep(0.5)  # 等待清除完成
            
            # 分段输入消息，模拟真实输入
            for chunk in [content[i:i+10] for i in range(0, len(content), 10)]:
                textarea.send_keys(chunk)
                await asyncio.sleep(0.1)  # 模拟输入间隔
                
            await asyncio.sleep(1)  # 等待输入完成
            
            # 发送消息
            textarea.send_keys(Keys.RETURN)
            await asyncio.sleep(2)  # 等待发送完成
            
            logger.info(f"Message sent to group {group_id}: {content}")
            return True
            
        except TimeoutException:
            logger.error("Timeout waiting for elements")
            return False
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return False
            
    def cleanup(self):
        """清理资源"""
        if self.driver:
            self.driver.quit()
            self.driver = None

async def main():
    sender = MessageSender()
    try:
        # 从命令行参数获取消息内容，如果没有提供则使用默认消息
        content = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "这是一条测试消息"
        
        print(f"\n=== 发送测试消息 ===")
        print(f"Content: {content}")
        
        success = await sender.send_message(content)
        
        if success:
            print("消息发送成功！")
        else:
            print("消息发送失败！")
            
    finally:
        sender.cleanup()

if __name__ == "__main__":
    asyncio.run(main())