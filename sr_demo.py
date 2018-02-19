#!/usr/bin/env python


from jsonrpclib import Server
from pprint import pprint as pp
from multiprocessing import Process
import multiprocessing
import SocketServer
import SimpleHTTPServer
from threading import Thread
import json
import os
import re
import signal
import ast
import sys
import socket
from time import sleep
import subprocess
import argparse
import pyeapi
import getopt
import copy
import optparse
import errno
import collections
import multiprocessing
import multiprocessing.queues
from  __builtin__ import any as b_any
import requests
from flask import Flask, render_template, request

##  Commands run in the polling of the ISIS router.

C = "show isis database detail"
C1 = "show isis segment-routing prefix-segments"

### Program Variables.  #############################################


##### Configure this ISIS poll timer so the switch Capi doesn't blow out.  5 sec is solid.  Min 2 sec

POLLTIMER = 5

###  System has a 1 second wait time as well (not really needed)

###This DEADTIMECOUNTER and DEADTIMETIMER - ensures we remove the route after a delay (default .5 sec)

DEADTIMECOUNTER = 1
DEADTIMETIMER = 0.5

#####################################################################


def parse_args(argv):
    nodes = []
    hostname_list = []
    switches = []
    switch_dict = {}
    switch_dict = {}
    parser = optparse.OptionParser()  
    parser.add_option('-u', help='Username. Mandatory option', dest='username', action='store')
    parser.add_option('-p', help='Password. Mandatory option', dest='password', action='store')
    parser.add_option('-r', help='explicit refresh rate running the command. By default the programs sets the system default refresh to 1 second,', dest='refresh_rate', type=int, default=1, action='store')
    parser.add_option('-a', help='One hostname (or IP address) of the ISIS DB Poll switch. Mandatory option with single argument', dest='hostnames', action='store')
    (opts, args) = parser.parse_args()
    mandatories = ['username', 'password', 'hostnames']
    for m in mandatories:
        if not opts.__dict__[m]:
            print "mandatory option is missing\n"
            parser.print_help()
            print "\n\n"
            exit(-1)
    hostname_list = opts.hostnames.split(',')
    for IPorHM in hostname_list:
        switch = connect (opts.username, opts.password, IPorHM)
        switches.append(switch)
    switch_dict = {k: v for k, v in zip(hostname_list, switches)}
    return opts.refresh_rate,switch_dict, hostname_list


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



class PopulateFiles(Process):
	global POLLTIMER
	def __init__(self):
		super(PopulateFiles, self).__init__()
		self.refresh_rate,self.switches, self.hostname_list  = parse_args(sys.argv[1:])
		
		# Create the files we need on initiation.
		
		script_dir = os.path.dirname(__file__)
		rel_path = "ISIS_DataBase"
		abs_file_path = os.path.join(script_dir, rel_path)
		f = open(abs_file_path,'w') #Clear the file or Create the file if it doesn't exist
		f.close()
		rel_path = "Active_SIDs"
		abs_file_path = os.path.join(script_dir, rel_path)
		f = open(abs_file_path,'w') #Clear the file or Create the file if it doesn't exist
		f.close()
		
		###########################################
		
	def run(self):
		while True:
			self.Get_Active_Node_SIDs(self.refresh_rate,self.switches, self.hostname_list)
			
	
			
	def Get_Active_Node_SIDs(self, refresh_rate, switches, hostname_list):
		while True:
			try:
				self.oldstdout = sys.stdout
				self.script_dir = os.path.dirname(__file__)
				self.rel_path = "ISIS_DataBase"
				self.abs_file_path = os.path.join(self.script_dir, self.rel_path)
				self.f = open(self.abs_file_path,'r+')
				sys.stdout = self.f
				self.switch = switches.values()[0]
				output = self.switch.runCmds ( 1, [ C ], "text" )
				f = output[0]['output']
				print f
				sys.stdout.close()
				sys.stdout = self.oldstdout
				ActiveNodeSIDs = []
				ActivePrefixes = []
				output = self.switch.runCmds ( 1, [ C1 ], "json" )
				prefix_segment_details = output[0]['vrfs']['default']['isisInstances']['sr_instance']['prefixSegments']
				sleep(0.1)
				output1 = self.switch.runCmds ( 1, [ 'show ip route '  ], "json" )
				sleep(0.1)
				prefixes = output1[0]['vrfs']['default']['routes']
				for prefix in prefixes:
					ActivePrefixes.append(str(prefix))
				#pp(ActivePrefixes)
				for entry in prefix_segment_details:
					line = str(entry['prefix'])
					#print line
					if line in ActivePrefixes:
						ActiveNodeSIDs.append(str(entry['systemId']))
				#pp(ActiveNodeSIDs)
				self.script_dir = os.path.dirname(__file__)
				self.rel_path = "Active_SIDs"
				self.abs_file_path = os.path.join(self.script_dir, self.rel_path)
				self.file = open(self.abs_file_path,'w')
				for item in ActiveNodeSIDs:
					self.file.write("%s\n" % item)
				sleep(POLLTIMER)
			except KeyboardInterrupt:
				sys.exit(0)




