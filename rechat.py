'''
Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at

    http://aws.amazon.com/apache2.0/

or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
'''

import sys
import irc.bot
import requests
from rehive import Rehive, APIException


class TwitchBot(irc.bot.SingleServerIRCBot):
    def __init__(self, username, token, channel, rehive_api_key):
        self.token = token
        self.channel = '#' + channel
        self.rehive = Rehive(rehive_api_key)

        # Create IRC bot connection
        server = 'irc.chat.twitch.tv'
        port = 6667
        print('Connecting to ' + server + ' on port ' + str(port) + '...')
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port, 'oauth:'+token)], username, username)   

    def on_welcome(self, c, e):
        print('Joining ' + self.channel)

        # You must request specific capabilities before you can use them
        c.cap('REQ', ':twitch.tv/membership')
        c.cap('REQ', ':twitch.tv/tags')
        c.cap('REQ', ':twitch.tv/commands')
        c.cap('REQ', ':twitch.tv/users')
        c.join(self.channel)

    def on_pubmsg(self, c, e):

        # If a chat message starts with an exclamation point, try to run it as a command
        if e.arguments[0][:1] == '!':
            cmd = e.arguments[0].split(' ')[0][1:]
            print('Received command: ' + cmd)
            self.do_command(e, cmd)
        else:
            # We want to process every message
            username = e.tags[2]['value']
            user_id = e.tags[11]['value']
            rehive_user_id = self._get_or_create_rehive_user(
                username,
                user_id
            )
            # Give a user 1 XLM for each message
            self._reward_for_message(username)

        return

    def do_command(self, e, cmd):
        c = self.connection
        print(e)
        print(cmd)
        args = e.arguments[0].split(' ')
        print(args)
        # Provide basic information to viewers for specific commands
        if cmd == "pay":
            username = e.tags[2]['value']
            amount = args[1]
            currency = args[2]
            to_user = args[3]
            user_pay = self._pay_user(
                username,
                to_user,
                amount,
                currency
            )
            if user_pay:
                message = "Sent %s %s to user %s." % amount, currency, to_user
            else:
                message = "Failed to send "
            c.privmsg(self.channel, message)

        # The command was not recognized
        else:
            c.privmsg(self.channel, "Did not understand command: " + cmd)

    def _get_or_create_rehive_user(self, username, user_id):
        try:
            r = self.rehive.admin.users.get(
                filter={'username': username}
            )
            return r[0]['id']
        except APIException as exc:
            r = self.rehive.admin.users.create(
                username=username,
                metadata={
                    'twitch_id': user_id
                }
            )
            return r['id']

    def _reward_for_message(self, username):
        try:
            r = self.rehive.admin.transactions.create_credit(
                user=username,
                amount=10000000,
                currency='XLM',
                status='complete'
            )
            print('Rewarded: ' + username + ' with 1 XLM')
        except APIException as exc:
            print('Error rewarding' + username)

    def _pay_user(self, from_user, to_user, amount, currency):
        """
        Send X currency to a specific user
        """
        amount = int(amount) * 10000000
        print(currency)
        try:
            r = self.rehive.admin.transactions.create_transfer(
                user=from_user,
                recipient=to_user,
                amount=amount,
                currency=currency
            )
            print(
                'Paid %s %s to %s' %
                amount,
                currency,
                to_user
            )
            return True
        except Exception as exc:
            print('Failed to pay')
            raise exc
            return False


def main():
    if len(sys.argv) != 5:
        print(
            "Usage: twitchbot <username> <token> <channel> <rehive_api_key>"
        )
        sys.exit(1)

    username  = sys.argv[1]
    token     = sys.argv[2]
    channel   = sys.argv[3]
    rehive_api_key = sys.argv[4]

    bot = TwitchBot(username, token, channel, rehive_api_key)
    bot.start()

if __name__ == "__main__":
    main()
