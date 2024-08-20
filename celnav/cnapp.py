#! /usr/bin/python

"""cnapp.py
Celnav application based on basic celnav objects in celnav.py
"""

__author__ = "markus@namaniatsea.org"
__version__ = "0.2.2"


# external application name and version (displayed in Help->About dialog):
EXT_APP_NAME = 'CelNav'
EXT_APP_VERSION = '0.2.2'

# import standard libraries
from math import *
import sys
import os
import os.path
import shutil
import configparser
import tempfile
import datetime as dt
import re           # needed for field validation

#import GUI stuff

# The Tkinter package from Python 2 has been renamed to tkinter in Python 3, as well as other modules related to it.
# 
# Here is a list of renamed modules:
# 
# Tkinter → tkinter
# tkMessageBox → tkinter.messagebox
# tkColorChooser → tkinter.colorchooser
# tkFileDialog → tkinter.filedialog
# tkCommonDialog → tkinter.commondialog
# tkSimpleDialog → tkinter.simpledialog
# tkFont → tkinter.font
# Tkdnd → tkinter.dnd
# ScrolledText → tkinter.scrolledtext
# Tix → tkinter.tix
# ttk → tkinter.ttk

import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox as tMB
import tkinter.filedialog as tFD
import tkinter.font as TkFont

# import celnav classes - will be customized to interact with GUI
import celnav.celnav as celnav

# import cncfg to get access to ConfigParser object:
import celnav.cncfg as cncfg

#-------------------------------------------------------------------------------------
# The following parameters can be overwritten in the INI_FILE read by module
# cncfg:
#-------------------------------------------------------------------------------------

SECTION_ID = 'cnapp'

APP_DIR = os.path.expandvars("$HOME/.celnav")   # used for cfg and log files
if cncfg.cncfg.has_option(SECTION_ID, 'APP_DIR'):
    APP_DIR = cncfg.cncfg.get(SECTION_ID, 'APP_DIR')

CFG_FILE = "celnav.cfg"
if cncfg.cncfg.has_option(SECTION_ID, 'CFG_FILE'):
    CFG_FILE = cncfg.cncfg.get(SECTION_ID, 'CFG_FILE')

LOG_FILE = "celnav.log"
if cncfg.cncfg.has_option(SECTION_ID, 'LOG_FILE'):
    LOG_FILE = cncfg.cncfg.get(SECTION_ID, 'LOG_FILE')

SPREADSHEET_PATH = "/usr/bin/gnumeric"   # path to spreadsheet executable
if cncfg.cncfg.has_option(SECTION_ID, 'SPREADSHEET_PATH'):
    SPREADSHEET_PATH = cncfg.cncfg.get(SECTION_ID, 'SPREADSHEET_PATH')

CSV_COLSEP  = ','   # used for Almanac Page and Star Data files that will be opend
                    # by program specified in SPREADSHEET_PATH
if cncfg.cncfg.has_option(SECTION_ID, 'CSV_COLSEP'):
    CSV_COLSEP = cncfg.cncfg.get(SECTION_ID, 'CSV_COLSEP')

EDITOR_PATH = "/usr/bin/leafpad"                # path to text editor executable
if cncfg.cncfg.has_option(SECTION_ID, 'EDITOR_PATH'):
    EDITOR_PATH = cncfg.cncfg.get(SECTION_ID, 'EDITOR_PATH')

BROWSER_PATH = "/usr/bin/firefox" # path to launch browser
if cncfg.cncfg.has_option(SECTION_ID, 'BROWSER_PATH'):
    BROWSER_PATH = cncfg.cncfg.get(SECTION_ID, 'BROWSER_PATH')

HELP_FILE_PATH = "/usr/local/share/doc/celnav/html/index.html"
if cncfg.cncfg.has_option(SECTION_ID, 'HELP_FILE_PATH'):
    HELP_FILE_PATH = cncfg.cncfg.get(SECTION_ID, 'HELP_FILE_PATH')

INITIAL_LAT = 0.0
if cncfg.cncfg.has_option(SECTION_ID, 'INITIAL_LAT'):
    INITIAL_LAT = cncfg.cncfg.getfloat(SECTION_ID, 'INITIAL_LAT')

INITIAL_LON = 0.0
if cncfg.cncfg.has_option(SECTION_ID, 'INITIAL_LON'):
    INITIAL_LON = cncfg.cncfg.getfloat(SECTION_ID, 'INITIAL_LON')

#------------ end ini-file stuff -------------------------------------------------

# import misc tools (e.g. generic print overloader)
import celnav.classprint as classprint

# TODO: global style definitions

# TODO: Reducing sights automatically picks median intercept in Radiobutton widget


# temporary directory into which Alamanac Pages  and Star Data can be written;
# will be set by Application which will also clean up before exiting
TMP_DIR = None



class ValidEntry(ttk.Entry, classprint.AttrDisplay):
    """Creates a ttk.Entry field and accepts a regex string for validation of
    user entry. If the entry does not match the regex upon focus moving away from
    the widget, an error message will be displayed and focus will remain on the
    widget.
    """
    # TODO: add remaining ttk.Entry options to constructor

    def __init__(self, master = None, width = 20, style = None, justify = tk.RIGHT,
            validateStr = r'^.*$', validate = 'focusout'):

        # controlVariable:
        self.cVar = tk.StringVar()

        # regex for field validation:
        self.validateStr = validateStr

        # register validation functions:
        self.validateFun = master.register(self.validateEntry)
        self.invalidFun = master.register(self.invalidEntry)

        ttk.Entry.__init__(self, master, style = style, width = width, justify = justify,
                textvariable = self.cVar, validatecommand = self.validateFun,
                invalidcommand = self.invalidFun, validate = validate)


    def validateEntry(self):
        r = re.compile(self.validateStr + '|^$', re.VERBOSE)
        if r.match(self.cVar.get()):
            return True
        else:
            return False

    def invalidEntry(self):
        message = 'Invalid entry: ' + self.cVar.get() + '\nentry must match ' + self.validateStr
        tMB.showerror('Invalid entry', message)
        self.focus_set()
        self.selection_own()


class LabeledEntry(ttk.Frame, classprint.AttrDisplay):
    """Provides a ValidEntry field, prefixed by a text label
    """

    def __init__(self, master = None, labelText = "Label", entryWidth = None, entryJustify = tk.RIGHT,
            entryValidateStr = r'^.*$', frameStyle = None, entryStyle = None, labelStyle = None):
        """Calls ttk.Frame contructor and then places a right-aligned label followed
        by a left-aligned ValidEntry box inside the frame.
        """
        ttk.Frame.__init__(self, master, class_ = "LabeledEntry", style = frameStyle)

        self.label = ttk.Label(self, text = labelText, justify = tk.RIGHT,
                padding = 5, style = labelStyle)
        self.label.grid(row = 0, column = 0, sticky = tk.E)

        self.entry = ValidEntry(self, width = entryWidth, style = entryStyle, justify = entryJustify,
                validateStr = entryValidateStr)
        self.entry.grid(row = 0, column = 1, sticky = tk.W)

    def set(self, text):
        self.entry.cVar.set(text)

    def get(self):
        return self.entry.cVar.get()


class AngleEntry(ttk.Frame, classprint.AttrDisplay):
    """Provides a composite entry field for a navigation angle (lat/lon or altitude) as a frame.

    The frame will contain three ValidEntry entry fields, one for whole degrees,
    one for minutes (incl. decimal fraction) and (optionally) one for a sign (see doc-string for
    __init__).
    """

    def __init__(self, master = None, frameStyle = None, entryStyle = None, degValidateStr = r"^[0-9]{1,3}$",
            minValidateStr = r"^[0-9]{1,2}\.?[0-9]?$", posValidateStr = None, negValidateStr = None,
            headerLabel = None, hdrLabelStyle = None, prefixLabel = None, prefixLabelStyle = None,
            padding = None):
        """Calls ttk.Frame consructor and then places ValidEntry fields for deg, min and sign (optionally
        - only if negValidateStr is provided) inside the frame. If headerLabel is provided, it will
        be placed above the Entry fields (spanning all of them).
        """
        ttk.Frame.__init__(self, master, class_ = "AngleEntry", padding = padding, style = frameStyle)

        if negValidateStr != None:
            noFields = 3
        else:
            noFields = 2

        if prefixLabel != None:
            noFields += 1

        currentRow = 0
        if headerLabel != None:
            hdr = ttk.Label(self, text = headerLabel, justify = tk.CENTER,
                    padding = 5, style = hdrLabelStyle)
            hdr.grid(row = currentRow, column = 0, columnspan = noFields+2)     # noFields+2 b/c of inserted
                                                                                # 'd' and 'm' labels
            currentRow += 1
            ttk.Separator(self, orient = tk.HORIZONTAL).grid(row = currentRow, column = 0,
                    columnspan = noFields+2, sticky = tk.E+tk.W)
            currentRow += 1

        currentCol = 0
        if prefixLabel != 1:
            ttk.Label(self, text = prefixLabel, justify = tk.RIGHT, padding = 5,
                    style = prefixLabelStyle).grid(row = currentRow,
                    column = currentCol, sticky = tk.E)
            currentCol += 1

        self.deg = ValidEntry(self, width = 3, style = entryStyle, validateStr = degValidateStr)
        self.deg.grid(row = currentRow, column = currentCol)
        currentCol += 1
        ttk.Label(self, text = u'\xb0').grid(row = currentRow, column = currentCol)
        currentCol += 1
        self.min = ValidEntry(self, width = 4, style = entryStyle, validateStr = minValidateStr)
        self.min.grid(row = currentRow, column = currentCol)
        currentCol += 1
        ttk.Label(self, text = "'").grid(row = currentRow, column = currentCol)
        currentCol += 1
        if negValidateStr != None:
            self.sign = ValidEntry(self, width = 2, justify = tk.LEFT, style = entryStyle,
                    validateStr = posValidateStr + '|' + negValidateStr)
            self.sign.grid(row = currentRow, column = currentCol)
        else:
            self.sign = None

        self.posValidateStr = posValidateStr
        self.negValidateStr = negValidateStr


    def set(self, angle):
        """sets control variables for each field according to angle which must
        be a tuple (deg, min, sign). The character to be used to indicate the
        sign (e.g. 'W' for negative longitude) will be taken from the posValidateStr /
        negValidateStr regexes (first character matching [A-Z]).
        """
        self.deg.cVar.set("%d" % (angle[0]))
        self.min.cVar.set("%.1f" % (angle[1]))
        if self.sign != None:
            if angle[2] == 1:
                self.sign.cVar.set(re.findall('[A-Z]', self.posValidateStr)[0])
            if angle[2] == -1:
                self.sign.cVar.set(re.findall('[A-Z]', self.negValidateStr)[0])


    def get(self):
        """Returns tuple (deg, min, sign) with each element set to corresponding
        Entry control variable. If there is no sign entry field, sign will be set
        to +1
        """
        deg = int(self.deg.cVar.get())
        minutes = float(self.min.cVar.get())
        if self.sign == None:
            s = 1
        else:
            p = re.compile(self.posValidateStr, re.VERBOSE)
            if p.match(self.sign.cVar.get()):
                s = 1
            else:
                s = -1

        return (deg, minutes, s)


