import discord
import logging
from discord.ext import commands
from discord import app_commands
from mongo_controller import MongoController
from binance_controller import BinanceController
from datetime import datetime
import os

class Shop(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def log(self, member: discord.Member, action: str):
        channel = self.client.get_channel(1073219018586066944)
        await channel.send(f"```[{member}] -> [{action}]```")
    
    @app_commands.command(name="address", description="Select menu for payment addresses")
    async def address(self, interaction: discord.Interaction):
        # Log command
        await self.log(interaction.user, interaction.command.name)
        view = SelectAddressInfoView()
        await interaction.response.send_message("Select payment option", view=view)


    @app_commands.command(name="buy", description="Buy accounts")
    async def buy(self, interaction: discord.Interaction, number_of_accounts: str):
        # Log command
        await self.log(interaction.user, f'{interaction.command.name} {number_of_accounts}')
        # Make sure that this command is being used in a ticket channel
        # Get interaction channel
        channel = interaction.channel.name
        if "ticket" in channel:
            # Check if user has a checkout session
            checkout_session = MongoController().get_pending_checkout_session_by_user_id(str(interaction.user.id))
            if checkout_session == [] or checkout_session == None:
                # Create new checkout session
                MongoController().create_new_checkout_session(str(interaction.user.id), int(number_of_accounts))
            else:
                # User can't have more than one checkout session
                return await interaction.response.send_message("You already have a checkout session", ephemeral=True)
            await interaction.response.send_message(embed=discord.Embed(title = f"Checking out {number_of_accounts} accounts", description="Select payment method to get the address.", color = discord.Colour.orange()).add_field(name="More Information", value="If you pay with **USDT** you will be able to **instantly checkout**.\n Cancel your checkout anytime.\nCheckout is valid for **15 minutes**."), view=SelectAddressView("buy"))

        else:
            await interaction.response.send_message("This command can only be used in a ticket channel", ephemeral=True)

    @app_commands.command(name="autocheckout", description="Autocheckout with Txid - USDT payments only")
    async def autocheckout(self, interaction: discord.Interaction, txid: str):
        # Log command
        await self.log(interaction.user, f'{interaction.command.name} {txid}')
        # Check if user has a checkout session
        checkout_session = MongoController().get_pending_checkout_session_by_user_id(str(interaction.user.id))
        if checkout_session == [] or checkout_session == None:
            return await interaction.response.send_message("You don't have a checkout session", ephemeral=True)
        elif checkout_session['status'] == "pending" and checkout_session['coin'] == 'USDT':
            # Check if txid exists 
            if BinanceController().get_deposit_by_txid("USDT", txid) != None:
                # Check if amount is correct
                if float(BinanceController().get_deposit_by_txid("USDT", txid)['amount']) >= int(checkout_session['total_price']):
                    # Check if date is correct
                    if datetime.fromtimestamp(int(BinanceController().get_deposit_by_txid("USDT", txid)['insertTime'])/1000) >= checkout_session['createdAt']:
                        # Send n_accounts
                        # Send accs in string if number_of_accounts is < 20
                        number_of_accounts = checkout_session['number_of_accounts']
                        client = checkout_session['user_id']
                        payment_method = checkout_session['coin']
                        total_price = checkout_session['total_price']
                        account_list = [acc['account'] for acc in MongoController().get_n_available_accounts(number_of_accounts)]
                        if len(account_list) != number_of_accounts:
                            return await interaction.response.send_message("There are not enough accounts available.\n For further support ping a Moderator", ephemeral=True)
                        if number_of_accounts < 20:
                            await interaction.response.send_message("Here are your accounts: \n" + "```" +  "\n".join(account_list) + "```")
                        else:
                            # Send accs in file if number_of_accounts is >= 20
                            with open("accounts.txt", "w") as f:
                                f.write("Here are your accounts: \n" + "\n".join(account_list))
                            await interaction.response.send_message(file=discord.File(fp="accounts.txt", filename="accounts.txt"))
                            os.remove("accounts.txt")
                        # Update accounts in database to status = sold
                        for acc in account_list:
                            MongoController().update_account_status(acc, "sold")
                        # Create Finance statement
                        finance_statement = {
                            "Type": "Income",
                            "Product": "Account",
                            "Quantity": number_of_accounts,
                            "Unit_price": round(total_price / number_of_accounts,2),
                            "Total_Price": total_price,
                            "Payment_Method": payment_method,
                            "Client_id": client,
                            "Date": datetime.now()
                        }
                        MongoController().insert_finance_statement(finance_statement)

                        # Update client document
                        # 1. Check if client exists
                        if MongoController().get_client(client) is not None:
                            # 2. Update client document
                            purchase = {
                                "Date": datetime.now(),
                                "Number_of_accounts": number_of_accounts,
                                "Total_price": total_price,
                                "Payment_method": payment_method,
                                "Account_list": account_list
                            }
                            MongoController().add_new_client_purchase(client, purchase)
                        else:
                            # 3. Create client document
                            account_purchases = [{
                                "Date": datetime.now(),
                                "Number_of_accounts": number_of_accounts,
                                "Total_price": total_price,
                                "Payment_method": payment_method,
                                "Account_list": account_list
                            }]
                            MongoController().insert_new_client(client.strip("<@>"), datetime.now(), 0, account_purchases, [], [], 0)

                        # Update checkout session status to completed
                        MongoController().set_session_status(checkout_session['_id'], "completed")
                    else:
                        await interaction.response.send_message(f"Transaction date is older than checkout session", ephemeral=True)
                else:
                    await interaction.response.send_message(f"Amount is not correct: {BinanceController().get_deposit_by_txid('USDT', txid)['amount']} ≠ {checkout_session['total_price']}", ephemeral=True)
            else:
                await interaction.response.send_message("Txid does not exist", ephemeral=True)
        return await interaction.response.send_message("Error, most likely your checkout has a coin different than USDT", ephemeral=True)

    @app_commands.command(name="cancel_checkout", description="Cancel Checkout Session")
    @app_commands.checks.has_permissions(administrator=True)
    async def cancel_checkout(self, interaction: discord.Interaction, client: str):
        # Log command
        await self.log(interaction.user, f'{interaction.command.name} {client}')
        client_id = client.strip('<@>')
        checkout_session = MongoController().get_pending_checkout_session_by_user_id(str(client_id))
        if checkout_session == None:
            return await interaction.response.send_message("No pending checkout session", ephemeral=True)
        MongoController().delete_checkout_session(checkout_session['_id'])
        await interaction.response.send_message("Checkout session cancelled", ephemeral=False)


class SelectAddressInfoView(discord.ui.View):
    def __init__(self, invoker=None):
        super().__init__(timeout=900)
        self.add_item(SelectAddressMenu(invoker))

class SelectAddressView(discord.ui.View):
    def __init__(self, invoker=None):
        super().__init__(timeout=900)
        self.add_item(SelectAddressMenu(invoker))

    @discord.ui.button(label="Cancel Checkout", style=discord.ButtonStyle.gray, emoji="❌", custom_id='cancel_sesion_1')
    async def cancel_checkout_session(self, interaction: discord.Interaction, button):
        checkout_session = MongoController().get_pending_checkout_session_by_user_id(str(interaction.user.id))
        if checkout_session != [] or checkout_session != None:
            MongoController().delete_checkout_session(checkout_session['_id'])
        await interaction.response.send_message("Checkout session cancelled", ephemeral=True)

        # Delete message
        await interaction.message.delete()

class SelectAddressMenu(discord.ui.Select):
    def __init__(self, invoker=None):
        self.invoker = invoker
        options = [discord.SelectOption(label="USDT", description="Thether usd", emoji="<:icons8tether144:1072903017038352565>"),
                   discord.SelectOption(label="LTC", description="Litecoin", emoji="<:icons8litecoin128:1072903013443829812>"),
                   discord.SelectOption(label="BTC", description="Bitcoin", emoji="<:icons8bitcoin144:1072903009689935882>"),
                   discord.SelectOption(label="ETH", description="Ethereum", emoji="<:icons8ethereum144:1072903012059725834>"),
                   discord.SelectOption(label="Revolut", description="Revolut", emoji="<:icons8revolut150:1072903015767474206>"),
                   discord.SelectOption(label="Binance Pay", description="Binance Pay ID - 0 fees", emoji="<:icons8binance128:1072903008444223568>")]
        super().__init__(placeholder="Select payment option", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Revolut":
            revolut_address = MongoController().get_revolut_address()
            
            if self.invoker == None:
                return await interaction.response.send_message(f'**{revolut_address}**')
            # Get checkout session
            checkout_session = MongoController().get_pending_checkout_session_by_user_id(str(interaction.user.id))   
            MongoController().set_session_payment_method(checkout_session['_id'], "Revolut")
            return await interaction.response.send_message(f"Please send **{checkout_session['total_price']}€** to **{revolut_address}**")
            
        elif self.values[0] == "Binance Pay":
            binance_pay = MongoController().get_binance_payid_address()
            if self.invoker == None:
                return await interaction.response.send_message(f'**{binance_pay}**')
            # Get checkout session
            checkout_session = MongoController().get_pending_checkout_session_by_user_id(str(interaction.user.id))
            MongoController().set_session_payment_method(checkout_session['_id'], "Crypto")
            return await interaction.response.send_message(f"Send **{checkout_session['total_price']}€** to **{binance_pay}**")
            
            
        else:
            await interaction.response.defer()
            if self.invoker == None:
                return await interaction.followup.send("Select a network", view=SelectNetworkView(BinanceController().get_coin_networks(self.values[0]), self.values[0]))
            # Get checkout session
            checkout_session = MongoController().get_pending_checkout_session_by_user_id(str(interaction.user.id)) 
            MongoController().set_session_payment_method(checkout_session['_id'], "Crypto")
            MongoController().set_session_coin(checkout_session['_id'], self.values[0])

            await interaction.followup.send("Select a network", view=SelectNetworkView(BinanceController().get_coin_networks(self.values[0]), self.values[0], self.invoker))


class SelectNetworkView(discord.ui.View):
    def __init__(self, options, coin, invoker=None):
        super().__init__(timeout=900)
        self.add_item(SelectNetworkMenu(options, coin, invoker))   

class SelectNetworkMenu(discord.ui.Select):
    def __init__(self, options, coin, invoker=None):
        self.invoker = invoker
        self.coin = coin
        options = [discord.SelectOption(label=network, description=name) for network, name in options.items()]
        super().__init__(placeholder="Chose a network", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        # Get checkout session
        if self.invoker == None:
            return await interaction.followup.send(BinanceController().get_deposit_address(self.coin, self.values[0])['address'])
        checkout_session = MongoController().get_pending_checkout_session_by_user_id(str(interaction.user.id))
        MongoController().set_session_network(checkout_session['_id'], self.values[0])
        # TODO: Add a way to make discounts on crypto payment
        if self.coin == "USDT":
            crypto_price = round(float(checkout_session['total_price'])*float(BinanceController().get_coin_price_EUR("USDT")),2)
        else:
            crypto_price = round(float(checkout_session['total_price'])/float(BinanceController().get_coin_price_EUR(self.coin)),6)
        return await interaction.followup.send(f"Please send **{crypto_price} {self.coin}** ({checkout_session['total_price']}€)  to **{BinanceController().get_deposit_address(self.coin, self.values[0])['address']}**")



async def setup(client:commands.Bot):
    await client.add_cog(Shop(client))