class Get_ISIS_SIDS(object):

	
	def parse_isis_adj(self):
		self.script_dir = os.path.dirname(__file__)
		self.rel_path = "ISIS_DataBase"
		self.abs_file_path = os.path.join(self.script_dir, self.rel_path)
		self.fin = open(self.abs_file_path,'r')
		hostname = ""
		code = ""
		d1 = {}
		Adj_SIDs = []
		Temp_Adj_SIDs = []
		for l in self.fin.readlines():
			l = l.lstrip()
			l = l.rstrip()
			if l.endswith("<>"):
				hostname = l.split(" ")[ 0 ]
				hostname = hostname.split(".")[0]
				#print hostname
				continue
			if l.startswith('IS Neighbor'):
				l = l.strip()
				l = l.rstrip()
				tmp = l.split( ':' )
				n = tmp[1].rstrip()
				n = n.lstrip()
				n = n.split(' ')[0]
				n = n.split('.')[0]
				#print n,
				code = '%s&*&%s' % ( hostname, n)
			if l.startswith('Adj-sid'):
				l = l.strip()
				l = l.rstrip()
				tmp = l.split( ':' )
				o = tmp[1].rstrip()
				o = o.lstrip()
				o = o.split(' ')[0]
				o = o.split('.')[0]
				#print o,
				code = '{'+str(code) +':%s}' % (o)
				Temp_Adj_SIDs.append(code)
		for node in Temp_Adj_SIDs:
			#d = dict(e.split(":") for e in node.translate(None,"{}").split(","))
			node = node.strip()
			t = node.lstrip('{')
			u = t.rstrip('}')
			try:
				k,v = u.split(':')
				d1[str(k)] = str(v)
				Adj_SIDs.append(d1.copy())
				del d1[k]
			except ValueError:
				print('Ignoring: malformed line: "{}"'.format(u))
		#pp(Adj_SIDs)	
		return Adj_SIDs
	

		
	def parse_isis_node(self):

		self.script_dir = os.path.dirname(__file__)
		self.rel_path = "ISIS_DataBase"
		self.abs_file_path = os.path.join(self.script_dir, self.rel_path)
		self.fin = open(self.abs_file_path,'r')
		findSRGBBase =  1
		if findSRGBBase == 1:
			for l in self.fin.readlines():
				l = l.strip()
				l = l.rstrip()
				if l.startswith('SRGB Base'):
					tmp = l.split( ':' )
					q = tmp[1].rstrip()
					q = q.lstrip()
					q = q.split(' ')[0]
					q = q.split('.')[0]
		self.script_dir = os.path.dirname(__file__)
		self.rel_path = "ISIS_DataBase"
		self.abs_file_path = os.path.join(self.script_dir, self.rel_path)
		self.fin = open(self.abs_file_path,'r')
		hostname = ""
		code = ""
		Node_SIDs = []
		Temp_Node_SIDs = []
		d2 = {}
		for l in self.fin.readlines():
			l = l.lstrip()
			l = l.rstrip()
			if l.endswith("<>"):
					hostname = l.split(" ")[ 0 ]
					hostname = hostname.split(".")[0]
					#print hostname
					continue
			if l.startswith('SR Prefix-SID') and 'N' in l:
					l = l.strip()
					l = l.rstrip()
					tmp = l.split( ':' )
					p = tmp[1].rstrip()
					p = p.lstrip()
					p = p.split(' ')[0]
					p = p.split('.')[0]
					r = (int(q)+int(p))
					code = '{%s:%s}' % (hostname ,r)
					Temp_Node_SIDs.append(code)
		#pp(Temp_Node_SIDs)
		ActiveNodeSIDs = []
		self.script_dir = os.path.dirname(__file__)
		self.rel_path = "Active_SIDs"
		self.abs_file_path = os.path.join(self.script_dir, self.rel_path)
		with open(self.abs_file_path,'r') as self.f:
			ActiveNodeSIDs = [word.strip() for word in self.f]
		#print "\n\nactive SIDs from parse Node SIDs"
		#pp(ActiveNodeSIDs)	
		for node in Temp_Node_SIDs:
			node = node.strip()
			t = node.lstrip('{')
			u = t.rstrip('}')
			try:
				k,v = u.split(':')
				#print "follows the value k"
				#print k
				if k in ActiveNodeSIDs:
					d2[str(k)] = str(v)
					Node_SIDs.append(d2.copy())
					del d2[k]
			except ValueError:
				print('Ignoring: malformed line: "{}"'.format(u))
			#pp(d2)
		#print "\n\nNode SIDs returned from parse Node SIDs"
		#pp(Node_SIDs)
		return Node_SIDs

	def get_key_val(self, x):
		a,b = x.split(':')
		return a,int(b)

	def deleteContent(self, pfile):
		pfile.seek(0)
		pfile.truncate()




