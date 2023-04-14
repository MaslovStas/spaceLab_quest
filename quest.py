import json
from json import JSONDecodeError

import numpy as np


class Field:
    """Стандартное поле"""

    def __init__(self, board, position: tuple, is_white=True, is_available=True):
        self.board = board
        self.position = position
        self.is_white = is_white
        self.is_fire = False
        self.is_available = is_available

        self.players = []
        self._has_key = False

        self.board[position] = self  # добавляем поле в общую матрицу

    @property
    def has_key(self):
        return self._has_key

    @has_key.setter
    def has_key(self, value):
        """При добавлении или удалении ключа к полю будет изменяться локация ключа на поле для сохранения"""
        self.board.key_location = self.position if value else None
        self._has_key = value

    def __repr__(self):
        if self.is_fire:
            return 'F'
        if self.has_key:
            return 'K'
        if self.players:
            return f'{self.players[0].health}'
        return '0'

    def effect_on_player(self, player):
        """Эффект поля на игрока в зависимости от того горит ли поле"""
        if self.is_fire:
            player.hurt()
            print('Герой получает урон от огня!')

    def player_enters(self, player):
        self.players.append(player)
        # если текущая позиция игрока уже не пустая, то это движение игрока, а не инициализация его на карте
        if player.current_field:
            player.current_field.player_leaves(player)  # очищаем клетку, с которой игрок уходит
            self.effect_on_player(player)  # воздействуем на игрока

    def player_leaves(self, player):
        self.players.remove(player)


class Wall(Field):
    """Поле со стеной, которое отталкивает назад и наносит урон, также присутствует оранжевый цвет для фильтрации"""

    def __init__(self, board, position):
        super().__init__(board, position, is_white=False, is_available=False)

    def player_enters(self, player):
        player.hurt()
        print('Герой ударился о стену!')

    def __repr__(self):
        return 'W'


class Altar(Field):
    """Поле с алтарём, который полностью восстанавливает здоровье"""

    def effect_on_player(self, player):
        super().effect_on_player(player)
        player.full_recovered()
        print('О чудо! Герой нашёл алтарь и здоровье полностью восстановлено!')

    def __repr__(self):
        return 'A'


class Golem(Field):
    """Поле с големом и ключом, который и может открыть именно этого голема"""

    def effect_on_player(self, player):
        super().effect_on_player(player)
        if player.has_key:
            print('Герой победил!')
            player.is_win = True
        else:
            print('У Героя нет ключа!')
            player.die()

    def __repr__(self):
        return 'G'


class EmptySpace(Field):
    """Пустое пространство для придания карте прямоугольной формы, также в контексте данного проекта им придается
    оранжевый цвет для фильтрации белых полей, на которых может загореться огонь"""

    def __init__(self, board, position):
        super().__init__(board, position, is_white=False)

    def __repr__(self):
        return ' '


class Board:
    SYMBOLS = {'a': Altar, 'f': Field, 'w': Wall, 'g': Golem, 'e': EmptySpace}

    def __init__(self, original_board, orange_fields, key_field, burning_fields=None):
        self.key_location = None
        self.burning_fields = []

        self.create_board(original_board, orange_fields)

        # Добавление ключа к заданному полю
        if key_field:
            self.board[key_field].has_key = True
        # Зажжение полей, если переданы при загрузке ранее сохраненной игры
        if burning_fields:
            for pos in burning_fields:
                self.board[pos].is_fire = True

    def create_board(self, original_board, orange_fields):
        width, height = len(original_board[0]), len(original_board)
        self.board = np.empty(shape=(height, width), dtype=object)
        # Конвертация текстовой карты в карту с объектами полей
        for i in range(height):
            for j in range(width):
                self.SYMBOLS[original_board[i][j]](self, position=(i, j))
        # Оранжевые поля
        for pos_x, pos_y in orange_fields:
            self.board[pos_x, pos_y].is_white = False

    def burn(self):
        """В конце раунда случайно из белых полей загораются 4 поля"""
        white_fields = [field for field in self.board.flatten() if field.is_white]
        self.burning_fields = np.random.choice(white_fields, size=4, replace=False)
        for field in white_fields:
            field.is_fire = field in self.burning_fields
        print('Загорелись следующие поля:', ', '.join(str(field.position) for field in self.burning_fields))

    def __getitem__(self, index: tuple):
        return self.board[index]

    def __setitem__(self, key, value):
        self.board[key] = value

    def __str__(self):
        return str(self.board)

    @property
    def to_json(self):
        return dict(burning_fields=[field.position for field in self.burning_fields],
                    key_location=self.key_location)


