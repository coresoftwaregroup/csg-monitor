# many ideas stolen from
# https://github.com/kylemarkwilliams/website-monitor

import requests
import smtplib
import time
import thread

from datetime import datetime
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText

from repeattimer import RepeatTimer

from monitor_config import monitor_config
from servers import server_list

# interval = monitor_config['interval']
# recipients = monitor_config['recipients']

args = []
kwargs = {}


def mail(to, subject, text):
    msg = MIMEMultipart()
    msg['From'] = monitor_config['mail_user']
    msg['To'] = to
    msg['Subject'] = subject
    msg.attach(MIMEText(text))
    mailServer = smtplib.SMTP(monitor_config['mail_server'],
                              monitor_config['mail_server_port'])
    # mailServer.ehlo()
    # mailServer.starttls()
    # mailServer.ehlo()
    # mailServer.login(monitor_config['mail_user'], monitor_config['mail_pass'])
    mailServer.sendmail(monitor_config['mail_user'], to, msg.as_string())
    mailServer.close()


class Monitor(object):

    def __init__(self, server_list, monitor_config):
        print "__init__"
        self.interval = monitor_config['interval']
        self.recipients = monitor_config['recipients']
        self.servers = self.get_servers(server_list)

    def run(self):
        print "run: "
        repeat_timer = RepeatTimer(self.interval,
                                   self.check_servers,
                                   *args,
                                   **kwargs)
        repeat_timer.start()

    def check_servers(self, *args, **kwargs):
        """"""
        print "check_servers: "
        for server in self.servers:
            print server.name
            thread.start_new_thread(server.check_status, ())
        # email message about down servers
        time.sleep(5)
        down_servers = self.get_down_servers()
        if len(down_servers) > 0:
            self.send_down_servers_email(down_servers)

    def get_down_servers(self):
        down_servers = []
        for server in self.servers:
            if server.status != 'OK' and server.fails >= server.max_fails:
                down_servers.append(server)
        return down_servers

    def send_down_servers_email(self, down_servers):
        print "send_down_servers_email"
        message = ''
        for server in down_servers:
            text = "%s %s %s - %s\n" % (server.name,
                                        server.last_checked,
                                        server.url,
                                        server.status)
            message += text
        for recipient in self.recipients:
            mail(recipient, 'CSG Monitor', message)

    def get_servers(self, server_list):
        """takes list of dicts and return list of Server objects"""
        print "get_servers: "
        servers = []
        for server in server_list:
            servers.append(Server(name=server['name'],
                                  url=server['url'],
                                  timeout=server['timeout'],
                                  max_fails=server['max_fails'],
                                  assert_string=server['assert_string']))
        return servers


class Server:

    def __init__(self, name, url, timeout, max_fails, assert_string):
        self.name = name
        self.url = url
        self.timeout = timeout
        self.max_fails = max_fails
        self.assert_string = assert_string

        self.fails = 0
        self.status_code = 0
        self.status = ''
        self.last_checked = datetime.min
        self.notified_fail = False
        self.assert_pass = False

    def check_status(self):

        self.last_checked = datetime.now()
        try:
            r = requests.get(self.url, timeout=self.timeout)

        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            self.status_code = 500
            self.status = str(e)
            self.fails += 1

        else:
            self.status_code = r.status_code
            if r.status_code == 200:
                if self.assert_string in r.text:
                    self.status = 'OK'
                    self.fails = 0
                    self.notified_fail = False
                    self.assert_pass = True
                else:
                    self.status = 'Assert Failed'
                    self.fails += 1
                    self.assert_pass = False
            else:
                self.fails += 1
                self.status = 'ERROR'

        print self.name, self.status
        return self

if __name__ == "__main__":
    # need to update server list when necessary
    monitor = Monitor(server_list, monitor_config)
    monitor.run()
    # servers = get_servers(server_list)
    # repeat_timer = RepeatTimer(interval, check_servers, *args, **kwargs)
    # repeat_timer.start()
