#!/usr/bin/env python
# coding: utf-8

# Version: 2015-02-19

# TODO: que faire pour un profil fonction du temps (cf. profileur js)
# TODO: faire en sorte de pouvoir se profiler soi meme: enorme
# TODO: deregistrer les threads spawnés par multiprocessing (genre les Queues)
# TODO: a chaque spawn de process, le sampler reinstalle les patchs par dessus
# TODO: donner un moyen (genre decorator) de patcher manuellement /
#		unifier le patchage de lib / monitoring de thread spawn
#		(plutot un couple spawn_process / spawn_thread)
# TODO: encore des conflits de noms / '__main__' quand l'interval est très court

__version__ = '0.1'
__author__ = 'Romain Vavassori'

import _mcp

import thread
import threading
import multiprocessing

import functools
import sys
import os
import xml.etree.ElementTree as xml
import inspect

import atexit
import argparse
import itertools
import Queue
import time
import re
import json

########################################################################
# Patching
########################################################################

class ThreadInfo:
	def __init__(self, accumulator, interval):
		self.accumulator = accumulator
		self.interval = interval
		
		self._lookup = {}
		self._lookup_lock = threading.Lock()

	def register_tid(self, frame_hide=(0, 0)):
		tid = _mcp.get_current_tid()
		python_tid = threading.current_thread().ident

		self._lookup_lock.acquire()
		self._lookup[tid] = (python_tid, frame_hide)
		self._lookup_lock.release()
		
	def unregister_tid(self):
		tid = _mcp.get_current_tid()
		
		self._lookup_lock.acquire()
		try:
			_, frame_hide = self._lookup[tid]
			del self._lookup[tid]
			return frame_hide
		finally:
			self._lookup_lock.release()

	def get_value(self, tid):
		self._lookup_lock.acquire()
		try:
			return self._lookup[tid]
		finally:
			self._lookup_lock.release()

	@staticmethod
	def stack_height():
		frame = inspect.currentframe()
		frame_count = 0
		while frame is not None:
			frame_count += 1
			frame = frame.f_back
		return frame_count - 1

	def watch_thread(self, func):
		@functools.wraps(func)
		def func_wrapper(*args, **kw):
			height = ThreadInfo.stack_height()
			self.register_tid(frame_hide=(height - 1, height))
			try:
				result = func(*args, **kw)
			finally:
				self.unregister_tid()
					
			return result
		return func_wrapper
	
	def watch_process(self, func):
		@functools.wraps(func)
		def func_wrapper(*args, **kw):
			sampler = Sampler(self.accumulator, self.interval)
			sampler.start()
			return func(*args, **kw)
		return func_wrapper

	def _thread_patch(self, start_func):
		@functools.wraps(start_func)
		def start_wrapper(function, args, kwargs={}):
			return start_func(self.watch_thread(function), args, kwargs)
		
		return start_wrapper

	def _multiprocessing_patch(self, start_func):
		@functools.wraps(start_func)
		def start_wrapper(Process_self):
			Process_self.run = self.watch_process(Process_self.run)
			return start_func(Process_self)
		
		return start_wrapper

	def install_patchs(self):
		"""Patch multithreading modules (thread, threading and
		multiprocessing) to track down thread events and react accordingly."""
		
		thread.start_new = self._thread_patch(thread.start_new)
		thread.start_new_thread = self._thread_patch(thread.start_new_thread)
		
		threading._start_new_thread = self._thread_patch(threading._start_new_thread)
		
		multiprocessing.Process.start = self._multiprocessing_patch(
			multiprocessing.Process.start)
		
########################################################################
# Sampling
########################################################################