class Player:
    MAX_HEALTH = 5  # Максимальное значение здоровья игрока
    NUMBER_OF_MEDICINE = 3  # Стартовое значение аптечек

    def __init__(self, name, current_field, previous_field=None, health=MAX_HEALTH, number_of_actions=1,
                 number_of_medicine=NUMBER_OF_MEDICINE, has_key=False):
        self.name = name
        self.health = health
        self.previous_field = previous_field
        self._current_field = None
        self.current_field = current_field
        self.number_of_actions = number_of_actions  # Количество действий для одного хода
        self.number_of_medicine = number_of_medicine
        self.has_key = has_key
        self.is_win = False

    @property
    def current_field(self):
        return self._current_field

    @current_field.setter
    def current_field(self, field):

        field.player_enters(self)

        if field == self.previous_field:
            self.die()
            print('Герой струсил и убежал!')

        if field.is_available:  # изменять локацию игрока, если в клетку разрешен вход
            # проверяем это инициализация или передвижение игрока и какого цвета новая клетка
            if self.current_field and field.is_white:
                self.previous_field = self.current_field

            self._current_field = field

    def spend_action(self, value=1):
        self.number_of_actions -= value

    def move(self, field):
        if self.previous_field == field:  # Убежал
            self.die()

        self.current_field = field
        self.spend_action()

    def strike(self, other):
        print(f'Герой ударил Героя {other.name}')
        other.hurt()

    def strike_all_in_the_field(self):
        if len(self.current_field.players) > 1:  # если в текущем поле, есть другие игроки кроме себя
            for player in self.current_field.players:
                if player != self:
                    self.strike(player)

            self.spend_action()
        else:
            print('А ударить-то некого!')

    def hurt(self, damage=1):
        self.health -= damage

    def take_key(self):
        if self.current_field.has_key:
            self.has_key = True
            self.current_field.has_key = False

            self.spend_action()
            print(f'Герой находит ключ!')
        else:
            print('А брать-то нечего!')

    def drop_key(self):
        if self.has_key:
            self.has_key = False
            self.current_field.has_key = True

    def heal(self):
        if self.number_of_medicine > 0:
            self.number_of_medicine -= 1
            self.health = min(self.health + 1, self.MAX_HEALTH)

            self.spend_action()
            print(f'Герой полечился, жизней - {self.health},  аптечек - {self.number_of_medicine}.')
        else:
            print('У вас нет аптечек!')

    def full_recovered(self):
        """Полное восстановление здоровья"""
        self.health = self.MAX_HEALTH

    def die(self):
        self.health = 0

    @property
    def to_json(self):
        return dict(name=self.name,
                    health=self.health,
                    previous_field=self.previous_field.position if self.previous_field else None,
                    current_field=self.current_field.position,
                    number_of_actions=self.number_of_actions,
                    number_of_medicine=self.number_of_medicine,
                    has_key=self.has_key)


