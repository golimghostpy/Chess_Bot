'''
методы распределены по уровню по уровню и у каждого справа в комментариях написан его уровень
уровень 0 - самые простые методы, которые в основном отвечают на вопрос "можно ли" или выполняют действие без каких-либо ограничений
уровень 1 - композиции методов уровней 0 и 1, не используются для обработки ввода, но реализуют соблюдение игровых правил
уровень 2 - методы высшего порядка, взаимодействуют с вводом
'''


class ChessField:  # класс шахматного поля
    def __init__(self):  # level 0
        self.end = False  # флаг, показывающий, поставлен ли мат
        self.step = 1  # self.step контролирует, чей сейчас ход
        self.acts = []  # массив действий игрока (нажатий на ячейки шахматного поля) за последний ход
        self.last_move = []  # массив, хранящий изменения поля за последний ход
        self.field = [[None] * 8 for _ in range(8)]  # шахматное поле хранится в матрице, где пустота означает None
        # self.figures - хранилище фигур, которые находятся в игре
        self.figures = {1: {Pawn: set(), Knight: set(), Rook: set(), King: set(), Bishop: set(), Queen: set()},
                        0: {Pawn: set(), Knight: set(), Rook: set(), King: set(), Bishop: set(), Queen: set()}}

    def made_in_heaven(self):  # функция, очищающая поле # level 1
        self.acts = []
        self.last_move = []
        self.field = [[None] * 8 for _ in range(8)]
        self.figures = {1: {Pawn: set(), Knight: set(), Rook: set(), King: set(), Bishop: set(), Queen: set()},
                        0: {Pawn: set(), Knight: set(), Rook: set(), King: set(), Bishop: set(), Queen: set()}}

    def build(self):  # функция создания шахматного поля на момент начала игры # level 1
        self.made_in_heaven()
        self.step = 1  # ходу белых соответствует значение self.step 1, а чёрных - 0
        for i in range(8):  # пешки
            Pawn(1, i, 1, self).put()
            Pawn(6, i, 0, self).put()
        Rook(0, 0, 1, self).put()  # ладьи
        Rook(0, 7, 1, self).put()
        Rook(7, 0, 0, self).put()
        Rook(7, 7, 0, self).put()
        Knight(0, 1, 1, self).put()  # кони
        Knight(0, 6, 1, self).put()
        Knight(7, 1, 0, self).put()
        Knight(7, 6, 0, self).put()
        Bishop(0, 2, 1, self).put()  # слоны
        Bishop(0, 5, 1, self).put()
        Bishop(7, 2, 0, self).put()
        Bishop(7, 5, 0, self).put()
        Queen(0, 3, 1, self).put()  # ферзи
        Queen(7, 3, 0, self).put()
        King(0, 4, 1, self).put()  # короли
        King(7, 4, 0, self).put()
        self.last_move.clear()
        self.acts.clear()
        self.end = False

    def another_one_bites_the_dust(self):  # откатывает ход игрока # level 1
        back = self.last_move[::-1]
        for act in back:
            if act[2] == (-1, -1):
                act[0].put()
            elif act[1] == (-1, -1):
                act[0].die()
            else:
                act[0].move(*act[1])
                act[0].moves -= 2
        self.last_move.clear()

    def change_step(self):  # смена цвета хода # level 0
        self.step = 1 - self.step

    def put_figure(self, figure, row, col, color):  # постановка фигуры на матричное поле # level 1
        if self.field[row][col]:
            self.field[row][col].die()
        figure(row, col, color, self).put()
        self.last_move.clear()

    def transform_check(self, color):  # проверка на наличие трансформируемых пешек # level 0
        for pawn in self.figures[color][Pawn]:
            if pawn.row == 7 * color:
                return pawn.row, pawn.col
        return False

    def check_check(self):  # проверка на шах, используется в конце хода игрока (ибо игрок не имеет права подставлять # level 1
        color = self.step  # короля под шах к концу своего хода)
        enemy = 1 - self.step
        king = self.figures[color][King].pop()
        self.figures[color][King].add(king)
        for figtype in self.figures[enemy].keys():
            for fig in self.figures[enemy][figtype]:
                if fig.attack_check(king.row, king.col):
                    self.another_one_bites_the_dust()  # откатывает ход игрока, если его король под шахом
                    return False
        return True

    def mat_check(self):  # проверка на мат # level 1 # проверка идёт уже во время вражеского хода
        color = self.step
        kr = 7 - self.step * 7
        if type(self.field[kr][4]) == King:  # проверки на случай, если от шаха можно уйти рокировкой
            if not self.field[kr][5] and not self.field[kr][6] and type(self.field[kr][7]) == Rook:
                if self.field[kr][7].moves == 0 and self.field[kr][4].moves == 0 \
                            and self.field[kr][7].color == self.field[kr][4].color:
                    self.field[kr][4].move(kr, 6)
                    self.field[kr][7].move(kr, 5)
                    if self.check_check():
                        self.another_one_bites_the_dust()
                        return True
            if type(self.field[kr][0]) == Rook and not self.field[kr][1] and not self.field[kr][2] and not \
            self.field[kr][3]:
                if self.field[kr][0].moves == 0 and self.field[kr][4].moves == 0 \
                            and self.field[kr][0].color == self.field[kr][4].color:
                    self.field[kr][4].move(kr, 1)
                    self.field[kr][0].move(kr, 2)
                    if self.check_check():
                        self.another_one_bites_the_dust()
                        return True
        for figtype in self.figures[color].keys():  # цикл, в котором проверятся, есть ли хоть один ход,
            for fig in self.figures[color][figtype]:  # не приводящий к шаху на своём короле
                for row in range(8):
                    for col in range(8):
                        fig.act_check(row, col)
                        if self.check_check():
                            self.another_one_bites_the_dust()
                            return True
        return False

    def castling_check(self):  # метод проверяет, могут ли последние действия игрока вести к рокировке # level 1
        if len(self.acts) == 0:  # и если да, то не даёт опустошить массив действий до самой рокировки
            return True
        if len(self.acts) == 1:
            r0, c0 = self.acts[0][0], self.acts[0][1]
            if type(self.field[r0][c0]) == King:
                if self.field[r0][c0].moves == 0:
                    return True
        if len(self.acts) == 2:
            r0, c0, r1, c1 = self.acts[0][0], self.acts[0][1], self.acts[1][0], self.acts[1][1]
            if r0 == r1 and c1 in (1, 6) and not self.field[r1][c1] and type(self.field[r0][c0]) == King and \
                    self.field[r0][c0].moves == 0:
                return True
        if len(self.acts) == 3:
            r0, c0, r1, c1, r2, c2 = self.acts[0][0], self.acts[0][1], self.acts[1][0], self.acts[1][1], self.acts[2][
                0], self.acts[2][1]
            if type(self.field[r2][c2]) == Rook:
                if r0 == r2 and (c2 - c0) * (c1 - c0) > 0 and self.field[r2][c2].moves == 0:
                    return True
        if len(self.acts) == 4:
            r0, c0, r1, c1 = self.acts[0][0], self.acts[0][1], self.acts[1][0], self.acts[1][1]
            r2, c2, r3, c3 = self.acts[2][0], self.acts[2][1], self.acts[3][0], self.acts[3][1]
            if self.field[r3][c3] or r3 + r2 != 2 * r1 or self.field[r0][c0].moves or self.field[r2][c2].moves:
                self.acts.clear()
                return True
            if c1 == 1 and self.field[r0][3]:
                self.acts.clear()
                return True
        return False

    def add_act(self, row, col):  # если была совершена пара нажатий, соответствующая правильному игровому ходу, поле # level 2
        if self.end:  # опустошает свой массив нажатий и выполняет ход
            return False
        if not self.acts and self.field[row][col]:
            if self.step == self.field[row][col].color:
                self.acts.append((row, col))
        elif self.acts:
            self.acts.append((row, col))
        if self.castling_check():  # а проверка на рокировку не даёт полю опустошить массив нажатий до того момента, когда
            return False  # игрок полностью ввёл рокировку (т.е совершил аж 4 нажатия вместо двух привычных)
        if len(self.acts) == 2:
            result = False
            r0, c0, r1, c1 = self.acts[0][0], self.acts[0][1], self.acts[1][0], self.acts[1][1]
            if self.field[r0][c0].act_check(r1, c1):
                self.change_step()
                result = True
            self.acts.clear()
            self.last_move.clear()
            if not self.mat_check():
                self.end = True
            return result
        elif len(self.acts) == 3:
            self.acts.clear()
            return False
        elif len(self.acts) == 4:  # а тут происходит выполнение рокировки
            r0, c0, r1, c1 = self.acts[0][0], self.acts[0][1], self.acts[1][0], self.acts[1][1]
            r2, c2, r3, c3 = self.acts[2][0], self.acts[2][1], self.acts[3][0], self.acts[3][1]
            self.field[r0][c0].move(r1, c1)
            self.field[r2][c2].move(r3, c3)
            self.acts.clear()
            if self.check_check():
                self.change_step()
                self.last_move.clear()
            if not self.mat_check():
                self.end = True
            return True
        return False

    def copy(self):  # функция копирования поля # level 2
        newbie = ChessField()
        newbie.step = self.step
        for color in (0, 1):  # переприсяга лл
            for figtype in self.figures[color].keys():
                for fig in self.figures[color][figtype]:
                    figtype(fig.row, fig.col, fig.color, newbie).put()
        newbie.last_move.clear()
        return newbie

    def rigged(self):  # функция проверки поля на допустимость(например: есть ли 2 короля) # level 2
        if (len(self.figures[0][King]), len(self.figures[1][King])) != (1, 1):
            return True
        for color in range(2):
            if not self.mat_check():
                return True
            if not self.check_check():
                return True
            if self.transform_check(color):
                return True
            self.change_step()
        return False

    def is_basic(self):  # проверка на то, является ли поле базовым
        newbie = ChessField()
        newbie.build()
        if newbie.step != self.step:
            return False
        for i in range(8):
            for j in range(8):
                if type(self.field[i][j]) != type(newbie.field[i][j]):
                    return False
                if self.field[i][j]:
                    if self.field[i][j].color != newbie.field[i][j].color:
                        return False
        return True


