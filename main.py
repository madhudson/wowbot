import asyncio
import httpx
import discord
import os
import time
from keep_alive import keep_alive


class WoWBot(discord.Client):
  def __init__(self, *args, **kwargs):
    super(WoWBot, self).__init__(*args, **kwargs)
    self.prefix = '!'
    self.commands = [
      'gif',
      'init',
      'log'
    ]
    self.channel_id = None
    self.last_raiderio_dungeon_time = None
    self.last_log_id = None
    self.raider_io_attempts = 3
    self.raiderio_url = 'https://raider.io/api/v1/characters/profile?region=eu&realm=tarren%20mill&name={NAME}&fields=mythic_plus_recent_runs'
    self.warcraft_logs_url_link = 'https://www.warcraftlogs.com/reports/{ID}#fight=last'
    self.warcraft_logs_api = f'https://www.warcraftlogs.com:443/v1/reports/user/huddo?api_key={os.environ["LOGS_SECRET_V1"]}'


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

  
  def parse_recent_raiderio_runs(self, data):
    runs = data.get('mythic_plus_recent_runs', None)
    if not runs or len(runs) == 0:
      print('no runs detected')
      return None, None, None, None
    if runs[0]['completed_at'] == self.last_raiderio_dungeon_time:
      print('no new dungeon')
      return None, None, None, None
    self.last_dungeon_time = runs[0]['completed_at']
    upgraded = runs[0]['num_keystone_upgrades']
    name = runs[0]["dungeon"]
    level = runs[0]["mythic_level"]
    return runs[0]['url'], name, upgraded, level


  def parse_recent_warcraftlogs_runs(self, data):
    if not data or len(data) == 0:
      return
    if data[0].get('id', None) == self.last_log_id:
      return
    self.last_log_id = data[0].get('id', None)
    return data[0].get('id', None)
    
  
  async def raiderio(self, char_name):
    uri = self.raiderio_url.replace('{NAME}', char_name)
    for i in range(self.raider_io_attempts):
      try:
        data = await self.external_request(uri)
        url, name, upgraded, level = self.parse_recent_raiderio_runs(data)
        if not url:
          time.sleep(10)
          continue
        return url, name, upgraded, level
      except Exception as e:
        raise e
    raise Exception('no new mythic runs detected in raiderio')


  async def warcraft_logs(self):
    for i in range(self.raider_io_attempts):
      try:
        data = await self.external_request(self.warcraft_logs_api)
        recent = self.parse_recent_warcraftlogs_runs(data)
        if not recent:
          time.sleep(10)
          continue
        return recent
      except Exception as e:
        raise e
    raise Exception('no new mythic logs detected')

    
  async def log_and_io(self, char_name, msg):
    raider_url = None
    name = None
    upgraded = None
    logs_url = None
    level = None
    if not char_name:
      raise Exception('require character name')
    try:
      raider_url, name, upgraded, level = await self.raiderio(char_name)
    except Exception as e:
      raise e
    try:
      recent = await self.warcraft_logs()
      logs_url = self.warcraft_logs_url_link.replace('{ID}', recent)
    except Exception as e:
      raise e
    if upgraded >= 1:
      await msg.channel.send(f'**KEY COMPLETED IN TIME: {name} +{level} (+{upgraded})**')
    else:
      await msg.channel.send(f'**KEY COMPLETED OVER TIME: {name} +{level}**')
    await msg.channel.send(raider_url)
    await msg.channel.send(f'''{logs_url}
--------------------------------------------------------------------''')
  

  async def handle_command(self, cmd, args, msg):
    # if cmd == 'init' and msg.author.name == os.environ['ADMIN']:
    #  asyncio.ensure_future(self.raiderio())
    if cmd == 'gif':
      pass
    if cmd == 'log' and msg.author.name == os.environ['ADMIN']:
      try:
        await self.log_and_io(args, msg)
      except Exception as e:
        raise e
  
  
  def parse_message(self, msg):
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
    if not message.content.startswith('!'):
      return
    try:
      await self.handle_message(message)
    except Exception as e:
      await message.channel.send(str(e))
    await message.delete()

keep_alive()

wow_bot = WoWBot()
wow_bot.run(os.environ['DISCORD_TOKEN'])