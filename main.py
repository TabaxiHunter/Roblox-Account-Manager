import sqlite3

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLineEdit, QScrollArea, QButtonGroup
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from threading import Thread
from playwright.sync_api import sync_playwright
from account import Account

def new_thread(target, *args):
    thread = Thread(target=target, args=args)
    thread.start()

def get_security(cookies):
    for cookie in cookies:
        if cookie["name"] == ".ROBLOSECURITY":
            return cookie["value"]

class ServerSelect(QWidget):
    def __init__(self, account_list):
        super().__init__()

        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        self.setFixedWidth(200)
        self.button_group = account_list.button_group 

        self.place = QLineEdit(self)
        self.place.setMaxLength(10)
        self.place.setPlaceholderText("4483381587")

        self.join = QPushButton(self)
        self.join.setText("Join Server")
        self.join.clicked.connect(self.join_server)

        self.layout.addWidget(self.place)
        self.layout.addWidget(self.join)

    def join_server(self):
        place = self.place
        place_id = place.displayText() or place.placeholderText()
        selected = self.button_group.checkedButton()

        if selected:
            new_thread(selected.account.join_game, place_id)

class AccountButton(QPushButton):
    def __init__(self, account):
        super().__init__()

        self.setStyleSheet("")
        self.setCheckable(True)
        self.setText(account.user_name)
        self.account = account # Reference to its account

class AccountList(QScrollArea):
    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout(self)
        self.accounts = QWidget(self)
        self.layout.addStretch()
        
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setWidgetResizable(True)
        self.setWidget(self.accounts)

        self.button_group = QButtonGroup()
        self.button_group.setExclusive(True)
            
        self.accounts.setLayout(self.layout)
        
    def add_account_button(self, account):
        button = AccountButton(account)
    
        self.button_group.addButton(button)
        self.layout.insertWidget(0, button) # Insert account to top of list

class Controls(QWidget):
    def __init__(self, account_list):
        super().__init__()

        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)
        self.setFixedWidth(200)

        self.add = QPushButton(self)
        self.add.setText("Add Account")
        self.add.clicked.connect(lambda: new_thread(self.add_account, account_list))

        self.remove = QPushButton(self)
        self.remove.setText("Remove Account")
        self.remove.clicked.connect(lambda: self.remove_account(account_list))

        self.layout.addWidget(self.add)
        self.layout.addWidget(self.remove)

    def add_account(self, account_list):
        with sync_playwright() as playwright:
            webkit = playwright.webkit # This seems to be the fastest
            browser = webkit.launch(headless=False)

            context = browser.new_context(bypass_csp=True)
            page = context.new_page()
            page.set_viewport_size({"width": 450, "height": 500}) # Not necessary

            try:
                page.goto("https://www.roblox.com/login")
                page.wait_for_url("https://www.roblox.com/home", timeout=0) # Implies successful login
            except Exception:
                # This error handling could be better
                context.close()
                browser.close()
                return

            user_cookie = get_security(context.cookies())

            response = context.request.get("https://users.roblox.com/v1/users/authenticated")
            data = response.json()

            context.close()
            browser.close()

            user_id = data["id"]
            user_name = data["name"]

            for button in account_list.button_group.buttons():
                if button.account.user_name == user_name:
                    return # TODO: Let user know they cannot add the same account twice

            account = Account(user_id, user_name, user_cookie)
            account_list.add_account_button(account)

            # Never done anything with databases before
            con = sqlite3.connect("accounts.db")
            cur = con.cursor()

            cur.execute(f"INSERT INTO account VALUES ('{user_id}', '{user_name}', '{user_cookie}')")

            con.commit()
            con.close()
    
    def remove_account(self, account_list):
        button_group = account_list.button_group
        selected = button_group.checkedButton()

        if selected:
            selected.deleteLater()
            account = selected.account

            con = sqlite3.connect("accounts.db")
            cur = con.cursor()

            cur.execute(f"DELETE FROM account WHERE id='{str(account.user_id)}'")
            
            con.commit()
            con.close()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Roblox Account Manager")
        self.setWindowIcon(QIcon("icon.png"))
        self.setMinimumSize(640, 360)

        main_layout = QHBoxLayout()
        side_layout = QVBoxLayout()

        account_list = AccountList()
        account_controls = Controls(account_list)
        server_select = ServerSelect(account_list)

        # Load all accounts already in the database to the account list
        con = sqlite3.connect("accounts.db")
        cur = con.cursor()

        for row in cur.execute("SELECT * FROM account"):
            user_id, user_name, user_token = row
            
            account = Account(int(user_id), user_name, user_token)
            account_list.add_account_button(account)

        con.close()

        main_layout.addWidget(account_list)
        main_layout.addLayout(side_layout)

        side_layout.addWidget(server_select)
        side_layout.addWidget(account_controls)
        side_layout.addStretch() 

        widget = QWidget()
        widget.setLayout(main_layout)

        self.setCentralWidget(widget)

if __name__ == "__main__":
    app = QApplication([]) # No arguments need to be passed

    # Create table if it doesn't already exist
    con = sqlite3.connect("accounts.db")
    cur = con.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS account(id, name, token)")
    con.commit()
    con.close()

    window = MainWindow()
    window.show()

    app.exec()