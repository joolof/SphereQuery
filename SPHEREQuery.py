import os
import sys
import glob
import requests
import subprocess
import configparser
from pathlib import Path
from astropy import log
from astropy.io import ascii
from dl_window import DlWindow
from cm_window import CommentWindow
from log_window import LogWindow
from pref_window import PrefWindow
from astroquery.simbad import Simbad
from do_query import DoQuery, DataDownloader
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QThread
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QGroupBox, QPushButton, QComboBox, QTableWidget, QAbstractScrollArea, QAbstractItemView, QTableWidgetItem, QScrollArea, QProgressBar, QRadioButton, QButtonGroup, QMessageBox
from PyQt5.QtGui import QFont
# ------------------------------------------------------------
cds_url = 'http://cdsweb.u-strasbg.fr/cgi-bin/nph-sesame/-oI/?'
log.setLevel('ERROR')
# ------------------------------------------------------------
"""
Main window
"""
class MainQuery(QMainWindow):
    def __init__(self, parent=None):
        super(MainQuery, self).__init__(parent)
        self.setStyleSheet(open(os.path.dirname(os.path.realpath(sys.argv[0]))+"/style.qss", "r").read())
        """
        Add the geometry
        """
        screen = QApplication.primaryScreen()
        rect = screen.availableGeometry()
        width, height = int(rect.width()*2./3), int(rect.height()*2./3.)
        xpos = int(rect.width()/2.-width/2)
        ypos = int(rect.height()/2.-height/2)
        self.setGeometry(xpos,ypos, width, height)
        self.setWindowTitle("SPHEREQuery")
        """
        A menu bar
        """
        self.MenuBar = self.menuBar()
        """
        Add the status bar
        """
        self.status = self.statusBar()

        self.query_window = QueryWindow(self)
        self.setCentralWidget(self.query_window)
        self.show()

