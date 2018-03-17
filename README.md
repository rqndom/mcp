# MCP

MCP is a statistical profiling module for Python.

The profiling of a running script is based on sampling the script state
at random time intervals (Monte Carlo style), whereas other profilers usually
use deterministic approach by tracing each function call.

Our method allows us to have a constant low overhead as well as
performance information up to the level of a single line.
Moreover this profiler can manage multithreaded applications (but it will
only know about python threads).

After execution, all profiling information is contained in a single
nice colorful HTML report, which can be manipulated by selecting parts
of the timeline.

## Build instructions

This module uses distutils for an easier deployment.
Simply run

    $ python setup.py build
    $ python setup.py install

to build and install it respectively.

## Usage

MCP operates on python scripts.
It is invoked with the following command line:

    $ python -m mcp <script.py> [[args] ...]
    
MCP will generate by default a file named report.html, containing all
the profiling information.

A more detailed help can be found with:

    $ python -m mcp --help

## Report structure

For each function (or module, or line) there are two main data:
* time actually spend in the function (in blue, or the first percentage column)
* total time spend in the function, with called sub functions (in blue
and cyan, or the second percentage column)

Number columns represent the percentage of samples located inside a
given function, module or line.
For a given function, 100 will means that all samples are located in it (in case of a single threaded application).
A value of 200 is possible if the function is executed on two threads (on two different cores).

Recursive functions are counted as one call per sample, which is the
expected behaviour.

## Examples

Profiling of [curve.py](http://github.com/rqndom/curve.py):
* [Plain report](http://rawgit.com/rqndom/mcp/master/examples/plain_report.html)
* [Extended report with timeline](http://rawgit.com/rqndom/mcp/master/examples/extended_report.html)

## TODO

* Moar tests