class Get_SIDs_DICTS(Process):
	def __init__(self):
		super(Get_SIDs_DICTS, self).__init__()
		self.refresh_rate,self.switches, self.hostname_list  = parse_args(sys.argv[1:])
	def run(self):
		while True:
			self.build_graph_dicts(self.refresh_rate,self.switches, self.hostname_list)

	def build_graph_dicts(self, refresh_rate, switches, hostname_list):
		while True:
			try:
				node_names = []
				links_list_temp = []
				links_list_for_force_graph = []
				links_list = []
				self.sid_dict={}
				node_sid_dict = {}
				local_subnets = {}
				node_names_final_list = []
				
		### Connect to the SINGLE device in the ISIS topology to get the ISIS DB
		### Actually we call class get_isis and use parse_isis_adj and parse_isis_node
		### To connect to the single "exporter" and it parses the returned output
		
				#isis_switch = switches.values()[0]
				get_isis = Get_ISIS_SIDS()
				Adj_SIDs = get_isis.parse_isis_adj()
				Node_SIDs = get_isis.parse_isis_node()
				
		### Build the mapping file for D3 in the fomat it likes.  Using the ADJ and Node SID's
		
				#pp(Adj_SIDs)
				for node in Node_SIDs:
					node_names.append(node.keys()[0])
				node_names_final = self.uniq(node_names)
				for node in node_names_final:
					node_names_final_list.append({"group" : int(node_names_final.index(node)), "name":str(node)})
				new_links_list_temp = []
				for entry in Adj_SIDs:
					for key in entry:
						splitkey = key.split("&*&")
						new_links_list_temp.append({"id": str(entry.get(key)), "source": str(splitkey[0]), "target": str(splitkey[1]),  "value":1})
				for link in new_links_list_temp:
					for node in node_names_final_list:
						value = 1
						if link['source'] == node['name']:
							source = node['group']
							for node in node_names_final_list:
								if link['target'] == node['name']:
									record = {"value":int(value), "id":link['id'], "source":source,"target": node['group']}
									if record not in links_list:
										links_list.append(record)
	
				#pp(links_list)
				#pp(new_links_list_temp)
				#print "\n\nNode name final list as determined in Get_SIDs_DICTS.build_graph_dicts"
				#pp(node_names_final_list)
		
		####  Now increment duplicates' value so it graphs nice and pretty.
				
				f_list = []
				for link in links_list:
					f = str(link['source'])+':'+str(link['target'])
					f_list.append(f)
				g = collections.Counter(f_list)
				values_list =  g.values()
				key_list = g.keys()
				index = [i for i, j in enumerate(values_list) if j >=2]
				for i in index:
					k = 1
					i_list = key_list[i].split(':')
					for link in links_list:
						if str(link['source']) == i_list[0] and str(link['target']) == i_list[1]:
							link['value'] = k
							k += 1
				
		### Write to topology file for the D3 graph (thats the ONLY thing that uses it.)

				json_prep = {"links":links_list, "nodes":node_names_final_list}
				#print json_prep
				filename_out = 'sr_topology.json'
				open(filename_out, 'w').close()
				with open(filename_out,'w') as json_out:
					json.dump(json_prep, json_out, indent = 2)
					json_out.close()
				sleep(1)
			except KeyboardInterrupt:
				sys.exit(0)