class FrameInfo:
	@staticmethod
	def extract(frame):
		path = frame.f_code.co_filename
		return FrameInfo(
			path = path,
			name = FrameInfo.module_name(path),
			line = frame.f_lineno,
			func_name = frame.f_code.co_name,
			func_line = frame.f_code.co_firstlineno
		)
	
	@staticmethod
	def module_name(module_path):
		# Non-file module ('<string>', etc.)
		if not os.path.isfile(module_path):
			return module_path
		
		# Main module
		if os.path.samefile(module_path, sys.argv[0]):
			return '__main__'

		# Find module in sys.modules
		for name, module in sys.modules.items():
			if name != '__main__':
				try:
					if module.__file__.startswith(module_path):
						return name
				except AttributeError:
					pass

		# Is this case really possible ?
		name = os.path.splitext(module_path)[0].replace('/', '.')
		if name.endswith('.__init__'):
			name = name[:-9]

		return name
	
	def __init__(self, **kw):
		self.__dict__.update(kw)

class StackInfo:
	@staticmethod
	def extract(frame, hide=(0, 0)):
		stack = []
		
		while frame is not None:
			stack.append(FrameInfo.extract(frame))
			frame = frame.f_back
		
		# remove profiler frames
		i0, i1 = len(stack) - hide[1], len(stack) - hide[0]
		stack = [x for i, x in enumerate(stack) if not (i0 <= i < i1)]
		
		return stack

class Sampler(threading.Thread):
	def __init__(self, accumulator, interval, origin=False):
		threading.Thread.__init__(self)
		self.daemon = True
		
		self.accumulator = accumulator
		self.sampler = _mcp.Sampler(interval)
		
		# force queue init to avoid tracking its spawned thread.
		accumulator.send(None, None)
		
		self.thread_info = ThreadInfo(accumulator, interval)
		self.thread_info.install_patchs()
		
		# main thread has already spawned, we need to register it manually.
		height = ThreadInfo.stack_height()
		frame_hide = (0 if origin else height - 2, height - 1)
			
		self.thread_info.register_tid(frame_hide=frame_hide)
	
	def watch_thread(self, func):
		self.thread_info.watch_thread(func)
	
	def watch_process(self, func):
		self.thread_info.watch_process(func)
		
	def stop(self):
		self.running = False
	
	def run(self):
		self.running = True
	
		frame_hide = self.thread_info.unregister_tid()
		self.sampler.start()
		
		while self.running:
			samples = self.sampler.wait_samples()
			frames = sys._current_frames()
			stacks = {}
			
			for time_stamp, tid, running in samples:
				if running:
					try:
						py_tid, frame_hide = self.thread_info.get_value(tid)
					except KeyError:
						continue
					
					try:
						stack_info = stacks[py_tid]
					except KeyError:
						frame = frames[py_tid]
						stack_info = StackInfo.extract(frame, hide=frame_hide)
						stacks[py_tid] = stack_info
					
					self.accumulator.send(time_stamp, stack_info)
				else:
					self.accumulator.send(time_stamp, None)
					
		self.sampler.stop()
		self.thread_info.register_tid(frame_hide)

########################################################################
# Accumulating
#
# Collect samples from all running instances of profiled code and
# organize them.
#
########################################################################

class Accumulator:
	def __init__(self):
		self._queue = multiprocessing.Queue()
		self._samples = {}
	
	def listen(self, timeout):
		try:
			while True:
				time, data = self._queue.get(timeout=timeout)
				if time is not None:
					sample = self._samples.setdefault(time, [])
					if data is not None:
						sample.append(data)
		except Queue.Empty:
			pass
			
	def send(self, time, data):
		self._queue.put((time, data))
				
	def samples(self):
		return self._samples
	
########################################################################
# Formatting
########################################################################

class Xml(xml.Element):
	def __init__(self, tag, attrib={}, text=None):
		xml.Element.__init__(self, tag, attrib)
		self.text = text
		
	def tree(self):
		return xml.ElementTree(self)

	def append(self, *args):
		for arg in args:
			if isinstance(arg, Xml):
				xml.Element.append(self, arg)
			elif isinstance(arg, basestring):
				try:
					element = list(self)[-1]
				except IndexError:
					self.text = (self.text if self.text else '') + arg
				else:
					element.tail = (element.tail if element.tail else '') + arg
			else:
				TypeError(repr(type(arg)))
		return self
	
	def extend(self, *args):
		return self.append(*sum(args, []))

