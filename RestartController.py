#!/usr/bin/env python

import os
import sys
import yaml
from time import sleep


def RenderConfigFiles():
	script_dir = os.path.dirname(__file__)
	rel_path = "TopologyVariables.yaml"
	abs_file_path = os.path.join(script_dir, rel_path)
	file=open(abs_file_path)
	topo_vars = yaml.load(file.read())
	topo_vars['home_directory'] = os.path.dirname(os.path.realpath(__file__))
	file.close()
	template_open = open("srdemo.j2")
	ingress_template = Template(template_open.read())
	template_output = ingress_template.render(topo_vars)
	script_dir = os.path.dirname(__file__)
	rel_path = "srdemo.conf"
	abs_file_path = os.path.join(script_dir, rel_path)
	with open(abs_file_path, "wb") as f:
		f.write(template_output)
	f.close()
	file.close()


def main():
	os.chdir( path )
	RenderConfigFiles()
	with open('TopologyVariables.yaml', 'r') as f:
		TopoVar = yaml.load(f)
	f.close()
	user = str(TopoVar['user'])
	password = str(TopoVar['password'])
	host = str(TopoVar['host'])
	poll_router = str(TopoVar['ISIS-DB-Poll']['ip_address'])
	poll_router_user = str(TopoVar['ISIS-DB-Poll']['user'])
	poll_router_pw = str(TopoVar['ISIS-DB-Poll']['password'])
	data = {"user": user,
		"host": host,
		"password": password,
		"commands": "sudo pkill -9 exabgp ; sudo pkill -9 screen ; screen -wipe ; screen -dm exabgp srdemo.conf --debug ; screen -dm python sr_demo.py -u "+str(poll_router_user)+" -p "+str(poll_router_pw)+" -a " + str(poll_router)}
	command = "sshpass -p {password} ssh -o StrictHostKeyChecking=no {user}@{host} {commands}"
	os.system(command.format(**data))
	print ("\n\nKilling Controller........\n\n\n")
	print ("\n\nStarting ExaBGP ........\n\n\n")
	sleep(0.5)
	print ("\n\nStarting Controller ........\n\n\n")
	print ("\n\nDone! ........\n\n\n")
	exit(0)

if __name__ == "__main__":
	main()
	os.system("sudo pkill -9 python")