class DateEntry(ttk.Frame, classprint.AttrDisplay):
    """Provides a composite entry field for a date as a frame.
    The frame will contain six ValidEntry entry fields (Y,M,D)
    """
    # TODO: re-write TimeEntry as a descendant of DateEntry (DateTimeEntry)

    def __init__(self, master = None, frameStyle = None, entryStyle = None, padding = None,
            headerLabel = None, hdrLabelStyle = None, prefixLabel = None, prefixLabelStyle = None):
        """Calls ttk.Frame consructor and then places ValidEntry fields for Y, M, D.
        If headerLabel is provided, it will be placed above the Entry fields
        (spanning all of them). If prefixLabel is provided it will be placed to
        the left of the entry fields.
        """
        ttk.Frame.__init__(self, master, class_ = "TimeEntry", padding = padding, style = frameStyle)

        noFields = 5   # 3 entries + 2 separation characters
        if prefixLabel != None:
            noFields += 1

        currentRow = 0
        if headerLabel != None:
            hdr = ttk.Label(self, text = headerLabel, justify = tk.CENTER,
                    padding = 5, style = hdrLabelStyle)
            hdr.grid(row = currentRow, column = 0, columnspan = noFields)
            currentRow += 1
            ttk.Separator(self, orient = tk.HORIZONTAL).grid(row = currentRow, column = 0,
                    columnspan = noFields, sticky = tk.E+tk.W)
            currentRow += 1

        currentCol = 0
        if prefixLabel != 1:
            ttk.Label(self, text = prefixLabel, justify = tk.RIGHT, padding = 5,
                    style = prefixLabelStyle).grid(row = currentRow,
                    column = currentCol, sticky = tk.E)
            currentCol += 1

        self.year = ValidEntry(self, width = 4, style = entryStyle, validateStr = r'^[0-9]{4,4}$')
        self.year.grid(row = currentRow, column = currentCol)
        currentCol += 1
        ttk.Label(self, text = '/').grid(row = currentRow, column = currentCol)
        currentCol += 1
        self.month = ValidEntry(self, width = 2, style = entryStyle, validateStr = r'^[0-1]?[0-9]$')
        self.month.grid(row = currentRow, column = currentCol)
        currentCol += 1
        ttk.Label(self, text = '/').grid(row = currentRow, column = currentCol)
        currentCol += 1
        self.day = ValidEntry(self, width = 2, style = entryStyle, validateStr = r'^[0-3]?[0-9]$')
        self.day.grid(row = currentRow, column = currentCol)
        currentCol += 1

    def set(self, date):
        """sets control variables for each field according to date which must
        be a tuple (Y, M, D)
        """
        self.year.cVar.set("%d" % (date[0]))
        self.month.cVar.set("%d" % (date[1]))
        self.day.cVar.set("%d" % (date[2]))

    def get(self):
        """Returns tuple (Y, M, D) with each element set to corresponding
        Entry control variable.
        """
        year = int(self.year.cVar.get())
        month = int(self.month.cVar.get())
        day = int(self.day.cVar.get())

        return (year, month, day)


class TimeEntry(ttk.Frame, classprint.AttrDisplay):
    """Provides a composite entry field for a date/time as a frame.
    The frame will contain six ValidEntry entry fields (Y,M,D,h,m,s)
    """

    def __init__(self, master = None, frameStyle = None, entryStyle = None, padding = None,
            headerLabel = None, hdrLabelStyle = None, prefixLabel = None, prefixLabelStyle = None):
        """Calls ttk.Frame consructor and then places ValidEntry fields for Y, M, D, h, m, s
        If headerLabel is provided, it will be placed above the Entry fields (spanning all of them).
        """
        ttk.Frame.__init__(self, master, class_ = "TimeEntry", padding = padding, style = frameStyle)

        noFields = 11   # 6 entries + 5 separation characters
        if prefixLabel != None:
            noFields += 1

        currentRow = 0
        if headerLabel != None:
            hdr = ttk.Label(self, text = headerLabel, justify = tk.CENTER,
                    padding = 5, style = hdrLabelStyle)
            hdr.grid(row = currentRow, column = 0, columnspan = noFields)
            currentRow += 1
            ttk.Separator(self, orient = tk.HORIZONTAL).grid(row = currentRow, column = 0,
                    columnspan = noFields, sticky = tk.E+tk.W)
            currentRow += 1

        currentCol = 0
        if prefixLabel != 1:
            ttk.Label(self, text = prefixLabel, justify = tk.RIGHT, padding = 5,
                    style = prefixLabelStyle).grid(row = currentRow,
                    column = currentCol, sticky = tk.E)
            currentCol += 1

        self.year = ValidEntry(self, width = 4, style = entryStyle, validateStr = r'^[0-9]{4,4}$')
        self.year.grid(row = currentRow, column = currentCol)
        currentCol += 1
        ttk.Label(self, text = '/').grid(row = currentRow, column = currentCol)
        currentCol += 1
        self.month = ValidEntry(self, width = 2, style = entryStyle, validateStr = r'^[0-1]?[0-9]$')
        self.month.grid(row = currentRow, column = currentCol)
        currentCol += 1
        ttk.Label(self, text = '/').grid(row = currentRow, column = currentCol)
        currentCol += 1
        self.day = ValidEntry(self, width = 2, style = entryStyle, validateStr = r'^[0-3]?[0-9]$')
        self.day.grid(row = currentRow, column = currentCol)
        currentCol += 1
        ttk.Label(self, text = '-').grid(row = currentRow, column = currentCol)
        currentCol += 1
        self.hour = ValidEntry(self, width = 2, style = entryStyle, validateStr = r'^[0-2]?[0-9]$')
        self.hour.grid(row = currentRow, column = currentCol)
        currentCol += 1
        ttk.Label(self, text = ':').grid(row = currentRow, column = currentCol)
        currentCol += 1
        self.minute = ValidEntry(self, width = 2, style = entryStyle, validateStr = r'^[0-5]?[0-9]$')
        self.minute.grid(row = currentRow, column = currentCol)
        currentCol += 1
        ttk.Label(self, text = ':').grid(row = currentRow, column = currentCol)
        currentCol += 1
        self.second = ValidEntry(self, width = 2, style = entryStyle, validateStr = r'^[0-5]?[0-9]$')
        self.second.grid(row = currentRow, column = currentCol)
        currentCol += 1

    def set(self, time):
        """sets control variables for each field according to time which must
        be a tuple (Y, M, D, h, m, s)
        """
        self.year.cVar.set("%d" % (time[0]))
        self.month.cVar.set("%d" % (time[1]))
        self.day.cVar.set("%d" % (time[2]))
        self.hour.cVar.set("%d" % (time[3]))
        self.minute.cVar.set("%d" % (time[4]))
        self.second.cVar.set("%d" % (time[5]))

    def get(self):
        """Returns tuple (Y. M. D, h, m, s)  with each element set to corresponding
        Entry control variable.
        """
        year = int(self.year.cVar.get())
        month = int(self.month.cVar.get())
        day = int(self.day.cVar.get())
        hour = int(self.hour.cVar.get())
        minute = int(self.minute.cVar.get())
        second = int(self.second.cVar.get())

        return (year, month, day, hour, minute, second)


class BodyComboBox(ttk.Frame, classprint.AttrDisplay):
    """Provides combined list boxes for bodies and stars. Has self.getSelection method
    that returns a tuple (<body>, , <star name>, <star number>). Uses global
    celnav.bodyList.
    """
    def __init__(self, master = None, frameStyle = None):

        ttk.Frame.__init__(self, master, class_ = "BodyListBox", style = frameStyle)

        ll = master.register(self.listLink)

        self.bodyDropDown = ttk.Combobox(self, values = celnav.bodyList[:],
                validatecommand = ll, validate = 'all', width = 6, justify = tk.LEFT)
        self.bodyDropDown.current(0)
        self.bodyDropDown.state(['readonly'])
        self.bodyDropDown.grid(row = 0, column = 0, sticky = tk.W)

        self.starDropDown = ttk.Combobox(self, values = celnav.starList,
                width = 12, justify = tk.LEFT)
        self.starDropDown.current(0)
        self.starDropDown.state(['disabled'])
        self.starDropDown.grid(row = 0, column = 1, sticky = tk.W)



    def listLink(self):
        """Enables/disables star ComboBox dependent on body selection
        """
        if self.bodyDropDown.current() == len(celnav.bodyList)-1:   # 'star' selected -> enable star selection
            self.starDropDown.state(['!disabled', 'readonly'])
        else:
            self.starDropDown.current(0)                            # something else selected -> disable
            self.starDropDown.state(['disabled'])

        return True

    def getSelection(self):
        """Returns currently selected body-star combination as a (<body text>,
        <star name>, <star number>) tuple
        """

        bodyIndex = self.bodyDropDown.current()
        if bodyIndex == -1:
            bodyText = "n/a"
        else:
            bodyText = celnav.bodyList[bodyIndex]

        starIndex = self.starDropDown.current()
        if starIndex < 1:
            starText = None
            starNum = None
        else:
            starText = celnav.starList[starIndex]
            starNum = celnav.starNum(starText)

        return (bodyText, starText, starNum)


class AppMenuBar(tk.Menu, classprint.AttrDisplay):
    """Creates menu bar for toplevel window with 'File' and 'Help' choices.
    Toplevel window must be passed to constructor.
    """
    def __init__(self, top):
        tk.Menu.__init__(self, top)
        self.top = top
        self.top['menu'] = self

        # add 'File' menu
        self.fileMenu = tk.Menu(self, tearoff = 0)
        self.add_cascade(label = 'File', menu = self.fileMenu)
        self.fileMenu.add_command(label = 'Open log file', command = self.__openLogHandler)
        self.fileMenu.add_command(label = 'Open ini file', command = self.__openIniHandler)
        self.fileMenu.add_separator()
        self.fileMenu.add_command(label = 'Quit', command = self.__quitHandler)

        self.helpMenu = tk.Menu(self, tearoff = 0)
        self.add_cascade(label = 'Help', menu = self.helpMenu)
        self.helpMenu.add_command(label = 'CelNav Help', command = self.__cnHelpHandler)
        self.helpMenu.add_separator()
        self.helpMenu.add_command(label = 'About', command = self.__aboutHandler)

    def __aboutHandler(self):
        aboutStr = ('%s %s: Electronic almanac and sight reduction for celestial navigation on small vessels.\n'
                % (EXT_APP_NAME, EXT_APP_VERSION))
        aboutStr += 'Use at your own risk!\n'
        aboutStr += 'Comments, bugs, suggestions: markus@namaniatsea.net'
        tMB.showinfo('About %s' % EXT_APP_NAME, aboutStr, icon = tMB.INFO)

    def __quitHandler(self):
        self.top.destroy()

    def __openLogHandler(self):
        os.spawnv(os.P_NOWAIT, SPREADSHEET_PATH, [SPREADSHEET_PATH,
            os.path.join(APP_DIR, LOG_FILE)])

    def __openIniHandler(self):
        os.spawnv(os.P_NOWAIT, EDITOR_PATH, [EDITOR_PATH,
            os.path.join(cncfg.INI_DIR, cncfg.INI_FILE)])

    def __cnHelpHandler(self):
        os.spawnv(os.P_NOWAIT, BROWSER_PATH, [BROWSER_PATH, HELP_FILE_PATH])


