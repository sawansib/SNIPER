/*
 * This file is covered under the Interval Academic License, see LICENCE.interval
 */

#include "rob_timer.h"

#include "tools.h"
#include "stats.h"
#include "config.hpp"
#include "core_manager.h"
#include "itostr.h"
#include "performance_model.h"
#include "core_model.h"
#include "rob_contention.h"
#include "instruction.h"
#include "thread_manager.h"
#include "thread.h"
#include "hooks_manager.h"

#include <iostream>
#include <sstream>
#include <iomanip>

// Define to get per-cycle printout of dispatch, issue, writeback stages
//#define DEBUG_PERCYCLE

// Define to not skip any cycles, but assert that the skip logic is working fine
//#define ASSERT_SKIP

#define DEBUG_DEPTRACE 0

Lock RobTimer::m_print_lock;

RobTimer::RobTimer(
  Core *core, PerformanceModel *_perf, const CoreModel *core_model,
  int misprediction_penalty,
  int dispatch_width,
  int window_size)
  : dispatchWidth(dispatch_width)
  , commitWidth(Sim()->getCfg()->getIntArray("perf_model/core/rob_timer/commit_width", core->getId()))
  , windowSize(window_size) // windowSize = ROB length = 96 for Core2
  , rsEntries(Sim()->getCfg()->getIntArray("perf_model/core/rob_timer/rs_entries", core->getId()))
  , misprediction_penalty(misprediction_penalty)
  , m_store_to_load_forwarding(Sim()->getCfg()->getBoolArray("perf_model/core/rob_timer/store_to_load_forwarding", core->getId()))
  , m_no_address_disambiguation(!Sim()->getCfg()->getBoolArray("perf_model/core/rob_timer/address_disambiguation", core->getId()))
  , inorder(Sim()->getCfg()->getBoolArray("perf_model/core/rob_timer/in_order", core->getId()))
  , deptrace(Sim()->getCfg()->getBoolArray("perf_model/core/rob_timer/deptrace", core->getId()))
  , deptrace_roi(Sim()->getCfg()->getBoolArray("perf_model/core/rob_timer/deptrace_roi", core->getId()))
  , deptrace_microops(Sim()->getCfg()->getBoolArray("perf_model/core/rob_timer/deptrace_microops", core->getId()))
  , m_core(core)
  , rob(window_size + 255)
  , m_num_in_rob(0)
  , m_rs_entries_used(0)
  , m_rob_contention(
    Sim()->getCfg()->getBoolArray("perf_model/core/rob_timer/issue_contention", core->getId())
    ? core_model->createRobContentionModel(core)
    : NULL)
  , now(core->getDvfsDomain())
  , frontend_stalled_until(SubsecondTime::Zero())
  , in_icache_miss(false)
  , last_store_done(SubsecondTime::Zero())
  , load_queue("rob_timer.load_queue", core->getId(), Sim()->getCfg()->getIntArray("perf_model/core/rob_timer/outstanding_loads", core->getId()))
  , store_queue("rob_timer.store_queue", core->getId(), Sim()->getCfg()->getIntArray("perf_model/core/rob_timer/outstanding_stores", core->getId()))
  , nextSequenceNumber(0)
  , nextInstructionNumber(0)
  , will_skip(false)
  , time_skipped(SubsecondTime::Zero())
  , registerDependencies(new RegisterDependencies())
  , memoryDependencies(new MemoryDependencies())
  , perf(_perf)
  , m_cpiCurrentFrontEndStall(NULL)
  , m_mlp_histogram(Sim()->getCfg()->getBoolArray("perf_model/core/rob_timer/mlp_histogram", core->getId()))
{

  registerStatsMetric("rob_timer", core->getId(), "time_skipped", &time_skipped);

  for(int i = 0; i < MicroOp::UOP_SUBTYPE_SIZE; ++i)
  {
    m_uop_type_count[i] = 0;
    registerStatsMetric("rob_timer", core->getId(), String("uop_") + MicroOp::getSubtypeString(MicroOp::uop_subtype_t(i)), &m_uop_type_count[i]);
  }
  m_insns_total = 0;
  m_uops_total = 0;
  m_uops_x87 = 0;
  m_uops_pause = 0;
  registerStatsMetric("rob_timer", core->getId(), "insns_total", &m_insns_total);
  registerStatsMetric("rob_timer", core->getId(), "uops_total", &m_uops_total);
  registerStatsMetric("rob_timer", core->getId(), "uops_x87", &m_uops_x87);
  registerStatsMetric("rob_timer", core->getId(), "uops_pause", &m_uops_pause);

  m_numSerializationInsns = 0;
  m_totalSerializationLatency = 0;

  registerStatsMetric("rob_timer", core->getId(), "numSerializationInsns", &m_numSerializationInsns);
  registerStatsMetric("rob_timer", core->getId(), "totalSerializationLatency", &m_totalSerializationLatency);

  m_totalHiddenDCacheLatency = 0;
  registerStatsMetric("rob_timer", core->getId(), "totalHiddenDCacheLatency", &m_totalHiddenDCacheLatency);

  m_numMfenceInsns = 0;
  m_totalMfenceLatency = 0;

  registerStatsMetric("rob_timer", core->getId(), "numMfenceInsns", &m_numMfenceInsns);
  registerStatsMetric("rob_timer", core->getId(), "totalMfenceLatency", &m_totalMfenceLatency);

  m_cpiBase = SubsecondTime::Zero();
  m_cpiBranchPredictor = SubsecondTime::Zero();
  m_cpiSerialization = SubsecondTime::Zero();

  registerStatsMetric("rob_timer", core->getId(), "cpiBase", &m_cpiBase);
  registerStatsMetric("rob_timer", core->getId(), "cpiBranchPredictor", &m_cpiBranchPredictor);
  registerStatsMetric("rob_timer", core->getId(), "cpiSerialization", &m_cpiSerialization);
  registerStatsMetric("rob_timer", core->getId(), "cpiRSFull", &m_cpiRSFull);

  m_cpiInstructionCache.resize(HitWhere::NUM_HITWHERES, SubsecondTime::Zero());
  for (int h = HitWhere::WHERE_FIRST ; h < HitWhere::NUM_HITWHERES ; h++)
  {
    if (HitWhereIsValid((HitWhere::where_t)h))
    {
      String name = "cpiInstructionCache" + String(HitWhereString((HitWhere::where_t)h));
      registerStatsMetric("rob_timer", core->getId(), name, &(m_cpiInstructionCache[h]));
    }
  }
  m_cpiDataCache.resize(HitWhere::NUM_HITWHERES, SubsecondTime::Zero());
  for (int h = HitWhere::WHERE_FIRST ; h < HitWhere::NUM_HITWHERES ; h++)
  {
    if (HitWhereIsValid((HitWhere::where_t)h))
    {
      String name = "cpiDataCache" + String(HitWhereString((HitWhere::where_t)h));
      registerStatsMetric("rob_timer", core->getId(), name, &(m_cpiDataCache[h]));
    }
  }

  m_outstandingLongLatencyCycles = SubsecondTime::Zero();
  m_outstandingLongLatencyInsns = SubsecondTime::Zero();
  m_lastAccountedMemoryCycle = SubsecondTime::Zero();

  registerStatsMetric("rob_timer", core->getId(), "outstandingLongLatencyInsns", &m_outstandingLongLatencyInsns);
  registerStatsMetric("rob_timer", core->getId(), "outstandingLongLatencyCycles", &m_outstandingLongLatencyCycles);

  m_loads_count = 0;
  m_loads_latency = SubsecondTime::Zero();
  m_stores_count = 0;
  m_stores_latency = SubsecondTime::Zero();

  registerStatsMetric("rob_timer", core->getId(), "loads-count", &m_loads_count);
  registerStatsMetric("rob_timer", core->getId(), "loads-latency", &m_loads_latency);
  registerStatsMetric("rob_timer", core->getId(), "stores-count", &m_stores_count);
  registerStatsMetric("rob_timer", core->getId(), "stores-latency", &m_stores_latency);

  m_totalProducerInsDistance = 0;
  m_totalConsumers = 0;
  m_producerInsDistance.resize(windowSize, 0);

  registerStatsMetric("rob_timer", core->getId(), "totalProducerInsDistance", &m_totalProducerInsDistance);
  registerStatsMetric("rob_timer", core->getId(), "totalConsumers", &m_totalConsumers);
  for (unsigned int i = 0; i < m_producerInsDistance.size(); i++)
  {
    String name = "producerInsDistance[" + itostr(i) + "]";
    registerStatsMetric("rob_timer", core->getId(), name, &(m_producerInsDistance[i]));
  }

  if (m_mlp_histogram)
  {
    m_outstandingLoads.resize(HitWhere::NUM_HITWHERES);
    for (unsigned int h = HitWhere::WHERE_FIRST ; h < HitWhere::NUM_HITWHERES ; h++)
    {
      if (HitWhereIsValid((HitWhere::where_t)h))
      {
	m_outstandingLoads[h].resize(MAX_OUTSTANDING, SubsecondTime::Zero());
	for(unsigned int i = 0; i < MAX_OUTSTANDING; ++i)
	{
	  String name = String("outstandingLoads.") + HitWhereString((HitWhere::where_t)h) + "[" + itostr(i) + "]";
	  registerStatsMetric("rob_timer", core->getId(), name, &(m_outstandingLoads[h][i]));
	}
      }
    }

    m_outstandingLoadsAll.resize(MAX_OUTSTANDING, SubsecondTime::Zero());
    for(unsigned int i = 0; i < MAX_OUTSTANDING; ++i)
    {
      String name = String("outstandingLoadsAll") + "[" + itostr(i) + "]";
      registerStatsMetric("rob_timer", core->getId(), name, &(m_outstandingLoadsAll[i]));
    }
  }

  if (deptrace)
  {
    _deptrace_f = std::unique_ptr<std::ostream>(new zstr::ofstream((Sim()->getConfig()->formatOutputFileName(String("sim.deptrace.")+itostr(core->getId())+".gz")).c_str()));
    _deptrace_insn_f = std::unique_ptr<std::ostream>(new zstr::ofstream((Sim()->getConfig()->formatOutputFileName(String("sim.deptrace_insn.")+itostr(core->getId())+".gz")).c_str()));

    if (deptrace_roi)
    {
      if (m_core->getId() == 0)
      {
	ScopedLock sl(m_print_lock);
	std::cout << "[DEPTRACE] Enabling trace generation with ROI\n";
      }
      Sim()->getHooksManager()->registerHook(HookType::HOOK_ROI_BEGIN, __deptrace_roi_begin, (UInt64)this);
      Sim()->getHooksManager()->registerHook(HookType::HOOK_ROI_END, __deptrace_roi_end, (UInt64)this);
    }
    else
    {
      if (m_core->getId() == 0)
      {
	ScopedLock sl(m_print_lock);
	std::cout << "[DEPTRACE] Enabling trace generation via RMS function\n";
      }
    }

    Sim()->getHooksManager()->registerHook(HookType::HOOK_THREAD_CREATE, __deptrace_thread_create, (UInt64)this);
  }
  else
  {
    _deptrace_f = std::unique_ptr<std::ostream>(new std::ofstream("/dev/null"));
    _deptrace_insn_f = std::unique_ptr<std::ostream>(new std::ofstream("/dev/null"));
  }

}

