/*
 * This file is covered under the Interval Academic License, see LICENCE.interval
 */

#ifndef ROBTIMER_HPP_
#define ROBTIMER_HPP_

#include "interval_timer.h"
#include "rob_contention.h"
#include "stats.h"
#include "hooks_manager.h"
#include "lock.h"

#include <deque>
#include <fstream>
#include <memory>
#include "zstr.hpp"
#include <unordered_set>
#include <string>
#include <iostream>
#include <sstream> 

class RobTimer
{
private:
   class RobEntry
   {
      private:
         static const size_t MAX_INLINE_DEPENDANTS = 8;
         size_t numInlineDependants;
         RobEntry* inlineDependants[MAX_INLINE_DEPENDANTS];
         std::vector<RobEntry*> *vectorDependants;
         std::vector<uint64_t> addressProducers;

      public:
         void init(DynamicMicroOp *uop, UInt64 sequenceNumber, UInt64 instructionNumber);
         void free();

         void addDependant(RobEntry* dep);
         uint64_t getNumDependants() const;
         RobEntry* getDependant(size_t idx) const;

         void addAddressProducer(UInt64 sequenceNumber) { addressProducers.push_back(sequenceNumber); }
         UInt64 getNumAddressProducers() const { return addressProducers.size(); }
         UInt64 getAddressProducer(size_t idx) const { return addressProducers.at(idx); }

         DynamicMicroOp *uop;
         SubsecondTime dispatched;
         SubsecondTime ready;    // Once all dependencies are resolved, cycle number that this uop becomes ready for issue
         SubsecondTime readyMax; // While some but not all dependencies are resolved, keep the time of the latest known resolving dependency
         SubsecondTime addressReady;
         SubsecondTime addressReadyMax;
         SubsecondTime issued;
         SubsecondTime done;
   };

   const uint64_t dispatchWidth;
   const uint64_t commitWidth;
   const uint64_t windowSize;
   const uint64_t rsEntries;
   const uint64_t misprediction_penalty;
   const bool m_store_to_load_forwarding;
   const bool m_no_address_disambiguation;
   const bool inorder;
   const bool deptrace;
   uint64_t deptrace_wait_for = 0;
   std::unordered_map<thread_id_t,bool> deptrace_active;
   std::unordered_map<thread_id_t,bool> deptrace_rms_active;
   bool deptrace_roi;
   bool deptrace_microops;
   bool deptrace_roi_seen = false;
   std::unique_ptr<std::ostream> _deptrace_f;
   std::unique_ptr<std::ostream> _deptrace_insn_f;
   uint64_t deptrace_last_insn = 0;
   uint64_t deptrace_insn_count = 0;
   uint64_t deptrace_last_insns = 0;
   bool deptrace_is_load = false;
   uint64_t deptrace_load_addr = 0x0;
   uint64_t deptrace_load_size = 0x0;
   bool deptrace_is_store = false;
   uint64_t deptrace_store_addr = 0x0;
   uint64_t deptrace_store_size = 0x0;
   bool deptrace_is_branch = false;
   bool deptrace_last_was_newline = true;
   std::stringstream deptrace_saved_data;
   bool sync_instr_pending = false;
   std::set<uint64_t> deptrace_reg_deps;
   std::set<uint64_t> deptrace_mem_deps;
   std::set<uint64_t> deptrace_addr_deps;
   std::unordered_map<uint64_t,uint64_t> deptrace_thread_released; // threadid -> mutex released
   bool deptrace_seen_end_tran = false;
   uint64_t deptrace_last_command = 0;
   uint64_t deptrace_last_pc = 0;
   bool deptrace_first_line = true;
   std::unordered_set<uint64_t> deptrace_acquire_list;
   RobEntry *entry = NULL;
   long long instr_to_insert_clear_stats = 0;
   void deptrace_roi_begin();
   void deptrace_roi_end();
   void deptrace_thread_create(HooksManager::ThreadCreate *args);
   uint64_t getXCHGrdep(uint64_t rdep, uint64_t num_seq);
   uint64_t getXCHGmdep(uint64_t mdep, uint64_t num_seq);
   uint64_t getXCHGadep(uint64_t adep, uint64_t num_seq);

   uint64_t loop_id = 0;
   bool look_for_loop_id_begin = false;
   bool look_for_loop_id_end = false;
   bool look_for_value = false;
   int DepValue[64];
   void resetDepValue();
   int FinalMarkerValue();
   int marker_index = 0;
   int final_DepValue_must = 0;
   int final_DepValue_may = 0;
   bool last_was_may = true;
   std::stringstream ss;
   std::stringstream last_load;
   bool last_load_pending = false;
   std::stringstream load_leftover;
   bool is_not_known_must = false;
   bool is_not_known_may = false;
   bool next_load_marker = false;
   int marker_executed = 0;
   int total_marker_executed = 0;
   uint64_t marker_dep_size = 0;
   uint64_t marker_begin_size = 0;
   uint64_t marker_size = 0;
   bool last_was_marker = 0;
   uint64_t real_rdep = 0;
   uint64_t real_mdep = 0;
   uint64_t xchg_rdep = 0;
   uint64_t xchg_mdep = 0;
   uint64_t xchg_adep = 0;
   bool is_out_of_range = false;

