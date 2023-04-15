import json
import logging
import sys  # импорт библиотеки sys для логирования в консоль, так как по умолчанию происходит в sys.stderr
from json import JSONDecodeError

import numpy as np

logging.basicConfig(level=logging.INFO,
                    handlers=[logging.StreamHandler(sys.stdout)],
                    format='%(message)s')


class Field:
    """Стандартное поле"""

    def __init__(self, board, position: tuple, is_white=True, is_available=True):
        """
        :param board: Ссылка на доску, которой принадлежит поле.
        :param position: Координаты доски, где располагается поле.
        :param is_white: Является ли поле белым, влияет на запись предыдущего поля и зажжение поля.
        :param is_available: Является ли поле доступным для перехода.
        """
        self.board = board
        self.position = position
        self.is_white = is_white
        self.is_fire = False
        self.is_available = is_available

        self.players = []
        self._has_key = False

        self.board[position] = self

    @property
    def has_key(self):
        """Лежит ли на поле ключ"""
        return self._has_key

    @has_key.setter
    def has_key(self, value):
        """При добавлении или удалении ключа к полю будет изменяться локация ключа на поле для сохранения в файл"""
        self.board.key_location = self.position if value else None
        self._has_key = value

    def effect_on_player(self, player):
        """Эффект поля на игрока в зависимости от того горит ли поле, в дальнейшем будет суммироваться с эффектами
        других полей"""
        if self.is_fire:
            player.hurt()
            logging.info(f'{player} получает урон от огня!')

    def player_enters(self, player):
        """Выполняется при входе игрока на поле. Если текущая позиция игрока уже не пустая, то это движение игрока,
        а не инициализация его на карте. При этом кроме добавления игрока в список игроков этого поля происходит
        очищение поля, с которого игрок уходит и воздействие эффектов поля на игрока"""
        if player.current_field:
            self.status_field(player)
            player.current_field.player_leaves(player)
            self.effect_on_player(player)

        self.players.append(player)

    def player_leaves(self, player):
        self.players.remove(player)

    def status_field(self, player):
        status = f'{player} заходит на поле {self.position}.'
        if self.players:
            status += ' Здесь уже есть следующие герои - ' + ", ".join([str(player) for player in self.players]) + '.'
        if self.has_key:
            status += ' Вы видите ключ.'
        logging.info(status)


class Wall(Field):
    """Поле со стеной, которое отталкивает назад и наносит урон, также присутствует оранжевый цвет для фильтрации"""

    def __init__(self, board, position):
        super().__init__(board, position, is_white=False, is_available=False)

    def player_enters(self, player):
        player.hurt()
        logging.info(f'{player} ударился о стену!')


class Altar(Field):
    """Поле с алтарём, который полностью восстанавливает здоровье"""

    def effect_on_player(self, player):
        super().effect_on_player(player)
        player.full_recovery()
        logging.info(f'О чудо! {player} находит Алтарь и он полностью исцелён!')


class Golem(Field):
    """Поле с големом, является финишным полем. При наличии ключа игрок побеждает, иначе погибает"""

    def effect_on_player(self, player):
        super().effect_on_player(player)
        if player.has_key:
            logging.info(f'\nПоздравляем! {player} преодолел все препятствия и победил!')
            player.is_win = True
        else:
            logging.info(f'{player} нашел Голема, но у него нет ключа!')
            player.die()


class EmptySpace(Field):
    """Пустое поле для придания карте прямоугольной формы, также в контексте данного проекта ему придается
    оранжевый цвет для фильтрации белых полей, на которых может загореться огонь"""

    def __init__(self, board, position):
        super().__init__(board, position, is_white=False)


