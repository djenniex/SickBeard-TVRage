# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: https://sickrage.tv
# Git: https://github.com/SiCKRAGETV/SickRage.git
#
# This file is part of SickRage.
#
# SickRage is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickRage is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickRage.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import datetime
import logging
import os.path
import re
import urlparse

import backlog_searcher
import db
import helpers
import naming
import scheduler
import sickbeard
from logger import SRLogger


urlparse.uses_netloc.append('scgi')

naming_ep_type = ("%(seasonnumber)dx%(episodenumber)02d",
                  "s%(seasonnumber)02de%(episodenumber)02d",
                  "S%(seasonnumber)02dE%(episodenumber)02d",
                  "%(seasonnumber)02dx%(episodenumber)02d")

sports_ep_type = ("%(seasonnumber)dx%(episodenumber)02d",
                  "s%(seasonnumber)02de%(episodenumber)02d",
                  "S%(seasonnumber)02dE%(episodenumber)02d",
                  "%(seasonnumber)02dx%(episodenumber)02d")

naming_ep_type_text = ("1x02", "s01e02", "S01E02", "01x02")

naming_multi_ep_type = {0: ["-%(episodenumber)02d"] * len(naming_ep_type),
                        1: [" - " + x for x in naming_ep_type],
                        2: [x + "%(episodenumber)02d" for x in ("x", "e", "E", "x")]}
naming_multi_ep_type_text = ("extend", "duplicate", "repeat")

naming_sep_type = (" - ", " ")
naming_sep_type_text = (" - ", "space")

censoredItems = {}

def change_HTTPS_CERT(https_cert):
    """
    Replace HTTPS Certificate file path

    :param https_cert: path to the new certificate file
    :return: True on success, False on failure
    """
    if https_cert == '':
        sickbeard.HTTPS_CERT = ''
        return True

    if os.path.normpath(sickbeard.HTTPS_CERT) != os.path.normpath(https_cert):
        if helpers.makeDir(os.path.dirname(os.path.abspath(https_cert))):
            sickbeard.HTTPS_CERT = os.path.normpath(https_cert)
            logging.info("Changed https cert path to " + https_cert)
        else:
            return False

    return True


def change_HTTPS_KEY(https_key):
    """
    Replace HTTPS Key file path

    :param https_key: path to the new key file
    :return: True on success, False on failure
    """
    if https_key == '':
        sickbeard.HTTPS_KEY = ''
        return True

    if os.path.normpath(sickbeard.HTTPS_KEY) != os.path.normpath(https_key):
        if helpers.makeDir(os.path.dirname(os.path.abspath(https_key))):
            sickbeard.HTTPS_KEY = os.path.normpath(https_key)
            logging.info("Changed https key path to " + https_key)
        else:
            return False

    return True


def change_LOG_DIR(new_log_dir, new_web_log):
    """
    Change logger directory for application and webserver

    :param log_dir: Path to new logger directory
    :param web_log: Enable/disable web logger
    :return: True on success, False on failure
    """
    log_dir_changed = False
    log_dir = os.path.normpath(os.path.join(sickbeard.DATA_DIR, new_log_dir))
    web_log = checkbox_to_value(new_web_log)

    if os.path.normpath(sickbeard.LOG_DIR) != log_dir:
        if helpers.makeDir(log_dir):
            sickbeard.LOG_DIR = log_dir
            SRLogger.logFile = sickbeard.LOG_FILE = os.path.join(sickbeard.LOG_DIR, 'sickrage.log')
            SRLogger.initialize()

            logging.info("Initialized new log file in " + sickbeard.LOG_DIR)
            log_dir_changed = True

        else:
            return False

    if sickbeard.WEB_LOG != web_log or log_dir_changed == True:
        sickbeard.WEB_LOG = web_log

    return True


