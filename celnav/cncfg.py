"""cncfg: reads INI_FILE in INI_DIR and exports a ConfigParser.ConfigParser
object named cncfg.  This object can be used by other modules in this package.
INI_FILE sections are assumed to equal module names but this is not strictly
neccessary as long as the modules using cncfg look for the right stuff.
"""

import configparser
import os
import tkinter.messagebox as tMB
INI_DIR = os.path.expandvars("$HOME/.celnav")
INI_FILE = 'celnav.ini'

cncfg = configparser.ConfigParser()

def build_cfg():

    global cncfg

    # read ini file:
    try:
        iniPath = os.path.join(INI_DIR, INI_FILE)
        cncfg.readfp(open(iniPath))
    except:
        warningStr = "Could not read configuration file %s" % iniPath
        tMB.showwarning(title = "CelNav Warning", message = warningStr, icon = tMB.WARNING)


build_cfg()
del build_cfg


if __name__ == '__main__':

    for s in cncfg.sections():
        for o in cncfg.options(s):
            v = cncfg.get(s, o)
            print(s, o, v)

