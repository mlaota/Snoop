from typing import Tuple

import discord
import os
from snoop.src.client.snoop import SnoopClient
from snoop.src.utils.keep_alive import keep_alive


def _init_client() -> Tuple[SnoopClient, str]:
    intents = discord.Intents.default()
    intents.members = True
    snoop = SnoopClient(command_prefix='^', intents=intents)
    return snoop, os.getenv('SNOOP_SECRET')


if __name__ == '__main__':
    print('Using discord.py version {}'.format(discord.__version__))
    keep_alive()
    client, password = _init_client()
    client.run(password)
