#!/usr/bin/env python3.2

import sys
import cherrypy
from jinja2 import Environment, FileSystemLoader
import traceback
import paramiko

def render(templateFilePath, vars):
	tb = None
	try:
		template = env.get_template(templateFilePath)
		return template.render(vars)
	except Exception,e:
		tb = traceback.format_exc()
	finally:
		if not tb==None:
			print "--------------- TEMPLATE EXCEPTION ----------------"
			print tb
			print "---------------------------------------------------"
			return "Error rendering template"

class sshManager(object):
	def __init__(self, host, username, password):
		self.host = host
		self.username = username
		self.password = password
		self.ssh = paramiko.SSHClient()
		self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
	def test(self):
		try:
			self.connect()
			self.disconnect()
			return True
		except:
			print traceback.format_exc()
			return False
	def connect(self):
		self.ssh.connect(self.host, username=self.username, password=self.password)
	def disconnect(self):
		self.ssh.close()
	def execute(self, command):
		self.connect()
		stdin, stdout, stderr = self.ssh.exec_command(command)
		stdout = stdout.read()
		stderr = stderr.read()
		self.disconnect()
		return (stdout, stderr)
	def execute_mc(self, command):
		return self.execute("/etc/init.d/minecraft command %s" % command)
	def start(self):
		return self.execute("/etc/init.d/minecraft start")
	def stop(self):
		return self.execute("/etc/init.d/minecraft stop")
	def status(self):
		return self.execute("/etc/init.d/minecraft status")
	def kill(self):
		return self.execute("killall java")

env = Environment(loader=FileSystemLoader("./templates/"))

def getManager(password):
	manager = sshManager('127.0.0.1', 'minecraft', password)
	if manager.test():
		return manager
	else:
		return False;

class mcmanager(object):
	def _checkLogin(self):
		if cherrypy.session.has_key("password"):
			success = getManager(cherrypy.session["password"])
			if not success:
				raise cherrypy.HTTPRedirect("/")
			else:
				return success
		else:
			raise cherrypy.HTTPRedirect("/")
	
	def index(self, password=None):
		vars ={}
		if password:
			success = getManager(password)
			if success:
				cherrypy.session["password"] = password
				raise cherrypy.HTTPRedirect("/manager")
			else:
				vars["failed"]=True
		return render("index.htm", vars)
	index.exposed = True
	
	def manager(self, success=None):
		ssh = self._checkLogin()
		yield render("manager.htm", {"success":success})
	manager.exposed = True
	
	def manager_command(self, command):
		ssh = self._checkLogin()
		resultRunning = ssh.status()
		result = ssh.execute_mc(command)
		yield render("manager_command.htm", {"result":"\n".join([resultRunning[0], result[0]])})
	manager_command.exposed = True
	
	def manager_stop(self):
		ssh = self._checkLogin()
		result = ssh.stop()
		yield render("manager_stop.htm", {"result":result[0]})
	manager_stop.exposed = True
	def manager_start(self):
		ssh = self._checkLogin()
		result = ssh.start()
		yield render("manager_start.htm", {"result":result[0]})
	manager_start.exposed = True
	def manager_restart(self):
		ssh = self._checkLogin()
		result1 = ssh.stop()
		result2 = ssh.start()
		yield render("manager_restart.htm", {"result":"\n".join([result1[0], result2[0]])})
	manager_restart.exposed = True
	def manager_kill(self):
		ssh = self._checkLogin()
		result = ssh.kill()
		yield render("manager_kill.htm", {"result":result[0] if len(result[0])>0 else result[1]})
	manager_kill.exposed = True
	def manager_status(self):
		ssh = self._checkLogin()
		result = ssh.status()
		yield render("manager_status.htm", {"result":result[0]})
	manager_status.exposed = True
	
	def logout(self):
		cherrypy.session.clear()
		yield render("logout.htm", {})
	logout.exposed = True

if __name__ == '__main__' or 'uwsgi' in __name__:
	appconf = {
		'/': {
			'tools.proxy.on':True,
			'tools.proxy.base': "http://manager.myminecraftserver.com",
			'tools.sessions.on':True,
			'tools.sessions.storage_type':'file',
			'tools.sessions.storage_path':'/opt/manager/sessions/',
			'tools.sessions.timeout':525600,
			'request.show_tracebacks': True
		},
		'/static': {
			'tools.staticdir.on': True,
			'tools.staticdir.dir': "/opt/manager/static/"
		}
	}
	cherrypy.config.update({
		'server.socket_port':8080,
		'server.thread_pool':1,
		'server.socket_host': '0.0.0.0',
		'sessionFilter.on':True,
		'server.show.tracebacks': True
	})
	cherrypy.server.socket_timeout = 5
	approot = mcmanager()
	application = None
	print("Ready to start application !")
	if(len(sys.argv)>1 and sys.argv[1]=="test"):
		application = cherrypy.quickstart(approot, "", appconf)
	else:
		sys.stdout = sys.stderr
		cherrypy.config.update({'environment': 'embedded'})
		application = cherrypy.tree.mount(approot, "", appconf)
