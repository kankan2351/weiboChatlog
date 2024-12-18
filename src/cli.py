# src/cli.py
import asyncio
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

from handlers.ai_interface import AIInterface
from utils.config import config
from utils.logger import get_logger

logger = get_logger(__name__)

class ChatBotCLI:
    def __init__(self):
        """Initialize ChatBot CLI interface"""
        self.ai_handler = AIInterface(config)
        
    async def summarize(self, args: argparse.Namespace) -> None:
        """Handle chat history summarization"""
        result = await self.ai_handler.summarize_history(
            time_range=args.time_range,
            summary_type=args.type
        )
        if result['success']:
            print("\nSummary:")
            print("-" * 50)
            print(result['summary'])
        else:
            print(f"Error: {result['message']}")
            
    async def search(self, args: argparse.Namespace) -> None:
        """Handle message search"""
        result = await self.ai_handler.search_messages(
            query=args.query,
            time_range=args.time_range
        )
        if result['success']:
            print(f"\nFound {result['count']} messages:")
            print("-" * 50)
            for msg in result['results']:
                print(f"[{msg['time']}] {msg['from']['name']}: {msg['content']}")
        else:
            print(f"Error: {result['message']}")
            
    async def suggest(self, args: argparse.Namespace) -> None:
        """Handle suggestion generation"""
        result = await self.ai_handler.get_suggestions(question=args.question)
        if result['success']:
            print("\nSuggestions:")
            print("-" * 50)
            for i, sugg in enumerate(result['suggestions'], 1):
                print(f"{i}. {sugg['suggestion']}")
        else:
            print(f"Error: {result['message']}")
            
    async def analyze(self, args: argparse.Namespace) -> None:
        """Handle chat analysis"""
        result = await self.ai_handler.analyze_activity(time_range=args.time_range)
        if result['success']:
            print("\nChat Analysis:")
            print("-" * 50)
            for key, value in result['insights'].items():
                print(f"{key}: {value}")
        else:
            print(f"Error: {result['message']}")
            
    async def chat(self, args: argparse.Namespace) -> None:
        """Interactive chat mode"""
        print("Starting interactive chat mode (Ctrl+C to exit)")
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
                
                print("\nBot:", result['response'])
                print("-" * 50)
                
        except KeyboardInterrupt:
            print("\nExiting chat mode...")
            
    def run(self) -> None:
        """Run the CLI application"""
        parser = argparse.ArgumentParser(
            description="ChatBot CLI - Interact with enhanced chat bot features"
        )
        
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Summarize command
        sum_parser = subparsers.add_parser('summarize', help='Summarize chat history')
        sum_parser.add_argument('--time-range', choices=['24h', '7d', '30d'], 
                              default='24h', help='Time range for summary')
        sum_parser.add_argument('--type', choices=['brief', 'detailed', 'topics'],
                              default='brief', help='Type of summary')
        
        # Search command
        search_parser = subparsers.add_parser('search', help='Search messages')
        search_parser.add_argument('query', help='Search query')
        search_parser.add_argument('--time-range', choices=['24h', '7d', '30d', 'all'],
                                 default='all', help='Time range for search')
        
        # Suggest command
        suggest_parser = subparsers.add_parser('suggest', help='Get suggestions')
        suggest_parser.add_argument('question', help='Question to get suggestions for')
        
        # Analyze command
        analyze_parser = subparsers.add_parser('analyze', help='Analyze chat activity')
        analyze_parser.add_argument('--time-range', choices=['24h', '7d', '30d'],
                                  default='7d', help='Time range for analysis')
        
        # Chat command
        chat_parser = subparsers.add_parser('chat', help='Start interactive chat mode')
        
        args = parser.parse_args()
        
        if not args.command:
            parser.print_help()
            return
            
        command_map = {
            'summarize': self.summarize,
            'search': self.search,
            'suggest': self.suggest,
            'analyze': self.analyze,
            'chat': self.chat
        }
        
        asyncio.run(command_map[args.command](args))

if __name__ == "__main__":
    cli = ChatBotCLI()
    cli.run()