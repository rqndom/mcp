from distutils.core import setup, Extension

_mcp_module = Extension(
	'_mcp',
	sources = ['_mcp.cpp'],
	extra_compile_args = ['-std=c++11']
)

setup(
	name = 'mcp',
	version = '1.0',
	description = 'Probabilistic profiler',
	ext_modules = [_mcp_module]
)