class Figure:  # суперкласс фигуры
    def __init__(self, row, col, color, gamefield):  # level 0
        self.moves = 0  # количество ходов фигуры (нужно для взятия на проходе, первого хода пешки, рокировки)
        self.col = col  # <--
        self.row = row  # <--  координаты фигуры
        self.color = color  # цвет фигуры
        self.gamefield = gamefield  # фигура знает, какому представителю класса ChessField принадлежит

    def put(self):  # фигура сама ставит себя на поле и добавляет себя в нужное множество фигур поля # level 0
        self.gamefield.field[self.row][self.col] = self
        self.gamefield.figures[self.color][type(self)].add(self)
        self.gamefield.last_move.append((self, (-1, -1), (self.row, self.col)))

    def die(self):  # фигура умирает: убирает себя с поля и из множества фигур поля # level 0
        self.gamefield.last_move.append((self, (self.row, self.col), (-1, -1)))
        self.gamefield.field[self.row][self.col] = None
        self.gamefield.figures[self.color][type(self)].remove(self)

    def move_check(self, row, col):  # проверка возможности хода (ход - перемещение фигуры на свободную клетку) # level 0
        return True  # (прописывается в подклассах)

    def attack_check(self, row,  # level 0
                     col):  # проверка возможности атаки (атака - перемещение фигуры на изначально занятую клетку)
        if self.gamefield.field[row][col].color == self.color:  # (прописывается в подклассах)
            return False
        return self.move_check(row, col)

    def act_check(self, row, col):  # проверка возможности действия (в случае возможности действия сразу его выполняет) # level 1
        if self.gamefield.field[row][col]:  # на случай действия-атаки
            if self.attack_check(row, col):
                self.gamefield.field[row][col].die()
                self.move(row, col)
                return self.gamefield.check_check()
        else:  # на случай действия-хода
            if self.move_check(row, col):
                self.move(row, col)
                return self.gamefield.check_check()
        return False

    def move(self, row, col):  # фигура двигается, удаляя себя из старого места и ставя в новое # level 0
        self.gamefield.last_move.append((self, (self.row, self.col), (row, col)))
        self.moves += 1
        self.gamefield.field[self.row][self.col] = None
        self.col = col
        self.row = row
        self.gamefield.field[self.row][self.col] = self

    def __str__(self):
        return repr(self)


