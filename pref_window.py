import configparser
from pathlib import Path
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import QMainWindow, QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit, QMainWindow, QGroupBox, QPushButton, QFileDialog, QGridLayout, QCheckBox, QButtonGroup

"""
Preferences Window
"""
class PrefWindow(QMainWindow):
    def __init__(self, parent=None):
        super(PrefWindow, self).__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.pr = Pref(self)
        self.setCentralWidget(self.pr)





class Pref(QWidget):
    def __init__(self, parent=None):
        super(Pref, self).__init__(parent)
        self.initUI()

    @pyqtSlot()
    def on_click_ok(self):
        filename = str(Path.home()) + '/.config/spherequery/spherequery.conf'
        output = configparser.ConfigParser()
        output.optionxform = str
        output.read(filename)
        """
        Add the login info, the structure should already be there
        so no need to check if the sections are there or not.
        """
        output['ESO']['login'] = self.ulogin.text()
        output['ESO']['password'] = self.upassword.text()
        output['DATA']['path'] = self.datapath

        with open(filename,'w') as file_object:
            output.write(file_object)
        self.parent().close()
        self.parent().parent()._read_config() # reload the config file after closing

    @pyqtSlot()
    def on_click_c(self):
        self.parent().close()

    def _get_dir(self):
        home_dir = str(Path.home())
        self.datapath = str(QFileDialog.getExistingDirectory(self, 'Select directory', home_dir))
        self.show_path.setText(self.datapath)

    def initUI(self):
        """
        The main window

        First get the variables that were saved
        """
        username = self.parent().parent().user
        password = self.parent().parent().password
        self.datapath = self.parent().parent().dpath
        """
        ESO log-in and password
        """
        ul = QLabel('Login:', self)
        self.ulogin = QLineEdit(username, self)
        if username is None:
            self.ulogin.setPlaceholderText("ESO login")
        up = QLabel('Password:', self)
        self.upassword = QLineEdit(password, self)
        if password is None:
            self.upassword.setPlaceholderText("ESO password")
        self.upassword.setEchoMode(QLineEdit.Password)
        self.upassword.returnPressed.connect(self.on_click_ok)
        """
        Data directory 
        """
        pathbut = QPushButton('Choose path')
        pathbut.clicked.connect(self._get_dir)
        self.show_path = QLineEdit(self.datapath, self)
        self.show_path.setReadOnly(True)
        """
        Ok and cancel buttons
        """
        okbut = QPushButton('Ok')
        okbut.clicked.connect(self.on_click_ok)
        cbut = QPushButton('Cancel')
        cbut.clicked.connect(self.on_click_c)
        """
        Define the layout
        """
        main = QVBoxLayout()
        grid = QVBoxLayout()
        """
        User info box
        """
        groupBox = QGroupBox('User information:')
        vbox = QVBoxLayout()
        upper = QHBoxLayout()
        upper.addWidget(ul)
        upper.addWidget(self.ulogin)
        lower = QHBoxLayout()
        lower.addWidget(up)
        lower.addWidget(self.upassword)

        vbox.addLayout(upper)
        vbox.addLayout(lower)
        vbox.addStretch()
        groupBox.setLayout(vbox)
        grid.addWidget(groupBox)
        """
        Data stuff
        """
        groupBox = QGroupBox('Directory for the data:')
        pd = QHBoxLayout()
        pd.addWidget(self.show_path)
        pd.addWidget(pathbut)
        # pd.addStretch()
        groupBox.setLayout(pd)
        grid.addWidget(groupBox)
        """
        Add the buttons
        """
        buts = QHBoxLayout()
        buts.addStretch()
        buts.addWidget(okbut, alignment = Qt.AlignRight)
        buts.addWidget(cbut, alignment = Qt.AlignRight)

        main.addLayout(grid)
        main.addLayout(buts)
        self.setLayout(main)

