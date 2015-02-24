#!/usr/bin/env python
# coding: utf-8

# Version: 2015-02-19

# TODO: que faire pour un profil fonction du temps (cf. profileur js)



import _mcp

import threading

class Sampler(threading.Thread):
	def __init__(self, interval):
		threading.Thread.__init__(self)
		self.daemon = True
		
		self.sampler = _mcp.Sampler(interval)
		self.start()
	
	def thread_ids(self):
		return [x.ident for x in threading.enumerate()]
	
	def stop(self):
		if self.running:
			self.running = False
			self.sampler.stop()
	
	def run(self):
		self.running = True
		self.sampler.start(self.thread_ids())
		
		while self.running:
			samples = self.sampler.wait_samples(self.thread_ids())
			print samples

