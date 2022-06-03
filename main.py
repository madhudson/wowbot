import discord
import os
import time
import threading


class WoWBot(discord.Client):
  def __init__(self, *args, **kwargs):
    super(WoWBot, self).__init__(*args, **kwargs)
    self.prefix = '!'
    self.commands = [
      'gif'
    ]

  async def test(self):
    while True:
      time.sleep(3)
      channels = 
      
  async def on_ready(self):
    print(f'logged in as {self.user}')

  async def on_message(self, message):
    if message.author == self.user:
      return
    print(f'got message!: {message.content}')


wow_bot = WoWBot()
x = threading.Thread(target=wow_bot.test)
x.start()
wow_bot.run(os.environ['DISCORD_TOKEN'])