## Returns index in passed Dictionary of inversed a,b

	def find_index(self, lst,a,b):
		result = []
		for link in lst:
			if str(link['target']) == a and str(link['source']) == b:
				result = lst.index(link)
		return result
	
## Returns only unique values in passed list that had duplicates

	def uniq(self, input):
		output = []
		for x in input:
			if x not in output:
				output.append(x)
		return output




##  Runs Flask as a backend process


class Backend_Flask(object):
	def __init__(self):
		script_dir = os.path.dirname(__file__)
		self.app = Flask('Backend_Flask', template_folder=script_dir, root_path=script_dir, static_url_path=script_dir, static_folder=script_dir)
		self.app.add_url_rule('/', "index", self.index, methods=['GET','POST'])
		self.app.add_url_rule('/path_frame.htm', "path_frame", self.path_frame, methods=['GET','POST'])
		self.app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
		self.rel_path = "new_path_info.json"
		self.script_dir = os.path.dirname(__file__)
		self.abs_file_path = os.path.join(self.script_dir, self.rel_path)
		self.logfile = open(self.abs_file_path,'w+')
		self.logfile.close()
	def index(self):
		if request.method=="GET":
			return render_template('index.html')
		if request.method=="POST":
			data = request.get_json()
			self.rel_path = "new_path_info.json"
			self.script_dir = os.path.dirname(__file__)
			self.abs_file_path = os.path.join(self.script_dir, self.rel_path)
			self.logfile = open(self.abs_file_path,'w+')
			with self.logfile as json_out:
				json.dump(data, json_out, indent = 2)
				json_out.close()
			return "OK"
	def path_frame(self):
		if request.method=="GET":
			return render_template("path_frame.htm")
		if request.method=="POST":
			return "OK"
		else:
			print "Got non-post"
			return "OK"
		
		
		
		