class ReportStructure:
	def __init__(self, title, general):
		self.document = Xml('html').append(Xml('head'), Xml('body'))
		
		# Head
		self.document.find('head').append(
			Xml('meta', {
				'http-equiv': 'Content-Type',
				'content': 'text/html; charset=utf-8'
			}),
			Xml('title', text=title),
			Xml('style', {'type': 'text/css'}, self._css()),
		)

		# Body
		self.add_title('General information')
		self.add_table([
			sum([[x, Xml('br')] for x in general[:-1:2]], []),
			sum([[x, Xml('br')] for x in general[1::2]], [])
		])

	def _css(self):
		css = '''
			span {
				width: 200px; height: 7px;
				display: inline-block; background-color: #ffffff;
			}
			.c{ display: inline-block; background-color: #0044ff; }
			.o{ display: inline-block; background-color: #00bbff; }
			
			td { padding-right: 14px; }
			
			pre { margin-top: 0px; margin-bottom: 0px; }
			.heat1 { background-color: #fff080; }
			.heat2 { background-color: #ffe040; }
			.heat3 { background-color: #ffb000; }
			.heat4 { background-color: #ff8000; }
			.heat5 { background-color: #ff4000; }
			.heat6 { background-color: #ff0000; }
		'''
		return re.sub('\s', '', css)

	def add_title(self, title):
		self.document.find('body').append(Xml('h1', text=title))
		
	def add_subtitle(self, subtitle):
		self.document.find('body').append(Xml('h2', text=subtitle))
	
	def add_table(self, columns):
		self.document.find('body').append(
			Xml('table').append(
				Xml('tr').extend([
					Xml('td').extend(c) for c in columns
				])
			)
		)
	
	def add_profile_table(self, lines, max_percent,
							lines_max_percent=None, heat=True):
		stat_column, code_column = [], []
		
		def heat_block(heat, text):
			if heat == 0:
				return Xml('pre', {}, text)
			else:
				return Xml('pre', {'class': 'heat%s' % heat}, text)
		
		def bar_block(current, outer):
			bar_part = lambda cls, percent: Xml('span', {
				'class': cls,
				'style': 'width: %spx' % int(percent * 200)
			}).append(Xml(None))
			return Xml('span').extend(
				[bar_part('c', current)] if current > 0 else [],
				[bar_part('o', outer)] if outer > 0 else []
			).append(Xml(None))
		
		if heat:
			heat_value = lambda x: int(x * (7 - 0.001))
			func = lambda x: heat_value((x[0] + x[1]) / lines_max_percent)
			grouped_lines = itertools.groupby(lines, func)
		else:
			grouped_lines = [(0, lines)]
			
		for heat, lines in grouped_lines:
			lines = list(lines)
			
			for c, o, t in lines:
				if t is None:
					stat_column.append('\n\n\n')
				else:
					stat_column.append('%.2f\t%.2f\t' % (c, c + o))
					stat_column.append(bar_block(c / max_percent, o / max_percent))
					stat_column.append('\n')
			
			texts = map(
				lambda text: '\n\t(...)\n' if text is None else text,
				[text for _, _, text in lines]
			)
			code_column.append(heat_block(heat, '\n'.join(texts) + '\n'))
				
		self.add_table([
			[Xml('pre').extend(stat_column)],
			code_column,
		])
		
	def add_canvas(self):
		self.document.find('body').append(
			Xml('canvas', {
				'id': 'timeline',
				'style': 'width: 100%; height: 100px; border: solid;'
						'border-width: 1px; border-color: #ddd;'
			}).append(Xml(None))
		)
		
	def add_script(self, attr={}, text=None):
		attr.setdefault('type', 'text/javascript')
		self.document.find('body').append(Xml('script', attr, text).append(Xml(None)))
		
	def write_to(self, file_name):
		self.document.tree().write(file_name, encoding='utf-8')
	
