#!/usr/bin/env python

# Copyright (c) 2016 Arista Networks, Inc.  All rights reserved.
# Arista Networks, Inc. Confidential and Proprietary.
# -----------------------------------------------------
# Version 1.0  01-Dec-2016
# Written by:  Russell Kelly, Arista Networks
#
# Developed and tested on vEOS EAPI
# ### Version history ###
# - v1.0 - initial release
# Description:
# Show counters and packet rates

from jsonrpclib import Server
from pprint import pprint as pp
from multiprocessing import Process
from threading import Thread
import os
import re
import signal
import sys
import socket
from time import sleep
import subprocess
import argparse
import pyeapi
import getopt
import optparse
import errno
import collections


def not_num_only_match(strg, search=re.compile(r'[^0-9]').search):
    return bool(search(strg))


def parse_args(argv):
    switches = []
    switch_dict = {}
    nodes = []
    switch_dict = {}
    hostname_list = []
    
    parser = optparse.OptionParser()
    
    parser.add_option('-b', help='This option enables KBps to be dispalyed.  Default is off.', dest='mbps', default=False, action='store_true')
    parser.add_option('--count_packet', help='This option enables packet count to be dispalyed.  Default is off.', dest='pkts', default=False, action='store_true')
    parser.add_option('--safe', help='This option enables configurations to be backed up before running the program and restored upon exiting (Thus keeping the load-interval commands as previous).  Default is off.', dest='safe', default=False, action='store_true')    
    parser.add_option('-u', help='Username. Mandatory option', dest='username', action='store')
    parser.add_option('-p', help='Password. Mandatory option', dest='password', action='store')
    parser.add_option('-l', help='explicit interface load-interval rate. If set then every interesting interface has its load-interval set, and subsequently removed when packet-rate drops below 2pps. Values 5-300.  By default the programs sets the system default load-interval to 5', dest='load_interval', type=int, default=False, action='store')
    parser.add_option('-r', help='min packet rate.  Any interface with a rate above this will report status. Default is 2 pps.', dest='ppsrate', type=int, default=2, action='store')
    parser.add_option('-a', help='One or more hostnames (or IP addresses) of the switches to poll.  Comma separated.  Mandatory option with multiple arguments', dest='hostnames', action='store')
    parser.add_option('-i', help='optional argument with multiple arguments.  Ethernet Ports Only- Format: Ethernet<num>, or Eth<num>, comma separated, or range separated with' '-' ' e.g. Eth21-45 or Eth1,Eth7,Eth21-45', dest='interfaces', action='store')
    (opts, args) = parser.parse_args()
    mandatories = ['username', 'password', 'hostnames']
    for m in mandatories:
        if not opts.__dict__[m]:
            print "mandatory option is missing\n"
            parser.print_help()
            print "\n\n"
            exit(-1)
    hostname_list = opts.hostnames.split(',')
    if opts.interfaces != None:
        interface_list_parsed = opts.interfaces.split(',')
        for interface in interface_list_parsed:
            if '-' in interface:
                interface_range_start_stop = interface.split('-')
                for line in interface_range_start_stop:
                    if not_num_only_match(line):
                        for x in line[::-1]:
                            if x.isalpha():
                                y = line.split(x)
                                interface_range_start_stop[0] = y[1]
                                interface_range = range(int(interface_range_start_stop[0]), (int(interface_range_start_stop[1])+1),1)
                                for i in interface_range:
                                    interface_list_parsed.append("Ethernet"+ str(i)) 
                                break
            elif 'Ethernet' in interface:    
                pass
            else:
                for x in interface[::-1]:
                    if x.isalpha():
                        y = interface.split(x)
                        interface_list_parsed.append("Ethernet"+ str(y[1]))
                        break
        interface_list_remove = []   
        for interface in interface_list_parsed:
            if '-' in interface:
                interface_list_remove.append(interface)
            elif 'Ethernet' not in interface:    
                interface_list_remove.append(interface)
            else:    
                pass
        interface_list = [x for x in interface_list_parsed if x not in interface_list_remove]
    else:
        interface_list = []
    for IPorHM in hostname_list:
        switch = connect (opts.username, opts.password, IPorHM)
        switches.append(switch)
    for IPorHM in hostname_list:
        node = pyeapi.connect(host =IPorHM, user=opts.username, password=opts.password, transport='http')
        nodes.append(node) 
    switch_dict = {k: v for k, v in zip(hostname_list, switches)}
    return opts.safe, interface_list, nodes, switch_dict, hostname_list,opts.mbps,opts.load_interval,opts.ppsrate,opts.pkts



