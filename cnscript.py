#! /usr/bin/python

"""main driver for celnav/cnapp - celestial navigation using PyEphem and aa;
see doc strings in celnav.py and cnapp.py for details
"""

import celnav.cnapp as cc
import tkinter as tk
    
app = cc.Application(tk.Tk())
app.winfo_toplevel().title( "%s %s" % (cc.EXT_APP_NAME, 
    cc.EXT_APP_VERSION))

app.mainloop()