class Board:
    SYMBOLS = {'a': Altar, 'f': Field, 'w': Wall, 'g': Golem, 'e': EmptySpace}

    def __init__(self, original_board, orange_fields, key_field, burning_fields=None):
        """
        При создании карты происходит ее рендирования из заданного текстового формата в двухмерный массив объектов
        полей в зависимости от буквы на оригинальной доске;
        :param original_board: Двухмерный массив оригинальной доски в текстовом формате;
        :param orange_fields: Список полей оранжевого цвета;
        :param key_field: Позиция расположение ключа на поле. При загрузке игры может быть None, так как ключ может
        принадлежать игроку;
        :param burning_fields: Список уже горящих полей, может передаваться только при загрузке игры.
        """
        self.key_location = None
        self.burning_fields = []

        self.create_board(original_board, orange_fields, key_field, burning_fields)

    def create_board(self, original_board, orange_fields, key_field, burning_fields):
        """Конвертация текстовой карты в карту с объектами полей, огнями и ключом"""
        width, height = len(original_board[0]), len(original_board)
        self.board = np.empty(shape=(height, width), dtype=object)

        for i in range(height):
            for j in range(width):
                self.SYMBOLS[original_board[i][j]](self, position=(i, j))

        for pos in orange_fields:
            self.board[pos].is_white = False

        if key_field:
            self.board[key_field].has_key = True

        if burning_fields:
            for pos in burning_fields:
                field = self.board[pos]
                field.is_fire = True
                self.burning_fields.append(field)
            logging.info(
                'Горят следующие поля: ' + ', '.join(str(field.position) for field in self.burning_fields) + '.')

    def burn(self):
        """В конце раунда случайно только из белых полей загораются 4 поля"""
        white_fields = [field for field in self.board.flatten() if field.is_white]
        self.burning_fields = np.random.choice(white_fields, size=4, replace=False)
        for field in white_fields:
            field.is_fire = field in self.burning_fields
        logging.info(
            'Загорелись следующие поля: ' + ', '.join(str(field.position) for field in self.burning_fields) + '.')

    def __getitem__(self, index: tuple):
        return self.board[index]

    def __setitem__(self, key, value):
        self.board[key] = value

    @property
    def to_json(self) -> dict:
        """Создание словаря для записи статуса доски в json"""
        return dict(burning_fields=[field.position for field in self.burning_fields],
                    key_location=self.key_location)


