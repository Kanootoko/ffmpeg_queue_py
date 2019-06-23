'''This is a console program which provides queue feature for ffmpeg. It can be used with other applications, if needed
Version: 1.1.0 [2018.09.19]
Usage:
1. Console arguments.
	"--help" - print this help message and terminate program
	"--ffmpeg_path=<path>" or "-ffpath=<path>" - set path to ffmpeg executable
	"--input_formats=<string>" or "-if=<string>" or "-fin=<string>" - set input format(s)
	    for input pattern. For multiple formats you should use commas. -if=mkv,avi,mp4
	"--output_format=<string>" or "-of=<string>" or "-fout=string" - set output format
	    for output pattern
	"--input_dir=<path>" or "-id=<path>" or "-din=<path>" - set path to directory with input files
	"--output_dir=<path>" or "-od=<path>" or "-dout=<path>" - set path to directory for output files
	    (if it doesen't exists, but can be created, it will be)
	"--input_parameters=<string>" or "-ip=<string>" - set string which will be put before input file path
	    (it should end with "-i" or else ffmpeg error will occur)
	"--output_parameters=<string>" or "-op=<string>"- set string which will be put before output file path
	"--threads=<int>" - change number of ffmpegs running at one time
	"--config_file=<path>" or "-cfg=<path>" - load configuration from <path>. By default, script tries to
	    load config file "default.ini" in directory of launching.
	"--shutdown" or "-s" - computer will be shut down after the script is finished
	"--hibernate" or "--hibernation" or "-h" - computer will be hibernated after the script is finished
	"--no_user" or "-no_user" - no interface will be shown, only commands passed with command line or configuration file
2. Interface.
	  After running program, you get to console interface, where you can see list of commands and how your
	executing string looks like at the moment. You can skip interface step by console command ("--no_user")
	or with parameter in configuration file (no_user = true)
3. Some notes.
	  Script is developed and tested (a little bit) under Windows 10 platform with python 3.7.0.
	Linux support will be implemented in future versions. I hope so. Nevertheless, one-threaded mode could work now.
	  Data which comes with console parameters practically never tested on correctness. Same with configuration files.
	In other words, you can easily get some exception or program would work incorrectly if you're not careful enough with those.'''
import sys
import os
import subprocess
import time

def pause():
	'Pause function. There should be commands both for Windows and Linux systems'
	if os.sys.platform == 'win32':
		subprocess.call('pause', shell=True)
	else: # other cases?
		input('Press enter to continue...')

def change_title(title):
	'Function that changes current window title. Used for one-threaded mode. There should be command for Linux too'
	if os.sys.platform == 'win32':
		subprocess.call('title {}'.format(title), shell=True)
	
def save_properties(props, filename):
	'Function for saving configuration in file. Takes properties class and filename'
	import configparser
	f = open(filename, 'w')
	saving = configparser.ConfigParser()
	saving.add_section('default')

	savedict = dict()
	for key in set(filter(lambda x: not x.startswith('_'), dir(props))):
		savedict[key] = str(getattr(props, key))
	if savedict['output_dir'] and len(savedict['output_dir'].split()) == 2 and \
	   savedict['output_dir'].split()[0].endswith('Output') and savedict['output_dir'].split()[1].isalnum():
		del savedict['output_dir']
	saving['default'].update(savedict)
	saving.write(f)
	f.close()
	
def load_properties(props, filename):
	'Function for loading configuration file. Edits properties class given in parameters'
	import configparser
	loading = configparser.ConfigParser()
	loading.read(filename)
	default_props = properties()
	if not 'default' in loading.sections():
		raise ValueError('no \'default\' section is found; load is aborted')
	loading = loading['default']
	params = set(filter(lambda x: not x.startswith('_'), dir(props)))
	for param in params:
		if param in loading:
			#print('setting {} to {}'.format(param, loading[param]))
			setattr(props, param, loading[param])
		else:
			#print('setting {} to {} from default'.format(param, getattr(default_props, param)))
			setattr(props, param, getattr(default_props, param))

def split_quotes(string):
	string = string.split()
	i = 0
	skip = False
	while i < len(string):
		if string[i].count('"') % 2 != 0 and not skip:
			if i + 1 < len(string):
				string[i] += ' ' + string[i + 1]
				del string[i + 1]
			else:
				skip = True
			continue
		else:
			#if string[i][0] == string[i][-1] == '"':
			#	string[i] = string[i][1:-1]
			string[i] = string[i].replace('"', '')
			i += 1
	return string