class Application(ttk.Frame, classprint.AttrDisplay):
    """Top level class; creates root window and 'Fix' instance.  Also provides
    handler for resizing management and self.__exitHandler for cleanup prior to
    exiting.  Sets global variable TMP_DIR. This directory can be used by any
    method in cnapp for writing temporary files. self.__exitHandler() will
    attempt to remove this directory and everythiing in it when the application
    terminates.
    """

    def __init__(self, master = None):
        """Reads config file and sets up Notebook tabs
        """
        global TMP_DIR

        ttk.Frame.__init__(self, master)
        self.grid()

        # read Tkinter config file if it exists
        cfgFileStr = os.path.join(APP_DIR, CFG_FILE)
        if os.access(cfgFileStr, os.F_OK):
            self.option_readfile(cfgFileStr)

        self.nb = ttk.Notebook(self)
        self.nb.grid()

        self.nb.almanac = AppAlmanac(self.nb)
        self.nb.add(self.nb.almanac, text = "Almanac")

        self.nb.planets = AppPlanetFinder(self.nb)
        self.nb.add(self.nb.planets, text = "Planet Finder")

        self.nb.fix = AppFix(self.nb)
        self.nb.add(self.nb.fix, text = "Sight Reduction & Fix")

        # add menu bar
        self.menubar = AppMenuBar(self.winfo_toplevel())

        # get screen dimensions and set initial maxsize for toplevel window accordingly
        # top = self.winfo_toplevel()
        # top.maxsize(height = self.winfo_screenheight(), width = self.winfo_screenwidth())
        self.winfo_toplevel().bind('<Configure>', self.topLevelConfigureHandler)

        # bind clean-up to 'Destroy' event:
        self.bind('<Destroy>', self.__exitHandler)
        self.needToCleanUp = True

        # create tmp directory:
        TMP_DIR = tempfile.mkdtemp(prefix = 'cnapp_')

        # log current celnav settings - if log file already exists (otherwise we block writing of headers)
        if 'START_UP_LOG_MSG' in celnav.__dict__:
            if os.access(os.path.join(APP_DIR, LOG_FILE), os.F_OK):
                timeStamp = "%04d/%02d/%02d,%02d:%02d:%02d" % dt.datetime.utcnow().timetuple()[:6]
                logFile = open(os.path.join(APP_DIR, LOG_FILE), 'a')
                logFile.write('%s,%s\n' % (timeStamp, celnav.START_UP_LOG_MSG))
                logFile.close()

    def __exitHandler(self, event):
        """Attempts to remove TMP_DIR and its contents. Should be bound to
        'Destroy' event for Application frame.
        """
        global TMP_DIR

        if self.needToCleanUp and (TMP_DIR != None):
            try:
                shutil.rmtree(TMP_DIR)
            except:
                warningStr = "Could not completely remove temporary directory %s" % TMP_DIR
                tMB.showwarning(title = "CelNav Warning", message = warningStr, icon = tMB.WARNING)

            self.needToCleanUp = False


    def topLevelConfigureHandler(self, event):
        """Handles configure events on top level window in order to display/hide
        scrollbars depending on window size
        """

        top = self.winfo_toplevel()

        # get screen dimensions and reset maxsize for toplevel window accordingly;
        # width will be restricted by the smaller of screenwidth and width of AppFix frame
        reqHeight = self.winfo_reqheight()
        reqWidth = self.winfo_reqwidth()

        maxHeight = (self.winfo_screenheight() - 60)    # leave some space for task/toolbar at bottom
        maxWidth = min(self.winfo_screenwidth(), reqWidth)

        top.maxsize(width = maxWidth, height = maxHeight)

        # if reqHeight < event.height:
        #     curTopGeoTuple = self.__geo2tuple(top.geometry())
        #     newTopGeoStr = "%dx%d%+d%+d" % (min(maxWidth, reqWidth, event.width),
        #            min(reqHeight, maxHeight), curTopGeoTuple[2], curTopGeoTuple[3])
        #    top.geometry(newTopGeoStr)

        # print self.configureCount, reqHeight, event.height


    def __geo2tuple(self, geoStr):
        """turns a Tk geometry string of the form 'wxh+/-x+/-y' into a tuple (w, h, x, y)
        """
        # use regex to isolate components:
        r = re.compile(r'^(?P<widthG>[0-9]*)x(?P<heightG>[0-9]*)(?P<xrootG>[+-][0-9]*)(?P<yrootG>[+-][0-9]*)$')
        m = r.match(geoStr)

        width = int(geoStr[m.start('widthG') : m.end('widthG')])
        height = int(geoStr[m.start('heightG') : m.end('heightG')])
        xroot = int(geoStr[m.start('xrootG') : m.end('xrootG')])
        yroot = int(geoStr[m.start('yrootG') : m.end('yrootG')])

        return (width, height, xroot, yroot)


class AppFix(ttk.Frame, celnav.Fix, classprint.AttrDisplay):
    """Customizes celnav.Fix to interact with GUI.
    Fix has all its attributes shared at class level. Hence all
    assigments have to via class rather than instance.
    """

    def __init__(self, master = None):
        """Calls ttk.Frame and celnav.Fix constructors, creates control variables and
        links them to celnav.Fix attributes, places fix-level widgets and instantiates
        first Shight
        """
        ttk.Frame.__init__(self, master)
        celnav.Fix.__init__(self)

        # lists /control variables for LOP management:
        self.lopAddDelFrameList = []                            # list of frames containing "+/-" buttons (1 per LOP)
        self.lopAddCallback = master.register(self.addLOP)      # callback for "+" button
        self.lopDelCallback = master.register(self.delLOP)      # callback for "-" button

        # create and place entry widgets:
        currentRow = 0
        currentCol = 0

        ttk.Label(self, class_ = "FrameTitle", text = "Fix").grid(row = currentRow, column = currentCol, sticky = tk.W)
        currentCol += 1

        self.sogDisp = LabeledEntry(self, labelText = "SOG [kn]:", entryWidth = 5, entryValidateStr = r'^[0-9]{1,3}\.?[0-9]?$')
        self.sogDisp.grid(row = currentRow, column = currentCol)
        currentCol += 1

        self.cogDisp = LabeledEntry(self, labelText = "COG [" + u'\xb0' + "T]:", entryWidth = 3, entryValidateStr = r'^[0-9]{1,3}$')
        self.cogDisp.grid(row = currentRow, column = currentCol)
        currentCol += 1

        self.fixUTDisp = TimeEntry(self, prefixLabel = "UT for fix:\n[Y/M/D-h:m:s]")
        self.fixUTDisp.grid(row = currentRow, column = currentCol)
        currentCol += 1

        self.fixPosDisp = ttk.Label(self, class_ = "FixPosDisplay", anchor = tk.E, borderwidth = 3,
                relief = tk.RIDGE, foreground = "blue", text = "position: N/A")
        self.fixPosDisp.grid(row = currentRow, column = currentCol, sticky = tk.E)
        currentCol += 1

        # initialize entry fields:
        self.__attr2entry()

        self.fixUpdateButton = ttk.Button(self, text = "Update Fix", command = self.calcFixCallback, padding = 5)
        self.fixUpdateButton.grid(row = currentRow, column = currentCol)
        currentCol += 1

        self.logButton = ttk.Button(self, text = "Write Log", command = self.__writeLog, padding = 5)
        self.logButton.grid(row = currentRow, column = currentCol)
        currentCol += 1

        currentRow += 1

        # set up AppLOPs, add initial LOP
        self.firstLOPRow = currentRow
        self.lopColSpan = currentCol-1

        self.addLOP()

        # if it doesn't exist: create log file:
        if not os.access(os.path.join(APP_DIR, LOG_FILE), os.F_OK):
            self.__writeLog()


    def calcFixCallback(self):
        """Callback for Calculate Fix' button; calls reduceSightCallback for each LOP,
        updates Sights and LOPs from entry fields,  and
        then uses Fix.__calc2LLPFix() and subsequently updates display.
        """
        for lop in self.lopList:
            lop.reduceSightsCallback()

        # update Fix attributes based on user entry:
        self.__entry2attr()

        # calculate plane trig 2 LOP fix:
        try:
            self.calc2LOPFix()
        except celnav.FixLOPError:
            errorStr = "Fix calculation requires two LOPs with one Sight selected in each LOP for inclusion in fix"
            tMB.showerror(title = "Fix Error", message = errorStr, icon = tMB.ERROR)

        # update display/entry values:
        self.__attr2entry()

        # write log:
        # self.__writeLog()


    def addLOP(self):
        """Adds an new LOP frame, creates and grids "+/-" buttons, removes "+/-" buttons on
        AppLOP above (will be remembered for future re-gridding).
        """
        global INITIAL_LAT, INITIAL_LON

        # append and grid new AppLOP
        i = len(self.lopList)

        if i > 0:       # initialize with values from previous LOP.observer
            self.lopList[i-1].lopEntry2Attr()
            prevObs = self.lopList[i-1].observer
            self.lopList.append(AppLOP(self, lopNumber = i, indexError = prevObs.indexError.decD * 60,
                heightOfEye = prevObs.heightOfEye, lat = prevObs.latDecD(), lon = prevObs.lonDecD(),
                temp = prevObs.temp, pressure = prevObs.pressure))
        else:
            self.lopList.append(AppLOP(self, lopNumber = i, lat = INITIAL_LAT, lon = INITIAL_LON))

        self.lopList[i].grid(row = self.firstLOPRow+i, column = 1, columnspan = self.lopColSpan, sticky = tk.E+tk.W)

        # hide all previous "+/-" buttons
        for j in range(i):
            self.lopAddDelFrameList[j].grid_remove()

        # create and grid new "+/-" button frame
        if i > 0: delButton = True
        else: delButton = False
        self.lopAddDelFrameList.append(AddDelFrame(self, delButton = delButton,
            addCallback = self.lopAddCallback, delCallback = self.lopDelCallback))
        self.lopAddDelFrameList[i].grid(row = self.firstLOPRow+i, column = 0, sticky = tk.S)


    def delLOP(self):
        """Destroys last (bottom-most) LOP incl. "+/-", re-grids "+/-" of next LOP.
        """
        i = len(self.lopList)     # that's the one we need to get rid off

        # get rid off "+/-" button
        self.lopAddDelFrameList[i-1].destroy()
        self.lopAddDelFrameList.pop(i-1)

        # re-grid next button frame in line
        self.lopAddDelFrameList[i-2].grid()

        # get rid of AppLOP instance itself
        self.lopList[i-1].destroy()
        self.lopList.pop(i-1)


    def fixEntry2Attr(self):        # TODO: replace wrapper + internal by external
        self.__entry2attr()

    def fixAttr2Entry(self):        # TODO: replace wrapper + internal by external
        self.__attr2entry()

    def __entry2attr(self):
        self.SOG = float(self.sogDisp.get())
        self.COG.decD = float(self.cogDisp.get())
        self.UT = self.fixUTDisp.get()

    def __attr2entry(self):
        self.sogDisp.set("%0.1f" % (self.SOG))
        self.cogDisp.set("%03d" % (int(round(self.COG.decD))))
        self.fixUTDisp.set(self.UT)
        self.__updateFixPosDisplay()


    def __updateFixPosDisplay(self):
        """Updates fix lat/lon display in AppFix frame based on current self.lat and self.lon.
        Does not calculate new fix.
        """
        # fix coordinates:
        latStr = "%02d%s %04.1f'" % (self.lat.degMin[0], u'\xb0', self.lat.degMin[1])
        if self.lat.degMin[2] == -1:
            latStr += " S"
        else:
            latStr += " N"
        lonStr = "%03d%s %04.1f'" % (self.lon.degMin[0], u'\xb0', self.lon.degMin[1])
        if self.lon.degMin[2] == -1:
            lonStr += " W"
        else:
            lonStr += " E"

        self.fixPosDisp.configure(text = ("%s - %s" % (latStr, lonStr)))


    logFileHeadings = [
        'UT Date',
        'UT Time',
        'Fix SOG [kn]',
        'Fix COG [deg T]',
        'Fix UT Date',
        'Fix UT Time',
        'Fix Lat in decD',
        'Fix Lat deg',
        'Fix Lat min',
        'Fix Lat sign',
        'Fix Lon in decD',
        'Fix Lon deg',
        'Fix Lon min',
        'Fix Lon sign',
        'LOP number',
        'LOP body',
        'LOP star',
        'LOP AP Lat decD',
        'LOP AP Lat deg',
        'LOP AP Lat min',
        'LOP AP Lat sign',
        'LOP AP Lon decD',
        'LOP AP Lon deg',
        'LOP AP Lon min',
        'LOP AP Lon sign',
        'LOP Height of Eye [m]',
        'LOP Index Error [arc min]',
        'LOP pressure [mbar]',
        'LOP temperature [deg C]',
        'Sight number',
        'Sight UT Date',
        'Sight UT Time',
        'Sight Hs in decD',
        'Sight Hs in deg',
        'Sight Hs in min',
        'Sight Ic [nm]',
        'Sight srfIc [nm]',
        'Sight Azimuth [deg T]',
        'Sight in Fix?'
        ]

    def __writeLog(self):
        """Writes log entry with all dcurrently available data
        """
        global CSV_COLSEP

        if not os.access(APP_DIR, os.F_OK):     # directory for logfile does not exist
            os.makedirs(APP_DIR)

        if not os.access(os.path.join(APP_DIR, LOG_FILE), os.F_OK):
            logFile = open(os.path.join(APP_DIR, LOG_FILE), 'w')
            hdgStr = ""
            for (i, h) in enumerate(AppFix.logFileHeadings):
                if i < len(AppFix.logFileHeadings)-1: sep = CSV_COLSEP
                else: sep = '\n'
                hdgStr += "%s%s" % (h, sep)
            logFile.write(hdgStr)
        else:
            logFile = open(os.path.join(APP_DIR, LOG_FILE), 'a')

        # time stamp
        timeStamp = "%04d/%02d/%02d,%02d:%02d:%02d" % dt.datetime.utcnow().timetuple()[:6]
        # fix SOG, COG, UT
        fixStr = "%.1f, %d" % (self.SOG, int(round(self.COG.decD)))
        fixStr += ", %04d/%02d/%02d,%02d:%02d:%02d" % self.UT
        #fix Lat
        fixStr += ",%f" % self.lat.decD
        fixStr += ",%d,%f,%d" % self.lat.degMin
        #fix Lon
        fixStr += ",%f" % self.lon.decD
        fixStr += ",%d,%f,%d" % self.lon.degMin

        for (lopNr, lop) in enumerate(self.lopList):
            # lop number, body and star
            lopStr = "%d,%s,%s" % (lopNr+1, lop.body, lop.starName)
            # AP Lat
            lopStr += ",%f" % lop.observer.latDecD()
            lopStr += ",%d,%f,%d" % lop.observer.latTuple()
            # AP Lon
            lopStr += ",%f" % lop.observer.lonDecD()
            lopStr += ",%d,%f,%d" % lop.observer.lonTuple()
            # hoe, ie, press, temp
            lopStr += ",%.1f,%.1f,%.1f,%.1f" % (lop.observer.heightOfEye, lop.observer.indexError.decD * 60,
                    lop.observer.pressure, lop.observer.temp)

            for (sNr, s) in enumerate(lop.sightList):
                sightStr = "%d" % (sNr+1)
                sightStr += ",%04d/%02d/%02d, %02d:%02d:%02d" % s.UT
                sightStr += ",%f,%d,%f" % (s.Hs.decD, s.Hs.degMin[0], s.Hs.degMin[1])
                sightStr += ",%f,%f,%d" % (s.Ic, s.srfIc, int(round(s.Az.decD)))
                if sNr == lop.lopSightIndex: sightStr += ", 1"
                else: sightStr += ",0"

                logFile.write("%s,%s,%s,%s\n" % (timeStamp, fixStr, lopStr, sightStr))

        logFile.close()


