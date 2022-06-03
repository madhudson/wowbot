import asyncio
import httpx
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
    self.last_dungeon_time = None
    self.raiderio_url = 'https://raider.io/api/v1/characters/profile?region=eu&realm=tarren%20mill&name=turdbrush&fields=mythic_plus_recent_runs'

  async def external_request(self, uri=None):
    async with httpx.AsyncClient() as client:
      r = await client.get(uri)
      print('got a response, parsing')
      return r.json()

  def parse_recent_runs(self, data):
    runs = data.get('mythic_plus_recent_runs', None)
    if not runs or len(runs) == 0:
      return
    if runs[0]['completed_at'] == self.last_dungeon_time:
      print('no new dungeon')
      return
    self.last_dungeon_time = runs[0]['completed_at']
    return runs[0]['url']
  
  async def raiderio(self):
    while True:
      if not self.channel_id:
        for chan in self.get_all_channels():
          if chan.name == 'general':
            self.channel_id = chan.id
      else:
        chan = self.get_channel(self.channel_id)
        data = None
        try:
          data = await self.external_request(self.raiderio_url)
        except Exception as e:
          await chan.send(e)
          return
        parsed = self.parse_recent_runs(data)
        if parsed:
          await chan.send(parsed)
      time.sleep(10)

  def parse_message(self, msg):
    if msg.content.startswith('!'):
      
  
  async def on_ready(self):
    print(f'logged in as {self.user}')

  async def on_message(self, message):
    if message.author == self.user:
      return
    parsed = self.parse_message(message)
    if not parsed: 
      return
    asyncio.ensure_future(self.raiderio())
    print('tis done')


wow_bot = WoWBot()
wow_bot.run(os.environ['DISCORD_TOKEN'])