def change_NZB_DIR(nzb_dir):
    """
    Change NZB Folder

    :param nzb_dir: New NZB Folder location
    :return: True on success, False on failure
    """
    if nzb_dir == '':
        sickbeard.NZB_DIR = ''
        return True

    if os.path.normpath(sickbeard.NZB_DIR) != os.path.normpath(nzb_dir):
        if helpers.makeDir(nzb_dir):
            sickbeard.NZB_DIR = os.path.normpath(nzb_dir)
            logging.info("Changed NZB folder to " + nzb_dir)
        else:
            return False

    return True


def change_TORRENT_DIR(torrent_dir):
    """
    Change torrent directory

    :param torrent_dir: New torrent directory
    :return: True on success, False on failure
    """
    if torrent_dir == '':
        sickbeard.TORRENT_DIR = ''
        return True

    if os.path.normpath(sickbeard.TORRENT_DIR) != os.path.normpath(torrent_dir):
        if helpers.makeDir(torrent_dir):
            sickbeard.TORRENT_DIR = os.path.normpath(torrent_dir)
            logging.info("Changed torrent folder to " + torrent_dir)
        else:
            return False

    return True


def change_TV_DOWNLOAD_DIR(tv_download_dir):
    """
    Change TV_DOWNLOAD directory (used by postprocessor)

    :param tv_download_dir: New tv download directory
    :return: True on success, False on failure
    """
    if tv_download_dir == '':
        sickbeard.TV_DOWNLOAD_DIR = ''
        return True

    if os.path.normpath(sickbeard.TV_DOWNLOAD_DIR) != os.path.normpath(tv_download_dir):
        if helpers.makeDir(tv_download_dir):
            sickbeard.TV_DOWNLOAD_DIR = os.path.normpath(tv_download_dir)
            logging.info("Changed TV download folder to " + tv_download_dir)
        else:
            return False

    return True


def change_AUTOPOSTPROCESSOR_FREQ(freq):
    """
    Change frequency of automatic postprocessing thread
    TODO: Make all thread frequency changers in config.py return True/False status

    :param freq: New frequency
    """
    sickbeard.AUTOPOSTPROCESSOR_FREQ = to_int(freq, default=sickbeard.DEFAULT_AUTOPOSTPROCESSOR_FREQ)

    if sickbeard.AUTOPOSTPROCESSOR_FREQ < sickbeard.MIN_AUTOPOSTPROCESSOR_FREQ:
        sickbeard.AUTOPOSTPROCESSOR_FREQ = sickbeard.MIN_AUTOPOSTPROCESSOR_FREQ

    sickbeard.SCHEDULER.modify_job('POSTPROCESSOR',
                                   trigger=scheduler.SRIntervalTrigger(
                                           **{'minutes': sickbeard.AUTOPOSTPROCESSOR_FREQ,
                                              'min': sickbeard.MIN_AUTOPOSTPROCESSOR_FREQ}))


def change_DAILY_SEARCHER_FREQ(freq):
    """
    Change frequency of daily search thread

    :param freq: New frequency
    """
    sickbeard.DAILY_SEARCHER_FREQ = to_int(freq, default=sickbeard.DEFAULT_DAILY_SEARCHER_FREQ)
    sickbeard.SCHEDULER.modify_job('DAILYSEARCHER',
                                   trigger=scheduler.SRIntervalTrigger(
                                           **{'minutes': sickbeard.DAILY_SEARCHER_FREQ,
                                              'min': sickbeard.MIN_DAILY_SEARCHER_FREQ}))


def change_BACKLOG_SEARCHER_FREQ(freq):
    """
    Change frequency of backlog thread

    :param freq: New frequency
    """
    sickbeard.BACKLOG_SEARCHER_FREQ = to_int(freq, default=sickbeard.DEFAULT_BACKLOG_SEARCHER_FREQ)
    sickbeard.MIN_BACKLOG_SEARCHER_FREQ = backlog_searcher.get_backlog_cycle_time()
    sickbeard.SCHEDULER.modify_job('BACKLOG',
                                   trigger=scheduler.SRIntervalTrigger(
                                           **{'minutes': sickbeard.BACKLOG_SEARCHER_FREQ,
                                              'min': sickbeard.MIN_BACKLOG_SEARCHER_FREQ}))