class AppLOP(ttk.Frame, celnav.LOP, classprint.AttrDisplay):
    """Customizes celnav.Sight to interact with GUI
    """

    def __init__(self, master = None, body = 'Sun LL', starName = None, indexError = 0,
            heightOfEye = 0, lat = INITIAL_LAT, lon = INITIAL_LON, elevation = 0, temp = 20, pressure = 1010,
            lopNumber = 0):
        """Calls ttk.Frame and celnav.Sight constructors, creates control variables and
        links them to celnav.Sight attributes, places sight-level widgets and instantiates
        first Shot
        """
        ttk.Frame.__init__(self, master, borderwidth = 3, relief = tk.GROOVE)
        celnav.LOP.__init__(self, fix = master, body = body, starName = starName, indexError = indexError,
                heightOfEye = heightOfEye, lat = lat, lon = lon, elevation = elevation,
                temp = temp, pressure = pressure)

        # lists /control variables for sight management:
        self.sightAddDelFrameList = []          # list of frames containing "+/-" buttons (1 per AppSight)
        self.sightForFixRBList = []             # list of radio buttons to pick Sight for inclusion in fix
        self.sightFixRBcVar = tk.IntVar()       # contral variable for radio button group
        self.sightAddCallback = master.register(self.addSight)      # callback for "+" button
        self.sightDelCallback = master.register(self.delSight)      # callback for "-" button

        #  create and place entry widgets:
        currentRow = 0
        currentCol = 0

        ttk.Label(self, text = "LOP #%d" % (lopNumber+1), class_ = "FrameTitle").grid(row = currentRow,
                column = currentCol, sticky = tk.W)
        currentCol += 1

        # Combined body/star dropdowns
        self.bodyStarDropDown = BodyComboBox(self)
        self.bodyStarDropDown.grid(row = currentRow, column = currentCol, sticky = tk.W)
        currentCol += 1

        # Assumed position lat / lon
        self.latEntry = AngleEntry(self, posValidateStr = r"^[Nn]$", negValidateStr = r"^[Ss]$", prefixLabel = "AP:")
        self.latEntry.grid(row = currentRow, column = currentCol, sticky = tk.W)
        currentCol += 1

        self.lonEntry = AngleEntry(self, posValidateStr = r"^[Ee]$", negValidateStr = r"^[Ww]$")
        self.lonEntry.grid(row = currentRow, column = currentCol, sticky = tk.W)
        currentCol += 1

        # Height of eye
        self.hoeEntry = LabeledEntry(self, labelText = "Height of eye:\n[meter]", entryWidth = 3,
            entryValidateStr = r"^[0-9][0-9]*\.?[0-9]?$")
        self.hoeEntry.grid(row = currentRow, column = currentCol, sticky = tk.W)
        currentCol += 1

        # index error
        self.ieEntry = LabeledEntry(self, labelText = "Index error:\n[minutes]", entryWidth = 4,
            entryValidateStr = r"^[+-]?[0-9]\.?[0-9]?$")
        self.ieEntry.grid(row = currentRow, column = currentCol, sticky = tk.W)
        currentCol += 1

        # pressure
        self.pressureEntry = LabeledEntry(self, labelText = "pressure:\n[mbar]", entryWidth = 4,
            entryValidateStr = r"^[0-9]{3,4}$")
        self.pressureEntry.grid(row = currentRow, column = currentCol, sticky = tk.W)
        currentCol += 1

        # temperature
        self.tempEntry = LabeledEntry(self, labelText = "temp.:\n[deg C]", entryWidth = 3,
            entryValidateStr = r"^[-]?[0-9]{1,2}$")
        self.tempEntry.grid(row = currentRow, column = currentCol, sticky = tk.W)
        currentCol += 1

        # place heading for Sight selection radio buttons under last column
        currentRow +=1
        self.sightForFixLabel = ttk.Label(self, text = "Use for Fix?", justify = tk.CENTER,
                padding = 5)
        self.sightForFixLabel.grid(row = currentRow, column = currentCol-1)

        # initialize display values:
        self.__attr2entry()

        # place "Reduce sights" button in last but one column:
        self.reduceSightsButton = ttk.Button(self, text="Reduce Sights", command = self.reduceSightsCallback,
                padding = 3)
        self.reduceSightsButton.grid(row = currentRow, column = currentCol-2, pady=3)

        # place "Hide Sights" button in col 1
        self.showHideSightsButton = ttk.Button(self, text="Hide Sights", command = self.__hideSights,
                padding = 3)
        self.showHideSightsButton.grid(row = currentRow, column = 1, pady=3, sticky = tk.W)

        # create label for Ic/Az display when sights are hidden; gridded and removed right away,
        # will be switched on and off by self.__hideSights() and self.__showSights
        self.IcAzDisp = ttk.Label(self, class_ = "IcAzDisplay", anchor = tk.E, borderwidth = 5,
                foreground = "blue", text = "Ic, Az: N/A", justify = tk.CENTER)
        self.IcAzDisp.grid(row = currentRow, column = 2, columnspan = currentCol-4)
        self.IcAzDisp.grid_remove()

        currentRow += 1

        # set up AppSights, add initial sight
        self.firstSightRow = currentRow
        self.sightColSpan = currentCol-2
        self.sightRBCol = currentCol-1

        self.addSight()


    def reduceSightsCallback(self):
        """Updates inherited celnav.LOP attributes from widget values and does the same for
        each sight in self.sightList. Also updates Fix attributs from widget value in order
        to calculate MOO correction. Calls self.calcIcAz() to reduce sights and update Ic
        and Az values for each sight in self.sightList. Finally, updates widgets in LOP and
        each sight in self.sightList() to reflect calculated values.
        """
        self.fix.fixEntry2Attr()

        self.__entry2attr()

        for sight in self.sightList:
            sight.sightEntry2Attr()

        self.calcIcAz()

        self.__attr2entry()

        for sight in self.sightList:
            sight.sightAttr2Entry()

    def lopEntry2Attr(self):        # TODO: replace wrapper + internal by external
        self.__entry2attr()

    def lopAttr2Entry(self):         # TODO: replace wrapper + internal by external
        self.__attr2entry()

    def __entry2attr(self):
        """Updates the attributes inherited from celnav.LOP based on current widget entries.
        Note that self.sightList is automatically maintained via self.addSight() and
        self.delSight() (plus AppSight. __entry2attr()).
        """
        bodyStarSel = self.bodyStarDropDown.getSelection()   # tuple (body, star name, star num)
        self.body = bodyStarSel[0]
        self.starName = bodyStarSel[1]
        self.starNum = bodyStarSel[2]
        self.lopSightIndex = int(self.sightFixRBcVar.get())
        a = celnav.Angle()
        a.degMin = self.latEntry.get()
        self.observer.lat = a.rad
        a.degMin = self.lonEntry.get()
        self.observer.lon = a.rad
        self.observer.temp = int(self.tempEntry.get())
        self.observer.pressure = int(self.pressureEntry.get())
        self.observer.indexError.decD = float(self.ieEntry.get()) / 60
        self.observer.heightOfEye = float(self.hoeEntry.get())
        self.observer.calcDip()          # sets self.dip


    def __attr2entry(self):
        """Updates values shown in entry fields based on current values of inherited celnav.LOP
        attributes
        """
        self.latEntry.set(self.observer.latTuple())
        self.lonEntry.set(self.observer.lonTuple())
        self.tempEntry.set("%d" % int(self.observer.temp))
        self.pressureEntry.set("%d" % int(self.observer.pressure))
        self.hoeEntry.set("%.1f" % self.observer.heightOfEye)
        self.ieEntry.set("%+.1f" % (self.observer.indexError.decD * 60))
        # TODO: set for bodyStar combobox


    def addSight(self):
        """Adds an new AppSight frame, creates and grids "+/-" buttons and radio button,
        removes "+/-" buttons on AppSights above (will be remembered)
        """
        # append and grid new AppSight
        i = len(self.sightList)

        if i > 0:       # initialize with previous Hs, UT values
            self.sightList[i-1].sightEntry2Attr()
            self.sightList.append(AppSight(master = self, sightNumber = i, Hs = self.sightList[i-1].Hs.decD,
                UT = self.sightList[i-1].UT))
        else:
            self.sightList.append(AppSight(master = self, sightNumber = i))

        self.sightList[i].grid(row = self.firstSightRow+i, column = 1, columnspan = self.sightColSpan, sticky = tk.E+tk.W)

        # hide all previous "+/-" buttons
        for j in range(i):
            self.sightAddDelFrameList[j].grid_remove()

        # create and grid new "+/-" button frame
        if i > 0: delButton = True
        else: delButton = False
        self.sightAddDelFrameList.append(AddDelFrame(self, delButton = delButton,
            addCallback = self.sightAddCallback, delCallback = self.sightDelCallback))
        self.sightAddDelFrameList[i].grid(row = self.firstSightRow+i, column = 0, sticky = tk.S)

        # add radio button
        self.sightForFixRBList.append(ttk.Radiobutton(self, value = i, variable = self.sightFixRBcVar))
        self.sightForFixRBList[i].grid(row = self.firstSightRow+i, column = self.sightRBCol)


    def delSight(self):
        """Destroys last (bottom-most) AppSight incl. "+/-" and radio buttons.
        Re-grids "+/-" of next AppSight
        """
        i = len(self.sightList)     # that's the one we need to get rid off

        # get rid off "+/-" button
        self.sightAddDelFrameList[i-1].destroy()
        self.sightAddDelFrameList.pop(i-1)

        # re-grid next button frame in line
        self.sightAddDelFrameList[i-2].grid()

        # get rid of AppSight instance itself
        self.sightList[i-1].destroy()
        self.sightList.pop(i-1)

        # radio button removal
        self.sightForFixRBList[i-1].destroy()
        self.sightForFixRBList.pop(i-1)


    def __hideSights(self):
        """Hides all AppSight frames under current LOP.
        Also changes text and callback assignment for self.showHideSightsButton.
        """
        n = len(self.sightList)

        self.sightAddDelFrameList[n-1].grid_remove()
        for i in range(n):
            self.sightList[i].grid_remove()
            self.sightForFixRBList[i].grid_remove()

        self.sightForFixLabel.grid_remove()
        self.reduceSightsButton.grid_remove()

        self.IcAzDisp.grid()
        self.sightList[int(self.sightFixRBcVar.get())].updateIcAzDisplay(self.IcAzDisp)

        self.showHideSightsButton.configure(text = "Show Sights", command = self.__showSights)


    def __showSights(self):
        """Unhides all AppSight frames under current LOP
        Also changes text and callback assignment for self.showHideSightsButton.
        """
        n = len(self.sightList)

        self.sightAddDelFrameList[n-1].grid()
        for i in range(n):
            self.sightList[i].grid()
            self.sightForFixRBList[i].grid()

        self.sightForFixLabel.grid()
        self.reduceSightsButton.grid()

        self.IcAzDisp.grid_remove()

        self.showHideSightsButton.configure(text = "Hide Sights", command = self.__hideSights)


