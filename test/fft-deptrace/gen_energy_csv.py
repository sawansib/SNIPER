#!/usr/bin/env python

import re, glob, json

# ['cholesky-p16-simsmall', 'MESI', 'OoO', 'TSO', '4', '192', '42', 'NoCoal', 'OnExecute', 'OoO', '16', '256', '16', '16', '1.stats.lines.8.energy']
with open('writersblock_energy.csv', "w") as f:

  f.write('app,coherence_protocol,core_type,memory_ordering,dispatch_width,rob_size,rs_size,coalescing_store_buffer,write_permission_on_execute,commit_type,num_of_mshrs,in_flight_mem_req,ooo_commit_depth,network_flit_size_bytes,energy_metric,energy_core,energy_icache,energy_dcache,energy_l2,energy_l3,energy_noc,time,energy,power\n')

  for fn in glob.glob('*.energy'):
    #print i
    i = fn.split('_')
    if 'simsmall' in i[1]:
      i[0] = i[0]+'.'+i[1]
      del i[1]
    assert(len(i) == 15)
    #print i
    
    f.write(','.join(i))

    # Here write the extra data
    # {'ncores': 16, 'labels': ['core', 'icache', 'dcache', 'l2', 'l3', 'noc'], 'power_data': {0: {'core': 0.4732019963154806, 'icache': 0.05627032269912213, 'noc': 0.0006918731232420561, 'l2': 0.037750933855574466, 'l3': 0.00021666020070022998, 'dcache': 0.1633262354429646}}, 'time_s': 0.029282323}

    with open(fn, 'r') as myfile:
      jsondata=myfile.read().replace("'", '"')
    jsondata = jsondata.replace('{0:','{"0":')

    energy_data = json.loads(jsondata)
    for l in energy_data['labels']:
      f.write(',%s'%energy_data['power_data']['0'][l])
    f.write(',%s'%energy_data['time_s'])
    f.write(',%s'%sum(energy_data['power_data']['0'].values()))
    f.write(',%s'%(sum(energy_data['power_data']['0'].values())/energy_data['time_s']))
    #print energy_data

    f.write('\n')
    

