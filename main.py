import asyncio
import httpx
import discord
import json
import time
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass


@dataclass
class RaiderIO:
  url: str
  name: str
  upgraded: int
  level: str


class WoWBot(discord.Client):
  def __init__(self, *args, **kwargs):
    super(WoWBot, self).__init__(*args, **kwargs)
    with open('./secrets.json', 'r') as f:
        self.secrets = json.loads(f.read())
    self.prefix = '!'
    self.commands = [
      'log',
      'purge'
    ]
    self.channel_id = None
    self.last_raiderio_dungeon_time = None
    self.last_log_id = None
    self.raider_io_attempts = 3
    self.raiderio_url = 'https://raider.io/api/v1/characters/profile?region=eu&realm=tarren%20mill&name={NAME}&fields=mythic_plus_recent_runs'
    self.warcraft_logs_url_link = 'https://www.warcraftlogs.com/reports/{ID}#fight=last'
    self.warcraft_logs_api = f'https://www.warcraftlogs.com:443/v1/reports/user/huddo?api_key={self.secrets["LOGS_SECRET_V1"]}'


  async def get_channel_id(self, name: str) -> str:
    for chan in self.get_all_channels():
      if chan.name == name:
        self.channel_id = chan.id
      return self.get_channel(self.channel_id)

  
  async def external_request(self, uri: str='') -> Dict[Any, Any]:
    async with httpx.AsyncClient() as client:
      try:
        r = await client.get(uri) 
        return r.json()
      except Exception as e:
        raise e

  
  def parse_recent_raiderio_runs(self, data: Dict[Any, Any]) -> RaiderIO:
    raider_io_data: RaiderIO = RaiderIO(url='', name='', upgraded=0, level='')
    runs = data.get('mythic_plus_recent_runs', None) 
    if not runs or len(runs) == 0 or runs[0]['completed_at'] == self.last_raiderio_dungeon_time: 
      return raider_io_data
    self.last_dungeon_time = runs[0]['completed_at']
    raider_io_data.upgraded = runs[0]['num_keystone_upgrades']
    raider_io_data.name = runs[0]["dungeon"]
    raider_io_data.level = runs[0]["mythic_level"]
    raider_io_data.url = runs[0]['url'] 
    return raider_io_data


  def parse_recent_warcraftlogs_runs(self, data: List[Dict[Any, Any]]) -> str:
    if not data or len(data) == 0:
      return
    if data[0].get('id', None) == self.last_log_id:
      return
    self.last_log_id = data[0].get('id', None)
    return data[0].get('id', None)
    
  
  async def raiderio(self, char_name: str) -> RaiderIO:
    uri: str = self.raiderio_url.replace('{NAME}', char_name)
    for i in range(self.raider_io_attempts):
      try:
        data: Dict[Any, Any] = await self.external_request(uri)
        raider_io_data: RaiderIO = self.parse_recent_raiderio_runs(data)
        if not raider_io_data.url:
          time.sleep(10)
          continue
        return raider_io_data
      except Exception as e:
        raise e
    raise Exception('no new mythic runs detected in raiderio')


  async def warcraft_logs(self) -> str:
    for i in range(self.raider_io_attempts):
      try:
        data: Dict[Any, Any] = await self.external_request(self.warcraft_logs_api)
        recent: str = self.parse_recent_warcraftlogs_runs(data)
        if not recent:
          time.sleep(10)
          continue
        return recent
      except Exception as e:
        raise e
    raise Exception('no new mythic logs detected')

    
  async def log_and_io(self, char_name: str, msg: discord.Message) -> None:
    raider_io_data: RaiderIO = RaiderIO(name='', url='', upgraded=0, level='')
    if not char_name:
      raise Exception('require character name')
    try:
      raider_io_data = await self.raiderio(char_name)
    except Exception as e:
      raise e
    try:
      recent: str = await self.warcraft_logs()
      logs_url = self.warcraft_logs_url_link.replace('{ID}', recent)
    except Exception as e:
      raise e 
    if raider_io_data.upgraded >= 1:
      upgraded_str = f'{raider_io_data.name}+{raider_io_data.level} (+{raider_io_data.upgraded})'
      await msg.channel.send(f'**KEY COMPLETED IN TIME: {upgraded_str} )**')
    else:
      await msg.channel.send(f'**KEY COMPLETED OVER TIME: {raider_io_data.name} +{raider_io_data.level}**')
    await msg.channel.send(raider_io_data.url)
    await msg.channel.send(f'''{logs_url}
--------------------------------------------------------------------''')


  async def purge_channel(self, msg: discord.Message) -> None:
    try:
      purged = await msg.channel.purge(limit=20) 
    except Exception as e:
      raise e
      

  def is_admin(self, msg: discord.Message) -> bool:
    return msg.author.name == self.secrets['ADMIN']

  
  async def handle_command(self, cmd: str, args: str, msg: discord.Message) -> None:
    #  asyncio.ensure_future(self.raiderio())
    if cmd == 'purge' and self.is_admin(msg):
      try:
        await self.purge_channel(msg)
      except Exception as e:
        raise e
    if cmd == 'log' and self.is_admin(msg):
      try:
        await self.log_and_io(args, msg)
      except Exception as e:
        raise e
  
  
  def parse_message(self, msg: discord.Message) -> Tuple[str, str]:
    all_cmd: str = msg.content[1:].split(' ')
    cmd: str = all_cmd[0]
    if cmd not in self.commands:
      raise Exception('can not find command, try !help')
    args = None if len(all_cmd) == 1 else ' '.join(all_cmd[1:]) 
    return cmd, args

      
  async def handle_message(self, msg: discord.Message) -> None:
    cmd: str = None
    args: str = None
    try:
      cmd, args = self.parse_message(msg)
    except Exception as e:
      raise e
    try:
      await self.handle_command(cmd, args, msg)
    except Exception as e:
      raise e

  
  async def on_ready(self) -> None:
    print(f'logged in as {self.user}')

  
  async def on_message(self, message: discord.Message) -> None:
    if message.author == self.user:
      return
    if not message.content.startswith('!'):
      return
    try:
      await self.handle_message(message)
    except Exception as e:
      print(e)
      await message.channel.send(str(e))
    await message.delete()


wow_bot = WoWBot()
wow_bot.run(wow_bot.secrets['DISCORD_TOKEN'])