bool RobTimer::deptraceAnyActive()
{
  for (auto &i : deptrace_active)
  {
    if (std::get<1>(i))
      return true;
  }
  return false;
}

// ROI-like state
bool RobTimer::deptraceRMSIsActive(thread_id_t thread_id)
{
  return deptrace_rms_active[thread_id];
}

// ROI-like state
void RobTimer::deptraceRMSSetActive(thread_id_t thread_id, bool is_active)
{
  {
    ScopedLock sl(m_print_lock);
    if (is_active) {
      std::cout << "[DEPTRACE:"<<m_core->getId()<<":"<<thread_id<<"] RMS: Enabling trace generation after "<<m_insns_total<<" instructions / "<<m_uops_total<<" micro-ops\n";
    } else {
      std::cout << "[DEPTRACE:"<<m_core->getId()<<":"<<thread_id<<"] RMS: Disabling trace generation after "<<m_insns_total<<" instructions / "<<m_uops_total<<" micro-ops\n";
    }
  }
  deptrace_rms_active[thread_id] = is_active;
}

// We need to be both in an ROI-like state (RMS active) and the thread needs to be active to write data to the trace file
bool RobTimer::deptraceIsActive(thread_id_t thread_id)
{
  return deptrace_rms_active[thread_id] && deptrace_active[thread_id];
}

// Allow the changing of the active state (determined by the trace commands), even if we aren't in RMS-active. This is independent of RMS active.
void RobTimer::deptraceSetActive(thread_id_t thread_id, bool is_active)
{
  deptrace_active[thread_id] = is_active;
}

// When we create new threads, set the start active flag appropriately
void RobTimer::deptrace_thread_create(HooksManager::ThreadCreate *args)
{
  if (deptrace_roi)
  {
    // ROI mode uses the RMS variable to indicate the ROI region
    deptrace_rms_active[args->thread_id] = deptrace_roi_seen;
  }
  else
  {
    // RMS mode needs a per-thread ready indicator to be seen
    deptrace_rms_active[args->thread_id] = false;
  }

  // this active variable is only to disable trace generation during spinloops/syscalls, etc.
  // Default to enabled
  deptrace_active[args->thread_id] = true;
}

void RobTimer::deptrace_roi_begin()
{
  deptrace_roi_seen = true;
  if (deptrace_roi)
  {
    if (m_core->getId() == 0)
    {
      ScopedLock sl(m_print_lock);
      std::cout << "[DEPTRACE] ROI: Enabling trace generation\n";
    }
    for (auto &i : deptrace_rms_active)
    {
      std::get<1>(i) = true;
    }
  }
}

void RobTimer::deptrace_roi_end()
{
  deptrace_roi_seen = false;
  if (deptrace_roi)
  {
    if (m_core->getId() == 0)
    {
      ScopedLock sl(m_print_lock);
      std::cout << "[DEPTRACE] ROI: Disabling trace generation\n";
    }
    for (auto &i : deptrace_rms_active)
    {
      std::get<1>(i) = false;
    }
  }
}

RobTimer::~RobTimer()
{
  for(Rob::iterator it = this->rob.begin(); it != this->rob.end(); ++it)
    it->free();

  if (deptrace) // && deptraceAnyActive())
  {
    if (deptrace_last_was_newline)
      deptrace_last_was_newline = false;
    else
      (*_deptrace_f) << "\n";

    if (!deptrace_seen_end_tran) {
      (*_deptrace_f) << "END " << std::hex << deptrace_last_pc << std::dec << "\n" << std::flush;
      deptrace_seen_end_tran = true;
    }
    for (auto &i : deptrace_active)
    {
      std::get<1>(i) = false;
    }
  }
}

void RobTimer::RobEntry::init(DynamicMicroOp *_uop, UInt64 sequenceNumber, UInt64 instructionNumber)
{
  ready = SubsecondTime::MaxTime();
  readyMax = SubsecondTime::Zero();
  addressReady = SubsecondTime::MaxTime();
  addressReadyMax = SubsecondTime::Zero();
  issued = SubsecondTime::MaxTime();
  done = SubsecondTime::MaxTime();

  uop = _uop;
  uop->setSequenceNumber(sequenceNumber);
  uop->setInstructionNumber(instructionNumber);

  addressProducers.clear();

  numInlineDependants = 0;
  vectorDependants = NULL;
}

void RobTimer::RobEntry::free()
{
  delete uop;
  if (vectorDependants)
    delete vectorDependants;
}

void RobTimer::RobEntry::addDependant(RobTimer::RobEntry* dep)
{
  if (numInlineDependants < MAX_INLINE_DEPENDANTS)
  {
    inlineDependants[numInlineDependants++] = dep;
  }
  else
  {
    if (vectorDependants == NULL)
    {
      vectorDependants = new std::vector<RobEntry*>();
    }
    vectorDependants->push_back(dep);
  }
}

uint64_t RobTimer::RobEntry::getNumDependants() const
{
  return numInlineDependants + (vectorDependants ? vectorDependants->size() : 0);
}

RobTimer::RobEntry* RobTimer::RobEntry::getDependant(size_t idx) const
{
  if (idx < MAX_INLINE_DEPENDANTS)
  {
    LOG_ASSERT_ERROR(idx < numInlineDependants, "Invalid idx %d", idx);
    return inlineDependants[idx];
  }
  else
  {
    LOG_ASSERT_ERROR(idx - MAX_INLINE_DEPENDANTS < vectorDependants->size(), "Invalid idx %d", idx);
    return (*vectorDependants)[idx - MAX_INLINE_DEPENDANTS];
  }
}

RobTimer::RobEntry *RobTimer::findEntryBySequenceNumber(UInt64 sequenceNumber)
{
  // Assumption: MicroOps in the ROB are numbered sequentially, none of them are removed halfway
  UInt64 first = rob[0].uop->getSequenceNumber();
  UInt64 position = sequenceNumber - first;
  LOG_ASSERT_ERROR(position < rob.size(), "Sequence number %ld outside of ROB", sequenceNumber);
  RobEntry *entry = &rob[position];
  LOG_ASSERT_ERROR(entry->uop->getSequenceNumber() == sequenceNumber, "Sequence number %ld unexpectedly not at ROB position %ld", sequenceNumber, position);
  return entry;
}

bool RobTimer::IsOutOfRange(UInt64 sequenceNumber){
  UInt64 first = rob[0].uop->getSequenceNumber();
  UInt64 position = sequenceNumber - first;
  if(position > rob.size())
    return true;
  else
    return false;
}

void RobTimer::resetDepValue(){
  for (int i = 0; i < 64; i++)
    {
      DepValue[i] = 0;
    }
}

int RobTimer::FinalMarkerValue() {
  std::stringstream ss;
  for (int i = 0; i < xchg_dep_executed; ++i)
    ss << DepValue[i];
  int result = 0;
  ss >> result;
  return result;
}

long long RobTimer::getPCDiff(uint64_t pc1, uint64_t pc2)
{
  long long diff;
  if (pc1 >= pc2) {
    diff = pc1 - pc2;
  }
  else
  {
    diff = pc2 - pc1;
    diff = 0 - diff;
  }
  return diff;
}

long long RobTimer::savePCdiff()
{
  DynamicMicroOp &dmo = *entry->uop;
  auto new_pc = dmo.getMicroOp()->getInstruction()->getAddress();
  long long diff = getPCDiff(new_pc, deptrace_last_pc);
  deptrace_last_pc = new_pc; //the pc that we printed
    return diff;
}

std::string RobTimer::getPCDiffAndUpdateLast()
{
  DynamicMicroOp &dmo = *entry->uop;
  auto new_pc = dmo.getMicroOp()->getInstruction()->getAddress();
  long long diff = getPCDiff(new_pc, deptrace_last_pc);
  deptrace_last_pc = new_pc; //the pc that we printed
  return std::to_string(diff);
}

std::string RobTimer::getPCDiffAndUpdateLast_Marker()
{
  DynamicMicroOp &dmo = *entry->uop;
  auto new_pc = dmo.getMicroOp()->getInstruction()->getAddress();
  long long diff = getPCDiff(new_pc, deptrace_last_pc);
  //assert(marker_executed > 0);
  //assert(marker_size > 0);
  diff = diff+newpcdiff;
  deptrace_last_pc = new_pc;
  return std::to_string(diff);
}

uint64_t RobTimer::getXCHGrdep(uint64_t rdep, uint64_t num_seq){
  bool inloop = false;
  uint64_t num_xchg_in_loop = 0;
  uint64_t num_xchg = 0;
  bool dep_on_xchg = false;
  
  for (int i = rdep; i > 0; i--){
      RobEntry *depentry =  findEntryBySequenceNumber(num_seq - i);
      if (depentry->uop->mGetMarker()) num_xchg++;
  }
  
  RobEntry *depentry =  findEntryBySequenceNumber(num_seq - rdep); //check if the dependence falls on XCHG
  if (depentry->uop->mGetMarker()) { 
    dep_on_xchg = true;
    inloop = true;
    rdep += depentry->uop->mGetrdep();
    while(inloop){
      is_out_of_range = IsOutOfRange(num_seq - rdep);
      if(!is_out_of_range) //give the else condition for this loop
	{
	  RobEntry *depentry =  findEntryBySequenceNumber(num_seq - rdep);
	  if (depentry->uop->mGetMarker()
	      && depentry->uop->mGetrdep() ){
	    rdep += depentry->uop->mGetrdep();
	  }
	  else  //we leave adding the dependencies when rdep comes 0 or next pointed is not XCHG
	    break;
	}
      else
	break;
    }
    
    for (int i = rdep; i > 0; i--){
      bool tmp = IsOutOfRange(num_seq - i);
      if(!tmp)
	{
	  RobEntry *depentry =  findEntryBySequenceNumber(num_seq - i);
	  if (depentry->uop->mGetMarker()) num_xchg_in_loop++;
	}
    }
  }
  if(dep_on_xchg)
    return rdep - num_xchg_in_loop;
  else
    return rdep - num_xchg;
}