class Game:
    ORIGINAL_BOARD = [['e', 'e', 'e', 'e', 'e', 'w', 'w', 'w', 'w', 'e'],
                      ['e', 'e', 'e', 'w', 'w', 'a', 'f', 'f', 'g', 'w'],
                      ['e', 'e', 'w', 'f', 'w', 'w', 'f', 'w', 'w', 'e'],
                      ['e', 'w', 'f', 'f', 'f', 'w', 'f', 'a', 'w', 'e'],
                      ['w', 'f', 'f', 'w', 'f', 'f', 'f', 'w', 'e', 'e'],
                      ['e', 'w', 'w', 'e', 'w', 'w', 'w', 'e', 'e', 'e']]

    ORANGE_FIELDS = ((2, 3), (1, 5), (3, 7))  # Оранжевые поля
    START_FIELD = (4, 1)  # Стартовая позиция игроков
    KEY_FIELD = (2, 3)  # Поле с ключом

    def __init__(self):
        self.board = Board(self.ORIGINAL_BOARD, self.ORANGE_FIELDS, self.KEY_FIELD)
        self.players = []

    def start(self):
        self.greet()
        self.creating_game()
        self.loop()

    @staticmethod
    def greet():
        print('-' * 90)
        print('{:^90s}'.format('Добро пожаловать'))
        print('{:^90s}'.format('в игру'))
        print('{:^90s}'.format('"Тайны Подземелья"'))
        print('-' * 90)
        print('Правила игры: Первым добраться до голема и с помощью ключа покинуть локацию.')
        print('Доступные команды: "Вверх", "Вниз", "Влево", "Вправо", "Ударить", "Лечиться", "Взять".')
        print('Также Вы в любой момент можете сохранить весь прогресс и выйти из игры с помощью команды: "Сохранить".')
        print('-' * 90)

    def creating_game(self):
        try:
            with open('save.json') as f:
                save = json.load(f)

            if input('Если Вы хотите загрузить игру, введите "Да", иначе будет запущена Новая игра: ').lower() == 'да':
                self.load_game(save)
            else:
                open('save.json', 'w').close()
                self.new_game()

        except (FileNotFoundError, JSONDecodeError):
            self.new_game()

    def new_game(self):
        print('Создание карты...')
        self.board = Board(self.ORIGINAL_BOARD, self.ORANGE_FIELDS, self.KEY_FIELD)
        print('Создание игроков...')
        self.creating_players()

    def load_game(self, save):
        print('Загрузка карты...')
        key_field = tuple(save['board']['key_location']) if save['board']['key_location'] else None
        burning_fields = [tuple(pos) for pos in save['board']['burning_fields']]
        self.board = Board(self.ORIGINAL_BOARD, self.ORANGE_FIELDS, key_field, burning_fields)
        print('Загрузка игроков...')
        for player in save['players']:
            current_field = self.board[tuple(player['current_field'])]
            previous_field = self.board[tuple(player['previous_field'])] if player['previous_field'] else None

            player_load = Player(player['name'],
                                 current_field=current_field,
                                 previous_field=previous_field,
                                 health=player['health'],
                                 number_of_actions=player['number_of_actions'],
                                 number_of_medicine=player['number_of_medicine'],
                                 has_key=player['has_key'])
            self.players.append(player_load)

    def creating_players(self):
        """Создание игроков, размещение их на стартовой позиции поля и добавление в общий список"""
        while True:
            answer = input('Введите количество игроков: ')
            if not answer.isdigit():
                continue

            for i in range(int(answer)):
                name = input(f'Введите имя {i + 1}-го героя: ').title()
                player = Player(name, current_field=self.board[self.START_FIELD])
                self.players.append(player)

            break

    def turn(self, player):
        while player.number_of_actions:  # Пока игрок не потратит действия
            self.check_health(player)  # проверка жизней до хода

            move_directions = {'вверх': (-1, 0), 'вниз': (1, 0), 'влево': (0, -1), 'вправо': (0, 1)}
            actions_player = {'ударить': player.strike_all_in_the_field,
                              'взять': player.take_key,
                              'лечить': player.heal,
                              'сохранить': self.save}
            action = input(f'{player.name}, Ваш ход: ').lower()
            if action in move_directions.keys():
                dx, dy = move_directions[action]
                pos_x, pos_y = player.current_field.position
                new_field = self.board[pos_x + dx, pos_y + dy]
                player.move(new_field)
            elif action in actions_player.keys():
                actions_player[action]()
            else:
                print('Не понял Ваши намерения...')

            self.check_health(player)  # проверка в конце хода

    def death_player(self, player):
        """При смерти происходит сброс ключа, если он был и освобождение клетки"""
        player.drop_key()
        player.current_field.player_leaves(player)
        self.players.remove(player)
        print(f'Герой {player.name} погибает и выбывает из игры...')

    def check_health(self, player):
        if player.health <= 0:
            self.death_player(player)

    def end_of_round(self):
        """Функция вызывается в конце раунда для восстановления возможности ходить игрокам и зажжению огня на 4-х
        случайных полях"""
        for player in self.players:
            player.number_of_actions = 1
        # загораются 4 случайных поля
        self.board.burn()

    def save(self):
        print('Сохранение...')
        with open('save.json', 'w') as f:
            json_obj = dict(players=[player.to_json for player in self.players],
                            board=self.board.to_json)
            json.dump(json_obj, f, indent=4)
        print('Выходим из игры...')
        exit()

    def loop(self):
        while self.players:
            print('-' * 20)
            for player in self.players:
                print(self.board)
                self.turn(player)

                if player.is_win:
                    print(f'Поздравляем! Герой {player.name} преодолел все препятствия и победил!')
                    return

            self.end_of_round()

        print('Конец игры. Игроков больше нет!')


if __name__ == '__main__':
    g = Game()
    g.start()