def connect(user, password, address):
   #Connect to Switch via eAPI
    switch = Server("http://"+user+":"+password+"@"+address+"/command-api")
    #capture Connection problem messages:
    try:
        response = switch.runCmds(1, ["show version"])
    except socket.error, error:
        error_code = error[0]
        if error_code == errno.ECONNREFUSED:
            run_error = str("[Error:"+str(error_code)+"] Connection Refused!(eAPI not configured?)")
            print "\n\nswitch: " + str(address)
            print run_error
            print "\n\n"
            sys.exit(2)
        elif error_code == errno.EHOSTUNREACH:
            run_error = str("[Error:"+str(error_code)+"] No Route to Host(Switch powered off?)")
            print "\n\nswitch: " + str(address)
            print run_error
            print "\n\n"
            sys.exit(2)
        elif error_code == errno.ECONNRESET:
            run_error = str("[Error:"+str(error_code)+"] Connection RST by peer (Restart eAPI)")
            print "\n\nswitch: " + str(address)
            print run_error
            sys.exit(2)
            print "\n\n"
        else:
            # Unknown error - report number and error string (should capture all)
            run_error = str("[Error5:"+str(error_code) + "] "+error[1])
            #raise error;
            print "\n\nswitch: " + str(address)
            print run_error
            sys.exit(2)
            print "\n\n"
    else:
        return switch


class load_rate(Process):
    def __init__(self):
        super(load_rate, self).__init__()
    def run(self):
        while True:
            self.safe, self.interface_list, self.nodes, self.switches, self.hostname_list, self.mbps, self.load_interval, self.ppsrate, self.pkts = parse_args(sys.argv[1:])
            if self.load_interval:
                self.set_load_rate(self.switches, self.load_interval, self.ppsrate)
            else:
                pass
    def set_load_rate(self, switches, load_interval, ppsrate):
        self.load_interval = load_interval
        self.ppsrate = ppsrate
        while True:
            try:
                for switch in switches.values():
                    intf = switch.runCmds ( 1, [ "show interfaces" ] )
                    intf_counters = switch.runCmds ( 1, [ "show interfaces counters rates" ] )
                    ports = intf[0][ "interfaces" ]
                    for p in ports:
                        try:
                            if intf[0][ "interfaces" ][p]["interfaceStatistics"]:
                                InterfaceValue = "interface %s" %(p)
                                LoadInterval = "load-interval %s" %(self.load_interval)
                                if intf[0][ "interfaces" ][p]["interfaceStatistics"]["updateInterval"] != self.load_interval and intf_counters[0][ "interfaces" ][p][ "inPpsRate"] > self.ppsrate and p != str('Management1'):
                                    self.change_load( switch, InterfaceValue, LoadInterval )
                                elif intf[0][ "interfaces" ][p]["interfaceStatistics"]["updateInterval"] == 300:
                                    pass
                                elif intf_counters[0][ "interfaces" ][p][ "inPpsRate"] <= self.ppsrate:
                                    LoadInterval = "default load-interval"
                                    self.change_load( switch, InterfaceValue, LoadInterval ) 
                            else:
                                pass
                        except KeyError:
                            pass
                sleep(1)
            except KeyboardInterrupt:
                sys.exit(0)
    
    def change_load(self, switch, InterfaceValue, LoadInterval ):
        self.response = switch.runCmds( 1, [ { "cmd": "enable" },
                                  "configure",
                                  InterfaceValue,
                                  LoadInterval,
                                  "end" ] )
        return self.response


