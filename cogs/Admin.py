import discord
import logging
from discord.ext import commands
from discord import app_commands
from mongo_controller import MongoController
from datetime import datetime
import os

class Admin(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def log(self, member: discord.Member, action: str):
        channel = self.client.get_channel(1073219018586066944)
        await channel.send(f"```[{member}] -> [{action}]```")   

    async def payment_method_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        payment_methods = ['USDT', 'LTC', 'BTC', 'ETH', 'Revolut', 'Binance Pay ID']
        return [
            app_commands.Choice(name=method, value=method)
            for method in payment_methods if current.lower() in method.lower()
        ]

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(payment_method=payment_method_autocomplete)
    @app_commands.command(name="gen", description="Generate accounts")
    async def gen(self, interaction: discord.Interaction, number_of_accounts: int, client: str, total_price: float, payment_method: str):
        # Log command
        await self.log(interaction.user, f'{str(interaction.command.name)} {number_of_accounts} {client} {total_price} {payment_method}')
        account_list = [acc['account'] for acc in MongoController().get_n_available_accounts(number_of_accounts)]
        # Defer
        await interaction.response.defer()
        
        if len(account_list) == number_of_accounts:
            # Send accs in string if number_of_accounts is < 20
            if number_of_accounts < 20:
                await interaction.followup.send("Here are your accounts: \n" + "```" +  "\n".join(account_list) + "```")
            else:
                # Send accs in file if number_of_accounts is >= 20
                with open("accounts.txt", "w") as f:
                    f.write("Here are your accounts: \n" + "\n".join(account_list))
                await interaction.followup.send(file=discord.File(fp="accounts.txt", filename="accounts.txt"))
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
                "Client_id": client.strip("<@>"),
                "Date": datetime.now()
            }
            MongoController().insert_finance_statement(finance_statement)

            # Update client document
            # 1. Check if client exists
            if MongoController().get_client(client.strip("<@>")) is not None:
                # 2. Update client document
                purchase = {
                    "Date": datetime.now(),
                    "Number_of_accounts": number_of_accounts,
                    "Total_price": total_price,
                    "Payment_method": payment_method,
                    "Account_list": account_list
                }
                MongoController().add_new_client_purchase(client.strip("<@>"), purchase)
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

                # Add Client role if not already added
                # Get member from client ID
                member = await interaction.guild.fetch_member(client.strip("<@>"))
                # Get role
                role = discord.utils.get(interaction.guild.roles, name="Client")
                # Add role
                await member.add_roles(role)

        else:
            await interaction.followup.send("Not enough accounts in stock")
            return
    
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="replace", description="Replace n accounts")
    async def replace(self, interaction: discord.Interaction, number_of_accounts: int, client: str):
        # Log command
        await self.log(interaction.user, f'{str(interaction.command.name)} {number_of_accounts} {client}')
        account_list = [acc['account'] for acc in MongoController().get_n_available_accounts(number_of_accounts)]
        if len(account_list) == number_of_accounts:
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
            # Update client document
            # 1. Check if client exists
            if MongoController().get_client(client.strip("<@>")) is not None:
                # 2. Update client document
                replacement = {
                    "Date": datetime.now(),
                    "Number_of_accounts": number_of_accounts,
                    "Account_list": account_list
                }
                MongoController().add_new_client_replacement(client.strip("<@>"), replacement)
            else:
                # 3. Create client document
                replacement = [{
                    "Date": datetime.now(),
                    "Number_of_accounts": number_of_accounts,
                    "Account_list": account_list
                }]
                MongoController().insert_new_client(client.strip("<@>"), datetime.now(), 0, [], replacement, [], 0)
        else:
            await interaction.response.send_message("Not enough accounts in stock")
            return

    async def account_status_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        account_status = ['cartable','uncartable','bad_account']
        return [
            app_commands.Choice(name=status, value=status)
            for status in account_status if current.lower() in status.lower()
        ]
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(status=account_status_autocomplete)
    @app_commands.command(name="import_accounts", description="Add accounts (can be cartable, bad_accs, and uncartable)")
    async def import_accounts(self, interaction: discord.Interaction, status: str, file: discord.Attachment):
        # Log Command
        await self.log(interaction.user, f'{interaction.command.name} {status} {file.filename}')
        await interaction.response.defer()
        f = await file.read()
        # Convert bytes to string
        f = f.decode("utf-8").split('\n')
        for account in f:
            # Check if account already exists
            if MongoController().get_account(account) is None and status.lower() == "cartable":
                # If not, insert it
                MongoController().insertOne_cartable_account(account)
            else:
                # If it does, update it
                MongoController().update_account_status(account, status)
        return await interaction.followup.send("Accounts imported successfully")
    
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="export_sold_accounts", description="Export sold accounts")
    async def export_sold_accounts(self, interaction: discord.Interaction):
        # Log Command
        await self.log(interaction.user, f'{interaction.command.name}')
        account_list = [acc['account'] for acc in MongoController().get_all_sold_accounts()]
        with open("sold_accounts.txt", "w") as f:
            f.write("\n".join(account_list))
        await interaction.response.send_message(file=discord.File(fp="sold_accounts.txt", filename="sold_accounts.txt"))
        return os.remove("sold_accounts.txt")
    

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="export_all_accounts", description="Export all accounts")
    async def export_all_accounts(self, interaction: discord.Interaction):
        # Log Command
        await self.log(interaction.user, f'{interaction.command.name}')
        account_list = [acc['account'] for acc in MongoController().get_all_accounts()]
        with open("all_accounts.txt", "w") as f:
            f.write("\n".join(account_list))
        await interaction.response.send_message(file=discord.File(fp="all_accounts.txt", filename="all_accounts.txt"))
        return os.remove("all_accounts.txt")
    

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="finance", description="Shows finance results")
    async def finance(self, interaction: discord.Interaction, start_date: str, end_date: str):
        # Log Command
        await self.log(interaction.user, f'{interaction.command.name} {start_date} {end_date}')
        revenue, expenses, profit, profit_margin, n_accounts_sold = MongoController().basic_finance_dashboard(datetime.strptime(start_date, '%d/%m/%Y'), datetime.strptime(end_date, '%d/%m/%Y'))
        embed = discord.Embed(title="Finance Dashboard", description=f"From {start_date} to {end_date}", color=0xff9a00)
        embed.add_field(name="Revenue", value=f"{round(revenue['total'],2)} €", inline=False)
        embed.add_field(name="Expenses", value=f"{round(expenses['total'],2)} €", inline=False)
        embed.add_field(name="Profit", value=f"{round(profit['total'],2)} €", inline=False)
        embed.add_field(name="Profit Margin", value=f"{round(profit_margin,2)} %", inline=False)
        embed.add_field(name="Number of accounts sold", value=f"{n_accounts_sold}", inline=False)
        embed.add_field(name="Average selling price per account", value=f"{round(revenue['total'] / n_accounts_sold, 2)} €", inline=False)
        embed.add_field(name="Average cost per account", value=f"{round(expenses['total'] / n_accounts_sold, 2)} €\n", inline=False)
        embed1 = discord.Embed(title="Details per payment method", description="\u200b", color=0xff9a00)
        for key in revenue.keys():
            if key != "total":
                embed1.add_field(name=f"Revenue {key}", value=f"{round(revenue[key],2)} €", inline=True)
                embed1.add_field(name=f"Expenses {key}", value=f"{round(expenses[key],2) if key in expenses else 0} €", inline=True)
                embed1.add_field(name=f"Profit {key}", value=f"{round(profit[key],2)} €", inline=True)
        embed1.set_footer(text=f"Requested by {interaction.user.name} | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        return await interaction.response.send_message(embeds=[embed, embed1])
        
        
    async def statement_type_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        statement_types = ['Income', 'Expense', 'Withdraw']
        return [
            app_commands.Choice(name=st_type, value=st_type)
            for st_type in statement_types if current.lower() in st_type.lower()
        ]
    
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(statement_type=statement_type_autocomplete, payment_method=payment_method_autocomplete)
    @app_commands.command(name="insert_finance_statement", description="Insert new finance statement in database")
    async def insert_finance_statement(self, interaction: discord.Interaction, statement_type: str, product: str, quantity: int, total_price: float, payment_method: str):
        # Log Command
        await self.log(interaction.user, f'{interaction.command.name} {statement_type} {product} {quantity} {total_price} {payment_method}')
        finance_statement = {
            "Type": statement_type,
            "Product": product,
            "Quantity": quantity,
            "Unit_price": round(total_price / quantity,2),
            "Total_Price": total_price,
            "Payment_Method": payment_method,
            "Client_id": str(interaction.user.id),
            "Date": datetime.now(),
        }
        MongoController().insert_finance_statement(finance_statement)
        return await interaction.response.send_message("Statement inserted successfully")
    
    @app_commands.command(name="stock", description="Shows the amount of accounts in stock")
    async def stock(self, interaction: discord.Interaction):
        # Log Command
        await self.log(interaction.user, f'{interaction.command.name}')
        
        if "ticket" not in interaction.channel.name:
            # Check if admin is using the command 
            if interaction.user.guild_permissions.administrator:
                pass
            else:
                return await interaction.response.send_message("You can only use this command in a ticket channel")
        n_accounts = MongoController().get_number_of_available_accounts()
        return await interaction.response.send_message(f"There are **{n_accounts}** accounts in stock")
    

    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="prices", description="Show prices")
    async def prices(self, interaction: discord.Interaction):
        # Log Command
        await self.log(interaction.user, f'{interaction.command.name}')
        prices = MongoController().get_account_prices()
        embed = discord.Embed(title="Prices", description="", color=0xff9a00)
        steps = [list(step.values())[0] for step in prices]
        for i in range(len(steps)-1):
            embed.add_field(name="\u200b", value=f"{steps[i]}-{steps[i+1]}: **{list(prices[i].values())[1]}€**", inline=False)
        embed.add_field(name="\u200b", value=f"{steps[-1]}+: **{list(prices[-1].values())[1]}€** (negotiable)", inline=False)
        # TODO: Add link to create ticket channel

        embed.set_footer(text=f"Requested by {interaction.user.name} | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        return await interaction.response.send_message(embed=embed)
    
    
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="set_price", description="Set price for a specific step")
    async def set_price(self, interaction: discord.Interaction, step: int, price: float):
        # Log Command
        await self.log(interaction.user, f'{interaction.command.name} {step} {price}')
        MongoController().set_account_price(step, price)
        return await interaction.response.send_message(f"Price for step {step} set to {price}€")
    
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="remove_price", description="Remove price for a specific step")
    async def remove_price(self, interaction: discord.Interaction, step: int):
        # Log Command
        await self.log(interaction.user, f'{interaction.command.name} {step}')
        MongoController().del_account_price(step)
        return await interaction.response.send_message(f"Price for step {step} removed")
    
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.command(name="client_profile", description="Sends client profile")
    async def client_profile(self, interaction: discord.Interaction, member: discord.Member):
        # Log Command
        await self.log(interaction.user, f'{interaction.command.name} {member.name}')
        total_number_of_accounts_bought = MongoController().get_client_number_of_account_purchases(str(member.id))
        total_number_replacements = MongoController().get_client_number_of_replacements(str(member.id))
        revenue = MongoController().get_client_revenue(str(member.id))
        #TODO: Implement Services

        embed = discord.Embed(title=f"Client Profile", description="", color=0xff9a00)
        embed.add_field(name="Name", value=f"{member.name}", inline=True)
        embed.set_thumbnail(url=member.avatar)
        embed.add_field(name="Total accounts bought", value=f"{total_number_of_accounts_bought}", inline=True)
        embed.add_field(name="Total replacements", value=f"{total_number_replacements}", inline=True)
        embed.add_field(name="Revenue", value=f"{round(revenue,2)}€", inline=True)
        embed.add_field(name="Avg price per account", value=f"{round(revenue/total_number_of_accounts_bought,2)}€", inline=True)
        embed.add_field(name="Estimate of profit", value=f"{round(((revenue/(total_number_of_accounts_bought+total_number_replacements))-1)*total_number_of_accounts_bought,2)}€", inline=True)
        embed.set_footer(text=f"Requested by {interaction.user.name} | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

        return await interaction.response.send_message(embed=embed)

async def setup(client:commands.Bot):
    await client.add_cog(Admin(client))