uint64_t RobTimer::getXCHGmdep(uint64_t mdep, uint64_t num_seq){
  bool inloop = false;
  uint64_t num_xchg_in_loop = 0;
  uint64_t num_xchg = 0;
  bool dep_on_xchg = false;

  for (int i = mdep; i > 0; i--){
    RobEntry *depentry =  findEntryBySequenceNumber(num_seq - i);
    if (depentry->uop->mGetMarker()) num_xchg++;
  }
  RobEntry *depentry =  findEntryBySequenceNumber(num_seq - mdep); //check if the dependence falls on XCHG
  if (depentry->uop->mGetMarker()) {
    dep_on_xchg = true;
    inloop = true;
    mdep += depentry->uop->mGetmdep();
    while(inloop){
      is_out_of_range = IsOutOfRange(num_seq - mdep);
      if(!is_out_of_range)
	{
	  RobEntry *depentry =  findEntryBySequenceNumber(num_seq - mdep);
	  if (depentry->uop->mGetMarker()
	      && depentry->uop->mGetmdep()){
	    mdep += depentry->uop->mGetmdep();
	  }
	  else
	    break;
	}
       else
	 break;
    }
    for (int i = mdep; i > 0; i--){
      bool tmp = IsOutOfRange(num_seq - i);
      if(!tmp){
      RobEntry *depentry =  findEntryBySequenceNumber(num_seq - i);
      if (depentry->uop->mGetMarker()) num_xchg_in_loop++;
      }
    }
  }
  if(dep_on_xchg)
    return mdep - num_xchg_in_loop;
  else
    return mdep - num_xchg;
}

uint64_t RobTimer::getXCHGadep(uint64_t adep, uint64_t num_seq){
  bool inloop = true;
  uint64_t num_xchg_in_loop = 0;
  uint64_t num_xchg = 0;
  bool dep_on_xchg = false;
  for (int i = adep; i > 0; i--){
    RobEntry *depentry =  findEntryBySequenceNumber(num_seq - i);
    if (depentry->uop->mGetMarker()) num_xchg++;
  }
  RobEntry *depentry =  findEntryBySequenceNumber(num_seq - adep); //check if the dependence falls on XCHG
  if (depentry->uop->mGetMarker()) {
    dep_on_xchg = true;
    inloop = true;
    adep += depentry->uop->mGetadep();
    while(inloop){
      is_out_of_range = IsOutOfRange(num_seq - adep);
      if(!is_out_of_range)
	{
	  RobEntry *depentry =  findEntryBySequenceNumber(num_seq - adep);
	  if (depentry->uop->mGetMarker()
	      && depentry->uop->mGetadep() ){
	    adep += depentry->uop->mGetadep();
	  }
	  else
	    break;
       }
       else
	 break;
    }
    for (int i = adep; i > 0; i--){
      bool tmp = IsOutOfRange(num_seq - i);
      if(!tmp){
	RobEntry *depentry =  findEntryBySequenceNumber(num_seq - i);
      if (depentry->uop->mGetMarker()) num_xchg_in_loop++;
      }
    }
  }
  if(dep_on_xchg)
    return adep - num_xchg_in_loop;
  else
   return adep - num_xchg;
}


