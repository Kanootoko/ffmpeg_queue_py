'''This is a console program which provides queue feautue for ffmpeg. It can be used with other applications, if needed
Version: 1.0.0 [2018.08.23]
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
2. Interface.
	  After running program, you get to console interface, where you can see list of commands and how your
	executing string looks like at the moment. You can skip interface step by console command or with parameter in
	configuration file [both feautues not implemented yet]
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
	
def save(filename, savelist):
	'Function for saving configuration in file. Takes filename ans tuple of all user-defined parameters'
	import configparser
	f = open(filename, 'w')
	saving = configparser.ConfigParser()
	saving.add_section('default')
	tmpFormats = savelist[3]
	tmpOutDir = savelist[6]
	savelist[3] = ','.join(savelist[3])
	if len(savelist[6].split()) == 2 and savelist[6].split()[0].endswith('Output') and savelist[6].split()[1].isalnum():
		savelist[6] = ''
	for name, val in zip(('ffmpeg_path', 'input_params', 'output_params', 'input_formats', \
	                      'output_format', 'input_dir', 'output_dir', 'threads'), savelist):
		saving['default'].update({name: str(val)})
	savelist[3] = tmpFormats
	savelist[6] = tmpOutDir
	saving.write(f)
	f.close()
	
def load(filename):
	'Function for loading configuration file. Returns tuple of all user-defined parameters'
	import configparser
	loading = configparser.ConfigParser()
	loading.read(filename)
	if not 'default' in loading.sections():
		return (False, ())
	loaded = {'ffmpeg_path': 'ffmpeg', 'input_params': '-i', 'output_params': '-c copy', \
	          'input_formats': 'avi', 'output_format': 'mkv', 'input_dir': '.', 'output_dir': './Output {}'.format(int(time.time())), \
	          'threads': 1}
	loaded.update(dict(loading['default']))
	if loaded['output_dir'] == '':
		loaded['output_dir'] = './Output {}'.format(int(time.time()))
	return (True, (loaded['ffmpeg_path'], loaded['input_params'], loaded['output_params'], \
	                      ' '.join(loaded['input_formats'].split(',')).replace('[', '').replace(']', '').replace('\'', '').replace('"', '').split(), \
	                      loaded['output_format'], loaded['input_dir'], loaded['output_dir'], int(loaded['threads'])))

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

def main(argv):

	ffmpeg_path = 'ffmpeg'
	input_params = '-i'
	output_params = '-c copy'
	input_formats = ['avi']
	output_format = 'mkv'
	input_dir = '.'
	output_dir = os.path.normpath('./Output {}'.format(int(time.time())))
	threads = 1
	
	try:
		trying = load('default.ini')
		if trying[0]:
			(ffmpeg_path, input_params, output_params, input_formats, output_format, input_dir, output_dir, threads) = trying[1]
	except Exception:
		pass

	# parsing arguments
	for el in argv[1:]:
		if el in ('help', '--help', '-h', '-help', '/h', '/?'):
			print(__doc__)
			return 0
		elif el.startswith(('--ffmpeg_path=', '-ffpath=')):
			ffmpeg_path = el.split('=')[1]
		elif el.startswith(('--input_formats=', '-if=')):
			input_formats = ' '.join(el.split('=')[1].split(',')).split()
		elif el.startswith(('--output_format=', '-of=')):
			output_format = el.split('=')[1]
		elif el.startswith(('--input_dir=', '-id=')):
			input_dir = el.split('=')[1]
		elif el.startswith(('--output_dir=', '-od=')):
			output_dir = el.split('=')[1]
		elif el.startswith(('--input_parameters=', '-ip=')):
			input_params = el.split('=')[1]
		elif el.startswith(('--output_parameters=', '-op=')):
			output_params = el.split('=')[1]
		elif el.startswith('threads='):
			try:
				threads = int(el.split('=')[1])
			except ValueError:
				threads = 1
				print('Error with threads parameter: \'{}\''.format(el))
		elif el.startswith(('--config_file=', '-cfg=')):
			trying = ''
			try:
				trying = load(el.split('=')[1])
			except Exception as exc:
				print('Error occured while loading: {}'.format(exc))
				trying = (False, ())
			if trying != '' and trying[0]:
			    (ffmpeg_path, input_params, output_params, input_formats, output_format, input_dir, output_dir, threads) = trying[1]

	while True:
		print('-' * (os.get_terminal_size().columns // 2))
		print('Now execution string looks like this:')
		print('{} {} {} {} {}'.format(ffmpeg_path, input_params, \
		      os.path.normpath('"' + input_dir + '/<filename>.' + (str(input_formats) if len(input_formats) > 1 else input_formats[0]) + '"'), \
		      output_params, os.path.normpath('"' + output_dir + '/<filename>.' + output_format + '"') \
		                             ))
		cnt = 0
		for fname in os.listdir(input_dir):
			cnt += fname.endswith(tuple(input_formats))
		print('{} files found'.format(cnt))

		print('List of commands:')
		print('\t"ffpath" / "ffmpeg_path" - change path to ffmpeg executable file', '[{}]'.format(ffmpeg_path))
		print('\t"if" / "input_formats" / "input_format" / "fin"- change input format(s)', input_formats)
		print('\t"of" / "output_format" / "fout" - change output format', '[{}]'.format(output_format))
		print('\t"id" / "input_dir" / "din" - change input directory', '[{}]'.format(input_dir))
		print('\t"od" / "output_dir" / "dout" - change output directory', '[{}]'.format(output_dir))
		print('\t"ip" / "input_params" / "input_parameters" - change input parameters string', '[{}]'.format(input_params))
		print('\t"op" / "output_params" / "output_parameters" - change output parameters string', '[{}]'.format(output_params))
		print('\t"threads" - change number of ffmpegs running at one time', '[{}]'.format(threads))
		print('\t"save <filename>" - save current configuration to <filename> file"')
		print('\t"load <filename>" - load configuration from <filename> file"')
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
					ffmpeg_path = os.path.normpath(data)
					print('Accepted, ffmpeg_path changed to \'{}\''.format(ffmpeg_path))
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
					input_formats = ' '.join(data.split(',')).split()
					print('Accepted, input_formats list changed to {}'.format(input_formats))
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
					output_format = ' '.join(data.split(',')).split()[0]
					print('Accepted, output_formats list changed to \'{}\''.format(output_format))
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
					input_dir = os.path.normpath(os.path.abspath(data))
					print('Accepted, input_dir path changed to \'{}\''.format(input_dir))
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
					output_dir = os.path.normpath(os.path.abspath(data))
					print('Accepted, output_dir path changed to \'{}\''.format(output_dir))
					break
				elif (data == 'halt'):
					print('Cancelled')
					break
				else:
					print('Error. Path is not correct: \'{}\''.format(data))
					data = ''
		elif comm.startswith(('ip', 'input_params', 'input_parameters')):
			if data == '':
				input_params = input('Enter a string for input parameters')
			else:
				input_params = data
			print('Accepted, new input parameters string is \'{}\''.format(input_params))
		elif comm.startswith(('op', 'output_params', 'output_parameters')):
			if data == '':
				output_params = input('Enter a string for output parameters')
			else:
				output_params = data
			print('Accepted, new output parameters string is \'{}\''.format(output_params))
		elif comm.startswith('threads'):
			while True:
				if data == '':
					data = input('Enter number of threads you need (or "halt" to cancel): ')
				if data == 'halt':
					break
				try:
					assert(int(data) > 0)
					threads = int(data)
					if threads > os.cpu_count():
						print('Warning: number of threads that you\'ve entered is larger than ' \
						      'your computer\'s number of cpus: {}, but {} threads'.format(os.cpu_count(), threads))
					else:
						print('Accepted')
					break
				except:
					print('Error of decoding your "number": \'{}\'. Try again'.format(data))
					data = ''
		elif comm.startswith('save'):
			if data == '':
				data = input('Enter path to save current configuration: ')
			try:
				save(data, [ffmpeg_path, input_params, output_params, input_formats, output_format, input_dir, output_dir, threads])
			except Exception as exc:
				print('Error occured while saving: {}'.format(exc))
			else:
				print('Save is completed successfully')
		elif comm.startswith('load'):
			if data == '':
				data = input('Enter path to configuration file to load: ')
			trying = ''
			try:
				trying = load(data)
			except Exception as exc:
				print('Error occured while loading: {}'.format(exc))
				trying = (False, ())
			if trying != '' and trying[0]:
			    (ffmpeg_path, input_params, output_params, input_formats, output_format, input_dir, output_dir, threads) = trying[1]
			    print('Loaded successfully')
			else:
				print('Error while loading. Are you sure that configuration file is correct?')
		elif comm in ('exit', 'stop', 'quit'):
			print('Exiting now')
			return 0
		elif comm in ('', 'start', 'go'):
			print('Start working.')
			save('lastconfig.ini', [ffmpeg_path, input_params, output_params, input_formats, output_format, input_dir, output_dir, threads])
			print('Current config has been written to "lastconfig.ini"')
			break
		else:
			print('Error. unknown command: "{}"'.format(comm))
		print('\n')

	# working
	jobs = []
	for fname in os.listdir(input_dir):
		if fname.endswith(tuple(input_formats)):
			jobs.append(fname)
	if len(jobs) > 0 and not os.path.exists(output_dir):
		os.mkdir(output_dir)
	jobs = tuple(jobs)
	if threads == 1:
		for fname in jobs:
			command = (ffmpeg_path, input_params, os.path.normpath(input_dir + '/' + fname), \
			           *split_quotes(output_params), os.path.normpath(output_dir + '/' + fname[:fname.rfind('.') + 1] + output_format))
			print(ffmpeg_path, input_params, os.path.normpath('"' + input_dir + '/' + fname + '"'), \
			      *split_quotes(output_params), os.path.normpath('"' + output_dir + '/' + fname[:fname.rfind('.') + 1] + output_format + '"'))
			change_title(fname)
			subprocess.call(command)
	else:
		import multiprocessing
		processes = [None] * threads
		pipes = [None] * threads
		action_pipe = multiprocessing.Pipe()
		for cnt in range(min(threads, len(jobs))):
			print('Starting thread {}'.format(cnt))
			pipes[cnt] = multiprocessing.Pipe()
			processes[cnt] = multiprocessing.Process(target = process, args = (cnt, pipes[cnt][0], action_pipe[0]))
			processes[cnt].start()
		for job in jobs:
			what_to_do = action_pipe[1].recv()
			choose = None
			for num in range(threads):
				if pipes[num][1].poll():
					choose = num
					break
			pipes[choose][1].recv()
			pipes[choose][1].send('start "{}" /WAIT '.format(job) + ffmpeg_path + ' ' + input_params + \
			                      os.path.normpath(' "' + input_dir + '/' + job + '" ') + output_params + \
			                      os.path.normpath(' "' + output_dir + '/' + job[:job.rfind('.') + 1] + output_format + '"')
			                     )
		for num in range(min(threads, len(jobs))):
			what_to_do = action_pipe[1].recv()
			for num in range(threads):
				if pipes[num][1].poll():
					pipes[num][1].recv()
					pipes[num][1].send(None)
					processes[num].join()
	if os.path.isdir(output_dir) and len(os.listdir(output_dir)) == 0:
		print('Output folder is empty, it will be deleted')
		os.rmdir(output_dir)
	pause()

if __name__ == '__main__':
	main(sys.argv)