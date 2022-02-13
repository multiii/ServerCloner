import random
import asyncio

import nextcord as discord
from nextcord.ext import commands
from tinydb import TinyDB, Query

from utils import resources
from utils.storage import YAMLStorage

User = Query()

db = TinyDB("database.yml", storage=YAMLStorage)

pr = db.table("prefix")

class Utility(commands.Cog):
  def __init__(self, bot):
    self.bot = bot

  @commands.command(
    name="clone",
    brief="clone a server"
  )
  async def _clone(self, ctx, guild1: discord.Guild):
    guild2 = ctx.guild

    m = await resources.default.embed(
      msg=ctx.message,
      title="This server will be overwritten with the channels of another server!",
      description="React to the message to confirm the cloning process."
    )

    await m.add_reaction("<a:caught:939883190825418843>")

    try:
      await self.bot.wait_for("reaction_add", check=lambda r, u: u.id == ctx.author.id and r.message.id == m.id, timeout=30.0)

    except asyncio.TimeoutError:
      return await m.delete()

    for channel in guild2.channels:
      await channel.delete()

    for role in guild2.roles:
      try:
        await role.delete()
      
      except discord.errors.HTTPException:
        continue

    roles = {}

    for role1 in guild1.roles:
      try:
        role2 = await guild2.create_role(
          name=role1.name,
          permissions=role1.permissions,
          colour=role1.colour,
          hoist=role1.hoist,
          mentionable=role1.mentionable,
          reason="Server cloning"
        )
      except Exception as e:
        raise e

      roles.update({role1.id: role2.id})

    # positions = {guild2.get_role(role2): guild1.get_role(role1).position for role1, role2 in roles.items() if guild2.get_role(role2).position < guild2.get_member(self.bot.user.id).top_role.position}    

    # await guild2.edit_role_positions(positions=positions)

    categories = {}
    channels = {}

    for cat1 in guild1.categories:
      overwrites = {}

      for key, value in channel.overwrites.items():
        if isinstance(key, discord.Role):
          role = guild2.get_role(roles[key.id])

          overwrites.update({role: value})

        elif isinstance(key, discord.Member):
          member = guild2.get_member(key.id)

          if member is not None:
            overwrites.update({member: value})
            
      cat2 = await guild2.create_category_channel(
        name=cat1.name,
        position=cat1.position,
        reason="Server cloning",
        overwrites=overwrites
      )

      categories.update({cat1.id: cat2.id})

    for channel in guild1.text_channels:
      overwrites = {}

      for key, value in channel.overwrites.items():
        if isinstance(key, discord.Role):
          role = guild2.get_role(roles[key.id])

          overwrites.update({role: value})

        elif isinstance(key, discord.Member):
          member = guild2.get_member(key.id)

          if member is not None:
            overwrites.update({member: value})

      if channel.category is None:
        cat = None

      else:
        cat = guild2.get_channel(categories[channel.category.id])

      channel2 = await guild2.create_text_channel(
        name=channel.name,
        topic=channel.topic,
        category=cat,
        position=channel.position,
        slowmode_delay=channel.slowmode_delay,
        nsfw=channel.is_nsfw(),
        reason="Server cloning",
        overwrites=overwrites
      )

      for thread in channel.threads:
        await channel2.create_thread(
          name=thread.name,
          auto_archive_duration=thread.auto_archive_duration,
          type=thread.type,
          reason="Server cloning"
        )

      channels.update({channel.id: channel2.id})

    for channel in guild1.voice_channels:
      overwrites = {}

      for key, value in channel.overwrites.items():
        if isinstance(key, discord.Role):
          role = guild2.get_role(roles[key.id])

          overwrites.update({role: value})

        elif isinstance(key, discord.Member):
          member = guild2.get_member(key.id)

          if member is not None:
            overwrites.update({member: value})

      if channel.category is None:
        cat = None

      else:
        cat = guild2.get_channel(categories[channel.category.id])

      await guild2.create_voice_channel(
        name=channel.name,
        category=cat,
        position=channel.position,
        bitrate=channel.bitrate,
        user_limit=channel.user_limit,
        rtc_region=channel.rtc_region,
        overwrites=overwrites
      )

    members1 = set([member.id for member in guild1.members])
    members2 = [member.id for member in guild2.members]

    for member in members1.intersection(members2):

      member1 = guild1.get_member(member)
      member2 = guild2.get_member(member)

      await member2.add_roles(*[guild2.get_role(roles[role.id]) for role in member1.roles])

    for channel1_id, channel2_id in channels.items():
      channel1 = self.bot.get_channel(channel1_id)
      channel2 = self.bot.get_channel(channel2_id)

      webhook = await channel2.create_webhook(name="Message Cloner")

      print(channel1.name)

      async for message in channel1.history(oldest_first=True):
        if message.author is None:
          continue
          
        kwargs = {
          "content": message.content if message.content != "" else "[No Message]",
          "username": f"{message.author.name}#{message.author.discriminator}",
          "avatar_url": message.author.display_avatar.url
        }

        if len(message.attachments) > 0:
          kwargs.update({
            "files": [await attachment.to_file(
              spoiler=attachment.is_spoiler()
            ) for attachment in message.attachments]
          })

        await webhook.send(**kwargs)

    await resources.default.embed(
      msg=random.choice(guild2.text_channels),
      title="Server cloned successfully!"
    )

  @commands.command(
    name="prefix",
    brief="used to change the bot's prefix"
  )
  @commands.has_permissions(manage_guild=True)
  async def _prefix(self, ctx, *, prefix):
    if len(prefix) > 3:
      return await resources.error.embed(
        msg=ctx.message,
        title="Prefix exceeded 3 characters!",
        description=f"Your bot prefix, for the server `{ctx.guild.name}` cannot exceeed 3 characters. Please retry the command"
      )

    await resources.default.embed(
      msg=ctx.message,
      title="Prefix successfully changed!",
      description=f"Your bot prefix, for the server `{ctx.guild.name}` was successfully changed to {prefix}"
    )

    pr.upsert({"id": ctx.guild.id, "prefix": prefix}, User.id == ctx.guild.id)

def setup(bot):
  bot.add_cog(Utility(bot))