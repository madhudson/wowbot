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
      'gif',
      'init'
    ]
    self.channel_id = None
    self.last_dungeon_time = None
    self.raider_io_attempts = 3
    self.raiderio_url = 'https://raider.io/api/v1/characters/profile?region=eu&realm=tarren%20mill&name={NAME}&fields=mythic_plus_recent_runs'


  async def get_channel_id(self, name):
    for chan in self.get_all_channels():
      if chan.name == name:
        self.channel_id = chan.id
      return self.get_channel(self.channel_id)

  
  async def external_request(self, uri=None):
    async with httpx.AsyncClient() as client:
      try:
        r = await client.get(uri)
        print('got a response, parsing')
        return r.json()
      except Exception as e:
        raise e

  
  def parse_recent_runs(self, data):
    runs = data.get('mythic_plus_recent_runs', None)
    if not runs or len(runs) == 0:
      print('no runs detected')
      return
    if runs[0]['completed_at'] == self.last_dungeon_time:
      print('no new dungeon')
      return
    self.last_dungeon_time = runs[0]['completed_at']
    return runs[0]['url']

  
  async def raiderio(self, char_name):
    uri = self.raiderio_url.replace('{NAME}', char_name)
    for i in range(self.raider_io_attempts):
      try:
        data = await self.external_request(uri)
        recent = self.parse_recent_runs(data)
        if not recent:
          time.sleep(10)
          continue
        return recent
      except Exception as e:
        raise e
    raise Exception('no new mythic runs detected')

    
  async def log_and_io(self, char_name, msg):
    raider_url = None
    logs_url = None
    if not char_name:
      raise Exception('require character name')
    try:
      raider_url = await self.raiderio(char_name)
    except Exception as e:
      raise e
    
    # get most recent raider io run 
    # get most recent warcraft log
  

  async def handle_command(self, cmd, args, msg):
    print('got command: ', cmd)
    print('got args: ', args)
    if cmd == 'init' and msg.author.name == os.environ['ADMIN']:
      asyncio.ensure_future(self.raiderio())
    if cmd == 'gif':
      pass
    if cmd == 'log' and msg.author.name == os.environ['ADMIN']:
      try:
        await self.log_and_io(args, msg)
      except Exception as e:
        raise e
  
  
  def parse_message(self, msg):
    if msg.content.startswith('!'):
      all_cmd = msg.content[1:].split(' ')
      cmd = all_cmd[0]
      if cmd not in self.commands:
        raise Exception('can not find command, try !help')
      args = None if len(all_cmd) == 1 else ' '.join(all_cmd[1:]) 
      return cmd, args

      
  async def handle_message(self, msg):
    cmd = None
    args = None
    try:
      cmd, args = self.parse_message(msg)
    except Exception as e:
      raise e
    try:
      await self.handle_command(cmd, args, msg)
    except Exception as e:
      raise e

  
  async def on_ready(self):
    print(f'logged in as {self.user}')

  
  async def on_message(self, message):
    if message.author == self.user:
      return
    try:
      response = await self.handle_message(message)
      if not response: 
        return
    except Exception as e:
      await message.channel.send(str(e))
  


wow_bot = WoWBot()
wow_bot.run(os.environ['DISCORD_TOKEN'])