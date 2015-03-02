
#include <Python.h>

#include <thread>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <chrono>
#include <vector>
#include <string>
#include <iterator>
#include <fstream>
#include <sstream>
#include <random>

#ifdef MS_WINDOWS
#include <windows.h>
#else
#include <sys/types.h>
#include <sys/syscall.h>
#include <unistd.h>
#include <dirent.h>
#endif

#ifdef MS_WINDOWS
typedef NTSTATUS (WINAPI* NtQueryInfoType)(
	SYSTEM_INFORMATION_CLASS, PVOID, ULONG, PULONG);

// Based on documentation by Tomasz Nowak from:
// http://undocumented.ntinternals.net/

typedef struct {
    HANDLE ProcessId;
    HANDLE ThreadId;
} CLIENT_ID;

typedef struct {
	LARGE_INTEGER           KernelTime;
	LARGE_INTEGER           UserTime;
	LARGE_INTEGER           CreateTime;
	ULONG                   WaitTime;
	PVOID                   StartAddress;
	CLIENT_ID               ClientId;
	KPRIORITY               Priority;
	LONG                    BasePriority;
	ULONG                   ContextSwitchCount;
	ULONG                   State;
	KWAIT_REASON            WaitReason;
} SYSTEM_THREAD;

typedef struct {
	ULONG                   NextEntryOffset;
	ULONG                   NumberOfThreads;
	LARGE_INTEGER           Reserved[3];
	LARGE_INTEGER           CreateTime;
	LARGE_INTEGER           UserTime;
	LARGE_INTEGER           KernelTime;
	UNICODE_STRING          ImageName;
	KPRIORITY               BasePriority;
	HANDLE                  ProcessId;
	HANDLE                  InheritedFromProcessId;
	ULONG                   HandleCount;
	ULONG                   Reserved2[2];
	ULONG                   PrivatePageCount;
	VM_COUNTERS             VirtualMemoryCounters;
	IO_COUNTERS             IoCounters;
	SYSTEM_THREAD           Threads[0];
} SYS_PROC_INFO;
#endif

typedef std::chrono::system_clock Clock;

typedef struct {
	double timestamp;
	long tid;
	int running;
} Sample;

typedef struct {
	PyObject_HEAD
	double interval;
	std::thread* state_thread;
	std::queue<Sample*>* queue;
	std::mutex* mutex;
	std::condition_variable* not_empty_cond;
	std::condition_variable* running_cond;
	bool running;
} Sampler;

void queue_value(Sampler* sampler, Sample* sample)
{
	sampler->queue->push(sample);
	sampler->not_empty_cond->notify_one();
}

void queue_error(Sampler* sampler, int error=-1)
{
	queue_value(sampler, new Sample{0, 0, error});
}