class counter(Process):
    def __init__(self):
        super(counter, self).__init__()
    def run(self):
        while True:
            self.safe, self.interface_list, self.nodes, self.switches, self.hostname_list, self.mbps, self.load_interval, self.ppsrate, self.pkts = parse_args(sys.argv[1:])
            self.print_counter(self.interface_list, self.switches, self.mbps, self.ppsrate, self.pkts)
    def print_counter(self, interface_list, switches, mbps, ppsrate, pkts):
        self.mbps = mbps
        self.pkts = pkts
        self.ppsrate = ppsrate
        self.oldstdout = sys.stdout
        self.interface_list = interface_list
        self.script_dir = os.path.dirname(__file__)
        self.rel_path = "CounterOutput"
        self.abs_file_path = os.path.join(self.script_dir, self.rel_path)
        while True:
            try:
                self.f = open(self.abs_file_path,'w')
                sys.stdout = self.f
                if self.mbps == False and self.pkts == False:
                    for switch in switches.values():
                        intf = switch.runCmds ( 1, [ "show interfaces" ] )
                        if self.interface_list == []:
                            ports = intf[0][ "interfaces" ].keys()
                            ports.sort()
                        else:
                            ports = self.interface_list
                            ports.sort()
                        j = 0
                        for key, value in switches.items():
                            if switch is value:
                                print "\n================ Switch: " + str(key) +" ===========\n"
                        print("{:<20}{:>10}{:>15}\n".format("Interface", "Input PPS", "Output PPS"))
                        print "==============================================\n"
                        for p in ports:
                            try:
                                if  p != str('Management1'):
                                    if intf[0][ "interfaces" ][p]["interfaceStatistics"][ "inPktsRate"] > self.ppsrate or intf[0][ "interfaces" ][p]["interfaceStatistics"][ "outPktsRate"] > self.ppsrate:
                                        j +=1
                                        print("{:<20}{:>10}{:>15}\n".format(p, int(intf[0][ "interfaces" ][p]["interfaceStatistics"][ "inPktsRate"] ), int(intf[0][ "interfaces" ][p]["interfaceStatistics"][ "outPktsRate"] )))
                                    else:
                                        pass
                                else:
                                    pass
                            except KeyError:
                                pass        
                        if j == 0:
                                print "\n===================================================\nMan, there aint no traffic through this switch\n===================================================\n"        
                elif self.mbps == False and self.pkts == True:
                    for switch in switches.values():
                        intf = switch.runCmds ( 1, [ "show interfaces" ] )
                        intf_counters = switch.runCmds ( 1, [ "show interfaces counters rates" ] )
                        if self.interface_list == []:     
                            ports = intf_counters[0][ "interfaces" ].keys()
                            ports.sort()
                        else:
                            ports = self.interface_list
                            ports.sort()                            
                        j = 0
                        for key, value in switches.items():
                            if switch is value:
                                print "\n\n================ Switch: " + str(key) +" ===========\n\n"
                        print("{:<27}{:<25}{:<8}{:<27}{:<20}\n".format("Interface", "Input Packets", "PPS", "Output Packets", "PPS"))
                        print "==========================================================================================\n"
                        for p in ports:
                            try:
                                if intf[0][ "interfaces" ][p]["interfaceStatistics"]:
                                    if  p != str('Management1'):
                                        if intf[0][ "interfaces" ][p]["interfaceStatistics"][ "inPktsRate"] > self.ppsrate or intf[0][ "interfaces" ][p]["interfaceStatistics"][ "outPktsRate"] > self.ppsrate:
                                            j += 1
                                            print("{:<25}{:>15}{:>15}{:>20}{:>15}\n".format(p, int(intf[0][ "interfaces" ][p]["interfaceCounters"][ "inUcastPkts"]), int(intf[0][ "interfaces" ][p]["interfaceStatistics"][ "inPktsRate"] ), int(intf[0][ "interfaces" ][p]["interfaceCounters"][ "outUcastPkts"]), int(intf[0][ "interfaces" ][p]["interfaceStatistics"][ "outPktsRate"])))
                                        else:
                                            pass
                                    else:
                                        pass
                            except KeyError:
                                pass
                        if j == 0:
                                print "\n===================================================\nMan, there aint no traffic through this switch\n===================================================\n"                   
                elif self.mbps == True and self.pkts == True:
                    for switch in switches.values():
                        intf = switch.runCmds ( 1, [ "show interfaces" ] )
                        intf_counters = switch.runCmds ( 1, [ "show interfaces counters rates" ] )
                        if self.interface_list == []:     
                            ports = intf_counters[0][ "interfaces" ].keys()
                            ports.sort()
                        else:
                            ports = self.interface_list
                            ports.sort()     
                        j = 0
                        for key, value in switches.items():
                            if switch is value:
                                print "\n\n================ Switch: " + str(key) +" ===========\n\n"
                        print("{:<20}{:>15}{:>10}{:>15}{:>20}{:>10}{:>15}\n".format("Interface", "Input Packets", "PPS", "Input KBps", "Output Packets", "PPS", "Output KBps"))
                        print "==========================================================================================================\n"
                        for p in ports:
                            try:
                                if intf[0][ "interfaces" ][p]["interfaceStatistics"]:
                                    if  p != str('Management1'):
                                        if intf[0][ "interfaces" ][p]["interfaceStatistics"][ "inPktsRate"] > self.ppsrate or intf[0][ "interfaces" ][p]["interfaceStatistics"][ "outPktsRate"] > self.ppsrate:
                                            j += 1
                                            print("{:<20}{:>15}{:>10}{:>15}{:>20}{:>10}{:>15}\n".format(p, int(intf[0][ "interfaces" ][p]["interfaceCounters"][ "inUcastPkts"]), int(intf[0][ "interfaces" ][p]["interfaceStatistics"][ "inPktsRate"] ), int((intf_counters[0][ "interfaces" ][p][ "inBpsRate" ])/1000),int(intf[0][ "interfaces" ][p]["interfaceCounters"][ "outUcastPkts"]), int(intf[0][ "interfaces" ][p]["interfaceStatistics"][ "outPktsRate"]), int((intf_counters[0][ "interfaces" ][p][ "outBpsRate" ])/1000)))
                                        else:
                                            pass
                                    else:
                                        pass
                            except KeyError:
                                pass
                        if j == 0:
                                print "\n===================================================\nMan, there aint no traffic through this switch\n===================================================\n"     
                elif self.mbps == True and self.pkts == False:
                    for switch in switches.values():
                        intf = switch.runCmds ( 1, [ "show interfaces" ] )
                        intf_counters = switch.runCmds ( 1, [ "show interfaces counters rates" ] )
                        if self.interface_list == []:     
                            ports = intf[0][ "interfaces" ].keys()
                            ports.sort()
                        else:
                            ports = self.interface_list
                            ports.sort()     
        
                        j = 0
                        for key, value in switches.items():
                            if switch is value:
                                print "\n\n================ Switch: " + str(key) +" ===========\n\n"
                        print("{:<20}{:>10}{:>15}{:>20}{:>15}\n".format("Interface", "Input PPS", "Input KBps", "Output PPS", "Output KBps"))
                        print "=================================================================================\n"
                        for p in ports:
                            try:
                                if  p != str('Management1'):
                                    if intf[0][ "interfaces" ][p]["interfaceStatistics"][ "inPktsRate"] > self.ppsrate or intf[0][ "interfaces" ][p]["interfaceStatistics"][ "outPktsRate"] > self.ppsrate:
                                        j +=1
                                        print("{:<20}{:>10}{:>15}{:>20}{:>15}\n".format(p, int(intf[0][ "interfaces" ][p]["interfaceStatistics"][ "inPktsRate"] ), int((intf_counters[0][ "interfaces" ][p][ "inBpsRate" ])/1000), int(intf[0][ "interfaces" ][p]["interfaceStatistics"][ "outPktsRate"] ), int((intf_counters[0][ "interfaces" ][p][ "outBpsRate" ])/1000)))
                                    else:
                                        pass
                                else:
                                    pass
                            except KeyError:
                                pass    
                        if j == 0:
                                print "\n===================================================\nMan, there aint no traffic through this switch\n===================================================\n"         

                sys.stdout.close()
                sys.stdout = self.oldstdout
                self.fin = open(self.abs_file_path,'r')
                os.system('clear')
                print self.fin.read()
            except KeyboardInterrupt:
                sys.stdout.close()
                sys.stdout = self.oldstdout
                sys.exit(0)


