from mongo_controller import MongoController

# This program contains some fucntions that help with the bot management

def import_cartalbe_accounts(file_name="Good_Accounts.txt"):
    """Given a txt file, import all accounts to the database"""
    with open(file_name, "r") as f:
        for line in f:
            print(line)
            # Check if account already exists
            if MongoController().get_account(line.strip('\n ')) is None:
                # If not, insert it
                MongoController().insertOne_cartable_account(line.strip('\n '))
            else:
                # If it does, update it
                MongoController().update_account_status(line.strip('\n '), "cartable")
        return "Done"

def export_sold_accounts(file_name="Sold_Accounts.txt"):
    """Given a list with all sold accs, export them to a txt file"""
    with open(file_name, "w") as f:
        for acc in MongoController().get_all_sold_accounts():
            f.write(acc['account'] + "\n")
        return "Done"

def set_bad_accounts(file_name="Bad_Accounts.txt"):
    """Given a txt file, set all accounts to state = Bad_account"""
    with open(file_name, "r") as f:
        for line in f:
            print(line)
            MongoController().update_account_status(line.strip('\n '), "Bad_account")
        return "Done"

def set_uncartable_accounts(file_name="Uncartable_Accounts.txt"):
    """Given a txt file, set all accounts to state = uncartable"""
    with open(file_name, "r") as f:
        for line in f:
            print(line)
            MongoController().update_account_status(line.strip('\n '), "uncartable")
        return "Done"

def main():
    import_cartalbe_accounts()

if __name__ == "__main__":
    main()