void state_func(Sampler* sampler)
{
	// init
#ifdef MS_WINDOWS
	NtQueryInfoType NtQueryInfo = (NtQueryInfoType)GetProcAddress(
		GetModuleHandleA("ntdll.dll"), "NtQuerySystemInformation");
	if (NtQueryInfo == NULL) {
		std::unique_lock<std::mutex> lock(*sampler->mutex);
		queue_error(sampler);
		return;
	}
	
	PVOID system_info = new char[4096];
	if (system_info == NULL) {
		std::unique_lock<std::mutex> lock(*sampler->mutex);
		queue_error(sampler);
		return;
	}

	DWORD pid = GetCurrentProcessId();
#else
	std::string path = std::string("/proc/") + std::to_string(getpid()) + "/task";

	DIR* dir = opendir(path.c_str());
	if (dir == NULL) {
		std::unique_lock<std::mutex> lock(*sampler->mutex);
		queue_error(sampler);
		return;
	}
#endif

	double period = double(Clock::period::num) / Clock::period::den;
    std::mt19937 rnd_gen;
	std::uniform_real_distribution<> rnd;

	// sampling loop
	while (sampler->running) {
		// sleep during the current interval
		Clock::duration now = Clock::now().time_since_epoch();
		
		double dither = rnd(rnd_gen);
		double t_curr = now.count() * period;
		double t_next = (long(t_curr / sampler->interval) + 1
										+ dither) * sampler->interval;

		Clock::time_point tp = Clock::time_point(
			Clock::duration(Clock::rep(t_next / period)));
	
		std::unique_lock<std::mutex> lock(*sampler->mutex);
		if (sampler->running_cond->wait_until(lock, tp) == std::cv_status::no_timeout)
			break;
		
		// list running threads
#ifdef MS_WINDOWS
		ULONG needed;
		while (NtQueryInfo(SystemProcessInformation, system_info,
							sizeof(system_info), &needed) != 0) {
			delete system_info;
			system_info = new char[needed];
			if (system_info == NULL) {
				queue_error(sampler);
				return;
			}
		}
		
		SYS_PROC_INFO* proc_info = (SYS_PROC_INFO*)system_info;
        while (proc_info->ProcessId != pid)
        {
			if (proc_info->NextEntryOffset == 0) {
				queue_error(sampler);
				return;
			}
			
            proc_info = (SYS_PROC_INFO*)((char*)proc_info +
										proc_info->NextEntryOffset);
		}
		
        for (ULONG i = 0; i < proc_info->NumberOfThreads; ++i)
        {
			long tid = proc_info->Threads[i].ClientId.ThreadId;
			bool running = (proc_info->Threads[i].State == 2);
			queue_value(sampler, new Sample{t_next, tid, running ? 1 : 0});
        }
#else
		rewinddir(dir);
		struct dirent* entry;
		
		for (entry = readdir(dir); entry != NULL; entry = readdir(dir)) {
			// get tid
			int tid;
			std::stringstream ss;
			
			ss << entry->d_name;
			ss >> tid;
			
			if (ss.fail())
				continue;
			
			// get status
			std::string file_path = path + "/" + entry->d_name + "/stat";

			std::ifstream file_stream(file_path.c_str());

			if (file_stream.fail()) {
				queue_error(sampler);
				break;
			}
	
			std::istream_iterator<std::string> begin(file_stream), end;
			std::vector<std::string> tokens(begin, end);

			if (tokens.size() < 52) {
				queue_error(sampler);
				break;
			}

			// create sample
			bool running = (tokens[tokens.size() - 50] == "R");
			queue_value(sampler, new Sample{t_next, tid, running ? 1 : 0});
		}
#endif
	}
	
	// cleanup
#ifdef MS_WINDOWS
	delete system_info;
#else
	if (closedir(dir) < 0) {
		std::unique_lock<std::mutex> lock(*sampler->mutex);
		queue_error(sampler);
	}
#endif
}