class AddDelFrame(ttk.Frame, classprint.AttrDisplay):
    """Provides Frame with two vertically stacked buttons "+" and "-" (if named argument delButton == True).
    Tk-registered callback functions for each button must be passed to constructor.
    """
    def __init__(self, master = None, frameStyle = None, addCallback = None, delCallback = None,
            buttonStyle = None, delButton = False):

        ttk.Frame.__init__(self, master, style = frameStyle, class_ = "AddDelFrame")

        ttk.Button(self, text = "+", width = 3, command = addCallback, style = buttonStyle).grid()

        if delButton == True:
            ttk.Button(self, text = "-", width = 3, command = delCallback, style = buttonStyle).grid()


class AppSight(ttk.Frame, celnav.Sight, classprint.AttrDisplay):
    """Augments celnav.Sight to interact with GUI
    """
    def __init__(self, master = None, Hs = 0, UT = None, sightNumber = 0):
        """sightNumber is the 0-based index of this Sight instance in the LOP's sightList
        """

        # First call super class contructors
        ttk.Frame.__init__(self, master, borderwidth = 3, relief = tk.GROOVE)
        celnav.Sight.__init__(self, Hs = Hs, UT = UT)

        #  create and place entry widgets:
        currentRow = 0
        currentCol = 0

        ttk.Label(self, text = "Sight #%d" % (sightNumber+1),
                class_ = "FrameTitle").grid(row = currentRow, column = currentCol, sticky = tk.W)
        currentCol += 1

        # Sight time:
        # self.UTEntry = TimeEntry(self, prefixLabel = "Sight UT:\n[Y/M/D-h:m:s]")
        self.UTEntry = TimeEntry(self, prefixLabel = "Sight UT:")
        self.UTEntry.grid(row = currentRow, column = currentCol)
        currentCol += 1

        # sextant altitude:
        self.HsEntry = AngleEntry(self, prefixLabel = "Hs:")
        self.HsEntry.grid(row = currentRow, column = currentCol)
        currentCol += 1

        # display Intercepts and Azimuth
        self.IcAzDisp = ttk.Label(self, class_ = "IcAzDisplay", anchor = tk.E, borderwidth = 5,
                foreground = "blue", text = "Ic, Az: N/A")
        self.IcAzDisp.grid(row = currentRow, column = currentCol)
        currentCol += 1

        # update widgets with current attribute values
        self.__attr2entry()


    def sightEntry2Attr(self):      # TODO: replace wrapper + internal by one external (required for sightList updates by LOP)
        self.__entry2attr()

    def sightAttr2Entry(self):      # TODO: replace wrapper + internal by one external (required for sightList updates by LOP)
        self.__attr2entry()


    def __entry2attr(self):
        """Updates the attributes inherited from celnav.Sight based on current widget entries.
        Does not update self.includeInFix (is done by LOP)
        """
        self.Hs.degMin = self.HsEntry.get()
        self.UT = self.UTEntry.get()

    def __attr2entry(self):
        """Updates values shown in entry fields based on current values of inherited celnav.Sight
        attributes
        """
        self.HsEntry.set(self.Hs.degMin)
        self.UTEntry.set(self.UT)
        self.updateIcAzDisplay(self.IcAzDisp)


    def updateIcAzDisplay(self, widget):
        """Updates sight's Ic, short run fix Ic, and Azimuth display in Sight frame based on current
        self.Ic, self.srfIc and self.Az. Does not reduce sight.
        Widget is the Label which is to be updated.
        """
        IcStr = "Ic = %4.1f" % (abs(self.Ic))
        if self.Ic < 0:
            IcStr += " A"
        else:
            IcStr += " T"

        srfIcStr = "MOO corr. Ic = %4.1f" % (abs(self.srfIc))
        if self.srfIc < 0:
            srfIcStr += " A"
        else:
            srfIcStr += " T"

        AzStr = "Az = %03d%sT" % (int(round(self.Az.decD)), u'\xb0')

        widget.configure(text = ("  %s    %s    %s" % (IcStr, srfIcStr, AzStr)))


