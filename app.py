import discord
from discord.ext import commands
import logging
from cogs.Ticket import TicketMenu
from mongo_controller import MongoController
from dotenv import load_dotenv
import os

class Client(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned_or('!'), intents=discord.Intents.all())
    
    async def on_ready(self):
        print("Bot is ready")
        await self.tree.sync()
    
    async def setup_hook(self) -> None:
        self.add_view(TicketMenu())
        await self.load_extension('cogs.Ticket')
        await self.load_extension('cogs.Shop')
        await self.load_extension('cogs.Admin')


class Modal(discord.ui.Modal, title="Modal"):
    field1 = discord.ui.TextInput(label="label", placeholder="Field 1", min_length=3, max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        return await interaction.response.send_message("You submitted the modal")

client = Client()

@commands.has_permissions(administrator=True)
@client.tree.command(name="shutdown", description="Shuts down the bot")
async def shutdown(interaction: discord.Interaction):
    await interaction.response.send_message("Shutting down")
    await client.close()

@client.tree.command(name="modal", description="Modal")
async def modal(interaction: discord.Interaction):
    await interaction.response.send_modal(Modal())

load_dotenv()
token = os.getenv('TOKEN')
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='a')
client.run(token, log_handler=handler)