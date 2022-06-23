# SSAVE

Author: Amlan Talukder

Date: June 23, 2022

SSAVE is a software used to detect and visualize sleep cycles with spectrogram from EEG data. 
It is developed by the Dr. Leping Li's group of BCBB branch NIH/NIEHS.

INSTALLATION
--------------------------------------------------------------------------------------------
   1. Install python 3.6 or higher
   2. Install the following python packages:
        a) numpy
        b) matplotlib
        c) mne
        d) flask (for web verison)

EXECUTION
--------------------------------------------------------------------------------------------------------------------------------------

   1. For desktop application, execute "python3 app_desktop.py"
   2. For the web application, the web server needs to be running. To run the web server, 
        a) execute "python3 app_web.py <host_name> <port_number>" with an host name (or ip-address) and port number.
        b) open the <host_name>:<port_number> in a web browser.

LICENSE & CREDITS
-------------------------------------------------------------------------------------------------
The software is a freely available for academic use.
please contact Leping li (li3@niehs.nih.gov) for further information. 

CONTACT INFO
-------------------------------------------------------------------------------------------------
If any issues arise, please feel free to contact us:
Amlan Talukder (amlan.talukder@nih.gov)
Leping Li (li3@niehs.nih.gov)
Yuanyuan Li (yuanyuan.li@nih.gov)