"""Installation file for CelNav source distribution under Linux

Will install:
    - Python package celnav
    - Python script file to run the application
    - Unix shell script to perform some housekeeping prior to executing Python script
    - Config and ini files
    - Html help documentation
    - Desktop configuration file to run under LXDE
    - Icon image file

See README file included in distribution for details.
"""

from distutils.core import setup
import os, sys, shutil


# need original user if setup run with sudo:
user = os.getenv('SUDO_USER')

# if run by non-root user, user is None at this point, so assume
# run as regular user
if user is None:
    user = os.getenv('USER')

APP_DIR = os.path.join('/home', user, '.celnav')   # used for ini, cfg files

# create APP_DIR if it doesn't exist:
if 'install' in sys.argv and not os.path.exists(APP_DIR):
    os.mkdirs(APP_DIR)

DATA_FILE_SRC_DIR = 'data_files'    # path relative to setup.py

PY_SCRIPT_DEST_DIR = '/opt/celnav'
SHELL_SCRIPT_DEST_DIR = '/usr/local/bin'
ICON_DEST_DIR = '/usr/local/share/icons'
DESKTOP_FILE_DEST_DIR = '/usr/share/applications'
DOC_DEST_DIR = '/usr/local/share/doc/celnav/html'
DOC_IMAGE_DEST_DIR = os.path.join(DOC_DEST_DIR, 'images')

PY_SCRIPT_FILE = 'cnscript.py'
SHELL_SCRIPT_FILE = 'nxcn'
ICON_FILE = 'navtriangle.png'
DESKTOP_FILE = 'celnav.desktop'
INI_FILE = 'celnav.ini'
TK_CFG_FILE = 'celnav.cfg'
LOG_FILE = 'celnav.log'

# dictionary with data files, mapping destination directory to source path:
dfMap = {
        os.path.join(DATA_FILE_SRC_DIR, SHELL_SCRIPT_FILE)      : SHELL_SCRIPT_DEST_DIR,
        PY_SCRIPT_FILE                                          : PY_SCRIPT_DEST_DIR,
        os.path.join(DATA_FILE_SRC_DIR, INI_FILE)               : APP_DIR,
        os.path.join(DATA_FILE_SRC_DIR, ICON_FILE)              : ICON_DEST_DIR,
        os.path.join(DATA_FILE_SRC_DIR, TK_CFG_FILE)            : APP_DIR,
        os.path.join(DATA_FILE_SRC_DIR, DESKTOP_FILE)           : DESKTOP_FILE_DEST_DIR,
        'data_files/doc/html/fix_method.html'                   : DOC_DEST_DIR,
        'data_files/doc/html/01_installation.html'              : DOC_DEST_DIR,
        'data_files/doc/html/stylesheet.css'                    : DOC_DEST_DIR,
        'data_files/doc/html/starnotes.txt'                     : DOC_DEST_DIR,
        'data_files/doc/html/index.html'                        : DOC_DEST_DIR,
        'data_files/doc/html/03_usage.html'                     : DOC_DEST_DIR,
        'data_files/doc/html/readme.txt'                        : DOC_DEST_DIR,
        'data_files/doc/html/02_configuration.html'             : DOC_DEST_DIR,
        'data_files/doc/html/celnav.ini'                        : DOC_DEST_DIR,
        'data_files/doc/html/images/page_banner.png'            : DOC_IMAGE_DEST_DIR,
        'data_files/doc/html/images/almanac_tab.gif'            : DOC_IMAGE_DEST_DIR,
        'data_files/doc/html/images/empty_bullet.gif'           : DOC_IMAGE_DEST_DIR,
        'data_files/doc/html/images/fix_tab.gif'                : DOC_IMAGE_DEST_DIR,
        'data_files/doc/html/images/star_data_commented.gif'    : DOC_IMAGE_DEST_DIR,
        'data_files/doc/html/images/celnav_log.gif'             : DOC_IMAGE_DEST_DIR,
        'data_files/doc/html/images/help_menu_detail.png'       : DOC_IMAGE_DEST_DIR,
        'data_files/doc/html/images/file_menu_ini_open.png'     : DOC_IMAGE_DEST_DIR,
        'data_files/doc/html/images/almanac_tab_numbered.gif'   : DOC_IMAGE_DEST_DIR,
        'data_files/doc/html/images/almanac_page_gnumeric.gif'  : DOC_IMAGE_DEST_DIR,
        'data_files/doc/html/images/file_menu_detail.png'       : DOC_IMAGE_DEST_DIR,
        'data_files/doc/html/images/star_data_gnumeric.gif'     : DOC_IMAGE_DEST_DIR,
        'data_files/doc/html/images/planet_finder_tab.gif'      : DOC_IMAGE_DEST_DIR,
        'data_files/doc/html/images/fix_tab_full_numbered.gif'  : DOC_IMAGE_DEST_DIR,
        'data_files/doc/html/images/planet_finder_tab_numbered.gif' : DOC_IMAGE_DEST_DIR
    }

