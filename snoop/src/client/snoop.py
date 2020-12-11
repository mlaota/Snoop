import asyncio
import datetime as dt
import discord as dc
import logging

from typing import Dict, Iterable, List


class SnoopClient(dc.Client):
    """
    This client continuously scans voice channels for deafened Members. When a
    Member is found to be deafened, they are added to a dictionary of suspects
    and the time at which they became a suspect is recorded. If enough time
    passes and the user is still deafened themselves, they are declared a snoop
    and removed from the voice channel.
    """

    def __init__(self, command_prefix: str, announcement_channel='commands',
                 **options):
        super().__init__(**options)
        self.command_prefix = command_prefix
        self.announcement_channel = announcement_channel

        self._probationary_period = dt.timedelta(minutes=5)
        self._suspects: Dict[dc.Member, dt.datetime] = {}

    # Override.
    async def on_ready(self):
        logging.info('Logged in as {0.user}'.format(self))
        self.loop.create_task(self._patrol())

    # Override.
    async def on_message(self, message: dc.Message):
        if message.author == self.user:
            return

        if self.user in message.mentions:
            await message.channel.send('*woof woof*')

    def set_probationary_period(self, period: dt.timedelta):
        if isinstance(period, dt.timedelta):
            logging.info(f'Probationary period set to {period}')
            self._probationary_period = period

    async def _patrol(self):
        """Infinitely "patrols" this clients' guilds.

        A patrol includes a search for suspects and the disconnection of
        suspects whose probationary period has ended.
        """
        TIC_SECONDS = 0.1
        while True:
            await self.wait_until_ready()
            self._find_suspects()
            await self._examine_all_suspects()
            await asyncio.sleep(TIC_SECONDS)

    def _find_suspects(self):
        """Iterates the members of this clients' guilds, searching for suspects.

        A suspect is a member who is self-deafened and not streaming. When a
        suspect is found, the time at which they were detected is recorded in
        ``self._suspects`` and their probationary period begins.
        """

        def without_suspects(members: Iterable[dc.Member]) -> List[dc.Member]:
            return [m for m in members if m not in self._suspects]

        for guild in self.guilds:
            for channel in guild.voice_channels:
                for member in without_suspects(channel.members):
                    if self._is_suspicious(member):
                        self._mark_suspicious(member)

    def _is_suspicious(self, member: dc.Member) -> bool:
        return member.voice.self_deaf and not member.voice.self_stream

    def _mark_suspicious(self, member: dc.Member):
        logging.info(f'Identified suspect: {member}')
        self._suspects[member] = dt.datetime.now()

    async def _examine_all_suspects(self):
        """Examines and updates the state of known suspects."""
        for member in tuple(self._suspects):
            await self._examine_suspect(member)

    async def _examine_suspect(self, suspect: dc.Member):
        """Examines a suspect.

        A suspect is removed from the suspect list if
        they are no longer suspicious. A suspect is kicked from their voice
        channel when the time since they were detected as suspicious has
        exceeded the probationary period.
        """
        if not suspect.voice.self_deaf:
            del self._suspects[suspect]
        elif self._probation_period_ended(suspect):
            await self._handle_snoop(suspect)
        elif self._probation_end_approaching(suspect):
            await self._sniff(suspect)

    def _probation_period_ended(self, member: dc.Member) -> bool:
        """Checks if the given member's probationary period has ended. If the
        member is not a suspect, this function returns False.
        """
        if member not in self._suspects:
            return False

        time_detected = self._suspects[member]
        probation_end = time_detected + self._probationary_period

        return dt.datetime.now() >= probation_end

    def _probation_end_approaching(self, member: dc.Member) -> bool:
        """Checks if the given member's probationary period will end within 2
        minutes. If the member is not a suspect, this function returns False.
        """
        if member not in self._suspects:
            return False

        now = dt.datetime.now()
        time_detected = self._suspects[member]
        probation_end = time_detected + self._probationary_period
        almost_end = probation_end - dt.timedelta(minutes=2)

        # For datetime equality.
        allowance = dt.timedelta(seconds=0.1)

        return almost_end - allowance <= now <= almost_end + allowance

    async def _sniff(self, suspect: dc.Member):
        channel = self._get_announcement_channel(suspect.guild)
        await channel.send(f'*sniff* {suspect.mention} *sniff*')

    async def _handle_snoop(self, snoop: dc.Member):
        """Disconnects the Member from the voice channel they are in and
        announces their snoopiness to ``self.announcement_channel``.
        """
        logging.info(f'Suspect {snoop} is a snoop')
        await self._disconnect_snoop(snoop)
        await self._announce_snoop(snoop)

    async def _disconnect_snoop(self, snoop: dc.Member):
        await snoop.move_to(None)
        del self._suspects[snoop]

    async def _announce_snoop(self, snoop: dc.Member):
        channel = self._get_announcement_channel(snoop.guild)
        await channel.send(f'BARK BARK BARK {snoop.mention} BARK BARK BARK')

    def _get_announcement_channel(self, guild: dc.Guild) -> dc.TextChannel:
        return dc.utils.get(guild.channels, name=self.announcement_channel)