class AppAlmanac(ttk.Frame, celnav.SunMoonRiseSet, classprint.AttrDisplay):
    """Provides entry fields for lat, lon and UT and displays table with data
    for Sun rise, set, meridian passage and civil and naut. twilight. Also Moon
    rise, set, upper meridian passage, prev. new and full moon, next new, and
    full moon, plus number of days into current lunar cycle.  Also provides
    button to write almanac page for given date as CSV table to a file. The
    file will contain hourly data for GHA Aries, for GHA and Dec for planets,
    Sun and Moon, and for HP for Moon. Data will be written in degrees with
    decimal fraction and the usual sign convention (+ = N/E, - = S/W).  See doc
    string for celnav.SunMoonRiseSet and celnav.AlmanacPage for details on
    attributes.
    """
    # TODO: add Aries meridian passage
    tableRowLabel = [
            'Naut. twilight',
            'Civil twilight',
            'Rise',
            'Meridian Pass.',
            'Set',
            'Civil twilight',
            'Naut. twilight',
            'SD'
            ]
    tableDataKeyMap =  [
            { 'sun' : 'twl_naut_am', 'moon' : None },
            { 'sun' : 'twl_civil_am', 'moon' : None },
            { 'sun' : 'rise', 'moon' : 'rise' },
            { 'sun' : 'mer_pass', 'moon' : 'mer_pass' },
            { 'sun' : 'set', 'moon' : 'set' },
            { 'sun' : 'twl_civil_pm', 'moon' : None },
            { 'sun' : 'twl_naut_pm', 'moon' : None },
            { 'sun' : 'sd', 'moon' : 'sd'}
            ]
    moonLabelMap = {
            'prev_new'  :   'Prev. New Moon',
            'prev_full' :   'Prev. Full Moon',
            'next_new'  :   'Next New Moon',
            'next_full' :   'Next Full Moon',
            'age'       :   'Moon Age'
            }

    # body sequence used to iterate over the differemnt planed data
    # dictionaries via self.__dict__
    alPgBodySeq = ('aries', 'sun', 'moon', 'venus', 'mars', 'jupiter', 'saturn')

    alPgBodyLabelMap = {
            'aries' : 'Aries',
            'sun' : 'Sun',
            'moon' : 'Moon',
            'venus' : 'Venus',
            'mars' : 'Mars',
            'jupiter' : 'Jupiter',
            'saturn' : 'Saturn'
            }

    alPgKeyLabelMap = {
            'gha' : 'GHA',
            'dec' : 'Dec',
            'hp' : 'HP'
            }

    def __init__(self, master = None):
        """Calls ttk.Frame and celnav.SunMoonRiseSet constructors, creates
        control varaiales and links them to celnav.SunMoonRiseSet attributes,
        places entry and label widgets in frame and calculates attributes for
        default lat/lon of 0/0 for current UT.
        """
        ttk.Frame.__init__(self, master)

        ut = dt.datetime.utcnow().timetuple()[:6]
        celnav.SunMoonRiseSet.__init__(self, lat = INITIAL_LAT, lon =
                INITIAL_LON, ut = ut)

        # dictionaries for control variables; keys will be same as in
        # celnav.SunMoonRiseSet.sun.data and celnav.SunMoonRiseSet.moon.data
        self.cVarDictSun = {}
        self.cVarDictMoon = {}

        # create and place entry widgets and buttons:
        currentRow = 0
        currentCol = 0

        ef = ttk.Frame(self, padding = 5)
        ef.grid(row = currentRow, column = currentCol, sticky = tk.W+tk.E)
        frameRow = 0
        frameCol = 0
        # UT date entry:
        self.utEntry = TimeEntry(ef, prefixLabel = "UT:", padding = 5)
        self.utEntry.grid(row = frameRow, column = frameCol)
        frameCol += 1

        # lat / lon for which rise/set/transit data is requested
        self.latEntry = AngleEntry(ef, posValidateStr = r"^[Nn]$", negValidateStr = r"^[Ss]$", prefixLabel = "Lat:",
                padding = 5)
        self.latEntry.grid(row = frameRow, column = frameCol, sticky = tk.W)
        frameCol += 1

        self.lonEntry = AngleEntry(ef, posValidateStr = r"^[Ee]$", negValidateStr = r"^[Ww]$", prefixLabel = "Lon:",
                padding = 5)
        self.lonEntry.grid(row = frameRow, column = frameCol, sticky = tk.W)
        frameCol += 1

        # initialize entry fields:
        self.attr2entry()

        # button for data update
        self.updateButton = ttk.Button(ef, text="Update Display", command = self.updateDataCallback,
                padding = 3)
        self.updateButton.grid(row = frameRow, column = frameCol, pady=3, sticky = tk.E)
        frameCol += 1

        # button for generating almanac page
        self.genAlmPgButton = ttk.Button(ef, text="Almanac Page", command = self.genAlmPgCallback,
                padding = 3)
        self.genAlmPgButton.grid(row = frameRow, column = frameCol, pady=3, padx=3, sticky = tk.E)
        frameCol += 1

        # button for generating star data
        self.genStarDataButton = ttk.Button(ef, text="Star Data", command = self.genStarDataCallback,
                padding = 3)
        self.genStarDataButton.grid(row = frameRow, column = frameCol, pady=3, padx=3, sticky = tk.E)
        frameCol += 1

        currentRow += 1
        currentCol = 0
        # now tables with data (placed inside frame so we can control table
        # placement within parent frame more easily)
        tf = ttk.Frame(self, padding = 5)
        tf.grid(row = currentRow, column = currentCol, sticky = tk.W+tk.E)
        tfRow = 0
        tfCol = 0

        # self.dataTableFrame = ttk.Frame(self, borderwidth = 3, relief = tk.GROOVE, padding = 10)
        frameLabel = ttk.Label(tf, class_ = 'LabelFrameLabel', text = 'Rise, Set & Transits')
        self.dataTableFrame = ttk.LabelFrame(tf, labelwidget = frameLabel, padding = 10)
        self.dataTableFrame.grid(row = tfRow, column = tfCol,  rowspan = 2, padx = 10, pady = 10)

        dtf = self.dataTableFrame   # just to save typing...

        # header row
        ttk.Label(dtf, text = 'Sun', class_ = 'TableHeader').grid(row = 0, column = 1, sticky = tk.W+tk.E)
        ttk.Label(dtf, text = 'Moon', class_ = 'TableHeader').grid(row = 0, column = 2, sticky = tk.W+tk.E)

        # first row labels...
        for i in range(len(self.tableRowLabel)):
            ttk.Label(dtf, text = self.tableRowLabel[i], class_ = 'TableRowLabel').grid(row = i+1, column = 0, sticky = tk.E)

        # ... then sun data...
        for i in range(len(self.tableRowLabel)):
            key = self.tableDataKeyMap[i]['sun']
            self.cVarDictSun[key] = tk.StringVar()
            if key == 'sd':
                ttk.Label(dtf, textvariable = self.cVarDictSun[key]).grid(row = i+1,
                        column = 1 )
            else:
                ttk.Label(dtf, textvariable = self.cVarDictSun[key], class_ = 'TableCell').grid(row = i+1,
                        column = 1, sticky = tk.E)

        # ... and finally moon data...
        for i in range(len(self.tableRowLabel)):
            key = self.tableDataKeyMap[i]['moon']
            if key != None:
                self.cVarDictMoon[key] = tk.StringVar()
                if key == 'sd':
                    ttk.Label(dtf, textvariable = self.cVarDictMoon[key]).grid(row = i+1,
                            column = 2)
                else:
                    ttk.Label(dtf, textvariable = self.cVarDictMoon[key],
                            class_ = 'TableCell').grid(row = i+1,
                            column = 2, sticky = tk.E)

        tfCol += 1
        # frame for EoT:
        frameLabel = ttk.Label(tf, class_ = 'LabelFrameLabel', text = 'Equation of Time')
        self.eotFrame = ttk.LabelFrame(tf, labelwidget = frameLabel, padding = 10)
        self.eotFrame.grid(row = tfRow, column = tfCol, padx = 10, pady = 10, sticky = tk.NW+tk.E)
        frameRow = 0
        ttk.Label(self.eotFrame, text = "GAT - UT at local noon:", class_ = 'TableCellNoBorder').grid(row = frameRow,
                column = 0, sticky = tk.W)
        self.cVarDictSun['eot'] = tk.StringVar()
        ttk.Label(self.eotFrame, textvariable = self.cVarDictSun['eot'],
                class_ = 'TableCellNoBorder').grid(row = frameRow, column = 1, sticky = tk.E)
        frameRow += 1

        tfRow += 1

        # frame for Moon stuff:
        frameLabel = ttk.Label(tf, class_ = 'LabelFrameLabel', text = 'Moon Phase')
        self.moonFrame = ttk.LabelFrame(tf, labelwidget = frameLabel, padding = 10)
        self.moonFrame.grid(row = tfRow, column = tfCol, padx = 10, pady = 10, sticky = tk.NW+tk.E+tk.S)
        frameRow = 0
        for key in ['prev_new', 'prev_full', 'next_new', 'next_full', 'age']:
            ttk.Label(self.moonFrame, text = "%s:            " % self.moonLabelMap[key],
                    class_ = 'TableCellNoBorder').grid(row = frameRow,
                    column = 0, sticky = tk.W)
            self.cVarDictMoon[key] = tk.StringVar()
            ttk.Label(self.moonFrame, textvariable = self.cVarDictMoon[key], class_ = 'TableCellNoBorder').grid(row = frameRow,
                    column = 1, sticky = tk.E )
            frameRow += 1

        # update all display widgets from data attributes
        self.attr2table()


    def updateDataCallback(self):
        """Updates lat, lon, date from entry fields, calls celnav's calcData()
        to calculate rise/set/transit etc. and then updates data table.
        """
        self.entry2attr()
        self.calcData()
        self.attr2table()


    def attr2table(self):
        """Refreshes values displayed in table from celnav.SunMoonRiseSet attributes
        """

        # ... then sun data...
        for i in range(len(self.tableRowLabel)):
            key = self.tableDataKeyMap[i]['sun']
            if key == 'sd':
                self.cVarDictSun[key].set("%4.1f'"% self.sunData[key].degMin[1])
            elif self.sunData[key] != None:
                self.cVarDictSun[key].set("%04d/%02d/%02d - %02d:%02d" % (self.sunData[key][0],
                        self.sunData[key][1], self.sunData[key][2],
                        self.sunData[key][3], self.sunData[key][4]))
            else:
                self.cVarDictSun[key].set("n/a")

        # ... and finally moon data...
        for i in range(len(self.tableRowLabel)):
            key = self.tableDataKeyMap[i]['moon']
            if key == 'sd':
                self.cVarDictMoon[key].set("%4.1f'"% self.moonData[key].degMin[1])
            elif key != None:
                if self.moonData[key] != None:
                    self.cVarDictMoon[key].set("%04d/%02d/%02d - %02d:%02d" % (self.moonData[key][0],
                            self.moonData[key][1], self.moonData[key][2],
                            self.moonData[key][3], self.moonData[key][4]))
                else:
                    self.cVarDictMoon[key].set("n/a")

        # text to the right of main table (EoT, Moon phases):
        eot = self.sunData['eot']   # tuple (min, sec, sign)
        try:
            self.cVarDictSun['eot'].set("%-02dm %02ds" % (eot[0]*eot[2],
                eot[1]))
        except:
            self.cVarDictSun['eot'].set("n/a")


        # Moon phases:
        for key in ['prev_new', 'prev_full', 'next_new', 'next_full']:
            self.cVarDictMoon[key].set("%04d/%02d/%02d" %
                    (self.moonData[key][0], self.moonData[key][1], self.moonData[key][2]))

        self.cVarDictMoon['age'].set("%2d days" % self.moonData['age'])


    def attr2entry(self):
        """Updates entry fields with corresponding attribute values
        """
        self.latEntry.set(celnav.Angle(degrees(self.observer.lat)).degMin)
        self.lonEntry.set(celnav.Angle(degrees(self.observer.lon)).degMin)
        self.utEntry.set(self.ut)


    def entry2attr(self):
        """Updates self.observer's lat, lon and date attributes from entry
        fields. Will set date to local midnight at lon in UT.
        """
        lat = self.latEntry.get()
        self.observer.lat = radians((lat[0]+lat[1]/60.0)*lat[2])
        lon = self.lonEntry.get()
        self.observer.lon = radians((lon[0]+lon[1]/60.0)*lon[2])

        self.ut = self.utEntry.get()


    def genStarDataCallback(self):
        """Creates a celnav.StarFinder object with self.date, self.lat and
        self.lon and writes star data as a tab-separated text file. User will
        be prompted for filename and directory. Uses global celnav.starList.
        """
        global TMP_DIR, CSV_COLSEP

        colSep = CSV_COLSEP
        colList = [ 'Star', 'SHA', 'Dec', 'Alt', 'Az', 'Mag', 'SHA', 'Dec', 'Alt', 'Az' ]

        self.updateDataCallback()                               # make sure current ut/lat/lon are also
                                                                # reflected in table display
        sf = celnav.StarFinder(celnav.starList, lat = degrees(self.observer.lat),
                lon = degrees(self.observer.lon), ut = self.ut)

        fileName = "star_data_%04d%02d%02d-%02d%02d%02dUT.txt" % (sf.ut)
        outFilePath = os.path.join(TMP_DIR, fileName)
        outFile = open(outFilePath, 'w')

        # write ut and lat/lon
        timeStr = '%04d/%02d/%02d-%02d:%02d:%02dUT' % (sf.ut)
        outFile.write('%s - %s : %s\n' % (timeStr, celnav.Angle(degrees(self.observer.lat)).latStr(),
            celnav.Angle(degrees(self.observer.lon)).lonStr()))
        outFile.write('\n')

        # write column headingsa
        hdr = colList[0]
        for c in colList[1:]: hdr += '%s%s' % (colSep, c)
        outFile.write('%s\n' % hdr)

        for key in sf.starData:
            sd = sf.starData[key]
            line = key
            line += '%s%.6f' % (colSep, sd['sha'].decD)
            line += '%s%.6f' % (colSep, sd['dec'].decD)
            line += '%s%.6f' % (colSep, sd['alt'].decD)
            line += '%s%.6f' % (colSep, sd['az'].decD)
            line += '%s%.1f' % (colSep, sd['mag'])
            line += '%s%s' % (colSep, sd['sha'].absStr())
            line += '%s%s' % (colSep, sd['dec'].latStr())
            line += '%s%s' % (colSep, sd['alt'].signStr())
            line += '%s%s' % (colSep, sd['az'].intStr())
            outFile.write('%s\n' % line)

        outFile.close()

        os.spawnv(os.P_NOWAIT, SPREADSHEET_PATH, [SPREADSHEET_PATH, outFilePath])


    def genAlmPgCallback(self):
        """Creates a celnav.AlmanacPage object with self.date and writes
        almanac data as a tab-separated text file in a temporary directory.
        """
        global TMP_DIR, CSV_COLSEP

        colSep = CSV_COLSEP

        self.updateDataCallback()                               # make sure current ut/lat/lon are also
                                                                # reflected in table display
        alPg = celnav.AlmanacPage(self.ut[:3])

        fileName = "almanac_page_%04d-%02d-%02d.txt" % (alPg.date[:3])
        outFilePath = os.path.join(TMP_DIR, fileName)
        outFile = open(outFilePath, 'w')

        # assemble string for header lines:
        line1 = ""
        line2= ""
        for b in self.alPgBodySeq:
            if b == 'aries':
                line1 += "%s%s" % (colSep, self.alPgBodyLabelMap['aries'])
                line2 += "%s%s" % (colSep, self.alPgKeyLabelMap['gha'])
            else:
                line1 += "%s%s%s%s" % (colSep, self.alPgBodyLabelMap[b], colSep, self.alPgBodyLabelMap[b])
                line2 += "%s%s%s%s" % (colSep, self.alPgKeyLabelMap['gha'], colSep, self.alPgKeyLabelMap['dec'])
                if b == 'moon':
                    line1 += "%s%s" % (colSep, self.alPgBodyLabelMap['moon'])
                    line2 += "%s%s" % (colSep, self.alPgKeyLabelMap['hp'])

        # add UT in front and repeat headings (once for angles as decimal
        # fractions and once as formatted strings)
        line1 = "UT%s%s" % (line1, line1)
        line2 = "[hrs]%s%s" % (line2, line2)

        outFile.write("%s\n%s\n" % (line1, line2))

        # now data records:
        for h in range(24):
            line1  = ""
            # first with degrees as decimal fractions...
            for b in self.alPgBodySeq:
                if b == 'aries':
                    line1 += "%s%f" % (colSep, alPg.__dict__['aries'][h].decD)
                else:
                    line1 += "%s%f%s%f" % (colSep, alPg.__dict__[b]['gha'][h].decD, colSep, alPg.__dict__[b]['dec'][h].decD)
                    if b == 'moon':
                        line1 += "%s%f" % (colSep, alPg.__dict__['moon']['hp'][h].decD)

            # ...then the same stuff again with angles as formatted strings
            for b in self.alPgBodySeq:
                if b == 'aries':
                    line1 += "%s%s" % (colSep, alPg.__dict__['aries'][h].absStr())
                else:
                    line1 += "%s%s%s%s" % (colSep, alPg.__dict__[b]['gha'][h].absStr(),
                            colSep, alPg.__dict__[b]['dec'][h].latStr())
                    if b == 'moon':
                        line1 += "%s%s" % (colSep, alPg.__dict__['moon']['hp'][h].absStr())

            line1 = "%02d%s" % (h, line1)
            outFile.write("%s\n" % line1)

        outFile.close()

        os.spawnv(os.P_NOWAIT, SPREADSHEET_PATH, [SPREADSHEET_PATH, outFilePath])


