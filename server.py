import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from random import randint
from Chess_Classes import *
from PIL import Image
import sqlite3
import schedule
from multiprocessing import Process

TOKEN = 'vk1.a.qOQPyAdJ_Z5WwjzbNl_WFUq2P05QGpwj-537I7vwLTneH1Fz06BBEslq0_rbUGJFabRakR9V-pL7dzhhx6qCeHA-AP2wNndJTFHYQ7sKmPyiAB05KWIkfmH4G_Gl9luw3qqe8UvwB6tTTaojNW1EcIHjgP8uX5Z89ppE5Mv2cpaWrEmrWtD9b9GC1ulJ_viLiTwOfjTcBd4mqifQqazVZw'
GROUP_ID = 219645807


def ping():
    session = vk_api.VkApi(token=TOKEN)
    session.get_api().messages.send(user_id=485414809, message='ping', random_id=randint(0, 2 ** 64))


def dude():
    schedule.every(3).minutes.do(ping)
    while 1:
        schedule.run_pending()


def to_cords(loc):
    try:
        if len(loc) != 2:
            return False
        row, col = int(loc[1]) - 1, ord(loc[0].lower()) - ord('a')
        if row not in range(8) or col not in range(8):
            return False
        return row, col
    except Exception:
        return False


def build_field_img(field, player):
    img = Image.new('RGB', (680, 680))
    if player:
        for i in range(8):
            for j in range(8):
                figure = Image.open(f"data/figures/{repr(field[i][j])}{(i + j) % 2}.png")
                img.paste(figure, (80 * (7 - j), 80 * (7 - i)))
    else:
        for i in range(8):
            for j in range(8):
                figure = Image.open(f"data/figures/{repr(field[i][j])}{(i + j) % 2}.png")
                img.paste(figure, (80 * j, 80 * i))
    img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if player:
        img.paste(Image.open('data/num_for_white.png'), (0, 0))
        img.paste(Image.open('data/let_for_white.png'), (40, 640))
    else:
        img.paste(Image.open('data/num_for_black.png'), (0, 0))
        img.paste(Image.open('data/let_for_black.png'), (40, 640))
    img.save('data/field.png')


def field_to_str(field):
    ans = f'{field.step};'
    for i in range(8):
        for j in range(8):
            ans += repr(field.field[i][j]) + ';'
    return ans[:-1]


def str_to_field(string):
    game = ChessField()
    figures = string.split(';')
    game.step = int(figures.pop(0))
    for i in range(8):
        for j in range(8):
            if 'None' not in figures[i * 8 + j]:
                figure_classes[figures[i * 8 + j][:-1]](i, j, int(figures[i * 8 + j][-1]), game).put()
    return game


NO_ENEMY, WAITING_FOR_ACCEPT, FIGHTING = 0, 1, 2


class Player:
    def __init__(self):
        self.color = 1
        self.edit_field = None
        self.game_field = None
        self.enemy = None
        self.condition = NO_ENEMY
        self.waiting = set()
        self.bet = False