class Pawn(Figure):  # класс пешки
    def transform(self, figure):  # превращение пешки # level 1
        self.die()
        figure(self.row, self.col, self.color, self.gamefield).put()

    def move_check(self, row, col):
        r0, c0, r1, c1 = self.row, self.col, row, col
        if self.color == 1:
            if (r1 - r0, c1 - c0) == (2, 0) and self.moves == 0:
                return True
            elif (r1 - r0, c1 - c0) == (1, 0):
                return True
            elif (r1 - r0, abs(c1 - c0)) == (1, 1):  # взятие на проходе
                if type(self.gamefield.field[self.row][c1]) == Pawn and self.gamefield.field[self.row][
                    c1].moves == 1 and self.row == 4:
                    self.gamefield.field[self.row][c1].die()
                    return True
        if self.color == 0:
            if (r1 - r0, c1 - c0) == (-2, 0) and self.moves == 0:
                return True
            elif (r1 - r0, c1 - c0) == (-1, 0):
                return True
            elif (r1 - r0, abs(c1 - c0)) == (-1, 1):  # взятие на проходе
                if type(self.gamefield.field[self.row][c1]) == Pawn and self.gamefield.field[self.row][
                    c1].moves == 1 and self.row == 3:
                    self.gamefield.field[self.row][c1].die()
                    return True
        return False

    def attack_check(self, row, col):
        if self.gamefield.field[row][col].color == self.color:
            return False
        r0, c0, r1, c1 = self.row, self.col, row, col
        if self.color == 1:
            if (r1 - r0, abs(c1 - c0)) != (1, 1):
                return False
        if self.color == 0:
            if (r1 - r0, abs(c1 - c0)) != (-1, 1):
                return False
        return True

    def __repr__(self):
        return f'Pawn{self.color}'

    def copy(self):
        return Pawn(self.row, self.col, self.color, self.gamefield)


