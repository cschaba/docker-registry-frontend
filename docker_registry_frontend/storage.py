import abc
import json
import os
import sqlite3

from docker_registry_frontend.registry import DockerV2Registry


class DockerRegistryWebStorage(abc.ABC):
    def get_registries(self):
        raise NotImplementedError

    def add_registry(self, name, url, user=None, password=None):
        raise NotImplementedError

    def remove_registry(self, name):
        raise NotImplementedError


class DockerRegistryJsonFileStorage(DockerRegistryWebStorage):
    def __init__(self, file_path, *args, **kwargs):
        self.__json_file = file_path

        if not os.path.exists(self.__json_file) and not os.path.isdir(self.__json_file):
            with open(self.__json_file, 'w') as f:
                json.dump({}, f)

        self.__read()  # read for the first time to make sure given file is readable and contains valid JSON

    def __read(self):
        with open(self.__json_file, 'r') as json_f:
            return json.load(json_f)

    def __write(self, content):
        with open(self.__json_file, 'w') as json_f:
            json.dump(content, json_f)

    def add_registry(self, name, url, user=None, password=None):
        registries = self.__read()

        registries[name] = {
            'url': url,
            'user': user,
            'password': password
        }

        self.__write(registries)

    def remove_registry(self, name):
        registries = self.__read()
        if name in registries:
            registries.pop(name)

        self.__write(registries)

    def get_registries(self):
        registries = []
        for name, config in self.__read().items():
            registries.append(
                DockerV2Registry(
                    name,
                    config['url'],
                    config.get('user', None),
                    config.get('password', None)
                )
            )

        return registries


class DockerRegistrySQLiteStorage(DockerRegistryWebStorage):
    def __init__(self, file_path, *args, **kwargs):
        self.__sqlite_file = file_path
        self.__conn = sqlite3.connect(file_path, check_same_thread=False)

        cursor = self.__conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS registries (id INTEGER PRIMARY KEY, name TEXT NOT NULL, url TEXT NOT NULL, user TEXT, password TEXT);")

    def __execute(self, *args, **kwargs):
        cursor = self.__conn.cursor()
        res = cursor.execute(*args, **kwargs)

        self.__conn.commit()
        return res

    def add_registry(self, name, url, user=None, password=None):
        self.__execute('INSERT INTO registries (name, url, user, password) VALUES (:name, :url, :user, :password);',
                       {'name': name, 'url': url, 'user': user, 'password': password})

    def remove_registry(self, name):
        self.__execute('DELETE FROM registries WHERE name = :name;', {'name': name})

    def get_registries(self):
        registries = []

        for row in self.__execute('SELECT * FROM registries;'):
            _, name, url, user, password = row
            registries.append(
                DockerV2Registry(
                    name,
                    url,
                    user,
                    password
                )
            )

        return registries


STORAGE_DRIVERS = {
    'sqlite': DockerRegistrySQLiteStorage,
    'json': DockerRegistryJsonFileStorage
}