class Bot:
    def __init__(self):
        self.session = vk_api.VkApi(token=TOKEN)
        self.long_poll = None
        self.players = dict()

    def send_message(self, user, message):
        self.session.get_api().messages.send(user_id=user, message=message, random_id=randint(0, 2 ** 64))

    def start(self):
        self.long_poll = VkBotLongPoll(self.session, GROUP_ID)

    def main_cycle(self):
        print('--------------------------------------------')
        Process(target=dude).start()
        for event in self.long_poll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                self.process_command(event.object.message["from_id"], event.object.message["text"])
                print(f'sender: {event.object.message["from_id"]}')
                print(f'text: {event.object.message["text"]}')
                print('--------------------------------------------')

    def send_field(self, user, color, message, field=False):
        if field:
            send = field
        else:
            if self.players[user].condition == NO_ENEMY:
                send = self.players[user].edit_field.field
            else:
                send = self.players[user].game_field.field
        build_field_img(send, color)
        vk = self.session.get_api()
        upload = vk_api.VkUpload(vk)
        vk_image = upload.photo_messages('data/field.png')
        owner_id = vk_image[0]['owner_id']
        photo_id = vk_image[0]['id']
        access_key = vk_image[0]['access_key']
        attachment = f'photo{owner_id}_{photo_id}_{access_key}'
        vk.messages.send(user_id=user, peer_id=user, random_id=0, attachment=attachment, message=message)

    def end_check(self, user):
        if self.players[user].game_field.end:
            self.send_message(user, 'you\'ve won, game is finished')
            self.send_message(self.players[user].enemy, 'you\'ve lost, game is finished')
            if self.players[user].bet:
                con = sqlite3.connect('data.db')
                cur = con.cursor()
                rating = [x[0] for x in cur.execute("""SELECT rating FROM top WHERE user_id = ?""", (user, ))][0]
                cur.execute("""UPDATE top SET rating = ? WHERE user_id = ?""", (rating + 1, user))
                self.send_message(user, f'your rating now is {rating + 1}')
                rating = [x[0] for x in cur.execute("""SELECT rating FROM top WHERE user_id = ?""", (self.players[user].enemy, ))][0]
                cur.execute("""UPDATE top SET rating = ? WHERE user_id = ?""",
                            (rating - 1 if rating > 0 else 0, self.players[user].enemy))
                self.send_message(self.players[user].enemy, f'your rating now is {rating - 1 if rating > 0 else 0}')
                con.commit()
            self.players[user].condition = NO_ENEMY
            self.players[self.players[user].enemy].condition = NO_ENEMY
            self.players[self.players[user].enemy].bet = False
            self.players[user].bet = False
            self.players[user].game_field = None
            self.players[self.players[user].enemy].game_field = None
            self.players[self.players[user].enemy].enemy = None
            self.players[user].enemy = None
            return True
        return False

    def process_put(self, user, command):
        if len(command) != 4:
            self.send_message(user, 'wrong command structure\ntype "/help put" for more information')
            return
        if self.players[user].condition != NO_ENEMY:
            self.send_message(user, 'too late for any customisation')
            return
        if self.players[user].edit_field is None:
            self.send_message(user, 'create field with "/field create" first')
            return
        try:
            figure = figure_classes[command[1].lower().capitalize()]
        except KeyError:
            self.send_message(user, 'wrong command arguments\ntype "/help put" for more information')
            return
        if to_cords(command[2]):
            row, col = to_cords(command[2])
        else:
            self.send_message(user, 'wrong command arguments\ntype "/help put" for more information')
            return
        try:
            color = colors[command[3].lower()]
            self.players[user].edit_field.put_figure(figure, row, col, color)
            self.send_field(user, self.players[user].color, 'figure put successfully')
        except Exception:
            self.send_message(user, 'wrong command arguments\ntype "/help put" for more information')

    def process_remove(self, user, command):
        if len(command) != 2:
            self.send_message(user, 'wrong command structure\ntype "/help remove" for more information')
            return
        if self.players[user].condition != NO_ENEMY:
            self.send_message(user, 'too late for any customisation')
            return
        if self.players[user].edit_field is None:
            self.send_message(user, 'create field with "/field create" first')
            return
        if to_cords(command[1]):
            row, col = to_cords(command[1])
            if not self.players[user].edit_field.field[row][col]:
                self.send_message(user, 'nothing to remove')
                return
            self.players[user].edit_field.field[row][col].die()
            self.send_field(user, self.players[user].color, 'figure removed successfully')
        else:
            self.send_message(user, 'wrong command arguments\ntype "/help remove" for more information')

    def process_set(self, user, command):
        if len(command) != 3:
            self.send_message(user, 'wrong command structure\ntype "/help set" for more information')
            return
        if self.players[user].condition != NO_ENEMY:
            self.send_message(user, 'too late for any customisation')
            return
        if self.players[user].edit_field is None:
            self.send_message(user, 'create field with "/field create" first')
            return
        if command[1] == 'color':
            if command[2] == 'random':
                self.players[user].color = randint(0, 1)
                self.send_message(user, 'user color set successfully')
                return
            try:
                self.players[user].color = colors[command[2]]
                self.send_message(user, 'user color set successfully')
            except KeyError:
                self.send_message(user, 'wrong command arguments\ntype "/help set" for more information')
                return
        elif command[1] == 'first':
            if command[2] == 'random':
                self.players[user].edit_field.step = randint(0, 1)
                self.send_message(user, 'first step set successfully')
                return
            try:
                self.players[user].edit_field.step = colors[command[2]]
                self.send_message(user, 'first step set successfully')
            except KeyError:
                self.send_message(user, 'wrong command arguments\ntype "/help set" for more information')
                return
        else:
            self.send_message(user, 'wrong command arguments\ntype "/help set" for more information')

    def process_challenge(self, user, command):
        if len(command) != 3:
            self.send_message(user, 'wrong command structure\ntype "/help challenge" for more information')
            return
        if command[1] == 'offer':
            if str(user) == command[2]:
                self.send_message(user, 'you can\'t challenge yourself')
                return
            if self.players[user].condition != NO_ENEMY:
                self.send_message(user, 'end your previous conflict first')
                return
            if self.players[user].edit_field is None:
                self.players[user].game_field = ChessField()
                self.players[user].game_field.build()
            else:
                self.players[user].game_field = self.players[user].edit_field.copy()
            if self.players[user].game_field.rigged():
                self.send_message(user, 'unavailable field to play')
                return
            try:
                if int(command[2]) not in self.players:
                    self.players[int(command[2])] = Player()
                self.send_field(int(command[2]), 1 - self.players[user].color,
                                f'you have been challenged by {user}\ntype "/challenge accept {user}" to accept challenge\nelse type "/challenge deny {user}"',
                                self.players[user].game_field.field)
                self.send_message(user, 'waiting for player reply...')
                self.players[user].condition = WAITING_FOR_ACCEPT
                self.players[user].enemy = int(command[2])
                self.players[int(command[2])].waiting.add(user)
            except ValueError:
                self.send_message(user,
                                  'this user hasn\'t started dialog with bot yet or does not exist at all\ntype "/help challenge" for more information')
        elif command[1] == 'cancel':
            if self.players[user].condition == NO_ENEMY:
                self.send_message(user, 'no challenge offered to any user right now')
                return
            if self.players[user].condition == FIGHTING:
                self.send_message(user, 'too late to cancel challenge')
                return
            if self.players[user].enemy != int(command[2]):
                self.send_message(user, 'you didn\'t challenge this player')
                return
            self.send_message(int(command[2]), f'{user} canceled his offer')
            self.send_message(user, 'challenge cancelled successfully')
            self.players[user].enemy = None
            self.players[int(command[2])].waiting.remove(user)
            self.players[user].condition = NO_ENEMY
        elif command[1] == 'accept':
            if self.players[user].condition == FIGHTING:
                self.send_message(user, 'you can\'t accept challenge while having another fight')
                return
            if int(command[2]) not in self.players[user].waiting:
                self.send_message(user, 'this player didn\'t challenge you')
                return
            self.players[user].condition = FIGHTING
            self.players[int(command[2])].condition = FIGHTING
            self.players[user].enemy = int(command[2])
            self.players[user].waiting.remove(int(command[2]))
            self.players[user].game_field = self.players[int(command[2])].game_field
            self.players[user].color = 1 - self.players[int(command[2])].color
            if self.players[user].game_field.is_basic():
                self.players[user].bet = True
                self.players[int(command[2])].bet = True
            self.send_message(user, 'challenge accepted successfully')
            self.send_message(int(command[2]), 'you challenge has been accepted')
        elif command[1] == 'deny':
            try:
                if int(command[2]) not in self.players[user].waiting:
                    self.send_message(user, 'this player didn\'t challenge you')
                    return
            except Exception:
                self.send_message(user, 'this player didn\'t challenge you')
                return
            self.players[user].waiting.remove(int(command[2]))
            self.players[int(command[2])].enemy = None
            self.players[int(command[2])].condition = NO_ENEMY
            self.send_message(user, 'challenge denied successfully')
            self.send_message(int(command[2]), 'you challenge has been denied')
        else:
            self.send_message(user, 'wrong command arguments\ntype "/help challenge" for more information')

    def process_surrender(self, user, command):
        if len(command) != 1:
            self.send_message(user, 'wrong command structure\ntype "/help surrender" for more information')
            return
        if self.players[user].condition != FIGHTING:
            self.send_message(user, 'you\'re not fighting right now')
            return
        vk = self.session.get_api()
        upload = vk_api.VkUpload(vk)
        vk_image = upload.photo_messages('data/fool.png')
        owner_id = vk_image[0]['owner_id']
        photo_id = vk_image[0]['id']
        access_key = vk_image[0]['access_key']
        attachment = f'photo{owner_id}_{photo_id}_{access_key}'
        vk.messages.send(user_id=user, peer_id=user, random_id=0, attachment=attachment, message="you\'ve surrendered")
        self.send_message(self.players[user].enemy, 'your enemy have surrendered')
        if self.players[user].bet:
            con = sqlite3.connect('data.db')
            cur = con.cursor()
            rating = [x[0] for x in cur.execute("""SELECT rating FROM top WHERE user_id = ?""", (self.players[user].enemy,))][0]
            cur.execute("""UPDATE top SET rating = ? WHERE user_id = ?""", (rating + 1, self.players[user].enemy))
            self.send_message(self.players[user].enemy, f'your rating now is {rating + 1}')
            rating = [x[0] for x in cur.execute("""SELECT rating FROM top WHERE user_id = ?""", (user,))][0]
            cur.execute("""UPDATE top SET rating = ? WHERE user_id = ?""",
                        (rating - 1 if rating > 0 else 0, user))
            self.send_message(user, f'your rating now is {rating - 1 if rating > 0 else 0}')
            con.commit()
        self.players[user].condition = NO_ENEMY
        self.players[self.players[user].enemy].condition = NO_ENEMY
        self.players[self.players[user].enemy].bet = False
        self.players[user].bet = False
        self.players[user].game_field = None
        self.players[self.players[user].enemy].game_field = None
        self.players[self.players[user].enemy].enemy = None
        self.players[user].enemy = None

    def process_field(self, user, command):
        if len(command) == 2:
            if self.players[user].condition != NO_ENEMY:
                self.send_message(user, 'too late for any field customisation')
                return
            if command[1] == 'delete':
                if self.players[user].edit_field:
                    self.players[user].edit_field = None
                    self.players[user].color = 1
                    self.send_message(user, 'field deleted successfully')
                else:
                    self.send_message(user, 'no field to delete')
            elif command[1] == 'clear':
                self.players[user].edit_field.made_in_heaven()
                self.send_message(user, 'field cleared successfully')
            else:
                self.send_message(user, 'wrong command arguments\ntype "/help field" for more information')
        elif len(command) == 3:
            if self.players[user].condition != NO_ENEMY:
                self.send_message(user, 'too late for any field customisation')
                return
            if command[1] == 'save':
                field_name = command[2]
                field = field_to_str(self.players[user].edit_field)
                try:
                    con = sqlite3.connect('data.db')
                    cur = con.cursor()
                    cur.execute('INSERT INTO data(title, user, field) VALUES(?, ?, ?)', (field_name, user, field))
                    con.commit()
                    self.send_message(user, 'field saved successfully')
                except Exception:
                    self.send_message(user, 'this name has already used, please try another one')
            elif command[1] == 'create':
                if self.players[user].edit_field:
                    self.send_message(user,
                            'field already exists\ndelete previous field with "/field delete" first to create new one')
                else:
                    if command[2] == 'empty':
                        self.players[user].edit_field = ChessField()
                        self.send_field(user, self.players[user].color, 'field created successfully\n"/field save" to save your field')
                    elif command[2] == 'basic':
                        self.players[user].edit_field = ChessField()
                        self.players[user].edit_field.build()
                        self.send_field(user, self.players[user].color, 'field created successfully\n"/field save" to save your field')
                    else:
                        self.send_message(user, 'wrong command arguments\ntype "/help field" for more information')
            elif command[1] == 'load':
                try:
                    con = sqlite3.connect('data.db')
                    cur = con.cursor()
                    field = [x[0] for x in cur.execute("""SELECT field FROM data WHERE title = ?""", (command[2],))][0]
                    self.players[user].edit_field = str_to_field(field)
                    self.send_field(user, self.players[user].color, 'field loaded successfully')
                except Exception:
                    self.send_message(user, 'field with this name doesn\'t exist')
            elif command[1] == 'list':
                con = sqlite3.connect('data.db')
                cur = con.cursor()
                if command[2] == 'all':
                    fields_names = [x[0] for x in cur.execute("""SELECT title FROM data""")]
                else:
                    fields_names = [x[0] for x in cur.execute("""SELECT title FROM data WHERE user=?""", (user, ))]
                send = []
                for i in range(len(fields_names)):
                    send.append(f'{i + 1}. {fields_names[i]}')
                self.send_message(user, '\n'.join(send))
            else:
                self.send_message(user, 'wrong command arguments\ntype "/help field" for more information')
        else:
            self.send_message(user, 'wrong command structure\ntype "/help field" for more information')

    def process_move(self, user, command):
        if len(command) != 3:
            self.send_message(user, 'wrong command structure\ntype "/help move" for more information')
            return
        if self.players[user].condition != FIGHTING:
            self.send_message(user, 'you\'re not fighting right now')
            return
        if self.players[user].color != self.players[user].game_field.step:
            self.send_message(user, 'it\'s not your move now')
            return
        if self.players[user].game_field.transform_check(self.players[user].color):
            self.send_message(user,
                              'choose what figure to transform your pawn into with "/transform {figure_class} first"')
            return
        if to_cords(command[1]) and to_cords(command[2]):
            row0, col0 = to_cords(command[1])
            row1, col1 = to_cords(command[2])
            self.players[user].game_field.add_act(row0, col0)
            if self.players[user].game_field.add_act(row1, col1):
                if self.players[user].game_field.transform_check(self.players[user].color):
                    self.players[user].game_field.change_step()
                    self.send_field(user, self.players[user].color,
                                      'choose what figure to transform your pawn into with "/transform {figure_class}"')
                    return
                self.send_field(user, self.players[user].color, 'move done successfully')
                self.send_field(self.players[user].enemy, 1 - self.players[user].color, 'enemy move has been done')
                if self.end_check(user):
                    return
            else:
                self.send_message(user, 'this move can\'t be done')
        elif command[1] == 'castling':
            row = 7 * (1 - self.players[user].color)
            if type(self.players[user].game_field.field[row][4]) != King:
                self.send_message(user, 'castling can\'t be done')
                return
            if command[2] == 'long':
                for col in (4, 1, 0):
                    self.players[user].game_field.add_act(row, col)
                if len(self.players[user].game_field.acts) != 3:
                    self.send_message(user, 'castling can\'t be done')
                    self.players[user].game_field.acts.clear()
                    return
                if self.players[user].game_field.add_act(row, 2):
                    self.send_field(user, self.players[user].color, 'castling done successfully')
                    self.send_field(self.players[user].enemy, 1 - self.players[user].color, 'enemy move has been done')
                    if self.end_check(user):
                        return
            elif command[2] == 'short':
                for col in (4, 6, 7):
                    self.players[user].game_field.add_act(row, col)
                if len(self.players[user].game_field.acts) != 3:
                    self.send_message(user, 'castling can\'t be done')
                    self.players[user].game_field.acts.clear()
                    return
                if self.players[user].game_field.add_act(row, 5):
                    self.send_field(user, self.players[user].color, 'castling done successfully')
                    self.send_field(self.players[user].enemy, 1 - self.players[user].color, 'enemy move has been done')
                    if self.end_check(user):
                        return
            else:
                self.send_message(user, 'wrong command arguments\ntype "/help move" for more information')
        else:
            self.send_message(user, 'wrong command arguments\ntype "/help move" for more information')

    def process_transform(self, user, command):
        if len(command) != 2:
            self.send_message(user, 'wrong command structure\ntype "/help transform" for more information')
            return
        if self.players[user].condition != FIGHTING:
            self.send_message(user, 'you\'re not fighting right now')
            return
        if self.players[user].color != self.players[user].game_field.step:
            self.send_message(user, 'it\'s not your move now')
            return
        if not self.players[user].game_field.transform_check(self.players[user].color):
            self.send_message(user, 'no pawn to transform')
            return
        try:
            figure = figure_classes[command[1].lower().capitalize()]
            if figure in (King, Pawn):
                self.send_message(user, 'pawn can\'t be transformed into that type of figure')
                return
            row, col = self.players[user].game_field.transform_check(self.players[user].color)
            self.players[user].game_field.field[row][col].transform(figure)
            self.players[user].game_field.last_move.clear()
            self.players[user].game_field.change_step()
            self.send_field(user, self.players[user].color, 'figure changed successfully')
            self.send_field(self.players[user].enemy, 1 - self.players[user].color, 'enemy move has been done')
            if self.end_check(user):
                return
        except Exception:
            self.send_message(user, 'wrong command arguments\ntype "/help transform" for more information')

    def process_message(self, user, command, original):
        message = original[original.find(command[1]) + len(command[1]) + 1:].strip()
        if len(command) < 3:
            self.send_message(user, 'wrong command structure\ntype "/help message" for more information')
            return
        if command[1] == 'enemy':
            if self.players[user].condition != NO_ENEMY:
                self.send_message(self.players[user].enemy, f'message received from user {user}:\n{message}')
                self.send_message(int(command[1]), f'reply user {user} with "/message {user} your_message"')
                self.send_message(user, 'message sent successfully')
        else:
            try:
                self.send_message(int(command[1]), f'message received from user {user}:\n{message}')
                self.send_message(int(command[1]), f'reply user {user} with "/message {user} your_message"')
                self.send_message(user, 'message sent successfully')
            except Exception:
                self.send_message(user,
                                  'this user hasn\'t started dialog with bot yet or does not exist at all\ntype "/help message" for more information')

    def process_top(self, user, command):
        con = sqlite3.connect('data.db')
        cur = con.cursor()
        rating = sorted([x for x in cur.execute("""SELECT * FROM top""")], key=lambda i: i[1], reverse=True)
        if len(command) == 1:
            n = 10
        elif len(command) == 2:
            try:
                n = int(command[1])
            except Exception:
                if command[1] == 'all':
                    n = len(rating)
                else:
                    self.send_message(user, 'wrong command structure\ntype "/help top" for more information')
                    return
        else:
            self.send_message(user, 'wrong command structure\ntype "/help top" for more information')
            return
        top = []
        for i in range(n):
            try:
                user_info = self.session.method('users.get', {'user_ids': rating[i][0]})
                url = f"https://vk.com/id{user_info[0]['id']}"
                fullname = f"{user_info[0]['first_name']} {user_info[0]['last_name']}"
                top.append(f'{i + 1}. {fullname} {url} - {rating[i][1]}')
            except Exception:
                break
        top.append('-' * 75)
        user_rating = [(rating[i][1], i + 1) for i in range(len(rating)) if rating[i][0] == user][0]
        top.append(f'You are now on {user_rating[1]} place, your rating: {user_rating[0]}')
        self.send_message(user, '\n'.join(top))

    def process_find(self, user, command):
        if not len(command) == 3:
            self.send_message(user, 'wrong command structure\ntype "/help find" for more information')
            return
        else:
            name, surname = command[1:]
            id = []
            con = sqlite3.connect('data.db')
            cur = con.cursor()
            rating = sorted([x for x in cur.execute("""SELECT * FROM top""")], key=lambda i: i[1])
            for i in range(len(rating)):
                user_info = self.session.method('users.get', {'user_ids': rating[i][0]})
                if name == user_info[0]['first_name'] and surname == user_info[0]['last_name']:
                    id.append(f'{rating[i][0]} https://vk.com/id{rating[i][0]}')
            if id:
                for i in id:
                    id, url = i.split()
                    self.send_message(user, f'{name} {surname} id: {id}\nprofile: {url}')
            else:
                self.send_message(user, 'this user doesn\'t exists or never wrote to this bot')

    def process_help(self, user, command):
        if len(command) != 2:
            self.send_message(user, 'wrong command structure, use "/help {command}"')
        elif command[1] == 'put':
            self.send_message(user,
'''"put" command is used to put figure on the field while it\'s edited

formats:
/put {figure type} {location} {color}

figure type can be: Queen, King, Rook, Knight, Bishop, Pawn
location must be written in format of {col}{row} like e2, g5, h1
color can be one of: white, black

examples:
/put Rook c5 white''')
        elif command[1] == 'remove':
            self.send_message(user,
'''"remove" command is used to remove figure from the field while it\'s edited

formats:
/remove {location}

location must be written in format of {col}{row} like e2, g5, h1

examples:
/remove e2''')
        elif command[1] == 'set':
            self.send_message(user,
'''"set" command is used to set some characteristics of field while it\'s edited

formats:
/set color {color}
/set first {color}

color in all cases can be one of: white, black, random
"/set color {color}" sets color user currently editing field will play
"/set first {color}" sets player of which color will make o move first

examples:
/set color white
/set first random''')
        elif command[1] == 'challenge':
            self.send_message(user,
'''"challenge" command is used for different actions about challenging other users

formats:
/challenge offer {id}
/challenge cancel {id}
/challenge accept {id}
/challenge deny {id}

id is just id of another user - it\'s 9-digit number usually
use command "find" to get id of user
"/challenge offer {id}" is used to challenge other player
"/challenge cancel {id}" is used to cancel your challenge before is\'s accepted or denied
"/challenge accept {id}" is used to accept challenge of some player to challenge you
"/challenge deny {id}" is used to deny challenge of some player to challenge you

examples:
/challenge offer 505468618
/challenge cancel 505468618
/challenge accept 505468618
/challenge deny 505468618''')
        elif command[1] == 'surrender':
            self.send_message(user,
'''"surrender" command is used to surrender while fighting some other user

formats:
/surrender

example:
/surrender''')
        elif command[1] == 'field':
            self.send_message(user,
'''"field" command is used to do various actions with field while it\'s customised

formats:
/field create {type}
/field save {name}
/field delete
/field clear
/field list {whose}

"/field create {type}" is used to create new field you\'ll challenge other users at later
type can be: empty, basic
"/field save {name}" is used to save field you\'re currently customising with some name you choose so it can be loaded by anyone
name can be only one word lenght
"/field load {name}" is used to load field from database using it\'s name
"/field delete" is used to delete field you\'re currently customising
"/field clear" is used to clear field  you\'re currently customising
"/field list {whose} is used to know a list of saved castomised fields"
whose can be: my, all

examples:
/field create empty
/field save fukk
/field load fukk
/field delete
/field clear
/field list my''')
        elif command[1] == 'move':
            self.send_message(user,
'''"move" command is used to move figures while fighting

formats:
/move {start location} {finish location}

locations must be written in format of {col}{row} like e2, g5, h1

examples:
/move e2 e4''')
        elif command[1] == 'transform':
            self.send_message(user,
'''"transform" command is used to choose what figure to transform pawn into as it reaches end of the field

formats:
/transform {figure type}

figure type can be: Queen, King, Rook, Knight, Bishop, Pawn

examples:
/transform Rook''')
        elif command[1] == 'message':
            self.send_message(user,
'''"message" command is used to send messages to other players

formats:
/message {id} {text}

id is just id of another user - it\'s 9-digit number usually
use command "find" to get id of user
text can be anything

examples:
/message 505468618 fuk u
''')
        elif command[1] == 'top':
            self.send_message(user,
'''"top" command is used to know the rating of players

formats:
/top
/top n

"/top" will show all rating
"/top n" will show only first n places, n > 0

examples:
/top 3''')
        elif command[1] == 'find':
            self.send_message(user,
'''"find" command is used to know user id, it's important that user has already written to the bot and you must write the same name as it in VK

formats:
/top {name} {surname}

examles:
/find Павел Дуров''')
        else:
            self.send_message(user, 'such command doesn\'t exist')


    def process_commands(self, user, command):
        if len(command) == 1:
            self.send_message(user, '''list of all commands:
/field\n/put\n/remove\n/set\n/challenge
/surrender\n/move\n/transform\n/message\n/top\n/find\n/commands\n\n
use "/help {name of command}" for more info about command''')
        else:
            self.send_message(user, 'just type "/commands"')

    def process_command(self, user, command):
        if user not in self.players:
            self.players[user] = Player()
        con = sqlite3.connect('data.db')
        cur = con.cursor()
        users_ids = [x[0] for x in cur.execute("""SELECT user_id FROM top""")]
        if user not in users_ids:
            cur.execute("""INSERT INTO top(user_id, rating) VALUES(?, ?)""", (user, 0))
        con.commit()
        original = command
        command = command.split()
        if not command:
            self.send_message(user, 'type "/commands" for command list')
            return
        if command[0] == '/put':  # done
            self.process_put(user, command)
        elif command[0] == '/remove':
            self.process_remove(user, command)
        elif command[0] == '/set':  # done
            self.process_set(user, command)
        elif command[0] == '/challenge':  # done
            self.process_challenge(user, command)
        elif command[0] == '/surrender':
            self.process_surrender(user, command)
        elif command[0] == '/field':  # in process
            self.process_field(user, command)
        elif command[0] == '/move':  # done
            self.process_move(user, command)
        elif command[0] == '/transform':  # done
            self.process_transform(user, command)
        elif command[0] == '/message':  # done
            self.process_message(user, command, original)
        elif command[0] == '/top':
            self.process_top(user, command)
        elif command[0] == '/find':
            self.process_find(user, command)
        elif command[0] == '/help':  # last to be finished
            self.process_help(user, command)
        elif command[0] == '/commands': # done
            self.process_commands(user, command)
        else:
            self.send_message(user, 'type "/commands" for command list')


if __name__ == '__main__':
    beeg_boi = Bot()
    beeg_boi.start()
    beeg_boi.main_cycle()