def process(number, parent_pipe, action_pipe):
	'''This is process working function. All of the processess have the same action_pipe, but parent_pipe is
	unique for each of them. Sending anything in action_pipe will activate main process, that will give work
	to those processes, which sent somethins at their parent_pipe.'''
	result = True
	while True:
		parent_pipe.send(result)
		action_pipe.send('encoded')
		job = parent_pipe.recv()
		if job == None:
			print('Thread {} finished at {}'.format(number, time.ctime()))
			return
		print('{}: Thread {} takes [[{}]]'.format(time.ctime(), number, job))
		subprocess.getoutput(job)

class shutdown:
	'''This class is for easy choice between shutdown, hibernation and nothing'''
	def __init__(self, type_ = '-', time = 30):
		from re import match, findall
		if isinstance(type_, list):
			type_ = ' '.join(type_)
		m = match('^([Hh](ibernation)?|[Ss](hutdown)?)[^\d]*(\d+)( seconds)?$', type_)
		if m is not None:
		    m = findall('(\w)\w*[^\d]*(\d+)', type_)[0]
		    type_ = m[0]
		    time = m[1]
		if type_ in ('hibernate', 'hibernation', '/h', 'h', 'H'):
			self._type = 'h'
		elif (type_ in ('shutdown', '/s', 's', 'S')):
			self._type = 's'
		else:
			self._type = '-'
		try:
			self._time = int(time)
		except ValueError:
			self._time = 30

	def __str__(self):
		if self._type == 's':
			return 'Shutdown in {} seconds'.format(self._time)
		elif self._type == 'h':
			return 'Hibernation in {} seconds'.format(self._time)
		else:
			return 'No shutdown is planned'
	def __repr__(self):
		return (self._type + ' ' + self.time) if self._type != '-' else self._type

	@property
	def type(self):
		return self._type

	@type.setter
	def type(self, new_type):
		if new_type in ('h', 'hibernate', 'hibernation', '/h'):
			self._type = 'h'
		elif (new_type in ('s', 'shutdown', '/s')):
			self._type = 's'
		else:
			self._type = '-'

	@property
	def time(self):
		return self._time

	@time.setter
	def time(self, new_time):
		try:
			self._time = new_time
		except ValueError:
			return False

	def execute(self):
		'''Shutdown will be launched as "shutdown /s /t <time>" and can be cancelled as "shutdown /a".
		But hibernation cannot be run like this, to stop the process, the file ".stayon" must be created in directory of script.
		Or Crl+C can be hit as well.'''
		if self._type == '-' or os.path.isfile('.stayon'):
			return
		change_title(str(self))
		if self._type == 'h':
			subprocess.call(('msg', os.getlogin(), 'Computer will be hibernated in {} seconds'.format(self._time)))
			print('Hibernating in {} seconds after {}'.format(self._time, time.ctime()))
			print('----- If you wish to stop the process, hit Ctrl + C on keyboard -----')
			try:
				time.sleep(self.time)
			except KeyboardInterrupt:
				print('Hibernation cancelled')
				return
			if os.path.isfile('.stayon'):
				return
			subprocess.call(('shutdown', '/h'))
		else:
			if os.path.isfile('.stayon'):
				return
			subprocess.call(('shutdown', '/s', '/t', str(self._time)))

class properties:
	def __init__(self):
		self.ffmpeg_path = 'ffmpeg'
		self.input_params = '-i'
		self.output_params = '-c copy'
		self._input_formats = ['avi']
		self.output_format = 'mkv'
		self.input_dir = '.'
		self._output_dir = os.path.normpath('./Output {}'.format(int(time.time())))
		self._threads = 1
		self._finish = shutdown()
		self._no_user = False
	@property
	def input_formats(self):
		return self._input_formats
	@input_formats.setter
	def input_formats(self, new_input_formats):
		if isinstance(new_input_formats, str):
			from re import match
			if match('^\[(.*)*\]$', new_input_formats) is not None:
				self._input_formats = list(map(lambda x: x[1:-1] if x.startswith("'") and x.endswith("'") else x, new_input_formats[1:-1].split(', ')))
			else:
				self._input_formats = ' '.join(new_input_formats.split(',')).split()
		else:
			self._input_formats = new_input_formats
	@property
	def threads(self):
		return self._threads
	@threads.setter
	def threads(self, new_threads):
		try:
			self._threads = int(new_threads)
		except:
			pass
	@property
	def no_user(self):
		return self._no_user
	@no_user.setter
	def no_user(self, new_no_user):
		if isinstance(new_no_user, str):
			self._no_user = True if new_no_user.lower() in ('true', 't', '1', True, 'yes', 'on') else False
		else:
			self._no_user = bool(new_no_user)
	@property
	def output_dir(self):
		return self._output_dir
	@output_dir.setter
	def output_dir(self, new_output_dir):
		self._output_dir = './Output {}'.format(int(time.time())) if new_output_dir == '' else new_output_dir

	@property
	def finish(self):
		return self._finish
	@finish.setter
	def finish(self, new_finish):
		if isinstance(new_finish, str):
			self._finish = shutdown(new_finish.split())
		else:
			self._finish = new_finish

