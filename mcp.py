#!/usr/bin/env python
# coding: utf-8

# Version: 2015-02-19

# TODO: que faire pour un profil fonction du temps (cf. profileur js)
# TODO: memory profiler statistique aussi ?
# TODO: faire en sorte de pouvoir se profiler soi meme: enorme
# TODO: deregistrer les threads spawnés par multiprocessing (genre les Queues)
# TODO: a chaque spawn de process, le sampler reinstalle les patchs par dessus
# TODO: donner un moyen (genre decorator) de patcher manuellement /
#		unifier le patchage de lib / monitoring de thread spawn
#		(plutot un couple spawn_process / spawn_thread)
# TODO: encore des conflits de noms / '__main__' quand l'interval est très court
# TODO: rajouter dans la doc que les thread spawnés par du C, etc.
#		(ie. pas par threading, thread ou multiprocessing), ne sont pas trackés
#		automatiquement. Il faut les passer dans @sampler.watch_thread & co. /
#		ou ajouter un mecanisme si non existant

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
# Embeded data
########################################################################

def _formatter_min_js():
	js = r'''
		eval(function(p,a,c,k,e,r){e=function(c){return(c<a?'':e(parseIn
		t(c/a)))+((c=c%a)>35?String.fromCharCode(c+29):c.toString(36))};
		if(!''.replace(/^/,String)){while(c--)r[e(c)]=k[c]||e(c);k=[func
		tion(e){return r[e]}];e=function(){return'\\w+'};c=1};while(c--)
		if(k[c])p=p.replace(new RegExp('\\b'+e(c)+'\\b','g'),k[c]);retur
		n p}('3 22=u;3 23=5;3 N=2J.2K(a.24(\'N\').O);3 P=N.P;3 z=N.z;3 L
		=N.L;3 l=2L 2M();9(3 t 2N N.P){l.G(t)}l.2O();f(l.m>0){3 Q=12(l[0
		]);3 1b=12(l[l.m-1]);3 1c=Q;3 1d=1b}4 25(R,D){f(l.m==0)6[A,A];6[
		1z(S.2P(R,D)),1z(S.1A(R,D))]}4 13(t){6(t-Q)/(1b-Q)*(p.E+1)-1}4 1
		z(1e){6 Q+(1e+1)*(1b-Q)/(p.E+1)}3 B,14;4 26(){B=27;14=0.28;9(3 g
		 b z){3 x=g.d+g.k;f(x>B)B=x;9(3 C b g.H){3 y=C.d+C.k;f(y>14)14=y
		}}9(3 T b L){3 x=T.d+T.k;f(x>B)B=x}}3 U=[];4 29(){f(D===A)6 l.r(
		x=>P[x]);6 l.2Q(x=>(1c<=12(x)&&12(x)<=1d)).r(x=>P[x])}4 1B(){3 1
		f=29();f(U.m==1f.m)f(U.2R((x,i,2S)=>(x===1f[i])))6 u;U=1f;3 1C=2
		7.0/U.m;9(3 g b z){g.d=0;g.k=0;9(3 C b g.H){C.d=0;C.k=0}}9(3 T b
		 L){T.d=0;T.k=0}4 2a(M){6 z[M[0]]}4 2b(M){6 L[M[1]]}4 2c(M){6 z[
		M[0]].H[M[2]]}9(3 2e b U){9(3 1D b 2e){3 2f=1D[0];3 2g=1D.2h(1);
		9(3 1E b[2a,2b,2c]){3 1F=1E(2f);3 1G=2T(2g.r(1E));1G.2U(1F);1F.d
		+=1C;9(3 2i b 1G)2i.k+=1C}}}26();6 15}3 p=a.24(\'V\');3 8=p.2V(\
		'2d\');3 V=A;4 1H(){3 w=p.E;3 h=p.2W;8.2j="#2X";8.2k(0,0,w,h);f(
		l.m<=1||w==0)6;f(V===A||V.E!=w){3 t=l.r(12);3 s=l.r(x=>P[x].m);3
		 2l=S.1A(...s);8.1I();9(3 i=0;i<t.m;++i){3 x=13(t[i])+0.5;3 y=s[
		i]/2l;8.1g(x,h);8.1h(x,h*(1-y))}8.1J="#2Y";8.1K();3 1i=S.2Z(l.m/
		23);3 W=[];W[0]=0;3 j=1;9(3 i=1;i<1i;++i){3 16=(t[t.m-1]-t[0])*i
		/1i+t[0];30(t[j]<16)++j;t.1L(j,0,16);s.1L(j,0,(s[j-1]*(t[j]-16)+
		s[j]*(16-t[j-1]))/(t[j]-t[j-1]));W[i]=j}W[1i]=t.m-1;3 1M=W.2h(0,
		-1).r((x,i)=>[x,W[i+1]]);3 2m=1M.r(x=>(t[x[1]]+t[x[0]])/2);3 2n=
		4(x){3 1N=0;9(3 i=x[0];i<x[1];++i)1N+=0.5*(s[i+1]+s[i])*(t[i+1]-
		t[i]);6 1N/(t[x[1]]-t[x[0]])};3 1O=1M.r(2n);3 2o=S.1A(...1O);3 x
		=2m.r(t=>(13(t)+0.5));3 y=1O.r(s=>h*(1-s/2o));8.1I();8.1g(x[0],y
		[0]);9(3 i=1;i<x.m;++i)8.1h(x[i],y[i]);8.1J="#31";8.1K();V=8.32(
		0,0,w,h)}8.33(V,0,0);f(D!==A){3 17=13(1c)+0.5;3 1j=13(1d)+0.5;8.
		2p=0.5;8.2j="#2q";8.2k(17,0,1j-17,h);8.2p=1;8.1J="#2q";8.1I();8.
		1g(17,0);8.1h(17,h);8.1g(1j,0);8.1h(1j,h);8.1K()}}4 18(d,k){6 S.
		34((d+k)/14*(7-0.28))}4 1P(F){6 a.35(F)}4 1Q(F){3 X=a.v(\'36\');
		X.O=F;6 X}4 1k(F){3 X=a.v(\'37\');X.O=F;6 X}4 Y(2r){3 Y=a.v(\'Y\
		');3 1l=a.v(\'1l\');Y.q(1l);9(3 2s b 2r){3 1m=a.v(\'1m\');1l.q(1
		m);9(3 2t b 2s)1m.q(2t)}6 Y}4 1n(19,Z=15){3 10=[];3 1o=[];4 1R(1
		8,F){3 I=a.v(\'2u\');I.1p=\'Z\'+18;I.O=F;6 I}4 2v(d,k){3 1q=a.v(
		\'1S\');3 1r=a.v(\'1S\');3 1s=a.v(\'1S\');1r.1p=\'c\';1s.1p=\'o\
		';1r.J.E=d/B*1t+\'1e\';1s.J.E=k/B*1t+\'1e\';1q.q(1r);1q.q(1s);6 
		1q}4 2w(d,k){3 I=a.v(\'38\');I.O=d.1u(2)+\'\\t\'+(d+k).1u(2)+\'\
		\t\';I.J.39=\'3a\';6 I}9(3[x,c,o,t]b 19){f(t===A){10.G(1P(\'\\n\
		\n\\n\'));1o.G(1R(0,\'\\n\\t(...)\\n\'+\'\\n\'))}3b{x.1T=2w(c,o)
		;x.1v=2v(c,o);x.1U=1R(Z?18(c,o):0,t+\'\\n\');10.G(x.1T);10.G(x.1
		v);10.G(1P(\'\\n\'));1o.G(x.1U)}}3 1V=a.v(\'2u\');9(3 x b 10)1V.
		q(x);6 Y([[1V],1o])}4 2x(){1B();3 2y=1n(z.r(4(x){6[x,x.d,x.k,x.1
		W]}),u);3 2z=1n(L.r(4(x){6[x,x.d,x.k,x.g+\': \'+x.1W]}),u);a.K.q
		(1Q(\'3c\'));a.K.q(1k(\'3d\'));a.K.q(2y);a.K.q(1k(\'3e\'));a.K.q
		(2z);a.K.q(1Q(\'3f-3g-C 3h\'));9(3 g b z){3 19=g.H.r(4(x){6[x,x.
		d,x.k,x.C+\'\\t\'+x.F]});3 1w=[];9(3 i=1;i<g.H.m;++i)f(g.H[i].C-
		1!=g.H[i-1].C)1w.G(i);1w.3i();9(3 s b 1w)19.1L(s,0,[{},0,0,A]);a
		.K.q(1k(g.1W));a.K.q(1n(19))}}4 2A(){f(!1B())6;4 1x(2B,Z=15){9(3
		 x b 2B){3 c=x.d;3 o=x.k;x.1T.O=c.1u(2)+\'\\t\'+(c+o).1u(2)+\'\\
		t\';x.1v.2C[0].J.E=c*1t/B;x.1v.2C[1].J.E=o*1t/B;x.1U.1p=\'Z\'+(Z
		?18(c,o):0)}}1x(z,u);1x(L,u);9(3 g b z)1x(g.H)}4 1X(){3 11=1Y(p.
		J.1Z);p.E=p.3j-2*11;1H()}20.1y(\'3k\',1X,u);3 1a=u;3 R=0,D=A;4 2
		1(2D){[1c,1d]=25(R,D);1H();f(2D)2A()}4 2E(e){1a=15;3 11=1Y(p.J.1
		Z);R=e.2F-p.2G-11;D=A}4 2H(e){f(!1a)6;3 11=1Y(p.J.1Z);D=e.2F-p.2
		G-11;21(22)}4 2I(e){f(!1a)6;1a=u;21(15)}p.1y(\'3l\',2E,u);20.1y(
		\'3m\',2H,u);20.1y(\'3n\',2I,u);2x();1X();',62,210,'|||var|funct
		ion||return||ctx|for|document|of||current||if|module||||outer|ts
		|length|||canvas|appendChild|map|||false|createElement||||module
		s|null|max_percent|line|x_end|width|text|push|code|block|style|b
		ody|functions|frame|data|innerHTML|samples|t0|x_start|Math|func|
		partial_samples|timeline|bin_i|element|table|heat|stat_column|bo
		rder|parseFloat|t_to_px|lines_max_percent|true|t_curr|x0|heat_va
		lue|lines|track_mouse|t1|t_start|t_end|px|new_samples|moveTo|lin
		eTo|bin_count|x1|sub_title|tr|td|profile_table|code_column|class
		Name|back|curr|out|200|toFixed|html_bar|separators|scoped_update
		|addEventListener|px_to_t|max|compute_usage|weight|stack|scoped_
		get|scoped_curr|scoped_outers|draw_timeline|beginPath|strokeStyl
		e|stroke|splice|bin_i2|int_s|bin_s|text_node|title|heat_block|sp
		an|html_num|html_heat|stat_pre|name|on_resize|parseInt|borderWid
		th|window|update_data|dynamic_update|bin_size|getElementById|t_w
		indow|compute_max|100|001|get_samples|get_module|get_function|ge
		t_line||stacks|curr_frame|outer_frames|slice|scoped_outer|fillSt
		yle|fillRect|s_max|bin_t|integral_s|bin_s_max|globalAlpha|ff0000
		|columns|column|row|pre|bar_block|num_block|insert_report|module
		_table|function_table|update_usage|scoped_table|children|update_
		all|on_mouse_down|clientX|offsetLeft|on_mouse_move|on_mouse_up|J
		SON|parse|new|Array|in|sort|min|filter|every|_|Set|delete|getCon
		text|height|ffffff|eeeeee|ceil|while|0000ff|getImageData|putImag
		eData|floor|createTextNode|h1|h2|div|display|inline|else|Summary
		|Modules|Functions|Line|by|profile|reverse|offsetWidth|resize|mo
		usedown|mousemove|mouseup'.split('|'),0,{}))
	'''
	return re.sub('\t|\n', '', js)

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
		self.document.tree().write(file_name, encoding='utf-8', method='html')
	
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
		report.add_script(
			attr={'type': 'text/javascript'},
			text=_formatter_min_js()
		)
		#~report.add_script(attr={'src': 'formatter.js'})

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
		os.kill(profiled_proc.pid, signal.SIGINT)
	except SystemExit:
		os.kill(profiled_proc.pid, signal.SIGTERM)

	# Cleanup and make report
	profiled_proc.join()
	sys.exit()

if __name__ == '__main__':
	main()
	