def change_UPDATER_FREQ(freq):
    """
    Change frequency of daily updater thread

    :param freq: New frequency
    """
    sickbeard.SRUPDATER_FREQ = to_int(freq, default=sickbeard.DEFAULT_SRUPDATE_FREQ)
    sickbeard.SCHEDULER.modify_job('SRUPDATER',
                                   trigger=scheduler.SRIntervalTrigger(
                                           **{'hours': sickbeard.SRUPDATER_FREQ,
                                              'min': sickbeard.MIN_SRUPDATER_FREQ}))


def change_SHOWUPDATE_HOUR(freq):
    """
    Change frequency of show updater thread

    :param freq: New frequency
    """
    sickbeard.SHOWUPDATE_HOUR = to_int(freq, default=sickbeard.DEFAULT_SHOWUPDATE_HOUR)
    if sickbeard.SHOWUPDATE_HOUR < 0 or sickbeard.SHOWUPDATE_HOUR > 23:
        sickbeard.SHOWUPDATE_HOUR = 0

    sickbeard.SCHEDULER.modify_job('SHOWUPDATER',
                                   trigger=scheduler.SRIntervalTrigger(
                                           **{'hours': 1,
                                              'start_date': datetime.datetime.now().replace(
                                                  hour=sickbeard.SHOWUPDATE_HOUR)}))


def change_SUBTITLE_SEARCHER_FREQ(freq):
    """
    Change frequency of subtitle thread

    :param freq: New frequency
    """
    sickbeard.SUBTITLE_SEARCHER_FREQ = to_int(freq, default=sickbeard.DEFAULT_SUBTITLE_SEARCHER_FREQ)
    sickbeard.SCHEDULER.modify_job('SUBTITLESEARCHER',
                                   trigger=scheduler.SRIntervalTrigger(
                                           **{'hours': sickbeard.SUBTITLE_SEARCHER_FREQ,
                                              'min': sickbeard.MIN_SUBTITLE_SEARCHER_FREQ}))

def change_VERSION_NOTIFY(version_notify):
    """
    Change frequency of versioncheck thread

    :param version_notify: New frequency
    """
    sickbeard.VERSION_NOTIFY = checkbox_to_value(version_notify)
    if not sickbeard.VERSION_NOTIFY:
        sickbeard.NEWEST_VERSION_STRING = None

def change_DOWNLOAD_PROPERS(download_propers):
    """
    Enable/Disable proper download thread
    TODO: Make this return True/False on success/failure

    :param download_propers: New desired state
    """
    sickbeard.DOWNLOAD_PROPERS = checkbox_to_value(download_propers)
    job = sickbeard.SCHEDULER.get_job('PROPERSEARCHER')
    (job.pause, job.resume)[sickbeard.DOWNLOAD_PROPERS]()

def change_USE_TRAKT(use_trakt):
    """
    Enable/disable trakt thread
    TODO: Make this return true/false on success/failure

    :param use_trakt: New desired state
    """
    sickbeard.USE_TRAKT = checkbox_to_value(use_trakt)
    job = sickbeard.SCHEDULER.get_job('TRAKTSEARCHER')
    (job.pause, job.resume)[sickbeard.USE_TRAKT]()

def change_USE_SUBTITLES(use_subtitles):
    """
    Enable/Disable subtitle searcher
    TODO: Make this return true/false on success/failure

    :param use_subtitles: New desired state
    """
    sickbeard.USE_SUBTITLES = checkbox_to_value(use_subtitles)
    job = sickbeard.SCHEDULER.get_job('SUBTITLESEARCHER')
    (job.pause, job.resume)[sickbeard.USE_SUBTITLES]()

