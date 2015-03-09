
////////////////////////////////////////////////////////////////////////
// global parameters
////////////////////////////////////////////////////////////////////////

var dynamic_update = false;
var bin_size = 5;

////////////////////////////////////////////////////////////////////////
// data
////////////////////////////////////////////////////////////////////////

var data = JSON.parse(document.getElementById('data').innerHTML);

var samples = data.samples;
var modules = data.modules;
var functions = data.functions;

// get timestamps
var ts = new Array();
for (var t in data.samples) {
	ts.push(t);
}
ts.sort();

if (ts.length > 0) {
	var t0 = parseFloat(ts[0]);
	var t1 = parseFloat(ts[ts.length - 1]);
	
	var t_start = t0;
	var t_end = t1;
}

function t_window(x_start, x_end) {
	if (ts.length == 0) return [null, null];
	return [
		px_to_t(Math.min(x_start, x_end)),
		px_to_t(Math.max(x_start, x_end))
	];
}

function t_to_px(t) { return (t - t0) / (t1 - t0) * (canvas.width + 1) - 1; }
function px_to_t(px) { return t0 + (px + 1) * (t1 - t0) / (canvas.width + 1); }

// max usage
var max_percent, lines_max_percent;

function compute_max() {
	max_percent = 100;
	lines_max_percent = 0.001;
	
	for (var module of modules) {
		var x = module.current + module.outer;
		if (x > max_percent)
			max_percent = x;
		
		for (var line of module.code) {
			var y = line.current + line.outer;
			if (y > lines_max_percent)
				lines_max_percent = y;
		}
	}
	
	for (var func of functions) {
		var x = func.current + func.outer;
		if (x > max_percent)
			max_percent = x;
	}
}

// compute partial usage given a subset of samples
var partial_samples = [];

function get_samples() {
	if (x_end === null)
		return ts.map(x => samples[x]);
	return ts
		.filter(x => (t_start <= parseFloat(x) && parseFloat(x) <= t_end))
		.map(x => samples[x]);
}

function compute_usage() {
	var new_samples = get_samples();
	
	if (partial_samples.length == new_samples.length)
		if (partial_samples.every((x, i, _) => (x === new_samples[i])))
			return false;
			
	partial_samples = new_samples;
	
	var weight = 100.0 / partial_samples.length;

	for (var module of modules) {
		module.current = 0;
		module.outer = 0;
		
		for (var line of module.code) {
			line.current = 0;
			line.outer = 0;
		}
	}
	
	for (var func of functions) {
		func.current = 0;
		func.outer = 0;
	}
	
	function get_module(frame) { return modules[frame[0]]; }
	function get_function(frame) { return functions[frame[1]]; }
	function get_line(frame) { return modules[frame[0]].code[frame[2]]; }
	
	for (var stacks of partial_samples) {
		for (var stack of stacks) {
			var curr_frame = stack[0];
			var outer_frames = stack.slice(1);
			
			for (var scoped_get of [get_module, get_function, get_line]) {
				var scoped_curr = scoped_get(curr_frame);
				var scoped_outers = Set(outer_frames.map(scoped_get));
				scoped_outers.delete(scoped_curr);
								
				scoped_curr.current += weight;
				for (var scoped_outer of scoped_outers)
					scoped_outer.outer += weight;
			}
		}
	}
	
	compute_max();
	
	return true;
}

////////////////////////////////////////////////////////////////////////
// draw timeline
////////////////////////////////////////////////////////////////////////

var canvas = document.getElementById('timeline');
var ctx = canvas.getContext('2d');

var timeline = null;

