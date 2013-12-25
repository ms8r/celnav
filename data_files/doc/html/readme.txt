================================================================================
                CelNav - Electronic Almanac and Sight Reduction
================================================================================

CelNav is a simple utility to support celestial navigation on a small boat. It
provides the data listed on the daily pages of the Nautical Almanac as well as
functionality for sight reduction and calculation of a fix from two LOPs taken
in relatively short succession (the program will correct for motion of observer
between the sights for the LOPs). It uses the PyEphem package to calculate
ephemeris data for Sun, Moon, navigational planets and stars
(http://rhodesmill.org/pyephem/index.html). PyEphem must be installed in order
for CelNav to run (it is available for free at the URL listed above). In
addition Python 2.6 or newer must be installed with Tkinter and its ttk
("Themed Tkinter") descendant.

This package is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.


-------------------------------------------------------------------------------
CONTENTS
-------------------------------------------------------------------------------
The archive file contains the source distribution for CelNav. It contains the
following file in addition to this README:

Root folder
-----------

setup.py        -   Python Distutils installation script. See below under
                    "Installation".

cnscript.py     -   Python script with a simple main driver that will run the
                    application. Will be installed in /opt/celnav. While you
                    can launch the application from the command line with
                    'python cnscript.py' it is recommended to use the shell
                    script 'nxcn' which performs some additional housekeeping
                    (see below under 'data files').  

PKG-INFO        ⁻   Package info: some meta data about this package.


Subfolder ./celnav
------------------
This folder contains the Python package consisting of the following modules:

celnav.py       -   Implements classes to calculate, store and manipulate
                    almanac and sight reduction data. celnav.py does not
                    contain any UI logic. 

cnapp.py        -   Implements the application and GUI by mixing classes from
                    celnav.py with Tkinter/ttk widget classes.

starcat.py      -   Contains the base data required by PyEphem for ephemeris
                    calculations for the 57 navigational stars plus Polaris.
                    Used instead of PyEphem's star.py which misses about 20 of
                    the navigational stars. 

cncfg.py        -   Uses a ConfigParser instance to read celnav.ini
                    configuration file and to provide access to its parameter
                    values. Imported by other modules to get access to config
                    parameters. 

classprint.py   -   Contains an inheritable print overload method that displays
                    instances with their class names and a name=value pair for
                    each attribute stored on the instance itself. Mixed into
                    celnav and cnapp classes to aid testing.

The package will be installed into the directory that contains 3rd party
distributions in your Python installation.


Subfolder ./data_files
----------------------

celnav.ini      -   Configuration file for setting application parameters such
                    as path names and initial latitude and longitude values.
                    Will be installed into $HOME/.celnav/

celnav.cfg      -   Xdefaults-type configuration file, defining options for the
                    Tkinter widgtes used in the GUI. Will be installed into
                    $HOME/.celnav. Path and filename can be changed in
                    celnav.ini if required.

doc/             -  Folder with html help files. Contents will be placed into
                    /usr/local/share/doc/celnav.  Can be accessed via the
                    application's Help menu.

nxcn            -   Minimalistic shell script that executes 'python
                    /opt/celnav/cnscript.py'. It redirects/appends stderr to
                    $HOME/.celnav/celnav.err and puts a timestamp in that file
                    before launching the application. It will create the
                    directory if it doesn't exist. If the files '/etc/nx.lat'
                    and '/etc/nx.lon' exist it is assumed that these contain
                    most recent values for latitude and longitude in degrees
                    (incl. decimal fractions). This is the case under
                    Navigatrix, a common Linux distribution among cruisers (see
                    http://navigatrix.net). If these files are found, the nxcn
                    shell script will use lat/lon values from these files to
                    update the INITIAL_LAT and INITIAL_LON parameters in
                    celnav.ini prior to launching the application.

celnav.desktop  -   LXDE desktop file. Will be installed in
                    /usr/local/share/applications and points to the nxcn shell
                    script which is assumed to reside in /usr/local/bin and
                    defines application category ("Navigation") and icon for
                    the LXDE environment. Can be ignored if not running under
                    LXDE. 

navtriangle.png -   48x48 icon image. celnav.desktop assumes this file resides
                    in /usr/local/share/icons/.


-------------------------------------------------------------------------------
INSTALLATION
-------------------------------------------------------------------------------

As mentioned above, Python 2.6 or later, Tkinter plus ttk and PyEphem must be
installed for CelNav to run (the program has been tested under Python 2.6.5.).
To install the celnav pacakge and its auxilliary files:

(1) Extract the contents of the archive file into any directory, preserving the
    folder structure.

(2) Open a terminal in the folder CelNav-0.2.0 and run

        python setup.py install

    at the command line. This will install the celnav package and place the
    auxilliary files (e.g. icon, shell script) in their respective target
    directories. Note that - depending on your system setup - you may need to
    run the above command as root. In this case type

        sudo python setup.py install

    at the command prompt.
    
(3) If the auxilliary files 

        /usr/local/bin/nxcn                             (shell script)
        /usr/local/share/applications/celnav.desktop    (LXDE desktop file)
        /usr/local/share/icons/navtriangle.png          (icon image file)

    already exist on the target platform, these files will not be installed.
    This is to avoid accidental overwriting of other files with these same
    names.  In this case the setup.py installation script will print a message
    which of these files have been skipped during installation and ask you to
    manually check whether you want to overvrite the exisiting files. In this
    case you can simply copy the file(s) from the package into their respective
    target directories. 

    Any existing files in /opt/celnav will be moved into a subdirectory
    "moved_by_CelNav_0.2.0".


That's it. A few notes:

+   Whenever a fix is calculated, CelNav will log all data for that fix to a
    file. The name for that file is set via the parameter LOG_FILE in
    celnav.ini (default: celnav.log). The file will be placed in the directory
    set via the variable APP_DIR in cnapp.py (default $HOME/.celnav). There is
    no housekeeping; the application will keep appending to the file. You can
    simply delete the file should it grow too big (will take a few thousand
    sights though...) and CelNav will start a fresh one.

+   CelNav can write the data contained in the "daily pages" of the Nautical
    Alamanc to a comma-separated text file (hourly GHA Aries, GHA and Dec for
    Sun, Moon and planets, plus HP for the Moon). After writing the file it
    will call the program defined by the parameter SPREADSHEET_PATH in
    celnav.ini to display the file. Default for this parameter is
    /usr/bin/gnumeric which shows the data in the Gnumeric spreadsheet
    application that is part of Navigatrix. Configure a different application
    executable (incl. path) in celnav.ini if you use a different spreadsheet
    application. You can open celnav.ini from CelNav's File menu. The program
    defined by SPREADSHEET_PATH will also be called to display star data and
    the CelNav log file (see above).

+   The parameter EDITOR_PATH in celnav.ini defines a text editor to be used
    for displaying the ini file and the error log.

+   The parameter BROWSER_PATH in celnav.ini defined the browser to be used for
    displaying the CelNav help file.


-------------------------------------------------------------------------------
USAGE
-------------------------------------------------------------------------------

Should be straight forward. The application offers three tabs:

(1) Almanac
-----------
Allows you to enter a date and a lat/lon position and will display Sun and Moon
rise/set/transit times and twighlight hours for that day. In addition it will
show the Equation of Time for that day (with negative values indicating the
apparent sun being ahead of the mean sun), the dates of previous and next full
and new moons, and how many days the moon is into its current cycle.

All dates and times on this tab are UT. If you enter a lat/lon and press
"Update Display" the times shown for the various events will be for that
position but still be expressed in UT.

Pressing the "Almanac Page" button will generate a comma-separated text file
with hourly GHA and Declination data for Aries, Sun, Moon and planets.  CelNav
will open this file in the Gnumeric spreadsheet application (or any application
specified via the SPREADSHEET_PATH parameter in celnav.ini). All angles are
displayed in degrees with decimal fractions (with the usual "S/W = -" sign
convention) as well as in the traditional Almanac format (e.g. "N 35 17.2"). 

Pressing the "Star Data" button will generate a comma-separated text file with
SHA and Declination data for the 57 navigational stars plus Polaris. The file
will also contain altitude and azimuth data for each star for the UT and
Lat/Lon entered by the user. As with the Almanac Page the file will be opened
in a spreadsheet application and can be used as a simple tool to select
suitable stars for a sight at a given UT.


(2) Planet Finder
-----------------
A visual aide for quickly checking which planets are available at given UT and
Lat/Lon entered by the user. The times during which planets will be above the
horizon will displayed in a simple Gantt chart on a 24hr grid on which twilight
periods are shaded.


(3) Sight Reduction & Fix
-------------------------
This tab allows entry of the usual data for a celestial sight and will
calculate intercept and azimuth for that sight. It will also calculate an
intercept corrected for the motion of the observer (MOO). The latter will be
used to calculate a fix from 2 LOPs as a "short run fix". 

The structure of this tab has a "Fix" at its top level. Associated with the fix
are vessel SOG and COG (used for the MOO correction of the intercept) and the
time for which the fix is to be calculated (this allows to use a time "close
to" but different from the time of sights, for example to accommodate some
plotting routine or comparison with a GPS reading.

Under the Fix you can have one or more LOPs and each LOP can have one or more
Sights. If there is only one LOP no Fix can be calculated but you can still
reduce the Sights for that LOP. The idea of multiple Sights per LOP allows you
to take a number of sights of a body in quick succession, have the application
reduce all of them, and pick for example the one with the median intercept,
thus eliminating any outliers (via the radio button selector to the right of
the Sights).

The Fix calculation performed by CelNav is a simple 2-LOP plane geometry fix
(same as you would do on a plotting sheet). The application will show an error
message if you have less or more than two LOPs and press "Calculate Fix".

