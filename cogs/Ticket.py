import discord
from discord.ext import commands
from discord import app_commands
from mongo_controller import MongoController

class Ticket(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def log(self, member: discord.Member, action: str):
        channel = self.client.get_channel(1073219018586066944)
        await channel.send(f"```[{member}] -> [{action}]```")

    
    @app_commands.command(name="create_ticket", description="Creates a message to whcih you can react to open a ticket")
    @app_commands.checks.has_permissions(administrator=True)
    async def create_ticket(self, interaction: discord.Interaction):
        # Log command
        await self.log(interaction.user, interaction.command.name)
        view = TicketMenu()
        await interaction.response.send_message(embed=discord.Embed(title = "Buy your account here", description ='To create a ticket click here', color = discord.Colour.orange()), view=view)

    @app_commands.command(name="close_ticket", description="Closes your ticket")
    async def close_ticket(self, interaction: discord.Interaction):
        # Log command
        await self.log(interaction.user, interaction.command.name)
        channel_id = interaction.channel.id
        if MongoController().get_ticket_by_channel_id(channel_id) != []:
            # Send confirmation message
            await interaction.response.send_message("Are you sure you want to close this ticket?", view=CloseTicketMenu())
        else:
            await interaction.response.send_message("You can't use this command here", ephemeral=True)


class TicketMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.primary, emoji="🎟️", custom_id='ticket-1')
    async def open_ticket(self, interaction: discord.Interaction, button):
        user_id = interaction.user.id
        if MongoController().get_ticket_by_user_id(user_id) == []:
            await interaction.response.send_message("Ticket opened", ephemeral=True)
            ticket_channel = await interaction.guild.create_text_channel("ticket-{}".format(interaction.user.name))
            # Set permissions
            await ticket_channel.set_permissions(interaction.guild.get_role(interaction.guild.id), send_messages=False, read_messages=False)
            await ticket_channel.set_permissions(interaction.user, send_messages=True, read_messages=True, read_message_history=True, attach_files=True, embed_links=True, add_reactions=True)
            await ticket_channel.send("Welcome <@"+str(interaction.user.id)+">")
            embed = discord.Embed(title="Hello, how can I help you?",description="For further support, please ping a Moderator",color = discord.Colour.orange())
            embed.add_field(name='• `/buy <number_of_accounts>`', value='Use this command to create a checkout session.\nYou will be promped to choose a payment gateway.\nAfter choosing a payment method you will be asked to pay a certain amount for your accounts.\nYou will be able to **autocheckout** if you choose to pay with **USDT**.', inline=False)
            embed.add_field(name='• `/autocheckout <txid>`', value='To use this command you need to previously use `/buy <number_of_accounts>`.\nUse this command to autocheckout your order (**USDT** PAYMENTS ONLY).\nInput the **Txid** (transaction ID) and you will get your accounts **instantly**.\nMake sure we have enough stock for your order.\nPay exactly what we ask you to pay.\nCheckout Session is valid for **15 minutes**', inline=False)
            embed.add_field(name='• `/stock`', value='Use this command to check how many accounts are available.', inline=False)
            embed.add_field(name='• `/address`', value='Use this command to check the payment addresses that we have available.', inline=False)
            embed.add_field(name='• `/close_ticket`', value='Use this command to close your ticket.', inline=False)
            # WILL NEED TO CHANGE Icon url
            embed.set_footer(text="LandoCart | Your zalando plug", icon_url="https://cdn.discordapp.com/emojis/1071032086632349737.webp?size=240&quality=lossless")
            await ticket_channel.send(embed=embed)
            MongoController().insert_new_ticket(interaction.user.id, ticket_channel.id)
        else:
            await interaction.response.send_message("You already have an opened ticket", ephemeral=True)

class CloseTicketMenu(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id='close_ticket-1')
    async def close_ticket(self, interaction: discord.Interaction, button):
        channel_id = interaction.channel.id
        await interaction.response.send_message("Ticket closed", ephemeral=True)
        ticket_channel = interaction.channel
        await ticket_channel.delete()
        MongoController().delete_ticket_by_channel_id(channel_id)
        
    @discord.ui.button(label="No", style=discord.ButtonStyle.primary, emoji="❌", custom_id='close_ticket-2')
    async def cancel(self, interaction: discord.Interaction, button):
        await interaction.response.send_message("Ticket not closed", ephemeral=True)



async def setup(client:commands.Bot):
    await client.add_cog(Ticket(client))