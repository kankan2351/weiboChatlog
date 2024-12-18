# src/main.py
import os
import sys
import asyncio
import argparse
from pathlib import Path
from typing import Optional
import logging

from handlers.ai_interface import AIInterface
from utils.config import config
from utils.logger import get_logger
from weibo.monitor import WeiboMonitor

logger = get_logger(__name__)

class ChatBotSystem:
    def __init__(self):
        """Initialize the chatbot system"""
        self.ai_handler = AIInterface(config)
        self.weibo_monitor = None
        
    async def start_weibo_monitor(self, username: str, password: str) -> None:
        """Start Weibo monitoring mode"""
        try:
            self.weibo_monitor = WeiboMonitor(
                ai_handler=self.ai_handler,
                username=username,
                password=password
            )
            await self.weibo_monitor.start()
        except Exception as e:
            logger.error(f"Error starting Weibo monitor: {str(e)}")
            sys.exit(1)
            
    async def start_chat_mode(self) -> None:
        """Start interactive chat mode"""
        print("Starting chat mode (Ctrl+C to exit)")
        print("-" * 50)
        
        try:
            while True:
                message = input("You: ").strip()
                if not message:
                    continue
                    
                result = await self.ai_handler.process_message(
                    content=message,
                    user="CLI_USER"
                )
                
                print("\nBot:", result.get('response', 'Error processing message'))
                print("-" * 50)
                
        except KeyboardInterrupt:
            print("\nExiting chat mode...")
        except Exception as e:
            logger.error(f"Error in chat mode: {str(e)}")
            
    def parse_args(self) -> argparse.Namespace:
        """Parse command line arguments"""
        parser = argparse.ArgumentParser(
            description="Enhanced ChatBot System with Weibo Monitoring"
        )
        
        parser.add_argument(
            '--mode',
            choices=['chat', 'weibo'],
            default='chat',
            help='Operation mode: chat or weibo monitoring'
        )
        
        parser.add_argument(
            '--username',
            help='Weibo username (required for weibo mode)'
        )
        
        parser.add_argument(
            '--password',
            help='Weibo password (required for weibo mode)'
        )
        
        args = parser.parse_args()
        
        # Validate arguments
        if args.mode == 'weibo' and (not args.username or not args.password):
            parser.error("Weibo mode requires both username and password")
            
        return args
        
    async def run(self) -> None:
        """Run the system"""
        args = self.parse_args()
        
        try:
            if args.mode == 'weibo':
                await self.start_weibo_monitor(args.username, args.password)
            else:
                await self.start_chat_mode()
                
        except Exception as e:
            logger.error(f"System error: {str(e)}")
            sys.exit(1)
            
    def cleanup(self) -> None:
        """Cleanup resources"""
        if self.weibo_monitor:
            self.weibo_monitor.cleanup()

def main():
    """Main entry point"""
    # Ensure data directories exist
    for path in ['logs', 'data', 'chroma_db']:
        Path(path).mkdir(parents=True, exist_ok=True)
    
    # Initialize system
    system = ChatBotSystem()
    
    try:
        # Run system
        asyncio.run(system.run())
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
    finally:
        system.cleanup()

if __name__ == "__main__":
    main()
