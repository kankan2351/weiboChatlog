# /data/chats/oqz4c/workspace/chatbot/main.py
import asyncio
from chatbot.utils.config import Config
from chatbot.db.message_db import MessageDB
from chatbot.weibo.monitor import WeiboMonitor
from chatbot.handlers.ai_interface import AIInterface
from chatbot.language.detector import LanguageDetector
from openai import OpenAI
import signal
import sys
import argparse

class ChatBot:
    def __init__(self):
        """Initialize chatbot with all components"""
        self.config = Config()
        self.message_db = MessageDB(self.config)
        
        # Initialize OpenAI client
        # azure_config = self.config.get_azure_config()
        # self.openai_client = AzureOpenAI(
        #     azure_endpoint=azure_config['openai_endpoint'],
        #     api_key=azure_config['openai_key'],
        #     api_version=azure_config['api_version']
        # )
        deepseek_config = self.config.get_deepseek_config()
        self.openai_client = OpenAI(
            api_key=deepseek_config['api_key'], 
            base_url=deepseek_config['base_url']
        )
        
        # Initialize components
        self.lang_detector = LanguageDetector()
        self.ai_handler = AIInterface(
            self.config,
            self.openai_client,
            self.lang_detector,
            self.message_db
        )
        self.weibo_monitor = WeiboMonitor(
            self.config,
            self.message_db,
            self.ai_handler
        )
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """处理退出信号"""
        print("\nReceived signal to terminate...")
        asyncio.create_task(self.cleanup())
        sys.exit(0)

    async def cleanup(self):
        """清理资源"""
        await self.weibo_monitor.cleanup()
        print("Cleanup completed")

    async def run(self, start_monitor=True):
        """运行聊天机器人"""
        try:
            if start_monitor:
                await self.weibo_monitor.start()
            else:
                print("Chat mode started. Type your message (or 'quit' to exit):")
                while True:
                    try:
                        # 使用 asyncio 友好的方式读取输入
                        message = await asyncio.get_event_loop().run_in_executor(
                            None, input, "You: "
                        )
                        
                        if message.lower() == 'quit':
                            print("Exiting chat mode...")
                            break
                            
                        # 构造用户信息
                        user_info = {
                            "uid": "cli_user",
                            "name": "CLI User",
                            "user_name": "CLI User"
                        }
                        
                        # 调用 AI 处理
                        response = await self.ai_handler.ai_process_message(message, user_info)
                        if response:
                            print(f"\nBot: {response}\n")
                            
                    except Exception as e:
                        print(f"Error processing message: {str(e)}")
                        
        except Exception as e:
            print(f"Error running chatbot: {str(e)}")
        finally:
            await self.cleanup()

def main():
    """主入口函数"""
    parser = argparse.ArgumentParser(description='ChatBot CLI')
    parser.add_argument('--monitor', action='store_true', help='Start Weibo monitor')
    args = parser.parse_args()

    bot = ChatBot()
    asyncio.run(bot.run(start_monitor=args.monitor))

if __name__ == "__main__":
    main()
[
    {
        "command_name": "Terminal.run_command",
        "args": {
            "cmd": "python -m chatbot.main"
        }
    }
]