boost::tuple<uint64_t,SubsecondTime> RobTimer::simulate(const std::vector<DynamicMicroOp*>& insts)
{
  uint64_t totalInsnExec = 0;
  SubsecondTime totalLat = SubsecondTime::Zero();
  std::ostream& deptrace_f = *_deptrace_f;
  
  Thread* thread = Sim()->getThreadManager()->getThreadOnCore(m_core->getId());
  thread_id_t thread_id = thread ? thread->getId() : 0xffffffff;

  for (std::vector<DynamicMicroOp*>::const_iterator it = insts.begin(); it != insts.end(); it++ )
  {
    if ((*it)->isSquashed())
    {
      delete *it;
      continue;
    }

    entry = &this->rob.next();
       
    entry->init(*it, nextSequenceNumber++, nextInstructionNumber);
    if ((*it)->isLast())
    {
      nextInstructionNumber++;
      instr_to_insert_clear_stats--;
      if (instr_to_insert_clear_stats == 0) 
      {
	if (deptrace_last_was_newline)
	  deptrace_last_was_newline = false;
	else
	  deptrace_f << " ";
	deptrace_f << "CLEAR";
      }
    }

    // Disable this for now. Just for testing
    if (false /*deptrace_active*/)
    {
      (*_deptrace_insn_f) << (*it)->getSequenceNumber() << " " << (*it)->getInstructionNumber() << " " << deptrace_insn_count << " " << (*it)->getMicroOp()->isLoad() << (*it)->getMicroOp()->isStore() << (*it)->getMicroOp()->isBranch() << " " << (*it)->getMicroOp()->getInstruction()->getDisassembly() << "\n";
      if ((*it)->getInstructionNumber() > deptrace_last_insn)
	deptrace_insn_count++;
      deptrace_last_insn = (*it)->getInstructionNumber();
#if ENABLE_MICROOP_STRINGS
      (*_deptrace_insn_f) << (*it)->getMicroOp()->toString() << "\n";
#endif
    }

    // Add = calculate dependencies, add yourself to list of depenants
    // If no dependants in window: set ready = now()
    uint64_t lowestValidSequenceNumber = this->rob.size() > 0 ? this->rob.front().uop->getSequenceNumber() : 0;
    if (entry->uop->getMicroOp()->isStore())
    {
      for(unsigned int i = 0; i < entry->uop->getMicroOp()->getAddressRegistersLength(); ++i)
      {
	xed_reg_enum_t reg = entry->uop->getMicroOp()->getAddressRegister(i);
	uint64_t addressProducer = this->registerDependencies->peekProducer(reg, lowestValidSequenceNumber);
	if (addressProducer != INVALID_SEQNR)
	{
	  RobEntry *prodEntry = this->findEntryBySequenceNumber(addressProducer);
	  if (prodEntry->done != SubsecondTime::MaxTime())
	    entry->addressReadyMax = std::max(entry->addressReadyMax, prodEntry->done);
	  else
	    entry->addAddressProducer(addressProducer);

	  // Add addr gen dependencies too
	  if (deptraceIsActive(thread_id))
	  {
	    //uint64_t d = entry->uop->getDependency(i);
	    uint64_t in = deptrace_microops ? entry->uop->getSequenceNumber() : entry->uop->getInstructionNumber();
	    RobEntry *depentry = prodEntry; //findEntryBySequenceNumber(d);
	    assert(depentry);
	    // microop? Yes, then grab the SeqNum, otherwise, the InsnNum
	    uint64_t din = deptrace_microops ? depentry->uop->getSequenceNumber() : depentry->uop->getInstructionNumber();
	    if (in != din)
	    {
	      deptrace_addr_deps.insert(in-din);
	    }
	  }

	}
      }
      if (entry->getNumAddressProducers() == 0)
	entry->addressReady = entry->addressReadyMax;
    }
    this->registerDependencies->setDependencies(*entry->uop, lowestValidSequenceNumber);

    if (deptraceIsActive(thread_id))
    {
      // Effectively disables memory dependencies
      size_t num_reg_dep = entry->uop->getDependenciesLength();
      // Save all of our dependencies, no matter which micro-op we are
      for (size_t i = 0 ; i < entry->uop->getDependenciesLength() ; ++i)
	{
	  uint64_t d = entry->uop->getDependency(i);
	  uint64_t in = deptrace_microops ? entry->uop->getSequenceNumber() : entry->uop->getInstructionNumber();
	  RobEntry *depentry = findEntryBySequenceNumber(d);
	  assert(depentry);
	  // microop? Yes, then grab the SeqNum, otherwise, the InsnNum
	  uint64_t din = deptrace_microops ? depentry->uop->getSequenceNumber() : depentry->uop->getInstructionNumber();
	  if (in != din)
	    {
	      if (i < num_reg_dep) {
		// Only add the register dependency if we don't find the addr-gen dep
		if (deptrace_addr_deps.count(in-din) == 0) {
		  deptrace_reg_deps.insert(in-din);
		}
	      } else {
		deptrace_mem_deps.insert(in-din);
	      }
	    }
	}
      if (entry->getNumAddressProducers() == 0)
	entry->addressReady = entry->addressReadyMax;
    }
    this->memoryDependencies->setDependencies(*entry->uop, lowestValidSequenceNumber);

    /* Trace format:
     *  [L|LA]<PC_diff_in_decimal>(d<dep>)(m<mem_dep>) <hex_addr> <size>
     *  [S|SA]<PC_diff_in_decimal>(d<dep>)(m<mem_dep>)(a<addr_dep>) <hex_addr> <size>
     *  B<PC_diff_in_decimal>(d<dep>)(m<dep>)(t<target_addr>)(*)?
     *  [A|M|D|Q|]<PC_diff_in_decimal>(d<dep>)(m<dep>)
     *
     * Legend:
     *  L=load, LA=load of atomic, S=store, SA=store of atomic, 
     *  B=conditional branch, A=fp_addsub, M=fp_mul, D=fp_div, Q=fp_sqrt, []=generic
     *  d=reg dependence, m=mem dependence, a=addr dependence, t=target address, *=taken
      
     * Example: 
     *  2 A0 3d1 B2d2t-120* L5d1 fff0 4
     */
    if (deptraceIsActive(thread_id))
    {
      // Collects whether we are a load/store/branch over time
      if ((*it)->getMicroOp()->isBranch())
      {
	deptrace_is_branch = true;
      }
      if ((*it)->getMicroOp()->isLoad())
      {
	deptrace_is_load = true;
	assert(deptrace_load_addr == 0x0);
	deptrace_load_addr = (*it)->getAddress().address;
	deptrace_load_size = (*it)->getMicroOp()->getMemoryAccessSize();
      }
      if ((*it)->getMicroOp()->isStore())
      {
	deptrace_is_store = true;
	assert(deptrace_store_addr == 0x0);
	deptrace_store_addr = (*it)->getAddress().address;
	deptrace_store_size = (*it)->getMicroOp()->getMemoryAccessSize();
      }

      // If we are looking for instructions (!deptrace_microops), then we only do this on the last instruction
      // If we are looking for microops (deptrace_microops), then we handle this for each microop
      if ((*it)->isLast() || deptrace_microops)
      {
	DynamicMicroOp &dmo = *entry->uop;
         
	if (deptrace_first_line) {
	  deptrace_last_pc = dmo.getMicroOp()->getInstruction()->getAddress();
	  deptrace_f << std::hex << deptrace_last_pc << std::dec << "\n"; 
	  deptrace_first_line = false;
	  instr_to_insert_clear_stats = Sim()->getCfg()->getInt("rob_timer/insert-clear-stats-by-icount");
	}

	if (deptrace_is_load)
	{
	  if (deptrace_last_was_newline)
	    deptrace_last_was_newline = false;
	  else
	   deptrace_f << " ";
	  if(next_load_marker){
	    if (dmo.getMicroOp()->getInstruction()->isAtomic()) //change bewlow 
	      deptrace_f << "LA" << getPCDiffAndUpdateLast_Marker(); // Load uop (part of an atomic instruction)
	    else
	      deptrace_f << "L" << getPCDiffAndUpdateLast_Marker();
	    
#if DEBUG_DEPTRACE >= 1
	    deptrace_f << "(" << std::hex << dmo.getMicroOp()->getInstruction()->getAddress() << std::dec << ")";
#endif
	    for (auto rdep : deptrace_reg_deps) //change below
	      {
		uint64_t tmp = this->getXCHGrdep(rdep,dmo.getSequenceNumber());
		if(!is_out_of_range)deptrace_f << "d" << tmp;
		//deptrace_f << "d" << rdep;
	      }
 	    for (auto mdep : deptrace_mem_deps)
	      {
		uint64_t tmp = this->getXCHGmdep(mdep,dmo.getSequenceNumber());
		if(!is_out_of_range)deptrace_f << "m" << tmp;
		// deptrace_f << "m" << mdep;
	      }
	    assert(last_load_pending == true);
	    if(!is_not_known_must && !is_not_known_may){ //both known
	      deptrace_f <<"s"<<final_DepValue_may;
	      deptrace_f <<"f"<<final_DepValue_must;
	    }
	    
	    else if(!is_not_known_must && is_not_known_may){ //only may alias is not known
	      deptrace_f <<"s99999";
	    }
	    
	    else if(is_not_known_must && !is_not_known_may){ //only must alias is not known
	      deptrace_f <<"f99999";
	    }
	    else if(is_not_known_must && is_not_known_may){ //both are not known
	      deptrace_f <<"s99999";
	      deptrace_f <<"f99999";
	    }
	    else
	      assert(false);
	    
	    final_DepValue_must = 0;
	    final_DepValue_may = 0;
	  }
	  else {
	    if (dmo.getMicroOp()->getInstruction()->isAtomic()) 
	      deptrace_f << "LA" << getPCDiffAndUpdateLast_Marker(); // Load uop (part of an atomic instruction)
	    else
	      deptrace_f << "L" << getPCDiffAndUpdateLast_Marker();
	    
#if DEBUG_DEPTRACE >= 1
	    deptrace_f << "(" << std::hex << dmo.getMicroOp()->getInstruction()->getAddress() << std::dec << ")";
#endif
	    for (auto rdep : deptrace_reg_deps)
	      {
		uint64_t tmp = this->getXCHGrdep(rdep,dmo.getSequenceNumber());
		if(!is_out_of_range)deptrace_f << "d" << tmp;
		//deptrace_f << "d" << rdep;
	      }
	    for (auto mdep : deptrace_mem_deps)
	      {
		uint64_t tmp = this->getXCHGmdep(mdep,dmo.getSequenceNumber());
		if(!is_out_of_range)deptrace_f << "m" << tmp;
		// deptrace_f << "m" << mdep;
	      }
	  }
	  
	  assert(deptrace_addr_deps.size() == 0);
	  deptrace_f << " " << std::hex << deptrace_load_addr << std::dec;
	  deptrace_f << " " << deptrace_load_size << "\n";
	  deptrace_load_addr = 0x0;
	  deptrace_last_was_newline = true;
	  next_load_marker = false;
	  last_load_pending = false;
	  last_was_marker = false;
	  marker_executed = 0;
	  newpcdiff = 0; //change this one as well
	  is_not_known_must = 0;
	  is_not_known_may = 0;
	}
	if (deptrace_is_store)
	  {
	    if (deptrace_last_was_newline)
	    deptrace_last_was_newline = false;
	    else
	      deptrace_f << " ";
	    if (dmo.getMicroOp()->getInstruction()->isAtomic()) 
	      deptrace_f << "SA" << getPCDiffAndUpdateLast_Marker(); // Store uop (part of an atomic instruction)
	    else
	      deptrace_f << "S" << getPCDiffAndUpdateLast_Marker();
	    
#if DEBUG_DEPTRACE >= 1
	    deptrace_f << "(" << std::hex << dmo.getMicroOp()->getInstruction()->getAddress() << std::dec << ")";
#endif
	    for (auto rdep : deptrace_reg_deps)
	      {
		uint64_t tmp = this->getXCHGrdep(rdep,dmo.getSequenceNumber());
		if(!is_out_of_range)deptrace_f << "d" << tmp;
		// deptrace_f << "d" << rdep;
	      }
	    for (auto mdep : deptrace_mem_deps)
	      {
		uint64_t tmp = this->getXCHGmdep(mdep,dmo.getSequenceNumber());
		if(!is_out_of_range)deptrace_f << "m" << tmp;
		// deptrace_f << "m" << mdep;
	      }
	    for (auto adep : deptrace_addr_deps)
	      {
		uint64_t tmp = this->getXCHGadep(adep,dmo.getSequenceNumber());
		if(!is_out_of_range)deptrace_f << "a" << tmp;
		// deptrace_f << "a" << adep;
	      }
	    deptrace_f << " " << std::hex << deptrace_store_addr << std::dec;
	    deptrace_f << " " << deptrace_store_size << "\n";
	    deptrace_store_addr = 0x0;
	    deptrace_last_was_newline = true;
	    newpcdiff = 0;
	  }
	
	if (deptrace_is_branch)
	  {
	    if (deptrace_last_was_newline)
	      deptrace_last_was_newline = false;
	    else
	      deptrace_f << " ";
	    assert(!(dmo.getMicroOp()->getInstruction()->isAtomic()));
	    deptrace_f << "B" << getPCDiffAndUpdateLast_Marker();
	    
#if DEBUG_DEPTRACE >= 1
	    deptrace_f << "(" << std::hex << dmo.getMicroOp()->getInstruction()->getAddress() << std::dec << ")";
#endif
	    for (auto rdep : deptrace_reg_deps)
	      {
		uint64_t tmp = this->getXCHGrdep(rdep,dmo.getSequenceNumber());
		if(!is_out_of_range)deptrace_f << "d" << tmp;
		//deptrace_f << "d" << rdep;
	  }
	    for (auto mdep : deptrace_mem_deps)
	      {
		uint64_t tmp = this->getXCHGmdep(mdep,dmo.getSequenceNumber());
		if(!is_out_of_range)deptrace_f << "m" << tmp;
		// deptrace_f << "m" << mdep;
	      }
	    assert(deptrace_addr_deps.size() == 0);
	    // No newlines for branches
	    
	    deptrace_f << "t" << getPCDiff(dmo.getBranchTarget(), deptrace_last_pc);
	    if (dmo.isBranchTaken()) 
	      deptrace_f << "*";
	    newpcdiff = 0;
	  }
	
	// For non-branch, non load, non-store instructions
	if (!deptrace_is_branch && !deptrace_is_load && !deptrace_is_store)
	{
	  if (deptrace_last_was_newline)
	    deptrace_last_was_newline = false;
	  else
	    deptrace_f << " ";	       

	  // If magic, print it
	  if (dmo.isXchg()) {
	    if (dmo.getRegValue() > 0) 
	      deptrace_f << "BEGIN_iNDRF " << dmo.getRegValue() << " ";
	    else 
	      deptrace_f << "END_iNDRF " << 0 - dmo.getRegValue() << " ";
	  }
	  
	  if(dmo.mGetMarker()){	   
	    deptrace_last_was_newline = true;
	    total_marker_executed++;
	    marker_executed++;
	     newpcdiff += savePCdiff();
	    if (dmo.mGetMarkerBegin()){
	      //deptrace_f << "XCHG_RDI "; 
	      for(int i = 0; i<64; i++) xchg_dep_rdep[i]=0;
	      xchg_dep_executed = 0;
	      last_was_marker = true;
	      marker_begin_size = dmo.getMicroOp()->getInstruction()->getAddress();
	      ss.str(""); //reset for new value
	      look_for_value = true; //begin looking for values
	    }
	   
	    if ((dmo.mGetMarkerEnd() && look_for_value) ||
		(dmo.mGetMarkerEnd() && look_for_loop_id_begin) ||
		(dmo.mGetMarkerEnd() && look_for_loop_id_end)){
	      //deptrace_f << "XCHG_RCX " << "MAR " <<last_was_may;
	      if (look_for_value){
		if(last_was_may)
		  final_DepValue_may = this->FinalMarkerValue();
		else 
		  final_DepValue_must = this->FinalMarkerValue();
		//deptrace_f << "MAY " <<final_DepValue_may<<" MUST"<<final_DepValue_must<<" ";
		if(last_was_may)
		  last_was_may = false;
		else
		  last_was_may = true;
	      }
	      
	      if(look_for_loop_id_begin || look_for_loop_id_end){
		loop_id = this->FinalMarkerValue();
		if(look_for_loop_id_begin) deptrace_f<<"BEGIN_LOOP "<<loop_id<<" ";
		if(look_for_loop_id_end)   deptrace_f<<"END_LOOP "<<loop_id<<" ";
	      }
	      assert(xchg_dep_executed > 0);
	      look_for_value = false; //stop looking for value
	      last_load_pending = true;
	      next_load_marker = true;
	      look_for_loop_id_begin = false;
	      look_for_loop_id_end = false;
	      loop_id = 0;		      
	    }

	    if (dmo.mGetIsNotKnown() && look_for_value){
	      xchg_dep_executed++;
	      //deptrace_f << "XCHG_RBX "; 
	      if(last_was_may)
		is_not_known_may = true;
	      else
		is_not_known_must = true;
	    }

	    if ((dmo.mGetMarkerDep() && look_for_value)
		|| (dmo.mGetMarkerDep() && look_for_loop_id_begin)
		|| (dmo.mGetMarkerDep() && look_for_loop_id_end)){
	      //deptrace_f << "XCHG_R " <<dmo.mGetMarkerValue()<<" "; 
	      marker_dep_size = dmo.getMicroOp()->getInstruction()->getAddress();
	      marker_size =  marker_dep_size - marker_begin_size;
	      assert(marker_size > 0);
	      DepValue[xchg_dep_executed] =  dmo.mGetMarkerValue(); //save value
	      xchg_dep_executed++;
	      		      
	    }
	    
	    if (dmo.mGetMarkerBeginLoop()){
	       xchg_dep_executed = 0;
	      look_for_loop_id_begin = true;
	      //deptrace_f << "XCHG_RSI"<<" ";
	      //std::cout<<"BEGIN_LOOP\n";
	    }
	    if (dmo.mGetMarkerEndLoop()){
	       xchg_dep_executed = 0;
	      look_for_loop_id_end = true;
	      //deptrace_f << "XCHG_RDX"<<" ";
	      //std::cout<<"END_LOOP\n";
	    }
	  }
	  
	  else if (dmo.getMicroOp()->getSubtype() == MicroOp::UOP_SUBTYPE_FP_ADDSUB) {
	    deptrace_f << "A";
	  } else if (dmo.getMicroOp()->getSubtype() == MicroOp::UOP_SUBTYPE_FP_MUL) { 
	    deptrace_f << "M";
	  } else if (dmo.getMicroOp()->getSubtype() == MicroOp::UOP_SUBTYPE_FP_DIV) { 
	    deptrace_f << "D";
	  } else if (dmo.getMicroOp()->getSubtype() == MicroOp::UOP_SUBTYPE_FP_SQRT) { 
	    deptrace_f << "Q";
	  } // else deptrace_f << "i";
	  if(!dmo.mGetMarker()){
	    deptrace_f << getPCDiffAndUpdateLast_Marker();
	    newpcdiff = 0;
	  }   
#if DEBUG_DEPTRACE >= 1
	  deptrace_f << "(" << std::hex << dmo.getMicroOp()->getInstruction()->getAddress() << std::dec << ")";
#endif
	  for (auto rdep : deptrace_reg_deps)
	    {
	      if(dmo.mGetMarker()){
		//deptrace_f << "d" << rdep << " ";
		dmo.mSetrdep(rdep);
	      }
	      else{
		uint64_t tmp = this->getXCHGrdep(rdep,dmo.getSequenceNumber());
		if(!is_out_of_range)deptrace_f << "d" << tmp;
		//deptrace_f << "d" << rdep;
	      }
	    }
	  for (auto mdep : deptrace_mem_deps)
	    {
	      if(dmo.mGetMarker()){
		//deptrace_f << "m" << mdep << " ";
		dmo.mSetmdep(mdep);
	      }
	      else{
		uint64_t tmp = this->getXCHGmdep(mdep,dmo.getSequenceNumber());
		if(!is_out_of_range)deptrace_f << "m" << tmp;
		//deptrace_f << "m" << mdep;
	      }
	    }
	  for (auto adep : deptrace_addr_deps)
	    {
	      if(dmo.mGetMarker()){
		//deptrace_f << "a" << adep << " ";
		dmo.mSetadep(adep);
	      }
	      else{
		uint64_t tmp = this->getXCHGadep(adep,dmo.getSequenceNumber());
		if(!is_out_of_range)deptrace_f << "a" << tmp;
		//deptrace_f << "a" << adep;
	      }
	    }
	  
	  assert(deptrace_addr_deps.size() == 0);
	  // No newlines for instructions with dependencies
	}
      }	

      // Clear per-instruction data structures
      deptrace_is_branch = false;
      deptrace_is_load = false;
      deptrace_is_store = false;

      deptrace_reg_deps.clear();
      deptrace_mem_deps.clear();
      deptrace_addr_deps.clear();
    }

    Thread* thread = Sim()->getThreadManager()->getThreadOnCore(m_core->getId());
    thread_id_t thread_id = thread ? thread->getId() : 0xffffffff;

    // Special trace state
    if ((*it)->getMicroOp()->is_trace)
    {
      auto current_cmd = (*it)->getMicroOp()->trace_data[0];

      //deptrace_f << " SPECIAL " << current_cmd << " ";
      //std::cout << current_cmd <<" "<<thread_id<<" "<<deptraceRMSIsActive(thread_id)<<sync_instr_pending<<"\n";
      switch (current_cmd)
      {

	//Init_DONE
      case 0:
	if (!deptrace_roi)
	{
	  deptraceRMSSetActive(thread_id, true);
	  //std::cout << current_cmd <<" "<<thread_id<<" "<<deptraceRMSIsActive(thread_id)<<"\n";
	  //assert(false);
	}
	break;

	//Start_Trans
      case 1:
	if (deptraceRMSIsActive(thread_id))
	{
	  if (deptrace_last_was_newline)
	    deptrace_last_was_newline = false;
	  else
	    deptrace_f << "\n";
          
	  deptrace_f << "CLEAR\n";
	  deptrace_last_was_newline = true;

	  {
	    ScopedLock sl(m_print_lock);
	    std::cout << "[DEPTRACE:"<<m_core->getId()<<":"<<thread_id<<"] RMS: Clear stats command seen at "<<m_insns_total<<" instructions / "<<m_uops_total<<" micro-ops\n";
	  }
	}
	break;

	//End_Trans
      case 2:
	if (!deptrace_roi)
	{
	  assert(deptraceRMSIsActive(thread_id));
          if (deptrace_last_was_newline)
	    deptrace_last_was_newline = false;
          else
	    deptrace_f << "\n";
        
          deptrace_f << "END " << std::hex << deptrace_last_pc << std::dec << "\n" << std::flush;
          deptrace_last_was_newline = true;
	  deptrace_seen_end_tran = true;

	  deptraceRMSSetActive(thread_id, false);
	}
	break;

	// Initial Acq
      case 3:
	if (deptraceRMSIsActive(thread_id))
	{
	  // Always handle thread state data
	  deptrace_saved_data.str("");
	  deptrace_saved_data << "ACQ " << std::hex << (*it)->getMicroOp()->trace_data[1] << " " << (*it)->getMicroOp()->trace_data[2]<< " " << thread_id << std::dec;
	  sync_instr_pending = true;
	  deptraceSetActive(thread_id, false);
	}
	break;

	// Final Acq
      case 4:
	assert(deptrace_last_command == 3);
	deptraceSetActive(thread_id, true);
	   
	// We need to test this again because we might not be in the RMS/ROI region
	if (sync_instr_pending)
	{
	  if (deptrace_last_was_newline)
	    deptrace_last_was_newline = false;
	  else
	    deptrace_f << " ";
	     
	  deptrace_f << deptrace_saved_data.str() << "\n";
	  deptrace_last_was_newline = true;
	  sync_instr_pending = false;
	}
	   
	break;
	// Initial Rel
      case 5:
	if (deptraceRMSIsActive(thread_id))
	{
	  if (deptrace_last_was_newline)
	    deptrace_last_was_newline = false;
	  else
	    deptrace_f << " ";
	     
	  deptrace_f << "REL " << std::hex << (*it)->getMicroOp()->trace_data[1] << " " << (*it)->getMicroOp()->trace_data[2] << " " << thread_id << std::dec << "\n";
	  deptrace_last_was_newline = true;
	}
	   
	deptraceSetActive(thread_id, false);
	break;
	// Final Rel
      case 6:
	assert(deptrace_last_command == 5);
	assert(sync_instr_pending == false);
	deptraceSetActive(thread_id, true);
	break;
	// Initial Barrier
      case 7:
	if (deptraceRMSIsActive(thread_id))
	{
	  deptrace_saved_data.str("");
	  deptrace_saved_data << "BAR " << std::hex << (*it)->getMicroOp()->trace_data[1] << " " << (*it)->getMicroOp()->trace_data[2] << " " << (*it)->getMicroOp()->trace_data[3] << " " << thread_id << std::dec;
	  sync_instr_pending = true;
	  deptraceSetActive(thread_id, false);
	}
	break;
	// Final Barrier
      case 8:
	assert(deptrace_last_command == 7);
	if (sync_instr_pending)
	{
	  if (deptrace_last_was_newline)
	    deptrace_last_was_newline = false;
	  else
	    deptrace_f << " ";
	     
	  deptrace_f << deptrace_saved_data.str() << "\n";
	  deptrace_last_was_newline = true;
	  sync_instr_pending = false;
	}
	deptraceSetActive(thread_id, true);
	break;
	// A-AcqRel
      case 9:
	assert(false);
	if (deptraceIsActive(thread_id))
	{
	  if (deptrace_last_was_newline)
	    deptrace_last_was_newline = false;
	  else
	    deptrace_f << " ";
               
	  deptrace_f << "AT_AR " << std::hex << (*it)->getMicroOp()->trace_data[1] << " " << (*it)->getMicroOp()->trace_data[2] << " " << (*it)->getMicroOp()->trace_data[3] << " " << thread_id << "\n" << std::dec;
	  deptrace_last_was_newline = true;
	}

	deptraceSetActive(thread_id, false);
	break;
	// A-Acq
      case 10:
	assert(false);
	if (deptraceIsActive(thread_id))
	{
	  if (deptrace_last_was_newline)
	    deptrace_last_was_newline = false;
	  else
	    deptrace_f << " ";
               
	  deptrace_f << "AT_AC " << std::hex << (*it)->getMicroOp()->trace_data[1] << " " << (*it)->getMicroOp()->trace_data[2] << " " << (*it)->getMicroOp()->trace_data[3] << " " << thread_id << "\n" << std::dec;
	  deptrace_last_was_newline = true;
	}

	deptraceSetActive(thread_id, false);
	break;
	// A-Rel
      case 11:
	assert(false);
	if (deptraceIsActive(thread_id))
	{
	  if (deptrace_last_was_newline)
	    deptrace_last_was_newline = false;
	  else
	    deptrace_f << " ";
               
	  deptrace_f << "AT_RE " << std::hex << (*it)->getMicroOp()->trace_data[1] << " " << (*it)->getMicroOp()->trace_data[2] << " " << (*it)->getMicroOp()->trace_data[3] << " " << thread_id << "\n" << std::dec;
	  deptrace_last_was_newline = true;
	}

	deptraceSetActive(thread_id, false);
	break;
	// Final A
      case 12:
	assert(false);
	deptraceSetActive(thread_id, true);
	break;
	// Cond Sig
      case 13:
	if (deptraceRMSIsActive(thread_id))
	{
	  // Always handle thread state data
	  deptrace_saved_data.str("");
	  deptrace_saved_data << "CV_SIGNAL " << std::hex << (*it)->getMicroOp()->trace_data[1] << " " << thread_id << std::dec;
	  sync_instr_pending = true;
	  deptraceSetActive(thread_id, false);
	}
	break;
	// Final Cond Sig
      case 14:
	assert(sync_instr_pending == false);
	deptraceSetActive(thread_id, true);
	break;
	// Cond BCast
      case 15:
	if (deptraceRMSIsActive(thread_id))
	{
	  // Always handle thread state data
	  deptrace_saved_data.str("");
	  deptrace_saved_data << "CV_BCAST " << std::hex << (*it)->getMicroOp()->trace_data[1] << " " << thread_id << std::dec;
	  sync_instr_pending = true;
	  deptraceSetActive(thread_id, false);
	}
	break;
	// Final Cond BCast
      case 16:
	assert(deptrace_last_command == 15);
	assert(sync_instr_pending == false);
	deptraceSetActive(thread_id, true);
	break;
	// Initial Cond Wait
      case 17:
	if (deptraceRMSIsActive(thread_id))
	{
	  // Always handle thread state data
	  deptrace_saved_data.str("");
	  deptrace_saved_data << "CV_WAIT " << std::hex << (*it)->getMicroOp()->trace_data[1] << " " << (*it)->getMicroOp()->trace_data[2] << " " << thread_id << std::dec;
	  sync_instr_pending = true;
	  deptraceSetActive(thread_id, false);
	}
	break;
	// Final Cond Wait
      case 18:
	assert(sync_instr_pending == false);
	deptraceSetActive(thread_id, true);
	break;
	// BEGIN_XDRF
      case 19:
	if (deptraceRMSIsActive(thread_id))
	  {
	  if (deptrace_last_was_newline)
	    deptrace_last_was_newline = false;
	  else
	    deptrace_f << "\n";
          
	  deptrace_f << "BEGIN_XDRF " << (*it)->getMicroOp()->trace_data[1] << "\n";
	  deptrace_last_was_newline = true;
	}
	break;
	// END_XDRF
      case 20:
	if (deptraceRMSIsActive(thread_id))
	{
	  if (deptrace_last_was_newline)
	    deptrace_last_was_newline = false;
	  else
	    deptrace_f << "\n";
          
	  deptrace_f << "END_XDRF " << (*it)->getMicroOp()->trace_data[1] << "\n";
	  deptrace_last_was_newline = true;
	}
	break;

        // BEGIN_NDRF_BARRIER
      case 21:
	assert(false); // Not tested
	break;
	// BEGIN_NDRF
      case 22:
	if (deptraceRMSIsActive(thread_id))
	{
	  if (deptrace_last_was_newline)
	    deptrace_last_was_newline = false;
	  else
	    deptrace_f << "\n";
          
	  deptrace_f << "BEGIN_NDRF " << (*it)->getMicroOp()->trace_data[1] << "\n";
	  deptrace_last_was_newline = true;
	}
	break;
	// END_NDRF
      case 23:
	if (deptraceRMSIsActive(thread_id))
	{
	  if (deptrace_last_was_newline)
	    deptrace_last_was_newline = false;
	  else
	    deptrace_f << "\n";
          
	  deptrace_f << "END_NDRF " << (*it)->getMicroOp()->trace_data[1] << "\n";
	  deptrace_last_was_newline = true;
	}
	break;
	// abstracted function calls 
      case 24:
	if (sync_instr_pending)
	{
	  if (deptrace_last_was_newline)
	    deptrace_last_was_newline = false;
	  else
	    deptrace_f << " ";
	     
	  deptrace_f << deptrace_saved_data.str() << "\n";
	  deptrace_last_was_newline = true;
	  sync_instr_pending = false;
	}
	break;
	    
	// init sem signal but not tested will be commented in the main routinereplace.cc file
      case 27:
	if (deptraceRMSIsActive(thread_id))
	{
	  // Always handle thread state data
	  deptrace_saved_data.str("");
	  deptrace_saved_data << "SIGNAL " << std::hex << (*it)->getMicroOp()->trace_data[1] << " " << thread_id << std::dec;
	  sync_instr_pending = true;
	  deptraceSetActive(thread_id, false);
	}
	break;
	// Final sem signal but not tested 
      case 28:
	assert(sync_instr_pending == false);
	deptraceSetActive(thread_id, true);
	sync_instr_pending = false ;
	break;
	//sem wait init not tested
      case 29:
	if (deptraceRMSIsActive(thread_id))
	{
	  // Always handle thread state data
	  deptrace_saved_data.str("");
	  deptrace_saved_data << "WAIT " << std::hex << (*it)->getMicroOp()->trace_data[1] << " " << thread_id << std::dec;
	  sync_instr_pending = true;
	  deptraceSetActive(thread_id, false);
	}
	break;
	// Final sem wait not tested 
      case 30:
	assert(sync_instr_pending == false);
	deptraceSetActive(thread_id, true);
	sync_instr_pending = false;
	break;
      }

      if (current_cmd < 19 || current_cmd > 24) 
	deptrace_last_command = current_cmd;
    }


    if (m_store_to_load_forwarding && entry->uop->getMicroOp()->isLoad())
    {
      for(unsigned int i = 0; i < entry->uop->getDependenciesLength(); ++i)
      {
	RobEntry *prodEntry = this->findEntryBySequenceNumber(entry->uop->getDependency(i));
	// If we depend on a store
	if (prodEntry->uop->getMicroOp()->isStore())
	{
	  // Remove dependency on the store (which won't execute until it reaches the front of the ROB)
	  entry->uop->removeDependency(entry->uop->getDependency(i));

	  // Add dependencies to the producers of the value being stored instead
	  // Remark: one of these may be producing the store address, but because the store has to be
	  //         disambiguated, it's correct to have the load depend on the address producers as well.
	  for(unsigned int j = 0; j < prodEntry->uop->getDependenciesLength(); ++j)
	    entry->uop->addDependency(prodEntry->uop->getDependency(j));

	  break;
	}
      }
    }

    // Add ourselves to the dependants list of the uops we depend on
    uint64_t minProducerDistance = UINT64_MAX;
    m_totalConsumers += 1 ;
    uint64_t deps_to_remove[8], num_dtr = 0;
    for(unsigned int i = 0; i < entry->uop->getDependenciesLength(); ++i)
    {
      RobEntry *prodEntry = this->findEntryBySequenceNumber(entry->uop->getDependency(i));
      minProducerDistance = std::min( minProducerDistance,  entry->uop->getSequenceNumber() - prodEntry->uop->getSequenceNumber() );
      if (prodEntry->done != SubsecondTime::MaxTime())
      {
	// If producer is already done (but hasn't reached writeback stage), remove it from our dependency list
	deps_to_remove[num_dtr++] = entry->uop->getDependency(i);
	entry->readyMax = std::max(entry->readyMax, prodEntry->done);
      }
      else
      {
	prodEntry->addDependant(entry);
      }
    }

#ifdef DEBUG_PERCYCLE
    // Make sure we are in the dependant list of all of our address producers
    for(unsigned int i = 0; i < entry->getNumAddressProducers(); ++i)
    {
      if (rob.size() && entry->getAddressProducer(i) >= rob[0].uop->getSequenceNumber())
      {
	RobEntry *prodEntry = this->findEntryBySequenceNumber(entry->getAddressProducer(i));
	bool found = false;
	for(unsigned int j = 0; j < prodEntry->getNumDependants(); ++j)
	  if (prodEntry->getDependant(j) == entry)
	  {
	    found = true;
	    break;
	  }
	LOG_ASSERT_ERROR(found == true, "Store %ld depends on %ld for address production, but is not in its dependants list",
			 entry->uop->getSequenceNumber(), prodEntry->uop->getSequenceNumber());
      }
    }
#endif

    if (minProducerDistance != UINT64_MAX)
    {
      m_totalProducerInsDistance += minProducerDistance;
      // KENZO: not sure why the distance can be larger than the windowSize, but it happens...
      if (minProducerDistance >= m_producerInsDistance.size())
	minProducerDistance = m_producerInsDistance.size()-1;
      m_producerInsDistance[ minProducerDistance ]++ ;
    }
    else
    {
      // Not depending on any instruction in the rob
      m_producerInsDistance[ 0 ] += 1 ;
    }

    // If there are any dependencies to be removed, do this after iterating over them (don't mess with the list we're reading)
    LOG_ASSERT_ERROR(num_dtr < sizeof(deps_to_remove)/sizeof(8), "Have to remove more dependencies than I expected");
    for(uint64_t i = 0; i < num_dtr; ++i)
      entry->uop->removeDependency(deps_to_remove[i]);
    if (entry->uop->getDependenciesLength() == 0)
    {
      // We have no dependencies in the ROB: mark ourselves as ready
      entry->ready = entry->readyMax;
    }

#ifdef DEBUG_PERCYCLE
    std::cout<<"** simulate: "<<entry->uop->getMicroOp()->toShortString(true)<<std::endl;
#endif

    m_uop_type_count[(*it)->getMicroOp()->getSubtype()]++;
    m_uops_total++;
    if ((*it)->getMicroOp()->isLast()) {
      m_insns_total++;
    }
    if ((*it)->getMicroOp()->isX87()) m_uops_x87++;
    if ((*it)->getMicroOp()->isPause()) m_uops_pause++;

    if (m_uops_total > 10000 && m_uops_x87 > m_uops_total / 20)
      LOG_PRINT_WARNING_ONCE("Significant fraction of x87 instructions encountered, accuracy will be low. Compile without -mno-sse2 -mno-sse3 to avoid.");
  }

  while (true)
  {
    uint64_t instructionsExecuted;
    SubsecondTime latency;
    execute(instructionsExecuted, latency);
    totalInsnExec += instructionsExecuted;
    totalLat += latency;
    if (latency == SubsecondTime::Zero())
      break;
  }

  return boost::tuple<uint64_t,SubsecondTime>(totalInsnExec, totalLat);
}
void RobTimer::synchronize(SubsecondTime time)
{
  // NOTE: depending on how far we jumped ahead (usually a considerable amount),
  //       we may want to flush the ROB and reset other queues
  //printf("RobTimer::synchronize(%lu) %+ld\n", time, (int64_t)time-now);
  now.setElapsedTime(time);
}

