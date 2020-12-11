import datetime as dt
import discord as dc
import logging
from typing import Dict


class SnoopClient(dc.Client):
    """
    This client continuously scans voice channels for deafened Members. When a
    Member is found to be deafened, they are added to a dictionary of suspects
    and the time at which they became a suspect is recorded. If enough time
    passes and the user is still deafened themselves, they are declared a snoop
    and removed from the voice channel.
    """

    def __init__(self, command_prefix: str, announcement_channel='commands'):
        super().__init__()
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
        await message.channel.send('*woof woof*')

    def set_probationary_period(self, period: dt.timedelta):
        if isinstance(period, dt.timedelta):
            logging.info(f'Probationary period set to {period}')
            self._probationary_period = period

    def _patrol(self):
        """Infinitely "patrols" this clients' guilds. A patrol includes a search
        for suspects and the disconnection of suspects whose probationary period
        has ended."""
        while True:
            await self.wait_until_ready()
            self._find_suspects()
            self._examine_suspects()

    def _find_suspects(self):
        """Iterates the members of this clients' guilds, searching for suspects.
        A suspect is a member who is self-deafened and not streaming. When a
        suspect is found, the time at which they were detected is recorded in
        ``self._suspects`` and their probationary period begins.
        """
        for guild in self.guilds:
            for voice_channel in guild:
                for member in voice_channel.members:
                    if self._is_suspicious(member):
                        self._suspects[member] = dt.datetime.now()

    def _is_suspicious(self, member: dc.Member) -> bool:
        return member.voice.self_deaf and member.voice.self_stream

    def _examine_suspects(self):
        """Examines and updates the state of known suspects.

        A suspect is removed from the suspect list if they have undeafened
        themselves. A suspect is kicked from their voice channel when the
        time since they were detected as deafened has exceeded the probationary
        period.
        """
        for member in self._suspects:
            if not member.voice.self_deaf:
                del self._suspects[member]
            elif self._probation_period_ended(member):
                self._remove_suspect(member)

    def _probation_period_ended(self, member: dc.Member) -> bool:
        """Checks if the given member's probationary period has ended. If the
        member is not a suspect, this function returns False."""
        if member not in self._suspects:
            return False

        time_detected = self._suspects[member]
        probation_end = time_detected + self._probationary_period

        return dt.datetime.now() <= probation_end

    def _remove_suspect(self, member: dc.Member):
        """Disconnects the Member from the voice channel they are in."""
        await member.move_to(None)


