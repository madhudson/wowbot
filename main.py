import discord
import os
import time


class WoWBot(discord.Client):
  async def on_ready(self):
    print(f'logged in as {self.user}')


wow_bot = WoWBot()
wow_bot.run(os.environ['DISCORD_TOKEN'])