SubsecondTime* RobTimer::findCpiComponent()
{
  // Determine the CPI component corresponding to the first non-committed instruction
  for(uint64_t i = 0; i < m_num_in_rob; ++i)
  {
    RobEntry *entry = &rob.at(i);
    DynamicMicroOp *uop = entry->uop;
    // Skip over completed instructions
    if (entry->done < now)
      continue;
    // This is the first instruction in the ROB which is still executing
    // Assume everyone is blocked on this one
    // Assign 100% of this cycle to this guy's CPI component
    if (uop->getMicroOp()->isSerializing() || uop->getMicroOp()->isMemBarrier())
      return &m_cpiSerialization;
    else if (uop->getMicroOp()->isLoad() || uop->getMicroOp()->isStore())
      return &m_cpiDataCache[uop->getDCacheHitWhere()];
    else
      return NULL;
  }
  // No instruction is currently executing
  return NULL;
}

SubsecondTime RobTimer::doDispatch(SubsecondTime **cpiComponent)
{
  SubsecondTime next_event = SubsecondTime::MaxTime();
  SubsecondTime *cpiFrontEnd = NULL;

  if (frontend_stalled_until <= now)
  {
    uint32_t instrs_dispatched = 0, uops_dispatched = 0;

    while(m_num_in_rob < windowSize)
    {
      LOG_ASSERT_ERROR(m_num_in_rob < rob.size(), "Expected sufficient uops for dispatching in pre-ROB buffer, but didn't find them");
      RobEntry *entry = &rob.at(m_num_in_rob);
      DynamicMicroOp &uop = *entry->uop;

      // Dispatch up to 4 instructions
      if (uops_dispatched == dispatchWidth)
	break;

      // This is actually in the decode stage, there's a buffer between decode and dispatch
      // so we shouldn't do this here.
      //// First instruction can be any size, but second and subsequent ones may only be single-uop
      //// So, if this is not the first instruction, break if the first uop is not also the last
      //if (instrs_dispatched > 0 && !uop.isLast())
      //   break;

      bool iCacheMiss = (uop.getICacheHitWhere() != HitWhere::L1I);
      if (iCacheMiss)
      {
	if (in_icache_miss)
	{
	  // We just took the latency for this instruction, now dispatch it
#ifdef DEBUG_PERCYCLE
	  std::cout<<"-- icache return"<<std::endl;
#endif
	  in_icache_miss = false;
	}
	else
	{
#ifdef DEBUG_PERCYCLE
	  std::cout<<"-- icache miss("<<uop.getICacheLatency()<<")"<<std::endl;
#endif
	  frontend_stalled_until = now + uop.getICacheLatency();
	  in_icache_miss = true;
	  // Don't dispatch this instruction yet
	  cpiFrontEnd = &m_cpiInstructionCache[uop.getICacheHitWhere()];
	  break;
	}
      }

      if (m_rs_entries_used == rsEntries)
      {
	cpiFrontEnd = &m_cpiRSFull;
	break;
      }

      entry->dispatched = now;
      ++m_num_in_rob;
      ++m_rs_entries_used;

      uops_dispatched++;
      if (uop.isLast())
	instrs_dispatched++;

      // If uop is already ready, we may need to issue it in the following cycle
      entry->ready = std::max(entry->ready, (now + 1ul).getElapsedTime());
      next_event = std::min(next_event, entry->ready);

#ifdef DEBUG_PERCYCLE
      std::cout<<"DISPATCH "<<entry->uop->getMicroOp()->toShortString()<<std::endl;
#endif

#ifdef ASSERT_SKIP
      LOG_ASSERT_ERROR(will_skip == false, "Cycle would have been skipped but stuff happened");
#endif

      // Mispredicted branch
      if (uop.getMicroOp()->isBranch() && uop.isBranchMispredicted())
      {
	frontend_stalled_until = SubsecondTime::MaxTime();
#ifdef DEBUG_PERCYCLE
	std::cout<<"-- branch mispredict"<<std::endl;
#endif
	cpiFrontEnd = &m_cpiBranchPredictor;
	break;
      }
    }

    m_cpiCurrentFrontEndStall = cpiFrontEnd;
  }
  else
  {
    // Front-end is still stalled: re-use last CPI component
    cpiFrontEnd = m_cpiCurrentFrontEndStall;
  }


  // Find CPI component corresponding to the first executing instruction
  SubsecondTime *cpiRobHead = findCpiComponent();

  if (cpiFrontEnd)
  {
    // Front-end is stalled
    if (cpiRobHead)
    {
      // Have memory/serialization components take precendence over front-end stalls
      *cpiComponent = cpiRobHead;
    }
    else
    {
      *cpiComponent = cpiFrontEnd;
    }
  }
  else if (m_num_in_rob == windowSize)
  {
    *cpiComponent = cpiRobHead ? cpiRobHead : &m_cpiBase;
  }
  else
  {
    *cpiComponent = &m_cpiBase;
  }


  if (m_num_in_rob == windowSize)
    return next_event; // front-end is effectively stalled so wait for another event
  else
    return std::min(frontend_stalled_until, next_event);
}

