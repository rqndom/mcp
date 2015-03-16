# MCP

MCP is a statistical profiler for Python.

The profiling of a running script is based on sampling the script state
at random time intervals (Monte Carlo), whereas other profilers usually
use deterministic approach by tracing each function call.

Our method allows us to have a constant low overhead as well as
performance information up to the level of a single line.

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

The basic information provided by each report is the percentage of time passed in each object (module, function, line, ...).



## Examples

* [Plain HTML report](http://rawgit.com/rqndom/mcp/master/examples/plain_report.html)
* [Extended report with dynamic timeline](http://rawgit.com/rqndom/mcp/master/examples/extended_report.html)

## TODO

* Moar tests
