#!/usr/bin/env python3
from src.bot_controller import BotController

if __name__ == '__main__':
    bot = BotController()
    # For now, we just run the state printer to test the new Vision architecture
    bot.run_state_printer()