extern "C" {
	static PyObject*
	get_current_tid(PyObject* self)
	{
#ifdef MS_WINDOWS
		return Py_BuildValue("l", (long int)GetCurrentThreadId());
#else
		return Py_BuildValue("l", (long int)syscall(SYS_gettid));
#endif
	}

	static PyObject*
	Sampler_new(PyTypeObject* type, PyObject* args, PyObject* kwds)
	{
		Sampler* self = (Sampler*)type->tp_alloc(type, 0);
		if (self == NULL)
			return NULL;
			
		if (!PyArg_ParseTuple(args, "d", &self->interval))
			goto fail;
		
		if (self->interval * Clock::period::den < Clock::period::num) {
			PyErr_Format(PyExc_ValueError,
				"interval too short (clock precision: %ld/%ld)",
				Clock::period::num, Clock::period::den);
			goto fail;
		}
		
		self->state_thread = NULL;
		self->running = false;
		
		self->queue = new std::queue<Sample*>();
		if (self->queue == NULL)
			goto memory_fail;

		self->mutex = new std::mutex();
		if (self->mutex == NULL)
			goto memory_fail;
		
		self->not_empty_cond = new std::condition_variable();
		if (self->not_empty_cond == NULL)
			goto memory_fail;
		
		self->running_cond = new std::condition_variable();
		if (self->running_cond == NULL)
			goto memory_fail;
		
		return (PyObject*)self;

	memory_fail:
		PyErr_NoMemory();
	fail:
		Py_DECREF(self);
		return NULL;
	}

	static PyObject*
	Sampler_start(Sampler* self)
	{
		if (self->running) {
			PyErr_SetString(PyExc_Exception, "already started");
			return NULL;
		}
		
		self->running = true;
		self->state_thread = new std::thread(state_func, self);
		if (self->state_thread == NULL)
			return PyErr_NoMemory();
		
		return Py_None;
	}
	
	static PyObject*
	Sampler_stop(Sampler* self)
	{
		if (!self->running) {
			PyErr_SetString(PyExc_Exception, "not started");
			return NULL;
		}
		
		self->running = false;
		self->running_cond->notify_one();
		self->state_thread->join();
		delete self->state_thread;
		self->state_thread = NULL;
		
		std::lock_guard<std::mutex> lock(*self->mutex);
		while (!self->queue->empty()) {
			delete self->queue->front();
			self->queue->pop();
		}
		
		return Py_None;
	}

	static PyObject*
	Sampler_wait_samples(Sampler* self)
	{
		if (!self->running) {
			PyErr_SetString(PyExc_Exception, "not started");
			return NULL;
		}
		
		// wait for new samples
		Py_BEGIN_ALLOW_THREADS
		
		std::unique_lock<std::mutex> lock(*self->mutex);
		while(self->queue->empty())
			self->not_empty_cond->wait(lock);
		
		Py_END_ALLOW_THREADS
		
		// collect samples
		unsigned queue_size = self->queue->size();

		PyObject* samples = PyList_New(queue_size);
		if (samples == NULL)
			return NULL;
			
		for (unsigned i = 0; i < queue_size; ++i) {
			Sample* sample = self->queue->front();
			self->queue->pop();
			
			if (sample == NULL) {
				PyErr_NoMemory();
				goto fail;
			}
			
			if (sample->running < 0) {
				PyErr_Format(PyExc_Exception, "sample error");
				goto fail;
			}
			
			PyObject* tuple = Py_BuildValue("(dli)", sample->timestamp,
											sample->tid, sample->running);
			delete sample;
			
			if (tuple == NULL)
				goto fail;
			
			if (PyList_SetItem(samples, i, tuple) < 0)
				goto fail;
		}

		return samples;

	fail:
		Py_DECREF(samples);
		return NULL;
	}

	static void
	Sampler_dealloc(Sampler* self)
	{
		if (self->running)
			(void) Sampler_stop(self);

		delete self->queue;
		delete self->mutex;
		delete self->not_empty_cond;
		delete self->running_cond;
		
		self->ob_type->tp_free((PyObject*)self);
	}

	static PyMethodDef Sampler_methods[] = {
		{"start", (PyCFunction)Sampler_start, METH_NOARGS, ""},
		{"stop", (PyCFunction)Sampler_stop, METH_NOARGS, ""},
		{"wait_samples", (PyCFunction)Sampler_wait_samples, METH_NOARGS, ""},
		{NULL}  /* Sentinel */
	};

	static PyTypeObject SamplerType = {
		PyObject_HEAD_INIT(NULL)
		0,                         /*ob_size*/
		"_mcp.Sampler",            /*tp_name*/
		sizeof(Sampler),             /*tp_basicsize*/
		0,                         /*tp_itemsize*/
		(destructor)Sampler_dealloc, /*tp_dealloc*/
		0,                         /*tp_print*/
		0,                         /*tp_getattr*/
		0,                         /*tp_setattr*/
		0,                         /*tp_compare*/
		0,                         /*tp_repr*/
		0,                         /*tp_as_number*/
		0,                         /*tp_as_sequence*/
		0,                         /*tp_as_mapping*/
		0,                         /*tp_hash */
		0,                         /*tp_call*/
		0,                         /*tp_str*/
		0,                         /*tp_getattro*/
		0,                         /*tp_setattro*/
		0,                         /*tp_as_buffer*/
		Py_TPFLAGS_DEFAULT, /*tp_flags*/
		"",           /* tp_doc */
		0,		               /* tp_traverse */
		0,		               /* tp_clear */
		0,		               /* tp_richcompare */
		0,		               /* tp_weaklistoffset */
		0,		               /* tp_iter */
		0,		               /* tp_iternext */
		Sampler_methods,             /* tp_methods */
		0,             /* tp_members */
		0,                         /* tp_getset */
		0,                         /* tp_base */
		0,                         /* tp_dict */
		0,                         /* tp_descr_get */
		0,                         /* tp_descr_set */
		0,                         /* tp_dictoffset */
		0,      /* tp_init */
		0,                         /* tp_alloc */
		Sampler_new,                 /* tp_new */
	};

	static PyMethodDef _mcp_methods[] = {
		{"get_current_tid", (PyCFunction)get_current_tid, METH_NOARGS, ""},
		{NULL}  /* Sentinel */
	};

	PyMODINIT_FUNC
	init_mcp(void) 
	{
		if (PyType_Ready(&SamplerType) < 0)
			return;

		PyObject* m = Py_InitModule("_mcp", _mcp_methods);

		Py_INCREF(&SamplerType);
		PyModule_AddObject(m, "Sampler", (PyObject*)&SamplerType);
	}
}