function draw_timeline() {
	var w = canvas.width;
	var h = canvas.height;
		
	ctx.fillStyle = "#ffffff";
	ctx.fillRect(0, 0, w, h);
	
	if (ts.length <= 1 || w == 0)
		return;
	
	// recompute timeline
	if (timeline === null || timeline.width != w) {
		var t = ts.map(parseFloat);
		var s = ts.map(x => samples[x].length);
		
		// draw samples
		var s_max = Math.max(...s);
		ctx.beginPath();
			
		for (var i = 0; i < t.length; ++i) {
			var x = t_to_px(t[i]) + 0.5;
			var y = s[i] / s_max;
			
			ctx.moveTo(x, h);
			ctx.lineTo(x, h * (1 - y));
		}
		
		ctx.strokeStyle = "#eeeeee";
		ctx.stroke();
		
		// compute bins
		var bin_count = Math.ceil(ts.length / bin_size);
		var bin_i = [];
		bin_i[0] = 0;
		
		var j = 1;
		for (var i = 1; i < bin_count; ++i) {
			var t_curr = (t[t.length - 1] - t[0]) * i / bin_count + t[0];
			while (t[j] < t_curr) ++j;
			
			t.splice(j, 0, t_curr);
			s.splice(j, 0, (s[j-1] * (t[j] - t_curr) +
				s[j] * (t_curr - t[j-1])) / (t[j] - t[j-1]));
			
			bin_i[i] = j;
		}
		
		bin_i[bin_count] = t.length - 1;

		var bin_i2 = bin_i.slice(0, -1).map((x, i) => [x, bin_i[i+1]]);
		var bin_t = bin_i2.map(x => (t[x[1]] + t[x[0]]) / 2);
		
		var integral_s = function(x) {
			var int_s = 0;
			for (var i = x[0]; i < x[1]; ++i)
				int_s += 0.5 * (s[i+1] + s[i]) * (t[i+1] - t[i]);
			return int_s / (t[x[1]] - t[x[0]]);
		};
		var bin_s = bin_i2.map(integral_s);

		var bin_s_max = Math.max(...bin_s);

		var x = bin_t.map(t => (t_to_px(t) + 0.5));
		var y = bin_s.map(s => h * (1 - s / bin_s_max));
		
		// draw bins
		ctx.beginPath();
		ctx.moveTo(x[0], y[0]);
			
		for (var i = 1; i < x.length; ++i)
			ctx.lineTo(x[i], y[i]);
		
		ctx.strokeStyle = "#0000ff";
		ctx.stroke();
			
		timeline = ctx.getImageData(0, 0, w, h);
	}
	
	// draw timeline
	ctx.putImageData(timeline, 0, 0);
	
	// draw selection
	if (x_end !== null) {
		var x0 = t_to_px(t_start) + 0.5;
		var x1 = t_to_px(t_end) + 0.5;
		
		ctx.globalAlpha = 0.5;
		ctx.fillStyle = "#ff0000";
		
		ctx.fillRect(x0, 0, x1 - x0, h);
		
		ctx.globalAlpha = 1;
		ctx.strokeStyle = "#ff0000";
		
		ctx.beginPath();
		ctx.moveTo(x0, 0);
		ctx.lineTo(x0, h);
		ctx.moveTo(x1, 0);
		ctx.lineTo(x1, h);
		ctx.stroke();

	}

}

////////////////////////////////////////////////////////////////////////
// html elements manipulation
////////////////////////////////////////////////////////////////////////

function heat_value(current, outer) {
	return Math.floor((current + outer) / lines_max_percent * (7 - 0.001));
}

function text_node(text) {
	return document.createTextNode(text); 
}

function title(text) {
	var element = document.createElement('h1');
	element.innerHTML = text;
	return element;
}

function sub_title(text) {
	var element = document.createElement('h2');
	element.innerHTML = text;
	return element;
}

function table(columns) {
	var table = document.createElement('table');
	var tr = document.createElement('tr');
	table.appendChild(tr);
	
	for (var column of columns) {
		var td = document.createElement('td');
		tr.appendChild(td);
		for (var row of column) td.appendChild(row);
	}
	
	return table;
}

