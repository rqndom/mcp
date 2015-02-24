
import pytest

import _mcp

import threading
import time

############
# Module
############

def test_Module_get_current_tid_ok():
	tid, run = [None], [True]
	
	def light_func():
		tid[0] = _mcp.get_current_tid()
		while run[0]:
			time.sleep(0.5)
		
	thread = threading.Thread(target=light_func)
	thread.daemon = True
	
	sampler = _mcp.Sampler(0.1)
	sampler.start()
	
	samples_without = sampler.wait_samples()
	thread.start()
	samples_with = sampler.wait_samples() + sampler.wait_samples()
	run[0] = False
	
	assert tid[0] not in [thread_id for _, thread_id, _ in samples_without]
	assert tid[0] in [thread_id for _, thread_id, _ in samples_with]

#############		
# Sampler
#############

def test_Sampler_lifecycle_ok():
	sampler = _mcp.Sampler(0.1)
	del sampler
	
def test_Sampler_lifecycle_with_multiple_running_ok():
	sampler = _mcp.Sampler(0.1)
	
	sampler.start()
	sampler.stop()
	
	sampler.start()
	sampler.stop()
	
	del sampler
	
def test_Sampler_lifecycle_without_stop_ok():
	sampler = _mcp.Sampler(0.1)
	sampler.start()
	del sampler
	
	
def test_Sampler_creation_failure_zero_interval():
	with pytest.raises(ValueError):
		sampler = _mcp.Sampler(0)
		
def test_Sampler_creation_failure_negative_interval():
	with pytest.raises(ValueError):
		sampler = _mcp.Sampler(-1)
		
def test_Sampler_creation_failure_wrong_arguments():
	with pytest.raises(TypeError):
		sampler = _mcp.Sampler('random string')


def test_Sampler_multiple_start_failure():
	sampler = _mcp.Sampler(0.1)
	sampler.start()
	with pytest.raises(Exception):
		sampler.start()
	
def test_Sampler_multiple_stop_failure():
	sampler = _mcp.Sampler(0.1)
	with pytest.raises(Exception):
		sampler.stop()


#~def test_impl_Sampler_start_right_arguments():
	#~sampler = _mcp.Sampler(0.1)
	#~sampler.start([1, 2])
#~
#~def test_impl_Sampler_start_wrong_arguments_nothing():
	#~sampler = _mcp.Sampler(0.1)
	#~with pytest.raises(Exception):
		#~sampler.start()
#~
#~def test_impl_Sampler_start_wrong_arguments_not_list():
	#~sampler = _mcp.Sampler(0.1)
	#~with pytest.raises(Exception):
		#~sampler.start('random string')
		#~
#~def test_impl_Sampler_start_wrong_arguments_not_integer_list():
	#~sampler = _mcp.Sampler(0.1)
	#~with pytest.raises(Exception):
		#~sampler.start(['a', 'b'])


#~def test_impl_Sampler_wait_samples_wrong_arguments_nothing():
	#~threads = [x.ident for x in threading.enumerate()]
	#~
	#~sampler = _mcp.Sampler(0.1)
	#~sampler.start(threads)
	#~
	#~with pytest.raises(Exception):
		#~sampler.wait_samples()
#~
#~def test_impl_Sampler_wait_samples_wrong_arguments_not_list():
	#~threads = [x.ident for x in threading.enumerate()]
	#~
	#~sampler = _mcp.Sampler(0.1)
	#~sampler.start(threads)
	#~
	#~with pytest.raises(Exception):
		#~sampler.wait_samples('random string')
		#~
#~def test_impl_Sampler_wait_samples_wrong_arguments_not_integer_list():
	#~threads = [x.ident for x in threading.enumerate()]
	#~
	#~sampler = _mcp.Sampler(0.1)
	#~sampler.start(threads)
	#~
	#~with pytest.raises(Exception):
		#~sampler.wait_samples(['a', 'b'])


def test_Sampler_wait_samples_not_started_failure():
	sampler = _mcp.Sampler(0.1)
	with pytest.raises(Exception):
		sampler.wait_samples()


def test_Sampler_wait_samples_ok():
	sampler = _mcp.Sampler(0.1)
	sampler.start()
	samples = sampler.wait_samples()
	assert all([(x[2] in [0, 1]) for x in samples])


#~def test_impl_Sampler_wait_samples_wrong_threads():
	#~real_threads = [x.ident for x in threading.enumerate()]
	#~wrong_threads = [1, 2]
	#~
	#~while any([x in real_threads for x in wrong_threads]):
		#~wrong_threads = [x + 1 for x in wrong_threads]
	#~
	#~sampler = _mcp.Sampler(0.1)
	#~sampler.start(wrong_threads)
	#~
	#~with pytest.raises(Exception):
		#~sampler.wait_samples(wrong_threads)


@pytest.mark.statistical
@pytest.mark.slow
def test_Sampler_interval_ok():
	interval = 0.1
	sampler = _mcp.Sampler(interval)
	sampler.start()
	
	timestamps = set([])
	while len(timestamps) < 10:
		samples = sampler.wait_samples()
		timestamps.update([x[0] for x in samples])
	
	times = sorted(list(timestamps))
	intervals = [t1 - t0 for t0, t1 in zip(times[:-1], times[1:])]
	
	assert all([abs(x - interval) < 0.1 * interval for x in intervals])
	
@pytest.mark.statistical
@pytest.mark.slow
def test_Sampler_light_thread_ok():
	tid, run = [None], [True]
	
	def light_func():
		tid[0] = _mcp.get_current_tid()
		while run[0]:
			time.sleep(0.5)
		
	thread = threading.Thread(target=light_func)
	thread.daemon = True
	thread.start()
	
	sampler = _mcp.Sampler(0.1)
	sampler.start()
	
	tid_filter = lambda x: x[1] == tid[0]
	samples = []
	while len(samples) < 10:
		samples.extend(filter(tid_filter, sampler.wait_samples()))
	run[0] = False
	
	assert sum([running for _, _, running in samples]) <= 1
	
@pytest.mark.statistical
@pytest.mark.slow
def test_Sampler_heavy_thread_ok():
	tid, run = [None], [True]
	
	def heavy_func():
		tid[0] = _mcp.get_current_tid()
		while run[0]:
			pass
		
	thread = threading.Thread(target=heavy_func)
	thread.daemon = True
	thread.start()
	
	sampler = _mcp.Sampler(0.1)
	sampler.start()
	
	tid_filter = lambda x: x[1] == tid[0]
	samples = []
	while len(samples) < 10:
		samples.extend(filter(tid_filter, sampler.wait_samples()))
	run[0] = False
	
	assert sum([running for _, _, running in samples]) >= 9
	
