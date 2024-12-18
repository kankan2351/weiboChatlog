# src/weibo/monitor.py
import warnings
import logging
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
import requests

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from ..handlers.ai_interface import AIInterface
from ..utils.logger import get_logger

logger = get_logger(__name__)

class WeiboMonitor:
    def __init__(self, ai_handler: AIInterface, username: str, password: str):
        """Initialize Weibo monitor"""
        self.ai_handler = ai_handler
        self.username = username
        self.password = password
        
        # Initialize Chrome options
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.options.add_experimental_option('excludeSwitches', ['enable-automation'])
        self.options.add_experimental_option('useAutomationExtension', False)
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-gpu')
        self.driver = None
        
        # Initialize state
        self.data_dir = Path("./data")
        self.data_dir.mkdir(exist_ok=True)
        self.processed_messages_file = self.data_dir / "processed_messages.json"
        self.last_message_time_file = self.data_dir / "last_message_time.txt"
        
        self.processed_messages = set()
        self.last_message_time = 0
        self.cookies = None
        
        # Load processing state
        self.load_state()
        
    def load_state(self) -> None:
        """Load processing state from files"""
        try:
            if self.processed_messages_file.exists():
                with open(self.processed_messages_file, 'r', encoding='utf-8') as f:
                    self.processed_messages = set(json.load(f))
                    
            if self.last_message_time_file.exists():
                with open(self.last_message_time_file, 'r') as f:
                    self.last_message_time = int(f.read().strip())
                    
            logger.info(f"Loaded {len(self.processed_messages)} processed messages")
            
        except Exception as e:
            logger.error(f"Error loading state: {str(e)}")
            self.processed_messages = set()
            self.last_message_time = 0
            
    def save_state(self) -> None:
        """Save processing state to files"""
        try:
            with open(self.processed_messages_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.processed_messages), f)
                
            with open(self.last_message_time_file, 'w') as f:
                f.write(str(self.last_message_time))
                
        except Exception as e:
            logger.error(f"Error saving state: {str(e)}")
            
    def start_browser(self) -> bool:
        """Start Chrome browser"""
        if not self.driver:
            try:
                service = Service(ChromeDriverManager().install())
                
                self.driver = webdriver.Chrome(
                    service=service,
                    options=self.options
                )
                
                self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': '''
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        })
                    '''
                })
                
                logger.info("Chrome browser started successfully")
                return True
                
            except Exception as e:
                logger.error(f"Error starting browser: {str(e)}")
                if self.driver:
                    self.driver.quit()
                    self.driver = None
                return False
                
    async def login(self) -> bool:
        """Login to Weibo"""
        try:
            if not self.start_browser():
                return False
                
            self.driver.get('https://passport.weibo.com/sso/signin')
            
            wait = WebDriverWait(self.driver, 10)
            
            try:
                # Switch to account login if needed
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
                wait = WebDriverWait(self.driver, 300)
                wait.until(lambda driver: 
                    driver.current_url and
                    'passport.weibo.com' not in driver.current_url and 
                    ('weibo.com' in driver.current_url or 'www.weibo.com' in driver.current_url)
                )
                logger.info("Login successful!")
                
                self.cookies = self.driver.get_cookies()
                return True
                
            except TimeoutException:
                logger.error("Login timeout")
                return False
                
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return False
            
    async def process_message(self, msg: Dict) -> Optional[Dict]:
        """Process single message"""
        try:
            message = {
                "id": str(msg.get('id', '')),
                "time": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(msg['time'])),
                "timestamp": msg.get('time'),
                "type": msg.get('type'),
                "sub_type": msg.get('sub_type'),
                "from": {
                    "uid": str(msg.get('from_user', {}).get('id', '')),
                    "name": msg.get('from_user', {}).get('screen_name', ''),
                    "verified": msg.get('from_user', {}).get('verified', False),
                    "verified_type": msg.get('from_user', {}).get('verified_type'),
                    "avatar": msg.get('from_user', {}).get('avatar_large')
                },
                "group": {
                    "gid": str(msg.get('gid', '')),
                    "name": None
                },
                "media_type": msg.get('media_type', 0),
                "content": msg.get('content', '')
            }
            
            # Handle @mentions
            if '@茧房爬楼王' in message['content']:
                response = await self.ai_handler.process_message(
                    content=message['content'],
                    user=message['from']['name']
                )
                message['bot_response'] = response
                
                # Check for special operations
                if response.get('function_called') == 'stop_tracking':
                    logger.info(f"Stop tracking user: {response.get('response')}")
                elif response.get('function_called') == 'delete_messages':
                    logger.info(f"Delete messages: {response.get('response')}")
                    return None
                    
            return message
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return None
            
    async def monitor_messages(self) -> None:
        """Monitor Weibo messages"""
        try:
            if not self.cookies:
                logger.error("No cookies available, login might have failed")
                return
                
            session = requests.Session()
            for cookie in self.cookies:
                session.cookies.set(cookie['name'], cookie['value'])
                
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://api.weibo.com/chat/',
                'Origin': 'https://api.weibo.com',
                'Accept': 'application/json, text/plain, */*'
            }
            
            base_url = 'https://api.weibo.com/webim/groupchat/query_messages.json'
            
            while True:
                try:
                    current_timestamp = int(time.time() * 1000)
                    params = {
                        'convert_emoji': 1,
                        'query_sender': 1,
                        'count': 20,
                        'id': '5110127851995592',
                        'max_mid': 0,
                        'source': '209678993',
                        't': current_timestamp,
                        'from': 'pc',
                        'version': '2.0.0',
                        '_': current_timestamp
                    }
                    
                    response = session.get(
                        base_url,
                        params=params,
                        headers=headers,
                        timeout=30,
                        verify=False
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('result') is True and 'messages' in data:
                            for msg in data['messages']:
                                msg_id = str(msg.get('id', ''))
                                msg_time = msg['time']
                                
                                if msg_id not in self.processed_messages and msg_time > self.last_message_time:
                                    message = await self.process_message(msg)
                                    if message:
                                        self.processed_messages.add(msg_id)
                                        self.last_message_time = max(self.last_message_time, msg_time)
                                        logger.info(f"New message: {json.dumps(message, ensure_ascii=False)}")
                                        self.save_state()
                                        
                    await asyncio.sleep(5)
                    
                except requests.Timeout:
                    logger.warning("Request timeout, retrying...")
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.error(f"Error monitoring messages: {str(e)}")
                    await asyncio.sleep(5)
                    
        except Exception as e:
            logger.error(f"Error in message monitor: {str(e)}")
        finally:
            self.save_state()
            if 'session' in locals():
                session.close()
                
    async def start(self) -> None:
        """Start monitoring"""
        if await self.login():
            await self.monitor_messages()
        else:
            logger.error("Failed to start monitoring: login failed")
            
    def cleanup(self) -> None:
        """Cleanup resources"""
        self.save_state()
        if self.driver:
            self.driver.quit()
            self.driver = None