function profile_table(lines, heat=true) {
	var stat_column = [];
	var code_column = [];
	
	function heat_block(heat_value, text) {
		var block = document.createElement('pre');
		block.className = 'heat' + heat_value;
		block.innerHTML = text;
		return block;
	}
	
	function bar_block(current, outer) {
		var back = document.createElement('span');
		var curr = document.createElement('span');
		var out = document.createElement('span');

		curr.className = 'c';
		out.className = 'o';

		curr.style.width = current / max_percent * 200 + 'px';
		out.style.width = outer / max_percent * 200 + 'px';

		back.appendChild(curr);
		back.appendChild(out);

		return back;
	}
	
	function num_block(current, outer) {
		var block = document.createElement('div');
		block.innerHTML = current.toFixed(2) + '\t' +
							(current + outer).toFixed(2) + '\t';
		block.style.display = 'inline';
		return block;
	}
	
	for (var [x, c, o, t] of lines) {
		if (t === null) {
			stat_column.push(text_node('\n\n\n'));
			code_column.push(heat_block(0, '\n\t(...)\n' + '\n'));
		} else {
			x.html_num = num_block(c, o);
			x.html_bar = bar_block(c, o);
			x.html_heat = heat_block(heat ? heat_value(c, o) : 0, t + '\n');
			
			stat_column.push(x.html_num);
			stat_column.push(x.html_bar);
			stat_column.push(text_node('\n'));
			
			code_column.push(x.html_heat);
		}
	}
	
	var stat_pre = document.createElement('pre');
	for (var x of stat_column) stat_pre.appendChild(x);
	
	return table([[stat_pre], code_column]);
}

function insert_report() {
	compute_usage();
	
	var module_table = profile_table(modules.map(
		function(x) { return [x, x.current, x.outer, x.name]; }
	), false);
	
	var function_table = profile_table(functions.map(
		function(x) { return [x, x.current, x.outer, x.module + ': ' + x.name]; }
	), false);
	
	document.body.appendChild(title('Summary'));
	document.body.appendChild(sub_title('Modules'));
	document.body.appendChild(module_table);
	document.body.appendChild(sub_title('Functions'));
	document.body.appendChild(function_table);
	
	document.body.appendChild(title('Line-by-line profile'));
	for (var module of modules) {
		var lines = module.code.map(
			function(x) { return [x, x.current, x.outer, x.line + '\t' + x.text]; }
		);
		
		var separators = [];
		for (var i = 1; i < module.code.length; ++i)
			if (module.code[i].line - 1 != module.code[i - 1].line)
				separators.push(i);
		separators.reverse();
		for (var s of separators) lines.splice(s, 0, [{}, 0, 0, null]);
		
		document.body.appendChild(sub_title(module.name));
		document.body.appendChild(profile_table(lines));
	}
}

function update_usage() {
	if (!compute_usage())
		return;
		
	function scoped_update(scoped_table, heat=true) {
		for (var x of scoped_table) {
			var c = x.current;
			var o = x.outer;
			
			x.html_num.innerHTML = c.toFixed(2) + '\t' + (c + o).toFixed(2) + '\t';
			
			x.html_bar.children[0].style.width = c * 200 / max_percent;
			x.html_bar.children[1].style.width = o * 200 / max_percent;
			
			x.html_heat.className = 'heat' + (heat ? heat_value(c, o) : 0);
		}
	}
	
	scoped_update(modules, false);
	scoped_update(functions, false);
	
	for (var module of modules)
		scoped_update(module.code);
}

////////////////////////////////////////////////////////////////////////
// events
////////////////////////////////////////////////////////////////////////

function on_resize() {
	var border = parseInt(canvas.style.borderWidth);
	canvas.width = canvas.offsetWidth - 2 * border;
	
	draw_timeline();
}
window.addEventListener('resize', on_resize, false);

var track_mouse = false;
var x_start = 0, x_end = null;

function update_data(update_all) {
	[t_start, t_end] = t_window(x_start, x_end);
	draw_timeline();
	if (update_all) update_usage();
}

function on_mouse_down(e) {
	track_mouse = true;
	
	var border = parseInt(canvas.style.borderWidth);
	x_start = e.clientX - canvas.offsetLeft - border;
	x_end = null;
}

function on_mouse_move(e) {
	if (!track_mouse) return;
	
	var border = parseInt(canvas.style.borderWidth);
	x_end = e.clientX - canvas.offsetLeft - border;
	
	update_data(dynamic_update);
}

function on_mouse_up(e) {
	if (!track_mouse) return;
	track_mouse = false;
	
	update_data(true);
}

canvas.addEventListener('mousedown', on_mouse_down, false);
window.addEventListener('mousemove', on_mouse_move, false);
window.addEventListener('mouseup', on_mouse_up, false);

////////////////////////////////////////////////////////////////////////
// main
////////////////////////////////////////////////////////////////////////

insert_report();
on_resize();
