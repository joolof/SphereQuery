import pyvo
import requests
import subprocess
import numpy as np
from pathlib import Path
from datetime import datetime
from astroquery.eso import Eso
import eso_programmatic as eso_prog
from PyQt5.QtCore import pyqtSignal, QObject
# ------------------------------------------------------------
eso = Eso()
eso.login(store_password = True)
# ------------------------------------------------------------
eso_url = "http://archive.eso.org/tap_obs"
base_access = 'https://dataportal.eso.org/dataPortal/file/'
base_datalink = 'https://archive.eso.org/datalink/links?ID=ivo://eso.org/ID?'
# ------------------------------------------------------------
class DoQuery(QObject):
    """
    docstring for DoQuery
    """
    changedStatus = pyqtSignal(str)
    changedLog = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, parent = None):
        """
        Query the ESO raw data archive
        """
        super(DoQuery, self).__init__(parent)
        self.starname, self.progid, self.dprtech, self.insfilt = '', '', '', ''
        self.drot, self.startdate, self.enddate  = '', '', ''
        self.obinfo = []

    def _set_status(self, text):
        self.changedStatus.emit(text)

    def _set_log(self, text):
        self.changedLog.emit(text)

    def _echo(self, message):
        self._set_log(message)
        self._set_status(message)

    def start_query(self):
        """
        Define the keywords
        """
        self._keywords = ['Release Date', 'Object', 'RA', 'DEC', 'Program ID', 'DP.ID', 'OB ID', 
                          'DPR TYPE', 'DPR TECH', 'INS3 OPTI5 NAME', 'INS3 OPTI6 NAME', 'INS COMB VCOR', \
                          'INS COMB IFLT', 'INS COMB POLA', 'INS COMB ICOR', 'DET DIT1', \
                          'DET SEQ1 DIT', 'DET NDIT', 'DET READ CURNAME', 'INS4 DROT2 MODE', \
                          'INS1 FILT NAME', 'INS1 OPTI1 NAME', 'INS1 OPTI2 NAME', 'INS4 OPTI11 NAME', \
                          'DIMM Seeing-avg']
        """
        Query a star
        """
        self.obinfo = []
        """
        Prepare the query
        """
        insquery = None
        self._echo('Querying the ESO archive for: {}'.format(self.starname))
        if self.dprtech == 'Any': self.dprtech = ''
        if self.insfilt == 'Any': self.insfilt = ''
        if self.drot == 'Any': self.drot = ''
        """
        Do the query
        """
        insquery = eso.query_instrument('sphere', target = self.starname, \
                ins_comb_iflt = self.insfilt, dp_tech = self.dprtech, dp_cat = 'SCIENCE', \
                seq_arm = 'IRDIS', cache = True, ins4_drot2_mode = self.drot, \
                prog_id = self.progid, stime = self.startdate, etime = self.enddate)
        """
        Parse the results
        """
        if insquery is None:
            self._echo('No results for: {}'.format(self.starname))
        else:
            self._prep_raw(insquery)
            self._set_status('Found {} entries ({} individual files)'.format(len(self.obinfo), len(insquery)))
        self.finished.emit()

    def _prep_raw(self, insquery):
        """
        Massage a bit the raw query output
        """
        self._echo('Query finished. Parsing the data.')
        date_obs = np.zeros(len(insquery), dtype = 'U23')
        insquery.add_column(date_obs, name = 'date_obs')
        obsnight = np.zeros(len(insquery), dtype = 'U10')
        insquery.add_column(obsnight, name = 'obsnight')
        for i in range(len(insquery)):
            insquery[i]['obsnight'] = str(insquery[i]['DP.ID'].replace('SPHER.','').split('T')[0])
            insquery[i]['date_obs'] = str(insquery[i]['DP.ID'].replace('SPHER.',''))
        insquery.sort('date_obs')

        groups = np.zeros(len(insquery))
        insquery.add_column(groups, name = 'groups')
        gid = 0
        for obid in np.unique(insquery['OB ID']):
            sel = np.where(insquery['OB ID'] == obid)[0]
            insquery[sel[0]]['groups'] = gid
            for ig in range(1,len(insquery[sel])):
                day1 = self._get_time(insquery[sel[ig]]['date_obs'])
                prev = self._get_time(insquery[sel[ig-1]]['date_obs'])
                deltah = divmod((day1 - prev).total_seconds(), 3600)[0]
                if deltah > 3.:
                    gid += 1
                insquery[sel[ig]]['groups'] = gid
            gid += 1
                
        for ir, io in enumerate(np.unique(insquery['groups'])):
            self.obinfo.append(self.parse(insquery[(insquery['groups'] == io)]))

    def _get_time(self, dobs):
        """
        Check the format of the date_obs
        and return a datetime object
        """
        if len(dobs.split('.')) == 2:
            dt = datetime.strptime(dobs, '%Y-%m-%dT%H:%M:%S.%f')
        else:
            dt = datetime.strptime(dobs, '%Y-%m-%dT%H:%M:%S')
        return dt

    def parse(self, q):
        """
        Parse the entries per "group"
        """
        d = {}
        d['nfiles'] = len(q)
        kw = self._keywords.copy()
        kw.append('obsnight')
        for key in kw:
            if key in q.colnames:
                tmp = np.unique(q[key].data)
                d[key] = self._format(tmp, key)
        return d

    def _format(self, entry, key):
        """
        Try to format things a bit better
        """
        text = ''
        if key == 'Object':
            if '' in entry: entry = np.delete(entry, np.where(entry == ''))
            if 'OBJECT' in entry: entry = np.delete(entry, np.where(entry == 'OBJECT'))
            if 'OBJECT NAME NOT SET' in entry: entry = np.delete(entry, np.where(entry == 'OBJECT NAME NOT SET'))
        if key == 'RA' or key == 'DEC':
            text += '{:.4f}'.format(np.mean(entry))
        else:
            if len(entry) ==0:
                text = '--'
            for i in range(len(entry)):
                text += str(entry[i])
                if i != len(entry) - 1:
                    text += '\n'
        return text