class Formatter:
	def __init__(self, accumulator, args):
		self.accumulator = accumulator
		self.args = args
		
	def register_exit(self):
		atexit.register(self.make_report)
		
	def set_start_time(self):
		self.start_time = time.time()
	
	def _structure(self, samples):
		if not samples:
			return [], []
			
		modules, functions = {}, {}
		weight = 100.0 / len(samples)
		
		def get_module(frame):
			try:
				return modules[frame.name]
			except KeyError:
				with open(frame.path, 'r') as f_in:
					code = f_in.read().decode('utf-8').splitlines()
				module = {
					'current': 0,
					'outer': 0,
					'name': frame.name,
					'path': frame.path,
					'code': [{
						'current': 0,
						'outer': 0,
						'line': i + 1,
						'text': x
					} for i, x in enumerate(code)],
				}
				modules[frame.name] = module
				return module
			
		def get_function(frame):
			func_id = (frame.name, frame.func_name, frame.func_line)
			return functions.setdefault(func_id, {
				'current': 0,
				'outer': 0,
				'module': frame.name,
				'name': frame.func_name,
				'line': frame.func_line,
			})

		def get_line(frame):
			try:
				return modules[frame.name]['code'][frame.line - 1]
			except Exception as e:
				# DEBUG
				print frame.name, frame.path, len(modules[frame.name]['code']),
				print frame.line, frame.func_name, frame.func_line
				raise e

		for stacks in samples:
			for stack in stacks:
				curr_frame, outer_frames = stack[0], stack[1:]
				
				for scoped_get in [get_module, get_function, get_line]:
					# get scoped object
					scoped_curr = scoped_get(curr_frame)
					
					scoped_outers = {
						id(o): o
						for o in map(scoped_get, outer_frames)
						if id(o) != id(scoped_curr)
					}.values()
					
					# apply weight
					scoped_curr['current'] += weight
					for scoped_outer in scoped_outers:
						scoped_outer['outer'] += weight
			
		weight_func = lambda x: -(x['current'] + x['outer'])
		return (
			sorted(modules.values(), key=weight_func),
			sorted(functions.values(), key=weight_func)
		)
		
	def make_report(self):
		exec_time = time.time() - self.start_time
		print '[MCP] create report...'
		
		# get data
		samples = self.accumulator.samples()
		modules, functions = self._structure(samples.values())
		
		sample_count = len(samples)
		max_percent = max([100.0] + [x['current'] + x['outer']
									for x in modules + functions])
	
		lines_max_percent = max([x['current'] + x['outer']
			for m in modules for x in m['code']] + [0.001])
	
		# prune empty lines
		for module in modules:
			non_empty = [x['current'] + x['outer'] > 0 for x in module['code']]
			dilate = [any(non_empty[i-2:i+3]) for i, x in enumerate(non_empty)]
			module['code'] = [x for x, y in zip(module['code'], dilate) if y]
	
		# make report
		report = ReportStructure(
			title='%s profile report' % self.args.script,
			general=[
				'Command line:', ' '.join([self.args.script] + self.args.args),
				'Working directory:', os.getcwdu(),
				'Total sample count:', str(sample_count),
				'Execution time:', '%.2f' % exec_time + ' sec',
			]
		)
		
		data = (samples, modules, functions,
				max_percent, lines_max_percent)
				
		if self.args.plain:
			self._add_plain_profile(report, data)
		else:
			self._add_extended_profile(report, data)
		
		report.write_to(self.args.report_file)
	
	def _add_plain_profile(self, report, data):
		_, modules, functions, max_percent, lines_max_percent = data
		
		# summary
		report.add_title('Summary')
		
		report.add_subtitle('Modules')
		report.add_profile_table([
			(m['current'], m['outer'], m['name'])
			for m in modules
		], max_percent, heat=False)

		report.add_subtitle('Functions')
		report.add_profile_table([
			(f['current'], f['outer'], '%s: %s' % (f['module'], f['name']))
			for f in functions
		], max_percent, heat=False)
		
		# details
		report.add_title('Line-by-line profile')
		
		for module in modules:
			report.add_subtitle(module['name'])
			
			lines = [(c['current'], c['outer'],
				'%d\t%s' % (c['line'], c['text'])) for c in module['code']]
			
			separators = [i + 1 
				for i, (x, y) in enumerate(zip(module['code'][1:], module['code'][:-1]))
				if x['line'] - y['line'] != 1]
			for i in reversed(separators):
				lines.insert(i, (0, 0, None))
				
			report.add_profile_table(lines, max_percent, lines_max_percent)

	def _add_extended_profile(self, report, data):
		samples, modules, functions, _, _ = data
		
		def mod_index(frame):
			for i, module in enumerate(modules):
				if module['name'] == frame.name:
					return i
			raise Exception
		
		def func_index(frame):
			for i, func in enumerate(functions):
				if func['name'] == frame.func_name:
					return i
			raise Exception
		
		def line_index(frame):
			for module in modules:
				if module['name'] == frame.name:
					for i, line in enumerate(module['code']):
						if line['line'] == frame.line:
							return i
			raise Exception
			
		samples = {
			t: [
				[
					(mod_index(frame), func_index(frame), line_index(frame))
					for frame in stack
				]
				for stack in stacks
			]
			for t, stacks in samples.iteritems()
		}
		
		for module in modules:
			del module['current']
			del module['outer']
		
			for line in module['code']:
				del line['current']
				del line['outer']
		
		for function in functions:
			del function['current']
			del function['outer']
		
		sample_data = {
			'samples': samples,
			'modules': modules,
			'functions': functions
		}

		# timeline
		report.add_title('Timeline')
		report.add_canvas()
		
		# scripts
		report.add_script(
			attr={'type': 'application/json', 'id': 'data'},
			text=json.dumps(sample_data)
		)
		report.add_script(attr={'src': 'formatter.js'})

