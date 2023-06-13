from .emojiSteal import EmojiSteal

async def setup(bot):
    await bot.add_cog(EmojiSteal(bot))