def change_PROCESS_AUTOMATICALLY(process_automatically):
    """
    Enable/Disable postprocessor thread
    TODO: Make this return True/False on success/failure

    :param process_automatically: New desired state
    """
    sickbeard.PROCESS_AUTOMATICALLY = checkbox_to_value(process_automatically)
    job = sickbeard.SCHEDULER.get_job('POSTPROCESSOR')
    (job.pause, job.resume)[sickbeard.PROCESS_AUTOMATICALLY]()


def CheckSection(CFG, sec):
    """ Check if INI section exists, if not create it """

    if sec in CFG:
        return True

    CFG[sec] = {}
    return False


def checkbox_to_value(option, value_on=1, value_off=0):
    """
    Turns checkbox option 'on' or 'true' to value_on (1)
    any other value returns value_off (0)
    """

    if isinstance(option, list):
        option = option[-1]

    if option == 'on' or option == 'true':
        return value_on

    return value_off


def clean_host(host, default_port=None):
    """
    Returns host or host:port or empty string from a given url or host
    If no port is found and default_port is given use host:default_port
    """

    host = host.strip()

    if host:

        match_host_port = re.search(r'(?:http.*://)?(?P<host>[^:/]+).?(?P<port>[0-9]*).*', host)

        cleaned_host = match_host_port.group('host')
        cleaned_port = match_host_port.group('port')

        if cleaned_host:

            if cleaned_port:
                host = cleaned_host + ':' + cleaned_port

            elif default_port:
                host = cleaned_host + ':' + str(default_port)

            else:
                host = cleaned_host

        else:
            host = ''

    return host


def clean_hosts(hosts, default_port=None):
    """
    Returns list of cleaned hosts by clean_host

    :param hosts: list of hosts
    :param default_port: default port to use
    :return: list of cleaned hosts
    """
    cleaned_hosts = []

    for cur_host in [x.strip() for x in hosts.split(",")]:
        if cur_host:
            cleaned_host = clean_host(cur_host, default_port)
            if cleaned_host:
                cleaned_hosts.append(cleaned_host)

    if cleaned_hosts:
        cleaned_hosts = ",".join(cleaned_hosts)

    else:
        cleaned_hosts = ''

    return cleaned_hosts


def clean_url(url):
    """
    Returns an cleaned url starting with a scheme and folder with trailing /
    or an empty string
    """

    if url and url.strip():

        url = url.strip()

        if '://' not in url:
            url = '//' + url

        scheme, netloc, path, query, fragment = urlparse.urlsplit(url, 'http')

        if not path:
            path = path + '/'

        cleaned_url = urlparse.urlunsplit((scheme, netloc, path, query, fragment))

    else:
        cleaned_url = ''

    return cleaned_url


def to_int(val, default=0):
    """ Return int value of val or default on error """

    try:
        val = int(val)
    except Exception:
        val = default

    return val


################################################################################
# Check_setting_int                                                            #
################################################################################
def minimax(val, default, low, high):
    """ Return value forced within range """

    val = to_int(val, default=default)

    if val < low:
        return low
    if val > high:
        return high

    return val


################################################################################
# Check_setting_int                                                            #
################################################################################
def check_setting_int(config, cfg_name, item_name, def_val, silent=True):
    try:
        my_val = config[cfg_name][item_name]
        if str(my_val).lower() == "true":
            my_val = 1
        elif str(my_val).lower() == "false":
            my_val = 0

        my_val = int(my_val)

        if str(my_val) == str(None):
            raise
    except Exception:
        my_val = def_val
        try:
            config[cfg_name][item_name] = my_val
        except Exception:
            config[cfg_name] = {}
            config[cfg_name][item_name] = my_val

    if not silent:
        logging.debug(item_name + " -> " + str(my_val))

    return my_val


