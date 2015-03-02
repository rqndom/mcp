from distutils.core import setup, Extension

_mcp_module = Extension(
	'_mcp',
	sources = ['_mcp.cpp'],
	extra_compile_args = ['-std=c++11']
)

setup(
	name = 'mcp',
	version = '0.1',
	description = 'Probabilistic profiler',
	author='Romain Vavassori',
	author_email='romain.vavassori@hotmail.com',
	url='http://github.com/rqndom/mcp',
	py_modules = ['mcp'],
	ext_modules = [_mcp_module]
)
