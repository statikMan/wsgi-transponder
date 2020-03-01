'''
	WSGI Transponder, (c) Copyright 2020, Nicolas Georges

	WSGI Transponder make easy to plugin any application server under a WSGI server such as Waitress or Passenger.
	It is compatible with 2.7.15 

	LICENSE : Artistic License 2.0
	https://opensource.org/licenses/artistic-license-2.0
'''
import sys, os, socket, json, subprocess, signal, re, time, traceback
from pprint import pprint
from datetime import datetime
#For python's noob like me:
#import pdb
#For JIT debugging, place a call to `pdb.set_trace()` where you want a JIT breakpoint
#Get methods of an object from the debugger:
#	def get_methods(obj): return [method_name for method_name in dir(obj) if callable(getattr(obj, method_name))]
#	get_methods(env)
#from var_dump import var_dump
#from hexdump import hexdump

def VERSION(): 
	return '1.00'

options = None
def trace(*args):
	global options
	with open(options['trace'], 'a') as f:
		prefix = "[" + str(datetime.now()) + "] "
		for msg in args: 
			if type(msg) is str: 
				f.write(prefix + msg + "\n")
			else: 
				#dump an object
				pprint(msg, f)
		f.close()

debug = False
def trace_debug(*args):
	global debug
	if debug: trace(*args)

try:
	with open('transponder.config.json', 'r') as f: 
		config = json.load(f)
	profile = os.getenv('WSGIT_PROFILE', config['default'])
	options = config['profiles'][profile]
	debug = options['debug']
	trace("WSGI Transponder v" + VERSION() + " Copyright 2020, Nicolas Georges")
	trace_debug("Profile:", profile, "Options:", options)

except Exception, e:
	print "WSGI Transponder v" + VERSION() + " - Load configuration error: "
	print traceback.format_exc()
	exit(-1)

worker = None
def get_worker():
	global worker, debug
	#return
	if not worker is None :
		trace_debug("worker.pid = " + str(worker.pid) + ", worker.poll()=" + str(worker.poll()))
	if (worker is None) or not (worker.poll() is None) :
		trace_debug("start worker")

		devnull = open(os.devnull, "wb")
		worker = subprocess.Popen(
			options['arguments'], 
			#stdin=devnull, stdout=devnull, stderr=devnull, 
			shell=options['shell'])
		worker.poll()

		trace_debug("Worker pid=" + str(worker.pid))

		#Wait until process respond to options['port']			
		checkclient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		i = 500 #max of 5 secs
		while i :
			i -= 1
			try:	
				checkclient.connect((options['host'], options['port']))
				break
			except Exception:
				pass
			trace_debug("Waiting for worker: " + str(500 - i) + "/500")
			time.sleep(0.01)
		checkclient.close()

		return worker

def stop_worker(signal, frame):
	global worker
	if not worker is None :
		trace("Stop worker of pid " + str(worker.pid))
		#FIXME: on windows (at least), that does not kill shell (cmd.Exe)
		worker.terminate()
	exit(0)
	
signal.signal(signal.SIGINT, stop_worker)

#pre-load worker
get_worker()

def application(environ, start_response):
	global debug

	try:
		#log the request
		trace(environ['REQUEST_METHOD'] + " " + environ['PATH_INFO'] + " " + environ['SERVER_PROTOCOL'] 
			+ " [remote host:" + environ.get('REMOTE_ADDR', environ.get('HTTP_X_REAL_IP', environ.get('REMOTE_HOST'))) + "]")
		#assert the worker exists : must be improved to check alive and restart
		get_worker()

		if debug:
			trace_debug("ENVIRONMENT:")
			for k in environ:
				trace_debug("  env["+k+"] = " + str(environ[k]))

		#inject Accept-Encoding : todo, should be based on HTTP_USER_AGENT; or from config/env var
		if options['force-accept-encoding']:
			trace_debug("Injecting Accept-Encoding = " + options['accept-encoding'])
			environ['HTTP_ACCEPT_ENCODING']=options['accept-encoding']

		header = environ['REQUEST_METHOD'] + " " + environ['PATH_INFO'] + " " + environ['SERVER_PROTOCOL'] + "\n"
		input = environ['wsgi.input']
		errors= environ['wsgi.errors']
		for k in filter(lambda s: s.startswith('HTTP_') , environ.keys()) : 
			v = environ[k]
			k2= k.replace('HTTP_','').title().replace('_','-')
			#convert HTTP_ keys by removing HTTP_, make it camelCase, replace _ by -
			header = header + k2 + ": " + v + "\n"

		content = ""
		#may not have content type
		if 'CONTENT_TYPE' in environ :
			trace_debug("* read from input")
			content = input.read()
			trace_debug("* input=" + content)
			header = header + 'Content-Length: ' + str(len(content)) + "\n"
			header = header + 'Content-Type: ' + environ['CONTENT_TYPE'] + "\n"
		header = header.replace("\r","")
		req = header + "\n" + content
		
		#may implement an little static file router here, by looking at PATH_INFO (in GET mode only)
		#this belongs to /public/ (may be a json config file option) using wsgi.file_wrapper if available
		# for better performance
		#	https://www.python.org/dev/peps/pep-0333/#optional-platform-specific-file-handling
		
		trace_debug("<<<<<<<<<<", "Reconstitued request:", req) #, hexdump(req)

		#initiate a request to the worker
		clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		clientsocket.connect((options['host'], options['port']))
		clientsocket.send(req)
		
		clientfile = clientsocket.makefile()
		buf = ""
		while True:
			line = clientfile.readline()
			#~ print hexdump(line)
			if line == "\r\n" : 
				break
			buf += line

		if len(buf) > 0: trace_debug(">>>>>>>>>>", buf)
		#transform plain header  into the wsgi specification header form
		headers = buf.split("\r\n")
		#trace response status
		trace(headers[0])
		status = headers[0].split(' ')[1]
		#delete status from headers, and empty last line
		del headers[0]
		del headers[-1]
		headers = map(lambda i: tuple(i.split(': ')), headers)
		writer = start_response(status, headers)

		''' https://www.python.org/dev/peps/pep-0333/#specification-details
		When called by the server, the application object must return an iterable yielding zero or more strings. This can be accomplished in a variety of ways, such as by returning a list of strings, or by the application being a generator function that yields strings, or by the application being a class whose instances are iterable. Regardless of how it is accomplished, the application object must always return an iterable yielding zero or more strings.
		'''
		m = re.search('Content-Length:\s*(\d+)', buf)
		if m is None : 
			#No content
			yield ""

		#This should be likely non blocking compatible...
		content_length = int(m.group(1))
		while True :
			content = clientfile.read(content_length if content_length < 512 else 512)
			content_length -= len(content)
			yield content
			if content_length <= 0 :
				break
	except Exception, e:
		trace("WSGI Transponder error: ", traceback.format_exc())

#For testing using waitress
if __name__ == "__main__":
	from waitress import serve
	serve(application, host='0.0.0.0', port=5001)