   uint64_t xchg_begin_rdep = 0;
   uint64_t xchg_end_rdep = 0;
   uint64_t xchg_dep_rdep[64];
   uint64_t xchg_dep_executed = 0;
   uint64_t newpcdiff = 0;

   
   static SInt64 __deptrace_roi_begin(UInt64 user, UInt64 arg) {reinterpret_cast<RobTimer*>(user)->deptrace_roi_begin(); return 0;}
   static SInt64 __deptrace_roi_end(UInt64 user, UInt64 arg) {reinterpret_cast<RobTimer*>(user)->deptrace_roi_end(); return 0;}

   static SInt64 __deptrace_thread_create(UInt64 user, UInt64 arg) {reinterpret_cast<RobTimer*>(user)->deptrace_thread_create(reinterpret_cast<HooksManager::ThreadCreate*>(arg)); return 0;}

   Core *m_core;

   typedef CircularQueue<RobEntry> Rob;
   Rob rob;
   uint64_t m_num_in_rob;
   uint64_t m_rs_entries_used;
   RobContention *m_rob_contention;

   ComponentTime now;
   SubsecondTime frontend_stalled_until;
   bool in_icache_miss;
   SubsecondTime last_store_done;
   ContentionModel load_queue;
   ContentionModel store_queue;

   uint64_t nextSequenceNumber;
   uint64_t nextInstructionNumber;
   bool will_skip;
   SubsecondTime time_skipped;

   RegisterDependencies* const registerDependencies;
   MemoryDependencies* const memoryDependencies;

   int addressMask;

   UInt64 m_uop_type_count[MicroOp::UOP_SUBTYPE_SIZE];
   UInt64 m_insns_total;
   UInt64 m_uops_total;
   UInt64 m_uops_x87;
   UInt64 m_uops_pause;

   uint64_t m_numICacheOverlapped;
   uint64_t m_numBPredOverlapped;
   uint64_t m_numDCacheOverlapped;

   uint64_t m_numLongLatencyLoads;
   uint64_t m_numTotalLongLatencyLoadLatency;

   uint64_t m_numSerializationInsns;
   uint64_t m_totalSerializationLatency;

   uint64_t m_totalHiddenDCacheLatency;
   uint64_t m_totalHiddenLongerDCacheLatency;
   uint64_t m_numHiddenLongerDCacheLatency;

   SubsecondTime m_outstandingLongLatencyInsns;
   SubsecondTime m_outstandingLongLatencyCycles;
   SubsecondTime m_lastAccountedMemoryCycle;

   uint64_t m_loads_count;
   SubsecondTime m_loads_latency;
   uint64_t m_stores_count;
   SubsecondTime m_stores_latency;

   uint64_t m_totalProducerInsDistance;
   uint64_t m_totalConsumers;
   std::vector<uint64_t> m_producerInsDistance;

   PerformanceModel *perf;

#if DEBUG_IT_INSN_PRINT
   FILE *m_insn_log;
#endif

   uint64_t m_numMfenceInsns;
   uint64_t m_totalMfenceLatency;

   // CPI stacks
   SubsecondTime m_cpiBase;
   SubsecondTime m_cpiBranchPredictor;
   SubsecondTime m_cpiSerialization;
   SubsecondTime m_cpiRSFull;

   std::vector<SubsecondTime> m_cpiInstructionCache;
   std::vector<SubsecondTime> m_cpiDataCache;

   SubsecondTime *m_cpiCurrentFrontEndStall;

   const bool m_mlp_histogram;
   static const unsigned int MAX_OUTSTANDING = 32;
   std::vector<std::vector<SubsecondTime> > m_outstandingLoads;
   std::vector<SubsecondTime> m_outstandingLoadsAll;

   RobEntry *findEntryBySequenceNumber(UInt64 sequenceNumber);
   bool IsOutOfRange(UInt64 sequenceNumber);
   
   SubsecondTime* findCpiComponent();
   void countOutstandingMemop(SubsecondTime time);
   void printRob();

   void execute(uint64_t& instructionsExecuted, SubsecondTime& latency);
   SubsecondTime doDispatch(SubsecondTime **cpiComponent);
   SubsecondTime doIssue();
   SubsecondTime doCommit(uint64_t& instructionsExecuted);

   void issueInstruction(uint64_t idx, SubsecondTime &next_event);

   long long getPCDiff(uint64_t pc1, uint64_t pc2);
   long long savePCdiff();
   
   std::string getPCDiffAndUpdateLast();
   std::string getPCDiffAndUpdateLast_Marker();

   bool deptraceAnyActive();
   bool deptraceIsActive(thread_id_t thread_id);
   void deptraceSetActive(thread_id_t thread_id, bool is_active = true);
   bool deptraceRMSIsActive(thread_id_t thread_id);
   void deptraceRMSSetActive(thread_id_t thread_id, bool is_active = true);

   static Lock m_print_lock;

public:

   RobTimer(Core *core, PerformanceModel *perf, const CoreModel *core_model, int misprediction_penalty, int dispatch_width, int window_size);
   ~RobTimer();

   boost::tuple<uint64_t,SubsecondTime> simulate(const std::vector<DynamicMicroOp*>& insts);
   void synchronize(SubsecondTime time);
};

#endif /* ROBTIMER_H_ */