################################################################################
# Check_setting_float                                                          #
################################################################################
def check_setting_float(config, cfg_name, item_name, def_val, silent=True):
    try:
        my_val = float(config[cfg_name][item_name])
        if str(my_val) == str(None):
            raise
    except Exception:
        my_val = def_val
        try:
            config[cfg_name][item_name] = my_val
        except Exception:
            config[cfg_name] = {}
            config[cfg_name][item_name] = my_val

    if not silent:
        logging.debug(item_name + " -> " + str(my_val))

    return my_val


################################################################################
# Check_setting_str                                                            #
################################################################################
def check_setting_str(config, cfg_name, item_name, def_val, silent=True, censor_log=False):
    # For passwords you must include the word `password` in the item_name and add `helpers.encrypt(ITEM_NAME, ENCRYPTION_VERSION)` in save_config()
    if bool(item_name.find('password') + 1):
        encryption_version = sickbeard.ENCRYPTION_VERSION
    else:
        encryption_version = 0

    try:
        my_val = helpers.decrypt(config[cfg_name][item_name], encryption_version)
        if str(my_val) == str(None):
            raise
    except Exception:
        my_val = def_val
        try:
            config[cfg_name][item_name] = helpers.encrypt(my_val, encryption_version)
        except Exception:
            config[cfg_name] = {}
            config[cfg_name][item_name] = helpers.encrypt(my_val, encryption_version)

    if censor_log or (cfg_name, item_name) in SRLogger.censoredItems:
        SRLogger.censoredItems[cfg_name, item_name] = my_val

    if not silent:
        logging.debug(item_name + " -> " + my_val)

    return my_val


