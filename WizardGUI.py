from PyQt6 import QtCore,QtWidgets,QtGui
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import sys
import numpy as np

class MplCanvas(FigureCanvasQTAgg):

    def __init__(self,parents=None, width=5, height=4,title=None,xlabel=None,ylabel=None):
        self.fig = Figure(figsize=(width,height))
        self.axes = self.fig.add_subplot(111)
        self.axes.set_xlabel(xlabel)
        self.axes.set_ylabel(ylabel)
        self.axes.set_title(title)
        super(MplCanvas,self).__init__(self.fig)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self,*args,**kwargs):
        super(MainWindow,self).__init__(*args,**kwargs)
        self.setWindowTitle("Wizard GUI")

        self.list_labels_player_names = []
        self.list_lineedits_said = []
        self.list_lineedits_achieved = []

        self.wdg_topLevel = QtWidgets.QWidget()
        self.hauptlayout = QtWidgets.QGridLayout()

        self.wdg_settings = QtWidgets.QWidget()
        self.layout_settings = QtWidgets.QGridLayout()
        self.label_names_players = QtWidgets.QLabel("Namen der Spieler: ")
        self.lineedit_names_players = QtWidgets.QLineEdit()
        self.lineedit_names_players.textEdited.connect(self.playerNamesChanged)

        self.layout_settings.addWidget(self.label_names_players, 0, 0, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.layout_settings.addWidget(self.lineedit_names_players, 0, 1, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.wdg_settings.setLayout(self.layout_settings)

        self.wdg_standings = QtWidgets.QWidget()
        self.layout_standings = QtWidgets.QGridLayout()
        self.label_players = QtWidgets.QLabel("Spieler")
        self.label_said = QtWidgets.QLabel("Angesagt")
        self.label_achieved = QtWidgets.QLabel("Gemacht")

        self.layout_standings.addWidget(self.label_players, 0, 0, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.layout_standings.addWidget(self.label_said, 0, 1, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.layout_standings.addWidget(self.label_achieved, 0, 2, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.wdg_standings.setLayout(self.layout_standings)

        self.button_round_done = QtWidgets.QPushButton("Runde beendet", self, clicked=self.roundDone)


        self.plot = MplCanvas(self)

        self.hauptlayout.addWidget(self.wdg_settings, 0, 0)
        self.hauptlayout.addWidget(self.wdg_standings, 1,0)
        self.hauptlayout.addWidget(self.plot, 0, 1, 2, 1)
        self.hauptlayout.setColumnStretch(1, 30)
        self.wdg_topLevel.setLayout(self.hauptlayout)
        self.setCentralWidget(self.wdg_topLevel)
        self.showMaximized()
    

    def playerNamesChanged(self):
        self.list_player_names = self.lineedit_names_players.text().replace(" ", "").split(",")
        for i in range(0, len(self.list_labels_player_names)):
            self.layout_standings.removeWidget(self.list_labels_player_names[i])
            self.layout_standings.removeWidget(self.list_lineedits_said[i])
            self.layout_standings.removeWidget(self.list_lineedits_achieved[i])
        try:
            self.layout_standings.removeWidget(self.button_round_done)
        except:
            pass

        self.list_arrs = [[0] for player in self.list_player_names]
        self.list_rounds = [0]
        self.list_avgs = []

        self.list_labels_player_names = []
        self.list_lineedits_said = []
        self.list_lineedits_achieved = []
        
        for name in self.list_player_names:
            self.list_labels_player_names.append(QtWidgets.QLabel(name))
            self.list_lineedits_said.append(QtWidgets.QLineEdit())
            self.list_lineedits_achieved.append(QtWidgets.QLineEdit())
        for i in range(0,len(self.list_player_names)):
            self.layout_standings.addWidget(self.list_labels_player_names[i], i+1 , 0, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
            self.layout_standings.addWidget(self.list_lineedits_said[i], i+1 , 1, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
            self.layout_standings.addWidget(self.list_lineedits_achieved[i], i+1 , 2, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.layout_standings.addWidget(self.button_round_done, len(self.list_player_names)+1, 0, 1, 3)


    def roundDone(self):

        self.list_avgs = []
        self.plot.axes.clear()
        self.list_rounds.append(self.list_rounds[-1] + 1)
        for i in range(len(self.list_player_names)):
            said = int(self.list_lineedits_said[i].text())
            achieved = int(self.list_lineedits_achieved[i].text())
            if said == achieved:
                self.list_arrs[i].append(self.list_arrs[i][-1] + 20 + said*10)
            else:
                self.list_arrs[i].append(self.list_arrs[i][-1] - 10*np.abs(said-achieved))
        
        for round in range(len(self.list_arrs[0])):
            sum_val = 0
            for arr in self.list_arrs:
                sum_val += arr[round]
            self.list_avgs.append(sum_val/len(self.list_arrs))
        
        for i_arr, arr in enumerate(self.list_arrs):
            self.plot.axes.plot(self.list_rounds, arr, marker="o", label=self.list_player_names[i_arr])
            max_i = np.argmax(arr)
            self.plot.axes.plot(self.list_rounds[max_i], arr[max_i], marker='d', color='black', markersize=10)
        self.plot.axes.plot(self.list_rounds, self.list_avgs, color="grey", label="Durchschnitt", linestyle="--")
        self.plot.fig.legend(fontsize=28, loc="upper left")
        self.plot.fig.tight_layout()
        self.plot.axes.axhline(0,0,1, linestyle="--", color="black")
        self.plot.draw()

        

        






app = QtWidgets.QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()