def GetInitialLoadRates(switches, hostname_list):
    for hostname in hostname_list:
        for switch in switches.values():
            intf = switch.runCmds ( 1, [ "show interfaces" ] )
            intf_counters = switch.runCmds ( 1, [ "show interfaces counters rates" ] )
            ports = intf[0][ "interfaces" ]
            for p in ports:
                try:
                    if intf[0][ "interfaces" ][p]["interfaceStatistics"]:
                        ExistingLoadRates[hostname][p] = int(intf[0][ "interfaces" ][p]["interfaceStatistics"]["updateInterval"])
                    else:
                        pass
                except KeyError:
                    pass        
    return ExistingLoadRates





    
if __name__ == "__main__":
    print "\n\nStarting....Getting Existing Configurations and parsing.....\n\n"
    #ExistingLoadRates = collections.defaultdict(dict)
    safe, interface_list, nodes, switches, hostname_list, mbps, load_interval, ppsrate, pkts  = parse_args(sys.argv[1:])
    if load_interval == False:
        for node in nodes:
            output1 = node.execute(['enable', 'configure', 'load-interval default 5']) 
    if safe:
        for node in nodes:
            output = node.execute(['enable', 'copy running-config file:mnt/flash/mon_int_config'])
    p1 = counter()
    p1.start()
    p2 = load_rate()
    p2.start()
    oldstdout = sys.stdout
    try:
         while True:
                 pass
    except KeyboardInterrupt:
        p2.terminate()
        p1.terminate()
        print "\n\n Exiting the Interface Monitoring Program........ \n\n"
        for node in nodes:
            output1 = node.execute(['enable', 'configure', 'no load-interval default 5']) 
        if safe:
            print "\n\n Restoring original interface configurations.....\n\n"
            for node in nodes:
                try:
                    input_config = node.execute(['enable', 'copy file:mnt/flash/mon_int_config running-config'])
                except:
                    pass
        sys.exit(0)
        




    