class ConfigMigrator():
    def __init__(self, config_obj):
        """
        Initializes a config migrator that can take the config from the version indicated in the config
        file up to the version required by SB
        """

        self.config_obj = config_obj

        # check the version of the config
        self.config_version = check_setting_int(config_obj, 'General', 'config_version', sickbeard.CONFIG_VERSION)
        self.expected_config_version = sickbeard.CONFIG_VERSION
        self.migration_names = {
            1: 'Custom naming',
            2: 'Sync backup number with version number',
            3: 'Rename omgwtfnzb variables',
            4: 'Add newznab catIDs',
            5: 'Metadata update',
            6: 'Convert from XBMC to new KODI variables',
            7: 'Use version 2 for password encryption'
        }

    def migrate_config(self):
        """
        Calls each successive migration until the config is the same version as SB expects
        """

        if self.config_version > self.expected_config_version:
            logging.log_error_and_exit(
                    """Your config version (%i) has been incremented past what this version of SiCKRAGE supports (%i).
                    If you have used other forks or a newer version of SiCKRAGE, your config file may be unusable due to their modifications.""" %
                    (self.config_version, self.expected_config_version)
            )

        sickbeard.CONFIG_VERSION = self.config_version

        while self.config_version < self.expected_config_version:
            next_version = self.config_version + 1

            if next_version in self.migration_names:
                migration_name = ': ' + self.migration_names[next_version]
            else:
                migration_name = ''

            logging.info("Backing up config before upgrade")
            if not helpers.backupVersionedFile(sickbeard.CONFIG_FILE, self.config_version):
                logging.log_error_and_exit("Config backup failed, abort upgrading config")
            else:
                logging.info("Proceeding with upgrade")

            # do the migration, expect a method named _migrate_v<num>
            logging.info("Migrating config up to version " + str(next_version) + migration_name)
            getattr(self, '_migrate_v' + str(next_version))()
            self.config_version = next_version

            # save new config after migration
            sickbeard.CONFIG_VERSION = self.config_version

        return self.config_obj

    # Migration v1: Custom naming
    def _migrate_v1(self):
        """
        Reads in the old naming settings from your config and generates a new config template from them.
        """

        sickbeard.NAMING_PATTERN = self._name_to_pattern()
        logging.info("Based on your old settings I'm setting your new naming pattern to: " + sickbeard.NAMING_PATTERN)

        sickbeard.NAMING_CUSTOM_ABD = bool(check_setting_int(self.config_obj, 'General', 'naming_dates', 0))

        if sickbeard.NAMING_CUSTOM_ABD:
            sickbeard.NAMING_ABD_PATTERN = self._name_to_pattern(True)
            logging.info("Adding a custom air-by-date naming pattern to your config: " + sickbeard.NAMING_ABD_PATTERN)
        else:
            sickbeard.NAMING_ABD_PATTERN = naming.name_abd_presets[0]

        sickbeard.NAMING_MULTI_EP = int(check_setting_int(self.config_obj, 'General', 'naming_multi_ep_type', 1))

        # see if any of their shows used season folders
        myDB = db.DBConnection()
        season_folder_shows = myDB.select("SELECT * FROM tv_shows WHERE flatten_folders = 0")

        # if any shows had season folders on then prepend season folder to the pattern
        if season_folder_shows:

            old_season_format = check_setting_str(self.config_obj, 'General', 'season_folders_format', 'Season %02d')

            if old_season_format:
                try:
                    new_season_format = old_season_format % 9
                    new_season_format = str(new_season_format).replace('09', '%0S')
                    new_season_format = new_season_format.replace('9', '%S')

                    logging.info(
                            "Changed season folder format from " + old_season_format + " to " + new_season_format + ", prepending it to your naming config")
                    sickbeard.NAMING_PATTERN = new_season_format + os.sep + sickbeard.NAMING_PATTERN

                except (TypeError, ValueError):
                    logging.error("Can't change " + old_season_format + " to new season format")

        # if no shows had it on then don't flatten any shows and don't put season folders in the config
        else:

            logging.info("No shows were using season folders before so I'm disabling flattening on all shows")

            # don't flatten any shows at all
            myDB.action("UPDATE tv_shows SET flatten_folders = 0")

        sickbeard.NAMING_FORCE_FOLDERS = naming.check_force_season_folders()

    def _name_to_pattern(self, abd=False):

        # get the old settings from the file
        use_periods = bool(check_setting_int(self.config_obj, 'General', 'naming_use_periods', 0))
        ep_type = check_setting_int(self.config_obj, 'General', 'naming_ep_type', 0)
        sep_type = check_setting_int(self.config_obj, 'General', 'naming_sep_type', 0)
        use_quality = bool(check_setting_int(self.config_obj, 'General', 'naming_quality', 0))

        use_show_name = bool(check_setting_int(self.config_obj, 'General', 'naming_show_name', 1))
        use_ep_name = bool(check_setting_int(self.config_obj, 'General', 'naming_ep_name', 1))

        # make the presets into templates
        naming_ep_type = ("%Sx%0E",
                          "s%0Se%0E",
                          "S%0SE%0E",
                          "%0Sx%0E")
        naming_sep_type = (" - ", " ")

        # set up our data to use
        if use_periods:
            show_name = '%S.N'
            ep_name = '%E.N'
            ep_quality = '%Q.N'
            abd_string = '%A.D'
        else:
            show_name = '%SN'
            ep_name = '%EN'
            ep_quality = '%QN'
            abd_string = '%A-D'

        if abd:
            ep_string = abd_string
        else:
            ep_string = naming_ep_type[ep_type]

        finalName = ""

        # start with the show name
        if use_show_name:
            finalName += show_name + naming_sep_type[sep_type]

        # add the season/ep stuff
        finalName += ep_string

        # add the episode name
        if use_ep_name:
            finalName += naming_sep_type[sep_type] + ep_name

        # add the quality
        if use_quality:
            finalName += naming_sep_type[sep_type] + ep_quality

        if use_periods:
            finalName = re.sub(r"\s+", ".", finalName)

        return finalName

    # Migration v2: Dummy migration to sync backup number with config version number
    def _migrate_v2(self):
        return

    # Migration v2: Rename omgwtfnzb variables
    def _migrate_v3(self):
        """
        Reads in the old naming settings from your config and generates a new config template from them.
        """
        # get the old settings from the file and store them in the new variable names
        sickbeard.OMGWTFNZBS_USERNAME = check_setting_str(self.config_obj, 'omgwtfnzbs', 'omgwtfnzbs_uid', '')
        sickbeard.OMGWTFNZBS_APIKEY = check_setting_str(self.config_obj, 'omgwtfnzbs', 'omgwtfnzbs_key', '')

    # Migration v4: Add default newznab catIDs
    def _migrate_v4(self):
        """ Update newznab providers so that the category IDs can be set independently via the config """

        new_newznab_data = []
        old_newznab_data = check_setting_str(self.config_obj, 'Newznab', 'newznab_data', '')

        if old_newznab_data:
            old_newznab_data_list = old_newznab_data.split("!!!")

            for cur_provider_data in old_newznab_data_list:
                try:
                    name, url, key, enabled = cur_provider_data.split("|")
                except ValueError:
                    logging.error("Skipping Newznab provider string: '" + cur_provider_data + "', incorrect format")
                    continue

                if name == 'Sick Beard Index':
                    key = '0'

                if name == 'NZBs.org':
                    catIDs = '5030,5040,5060,5070,5090'
                else:
                    catIDs = '5030,5040,5060'

                cur_provider_data_list = [name, url, key, catIDs, enabled]
                new_newznab_data.append("|".join(cur_provider_data_list))

            sickbeard.NEWZNAB_DATA = "!!!".join(new_newznab_data)

    # Migration v5: Metadata upgrade
    def _migrate_v5(self):
        """ Updates metadata values to the new format """

        """ Quick overview of what the upgrade does:

        new | old | description (new)
        ----+-----+--------------------
          1 |  1  | show metadata
          2 |  2  | episode metadata
          3 |  4  | show fanart
          4 |  3  | show poster
          5 |  -  | show banner
          6 |  5  | episode thumb
          7 |  6  | season poster
          8 |  -  | season banner
          9 |  -  | season all poster
         10 |  -  | season all banner

        Note that the ini places start at 1 while the list index starts at 0.
        old format: 0|0|0|0|0|0 -- 6 places
        new format: 0|0|0|0|0|0|0|0|0|0 -- 10 places

        Drop the use of use_banner option.
        Migrate the poster override to just using the banner option (applies to xbmc only).
        """

        metadata_xbmc = check_setting_str(self.config_obj, 'General', 'metadata_xbmc', '0|0|0|0|0|0')
        metadata_xbmc_12plus = check_setting_str(self.config_obj, 'General', 'metadata_xbmc_12plus', '0|0|0|0|0|0')
        metadata_mediabrowser = check_setting_str(self.config_obj, 'General', 'metadata_mediabrowser', '0|0|0|0|0|0')
        metadata_ps3 = check_setting_str(self.config_obj, 'General', 'metadata_ps3', '0|0|0|0|0|0')
        metadata_wdtv = check_setting_str(self.config_obj, 'General', 'metadata_wdtv', '0|0|0|0|0|0')
        metadata_tivo = check_setting_str(self.config_obj, 'General', 'metadata_tivo', '0|0|0|0|0|0')
        metadata_mede8er = check_setting_str(self.config_obj, 'General', 'metadata_mede8er', '0|0|0|0|0|0')

        use_banner = bool(check_setting_int(self.config_obj, 'General', 'use_banner', 0))

        def _migrate_metadata(metadata, metadata_name, use_banner):
            cur_metadata = metadata.split('|')
            # if target has the old number of values, do upgrade
            if len(cur_metadata) == 6:
                logging.info("Upgrading " + metadata_name + " metadata, old value: " + metadata)
                cur_metadata.insert(4, '0')
                cur_metadata.append('0')
                cur_metadata.append('0')
                cur_metadata.append('0')
                # swap show fanart, show poster
                cur_metadata[3], cur_metadata[2] = cur_metadata[2], cur_metadata[3]
                # if user was using use_banner to override the poster, instead enable the banner option and deactivate poster
                if metadata_name == 'XBMC' and use_banner:
                    cur_metadata[4], cur_metadata[3] = cur_metadata[3], '0'
                # write new format
                metadata = '|'.join(cur_metadata)
                logging.info("Upgrading " + metadata_name + " metadata, new value: " + metadata)

            elif len(cur_metadata) == 10:

                metadata = '|'.join(cur_metadata)
                logging.info("Keeping " + metadata_name + " metadata, value: " + metadata)

            else:
                logging.error("Skipping " + metadata_name + " metadata: '" + metadata + "', incorrect format")
                metadata = '0|0|0|0|0|0|0|0|0|0'
                logging.info("Setting " + metadata_name + " metadata, new value: " + metadata)

            return metadata

        sickbeard.METADATA_XBMC = _migrate_metadata(metadata_xbmc, 'XBMC', use_banner)
        sickbeard.METADATA_XBMC_12PLUS = _migrate_metadata(metadata_xbmc_12plus, 'XBMC 12+', use_banner)
        sickbeard.METADATA_MEDIABROWSER = _migrate_metadata(metadata_mediabrowser, 'MediaBrowser', use_banner)
        sickbeard.METADATA_PS3 = _migrate_metadata(metadata_ps3, 'PS3', use_banner)
        sickbeard.METADATA_WDTV = _migrate_metadata(metadata_wdtv, 'WDTV', use_banner)
        sickbeard.METADATA_TIVO = _migrate_metadata(metadata_tivo, 'TIVO', use_banner)
        sickbeard.METADATA_MEDE8ER = _migrate_metadata(metadata_mede8er, 'Mede8er', use_banner)

    # Migration v6: Convert from XBMC to KODI variables
    def _migrate_v6(self):
        sickbeard.USE_KODI = bool(check_setting_int(self.config_obj, 'XBMC', 'use_xbmc', 0))
        sickbeard.KODI_ALWAYS_ON = bool(check_setting_int(self.config_obj, 'XBMC', 'xbmc_always_on', 1))
        sickbeard.KODI_NOTIFY_ONSNATCH = bool(check_setting_int(self.config_obj, 'XBMC', 'xbmc_notify_onsnatch', 0))
        sickbeard.KODI_NOTIFY_ONDOWNLOAD = bool(check_setting_int(self.config_obj, 'XBMC', 'xbmc_notify_ondownload', 0))
        sickbeard.KODI_NOTIFY_ONSUBTITLEDOWNLOAD = bool(
            check_setting_int(self.config_obj, 'XBMC', 'xbmc_notify_onsubtitledownload', 0))
        sickbeard.KODI_UPDATE_LIBRARY = bool(check_setting_int(self.config_obj, 'XBMC', 'xbmc_update_library', 0))
        sickbeard.KODI_UPDATE_FULL = bool(check_setting_int(self.config_obj, 'XBMC', 'xbmc_update_full', 0))
        sickbeard.KODI_UPDATE_ONLYFIRST = bool(check_setting_int(self.config_obj, 'XBMC', 'xbmc_update_onlyfirst', 0))
        sickbeard.KODI_HOST = check_setting_str(self.config_obj, 'XBMC', 'xbmc_host', '')
        sickbeard.KODI_USERNAME = check_setting_str(self.config_obj, 'XBMC', 'xbmc_username', '', censor_log=True)
        sickbeard.KODI_PASSWORD = check_setting_str(self.config_obj, 'XBMC', 'xbmc_password', '', censor_log=True)
        sickbeard.METADATA_KODI = check_setting_str(self.config_obj, 'General', 'metadata_xbmc', '0|0|0|0|0|0|0|0|0|0')
        sickbeard.METADATA_KODI_12PLUS = check_setting_str(self.config_obj, 'General', 'metadata_xbmc_12plus',
                                                           '0|0|0|0|0|0|0|0|0|0')

    # Migration v6: Use version 2 for password encryption
    def _migrate_v7(self):
        sickbeard.ENCRYPTION_VERSION = 2