class Knight(Figure):  # класс коня
    def move_check(self, row, col):
        r0, c0, r1, c1 = self.row, self.col, row, col
        if {abs(r0 - r1), abs(c0 - c1)} != {1, 2}:
            return False
        return True

    def __repr__(self):
        return f'Knight{self.color}'

    def copy(self):
        return Knight(self.row, self.col, self.color, self.gamefield)


class King(Figure):  # класс короля
    def move_check(self, row, col):
        r0, c0, r1, c1 = self.row, self.col, row, col
        if {0, abs(r0 - r1), abs(c0 - c1)} != {0, 1}:
            return False
        return True

    def __repr__(self):
        return f'King{self.color}'

    def copy(self):
        return King(self.row, self.col, self.color, self.gamefield)


class Rook(Figure):  # класс ладьи
    def move_check(self, row, col):
        r0, c0, r1, c1 = self.row, self.col, row, col
        if r0 > r1:
            r1, r0 = r0, r1
        if c0 > c1:
            c1, c0 = c0, c1
        f1 = int(r0 == r1)
        f2 = int(c0 == c1)
        if f1 + f2 != 1:
            return False
        for r in range(r0 + 1, r1):
            if self.gamefield.field[r][self.col]:
                return False
        for c in range(c0 + 1, c1):
            if self.gamefield.field[self.row][c]:
                return False
        return True

    def __repr__(self):
        return f'Rook{self.color}'

    def copy(self):
        return Rook(self.row, self.col, self.color, self.gamefield)


class Bishop(Figure):  # класс слона
    def move_check(self, row, col):
        r0, c0, r1, c1 = self.row, self.col, row, col
        if abs(c1 - c0) != abs(r1 - r0):
            return False
        stcl, strw = abs(c1 - c0) // (c1 - c0), abs(r1 - r0) // (r1 - r0)
        for i in range(1, abs(c1 - c0)):
            if self.gamefield.field[r0 + strw * i][c0 + stcl * i]:
                return False
        return True

    def __repr__(self):
        return f'Bishop{self.color}'

    def copy(self):
        return Bishop(self.row, self.col, self.color, self.gamefield)


class Queen(Bishop, Rook):  # класс ферзя
    def move_check(self, row, col):
        return Rook.move_check(self, row, col) or Bishop.move_check(self, row, col)

    def __repr__(self):
        return f'Queen{self.color}'

    def copy(self):
        return Queen(self.row, self.col, self.color, self.gamefield)


figure_classes = {
    Knight: 'Knight', 'Knight': Knight,
    Rook: 'Rook', 'Rook': Rook,
    Bishop: 'Bishop', 'Bishop': Bishop,
    Queen: 'Queen', 'Queen': Queen,
    King: 'King', 'King': King,
    Pawn: 'Pawn', 'Pawn': Pawn
}

colors = {'black': 0, 'white': 1, '0': 0, '1': 1}