# build data file list from dfMap:
fd = {}
for sf in dfMap:
    if dfMap[sf] in fd:
        fd[dfMap[sf]] = fd[dfMap[sf]] + [sf, ]
    else:
        fd[dfMap[sf]] = [sf, ]

dataFiles = []
for d in fd:
    dataFiles.append( (d, fd[d]) )


def move2old(sf):
    """Checks if the file with path exists and if yes moves it to fileName.old.
    The 'old' suffix may be preceded by a number of '_' in order not
    to overwrite existing files. Will print message to stdout if the
    file is moved.
    """
    if os.access(sf, os.F_OK):
        bk = '.old'
        i = 0
        while os.access(sf + bk, os.F_OK):
            i += 1
            bk = bk + i*'_'
        bk = sf + bk
        print
        print 'moving existing file %s to %s ...' % (sf, bk)
        shutil.move(sf, bk)


# First move any existing files out of the way and inform user:
if 'install' in sys.argv:

    # move stuff out of /opt/celnav...
    if os.access(PY_SCRIPT_DEST_DIR, os.F_OK):
        # move to /opt/celnav/old:
        dl = os.listdir(PY_SCRIPT_DEST_DIR)
        bk = 'old'
        i = 0
        while os.access(os.path.join(PY_SCRIPT_DEST_DIR, bk), os.F_OK):
            i += 1
            bk = i*'_' + bk
        bk = os.path.join(PY_SCRIPT_DEST_DIR, bk)
        print 'creating directory % s...' % bk
        os.mkdir(bk, 0755)
        for f in dl:
            sf = os.path.join(PY_SCRIPT_DEST_DIR, f)
            print
            print 'moving existing file %s to %s ...' % (sf, os.path.join(bk, f))
            shutil.move(sf, bk)

    # ...then the other stuff:
    for sf in [ os.path.join(SHELL_SCRIPT_DEST_DIR, SHELL_SCRIPT_FILE),
                os.path.join(DESKTOP_FILE_DEST_DIR, DESKTOP_FILE),
                os.path.join(APP_DIR, INI_FILE),
                os.path.join(APP_DIR, TK_CFG_FILE),
                os.path.join(APP_DIR, LOG_FILE) ]:
        move2old(sf)

# and now the meat:
setup(  name = 'CelNav',
        version = '0.2.3',
        description = 'Celestial Navigation for Cruisers',
        author = 'Markus Schweitzer',
        author_email = 'markus@namaniatsea.org',
        url = 'http://navigatrix.net/viewforum.php?f=21',
        requires = [ 'ephem', 'Tkinter', 'ttk' ],
        provides = [ 'celnav' ],
        packages = [ 'celnav' ],
        data_files = dataFiles
    )

if 'install' in sys.argv:
    # make shell script executable
    os.chmod(os.path.join(SHELL_SCRIPT_DEST_DIR, SHELL_SCRIPT_FILE), 0755)
    # make sure celnav.ini is writeable for the user
    os.chmod(os.path.join(APP_DIR, INI_FILE), 0666)

