import os
import requests
from time import sleep

class Monitor:
    def __init__(self):
        self.api_key = "<PLACE HASHMOB API KEY HERE>"
        self.hashlist_data = self.fetch_hashlists()
        self.hashlist_monitor = []  # specific hashlist IDs to track & update for performance reasons. Empty array = all
        self.monitor_data = {}
        for hashlist in self.hashlist_data:
            try:
                self.monitor_data[hashlist['id']] = 0
            except:
                print("Your API Key is invalid or an error occurred")
                print(self.hashlist_data)
                exit()
            if len(self.hashlist_monitor) == 0 or hashlist['id'] not in self.hashlist_monitor: continue

            self.fetch_left(hashlist['id'])
            self.fetch_found(hashlist['id'], hashlist['hash_type'])
            self.append_found_to_left(hashlist['id'])
        print("Loaded. Please use hashcat similar to the following commands or use our provided config")
        print("hashcat -a3 -m0 <id>.left -o <id>.new --potfile-path=<id>.found ?a?a?a?a?a -i -O")
        print("hashcat -a1 -m0 3.left -o 3.new --potfile-path=3.found wordlist1.txt wordlist2.txt -O -k ]")
        print("Required are: ")
        print("\t-o <id>.new")
        print("\t--potfile-path <id>.found")
        print("\t--debug-mode 4")
        print("\t--debug-file <id>.debug_rule")
        print("\tid.left\t\t(as hashlist)")

    def fetch_hashlists(self):
        headers = {"api-key": self.api_key}
        r = requests.get('https://pro.hashmob.net/api/v2/hashlist', headers=headers)
        return r.json()

    def fetch_left(self, id):
        headers = {"api-key": self.api_key}
        r = requests.get('https://pro.hashmob.net/api/v2/hashlist/' + str(id) + '/left', headers=headers)
        with open(str(id)+'.left','w+', encoding='utf8', errors='ignore') as f:
            if "\"error_message\"" in r.text:
                f.write("")
            else:
                f.write(r.text)

    def fetch_found(self, id, hash_type):
        headers = {"api-key": self.api_key}
        r = requests.get('https://pro.hashmob.net/api/v2/hashlist/' + str(id) + '/found/' + str(hash_type), headers=headers)
        with open(str(id)+'.found','w+', encoding='utf8', errors='ignore') as f:
            if "\"error_message\"" in r.text:
                f.write("")
            else:
                f.write(r.text)
        with open("hashcat.outfiles/" + str(id) +'.found','w+', encoding='utf8', errors='ignore') as f:
            if "\"error_message\"" in r.text:
                f.write("")
            else:
                f.write(r.text)

    def append_found_to_left(self, id):
        with open(str(id)+'.found','r', encoding='utf8', errors='ignore') as f:
            content = f.read()
        lines = content.split("\n")
        new_lines = []
        for line in lines:
            if "\"error_message\"" in line:
                continue
            if ":" in line:
                new_lines.append((line[::-1].split(":", 1)[1])[::-1])
        with open(str(id)+'.left','a+', encoding='utf8', errors='ignore') as f:
            f.write("\n".join(new_lines)+"\n")


    def check_change(self, id, hash_type):
        try:
            stamp = os.stat(str(id)+".new").st_mtime
        except FileNotFoundError:
            return
        if id in self.monitor_data and stamp != self.monitor_data[id]:
            self.monitor_data[id] = stamp
            self.submit(id, hash_type)

    def test(self):
        for hashlist in self.hashlist_data:
            self.fetch_left(hashlist['id'])
            self.fetch_found(hashlist['id'], hashlist['hash_type'])
            self.append_found_to_left(hashlist['id'])
            self.check_change(hashlist['id'], hashlist['hash_type'])

    def submit(self, id, hash_type):
        with open(str(id)+'.new','r+', encoding='utf8', errors='ignore') as f:
            content = f.read()
        os.remove(str(id)+'.new')
        open(str(id) + '.new', 'a', encoding='utf8', errors='ignore').close()
        try:
            stamp = os.stat(str(id)+".new").st_mtime
        except FileNotFoundError:
            return
        if stamp != self.monitor_data[id]:
            self.monitor_data[id] = stamp

        lines = content.split("\n")
        lines = [string for string in lines if string != "" and string is not None]

        to_submit = []
        i = 0
        for line in lines:
            to_submit.append(line)
            i+=1
            if i >= 5000:
                with open(str(id)+'.submitted','a+', encoding='utf8', errors='ignore') as f:
                    f.write(content+"\n")
                    while True:
                        try:
                            r = requests.post('https://pro.hashmob.net/api/v2/submit', json={"algorithm": hash_type, "founds": to_submit}, headers={'api-key': self.api_key})
                            if r.status_code == 200:
                                print("Submitted " + str(len(to_submit)) + " founds.")
                            else:
                                print("Issue submitting data, received status: " + str(r.status_code))
                                print(r.json())
                            break
                        except:
                            print("Connection timed out, retrying")
                            continue
                i = 0
                to_submit = []

        if len(to_submit) > 0:
            with open(str(id)+'.submitted','a+', encoding='utf8', errors='ignore') as f:
                f.write(content+"\n")

            r = requests.post('https://pro.hashmob.net/api/v2/submit', json={"algorithm": hash_type, "founds": to_submit}, headers={'api-key': self.api_key})
            if r.status_code == 200:
                print("Submitted " + str(len(to_submit)) + " founds.")
            else:
                print("Issue submitting data, received status: " + str(r.status_code))
                print(r.json())

if not os.path.exists("hashcat.outfiles"):
    os.makedirs("hashcat.outfiles")

monitor = Monitor()
while True:
    monitor.test()
    sleep(60)