########################################################################
# Main program
########################################################################

def _parse_args():
	min_interval = 0.1
	default_output = 'report.html'

	parser = argparse.ArgumentParser(description=
		'MCP is a statistical profiler for python based on regular '
		'sampling, which report cpu usage line by line.'
	)
		
	parser.add_argument('-s', '--sample-rate', default=min_interval, type=float,
		help='Interval between two samples, in second (default: %(default)s)',
		dest='interval')
	parser.add_argument('-o', '--output', default=default_output,
		help='Output file of the profile report, in HTML (default: %(default)s)',
		dest='report_file')
	parser.add_argument('--plain', action='store_true',
		help='Report profile in plain HTML (no Javascript)',
		dest='plain')
	parser.add_argument('script', help='profiled script file')
	parser.add_argument('args', help='profiled script arguments', nargs='*')

	return parser.parse_args()

def _program_wrapper(accumulator, interval, script, args):
	# Fix sys variables
	import sys, os
	sys.argv = [script] + args
	sys.path.insert(0, os.path.abspath(os.path.dirname(script)))
	
	# Start sampler
	import mcp
	sampler = mcp.Sampler(accumulator, interval, origin=True)
	sampler.start()
	
	# Execute profiled code in clean environment
	env = {
		'__name__': '__main__',
		'__file__': script,
	}
	execfile(script, env)

def main():
	args = _parse_args()
	
	accumulator = Accumulator()
	formatter = Formatter(accumulator, args)
	formatter.register_exit()
	
	# Start profiled process
	profiled_proc = multiprocessing.Process(
		target=_program_wrapper,
		args=(accumulator, args.interval, args.script, args.args)
	)
	
	formatter.set_start_time()
	profiled_proc.start()

	# Wait for samples
	try:
		while profiled_proc.exitcode == None:
			accumulator.listen(args.interval)
	except KeyboardInterrupt:
		os.kill(proc.pid, signal.SIGINT)
	except SystemExit:
		os.kill(proc.pid, signal.SIGTERM)

	# Cleanup and make report
	profiled_proc.join()
	sys.exit()

if __name__ == '__main__':
	main()
	