class AppPlanetFinder(ttk.Frame, celnav.PlanetFinder, classprint.AttrDisplay):
    """Subclasses celnav.PlanetFinder and adds interface logic
    """
    # sequence with body names (used as keys to celnav.PlanetFinder.planets)
    planetList = ['Moon', 'Venus', 'Mars', 'Jupiter', 'Saturn']

    # parameters for canvas sizing and element placement
    ch = 350                # canvas height
    cw = 900                # canvas width
    rLblNW = (10, 95)       # NW corner for row labels (planets)
    rLblYStep = 50          # vertical step between row labels
    hrGrNW = (100, 80)      # NW corner for hr grid lines
    hrGrLblNW = (100, 70)   # NW corner for hr grid label
    hrGrXStep = 25          # horizontal step between grid lines
    xL = 24 * hrGrXStep     # total width of grid

    localMidnLblS = (hrGrNW[0] + xL/2, 40)
                            # anchor point for "Local midnight..." heading

    amplLblS = (hrGrNW[0] + xL + 80, hrGrLblNW[1])
                            # anchor point for "Amplitude" column heading
    maxAltLblS = (amplLblS[0] + 80,  hrGrLblNW[1])
                            # anchor point for "Max. Alt." column heading

    def __init__(self, master = None):

        ttk.Frame.__init__(self, master)
        self.grid(sticky = tk.N+tk.S+tk.W+tk.E)

        ut = dt.datetime.utcnow().timetuple()[:6]
        celnav.PlanetFinder.__init__(self, lat = INITIAL_LAT, lon = INITIAL_LON, ut = ut)

        # local time offset at lon incl. fractional hrs
        self.localHrOffset = degrees(self.observer.lon) / 15.0

        # time zone offset in whole hrs (west lon -> tzOffset < 0)
        self.tzHrOffset = int(round(self.localHrOffset))

        # create and place entry widgets and buttons:
        currentRow = 0
        currentCol = 0

        ef = ttk.Frame(self, padding = 5)
        ef.grid(row = currentRow, column = currentCol, sticky = tk.W+tk.E)
        frameRow = 0
        frameCol = 0
        # date entry:
        self.utEntry = TimeEntry(ef, prefixLabel = "UT:", padding = 5)
        self.utEntry.grid(row = frameRow, column = frameCol)
        frameCol += 1

        # lat / lon for which rise/set/transit data is requested
        self.latEntry = AngleEntry(ef, posValidateStr = r"^[Nn]$", negValidateStr = r"^[Ss]$", prefixLabel = "Lat:",
                padding = 5)
        self.latEntry.grid(row = frameRow, column = frameCol, sticky = tk.W)
        frameCol += 1

        self.lonEntry = AngleEntry(ef, posValidateStr = r"^[Ee]$", negValidateStr = r"^[Ww]$", prefixLabel = "Lon:",
                padding = 5)
        self.lonEntry.grid(row = frameRow, column = frameCol, sticky = tk.W)
        frameCol += 1

        # initialize entry fields:
        self.__attr2entry()

        # button for data update
        self.updateButton = ttk.Button(ef, text="Update Display",
                command = self.__updateDataCallback, padding = 3)
        self.updateButton.grid(row = frameRow, column = frameCol, pady=3, sticky = tk.E)
        frameCol += 1

        currentRow += 1

        # now: the canvas...
        self.cv = tk.Canvas(self, bg = '#ffffff', width = self.cw, height = self.ch)
        self.cv.grid(sticky = tk.N+tk.S+tk.W+tk.E, padx= 10, pady = 5)

        # place planet names as row headings
        for i, p in enumerate(self.planetList):
            self.cv.create_text(self.rLblNW[0], self.rLblNW[1] + i*self.rLblYStep,
                    text = p, font = 'lucidatypewriter 10 bold', anchor = tk.W)

        # Amplitude and max. alt column headings to the right of the chart
        self.cv.create_text(*self.amplLblS, text = 'Amplitude',
                anchor = tk.S)
        self.cv.create_text(*self.maxAltLblS, text = 'Max. Alt.',
                anchor = tk.S)

        self.__drawData()


    def __drawData(self):
        """Draws/updates canvas elements that change with input data.
        """
        # delete local midnight heading:
        self.cv.delete('localMidnHdg')

        # local midnight:
        if self.observer.date > 0:
            self.cv.create_text(*self.localMidnLblS, text =
                    'Local midnight: %s UT' % self.observer.date, anchor =
                    tk.S, tags = 'localMidnHdg')

        # delete old apmlitudes and transits alts:
        self.cv.delete('amplVal')
        self.cv.delete('maxAltVal')

        # write amplitudes and alt. at transit:
        for i, p in enumerate(self.planetList):
            if p != 'Moon':

                try:
                    ampl = celnav.Angle(90 - self.planets[p]['rise_az'].decD)
                    self.cv.create_text(self.amplLblS[0], self.rLblNW[1]+i*self.rLblYStep,
                            text = "%3s%s" % (ampl.latStrDeg(), u'\xb0'), tags = 'amplVal')
                except:  # None value in dictionary
                    self.cv.create_text(self.amplLblS[0], self.rLblNW[1]+i*self.rLblYStep,
                            text = "---", tags = 'amplVal')
                try:
                    self.cv.create_text(self.maxAltLblS[0], self.rLblNW[1]+i*self.rLblYStep,
                            text = "%2s%s" % (self.planets[p]['mer_pass_alt'].intStr(),
                                u'\xb0'), tags = 'maxAltVal')
                except:  # None value in dictionary
                    self.cv.create_text(self.maxAltLblS[0], self.rLblNW[1]+i*self.rLblYStep,
                            text = "--", tags = 'maxAltVal')

        # delete shaded twilight and night rectangles:
        self.cv.delete('twlShades')

        # shaded rectangles for twilight and night:
        xPMtwlStart =   self.dt2dx(self.twilight['pm_start'], self.xL)
        xPMtwlEnd   =   self.dt2dx(self.twilight['pm_end'], self.xL)
        xAMtwlStart =   self.dt2dx(self.twilight['am_start'], self.xL)
        xAMtwlEnd   =   self.dt2dx(self.twilight['am_end'], self.xL)

        # length of grid lines
        lineLen = (len(self.planets) - 1) * self.rLblYStep + self.rLblNW[1] - self.hrGrNW[1] + 20

        # start/end values might be none for events above the arctic circle:
        try:
            self.cv.create_rectangle(xPMtwlStart+self.hrGrNW[0],
                    self.hrGrNW[1], xPMtwlEnd+self.hrGrNW[0], self.hrGrNW[1] +
                    lineLen, fill = '#aaaaaa', width = 0, tags = 'twlShades')
        except:
            pass
        try:
            self.cv.create_rectangle(xPMtwlEnd+self.hrGrNW[0], self.hrGrNW[1],
                    xAMtwlStart+self.hrGrNW[0], self.hrGrNW[1] + lineLen, fill
                    = '#888888', width = 0, tags = 'twlShades')
        except:
            pass
        try:
            self.cv.create_rectangle(xAMtwlStart+self.hrGrNW[0],
                    self.hrGrNW[1], xAMtwlEnd+self.hrGrNW[0], self.hrGrNW[1] +
                    lineLen, fill = '#aaaaaa', width = 0, tags = 'twlShades')
        except:
            pass

        # delete grid lines and hr labels:
        self.cv.delete('gridLine')
        self.cv.delete('hrLabel')

        # (re-)draw grid lines and hr labels:
        for i in range(25):
            hr = (i+12-self.tzHrOffset)%24
            x = self.hrGrLblNW[0] + i*self.hrGrXStep
            self.cv.create_text(x, self.hrGrLblNW[1], text = '%02d' % hr,
                    anchor = tk.S, tags = 'hrLabel')
            self.cv.create_line(x, self.hrGrNW[1], x, self.hrGrNW[1]+lineLen,
                    dash = (3, 3), fill = '#666666', tags = 'gridLine')

        # and now the Gantt bars: delete
        self.cv.delete('ganttBar')

        # and now the Gantt bars: (re-)draw
        for i, p in enumerate(self.planetList):
            try:
                xStart = self.hrGrNW[0] + self.dt2dx(self.planets[p]['rise'], self.xL)
            except:
                xStart = None
            try:
                xEnd = self.hrGrNW[0] + self.dt2dx(self.planets[p]['set'], self.xL)
            except:
                xEnd = None

            if xStart == None and xEnd != None:     # already up and doesn't rise but sets
                self.cv.create_line(self.hrGrNW[0], self.rLblNW[1] +
                        i*self.rLblYStep, xEnd, self.rLblNW[1] +
                        i*self.rLblYStep, fill = '#f6ca0e', width = 8, tags =
                        'ganttBar')

            elif xStart != None and xEnd == None:   # rises but doesn't set
                self.cv.create_line(xStart, self.rLblNW[1] +
                        i*self.rLblYStep, selfhrGrNW[0]+self.xL, self.rLblNW[1] +
                        i*self.rLblYStep, fill = '#f6ca0e', width = 8, tags =
                        'ganttBar')

            elif xStart == None and xEnd == None:
                pass

            elif xStart < 0 and xEnd >= 0:
                xStart = 0
                self.cv.create_line(xStart, self.rLblNW[1] + i*self.rLblYStep, xEnd,
                        self.rLblNW[1] + i*self.rLblYStep, fill = '#f6ca0e',
                        width = 8, tags = 'ganttBar')

            elif xEnd > self.xL+self.hrGrNW[0] and xStart <= self.xL+self.hrGrNW[0]:
                xEnd = self.xL
                self.cv.create_line(xStart, self.rLblNW[1] + i*self.rLblYStep, xEnd,
                        self.rLblNW[1] + i*self.rLblYStep, fill = '#f6ca0e',
                        width = 8, tags = 'ganttBar')

            elif xStart <= xEnd:
                self.cv.create_line(xStart, self.rLblNW[1] + i*self.rLblYStep, xEnd,
                        self.rLblNW[1] + i*self.rLblYStep, fill = '#f6ca0e',
                        width = 8, tags = 'ganttBar')

            else:           # rise and set swapped - need two bars
                self.cv.create_line(self.hrGrNW[0], self.rLblNW[1] + i*self.rLblYStep,
                        xEnd, self.rLblNW[1] + i*self.rLblYStep, fill = '#f6ca0e',
                        width = 8, tags = 'ganttBar')
                self.cv.create_line(xStart, self.rLblNW[1] + i*self.rLblYStep,
                        self.hrGrNW[0]+self.xL, self.rLblNW[1] + i*self.rLblYStep,
                        fill = '#f6ca0e', width = 8, tags = 'ganttBar')


    def dt2dx(self, t, xL):
        """Returns the x-coordinate on the canvas that corresponds to t which
        is a tuple (nY, M, D, h, m, s). xL is the total length of the 24 hr
        Gantt chart.
        Calculates:
            t - (local midnight at lon)
            + 0.5 days
            + (tzHrOffset - localHrOffset)
        in days to get value between 0 and 1 (if t within that 24 hr range)
        that represents the fraction of that 24hr period counted from the
        beginning of the hr grid.
        Returns None if datetime raises a TypeError on being passed t or
        self.observer.date (t would be None for example for
        sunrise/-set/twilight events above the arctic cricle).
        """
        od = self.observer.date.tuple()
        od = od[:5] + (int(od[5]),)

        try:
            deltaT = dt.datetime(*t) - dt.datetime(*od)
        except TypeError:
            return None

        # convert timedelta object to days and offset to -0.5 = 0
        deltaD = (deltaT.days + deltaT.seconds / (3600.0 * 24)
                + deltaT.microseconds / (3600e6 * 24) + 0.5)

        # adjust for fractional hrs difference between time zone (= grid) and
        # true local time at lon
        deltaD += (self.tzHrOffset - self.localHrOffset) / 24.0

        return int(round(xL * deltaD))


    def __entry2attr(self):
        """Updates self.observer's lat, lon and date attributes from entry
        fields. Will set date to local midnight at lon in UT.
        """
        lat = self.latEntry.get()
        self.observer.lat = radians((lat[0]+lat[1]/60.0)*lat[2])
        lon = self.lonEntry.get()
        self.observer.lon = radians((lon[0]+lon[1]/60.0)*lon[2])

        self.ut = self.utEntry.get()


    def __attr2entry(self):
        """Updates entry fields with corresponding attribute values
        """
        self.latEntry.set(celnav.Angle(degrees(self.observer.lat)).degMin)
        self.lonEntry.set(celnav.Angle(degrees(self.observer.lon)).degMin)
        self.utEntry.set(self.ut)


    def __updateDataCallback(self):

        self.__entry2attr()
        self.calcData()

        self.__attr2entry()

        # local time offset at lon incl. fractional hrs
        self.localHrOffset = degrees(self.observer.lon) / 15.0

        # time zone offset in whole hrs (west lon -> tzOffset < 0)
        self.tzHrOffset = int(round(self.localHrOffset))

        self.__drawData()