class AddRemoveRoutes(Process):
	global DEADTIMECOUNTER
	global DEADTIMETIMER
	
	def __init__(self):
			super(AddRemoveRoutes, self).__init__()
			self.refresh_rate,self.switches, self.hostname_list  = parse_args(sys.argv[1:])
			self.data = []
			self.rel_path = "new_path_info.json"
			self.script_dir = os.path.dirname(__file__)
			self.abs_file_path = os.path.join(self.script_dir, self.rel_path)
			self.logfile = open(self.abs_file_path,'w')
			self.logfile.close()
	def run(self):
		PrimaryPathElementDictionary = {}
		PrimaryPathList = []
		ActiveSIDs = []
		OldActiveSIDs = []
		SecondaryPathList = []
		PrefixList = []
		OldPrimaryPathList = []
		OldSecondaryPathList = []
		OldPrefixList = []
		controller_ip = CONTROLLER_IP
		deadcounter = DEADTIMECOUNTER
		SecondaryFECServicePrefixList = []
		TopoChangeAddPathList = []
		TopoChangeRemovePathList = []
		PrimaryFECServicePrefixList = []
		count_list = []				#####  Remove this later
		while True:
			try:
				print "Running Main Routine.... All engines are go........"	
				self.isis_switch = self.switches.values()[0]
				self.get_isis = Get_ISIS_SIDS()
				self.Adj_SIDs = self.get_isis.parse_isis_adj()
				self.Node_SIDs = self.get_isis.parse_isis_node()
				self.data = []
				TopoChangeAddPathList = []
				TopoChangeRemovePathList = []
				self.rel_path = "new_path_info.json"
				self.script_dir = os.path.dirname(__file__)
				self.abs_file_path = os.path.join(self.script_dir, self.rel_path)
				self.logfile = open(self.abs_file_path,'r+')
				with self.logfile as f:
					try:
						self.data = json.load(f)
						f.seek(0)
						f.truncate()
						f.close()
					except ValueError:
						#print "Path File Is Empty"
						self.data = {u'fec': u'', u'dstPrefix': u'', u'Primary': False, u'dstNH': u'', u'dstFecNH': u'', u'RemoveFEC': u'', u'path': [], u'ManualFECPath':[], u'ManualFECPathID': u'', u'FECPathID': u'', u'RemoveRoute': u'', u'Secondary': False}
						pass
			
		### Here if there is a manual path entered and it comes over the JSON POST take it (a string)
		### Listify it and save it as path so it's used just like a force path would be.
		### Basic checking to make sure it's a 6 digit number or multiples space separated
		
		
				if len(self.data['ManualFECPath']) >= 1:
					try:
						if re.findall(r"\b\d{6}\b", self.data['ManualFECPath']):
							path_sids = re.findall(r"\b\d{6}\b", self.data['ManualFECPath'])
							self.data['path'] = path_sids
						else:
							print " You need to input space separated 6 Digit Labels!!!"
							return
					except(KeyError, ValueError):
						print " You need to input space separated 6 Digit Labels!!!"
						return
					
		### Right - now kick off the parsing and storing of said POST variables.
		
				try:
					if str(self.data['dstPrefix']):
						currentpath = str(self.data['dstPrefix'])+' next-hop ' +str(self.data['dstNH'])
						if PrefixList == []:
							PrefixList.append(str(self.data['dstPrefix'])+' next-hop ' +str(self.data['dstNH']))
						for entry in PrefixList:
							if currentpath in PrefixList:
								pass
							else:
								PrefixList.append(str(self.data['dstPrefix'])+' next-hop ' +str(self.data['dstNH']))
					if self.data['Primary'] == True:
						try:
							for p in self.data['path']:
								index = int(self.data['path'].index(p))
								for node in self.Node_SIDs:
									if node.get(p) != None:
										self.data['path'][index] = str(node.get(p))
							Path_String = ' '.join(self.data['path'])
							currentpath = str(self.data['fec'])+' next-hop ' + str(self.data['dstFecNH']) + ' label ['+str(Path_String)+']'
							current_fec_NH = str(self.data['fec'])+' next-hop ' + str(self.data['dstFecNH'])
							current_fec = str(self.data['fec'])
							
		### Do a couple of funky operations.  1) If the currentpath is in Primary path list - skip. 2) If the FEC  are the Same
		### The put the "latest" in Primary and relegate the current primary to secondary.  This keeps the router and the controller in sync.
		## As the router will always take the latest as advertised from exabgp. 3) Else - just add currentpath to PrimaryPath List
		
							if PrimaryPathList == []:
								PrimaryPathList.append(str(self.data['fec'])+' next-hop ' + str(self.data['dstFecNH']) + ' label ['+str(Path_String)+']')
							for entry in PrimaryPathList:
								if currentpath in PrimaryPathList:
									pass
								elif current_fec in entry and currentpath in SecondaryPathList:
									SecondaryPathList.remove(currentpath)
									PrimaryPathList.append(currentpath)
									PrimaryPathList.remove(entry)
									SecondaryPathList.append(entry)
								elif current_fec in entry and currentpath not in SecondaryPathList:
									PrimaryPathList.remove(entry)
									SecondaryPathList.append(entry)
									PrimaryPathList.append(currentpath)
								elif currentpath not in PrimaryPathList:
									if b_any(current_fec in x for x in PrimaryPathList):
										pass
									else:
										PrimaryPathList.append(str(self.data['fec'])+' next-hop ' + str(self.data['dstFecNH']) + ' label ['+str(Path_String)+']')
						except KeyError:
							pass
						
					if self.data['Secondary'] == True:
						try:
							for p in self.data['path']:
								index = int(self.data['path'].index(p))
								for node in self.Node_SIDs:
									if node.get(p) != None:
										self.data['path'][index] = str(node.get(p))
							Path_String = ' '.join(self.data['path'])
							currentpath = str(self.data['fec'])+' next-hop ' + str(self.data['dstFecNH']) + ' label ['+str(Path_String)+']'
							if SecondaryPathList == []:
								SecondaryPathList.append(str(self.data['fec'])+' next-hop ' + str(self.data['dstFecNH']) + ' label ['+str(Path_String)+']')
							for entry in SecondaryPathList:
								if currentpath in SecondaryPathList:
									pass
								else:
									SecondaryPathList.append(str(self.data['fec'])+' next-hop ' + str(self.data['dstFecNH']) + ' label ['+str(Path_String)+']')
						except KeyError:
							pass
					
			###  Now remove any FEC routes (Primary or secondary) when the FECtoRemove is received
					
					if str(self.data['RemoveFEC']):
						FECtoRemove = self.data['RemoveFEC']
						for line in PrimaryPathList:
							if line.find(FECtoRemove) == -1:
								pass
							else:
								PrimaryPathList.remove(line)
						FECtoRemove = self.data['RemoveFEC']
						for line in SecondaryPathList:
							if line.find(FECtoRemove) == -1:
								pass
							else:
								SecondaryPathList.remove(line)
								
			###  Now remove any Route when the RouteRemove is received
					
					if str(self.data['RemoveRoute']):
						RoutetoRemove = self.data['RemoveRoute']
						for line in PrefixList:
							if line.find(RoutetoRemove) == -1:
								pass
							else:
								PrefixList.remove(line)
								
				except KeyError:
					pass
				
				
			#####  Now Find the SIDs ->
			##### Just like in Get_SIDs_and_Dicts


				self.AllActiveSIDs = []
				self.ActiveAdjSIDs = []
				self.ActiveNodeSIDs = []
				
		##  This just gets the SID from the dictionaries returned from the ISIS database parsing function
		### add them to AllActiveSIDs
		
				for line in self.Adj_SIDs:
					for node in line:
						adjsid = line[node]
						self.ActiveAdjSIDs.append(adjsid)
	
				for line in self.Node_SIDs:
					for node in line:
						nsid = line[node]
						self.ActiveNodeSIDs.append(nsid)
				
				self.AllActiveSIDs = list(set(self.ActiveNodeSIDs + self.ActiveAdjSIDs))

		# Search the primary FEC Path list- where one or more labels are missing from the
		# path.  Add these paths to the list TopoChangeRemovePathList (to be used later)
		

				path_ip_address_list = []
				for path in PrimaryPathList:
					path_sids = re.findall(r"\b\d{6}\b", path)
					if set(path_sids) < set(self.AllActiveSIDs) and deadcounter == DEADTIMECOUNTER:
						pass
					
		### If things are Still busted, build a list of the next hops we need to look for in the Secondary table to add.
		
					elif deadcounter == DEADTIMECOUNTER + 1:
						for path in PrimaryPathList:
							path_sids = re.findall(r"\b\d{6}\b", path)
							if set(path_sids) < set(self.AllActiveSIDs):
								deadcounter = DEADTIMECOUNTER
								pass
							else:
								TopoChangeRemovePathList.append(path)
								first_ip = re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', path).group()
								path_ip_address_list.append(first_ip)
						deadcounter = DEADTIMECOUNTER
								
		### Give it a hot half second - might be a glitch getting the ISIS DB, or a refresh of DB
		### Sleep for 0.5 seconds and request the SID's again.
		
					else:
						sleep(DEADTIMETIMER)
						deadcounter +=1
				#print path_ip_address_list

		# First Step on secondary - Search the primary secondary Path list- if one or more labels are missing from the
		# path remove it. 
		
				for path in SecondaryPathList:
					path_sids = re.findall(r"\b\d{6}\b", path)
					if set(path_sids) < set(self.AllActiveSIDs):
						pass
					else:
						SecondaryPathList.remove(path)
						
		## Second step on secondary table. We do the search for routes from the  after we've removed the once from the routing disruptions.
		##  We now use the path_ip_address_list (from above) to see if there are any routes to add in.  So now we only care about the FEC NH
		##  We do need to remove them from the secondary too - because they're now going to be active in Primary!	
		
				for ip in path_ip_address_list:
					for path in SecondaryPathList:
						secondpath_first_ip = re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', path).group()
						if secondpath_first_ip in path:
							SecondaryPathList.remove(path)
							TopoChangeAddPathList.append(path)

		#### Now update Primary Path list for Visibility.
					
				for path in TopoChangeAddPathList:
					PrimaryPathList.append(path)
				for path in TopoChangeRemovePathList:
					PrimaryPathList.remove(path)
					
				TopoChangeAddPathList = []
				TopoChangeRemovePathList = []
				
		## We now have the primary table with reoved routes so len(OldPrimaryPathList) >= len(PrimaryPathList) should pick up the withdraw routes
		## for the path routes.  We also have TopoChangeAddPathList and TopoChangeRemovePathList we need to action below.  We dont add these to the
		## primaryPath list until after the Paths are added/removed
		
		## Now Program the changed Primary FEC Routes: Program Them!!!  Skip if nothing changed completely.
				
				if len(OldPrimaryPathList) == len(PrimaryPathList) and cmp(PrimaryPathList, OldPrimaryPathList) == 0:
					pass
				
				elif len(OldPrimaryPathList) == len(PrimaryPathList) and cmp(PrimaryPathList, OldPrimaryPathList) != 0:
					print("Advertising the following newly learned FEC routes for the same FEC")	
					for ppath in PrimaryPathList:
						if ppath not in OldPrimaryPathList:
							r = requests.post('http://' + str(controller_ip) + ':5000', files={'command': (None, 'announce route '+str(ppath))})
							sleep(.2)
							print 'announce route '+str(ppath)
	
				
				elif len(OldPrimaryPathList) == 0 and len(PrimaryPathList) >= 0:
					print("Advertising the following newly learned FEC routes First Match")	
					for ppath in PrimaryPathList:
						if ppath not in OldPrimaryPathList:
							r = requests.post('http://' + str(controller_ip) + ':5000', files={'command': (None, 'announce route '+str(ppath))})
							sleep(.2)
							print 'announce route '+str(ppath)
	
				
				elif len(OldPrimaryPathList) > len(PrimaryPathList):
					print("Removing the following FEC routes ")
					for route in OldPrimaryPathList:
						if route not in PrimaryPathList:
							path_copy = copy.deepcopy(route)
							withdraw_ip = path_copy.split("next-hop", 1)[0]
							ip_list = re.findall( r'[0-9]+(?:\.[0-9]+){3}', path_copy )
							next_hop_ip = ip_list[1]
							r = requests.post('http://' + str(controller_ip) + ':5000', files={'command': (None, 'withdraw route ' + str(withdraw_ip) +' next-hop ' + str(next_hop_ip)+ ' label [800000]''\n')})
							sleep(.2)
							print 'withdraw route ' + str(withdraw_ip) +' next-hop ' + str(next_hop_ip)+ ' label [800000]''\n'
	
	
				elif len(OldPrimaryPathList) < len(PrimaryPathList):
					print("Advertising the following newly learned FEC routes last match")
					for route in PrimaryPathList:
						if route not in OldPrimaryPathList:
							r = requests.post('http://' + str(controller_ip) + ':5000', files={'command': (None, 'announce route '+str(route))})
							sleep(.2)
							print 'announce route '+str(route)
							
			

				
		### Final Step (from above:  Search the Active Service prefixes - and if there is no route in the primary or
		### secondary table with it's NH - then use the default, or remove it.  I havent decided yet.
		### Build a list of paths to remove/change
				
				
		### Now that we added and removed the topology changes -> updated  the Primary Path list and determined
		### even if any service prefixes need to be removed.  Lets just use the "normal function"
		
		### Programmed the Active programmed routes.  Skip if nothing changed.
	
				if len(OldPrefixList) == len(PrefixList) and cmp(PrefixList, OldPrefixList) == 0:
					#print("No Change in the Route Table\n")
					pass
					
				elif len(OldPrefixList) == 0 and len(PrefixList) >= 0:
					print("Advertising the following newly learned routes First Match")	
					for ppath in PrefixList:
						if ppath not in OldPrefixList:
							r = requests.post('http://' + str(controller_ip) + ':5000', files={'command': (None, 'announce route '+str(ppath))})
							sleep(.2)
							print 'announce route '+str(ppath)
	
				
				elif len(OldPrefixList) >= len(PrefixList):
					print("Removing the following routes ")
					for route in OldPrefixList:
						if route not in PrefixList:
							r = requests.post('http://' + str(controller_ip) + ':5000', files={'command': (None, 'withdraw route ' + str(route) +'\n')})
							sleep(.2)
							print 'withdraw route ' + str(route) +'\n'
	
	
				elif len(OldPrefixList) <= len(PrefixList):
					print("Advertising the following newly learned routes last match")
					for route in PrefixList:
						if route not in OldPrefixList:
							r = requests.post('http://' + str(controller_ip) + ':5000', files={'command': (None, 'announce route '+str(route))})
							sleep(.2)
							print 'announce route '+str(route)			
	
	
		###  Just print out the paths for visibility
		
				PrefixDict = []
				# print"here is the active Service prefix list"
				# pp(PrefixList)
				PrefixDict = dict(enumerate(PrefixList))
				# print PrefixDict
				# print"here is the current primary path list"
				# pp(PrimaryPathList)
				PrimaryPathDict = dict(enumerate(PrimaryPathList))
				# print"here is the old primary path list"
				# pp(OldPrimaryPathList)
				# print"here is the current secondary path list"
				# pp(SecondaryPathList)
				SecondaryPathDict = dict(enumerate(SecondaryPathList))
				
				
				json_prep = {"prefixes":PrefixDict, "primary":PrimaryPathDict , "secondary": SecondaryPathDict }
				self.rel_path = "controller_output.json"
				self.script_dir = os.path.dirname(__file__)
				self.abs_file_path = os.path.join(self.script_dir, self.rel_path)
				self.logfile = open(self.abs_file_path,'w')
				with self.logfile as json_out:
					json.dump(json_prep, json_out, indent = 2)
					json_out.close()
					
				sleep(1)
				_=os.system("clear")					### (need to move display to JSON))
				
				
				OldPrimaryPathList = copy.deepcopy(PrimaryPathList)
				OldPrefixList = copy.deepcopy(PrefixList)
				
			except KeyboardInterrupt:
				exit(0)
			
	def deleteContent(self, file):
		self.file = file
		self.file.seek(0)
		self.truncate()
		
		## Returns index in passed Dictionary of inversed a,b

	def find_index(self, lst,a,b):
		result = []
		for link in lst:
			if str(link['target']) == a and str(link['source']) == b:
				result = lst.index(link)
		return result

	