class QueryWindow(QWidget):
    def __init__(self,parent=None):
        super(QueryWindow, self).__init__(parent)
        self.doquery = DoQuery()
        self.datadownloader = DataDownloader()
        self.make_connection()
        self.initUI()

    @pyqtSlot(str)
    def set_status(self, val):
        self.parent().status.showMessage(val)
        QApplication.processEvents()

    @pyqtSlot(str)
    def set_log(self, val):
        self.logwindow.lt.logframe.append(val)
        QApplication.processEvents()

    def make_connection(self):
        self.doquery.changedStatus.connect(self.set_status)
        self.doquery.changedLog.connect(self.set_log)
        self.datadownloader.changedStatus.connect(self.set_status)
        self.datadownloader.changedLog.connect(self.set_log)

    def initUI(self):
        """
        The main window
        """
        self.warning = QMessageBox()
        self.warning.setWindowTitle('Warning')
        self.font = QFont()
        self.font.setPointSize(8)
        self.logwindow = LogWindow(self)
        self.cmwindow = CommentWindow(self)
        self._create_config()
        self._read_config()
        self._read_comments()
        self.pref = PrefWindow(self)
        self.dlwindow = DlWindow(self)
        window = QVBoxLayout()
        window.addLayout(self._create_topbar())
        window.addLayout(self._create_main_panel())
        window.addLayout(self._create_progressbar())
        self.setLayout(window)
        self._create_table()
        self._qmoved = False
        self._dmoved = False

    def _read_comments(self, update = False):
        filename = str(Path.home()) + '/.config/spherequery/comments.csv'
        self.comments = ascii.read(filename, data_start = 1, delimiter = ';')
        if update:
            self._update_table(self.results)

        
    def _create_progressbar(self):
        """
        Progressbar
        """
        bot_bar = QHBoxLayout()
        self.pbar = QProgressBar(self)
        self.pbar.setVisible(False)
        # self.pbar.setValue(20)
        bot_bar.addWidget(self.pbar)
        return bot_bar

    def _create_topbar(self):
        starlabel = QLabel('Star name:', self)
        # self.star= QLineEdit('HD129590', self)
        self.star= QLineEdit(self)
        self.star.setPlaceholderText("Search")
        # self.star.setFixedWidth(200)
        self.star.returnPressed.connect(self.query_star)

        pidlabel = QLabel('Prog. ID:', self)
        self.progid = QLineEdit(self)
        self.progid.returnPressed.connect(self.query_star)

        techlabel = QLabel('DPR Tech:', self)
        self.dprtech = QComboBox()
        self.dprtech.addItems(['Any', 'IFU', 'IMAGE, CORONOGRAPHY',\
                'POLARIMETRY,CORONOGRAPHY', 'SPECTRUM', 'SPECTRUM,CORONOGRAPHY'])
		
        filtlabel = QLabel('COMB IFLT:', self)
        self.insfilt = QComboBox()
        self.insfilt.addItems(['Any', 'DB_Y23', 'DB_J23', 'DB_H23', 'DB_K12', 'BB_Y', 'BB_J', 'BB_H',\
                'BB_Ks', 'DP_0_BB_Y', 'DP_0_BB_J', 'DP_0_BB_H', 'DP_0_BB_Ks'])

        drotlabel = QLabel('DROT2 MODE:', self)
        self.drot = QComboBox()
        self.drot.addItems(['Any', 'ELEV', 'SKY'])
		
        startlabel = QLabel('Start date:', self)
        self.startdate = QLineEdit(self)
        self.startdate.setPlaceholderText("YYYY-MM-DD")
        
        endlabel = QLabel('End date:', self)
        self.enddate = QLineEdit(self)
        self.enddate.setPlaceholderText("YYYY-MM-DD")
        self.enddate.returnPressed.connect(self.query_star)
        
        self.searchbut= QPushButton('Ok')
        self.searchbut.clicked.connect(self.query_star)
        self.searchbut.setDefault(True);
        self.searchbut.setAutoDefault(False);
        self.dlbut= QPushButton('Download')
        self.dlbut.clicked.connect(self._prep_dl)
        self.dlbut.setEnabled(False)
        self.logbut= QPushButton('Log')
        self.logbut.clicked.connect(self.displayLog)
        self.prefbut= QPushButton('Preferences')
        self.prefbut.clicked.connect(self.displayPref)

        upper = QHBoxLayout()
        upper.addWidget(starlabel)
        upper.addWidget(self.star)
        upper.addWidget(pidlabel)
        upper.addWidget(self.progid)
        upper.addWidget(techlabel)
        upper.addWidget(self.dprtech)
        upper.addWidget(self.prefbut)
        upper.addWidget(self.logbut)

        lower = QHBoxLayout()
        lower.addWidget(filtlabel)
        lower.addWidget(self.insfilt)
        lower.addWidget(drotlabel)
        lower.addWidget(self.drot)
        lower.addWidget(startlabel)
        lower.addWidget(self.startdate)
        lower.addWidget(endlabel)
        lower.addWidget(self.enddate)
        lower.addWidget(self.searchbut)
        lower.addWidget(self.dlbut)

        bar = QVBoxLayout()
        bar.addLayout(upper)
        bar.addLayout(lower)
        return bar

    def displayPref(self):
        self.pref.show()

    def displayLog(self):
        self.logwindow.show()

    def _prep_dl(self):
        """
        Method to download the data. There should be a
        popup window with some additional options.

        I need to pass the list of urls to that window
        """
        if not Path(self.dpath).exists():
            self.warning.setText('The directory cannot be found')
            self.warning.exec_()
        else:
            if self.obstable.currentRow() != -1:
                self.dlwindow.show()

    def _start_download(self, selector):
        """
        Will be called from the DlWindow
        """
        self.pbar.setVisible(True)
        row = self.obstable.currentRow()
        index = int(self.obstable.item(row,0).text())
        starname = str(self.obstable.item(row,self.cols['mainID']).text())

        self.datadownloader.obsnight = self.results[index]['obsnight'].split('\n')[0]
        self.datadownloader.ob_id = self.results[index]['OB ID']

        self.datadownloader.user = self.user
        self.datadownloader.password = self.password
        self.datadownloader.dpath = self.dpath
        self.datadownloader.starname = str(self.obstable.item(row,self.cols['mainID']).text())
        self.datadownloader.dp_id = self.results[index]['DP.ID'].split('\n')
        self.datadownloader.selector = selector

        thread = QThread(parent = self) # To avoid the UI to freeze during the query
        if not self._dmoved:
            self.datadownloader.moveToThread(thread)
            self._dmoved = True # To avoid having to move the thread again for the 2nd query
        thread.started.connect(self.datadownloader._get_data)
        thread.start()

        self.star.setEnabled(False)
        self.searchbut.setEnabled(False)
        self.obstable.setEnabled(False)
        self.dlbut.setEnabled(False)
        self.datadownloader.progress.connect(self._update_pbar)
        self.datadownloader.finished.connect(thread.quit)
        self.datadownloader.finished.connect(lambda: self.searchbut.setEnabled(True))
        self.datadownloader.finished.connect(lambda: self.dlbut.setEnabled(True))
        self.datadownloader.finished.connect(lambda: self.star.setEnabled(True))
        self.datadownloader.finished.connect(lambda: self.pbar.setVisible(False))
        self.datadownloader.finished.connect(lambda: self.pbar.setValue(0))
        self.datadownloader.finished.connect(lambda: self.obstable.setEnabled(True))
        self.datadownloader.finished.connect(lambda: self._update_table(self.results))
        self.datadownloader.finished.connect(lambda: self._cp_template_DR())

    def _cp_template_DR(self):
        """
        Copy the template for the data reduction
        """
        row = self.obstable.currentRow()
        starname = str(self.obstable.item(row,self.cols['mainID']).text())
        obsnight = str(self.obstable.item(row,self.cols['obsnight']).text())
        ob_id = str(self.obstable.item(row,self.cols['ob_id']).text())
        dptech = str(self.obstable.item(row,self.cols['dptech']).text())
        if 'POLARIMETRY' not in dptech:
            dirname = '{}/{}/{}/{}/'.format(self.dpath, starname, obsnight, ob_id)
            args = ['cp','{}/data_reduction.py'.format(str(Path(__file__).parent.resolve())), dirname]
            tmp = subprocess.Popen(args).wait()

    def _update_pbar(self, value):
        self.pbar.setValue(value)

    def _create_main_panel(self):
        """
        Main panel
        """
        self.obstable = ObsTable()
        main_panel = QHBoxLayout()
        main_panel.addWidget(self.obstable)
        return main_panel

    def _create_config(self):
        """
        Create the config file directory
        """
        filename = str(Path.home()) + '/.config/spherequery/spherequery.conf'
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        if not Path(filename).is_file():
            output = configparser.ConfigParser()
            output.read(filename)
            output.optionxform = str
            output['ESO']={
                'login': ' ',
                'password': ' '
            }
            output['DATA']={
                'path': '{}'.format(str(Path.home()))
            }
            with open(filename,'w') as file_object:
                output.write(file_object)
        self.set_status('Checking for config file: {}'.format(filename))

    def _read_config(self):
        """
        Read the config file
        """
        self.pref_insts = []
        filename = str(Path.home()) + '/.config/spherequery/spherequery.conf'
        output = configparser.ConfigParser()
        output.optionxform = str
        output.read(filename)
        if output.has_section('ESO'):
            self.user = output['ESO']['login']
            self.password = output['ESO']['password']
        else:
            self.user, self.password = None, None
        if output.has_section('DATA'):
            self.dpath = output['DATA']['path']
        else:
            self.dpath = str(Path.home())
        """
        Display some info in the log
        """
        if self.user is not None and self.user != '':
            self.set_log('User name is: {}'.format(self.user))
        if self.password is not None and self.password != '':
            self.set_log('Password is set, but not shown here.')
        if self.dpath is not None and self.dpath != '':
            self.set_log('Data will be saved in: {}'.format(self.dpath))
        """
        Check if the path exists
        """
        if not Path(self.dpath).exists():
            self.warning.setText('The directory cannot be found')
            self.warning.exec_()

    def _resolve_name(self, starname):
        """
        Query the cds to get the right ascension
        and declination
        """
        """
        TO DO: keep a file with the objects already
        resolved to speed things up a bit.
        """
        if starname == '':
            return ''
        filename = str(Path.home()) + '/.config/spherequery/resolved_names.csv'
        if Path(filename).exists():
            data = ascii.read(filename, data_start=1)
            ori = data['Original']
            mainid = data['MainID']
            if starname in ori:
                return mainid[(ori == starname)][0]
        else:
            f = open(filename, 'w')
            f.write('Original,MainID\n')
            f.close()

        tempname = Simbad.query_object(self._reformat_starname(starname))
        if tempname is None:
            tempname = starname.replace(' ', '_')
        else:
            tempname = tempname['MAIN_ID'][0]
            tempname = tempname.replace('V* ', 'V ')
            tempname = tempname.replace('EM* ', 'EM ')
            tempname = tempname.replace('* ', '')
            tempname = tempname.replace('  ', '_')
            tempname = tempname.replace(' ','_')

        f = open(filename, 'a')
        f.write('{},{}\n'.format(starname, tempname))
        f.close()
        return tempname

    def _reformat_starname(self, starname):
        starname = starname.replace('V ', 'V* ')
        starname = starname.replace('EM ', 'EM* ')
        return starname

    def query_star(self):
        """
        Search the ESO archive for the selected star and instrument
        """
        self.doquery.starname = self.star.text()
        self.doquery.progid = self.progid.text()
        self.doquery.dprtech = self.dprtech.currentText()
        self.doquery.insfilt = self.insfilt.currentText()
        self.doquery.drot = self.drot.currentText()
        self.doquery.startdate = self.startdate.text()
        self.doquery.enddate = self.enddate.text()

        thread = QThread(parent = self) # To avoid the UI to freeze during the query
        if not self._qmoved:
            self.doquery.moveToThread(thread)
            self._qmoved = True # To avoid having to move the thread again for the 2nd query
        thread.started.connect(self.doquery.start_query)
        thread.start()
        """
        Make sure we cannot do much during the query
        """
        self.star.setEnabled(False)
        self.searchbut.setEnabled(False)
        self.dlbut.setEnabled(False)
        self.obstable.setEnabled(False)
        self.doquery.finished.connect(thread.quit)
        self.doquery.finished.connect(lambda: self._update_table(self.doquery.obinfo))
        self.doquery.finished.connect(lambda: self.searchbut.setEnabled(True))
        self.doquery.finished.connect(lambda: self.star.setEnabled(True))
        self.doquery.finished.connect(lambda: self.obstable.setEnabled(True))

    def _create_table(self):
        """
        Create the table that will be used.
        """
        self.obstable.setFont(self.font)
        self.obstable.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.obstable.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.obstable.verticalHeader().setVisible(False)
        self.obstable.horizontalHeader().setVisible(False)
        self.obstable.horizontalHeader().setStretchLastSection(True)
        self.obstable.setSortingEnabled(True)

        self.obstable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.obstable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.obstable.setSelectionMode(QAbstractItemView.SingleSelection)
        self.obstable.setAlternatingRowColors(True)
        self.obstable.move(0,0)
        """
        Actions on single clik and double clicks
        """
        self.obstable.clicked.connect(self.singleClicked_table)
        self.obstable.doubleClicked.connect(self.doubleClicked_table)

    def singleClicked_table(self):
        self.dlbut.setEnabled(True)
        row = self.obstable.currentRow()
        starname = str(self.obstable.item(row,self.cols['mainID']).text())
        obsnight = str(self.obstable.item(row,self.cols['obsnight']).text())
        ob_id = str(self.obstable.item(row,self.cols['ob_id']).text())
        dirname = '{}/{}/{}/{}/raw/'.format(self.dpath, starname, obsnight, ob_id)
        self.set_status('Directory is: {}'.format(dirname))

    def doubleClicked_table(self):
        row = self.obstable.currentRow()
        starname = str(self.obstable.item(row,self.cols['mainID']).text())
        obsnight = str(self.obstable.item(row,self.cols['obsnight']).text()).split('\n')[0]
        ob_id = int(self.obstable.item(row,self.cols['ob_id']).text())
        self.cmwindow.cm.starname = starname
        self.cmwindow.cm.obsnight = obsnight
        self.cmwindow.cm.ob_id = ob_id
        self.cmwindow.cm.commentBox.setText(str(self._find_comment(starname, obsnight, ob_id)))
        self.cmwindow.show()

    def _check_dled(self, starname, obsnight, ob_id):
        """
        Check if I have downloaded the data already
        """
        dirname = '{}/{}/{}/{}/raw/'.format(self.dpath, starname, obsnight, ob_id)
        if Path(dirname).exists():
            lfits = glob.glob('{}/*'.format(dirname))
            if len(lfits) != 0:
                return True
            else:
                return False
        else:
            return False

    def _find_comment(self, starname, obsnight, ob_id):
        obsnight = obsnight.split('\n')[0]
        mask = (self.comments['starname'] == starname) & (self.comments['obsnight'] == obsnight) & (self.comments['ob_id'] == ob_id)
        if len(self.comments[mask]) != 0:
            ind = mask.nonzero()[0][0]
            return self.comments['comment'][ind]
        else:
            return ''

    def _update_table(self, results):
        """
        Update the obstable with the results
        """
        self.results = results
        labels = ['ID', 'Object', 'RA', 'DEC', 'Program ID', 'OB ID', 'INS COMB IFLT', \
                'INS4 DROT2 MODE', 'DET SEQ1 DIT', 'obsnight', 'Release Date', 'nfiles', 'DPR TECH']
        self.cols = {'mainID': 2, 'ob_id': 7, 'obsnight': 11, 'dptech': 14}
        nr = len(self.results)
        self.obstable.setRowCount(nr)
        self.obstable.setColumnCount(len(labels)+3)
        for i in range(nr):
            self.obstable.setItem(i,0, QTableWidgetItem(str(i)))
            obsnight = self.results[i]['obsnight'].split('\n')[0]
            ob_id = self.results[i]['OB ID']
            tempname = self._resolve_name(self.results[i]['Object'].split('\n')[0])
            comment = self._find_comment(tempname, obsnight, int(ob_id))
            if self._check_dled(tempname, obsnight, ob_id):
                self.obstable.setItem(i,1, QTableWidgetItem(u'\u25cf'))
            else:
                if comment != '':
                    self.obstable.setItem(i,1, QTableWidgetItem('x'))
                else:
                    self.obstable.setItem(i,1, QTableWidgetItem(' '))
            self.obstable.setItem(i,2, QTableWidgetItem(str(tempname)))
            for j in range(1,len(labels)):
                self.obstable.setItem(i,j+2, QTableWidgetItem(str(self.results[i][labels[j]])))
            self.obstable.setItem(i,len(labels)+2, QTableWidgetItem(comment))
        """
        Hide some of the columns
        """
        self.obstable.setColumnHidden(0, True)
        self.obstable.resizeColumnsToContents()
        self.obstable.resizeRowsToContents()
        """
        Refresh the infobox if a row was selected
        """
        # if self.obstable.currentRow() != -1:
            # self.dlbut.setEnabled(True)
            # self.singleClicked_table()
            # self.obstable.clearSelection()

class ObsTable(QTableWidget):
    """docstring for createTable"""
    enter_key = pyqtSignal()
    del_key = pyqtSignal()
    home_key = pyqtSignal()
    end_key = pyqtSignal()

    def __init__(self, parent = None):
        super(ObsTable, self).__init__(parent)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Return or key == Qt.Key_Enter:
            self.enter_key.emit()
        elif key == Qt.Key_Delete:
            self.del_key.emit()
        elif key == Qt.Key_Home:
            self.home_key.emit()
        elif key == Qt.Key_End:
            self.end_key.emit()
        else:
            super(ObsTable, self).keyPressEvent(event)



if __name__ == '__main__':
        app = QApplication(sys.argv)
        win = MainQuery()
        # apply_stylesheet(app, theme='light_blue.xml')
        win.show()
        sys.exit(app.exec_())
