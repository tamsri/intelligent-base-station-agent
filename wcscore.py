import socket
from time import sleep


class WCsimEnvCore:

    def __init__(self, server_ip='127.0.0.1', server_port=8877):
        self.server_ip = server_ip
        self.server_port = server_port
        # initialize socket
        self.env_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Trying to connect to the simulator
        while not self.connect():
            print("Retrying to connect to server: " + self.server_ip + ":" + str(self.server_port));
            sleep(3)
        # Connection is success
        print("Connected to Server successfully.")
        self.reset()  # ensure that the environment is reset.
        print("The Simulator is ready.")
        self.stations = []  # index of stations in the environment.
        self.users = []  # index of users in the environment.

    def connect(self):
        try:
            self.env_sock.connect((self.server_ip, self.server_port))
            self.env_sock.send("Client: Hello Server".encode())
            print(self.env_sock.recv(1024).decode())
            return True
        except:
            print("Unable to connect to the server.")
        return False

    def reset(self):
        self.env_sock.send("r".encode())
        res = self.env_sock.recv(1024).decode()
        assert res[0:3] == "rok"

    def disconnect(self):
        self.env_sock.send("e".encode())
        res = self.env_sock.recv(1024).decode()
        assert res[0:3] == "eok"
        self.env_sock.close()

    def ask_stations_info(self):  # return list of station IDs.
        answer = self.ask(1)
        # answer form: "(number of stations)&(list of station IDs)"
        answer = answer.split('&')
        station_ids = []
        if int(answer[0]) > 0:
            station_ids = list(map(int, answer[1].split(',')))
        return station_ids

    def ask_users_info(self):  # return list of user IDs.
        answer = self.ask(2)
        # answer form: "(number of users)&(list of user IDs)"
        answer = answer.split('&')
        user_ids = []
        if int(answer[0]) > 0:
            user_ids = list(map(int, answer[1].split(',')))
        return user_ids

    def ask_station_info(self, station_number):
        # answer form:
        # (id):(position):(rotation):(frequency):(N of user)&(list of user):(avg loss)
        answer = self.ask(3, index=station_number)
        answer = answer.split(':')

        if int(answer[0]) == -1:
            return {}  # return an empty struct

        # Structure of a station
        station = {'id': int(answer[0]),
                   'position': list(map(float, answer[1].split(','))),
                   'rotation': list(map(float, answer[2].split(','))),
                   'frequency': float(answer[3]), 'users': [],
                   'average path loss': None}
        user_info = answer[4].split('&')
        if int(user_info[0]) > 0:
            station['users'] = list(map(int, user_info[1].split(',')))
            if answer[5] != '-nan(ind)':
                station['average path loss'] = float(answer[5])
        return station

    def ask_user_info(self, user_id):
        # answer form:
        # (id):(position):(station):(path loss)
        answer = self.ask(4, index=user_id)
        answer = answer.split(':')

        if int(answer[0]) == -1:
            return {}

        # Structure of a user
        user = {'id': int(answer[0]),
                'position': list(map(float, answer[1].split(','))),
                'station': None,
                'path loss': None}
        if len(answer) > 2:
            user['station'] = int(answer[2])
        if len(answer) > 3:
            user['path loss'] = float(answer[3])
        return user

    def ask(self, question, index=None):
        # Questions:
        # 1: How many stations are?
        # 2: How many users are?
        # 3: What is location of base station number N
        # 4: Who are users of base station number N
        message = 'q'
        if index is None:
            message += str(question)
        else:
            message += str(question) + str(index)

        self.env_sock.send(message.encode())
        # Confirms that the server understands the question
        assert self.env_sock.recv(1024).decode()[0:3] == 'qok'
        # Get the answer
        answer = self.env_sock.recv(1024).decode()
        # Confirms that the server sent the answer
        assert answer[0] == 'a'
        answer = answer[2:]
        return answer

    def add_station(self, location, rotation, frequency=2.3e9):
        return self.command(1, location, rotation, frequency)

    def add_user(self, location):
        return self.command(2, location)

    def connect_user_to_station(self, station_id, user_id):
        return self.command(3, station_id=station_id, user_id=user_id)

    def move_station_to(self, station_id, location, rotation):
        return self.command(4, station_id=station_id, location=location, rotation=rotation)

    def remove_station(self, station_id):
        return self.command(5, station_id=station_id)

    def remove_user(self, user_id):
        return self.command(6, user_id=user_id)

    def disconnect_user_from_station(self, station, user_id):
        return self.command(7, station_id=station, user_id=user_id)

    def move_user_to(self, user_id, location):
        return self.command(8, user_id=user_id, location=location)

    def command(self, command_id, location=None, rotation=None, frequency=2.3e9, station_id=None, user_id=None):
        # Commands:
        # 1: Add a station to the env
        # 2: Add a user to the env
        # 3: Connect a user to a station
        # 4: Move a station
        # 5: Remove a station
        # 6: Remove a user
        # 7: Disconnect a user to a station
        # 8: Move a user
        # Add transmitter and return the transmitter id
        # tx_id = self.env_sock.recv(1024).decode()
        if command_id == 1:
            context = 'c1:%f,%f,%f:%f,%f,%f:%f' % (location[0], location[1], location[2],
                                                   rotation[0], rotation[1], rotation[2],
                                                   frequency)
        elif command_id == 2:
            context = 'c2:%f,%f,%f' % (location[0], location[1], location[2])
        elif command_id == 3:
            context = 'c3:%d,%d' % (station_id, user_id)
        elif command_id == 4:
            context = 'c4:%d:%f,%f,%f:%f,%f,%f' % (station_id,
                                                   location[0], location[1], location[2],
                                                   rotation[0], rotation[1], rotation[2])
        elif command_id == 5:
            context = 'c5:%d' % station_id
        elif command_id == 6:
            context = 'c6:%d' % user_id
        elif command_id == 7:
            context = 'c7:%d:%d' % (station_id, user_id)
        elif command_id == 8:
            context = 'c8:%d:%f,%f,%f' % (user_id,
                                          location[0], location[1], location[2])
        else:
            assert False
        self.env_sock.send(context.encode())
        assert self.env_sock.recv(1024).decode()[0:3] == 'cok'
        # to confirm the command was done successfully
        assert self.env_sock.recv(1024).decode()[0:3] == 'suc'

