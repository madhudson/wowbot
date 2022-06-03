import asyncio
import discord
import os
import time


class WoWBot(discord.Client):
  def __init__(self, *args, **kwargs):
    super(WoWBot, self).__init__(*args, **kwargs)
    self.prefix = '!'
    self.commands = [
      'gif'
    ]
    self.channel_id = None

  async def test(self):
    while True:
      time.sleep(5)
      if not self.channel_id:
        for chan in self.get_all_channels():
          if chan.name == 'general':
            self.channel_id = chan.id
      else:
        chan = self.get_channel(self.channel_id)
        print(chan)
        await chan.send('testing this out')
        return


  async def on_ready(self):
    print(f'logged in as {self.user}')

  async def on_message(self, message):
    if message.author == self.user:
      return
    asyncio.ensure_future(self.test())
    print('tis done')


wow_bot = WoWBot()
wow_bot.run(os.environ['DISCORD_TOKEN'])