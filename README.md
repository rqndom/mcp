# MCP

MCP is a statistical profiler for Python.
It is based on random sampling of a running script (Monte Carlo)

line based unlike standard python profilers
cool output
dynamic time based

## Build instructions

This module uses distutils for an easier deployment.
Simply run `python setup.py build` and `python setup.py install` to build and install it respectively.

## Usage

MCP operates on python scripts.
You can invoke it with the command line `python -m mcp <script.py> [[args] ...]`.
MCP will generate by default a file named report.html, containing all the profiling information.
A more detailed help can be found in `python -m mcp --help`

## Report structure

## Examples

* [Plain HTML report](examples/plain_report.html)
* [Extended report with dynamic timeline](examples/extended_report.html)

## TODO

* Moar tests
