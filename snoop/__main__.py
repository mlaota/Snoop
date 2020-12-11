import discord
import os
from snoop.src.client.snoop import SnoopClient
from snoop.src.utils.keep_alive import keep_alive

if __name__ == '__main__':
    password = os.getenv('SNOOP_SECRET')
    client = SnoopClient(command_prefix='^')
    print('Using discord.py version {}'.format(discord.__version__))
    keep_alive()
    client.run(password)