def main(argv):

	props = properties()
	try:
		load_properties(props, 'default.ini')
	except:
		pass

	# parsing arguments
	for el in argv[1:]:
		if el in ('help', '--help', '-h', '-help', '/h', '/?'):
			print(__doc__)
			return 0
		elif el.startswith(('--ffmpeg_path=', '-ffpath=')):
			props.ffmpeg_path = el.split('=')[1]
		elif el.startswith(('--input_formats=', '-if=')):
			props.input_formats = ' '.join(el.split('=')[1].split(',')).split()
		elif el.startswith(('--output_format=', '-of=')):
			props.output_format = el.split('=')[1]
		elif el.startswith(('--input_dir=', '-id=')):
			props.input_dir = el.split('=')[1]
		elif el.startswith(('--output_dir=', '-od=')):
			props.output_dir = el.split('=')[1]
		elif el.startswith(('--input_parameters=', '-ip=')):
			props.input_params = el.split('=')[1]
		elif el.startswith(('--output_parameters=', '-op=')):
			props.output_params = el.split('=')[1]
		elif el.startswith(('--threads=', '-threads=')):
			try:
				props.threads = int(el.split('=')[1])
			except ValueError:
				props.threads = 1
				print('Error with threads parameter: \'{}\''.format(el))
		elif el.startswith(('--config_file=', '-cfg=')):
			trying = ''
			try:
				load(props, el.split('=')[1])
			except Exception as exc:
				print('Error occured while loading: \'{}\''.format(exc))
				trying = (False, ())
			if trying != '' and trying[0]:
			    (props.ffmpeg_path, props.input_params, props.output_params, props.input_formats, \
			     props.output_format, props.input_dir, props.output_dir, props.threads, props.finish.type, \
			     props.finish.time, props.no_user) = trying[1]
		elif el in ('--shutdown', '-s'):
			props.finish.change_type('s')
		elif el in ('--hybernation', '--hibernate', '-h'):
			props.finish.change_type('h')
		elif el.startswith(('--shutdown_time=', '-time=')):
			props.finish.change_time(el.split('=')[1])
		elif el in ('--no_user', '-no_user'):
			props.no_user = True
		else:
			print('Unknown console parameter: {}'.format(el))

	while not props.no_user:
		print('-' * (os.get_terminal_size().columns // 2))
		print('Now execution string looks like this:')
		print('{} {} {} {} {}'.format(props.ffmpeg_path, props.input_params, \
		      os.path.normpath('"' + props.input_dir + '/<filename>.' + (str(props.input_formats) if len(props.input_formats) > 1 else props.input_formats[0]) + '"'), \
		      props.output_params, os.path.normpath('"' + props.output_dir + '/<filename>.' + props.output_format + '"') \
		                             ))
		cnt = 0
		for fname in os.listdir(props.input_dir):
			cnt += fname.endswith(tuple(props.input_formats))
		print('{} files found'.format(cnt))

		print(props.finish)
		print('List of commands:')
		print('\t"ffpath" / "ffmpeg_path" - change path to ffmpeg executable file', '[{}]'.format(props.ffmpeg_path))
		print('\t"if" / "input_formats" / "input_format" / "fin"- change input format(s)', props.input_formats)
		print('\t"of" / "output_format" / "fout" - change output format', '[{}]'.format(props.output_format))
		print('\t"id" / "input_dir" / "din" - change input directory', '[{}]'.format(props.input_dir))
		print('\t"od" / "output_dir" / "dout" - change output directory', '[{}]'.format(props.output_dir))
		print('\t"ip" / "input_params" / "input_parameters" - change input parameters string', '[{}]'.format(props.input_params))
		print('\t"op" / "output_params" / "output_parameters" - change output parameters string', '[{}]'.format(props.output_params))
		print('\t"threads" - change number of ffmpegs running at one time', '[{}]'.format(props.threads))
		print('\t"save <filename>" - save current configuration to <filename> file"')
		print('\t"load <filename>" - load configuration from <filename> file"')
		print('\t"s_ty" / "shutdown_type" - chage type of action after finishing ("-" or "shutdown" / "s" or "hibernation" / "h")')
		print('\t"s_ti" / "shutdown_time" - change time between finishing and shutdown/hibernation')
		print('\t"exit" / "stop" / "quit" - exit the script')
		print('\t"start" / "go" / <empty_string> - start the script')

		comm = input('>>> ')
		pth = ''
		data = ''
		oneline = tuple(comm.split())
		if len(oneline) > 1:
			data = ' '.join(oneline[1:])
		del oneline
		if comm.startswith(('ffpath', 'ffmpeg_path')):
			while True:
				if data == '':
					data = input('Enter path to ffmpeg executable (or "halt" to cancel): ')
				if os.path.isfile(data) or True:
					props.ffmpeg_path = os.path.normpath(data)
					print('Accepted, ffmpeg_path changed to \'{}\''.format(props.ffmpeg_path))
					break
				elif (data == 'halt'):
					print('Cancelled')
					break
				else:
					print('Error. Path is not correct \'{}\''.format(data))
					data = ''
		elif comm.startswith(('if', 'inupt_format', 'fin')):
			while True:
				if data == '':
					data = input('Enter format(s) for input (or "halt" to cancel): ')
				if len(data) > 0:
					props.input_formats = data
					print('Accepted, input_formats list changed to {}'.format(props.input_formats))
					break
				elif (data == 'halt'):
					print('Cancelled')
					break
				else:
					print('Error. Empty string is not acceptable')
					data = ''
		elif comm.startswith(('of', 'output_format', 'fout')):
			while True:
				if data == '':
					data = input('Enter format for output (or "halt" to cancel): ')
				if len(data) > 0 and len(' '.join(data.split(',')).split()) == 1:
					props.output_format = ' '.join(data.split(',')).split()[0]
					print('Accepted, output_formats list changed to \'{}\''.format(props.output_format))
					break
				elif (data == 'halt'):
					print('Cancelled')
					break
				else:
					print('Error. Empty strings or strings contining spaces or commas are not acceptable: \'{}\''.format(data))
					data = ''
		elif comm.startswith(('id', 'input_dir', 'din')):
			while True:
				if data == '':
					data = input('Enter path to input dirctory (or "halt" to cancel): ')
				if os.path.isdir(data):
					props.input_dir = os.path.normpath(os.path.abspath(data))
					print('Accepted, input_dir path changed to \'{}\''.format(props.input_dir))
					break
				elif (data == 'halt'):
					print('Cancelled')
					break
				else:
					print('Error. Path is not correct: \'{}\''.format(data))
					data = ''
		elif comm.startswith(('od', 'output_dir', 'dout')):
			while True:
				if data == '':
					data = input('Enter path to input dirctory (or "halt" to cancel): ')
				if os.access('\\'.join(os.path.split(os.path.abspath(data))[:-1]), os.W_OK):
					props.output_dir = os.path.normpath(os.path.abspath(data))
					print('Accepted, output_dir path changed to \'{}\''.format(props.output_dir))
					break
				elif (data == 'halt'):
					print('Cancelled')
					break
				else:
					print('Error. Path is not correct: \'{}\''.format(data))
					data = ''
		elif comm.startswith(('ip', 'input_params', 'input_parameters')):
			if data == '':
				props.input_params = input('Enter a string for input parameters')
			else:
				props.input_params = data
			print('Accepted, new input parameters string is \'{}\''.format(props.input_params))
		elif comm.startswith(('op', 'output_params', 'output_parameters')):
			if data == '':
				props.output_params = input('Enter a string for output parameters')
			else:
				props.output_params = data
			print('Accepted, new output parameters string is \'{}\''.format(props.output_params))
		elif comm.startswith('threads'):
			while True:
				if data == '':
					data = input('Enter number of threads you need (or "halt" to cancel): ')
				if data == 'halt':
					break
				try:
					assert(int(data) > 0)
					props.threads = int(data)
					if props.threads > os.cpu_count():
						print('Warning: number of threads that you\'ve entered is larger than ' \
						      'your computer\'s number of cpus: {}, but {} props.threads'.format(os.cpu_count(), props.threads))
					print('Accepted')
					break
				except:
					print('Error of decoding your "number": \'{}\'. Try again'.format(data))
					data = ''
		elif comm.startswith('save'):
			if data == '':
				data = input('Enter path to save current configuration: ')
			try:
				save_properties(props, data)
			except Exception as exc:
				print('Error occured while saving: \'{}\''.format(exc))
			else:
				print('Save is completed successfully')
		elif comm.startswith('load'):
			if data == '':
				data = input('Enter path to configuration file to load: ')
			try:
				load_properties(props, data)
			except Exception as exc:
				print('Error occured while loading: \'{}\''.format(exc))
			else:
			    print('Loaded successfully')
		elif comm.startswith(('s_ty', 'shutdown_type')):
			if data == '':
				props.finish.type = input('Enter "shutdown" / "s" to shut PC down, "hibernate" / "h" to hibernate it, "-" to keep it on')
			else:
				props.finish.type = data
		elif comm.startswith(('s_ti', 'shutdown_time')):
			if data == '':
				props.finish.time = input('Enter time before shutdown: ')
			else:
				props.finish.time = data
		elif comm == 'help':
			print(__doc__)
			pause()
		elif comm in ('exit', 'stop', 'quit'):
			print('Exiting now')
			return 0
		elif comm in ('', 'start', 'go'):
			print('Start working.')
			break
		else:
			print('Error. unknown command: "{}"'.format(comm))
		print('\n')

	save_properties(props, 'lastconfig.ini')
	print('Current config has been written to "lastconfig.ini"')
	# working
	jobs = []
	for fname in os.listdir(props.input_dir):
		if fname.endswith(tuple(props.input_formats)):
			jobs.append(fname)
	if len(jobs) > 0 and not os.path.exists(props.output_dir):
		os.mkdir(props.output_dir)
	jobs = tuple(jobs)
	if props.threads == 1:
		for i, fname in enumerate(jobs):
			command = (props.ffmpeg_path, *split_quotes(props.input_params), os.path.normpath(props.input_dir + '/' + fname), \
			           *split_quotes(props.output_params), os.path.normpath(props.output_dir + '/' + fname[:fname.rfind('.') + 1] + props.output_format))
			print(props.ffmpeg_path, props.input_params, os.path.normpath('"' + props.input_dir + '/' + fname + '"'), \
			      *split_quotes(props.output_params), os.path.normpath('"' + props.output_dir + '/' + fname[:fname.rfind('.') + 1] + props.output_format + '"'))
			change_title('[{} / {}] {}, {}'.format(i, len(jobs), fname, ', ', props.finish))
			subprocess.call(command)
	else:
		import multiprocessing
		processes = [None] * props.threads
		pipes = [None] * props.threads
		action_pipe = multiprocessing.Pipe()
		for cnt in range(min(props.threads, len(jobs))):
			print('Starting thread {}'.format(cnt))
			pipes[cnt] = multiprocessing.Pipe()
			processes[cnt] = multiprocessing.Process(target = process, args = (cnt, pipes[cnt][0], action_pipe[0]))
			processes[cnt].start()
		jobN = 0
		while True:
			what_to_do = action_pipe[1].recv()
			if jobN == len(jobs):
				break
			for num in range(props.threads):
				if pipes[num][1].poll():
					job = jobs[jobN]
					pipes[num][1].recv()
					if os.sys.platform == 'win32':
						pipes[num][1].send('start "{}" /WAIT '.format(job) + props.ffmpeg_path + ' ' + props.input_params + \
						                   os.path.normpath(' "' + props.input_dir + '/' + job + '" ') + props.output_params + \
						                   os.path.normpath(' "' + props.output_dir + '/' + job[:job.rfind('.') + 1] + props.output_format + '"')
						                  )
					else:
						pipes[num][1].send(props.ffmpeg_path + ' ' + props.input_params + os.path.normpath(' "' + props.input_dir + '/' + job + '" ') +\
						                   props.output_params + os.path.normpath(' "' + props.output_dir + '/' + job[:job.rfind('.') + 1] + props.output_format + '"') + \
						                   ' &')
					jobN += 1
					if jobN == len(jobs):
						break
		closed_threads = 0
		while closed_threads < props.threads:
			what_to_do = action_pipe[1].recv()
			for num in range(props.threads):
				if pipes[num][1].poll():
					pipes[num][1].recv()
					pipes[num][1].send(None)
					processes[num].join()
					closed_threads += 1
	if os.path.isdir(props.output_dir) and len(os.listdir(props.output_dir)) == 0:
		print('Output folder is empty, it will be deleted')
		os.rmdir(props.output_dir)
	props.finish.execute()
	if not props.no_user:
		pause()

if __name__ == '__main__':
	main(sys.argv)