class Player:
    MAX_HEALTH = 5
    NUMBER_OF_MEDICINE = 3

    def __init__(self, name, current_field, previous_fields=None, health=MAX_HEALTH, number_of_actions=1,
                 number_of_medicine=NUMBER_OF_MEDICINE, has_key=False):
        """
        При создании игрока вводятся только первые два параметра, при загрузке - все.
        :param name: Имя игрока;
        :param current_field: Текущее поле карты, с расположением игрока.
        :param previous_fields: Список предыдущих мест расположений игрока на карте, может быть только одно белое и
        одно оранжевое.
        :param health: Текущее здоровье игрока.
        :param number_of_actions: Количество действий еще доступных игроку, обновляется в конце раунда.
        :param number_of_medicine: Текущее количество аптечек игрока.
        :param has_key: Есть ли ключ у игрока, необходимо наличие для победы.
        """
        self.name = name
        self.health = health
        self.previous_fields = previous_fields if previous_fields else []
        self._current_field = None
        self.current_field = current_field
        self.number_of_actions = number_of_actions
        self.number_of_medicine = number_of_medicine
        self.has_key = has_key
        self.is_win = False
        self.is_escaped = False

    def __str__(self):
        return f'Герой {self.name}'

    @property
    def current_field(self):
        return self._current_field

    @current_field.setter
    def current_field(self, field):
        """При изменении текущей локации игрока проверяется не является ли ход игрока бегством, а также является ли
        поле доступным для перехода (field.is_available), а также менять значение предыдущего поля, если это именно
        движение игрока и новое поле белого цвета"""
        if field in self.previous_fields:
            self.die()
            self.is_escaped = True
            logging.info(f'{self} струсил и убежал!')
            return

        field.player_enters(self)

        if field.is_available:
            if self.current_field and field.is_white:
                if self.current_field.is_white:
                    self.previous_fields = [self.current_field]
                else:
                    self.previous_fields.append(self.current_field)

            self._current_field = field

    def spend_action(self, value=1):
        """Трата действий игрока при совершении хода"""
        self.number_of_actions -= value

    def move(self, field):
        """Движение игрока"""
        self.current_field = field
        self.spend_action()

    def strike(self, other):
        """Удар игрока"""
        logging.info(f'{self} ударил {other}')
        other.hurt()

    def strike_all_in_the_field(self):
        """Удар игрока по всем игрокам, если они присутствуют на поле, иначе действие не тратится"""
        if len(self.current_field.players) > 1:  # если в текущем поле, есть другие игроки кроме себя
            for player in self.current_field.players:
                if player != self:
                    self.strike(player)

            self.spend_action()
        else:
            logging.warning('А ударить-то некого!')

    def hurt(self, damage=1):
        """Ранение игрока"""
        self.health -= damage

    def take_key(self):
        """Взять ключ, если он области досягаемости"""
        if self.current_field.has_key:
            self.has_key = True
            self.current_field.has_key = False

            self.spend_action()
            logging.info(f'{self} находит ключ!')
        else:
            logging.info('А брать-то нечего!')

    def drop_key(self):
        """Сброс ключа в текущее поле"""
        if self.has_key:
            self.has_key = False
            self.current_field.has_key = True
            logging.info(f'{self} теряет ключ на поле {self.current_field.position}')

    def heal(self):
        """Лечение игрока"""
        if self.number_of_medicine > 0:
            self.number_of_medicine -= 1
            self.health = min(self.health + 1, self.MAX_HEALTH)

            self.spend_action()
            logging.info(f'{self} полечился.')
        else:
            logging.info('У вас нет аптечек!')

    def full_recovery(self):
        """Полное восстановление здоровья"""
        self.health = self.MAX_HEALTH

    def die(self):
        """Смерть игрока"""
        self.health = 0

    @property
    def is_alive(self):
        return self.health > 0

    @property
    def to_json(self) -> dict:
        """Создание словаря для записи статуса игрока в json"""
        return dict(name=self.name,
                    health=self.health,
                    previous_fields=[field.position
                                     for field in self.previous_fields] if self.previous_fields else None,
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

    ORANGE_FIELDS = ((2, 3), (1, 5), (3, 7))
    START_FIELD = (4, 1)
    KEY_FIELD = (2, 3)

    def __init__(self):
        self.board = Board(self.ORIGINAL_BOARD, self.ORANGE_FIELDS, self.KEY_FIELD)
        self.players = []

    def start(self):
        self.greet()
        self.creating_game()
        self.loop()

    @staticmethod
    def greet():
        print('-' * 100)
        print('{:^100s}'.format('Добро пожаловать'))
        print('{:^100s}'.format('в игру'))
        print('{:^100s}'.format('"Тайны Подземелья"'))
        print('-' * 100)
        print('Правила игры: Первым добраться до голема и с помощью ключа покинуть локацию.')
        print('Возврат на предыдущую клетку, если Вы вернулись не с оранжевой клетки означает бегство.')
        print('На оранжевую клетку можно зайти лишь 1 раз.')
        print('Ход пропускать нельзя, у вас имеется 3 аптечки. При столкновении со стеной получаете урон.')
        print('При нанесении удара по противникам, получают урон все Герои, находящиеся в этой клетке.')
        print('Доступные команды: "вверх", "вниз", "влево", "вправо", "ударить", "лечить", "взять".')
        print('Также Вы в любой момент можете сохранить весь прогресс и выйти из игры с помощью команды: "сохранить".')
        print('-' * 100)

    def creating_game(self):
        """При наличии файла сохраненной игры и успешной попытки декодирования данных, игроку предлагается загрузить
        игру. При отказе создается новая игра. Также по умолчанию файл сохраненной игры всегда обнуляется."""
        try:
            with open('save.json') as f:
                save = json.load(f)

            if input('Если Вы хотите ЗАГРУЗИТЬ игру, введите "да", иначе будет запущена НОВАЯ игра: ').lower() == 'да':
                self.load_game(save)
            else:
                self.new_game()

        except (FileNotFoundError, JSONDecodeError):
            self.new_game()
        finally:
            open('save.json', 'w').close()

    def new_game(self):
        """Новая игра"""
        self.board = Board(self.ORIGINAL_BOARD, self.ORANGE_FIELDS, self.KEY_FIELD)
        self.creating_players()

    def load_game(self, save):
        """Загрузка игра"""
        print('Загрузка карты...')
        key_field = tuple(save['board']['key_location']) if save['board']['key_location'] else None
        burning_fields = [tuple(pos) for pos in save['board']['burning_fields']]
        self.board = Board(self.ORIGINAL_BOARD, self.ORANGE_FIELDS, key_field, burning_fields)
        print('Загрузка игроков...')
        for player in save['players']:
            current_field = self.board[tuple(player['current_field'])]
            if player['previous_fields']:
                previous_fields = [self.board[tuple(pos)] for pos in player['previous_fields']]
            else:
                previous_fields = None

            player_load = Player(player['name'],
                                 current_field=current_field,
                                 previous_fields=previous_fields,
                                 health=player['health'],
                                 number_of_actions=player['number_of_actions'],
                                 number_of_medicine=player['number_of_medicine'],
                                 has_key=player['has_key'])
            self.players.append(player_load)

    def creating_players(self):
        """Создание игроков, размещение их на стартовой позиции поля и добавление в общий список игроков"""
        while True:
            answer = input('Введите количество игроков: ')
            if not answer.isdigit():
                continue

            for i in range(int(answer)):
                name = input(f'Введите имя {i + 1}-го героя: ').title()
                player = Player(name, current_field=self.board[self.START_FIELD])
                self.players.append(player)

            return

    def turn(self, player):
        """Ход игрока. В начале и в конце хода проверяется количество здоровья игрока. Пока игрок не совершит
        результативное действие у него будет возможность ходить. Также при возможности взять ключ, ему будет выведена в
        сообщение"""
        while player.number_of_actions and player.is_alive:

            if player.current_field.has_key:
                logging.info(f'{player} может взять ключ!')

            move_directions = {'вверх': (-1, 0), 'вниз': (1, 0), 'влево': (0, -1), 'вправо': (0, 1)}
            actions = {'ударить': player.strike_all_in_the_field,
                       'взять': player.take_key,
                       'лечить': player.heal,
                       'сохранить': self.save}
            action = input(
                f'{player}, у Вас жизней - {player.health} и аптечек - {player.number_of_medicine}. Ваши действия: '
            ).lower()
            if action in move_directions:
                dx, dy = move_directions[action]
                pos_x, pos_y = player.current_field.position
                new_field = self.board[pos_x + dx, pos_y + dy]
                player.move(new_field)
            elif action in actions:
                actions[action]()
            else:
                print('Не понял Ваши намерения...')

        if not player.is_alive:
            if not player.is_escaped:
                logging.info(f'{player} погибает!')
            self.destroy(player)

    def destroy(self, player):
        """При смерти происходит сброс ключа, если он был и освобождение клетки"""
        player.drop_key()
        player.current_field.player_leaves(player)
        self.players.remove(player)
        logging.info(f'{player} выводится из игры...')

    def end_of_round(self):
        """Функция вызывается в конце раунда для восстановления возможности ходить игрокам и зажжению огня на 4-х
        случайных полях"""
        for player in self.players:
            player.number_of_actions = 1

        self.board.burn()

    def save(self):
        """Сохранение игры в json-файл"""
        print('Сохранение...')
        with open('save.json', 'w') as f:
            json_obj = dict(players=[player.to_json for player in self.players],
                            board=self.board.to_json)
            json.dump(json_obj, f, indent=4)
        print('Выходим из игры...')
        exit()

    def loop(self):
        """Основной цикл программы. Итерация идет по копии списка игроков, чтобы при удалении игроков из списка итератор
         не сбивался"""
        while self.players:
            print('-' * 100)
            for player in self.players[:]:
                self.turn(player)
                print()
                if player.is_win:
                    return

            self.end_of_round()
        print('\nКонец игры. Игроков больше нет!')


if __name__ == '__main__':
    g = Game()
    g.start()
