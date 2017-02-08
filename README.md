# SR Demo & Controller

An SR Controller BGP-LU with Segment Routing Labels

A Python Based SR and BGP Route Controller for Traffic Engineering.

To run the demo install EXABGP (version 4.0.0) along with Python 2.7.

This controller can be run on a VM or a BMS, but in addition is all dockerized and can be run in a container (instructions below)

For details on  EXABGP refer to this link:

https://github.com/Exa-Networks/exabgp

INSTALLATION:

To build your own version of the controller all you need to do is install Docker clone the git repository:

        git clone git@github.com:russellkelly/SR_Demo_Repo.git

IMPORTANT: ! Change the srdemo.conf file to match ingress (ingress LER) router's peering IP address.  Note:  The exabgp address, if runnning in a docker container) will not need to be changed as the docker container runs in private sr-net subnet and the controller (and hence the exabgp process) is given address 192.168.1.2.

Then in the cloned (SR_Demo_Repo) directory run:

        make demo # This runs build: (Builds the image sr-demo) and spawns containers srbase & srdemo

The srbase container is one that exabgp runs in, and peers with ingress LER.  One can connect to the container if required by running:

        docker attach <container-id>|<container name>
        
        to stop/start exabgp in this conatiner run: exabgp srdemo.conf  (stop exabgp with CTRL+C)

The srdemo container starts as another container in sr-net to run the demo from.


The srdemo will delete upon exit.  The srbase container will not.  To stop and remove run:

        make clean



Below is some details on what each file does:


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
          Holds the digrams for the original demo.  Can replace these if required.
          Note: best to amend the index.html file if you dont want these included
          
monitor_interface.py
--------------------
          Monitor Interfaces Command for Arista Devices.  Used in this demo to 
          visulize trafficbeing engineered troughout the domain.

          This script continually monitors interfaces in one, 
          or more Arista devices. 

          ```
          'monitor interface traffic'
          ```
          I created this program to allow one or a number of switches to be monitored at 
          once, running on-box or off, and monitoring multiple specifically defined 
          interfaces or all of them, and the ability to define variables like packet count, 
          min packet rate to show etc.  

          See the help below:

          ```
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


          ```

          As an example if I want to monitor devices lf275,fm213,fm382, but only 
          interfaces Eth2,4 and range 41-48, I want to show packet count and and KBps count 
          I would run the follwoing:

          ```
          python monitor_interfaces.py -u admin -p admin -r 10 -a lf275,fm213,fm382 --count_packet  -b -i Eth1,Eth2, Eth41-48
          ```

          For no KBps count and all interfaces over the rate of 10pps:


          ```
          python monitor_interfaces.py -u admin -p admin -r 10 -a lf275,fm213,fm382 --count_packet
          ```


Running the demo in a container
===============================

Once the git repository has been cloned locally the files srdemo and sr_demo.py need to be amended with the specific 
Topology and Runtime information for your topology

Change the following in sr_demo.py:  BGP_LU_Peer = 'xxx.xxx.xxx.xxx' (your ingress LER IP)
Change the following in srdemo.conf: neighbor <Add your LER IP Address Here>

One of the ISIS SR enabled routers that is in your domain will need to have eAPI enabled (see documentation).  This
router will be used for topology (ISIS DB) export.

Now one can run controller:

        make demo
        python sr_demo.py -u <eAPI username> -p <eAPI password> -a <ISIS DB Topology Export Router IP>


Running the demo in a VM or a BMS
===============================

Build an Ubuntu BMS, or VM and add all requirements per the Dockerfile (detailed below - one can use the Makefile):

        Base ubuntu 14.04 Install
        apt-get update
        apt-get install -qy --no-install-recommends wget python git
        apt-get install -qy openssh-server
        apt-get install -qy openssh-client
        apt-get install -qy python-pip
        apt-get install -qy python-dev
        apt-get install -qy libxml2-dev
        apt-get install -qy libxslt-dev
        apt-get install -qy libssl-dev
        apt-get install -qy libffi-dev
        apt-get install -qy sudo
        apt-get install -qy vim
        apt-get install -qy telnet
        apt-get clean
        pip install flask
        pip install pyeapi
        pip install jsonrpc
        pip install jsonrpclib

        mkdir /home/demos/sr-demo

        git clone https://github.com/Exa-Networks/exabgp.git
        /home/demos/sr-demo/exabgp
        git checkout master
        chmod +x setup.py
        sudo ./setup.py install
        cd /home/demos/sr-demo
        cp exabgp.env /usr/local/etc/exabgp/exabgp.env

        useradd -m demo && echo "demo:demo" | chpasswd && adduser demo sudo

Once the git repository has been cloned locally follow the same instructions above to configure the files and ru the demo.
