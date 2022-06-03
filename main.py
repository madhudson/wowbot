import asyncio
import aiohttp
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
    self.last_dungeon = None
    self.raiderio_url = 'https://raider.io/api/v1/characters/profile?region=eu&realm=tarren%20mill&name=turdbrush&fields=mythic_plus_recent_runs'

  async def external_request(self, uri=None):
    with aiohttp.ClientSession() as session:
      async with session.get(uri) as resp:
        data = await resp.json()
        print(data)
  
  async def raiderio(self):
    while True:
      time.sleep(3)
      if not self.channel_id:
        for chan in self.get_all_channels():
          if chan.name == 'general':
            self.channel_id = chan.id
      else:
        chan = self.get_channel(self.channel_id)
        data = await self.external_request(self.raiderio_url)
        print(data)


  async def on_ready(self):
    print(f'logged in as {self.user}')

  async def on_message(self, message):
    if message.author == self.user:
      return
    asyncio.ensure_future(self.raiderio())
    print('tis done')


wow_bot = WoWBot()
wow_bot.run(os.environ['DISCORD_TOKEN'])