from pathlib import Path
from astropy.io import ascii
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import QMainWindow, QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit, QMainWindow, QPushButton, QTextEdit, QGroupBox

"""
Preferences Window
"""
class CommentWindow(QMainWindow):
    def __init__(self, parent=None):
        super(CommentWindow, self).__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.cm = Comment(self)
        self.setCentralWidget(self.cm)



class Comment(QWidget):
    def __init__(self, parent=None):
        super(Comment, self).__init__(parent)
        self.starname, self.obsnight, self.ob_id = '', '', None
        self.initUI()

    @pyqtSlot()
    def on_click_ok(self):
        filename = str(Path.home()) + '/.config/spherequery/comments.csv'
        comment = self.commentBox.toPlainText().replace('\n', ' ').replace(';', ',')
        if Path(filename).exists():
            data = ascii.read(filename, data_start = 1, delimiter = ';')
            mask = (data['starname'] == self.starname) & (data['obsnight'] == self.obsnight) & (data['ob_id'] == self.ob_id)
            if len(data[mask]) != 0:
                ind = mask.nonzero()[0][0]
                data.remove_row(ind)
            data.add_row([self.starname, self.obsnight, self.ob_id, comment])
            ascii.write(data, filename, format='csv', delimiter=';', overwrite = True)
        else:
            f = open(filename, 'w')
            f.write('starname;obsnight;ob_id;comment\n')
            f.write('{};{};{};{}\n'.format(self.starname, self.obsnight, self.ob_id, \
                    self.commentBox.toPlainText().replace('\n',' ')))
            f.close()
        self.parent().close()
        self.parent().parent()._read_comments(update = True) # reload the config file after closing

    @pyqtSlot()
    def on_click_c(self):
        self.parent().close()

    def initUI(self):
        """
        The main window

        First get the variables that were saved
        """
        # need to get the starname, obsnight, and ob_id for uniqueness
        """
        Text box
        """
        self.commentBox = QTextEdit()
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
        groupBox = QGroupBox('Comments:')
        upper = QHBoxLayout()
        upper.addWidget(self.commentBox)
        groupBox.setLayout(upper)
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