void RobTimer::issueInstruction(uint64_t idx, SubsecondTime &next_event)
{
  RobEntry *entry = &rob[idx];
  DynamicMicroOp &uop = *entry->uop;

  if ((uop.getMicroOp()->isLoad() || uop.getMicroOp()->isStore())
      && uop.getDCacheHitWhere() == HitWhere::UNKNOWN)
  {
    MemoryResult res = m_core->accessMemory(
      Core::NONE,
      uop.getMicroOp()->isLoad() ? Core::READ : Core::WRITE,
      uop.getAddress().address,
      NULL,
      uop.getMicroOp()->getMemoryAccessSize(),
      Core::MEM_MODELED_RETURN,
      uop.getMicroOp()->getInstruction() ? uop.getMicroOp()->getInstruction()->getAddress() : static_cast<uint64_t>(NULL),
      now.getElapsedTime()
      );
    uint64_t latency = SubsecondTime::divideRounded(res.latency, now.getPeriod());

    uop.setExecLatency(uop.getExecLatency() + latency); // execlatency already contains bypass latency
    uop.setDCacheHitWhere(res.hit_where);
  }

  if (uop.getMicroOp()->isLoad())
  {
    load_queue.getCompletionTime(now, uop.getExecLatency() * now.getPeriod(), uop.getAddress().address);
  }
  else if (uop.getMicroOp()->isStore())
  {
    store_queue.getCompletionTime(now, uop.getExecLatency() * now.getPeriod(), uop.getAddress().address);
  }

  ComponentTime cycle_depend = now + uop.getExecLatency();        // When result is available for dependent instructions
  SubsecondTime cycle_done = cycle_depend + 1ul;                  // When the instruction can be committed

  if (uop.getMicroOp()->isLoad())
  {
    m_loads_count++;
    m_loads_latency += uop.getExecLatency() * now.getPeriod();
  }
  else if (uop.getMicroOp()->isStore())
  {
    m_stores_count++;
    m_stores_latency += uop.getExecLatency() * now.getPeriod();
  }

  if (uop.getMicroOp()->isStore())
  {
    last_store_done = std::max(last_store_done, cycle_done);
    cycle_depend = now + 1ul;                          // For stores, forward the result immediately
    // Stores can be removed from the ROB once they're issued to the memory hierarchy
    // Dependent operations such as SFENCE and synchronization instructions need to wait until last_store_done
    cycle_done = now + 1ul;

    LOG_ASSERT_ERROR(entry->addressReady <= entry->ready, "%ld: Store address cannot be ready (%ld) later than the whole uop is (%ld)",
		     entry->uop->getSequenceNumber(), entry->addressReady.getPS(), entry->ready.getPS());
  }

  if (m_rob_contention)
    m_rob_contention->doIssue(uop);

  entry->issued = now;
  entry->done = cycle_done;
  next_event = std::min(next_event, entry->done);

  --m_rs_entries_used;

#ifdef DEBUG_PERCYCLE
  std::cout<<"ISSUE    "<<entry->uop->getMicroOp()->toShortString()<<"   latency="<<uop.getExecLatency()<<std::endl;
#endif

  for(size_t idx = 0; idx < entry->getNumDependants(); ++idx)
  {
    RobEntry *depEntry = entry->getDependant(idx);
    LOG_ASSERT_ERROR(depEntry->uop->getDependenciesLength()> 0, "??");

    // Remove uop from dependency list and update readyMax
    depEntry->readyMax = std::max(depEntry->readyMax, cycle_depend.getElapsedTime());
    depEntry->uop->removeDependency(uop.getSequenceNumber());

    // If all dependencies are resolved, mark the uop ready
    if (depEntry->uop->getDependenciesLength() == 0)
    {
      depEntry->ready = depEntry->readyMax;
      //std::cout<<"    ready @ "<<depEntry->ready<<std::endl;
    }

    // For stores, check if their address has been produced
    if (depEntry->uop->getMicroOp()->isStore() && depEntry->addressReady == SubsecondTime::MaxTime())
    {
      bool ready = true;
      for(unsigned int i = 0; i < depEntry->getNumAddressProducers(); ++i)
      {
	uint64_t addressProducer = depEntry->getAddressProducer(i);
	RobEntry *prodEntry = addressProducer >= this->rob.front().uop->getSequenceNumber()
	  ? this->findEntryBySequenceNumber(addressProducer) : NULL;

	if (prodEntry == entry)
	{
	  // The instruction we just executed is producing an address. Update the store's addressReadyMax
	  depEntry->addressReadyMax = std::max(depEntry->addressReadyMax, cycle_depend.getElapsedTime());
	}

	if (prodEntry && prodEntry->done == SubsecondTime::MaxTime())
	{
	  // An address producer has not yet been issued: address remains not ready
	  ready = false;
	}
      }

      if (ready)
      {
	// We did not find any address producing instructions that have not yet been issued.
	// Store address will be ready at addressReadyMax
	depEntry->addressReady = depEntry->addressReadyMax;
      }
    }
  }

  // After issuing a mispredicted branch: allow the ROB to refill after flushing the pipeline
  if (uop.getMicroOp()->isBranch() && uop.isBranchMispredicted())
  {
    frontend_stalled_until = now + (misprediction_penalty - 2); // The frontend needs to start 2 cycles earlier to get a total penalty of <misprediction_penalty>
#ifdef DEBUG_PERCYCLE
    std::cout<<"-- branch resolve"<<std::endl;
#endif
  }
}

