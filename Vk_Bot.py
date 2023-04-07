import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from random import randint
from Chess_Classes import *
from PIL import Image
import sqlite3

TOKEN = 'vk1.a.qOQPyAdJ_Z5WwjzbNl_WFUq2P05QGpwj-537I7vwLTneH1Fz06BBEslq0_rbUGJFabRakR9V-pL7dzhhx6qCeHA-AP2wNndJTFHYQ7sKmPyiAB05KWIkfmH4G_Gl9luw3qqe8UvwB6tTTaojNW1EcIHjgP8uX5Z89ppE5Mv2cpaWrEmrWtD9b9GC1ulJ_viLiTwOfjTcBd4mqifQqazVZw'
GROUP_ID = 219645807

'''
commands:
done:
/set (color, start) (white, black, random)
/put {figure class} {location} (white, black)
in process:
/challenge (offer, cancel, accept, deny) {id}
undone:
/move {location_A} {location_B} OR specials: /move castling (right, left)
/field (create, delete, show, save (enter name in that case))
/message {id} {message}
/commands
/help {command}
'''


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
    img.paste(Image.open('data/num_col.png'), (0, 0))
    img.paste(Image.open('data/let_row.png'), (40, 640))
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
        for event in self.long_poll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                self.process_command(event.object.message["from_id"], event.object.message["text"])
                print(f'sender: {event.object.message["from_id"]}')
                print(f'text: {event.object.message["text"]}')
                print('--------------------------------------------')

    def end_check(self, user):
        if self.players[user].game_field.end:
            self.send_message(user, 'you\'ve won, game is finished')
            self.send_message(self.players[user].enemy, 'you\'ve lost, game is finished')
            self.players[user].condition = NO_ENEMY
            self.players[self.players[user].enemy].condition = NO_ENEMY
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
            self.send_message(user, 'figure put successfully')
        except Exception:
            self.send_message(user, 'wrong command arguments\ntype "/help put" for more information')

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
                self.send_message(int(command[2]),
                                  f'you have been challenged by {user}\ntype "/challenge accept {user}" to accept challenge\nelse type "/challenge deny {user}"')
                self.send_message(user, 'waiting for player reply...')
                self.players[user].condition = WAITING_FOR_ACCEPT
                self.players[user].enemy = int(command[2])
                self.players[int(command[2])].waiting.add(user)
            except vk_api.exceptions.ApiError or AttributeError:
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

    def process_field(self, user, command):
        if len(command) == 2:
            if command[1] == 'show':
                if self.players[user].condition == NO_ENEMY and self.players[user].edit_field:
                    build_field_img(self.players[user].edit_field.field, self.players[user].color)
                elif self.players[user].condition != NO_ENEMY:
                    build_field_img(self.players[user].game_field.field, self.players[user].color)
                else:
                    self.send_message(user, 'no field to show')
                    return
                vk = self.session.get_api()
                upload = vk_api.VkUpload(vk)
                vk_image = upload.photo_messages('data/field.png')
                owner_id = vk_image[0]['owner_id']
                photo_id = vk_image[0]['id']
                access_key = vk_image[0]['access_key']
                attachment = f'photo{owner_id}_{photo_id}_{access_key}'
                vk.messages.send(user_id=user, peer_id=user, random_id=0, attachment=attachment)
                return
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
                    con = sqlite3.connect('custom_fields.db')
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
                        self.send_message(user, 'field created successfully\n"/field save" to save your field')
                    elif command[2] == 'basic':
                        self.players[user].edit_field = ChessField()
                        self.players[user].edit_field.build()
                        self.send_message(user, 'field created successfully\n"/field save" to save your field')
                    else:
                        self.send_message(user, 'wrong command arguments\ntype "/help field" for more information')
            elif command[1] == 'load':
                try:
                    con = sqlite3.connect('custom_fields.db')
                    cur = con.cursor()
                    field = [x[0] for x in cur.execute("""SELECT field FROM data WHERE title = ?""", (command[2],))][0]
                    self.players[user].edit_field = str_to_field(field)
                    self.send_message(user, 'field loaded successfully')
                except Exception:
                    self.send_message(user, 'field with this name doesn\'t exist')
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
                    self.send_message(user,
                                      'choose what figure to transform your pawn into with "/transform {figure_class}"')
                    return
                if self.end_check(user):
                    return
                self.send_message(user, 'move done successfully')
                self.send_message(self.players[user].enemy, 'enemy move has been done')
            else:
                self.send_message(user, 'this move can\'t be done')
        elif command[1] == 'castling':
            row = 7 * (1 - self.players[user].color)
            if type(self.players[user].game_field.field[row][4]) != King:
                self.send_message(user, 'castling can\'t be done')
                return
            if command[2] == 'left':
                for col in (4, 1, 0):
                    self.players[user].game_field.add_act(row, col)
                if len(self.players[user].game_field.acts) != 3:
                    self.send_message(user, 'castling can\'t be done')
                    self.players[user].game_field.acts.clear()
                    return
                if self.players[user].game_field.add_act(row, 2):
                    self.send_message(user, 'castling done successfully')
            elif command[2] == 'right':
                for col in (4, 6, 7):
                    self.players[user].game_field.add_act(row, col)
                if len(self.players[user].game_field.acts) != 3:
                    self.send_message(user, 'castling can\'t be done')
                    self.players[user].game_field.acts.clear()
                    return
                if self.players[user].game_field.add_act(row, 5):
                    self.send_message(user, 'castling done successfully')
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
            self.send_message(user, 'figure changed successfully')
            self.send_message(self.players[user].enemy, 'enemy move has been done')
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

    def process_help(self, user, command):
        self.send_message(user, 'nothing here so far')

    def process_commands(self, user, command):
        self.send_message(user, 'nothing here so far')

    def process_command(self, user, command):
        if user not in self.players:
            self.players[user] = Player()
        original = command
        command = command.split()
        if command[0] == '/put':  # done
            self.process_put(user, command)
        elif command[0] == '/set':  # done
            self.process_set(user, command)
        elif command[0] == '/challenge':  # done
            self.process_challenge(user, command)
        elif command[0] == '/field':  # in process
            self.process_field(user, command)
        elif command[0] == '/move':  # done
            self.process_move(user, command)
        elif command[0] == '/transform':  # done
            self.process_transform(user, command)
        elif command[0] == '/message':  # done
            self.process_message(user, command, original)
        elif command[0] == '/help':  # last to be finished
            self.process_help(user, command)
        elif command[0] == '/commands':  # last to be finished
            self.process_commands(user, command)
        else:
            self.send_message(user, 'type "/commands" for command list')


if __name__ == '__main__':
    beeg_boi = Bot()
    beeg_boi.start()
    beeg_boi.main_cycle()
