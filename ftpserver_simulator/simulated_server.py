import logging
import os

from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from pyftpdlib.authorizers import DummyAuthorizer
import json
import argparse

logfileName = os.path.join(os.path.dirname(__file__), 'simulated_ftp_server.log')
logging.basicConfig(filename=logfileName, level=logging.INFO)


class MyHandler(FTPHandler):

    def on_connect(self):
        print("%s:%s connected" % (self.remote_ip, self.remote_port))

    def on_disconnect(self):
        # do something when client disconnects
        pass

    def on_login(self, username):
        # do something when user login
        pass

    def on_logout(self, username):
        # do something when user logs out
        pass

    def on_file_sent(self, file):
        # do something when a file has been sent
        if os.path.exists(file):
            os.remove(file)
            print("File: " + file + " has being removed since it has being sent to the caller.")
        else:
            print("Sorry, I can not remove %s file." % file)
        pass

    def on_file_received(self, file):
        # do something when a file has been received
        pass

    def on_incomplete_file_sent(self, file):
        # do something when a file is partially sent
        pass

    def on_incomplete_file_received(self, file):
        # remove partially uploaded files
        import os
        os.remove(file)


def extant_file(x, CREATE_FLAG=False):
    """
    'Type' for argparse - checks that file exists but does not open.
    """
    if CREATE_FLAG == True:
        if not os.path.exists(x):
            os.makedirs(x)
            raise argparse.ArgumentTypeError("{0} did  NOT exist but created".format(x))
    else:
        if not os.path.exists(x):
            # Argparse uses the ArgumentTypeError to give a rejection message like:
            # error: argument input: x does not exist
            raise argparse.ArgumentTypeError("{0} does not exist".format(x))

    return x


def assure_path_exists(path):
    # dir = os.path.dirname(path)
    if not os.path.exists(path):
        os.makedirs(path)


def main():
    parser = argparse.ArgumentParser(description="Simulated FTP Server ")
    parser.add_argument("-c", "--config",
                        dest="filename", required=True, type=extant_file,
                        help="Server configuration file", metavar="FILE")
    args = parser.parse_args()
    full_path_filename = os.path.join(os.path.dirname(__file__), args.filename)
    with open(full_path_filename) as json_data_file:
        data = json.load(json_data_file)
    print(data)

    serverPARMS = data.get('SERVER', False)

    HOST = serverPARMS.get('HOST', False)
    PORT = serverPARMS.get('PORT', False)
    HOMEDIRECTORY_NAME = serverPARMS.get('HOMEDIRECTORY_NAME', False)
    HOMEDIRECTORY_PATH = serverPARMS.get('HOMEDIRECTORY_PATH', False)
    if HOST and PORT and HOMEDIRECTORY_NAME:
        if HOMEDIRECTORY_PATH:
            DataFileHomeDirectory = os.path.join(HOMEDIRECTORY_PATH, HOMEDIRECTORY_NAME)
        else:
            DataFileHomeDirectory = os.path.join(os.path.dirname(__file__), HOMEDIRECTORY_NAME)
        # Instantiate a dummy authorizer for managing 'virtual' users
        authorizer = DummyAuthorizer()
        # Define a new user having full r/w permissions and a read-only
        # add_user(username, password, homedir, perm="elr", msg_login="Login successful.", msg_quit="Goodbye.")
        FTP_USER_DATAFILE_LOCATION = os.path.join(DataFileHomeDirectory, 'dev1')
        assure_path_exists(FTP_USER_DATAFILE_LOCATION)
        authorizer.add_user('dev1', '12345!', homedir=FTP_USER_DATAFILE_LOCATION, perm='elradfmwMT')
        FTP_USER_DATAFILE_LOCATION = os.path.join(DataFileHomeDirectory, 'dummy')
        assure_path_exists(FTP_USER_DATAFILE_LOCATION)
        authorizer.add_user('dummy', '12345', homedir=FTP_USER_DATAFILE_LOCATION, perm='elradfmwMT')
        handler = MyHandler
        handler.authorizer = authorizer
        server = FTPServer((HOST, PORT), handler)
        print("Server started...")
        server.serve_forever()
    else:
        print("Missing or bad server configuration parameter(s). Program exited")


if __name__ == "__main__":
    main()
