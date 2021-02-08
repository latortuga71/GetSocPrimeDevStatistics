#!/usr/bin/python3
import requests
import bs4
import sqlite3
import datetime
import time

class SocPrime(object):
    def __init__(self,username,password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.login_page = "https://www.developer.socprime.com/login/"
        self.headers = {"Content-Type":"application/x-www-form-urlencoded"}
        self.form_data = {"login":self.username,"password":self.password,"submit":"Login","csrf":""}

    def login(self):
        resp = self.session.get(self.login_page)
        token_line = [x for x in resp.text.split("\n") if "csrf" in x][0]
        if not token_line:
            print("::: ERROR failed to acquire csrf token exiting...:::")
            return None
        token = token_line.split("=")[3].split(">")[0].strip('"')
        print("::: SUCCCESS csrf token acquired :::")
        self.form_data["csrf"] = token
        login_resp = self.session.post("https://www.developer.socprime.com/login/",data=self.form_data,headers=self.headers,allow_redirects=True)
        if login_resp.status_code != 200:
            print("::: Error failed to login ::: exiting...")
            return None
        print("::: SUCCESS logged in :::")
        return login_resp.text

    def parse_content(self,page_to_parse):
        complete_rules = []
        parsed_data = []
        rule = {"rule":"","unlocks":"","downloads":"","views":"","mode":""}
        possible_modes = ["Free","Paid"]
        soup = bs4.BeautifulSoup(page_to_parse,'html.parser')
        table = soup.find('table',attrs={'class':'table table-sm table-content-statistics'})
        table_body = table.find('tbody')
        rows = table_body.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            cols = [ele.text.strip() for ele in cols]
            parsed_data.append([ele for ele in cols if ele])
        for entry in parsed_data:
            rule["rule"] = entry[0]
            rule["mode"] = entry[1]
            rule["unlocks"] = int(entry[2].split("\n")[0])
            rule["downloads"] = int(entry[3].split("\n")[0]) 
            rule["views"] = int(entry[4].split("\n")[0])
            complete_rules.append(rule.copy())
        return complete_rules

class Database(object):
    def __init__(self,db_name="default.db",data_array=None):
        self.db_name = db_name
    def connect_DB(self):
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.conn.execute('''CREATE TABLE IF NOT EXISTS SOCPRIME (rule_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,rule_name TEXT NOT NULL,rule_mode TEXT NOT NULL,download_count INT NOT NULL,unlock_count INT NOT NULL,view_count INT NOT NULL,last_updated timestamp NOT NULL);''')
            print("::: Connected to db ::::")
            return True
        except Exception as e:
            print(e)
            return False
    def close_DB(self):
        self.conn.close()

    def print_all_rules(self,print_or_not=False):
        cursor = self.conn.cursor()
        select_statement = '''SELECT * FROM SOCPRIME;'''
        cursor.execute(select_statement)
        records = cursor.fetchall()
        if not records:
            print("::: No records :::")
            print("::: Creating dummy records...:::")
            cursor.close()
            return False
        if print_or_not: 
            for row in records:
                print(row)
        cursor.close()
        return True

    def init_data_if_empty(self,data):
        cursor = self.conn.cursor()
        insert_statment = '''INSERT INTO 'SOCPRIME' ('rule_name','rule_mode','download_count','unlock_count','view_count','last_updated') VALUES (?,?,?,?,?,?);'''
        for entry in data:
            value_tuple = (entry["rule"],entry['mode'],0,0,0,datetime.datetime.now())
            cursor.execute(insert_statment,value_tuple)
            self.conn.commit()
            print("::: Added entry :::")
        cursor.close()

    def add_new_rule(self,rule):
        cursor = self.conn.cursor()
        insert_statment = '''INSERT INTO 'SOCPRIME' ('rule_name','rule_mode','download_count','unlock_count','view_count','last_updated') VALUES (?,?,?,?,?,?);'''
        value_tuple = (rule["rule"],rule['mode'],rule['downloads'],rule["unlocks"],rule["views"],datetime.datetime.now())
        try:
            cursor.execute(insert_statment,value_tuple)
            self.conn.commit()
            print("::: Added entry :::")
            cursor.close()
            return True
        except Exception as e:
            cursor.close()
            print(e)
            return False

    def update_rule(self,rule):
        #print(f'::: Attempting to update rule: {rule["rule"]} :::')
        cursor = self.conn.cursor()
        value_tuple = (rule["downloads"],rule["unlocks"],rule["views"],datetime.datetime.now(),rule["rule"])
        update_statement = '''UPDATE SOCPRIME set download_count = ? ,  unlock_count = ? , view_count = ? , last_updated = ? WHERE rule_name = ?'''
        try:
            cursor.execute(update_statement,value_tuple)
            self.conn.commit()
            cursor.close()
            #print('::: Successfully updated :::')
            return True
        except Exception as e:
            cursor.close()
            print(e)
            return False

    def update_if_changes(self,data):
        change_counter = 0
        cursor = self.conn.cursor()
        select_statement = '''SELECT download_count,unlock_count,view_count FROM SOCPRIME WHERE rule_name = ?'''
        for entry in data:
            value_tuple = (entry["rule"])
            cursor.execute(select_statement,(value_tuple,))
            record = cursor.fetchone()
            # if it doesnt exist add it
            if not record:
                print("::: New rule detected attempting to add :::")
                self.add_new_rule(entry)
                continue
            # check if entry in db is not up to date
            db_download_count = record[0]
            db_unlock_count = record[1]
            db_view_count = record[2]
            if db_download_count != entry["downloads"]:
                print(f'(+) {entry["rule"]} download changed from {db_download_count} ===> {entry["downloads"]}')
                self.update_rule(entry)
                change_counter+=1
            if db_unlock_count != entry["unlocks"]:
                print(f'(+) {entry["rule"]} unlock count changed from {db_unlock_count} ===> {entry["unlocks"]}')
                self.update_rule(entry)
                change_counter+=1
            if db_view_count != entry["views"]:
                print(f'(+) {entry["rule"]} view count changed from {db_view_count} ===> {entry["views"]}')
                self.update_rule(entry)
                change_counter+=1
            continue
        if change_counter == 0:
            print("::: NO CHANGES FOUND :::")
        return True


if __name__ == "__main__":
    current_year = time.strftime("%Y")
    print(f"::: SOC PRIME STATISTICS FOR YEAR OF {current_year} :::")
    print("::: Connecting to Soc Prime :::")
    socprime = SocPrime("ur email","ur pass")
    content = socprime.login()
    if not content: quit() # exit if failed to login
    parsed_stats = socprime.parse_content(content)
    print("::: Got soc prime stats :::")
    [print(x) for x  in parsed_stats]
    print("::: DB Stuff Now :::")
    db = Database(f"Soc_Prime_Stats_{current_year}.db")
    if not db.connect_DB():
        print("::: Failed to connect to db exiting... :::")
    print("::: Querying db for rules :::")
    if not db.print_all_rules():
        db.init_data_if_empty(parsed_stats)
    print("::: Checking scraped data against db for changes :::")
    print("##################### CHANGES ##############################")
    db.update_if_changes(parsed_stats)
    print("####################################################")
    print("::: Successfully checked for all since last run :::")
    print("::: Closing DB :::")
    db.close_DB()