class MyError(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)				


def _worker():
    global backend_flask_instance
    if backend_flask_instance == None:
        backend_flask_instance = Backend_Flask()


if __name__ == "__main__":
	refresh_rate, switches, hostname_list  = parse_args(sys.argv[1:])
	print "\n\nStarting....Label Gathering and Webserver.....\n\n"
	#start the controller as a separate proceses
	with open('TopologyVariables.yaml', 'r') as f:
		TopoVar = yaml.load(f)
	f.close()
	CONTROLLER_IP = str(TopoVar['exabgp']['ip_address'])
	password = str(TopoVar['password'])
	BGP_LU_Peer = TopoVar['LERs']['ip_address']
	backend_flask_instance = None
	flask_backend_process = multiprocessing.Process(None, _worker,"async web interface listener")
	flask_backend_process.start()
	p2 = Get_SIDs_DICTS()
	p3 = AddRemoveRoutes()
	p1 = PopulateFiles()
	p1.start()
	p2.start()
	p3.start()
	try:
		while True:
		   pass
	except KeyboardInterrupt:
		controller_ip = CONTROLLER_IP
		for Peer in BGP_LU_Peer:
			r = requests.post('http://' + str(controller_ip) + ':5000', files={'command': (None, 'neighbor '+str(Peer)+  ' teardown 2')})
			sleep(.5)
		print " \n\n Hard Clearing the Controller BGP peering Session"
		p1.terminate()
		p2.terminate()
		flask_backend_process.terminate()
		backend_flask_instance = None
		print "\n\n Exiting the Program........ \n\n"
		sys.exit(0)



