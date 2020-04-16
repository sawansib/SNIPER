print("Hello from Lua")
print("  Arguments:", arg)

freq_ghz = sim.config.get("perf_model/core/frequency")
print("  core frequency = ", freq_ghz, "GHz")

sim.hooks.register(sim.hooks.HOOK_ROI_BEGIN, function() sim.dvfs.set_frequency(0, 3.92) end)

function roi_end()
  print("ROI end from Lua")
  time_fs = sim.stats.get("performance_model", 0, "elapsed_time")
  print("  cpu0 time", time_fs/1e6, "ns, ", time_fs*freq_ghz/1e6, "cycles")
  freq0_ghz = sim.dvfs.get_frequency(0)
  print("  core0 frequency = ", freq0_ghz, "GHz")
  freqG_ghz = sim.dvfs.get_frequency(sim.dvfs.GLOBAL)
  print("  global frequency = ", freqG_ghz, "GHz")
end
sim.hooks.register(sim.hooks.HOOK_ROI_END, roi_end)

function dvfs_change(coreid)
  print("DVFS change from Lua")
  print("  core", coreid, "new freq", sim.dvfs.get_frequency(coreid), "GHz")
end
sim.hooks.register(sim.hooks.HOOK_CPUFREQ_CHANGE, dvfs_change)
