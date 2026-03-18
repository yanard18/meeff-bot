#!/usr/bin/env python3
from dotenv import load_dotenv
load_dotenv()

from src.bot_controller import BotController

if __name__ == '__main__':
    bot = BotController()
    bot.run()
