import discord
import io
import re
import aiohttp
import asyncio
from dataclasses import dataclass
from redbot.core import commands
from typing import Optional, List
from itertools import zip_longest

MISSING_EMOJIS = "Can't find emojis or stickers in that message."
MISSING_REFERENCE = "Reply to a message with this command to steal an emoji."
MESSAGE_FAIL = "I couldn't grab that message, sorry."
EMOJI_FAIL = "❌ Failed to upload"
EMOJI_SLOTS = "⚠ This server doesn't have any more space for emojis!"
INVALID_EMOJI = "Invalid emoji or emoji ID."

@dataclass(init=True, order=True, frozen=True)
class StolenEmoji:
    animated: bool
    name:str
    id: int

    @property
    def url(self):
        return f"https://cdn.discordapp.com/emojis/{self.id}.{'gif' if self.animated else 'png'}"
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        return isinstance(other, StolenEmoji) and self.id == other.id

class EmojiSteal(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @staticmethod
    def get_emojis(content: str) -> Optional[List[StolenEmoji]]:
        results = re.findall(r"<(a?):(\w+):(\d{10,20})>", content)
        return [StolenEmoji(*result) for result in results]
    
    @staticmethod
    def available_emoji_slots(guild: discord.Guild, animated: bool):
        current_emojis = len([em for em in guild.emojis if em.animated == animated])
        return guild.emoji_limit - current_emojis
    
    async def steal_ctx(self, ctx: commands.Context) -> Optional[List[StolenEmoji]]:
        reference = ctx.message.reference
        if not reference:
            await ctx.send(MISSING_REFERENCE)
            return None
        message = await ctx.channel.fetch_message(reference.message_id)
        if not message:
            await ctx.send(MESSAGE_FAIL)
            return None
        emojis = self.get_emojis(message.content)
        if not emojis:
            await ctx.send(MISSING_EMOJIS)
            return None
        return emojis
    
    @commands.group(name="steal", aliases=["emojisteal"], invoke_without_command=True)
    async def steal_command(self, ctx: commands.Context):
        """Steals the emojis of the message you reply to. Can also upload them with [p]steal upload."""
        if not (emojis := await self.steal_ctx(ctx)):
            return
        response = '\n'.join([emoji.url for emoji in emojis])
        print(response)
        await ctx.send(response)

    @steal_command.command(name="upload")
    @commands.guild_only()
    @commands.has_permissions(manage_emojis=True)
    @commands.bot_has_permissions(manage_emojis=True, add_reactions=True)
    async def steal_upload_command(self, ctx: commands.Context):
        """Steals emojis you reply to and uploads them to this server."""
        if not (emojis := await self.steal_ctx(ctx)):
            return
        
        emojis = list(dict.fromkeys(emojis))
        print(emojis)

        async with aiohttp.ClientSession() as session:
            for emoji in emojis:
                if not self.available_emoji_slots(ctx.guild, emoji.animated):
                    return await ctx.send(EMOJI_SLOTS)
                if not emoji:
                    break
                try:
                    async with session.get(emoji.url) as resp:
                        image = io.BytesIO(await resp.read()).read()
                    added = await ctx.guild.create_custom_emoji(emoji.name, image=image)
                except Exception as error:
                    return await ctx.send(f"{EMOJI_FAIL} {emoji.name}, {type(error).__name__}: {error}")
                try:
                    await ctx.message.add_reaction(added)
                except:
                    pass

    @commands.command()
    async def get_emoji(self, ctx: commands.Context, *, emoji: str):
        """Get the image link for custom emojis or an emoji ID."""
        emoji = emoji.strip()
        if emoji.isnumeric():
            emojis = [StolenEmoji(False, "e", int(emoji)), StolenEmoji(True, "e", int(emoji))]
        elif not (emojis := self.get_emojis(emoji)):
            await ctx.send(INVALID_EMOJI)
            return
        await ctx.send('\n'.join(emoji.url for emoji in emojis))