SubsecondTime RobTimer::doIssue()
{
  uint64_t num_issued = 0;
  SubsecondTime next_event = SubsecondTime::MaxTime();
  bool head_of_queue = true, no_more_load = false, no_more_store = false, have_unresolved_store = false;

  if (m_rob_contention)
    m_rob_contention->initCycle(now);

  for(uint64_t i = 0; i < m_num_in_rob; ++i)
  {
    RobEntry *entry = &rob.at(i);
    DynamicMicroOp *uop = entry->uop;


    if (entry->done != SubsecondTime::MaxTime())
    {
      next_event = std::min(next_event, entry->done);
      continue;                     // already done
    }

    next_event = std::min(next_event, entry->ready);


    // See if we can issue this instruction

    bool canIssue = false;

    if (entry->ready > now)
      canIssue = false;          // blocked by dependency

    else if ((no_more_load && uop->getMicroOp()->isLoad()) || (no_more_store && uop->getMicroOp()->isStore()))
      canIssue = false;          // blocked by mfence

    else if (uop->getMicroOp()->isSerializing())
    {
      if (head_of_queue && last_store_done <= now)
	canIssue = true;
      else
	break;
    }

    else if (uop->getMicroOp()->isMemBarrier())
    {
      if (head_of_queue && last_store_done <= now)
	canIssue = true;
      else
	// Don't issue any memory operations following a memory barrier
	no_more_load = no_more_store = true;
      // FIXME: L/SFENCE
    }

    else if (!m_rob_contention && num_issued == dispatchWidth)
      canIssue = false;          // no issue contention: issue width == dispatch width

    else if (uop->getMicroOp()->isLoad() && !load_queue.hasFreeSlot(now))
      canIssue = false;          // load queue full

    else if (uop->getMicroOp()->isLoad() && m_no_address_disambiguation && have_unresolved_store)
      canIssue = false;          // preceding store with unknown address

    else if (uop->getMicroOp()->isStore() && (!head_of_queue || !store_queue.hasFreeSlot(now)))
      canIssue = false;          // store queue full

    else
      canIssue = true;           // issue!


    // canIssue already marks issue ports as in use, so do this one last
    if (canIssue && m_rob_contention && ! m_rob_contention->tryIssue(*uop))
      canIssue = false;          // blocked by structural hazard


    if (canIssue)
    {
      num_issued++;
      issueInstruction(i, next_event);

      // Calculate memory-level parallelism (MLP) for long-latency loads (but ignore overlapped misses)
      if (uop->getMicroOp()->isLoad() && uop->isLongLatencyLoad() && uop->getDCacheHitWhere() != HitWhere::L1_OWN)
      {
	if (m_lastAccountedMemoryCycle < now) m_lastAccountedMemoryCycle = now;

	SubsecondTime done = std::max( now.getElapsedTime(), entry->done );
	// Ins will be outstanding for until it is done. By account beforehand I don't need to
	// worry about fast-forwarding simulations
	m_outstandingLongLatencyInsns += (done - now);

	// Only account for the cycles that have not yet been accounted for by other long
	// latency misses (don't account cycles twice).
	if ( done > m_lastAccountedMemoryCycle )
	{
	  m_outstandingLongLatencyCycles += done - m_lastAccountedMemoryCycle;
	  m_lastAccountedMemoryCycle = done;
	}

#ifdef ASSERT_SKIP
	LOG_ASSERT_ERROR( m_outstandingLongLatencyInsns >= m_outstandingLongLatencyCycles, "MLP calculation is wrong: MLP cannot be < 1!"  );
#endif
      }


#ifdef ASSERT_SKIP
      LOG_ASSERT_ERROR(will_skip == false, "Cycle would have been skipped but stuff happened");
#endif
    }
    else
    {
      head_of_queue = false;     // Subsequent instructions are not at the head of the ROB

      if (uop->getMicroOp()->isStore() && entry->addressReady > now)
	have_unresolved_store = true;

      if (inorder)
	// In-order: only issue from head of the ROB
	break;
    }


    if (m_rob_contention)
    {
      if (m_rob_contention->noMore())
	break;
    }
    else
    {
      if (num_issued == dispatchWidth)
	break;
    }
  }

  return next_event;
}

