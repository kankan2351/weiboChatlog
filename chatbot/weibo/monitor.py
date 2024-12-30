# src/weibo/monitor.py
import warnings
import logging
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Set
import requests
import urllib3
import aiohttp
import urllib.parse
import ssl
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from ..handlers.ai_interface import AIInterface
from ..utils.logger import get_logger
from ..utils.config import Config
from ..db.sqlite_db import SQLiteDB

logger = get_logger(__name__)

# 禁用 SSL 警告
requests.packages.urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class WeiboMonitor:
    def __init__(self, config: Config, message_db, ai_handler: AIInterface):
        """Initialize Weibo monitor"""
        self.config = config
        self.ai_handler = ai_handler
        self.message_db = message_db
        self.sqlite_db = message_db.sqlite_db
        
        # 获取微博配置
        self.weibo_config = self.config.get_weibo_config()
        self.test_mode = self.weibo_config.get('test_mode', False)
        
        # 长连接相关配置
        self.client_id = None
        self.handshake_url = "https://web.im.weibo.com/im/handshake"
        self.connect_url = "https://web.im.weibo.com/im/connect"
        self.headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Content-Type': 'application/json;charset=UTF-8',
            'Origin': 'https://api.weibo.com',
            'Referer': 'https://api.weibo.com/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        }
        
        # 从配置文件获取 cookies
        self.cookies = self.weibo_config.get('cookies', [])
        self._running = False
        self._monitoring_old = True  # 新增标志
        
        # Selenium 相关配置
        self.login_url = "https://passport.weibo.com/sso/signin"
        self.driver = None
        
        # 加载已处理的消息 ID
        self.processed_messages_file = "./data/processed_messages.json"
        self.processed_messages = self._load_processed_messages()

    def _load_processed_messages(self) -> Set[str]:
        """加载已处理的消息 ID"""
        try:
            if os.path.exists(self.processed_messages_file):
                with open(self.processed_messages_file, 'r') as f:
                    return set(json.load(f))
            return set()
        except Exception as e:
            logger.error(f"Error loading processed messages: {str(e)}")
            return set()

    def _save_processed_messages(self):
        """保存已处理的消息 ID"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.processed_messages_file), exist_ok=True)
            with open(self.processed_messages_file, 'w') as f:
                json.dump(list(self.processed_messages), f)
        except Exception as e:
            logger.error(f"Error saving processed messages: {str(e)}")

    async def wait_for_login(self):
        """等待手动登录并获取 cookies"""
        try:
            # 设置 Chrome 选项
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument('--start-maximized')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            # 初始化 Chrome 驱动
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 访问登录页面
            self.driver.get(self.login_url)
            print("\n请在打开的浏览器窗口中完成登录...")
            
            # 等待用户手动登录
            try:
                # 等待跳转到 weibo.com，但排除登录页面
                WebDriverWait(self.driver, 300).until(
                    lambda driver: "weibo.com" in driver.current_url 
                    and "passport.weibo.com" not in driver.current_url
                )
                print("检测到登录成功...")
                
                # 获取 cookies
                cookies = self.driver.get_cookies()
                
                # 更新配置文件中的 cookies
                self.weibo_config['cookies'] = cookies
                self.config.update_weibo_config(self.weibo_config)
                
                # 更新当前实例的 cookies
                self.cookies = cookies
                
                print("已保存 cookies")
                
                # 发送启动消息
                chat_url = self.weibo_config.get('chat_url', 'https://api.weibo.com/chat#/chat')
                group_name = self.weibo_config.get('send_group', {}).get('name', '茧房建筑师协会')
                # 打开聊天页面
                self.driver.get(chat_url)
                await asyncio.sleep(2)  # 等待页面基本加载
                
                # 等待页面加载
                wait = WebDriverWait(self.driver, 10)
                
                # 等待并点击群聊
                group_div = wait.until(
                    EC.presence_of_element_located((By.XPATH, f"//div[contains(text(), '{group_name}')]"))
                )
                await asyncio.sleep(1)
                group_div.click()
                await asyncio.sleep(2)
                
                # 等待输入框出现
                textarea = wait.until(
                    EC.element_to_be_clickable((By.TAG_NAME, "textarea"))
                )
                await asyncio.sleep(1)
                
                # # 输入启动消息
                # startup_message = "已启动，正在监听消息..."
                # textarea.clear()
                # await asyncio.sleep(0.5)
                
                # # 分段输入消息
                # for chunk in [startup_message[i:i+10] for i in range(0, len(startup_message), 10)]:
                #     textarea.send_keys(chunk)
                #     await asyncio.sleep(0.1)
                
                # await asyncio.sleep(1)
                # textarea.send_keys(Keys.RETURN)
                # await asyncio.sleep(2)
                
                return True
                
            except TimeoutException:
                print("登录超时，请重试")
                return False
                
        except Exception as e:
            logger.error(f"登录过程出错: {str(e)}")
            return False
            
        # finally:
        #     # 关闭浏览器
        #     if self.driver:
        #         self.driver.quit()
        #         self.driver = None

    # 废弃了
    async def monitor_messages(self) -> None:
        """Monitor Weibo messages using long-polling"""
        try:
            if not self.cookies:
                logger.error("No cookies available")
                return
                
            # 设置 SSL 上下文
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # 创建 session
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=ssl_context)
            ) as session:
                # 设置 cookies
                for cookie in self.cookies:
                    session.cookie_jar.update_cookies({cookie['name']: cookie['value']})
                
                # 开始长轮询
                while self._running:
                    try:
                        connect_data = [{
                            "id": str(int(time.time() * 1000)),
                            "channel": "/meta/connect",
                            "connectionType": "long-polling",
                            "advice": {"timeout": 0},
                            "clientId": "o2y4j1tq71gnsjazecb27c9dvvbf68"  # 这个需要动态获取
                        }]
                        
                        async with session.post(
                            self.connect_url,
                            headers=self.headers,
                            json=connect_data,
                            timeout=70
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                logger.debug(f"Received data: {data}")
                                
                                # 处理接收到的消息
                                if data and isinstance(data, list):
                                    for item in data:
                                        if item.get('data'):
                                            await self.process_message(item['data'])
                            else:
                                logger.error(f"Connect request failed with status {response.status}")
                                await asyncio.sleep(5)
                                
                    except asyncio.TimeoutError:
                        logger.debug("Long-polling timeout, reconnecting...")
                        continue
                    except Exception as e:
                        logger.error(f"Error in long-polling: {str(e)}")
                        await asyncio.sleep(5)
                        
        except Exception as e:
            logger.error(f"Monitor error: {str(e)}")
        finally:
            logger.info("Monitor stopped")

    async def process_message(self, msg: Dict, is_old_message: bool = False) -> Optional[Dict]:
        """处理单个消息"""
        try:
            logger.debug(f"Processing message: {msg}")
            # 如果消息是BOT则不处理
            if 'info' in msg:
                info = msg['info']
                if info.get('from_user', {}) == 'Noname':
                    return None
            if msg.get('from', {}).get('name') == 'Noname':
                return None

            # 如果消息为空或不是预期的格式，直接返回
            if not msg or not isinstance(msg, dict):
                logger.warning(f"Invalid message format: {msg}")
                return None
                
            # 判断消息格式（长轮询还是普通轮询）
            if 'info' in msg:  # 长轮询格式
                info = msg['info']
                from_user = info.get('from_user', {})
                msg_type = info.get('type')
                msg_id = info.get('id', '')
                msg_content = info.get('content', '')
                msg_media_type = info.get('media_type', 0)
                group_id = info.get('gid', '')
                group_name = info.get('group_name')
                user_id = str(info.get('from_uid', ''))  # 从 info 中获取 from_uid
                msg_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(time.time())))
            else:  # 普通轮询格式
                from_user = msg.get('from_user', {})
                msg_type = msg.get('type')
                msg_id = msg.get('id', '')
                msg_content = msg.get('content', '')
                msg_media_type = msg.get('media_type', 0)
                group_id = msg.get('gid', '')
                group_name = None
                user_id = str(from_user.get('id', ''))  # 从 from_user 中获取 id
                # 时间要用从接口获取的数据
                msg_time = msg.get('time', '')
                if not msg_time:
                    msg_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time))
                
            if not from_user:
                logger.warning("Message missing from_user field")
                return None
                
            speaker_name = from_user.get('screen_name', 'Unknown')
            current_time = int(time.time())
            
            # 检查消息是否已处理
            if msg_id in self.processed_messages:
                return None
                
            # 构建标准消息格式
            message = {
                "id": str(msg_id),
                "time": msg_time,
                "timestamp": current_time,
                "type": msg_type,
                "from": {
                    "uid": user_id,  # 使用正确的 user_id
                    "name": speaker_name,
                    "verified": from_user.get('verified', False),
                    "verified_type": from_user.get('verified_type'),
                    "avatar": from_user.get('profile_image_url'),  # 使用正确的头像字段
                    "user_name": speaker_name
                },
                "group": {
                    "gid": str(group_id),
                    "name": group_name
                },
                "media_type": msg_media_type,
                "content": msg_content or "",
                "reply_to": None,
                "metadata": {
                    "source": "weibo",
                    "raw_type": msg.get('sub_type', msg_type),
                    "user_id": user_id,  # 使用正确的 user_id
                    "user_name": speaker_name
                }
            }
            
            # logger.info(f"Constructed message: {message}")
            # 在存储消息之前检查用户隐私设置
            user_status = await self.sqlite_db.get_user_status(speaker_name)

            if user_status != "no_record":
                try:
                    # 存储到向量数据库和 SQLite
                    await self.message_db.add_message(message)
                    await self.sqlite_db.add_message(message)
                    
                    # 添加到已处理集合并保存
                    self.processed_messages.add(msg_id)
                    self._save_processed_messages()
                except Exception as e:
                    logger.error(f"Error storing message: {str(e)}")
                    return None
            
            # 处理消息
            if msg_type == 321 and msg_content:
                separator = '- - - - - - - - - - - - - - -'
                bot_name = self.config.bot_config.get('name', 'BOT')
                
                # 获取真实回复内容
                real_content = msg_content
                # 如果有分隔符，取最后一部分
                if separator in msg_content:
                    parts = msg_content.split(f'\n{separator}\n')
                    real_content = parts[-1].strip()
                
                # 检查是否 @ 了机器人, 新消息处理，老消息不处理
                current_time = int(time.time())
                msg_time = int(msg.get('timestamp', current_time))
                if f'@{bot_name}' in real_content and is_old_message==False:
                    user_info = {
                        "uid": user_id,
                        "name": speaker_name,
                        "user_name": speaker_name
                    }
                    # 处理消息并获取回复
                    reply = await self.ai_handler.ai_process_message(real_content, user_info)
                    if reply["success"]:
                        logger.info(reply["response"])
                        await self.send_message(reply["response"])
            
            return message
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return None

    async def start(self):
        """启动监控"""
        # 等待登录
        if not await self.wait_for_login():
            return
            
        self._running = True
        
        # 创建两个任务：监控老消息和新消息
        old_messages_task = asyncio.create_task(self.monitor_old_messages())
        new_messages_task = asyncio.create_task(self.monitor_new_messages())
        
        # 等待两个任务完成
        await asyncio.gather(old_messages_task, new_messages_task)

    async def monitor_old_messages(self) -> None:
        """监控历史消息（使用原有的轮询方式）"""

        try:
            session = requests.Session()
            for cookie in self.cookies:
                session.cookies.set(cookie['name'], cookie['value'])
                
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://api.weibo.com/chat/',
                'Origin': 'https://api.weibo.com',
                'Accept': 'application/json, text/plain, */*'
            }
            
            base_url = f"{self.weibo_config.get('api_base', 'https://api.weibo.com')}/webim/groupchat/query_messages.json"
            monitor_group = self.weibo_config.get('monitor_group', {})
            group_id = monitor_group.get('id')
            source = self.weibo_config.get('source')
            
            if not all([group_id, source]):
                logger.error("Missing required configuration for monitoring")
                return
                
            max_mid = 0
            message_count = 0
            
            while self._running and self._monitoring_old:
                try:
                    # 获取历史消息
                    current_timestamp = int(time.time() * 1000)
                    params = {
                        'convert_emoji': 1,
                        'query_sender': 1,
                        'count': 20,
                        'id': group_id,
                        'max_mid': max_mid,
                        'source': source,
                        't': current_timestamp,
                        'from': 'pc',
                        'version': '2.0.0',
                        '_': current_timestamp
                    }
                    
                    # 构建完整URL并记录日志
                    # url = base_url + '?' + '&'.join([f"{k}={v}" for k, v in params.items()])
                    # logger.info(f"Requesting URL: {url}")
                    
                    response = session.get(
                        base_url,
                        params=params,
                        headers=headers,
                        timeout=30,
                        verify=False
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        messages = data.get('messages', [])
                        
                        if not messages:  # 如果没有消息了，就停止
                            logger.info("No more historical messages")
                            self._running = False
                            break
                            
                        # 更新 max_mid 为第一条消息的 ID（因为是倒序的）
                        if messages:
                            max_mid = messages[0].get('id')
                            # logger.info(f"Updated max_mid to: {max_mid}")
                        
                        for msg in messages:
                            await self.process_message(msg, is_old_message=True)
                            message_count += 1
                            if message_count >= 1000:  # 达到1000条消息后停止
                                logger.info("Reached 1000 messages limit, stopping old message monitoring")
                                self._monitoring_old = False  # 只停止历史消息监控
                                break
                                
                    else:
                        logger.error(f"Query messages failed: {response.text}")
                        
                    # 等待一段时间再次检查
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    logger.error(f"Error monitoring old messages: {str(e)}")
                    await asyncio.sleep(10)
                    
        except Exception as e:
            logger.error(f"Error in old message monitor: {str(e)}")
        finally:
            if 'session' in locals():
                session.close()

    async def monitor_new_messages(self) -> None:
        """监控新消息（使用长轮询方式）"""
        try:
            # 设置 SSL 上下文
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # 创建 session
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=ssl_context)
            ) as session:
                # 设置 cookies
                for cookie in self.cookies:
                    session.cookie_jar.update_cookies({cookie['name']: cookie['value']})
                
                # 开始长轮询
                while self._running:
                    try:
                        connect_data = [{
                            "id": str(int(time.time() * 1000)),
                            "channel": "/meta/connect",
                            "connectionType": "long-polling",
                            "advice": {"timeout": 0},
                            "clientId": "o2y4j1tq71gnsjazecb27c9dvvbf68"  # 这个需要动态获取
                        }]
                        
                        async with session.post(
                            self.connect_url,
                            headers=self.headers,
                            json=connect_data,
                            timeout=70
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                logger.debug(f"Received new message data: {data}")
                                
                                # 处理接收到的消息
                                if data and isinstance(data, list):
                                    for item in data:
                                        if item.get('data'):
                                            await self.process_message(item['data'])
                                            logger.info(f"Processed message: {item['data']}")
                            else:
                                logger.error(f"Connect request failed with status {response.status}")
                                await asyncio.sleep(5)
                                
                    except asyncio.TimeoutError:
                        logger.debug("Long-polling timeout, reconnecting...")
                        continue
                    except Exception as e:
                        logger.error(f"Error in new message monitor: {str(e)}")
                        await asyncio.sleep(5)
                        
        except Exception as e:
            logger.error(f"Error in new message monitor: {str(e)}")

    async def stop(self):
        """停止监控"""
        self._running = False
        logger.info("Monitor stopping...")
        
    async def cleanup(self):
        """清理资源"""
        await self.stop()
        self._save_processed_messages()  # 确保退出时保存
        logger.info("Monitor cleanup completed")

    async def send_message(self, content: str) -> bool:
        """发送消息到微博群聊"""
        try:
            if not self.driver:
                logger.error("Browser not initialized")
                return False
                
            # 从配置获取聊天相关信息
            chat_url = self.weibo_config.get('chat_url', 'https://api.weibo.com/chat#/chat')
            monitor_group = self.weibo_config.get('monitor_group', {})
            group_name = monitor_group.get('name', '茧房建筑师协会')
            group_id = monitor_group.get('id')
            
            if not group_id:
                logger.error("Group ID not found in config")
                return False
                
            # 打开聊天页面
            self.driver.get(chat_url)
            
            # 等待页面加载
            wait = WebDriverWait(self.driver, 10)
            
            # 等待并点击群聊
            group_div = wait.until(
                EC.presence_of_element_located((By.XPATH, f"//div[contains(text(), '{group_name}')]"))
            )
            group_div.click()
            
            # 等待输入框出现并确保它是可交互的
            textarea = wait.until(
                EC.element_to_be_clickable((By.TAG_NAME, "textarea"))
            )
            
            # 处理 Emoji 字符
            def remove_emojis(text):
                return ''.join(char for char in text if ord(char) < 0x10000)
            
            # 清理内容中的 Emoji
            cleaned_content = remove_emojis(content)
            if cleaned_content != content:
                logger.info("Removed emojis from message content")
            
            # 处理多行内容，将换行符替换为 Shift+Enter 组合键
            lines = cleaned_content.split('\n')
            full_content = lines[0]
            for line in lines[1:]:
                full_content += Keys.SHIFT + Keys.RETURN + line
            
            # 一次性发送所有内容
            textarea.send_keys(full_content)
            textarea.send_keys(Keys.RETURN)
            await asyncio.sleep(0.5)  # 保留一个短暂等待确保发送完成
            
            logger.info(f"Message sent to group {group_id}: {cleaned_content}")
            return True
            
        except TimeoutException:
            logger.error("Timeout waiting for elements")
            return False
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return False