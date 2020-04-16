--
-- ipctrace.lua
--
-- Write a trace of instantaneous IPC values for all cores.
-- Argument is either a filename, or none to write to standard output.
--

ncores = sim.config.ncores
if arg then
  out = io.output(sim.config.output_dir..arg)
else
  out = nil
end


function update_core_freq(core)
  freqs[core] = sim.dvfs.get_frequency(core)
end

-- initial copy of all frequencies
freqs = {}
for core = 0, ncores-1 do
  update_core_freq(core)
end

-- handle frequency updates
sim.hooks.register(sim.hooks.HOOK_CPUFREQ_CHANGE, update_core_freq)


-- only active during ROI
in_roi = false
sim.hooks.register(sim.hooks.HOOK_ROI_BEGIN, function() in_roi = true end)
sim.hooks.register(sim.hooks.HOOK_ROI_END, function() in_roi = false end)


-- state from previous iteration

prev_time = 0
prev_instrs = {}
function update_state(time)
  prev_time = time
  for core = 0, ncores-1 do
    prev_instrs[core] = sim.stats.get("performance_model", core, "instruction_count")
  end
end


-- at each iteration

sim.hooks.register(sim.hooks.HOOK_PERIODIC, function(time)
  if in_roi then
    if prev_time > 0 then
      line = string.format('%.0f', time/1e6)
      for core = 0, ncores-1 do
        d_instrs = sim.stats.get("performance_model", core, "instruction_count") - prev_instrs[core]
        d_time = time - prev_time
        d_cycles = (d_time / 1e6) * freqs[core]
        line = line..string.format(' %.3f', d_instrs / d_cycles)
      end
      if out then
        out:write(line..'\n')
      else
        print(line)
      end
    end
    update_state(time)
  end
end)