SubsecondTime RobTimer::doCommit(uint64_t& instructionsExecuted)
{
  uint64_t num_committed = 0;

  while(rob.size() && (rob.front().done <= now))
  {
    RobEntry *entry = &rob.front();

#ifdef DEBUG_PERCYCLE
    std::cout<<"COMMIT   "<<entry->uop->getMicroOp()->toShortString()<<std::endl;
#endif

    // Send instructions to loop tracer, in-order, once we know their issue time
    InstructionTracer::uop_times_t times = {
      entry->dispatched,
      entry->issued,
      entry->done,
      now
    };
    m_core->getPerformanceModel()->traceInstruction(entry->uop, &times);

    if (entry->uop->isLast())
      instructionsExecuted++;

    entry->free();
    rob.pop();
    m_num_in_rob--;

#ifdef ASSERT_SKIP
    LOG_ASSERT_ERROR(will_skip == false, "Cycle would have been skipped but stuff happened");
#endif

    ++num_committed;
    if (num_committed == commitWidth)
      break;
  }

  if (rob.size())
    return rob.front().done;
  else
    return SubsecondTime::MaxTime();
}

void RobTimer::execute(uint64_t& instructionsExecuted, SubsecondTime& latency)
{
  latency = SubsecondTime::Zero();
  instructionsExecuted = 0;
  SubsecondTime *cpiComponent = NULL;

#ifdef DEBUG_PERCYCLE
  std::cout<<std::endl;
  std::cout<<"Running cycle "<<now<<std::endl;
#endif


  // If frontend not stalled
  if (frontend_stalled_until <= now)
  {
    if (rob.size() < m_num_in_rob + 2*dispatchWidth)
    {
      // We don't have enough instructions to dispatch <dispatchWidth> new ones. Ask for more before doing anything this cycle.
      return;
    }
  }


  // Model dispatch, issue and commit stages
  // Decode stage is not modeled, assumes the decoders can keep up with (up to) dispatchWidth uops per cycle

  SubsecondTime next_dispatch = doDispatch(&cpiComponent);
  SubsecondTime next_issue    = doIssue();
  SubsecondTime next_commit   = doCommit(instructionsExecuted);


#ifdef DEBUG_PERCYCLE
#ifdef ASSERT_SKIP
  if (! will_skip)
  {
#endif
    printRob();
#ifdef ASSERT_SKIP
  }
#endif
#endif


#ifdef DEBUG_PERCYCLE
  std::cout<<"Next event: D("<<next_dispatch<<") I("<<next_issue<<") C("<<next_commit<<")"<<std::endl;
#endif
  SubsecondTime next_event = std::min(next_dispatch, std::min(next_issue, next_commit));
  SubsecondTime skip;
  if (next_event != SubsecondTime::MaxTime() && next_event > now + 1ul)
  {
#ifdef DEBUG_PERCYCLE
    std::cout<<"++ Skip "<<(next_event - now)<<std::endl;
#endif
    will_skip = true;
    skip = next_event - now;
  }
  else
  {
    will_skip = false;
    skip = now.getPeriod();
  }

#ifdef ASSERT_SKIP
  now += now.getPeriod();
  latency += now.getPeriod();
  if (will_skip)
    time_skipped += now.getPeriod();
#else
  now += skip;
  latency += skip;
  if (skip > now.getPeriod())
    time_skipped += skip - now.getPeriod();
#endif

  if (m_mlp_histogram)
    countOutstandingMemop(skip);

  LOG_ASSERT_ERROR(cpiComponent != NULL, "We expected cpiComponent to be set by doDispatch, but it wasn't");
  *cpiComponent += latency;
}

void RobTimer::countOutstandingMemop(SubsecondTime time)
{
  UInt64 counts[HitWhere::NUM_HITWHERES] = {0}, total = 0;

  for(unsigned int i = 0; i < m_num_in_rob; ++i)
  {
    RobEntry *e = &rob.at(i);
    if (e->done != SubsecondTime::MaxTime() && e->done > now && e->uop->getMicroOp()->isLoad())
    {
      ++counts[e->uop->getDCacheHitWhere()];
      ++total;
    }
  }

  for(unsigned int h = 0; h < HitWhere::NUM_HITWHERES; ++h)
    if (counts[h] > 0)
      m_outstandingLoads[h][counts[h] >= MAX_OUTSTANDING ? MAX_OUTSTANDING-1 : counts[h]] += time;
  if (total > 0)
    m_outstandingLoadsAll[total >= MAX_OUTSTANDING ? MAX_OUTSTANDING-1 : total] += time;
}

void RobTimer::printRob()
{
  std::cout<<"** ROB state @ "<<now<<"  size("<<m_num_in_rob<<") total("<<rob.size()<<")"<<std::endl;
  if (frontend_stalled_until > now)
  {
    std::cout<<"   Front-end stalled";
    if (frontend_stalled_until != SubsecondTime::MaxTime())
      std::cout << " until " << frontend_stalled_until;
    if (in_icache_miss)
      std::cout << ", in I-cache miss";
    std::cout<<std::endl;
  }
  std::cout<<"   RS entries: "<<m_rs_entries_used<<std::endl;
  std::cout<<"   Outstanding loads: "<<load_queue.getNumUsed(now)<<"  stores: "<<store_queue.getNumUsed(now)<<std::endl;
  for(unsigned int i = 0; i < rob.size(); ++i)
  {
    std::cout<<"   ["<<std::setw(3)<<i<<"]  ";
    RobEntry *e = &rob.at(i);

    std::ostringstream state;
    if (i >= m_num_in_rob) state<<"PREROB ";
    else if (e->done != SubsecondTime::MaxTime()) state<<"DONE@+"<<(e->done-now)<<"  ";
    else if (e->ready != SubsecondTime::MaxTime()) state<<"READY@+"<<(e->ready-now)<<"  ";
    else
    {
      state<<"DEPS ";
      for(uint32_t j = 0; j < e->uop->getDependenciesLength(); j++)
	state << std::dec << e->uop->getDependency(j) << " ";
    }
    std::cout<<std::left<<std::setw(20)<<state.str()<<"   ";
    std::cout<<std::right<<std::setw(10)<<e->uop->getSequenceNumber()<<"  ";
    if (e->uop->getMicroOp()->isLoad())
      std::cout<<"LOAD      ";
    else if (e->uop->getMicroOp()->isStore())
      std::cout<<"STORE     ";
    else
      std::cout<<"EXEC ("<<std::right<<std::setw(2)<<e->uop->getExecLatency()<<") ";
    if (e->uop->getMicroOp()->getInstruction())
    {
      std::cout<<std::hex<<e->uop->getMicroOp()->getInstruction()->getAddress()<<std::dec<<": "
	       <<e->uop->getMicroOp()->getInstruction()->getDisassembly();
      if (e->uop->getMicroOp()->isLoad() || e->uop->getMicroOp()->isStore())
	std::cout<<"  {0x"<<std::hex<<e->uop->getAddress().address<<std::dec<<"}";
    }
    else
      std::cout<<"(dynamic)";
    std::cout<<std::endl;
  }
}