class AppAlmanacPageTV(ttk.Frame, celnav.AlmanacPage, classprint.AttrDisplay):
    """Customizes celnav.AlmanacPage to provide ttk.Frame with entry widget for
    date and Treeview widget to display tabular NA data for Sun, Moon, and
    planets as well as GHA Aries.
    NOTE: scrollbars don't wotk correctly - don't use this class
    """

    # identifier strings for columns in Treeview widget (24 hrs):
    colID = []     # first column contains key (e.g. 'GHA')
    for h in range(24):
        colID.append("%02d" % h)

    keyLabelMap = {
            'gha' : 'GHA',
            'dec' : 'Dec',
            'hp' : 'HP'
            }

    # body sequence used to iterate over the differemnt planed data
    # dictionaries via self.__dict__
    bSeq = ('aries', 'sun', 'moon', 'venus', 'mars', 'jupiter', 'saturn')

    bLabelMap = {
            'aries' : 'Aries',
            'sun' : 'Sun',
            'moon' : 'Moon',
            'venus' : 'Venus',
            'mars' : 'Mars',
            'jupiter' : 'Jupiter',
            'saturn' : 'Saturn'
            }

    def __init__(self, master = None):
        """Calls parent constructors and generates and grids widgets.
        """
        ttk.Frame.__init__(self, master, width = 800, height = 600)
        self.grid_propagate(0)
        celnav.AlmanacPage.__init__(self)       # will initialize date with datetime.utcnow()

        # create and place widgets
        currentRow = 0
        currentCol = 0

        # ttk.Label(self, class_ = "FrameTitle", text = "Almanac\nPage").grid(row = currentRow, column = currentCol, sticky = tk.W)
        currentCol += 1

        # UT date entry:
        self.utEntry = TimeEntry(self, prefixLabel = "UT:\n[Y/M/D-h:m:s]", padding = 5)
        self.utEntry.grid(row = currentRow, column = currentCol, sticky = tk.W)
        currentCol += 1

        currentRow += 1
        currentCol = 1

        # create and grid treeview widget
        self.tv = ttk.Treeview(self, column = self.colID, displaycolumns = '#all',
                height = len(self.bSeq)*3, selectmode = 'extended')
        self.tv.grid(row = currentRow, column = currentCol)
        self.tv.grid_propagate(0)


        # set up columns
        self.tv.column('#0', width = 80)
        for cID in self.colID:
            self.tv.column(cID, anchor = tk.E, width = 80)
            self.tv.heading(cID, anchor = tk.CENTER, text = cID)

        # and now... insert rows..
        for b in self.bSeq:

            # insert parent:
            self.tv.insert('', 'end', iid = b, text = self.bLabelMap[b], tag = 'body')

            # and its children:
            ghaList = []        # value string with formatted entries to be added
            decList = []        # value string with formatted entries to be added
            hpList = []         # value string with formatted entries to be added
            if b == 'aries':
                # assemble formated value string
                for h in range(24):
                    ghaList.append("%3d %04.1f" % (self.aries[h].degMin[0], self.aries[h].degMin[1]))

                self.tv.insert(b, 'end', iid = b+'gha', text = self.keyLabelMap['gha'],
                        values = ghaList, tag = 'data')
            else:
                dDict = self.__dict__[b]
                # assemble formated value strings
                for h in range(24):
                    # first GHA:
                    ghaList.append("%3d %04.1f" % (dDict['gha'][h].degMin[0], dDict['gha'][h].degMin[1]))
                    # then Dec:
                    if dDict['dec'][h].degMin[2] == -1: signStr = "S"
                    else: signStr = "N"
                    decList.append("%s %2d %04.1f" % (signStr, dDict['dec'][h].degMin[0], dDict['dec'][h].degMin[1]))
                    if b == 'moon':     # also HP
                        hpList.append("%04.1f" % (dDict['hp'][h].decD * 60))

                self.tv.insert(b, 'end', iid = b+'gha', text = self.keyLabelMap['gha'], values = ghaList, tag = 'data')
                self.tv.insert(b, 'end', iid = b+'dec', text = self.keyLabelMap['dec'], values = decList, tag = 'data')

                if b == 'moon':     # also HP
                    self.tv.insert(b, 'end', iid = b+'hp', text = self.keyLabelMap['hp'], values = hpList, tag = 'data')

        self.tv.configure(displaycolumns = [ i for i in range(6) ])

        # add scrollbars
        self.scrollX = tk.Scrollbar(self, orient = tk.HORIZONTAL, command = self.tv.xview)
        self.scrollX.grid(row = currentRow+1, column = currentCol, sticky = tk.E+tk.W)
        self.tv['xscrollcommand'] = self.scrollX.set
        # bself.scrollY = tk.Scrollbar(self, orient = tk.VERTICAL, command = self.tv.yview)
        # self.scrollY.grid(row = currentRow, column = currentCol+1, sticky = tk.N+tk.S)
        # self.tv['yscrollcommand'] = self.scrollY.set

        self.tv.configure(displaycolumns = '#all')


if __name__ == '__main__':
    #    import doctest
    #    doctest.testmod( )

    root = tk.Tk()
    app = AppAlmanacPageTV(root)
    app.grid()

    app.mainloop()
