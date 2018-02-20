# SR Demo & Controller

An SR Controller BGP-LU with Segment Routing Labels

A Python Based SR and BGP Route Controller for Traffic Engineering.

To run the demo install EXABGP (version 4.0.0) along with Python 2.7.

This controller can be run on a VM or a BMS, but in addition is all dockerized
and can be run in a container (instructions below)

For details on  EXABGP refer to this link:

https://github.com/Exa-Networks/exabgp

INSTALLATION:
=============

To build your own version of the controller all you need to do is install Docker
clone the git repository:

        git clone git@github.com:russellkelly/SR_Demo_Repo.git

IMPORTANT: ! Change the srdemo.conf file to match ingress (ingress LER) router's
peering IP address.  Note:  The exabgp address, if runnning in a docker
container) will not need to be changed as the docker container runs in private
sr-net subnet and the controller (and hence the exabgp process) is given
address 192.168.1.2.

Switch to the clone directory SR_Demo_Repo

        cd SR_Demo_Repo

Then in the cloned (SR_Demo_Repo) directory run:

        make demo

This command runs build: (Builds the image sr-demo) and spawns container srdemo.
It will enter you in to the bash shell of the container.


The srdemo will delete upon exit. To stop and remove the sr-net run:

        make clean


All links in the ISIS configuration need to be configured as p2p

- isis network point-to-point

Below is some details on what each file does:


CONFIGURING AND RUNNING THE SR CONTROLLER
==========================================

Once the git repository has been cloned locally and the images and containers
installed as above and you are in the srdemo bash shell proceed with the
following steps:

Step 1: Customize the TopologyVariables.yaml File.
--------------------------------------------------

Amend the variables in the file below to match your topology :

TopologyVariables.yaml file.  (THIS IS THE ONLY FILE THAT NEEDS TO BE AMENDER)

Change the following in TopologyVariables.yaml:

The LERs to match your topology

        LERs:
          ip_address:
              - xxx.xxx.xxx.xxx
              - xxx.xxx.xxx.xxx


The ISIS-DB export router. This is in your domain will need to have
eAPI enabled (see documentation).  This router will be used for topology
(ISIS DB) export.

        ISIS-DB-Poll:
          ip_address: xxx.xxx.xxx.xxx
          user: <string>
          password: <string>

Amend the local and remote AS in this file to match your Topology

(NOTE:  The rest of the sections should not need to be changed)


Step 2:
=================================

Now one can run controller:

        make demo
        python sr_demo.py -u <eAPI username> -p <eAPI password> -a <ISIS DB Topology Export Router IP>


Now browse to the IP address of the VM or local machine where docker is installed, on port 5003

http://"localhost" or "VM IP":5001


SYSTEM RUNTIME FILES
====================


app.py
------
        Fires up a simple HTTP portal on port 5000 so one can post via the
        EXABGP API.


exabgp.env
----------
        Environmental file for exabgp.  Copied into srbase

Makefile/Dockerfile
-------------------

        For building the demo containers.


sr_demo.py
-----------
          This is the main script that is a multiprocess python program.  One
          process runs a Flask application to render the WebUI for interacting
          with the controller.  Another process continually gets the SID's from
          the domain, and announces/removes routes upon any input from user via
          Web UI, or automatically on any topology change.   File itself is
          extensively commented.

index.html
-----------
          This is the html file that builds the webpage.


images
-------
          Holds the diagrams for the original demo.  Can replace these if required.
          Note: best to amend the index.html file if you don't want these included

monitor_interface.py
--------------------
          Monitor Interfaces Command for Arista Devices.  Used in this demo to
          visulize trafficbeing engineered troughout the domain.

          This script continually monitors interfaces in one,
          or more Arista devices.

          I created this program to allow one or a number of switches to be
          monitored at once, running on-box or off, and monitoring multiple
          specifically defined interfaces or all of them, and the ability to
          define variables like packet count, min packet rate to show etc.  

          See the help below:

          Usage: monitor_interfaces.py [options]

          Options:
            -h, --help        show this help message and exit
            -b                This option enables KBps to be dispalyed.  Default is off.
            --count_packet    This option enables packet count to be dispalyed.  Default
                              is off.
            --safe            This option enables configurations to be backed up before
                              running the program and restored upon exiting (Thus
                              keeping the load-interval commands as previous).  Default
                              is off.
            -u USERNAME       Username. Mandatory option
            -p PASSWORD       Password. Mandatory option
            -l LOAD_INTERVAL  explicit interface load-interval rate. If set then every
                              interesting interface has its load-interval set, and
                              subsequently removed when packet-rate drops below 2pps.
                              Values 5-300.  By default the programs sets the system
                              default load-interval to 5
            -r PPSRATE        min packet rate.  Any interface with a rate above this
                              will report status. Default is 2 pps.
            -a HOSTNAMES      One or more hostnames (or IP addresses) of the switches to
                              poll.  Comma separated.  Mandatory option with multiple
                              arguments
            -i INTERFACES     optional argument with multiple arguments.  Ethernet Ports
                              Only- Format: Ethernet<num>, or Eth<num>, comma separated,
                              or range separated with- e.g. Eth21-45 or
                              Eth1,Eth7,Eth21-45


          As an example if I want to monitor devices lf275,fm213 but only
          interfaces Eth2,4 and range 41-48, I want to show packet count and and KBps count
          I would run the follwoing:


          python monitor_interfaces.py -u admin -p admin -r 10 -a lf275,fm213 --count_packet  -b -i Eth1,Eth2, Eth41-48


          For no KBps count and all interfaces over the rate of 10pps:

          python monitor_interfaces.py -u admin -p admin -r 10 -a lf275,fm213,fm382 --count_packet
