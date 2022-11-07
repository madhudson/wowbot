import httpx
import discord
import os
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
  time: int


class WoWBot(discord.Client):
  def __init__(self, *args, **kwargs):
    super(WoWBot, self).__init__(*args, **kwargs)
    self.parse_secrets()
    self.prefix = '!'
    self.commands = [
      'log',
      'purge',
      'test'
    ]
    self.channel_id = None
    self.last_raiderio_dungeon_time = None
    self.last_log_id = None
    self.raider_io_attempts = 3
    self.warcraft_log_threshold = 5
    self.raiderio_url = 'https://raider.io/api/v1/characters/profile?region=eu&realm=tarren%20mill&name={NAME}&fields=mythic_plus_recent_runs'
    self.warcraft_logs_url_link = 'https://www.warcraftlogs.com/reports/{ID}/#fight={RUN}'
    self.warcraft_logs_api = f'https://www.warcraftlogs.com:443/v1/reports/user/huddo?api_key={self.secrets["LOGS_SECRET_V1"]}'
    self.warcraft_logs_detailed = f'https://www.warcraftlogs.com:443/v1/report/fights/[ID]?api_key={self.secrets["LOGS_SECRET_V1"]}'


  def parse_secrets(self):
    if os.environ.get('REPL_ID'):
      self.secrets = {
        'ADMIN': os.environ['ADMIN'],
        'DISCORD_TOKEN': os.environ['DISCORD_TOKEN'],
        'LOGS_SECRET_V1': os.environ['LOGS_SECRET_V1']
      }
      return
    with open('./secrets.json', 'r') as f:
        self.secrets = json.loads(f.read())
  
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
        print('REQUEST ERROR')
        raise e


  async def raiderio(self, char_name: str):
    uri: str = self.raiderio_url.replace('{NAME}', char_name)
    for i in range(self.raider_io_attempts):
      try:
        data: Dict[Any, Any] = await self.external_request(uri) 
        if not data.get('mythic_plus_recent_runs'):
          time.sleep(10)
          continue
        return data.get('mythic_plus_recent_runs')
      except Exception as e:
        print('[ERROR] raiderio')
        raise e

  
  async def get_recent_log(self):
    try:
      data: Dict[Any, Any] = await self.external_request(self.warcraft_logs_api)
    except Exception as e:
      print('[ERROR] warcraft logs')
      raise e
    if len(data) < 1:
      raise Exception('no warcraft logs found')
    recent_id = data[0].get('id')
    if not recent_id:
      raise Exception('cannot find warcraft log id')
    detailed_uri = self.warcraft_logs_detailed.replace('[ID]', recent_id)
    try:
      log_detailed = await self.external_request(detailed_uri)
    except Exception as e:
      raise Exception('cannot connect to detailed warcraft log end point')
    if not log_detailed.get('fights'):
      raise Exception('cannot find fights in: ', detailed_uri)
    return recent_id, log_detailed.get('fights')


  def parse_out_fights(self, log_report_id, logs, raider_io):
    fights = []
    for log in logs:
      completion_time = log.get('completionTime')
      if not completion_time: continue
      key_level = log.get('keystoneLevel')
      if not key_level: continue
      # TODO: dict of dungeon names as they're different
      for raider in raider_io:
        if completion_time == raider.get('clear_time_ms') and key_level == raider.get('mythic_level'):
          #https://www.warcraftlogs.com/reports/2pr9LfM7vT8GNd4j/#fight=1
          #'https://www.warcraftlogs.com/reports/{ID}/#fight={RUN}'
          log_uri = self.warcraft_logs_url_link.replace('{ID}', str(log_report_id))
          log_uri = log_uri.replace('{RUN}', str(log.get('id')))
          fights.append({
            'log_uri':  log_uri,
            'raider_uri': raider.get('url'),
            'in_time': True if raider.get('num_keystone_upgrades') > 0 else False,
            'upgrades': raider.get('num_keystone_upgrades'),
            'dungeon': raider.get('dungeon'),
            'level': raider.get('mythic_level')
          })
    return fights


  async def send_results(self, fights, msg):
    for fight in fights:
      if fight.get('in_time'):
        upgraded_str = f'{fight["dungeon"]} {fight["level"]} (+{fight["upgrades"]})'
        await msg.channel.send(f'**KEY COMPLETED IN TIME: {upgraded_str} )**')
      else:
        await msg.channel.send(f'**KEY COMPLETED OVER TIME: {fight["dungeon"]}  {fight["level"]}**')
      await msg.channel.send(fight["raider_uri"])
      await msg.channel.send(f'''{fight["log_uri"]})
--------------------------------------------------------------------''')
      time.sleep(4)


  async def log_it(self, args: List[str], msg: discord.Message):
    char_name = args[0]
    try:
      log_id, log = await self.get_recent_log()
    except Exception as e:
      raise e
    try:
      raider_io = await self.raiderio(char_name)
    except Exception as e:
      raise e
    fights = self.parse_out_fights(log_id, log, raider_io)
    await self.send_results(fights, msg)


  async def purge_channel(self, msg: discord.Message) -> None:
    try:
      purged = await msg.channel.purge(limit=20) 
    except Exception as e:
      raise e
      

  def is_admin(self, msg: discord.Message) -> bool:
    return msg.author.name == self.secrets['ADMIN']

  
  async def handle_command(self, cmd: str, args: List[str], msg: discord.Message) -> None:
    #  asyncio.ensure_future(self.raiderio())
    if cmd == 'purge' and self.is_admin(msg):
      try:
        await self.purge_channel(msg)
      except Exception as e:
        print('[ERROR] handle_command')
        raise e
    if cmd == 'log' and self.is_admin(msg):
      try:
        await self.log_it(args, msg)
      except Exception as e:
        print(e)
        raise e
    if cmd == 'test' and self.is_admin(msg):
      await self.log_it(args, msg)
  
  
  def parse_message(self, msg: discord.Message) -> Tuple[str, str]:
    all_cmd: str = msg.content[1:].split(' ')
    cmd: str = all_cmd[0]
    if cmd not in self.commands:
      raise Exception('can not find command, try !help')
    args = None if len(all_cmd) == 1 else all_cmd[1:]
    return cmd, args

      
  async def handle_message(self, msg: discord.Message) -> None:
    cmd: str = None
    args: List[str] = None
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

intents = discord.Intents.default()
intents.message_content = True

wow_bot = WoWBot(intents=intents)
wow_bot.run(wow_bot.secrets['DISCORD_TOKEN'])
