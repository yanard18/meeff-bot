#!/usr/bin/env python3
from src.bot_controller import BotController

if __name__ == '__main__':
    bot = BotController()
    # Runs the loop that continuously prints the current screen state
    bot.run_state_printer()