class DataDownloader(QObject):
    """
    docstring for DataDownloader
    """
    changedStatus = pyqtSignal(str)
    changedLog = pyqtSignal(str)
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self, parent = None):
        """
        Query the ESO raw data archive
        """
        super(DataDownloader, self).__init__(parent)
        self.user, self.password, self.dpath = None, None, None
        self.starname = ''
        self.obsnight, self.ob_id = None, None
        self.dp_id, self.selector = [], None

    def _set_status(self, text):
        self.changedStatus.emit(text)

    def _set_log(self, text):
        self.changedLog.emit(text)

    def _echo(self, message):
        self._set_log(message)
        self._set_status(message)

    def _get_data(self):
        """
        Get the main target name from CDS
        """
        token = eso_prog.getToken(self.user, self.password)
        session = None
        if token:
            session = requests.Session()
            session.headers['Authorization'] = "Bearer " + token

        self.access_url, self.datalink_url = [], []
        for dpid in self.dp_id:
            self.access_url.append('{}{}'.format(base_access, dpid))
            self.datalink_url.append('{}{}'.format(base_datalink, dpid))
        urls = self._urls_raw()

        dirname = '{}/{}/{}/{}/raw'.format(self.dpath, self.starname, self.obsnight, self.ob_id)
        Path(dirname).mkdir(parents=True, exist_ok=True)

        nf = len(urls)
        if nf > 0:
            self._echo('Will download {} files in {}'.format(nf, dirname))
        for i in range(nf):
            # print(urls[i])
            status, filename = eso_prog.downloadURL(urls[i], dirname = dirname, session = session)
            if status != 200:
                self._echo('Could not download the following file: {}'.format(filename))
            else:
                if filename[-1] == 'Z':
                    args = ['uncompress', '-f', filename]
                    tmp = subprocess.Popen(args).wait()
            self.progress.emit(int(100.*(i+1)/nf))
        self.finished.emit()

    def _urls_raw(self):
        """
        Get the urls for the raw data
        """
        urls = self.access_url
        if self.selector != 'sci':
            """
            Get the calibration files
            """
            self._echo('Running the calibration cascade.')
            semantics = 'http://archive.eso.org/rdf/datalink/eso#calSelector_{}'.format(self.selector)
            for i in range(len(self.datalink_url)):
                """
                Following the notebook at:
                http://archive.eso.org/programmatic/HOWTO/jupyter/authentication_and_authorisation/programmatic_authentication_and_authorisation.html
                """
                datalink = pyvo.dal.adhoc.DatalinkResults.from_result_url(self.datalink_url[i])
                raw2master_url = next(datalink.bysemantics(semantics), None)
                if raw2master_url is not None:
                    raw2master_url = raw2master_url.access_url
                    associated_calib_files = pyvo.dal.adhoc.DatalinkResults.from_result_url(raw2master_url)
                    calibrator_mask = associated_calib_files['semantics'] == '#calibration'
                    calibs = associated_calib_files.to_table()[calibrator_mask]['access_url']
                    for calib in calibs:
                        urls.append(calib)
            if urls == self.access_url:
                self._echo('No calibration files were found. ')
        return np.unique(urls)

