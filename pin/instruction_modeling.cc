#include "instruction_modeling.h"
#include "inst_mode_macros.h"
#include "local_storage.h"
#include "spin_loop_detection.h"
#include "lite/memory_modeling.h"
#include "lite/handle_syscalls.h"

#include "simulator.h"
#include "performance_model.h"
#include "core_manager.h"
#include "core.h"
#include "thread.h"
#include "timer.h"
#include "instruction_decoder.h"
#include "instruction.h"
#include "dynamic_instruction.h"
#include "micro_op.h"
#include "magic_client.h"
#include "inst_mode.h"
#include "dvfs_manager.h"
#include "hooks_manager.h"
#include "branch_predictor.h"
#include "dynamic_micro_op.h"

#include <unordered_map>

void InstructionModeling::handleInstruction(THREADID thread_id, Instruction *instruction)
{
   Thread *thread = localStore[thread_id].thread;
   Core *core = thread->getCore();
   PerformanceModel *prfmdl = core->getPerformanceModel();

   if (localStore[thread_id].dynins)
      prfmdl->queueInstruction(localStore[thread_id].dynins);

   localStore[thread_id].dynins = prfmdl->createDynamicInstruction(instruction, instruction->getAddress());
}

void InstructionModeling::handleBasicBlock(THREADID thread_id)
{
   Thread *thread = localStore[thread_id].thread;
   Core *core = thread->getCore();
   assert(core);
   PerformanceModel *prfmdl = core->getPerformanceModel();

   if (localStore[thread_id].dynins)
   {
      prfmdl->queueInstruction(localStore[thread_id].dynins);
      localStore[thread_id].dynins = NULL;
   }

#ifndef ENABLE_PERF_MODEL_OWN_THREAD
   prfmdl->iterate();
   SubsecondTime time = prfmdl->getElapsedTime();
   if (thread->reschedule(time, core))
   {
      core = thread->getCore();
      prfmdl = core->getPerformanceModel();
   }
#endif
}

static void handleBranch(THREADID thread_id, ADDRINT eip, BOOL taken, ADDRINT target)
{
   assert(localStore[thread_id].dynins);
   localStore[thread_id].dynins->addBranch(taken, target);
}

static void handleBranchWarming(THREADID thread_id, ADDRINT eip, BOOL taken, ADDRINT target)
{
   Core *core = localStore[thread_id].thread->getCore();
   assert(core);
   PerformanceModel *prfmdl = core->getPerformanceModel();

   bool mispredict = core->accessBranchPredictor(eip, taken, target);
   if (mispredict)
      prfmdl->handleBranchMispredict();
}

ADDRINT handleMagic(THREADID threadIndex, ADDRINT a, ADDRINT b, ADDRINT c)
{
   return handleMagicInstruction(localStore[threadIndex].thread->getId(), a, b, c);
}

static void handleXchg(const CONTEXT *ctxt, THREADID thread_id) {
  REG reg = REG_EDI;
  assert(!REG_is_gr8(reg) && !REG_is_gr16(reg));
  ADDRINT regVal;
  regVal = PIN_GetContextReg(ctxt, REG_FullRegName(reg));
  if (int(regVal) > 0) {
    //cerr << thread_id << " BEGIN_iDRF " << int(regVal) << endl;
  } else {
    //cerr << thread_id << " END_iDRF " << 0 - int(regVal) << endl;
  }
  assert(localStore[thread_id].dynins);
  localStore[thread_id].dynins->setXchgRegValue(int(regVal));
}

static void handleXchgRDI(const CONTEXT *ctxt, THREADID thread_id) {
  localStore[thread_id].dynins->setMarker(true); //Sends the info that this XCHG belongs to the Mem Dep project
  localStore[thread_id].dynins->setStartMarker(); //Make the Marker true for that instruction
}

static void handleXchgRCX(const CONTEXT *ctxt, THREADID thread_id) {
  localStore[thread_id].dynins->setMarker(true);
  localStore[thread_id].dynins->setEndMarker();
}

static void handleXchgRBX(const CONTEXT *ctxt, THREADID thread_id) {
  localStore[thread_id].dynins->setMarker(true);
  localStore[thread_id].dynins->setNotKnown();
 }

static void handleXchgDep0(const CONTEXT *ctxt, THREADID thread_id) {
  localStore[thread_id].dynins->setMarker(true);
  localStore[thread_id].dynins->setMarkerDep(true);
  localStore[thread_id].dynins->SetMarkerValue(0);
}

static void handleXchgDep1(const CONTEXT *ctxt, THREADID thread_id) {
  localStore[thread_id].dynins->setMarker(true);
  localStore[thread_id].dynins->setMarkerDep(true);
  localStore[thread_id].dynins->SetMarkerValue(1);
}

static void handleXchgDep2(const CONTEXT *ctxt, THREADID thread_id) {
  localStore[thread_id].dynins->setMarker(true);
  localStore[thread_id].dynins->setMarkerDep(true);
  localStore[thread_id].dynins->SetMarkerValue(2);
}
static void handleXchgDep3(const CONTEXT *ctxt, THREADID thread_id) {
  localStore[thread_id].dynins->setMarker(true);
  localStore[thread_id].dynins->setMarkerDep(true);
  localStore[thread_id].dynins->SetMarkerValue(3);
}

static void handleXchgDep4(const CONTEXT *ctxt, THREADID thread_id) {
  localStore[thread_id].dynins->setMarker(true);
  localStore[thread_id].dynins->setMarkerDep(true);
  localStore[thread_id].dynins->SetMarkerValue(4);
}

static void handleXchgDep5(const CONTEXT *ctxt, THREADID thread_id) {
  localStore[thread_id].dynins->setMarker(true);
  localStore[thread_id].dynins->setMarkerDep(true);
  localStore[thread_id].dynins->SetMarkerValue(5);
}

static void handleXchgDep6(const CONTEXT *ctxt, THREADID thread_id) {
  localStore[thread_id].dynins->setMarker(true);
  localStore[thread_id].dynins->setMarkerDep(true);
  localStore[thread_id].dynins->SetMarkerValue(6);
}

static void handleXchgDep7(const CONTEXT *ctxt, THREADID thread_id) {
  localStore[thread_id].dynins->setMarker(true);
  localStore[thread_id].dynins->setMarkerDep(true);
  localStore[thread_id].dynins->SetMarkerValue(7);
}

static void handleXchgBeginLoop(const CONTEXT *ctxt, THREADID thread_id) {
  localStore[thread_id].dynins->setMarker(true);
  localStore[thread_id].dynins->setMarkerBeginLoop();
  // cerr << "called\n";
}

static void handleXchgEndLoop(const CONTEXT *ctxt, THREADID thread_id) {
  localStore[thread_id].dynins->setMarker(true);
  localStore[thread_id].dynins->setMarkerEndLoop();
  ////cerr <<"end \n";
}


VOID InstructionModeling::handleXchgDep(const CONTEXT *ctxt, THREADID thread_id, INS ins) {
  localStore[thread_id].dynins->setXchgRegValue(0);
  if (INS_OperandReg(ins, 0) == REG_R8 && INS_OperandReg(ins, 1) == REG_R8)
    localStore[thread_id].dynins->SetMarkerValue(0);
  else if (INS_OperandReg(ins, 0) == REG_R9 && INS_OperandReg(ins, 1) == REG_R9)
    localStore[thread_id].dynins->SetMarkerValue(1);
  else if (INS_OperandReg(ins, 0) == REG_R10 && INS_OperandReg(ins, 1) == REG_R10)
    localStore[thread_id].dynins->SetMarkerValue(2);
  else if (INS_OperandReg(ins, 0) == REG_R11 && INS_OperandReg(ins, 1) == REG_R11)
    localStore[thread_id].dynins->SetMarkerValue(3);
  else if (INS_OperandReg(ins, 0) == REG_R12 && INS_OperandReg(ins, 1) == REG_R12)
    localStore[thread_id].dynins->SetMarkerValue(4);
  else if (INS_OperandReg(ins, 0) == REG_R13 && INS_OperandReg(ins, 1) == REG_R13)
    localStore[thread_id].dynins->SetMarkerValue(5);
  else if (INS_OperandReg(ins, 0) == REG_R14 && INS_OperandReg(ins, 1) == REG_R14)
    localStore[thread_id].dynins->SetMarkerValue(6);
  else if (INS_OperandReg(ins, 0) == REG_R15 && INS_OperandReg(ins, 1) == REG_R15)
    localStore[thread_id].dynins->SetMarkerValue(7);
  else
    assert(false);
  //assert(localStore[thread_id].dynins);
}

static void handleRdtsc(THREADID thread_id, PIN_REGISTER * gax, PIN_REGISTER * gdx)
{
   Core *core = localStore[thread_id].thread->getCore();
   assert (core);
   SubsecondTime cycles_fs = core->getPerformanceModel()->getElapsedTime();
   // Convert SubsecondTime to cycles in global clock domain
   const ComponentPeriod *dom_global = Sim()->getDvfsManager()->getGlobalDomain();
   UInt64 cycles = SubsecondTime::divideRounded(cycles_fs, *dom_global);
   // Return in eax and edx
   gdx->dword[0] = cycles >> 32;
   gax->dword[0] = cycles & 0xffffffff;
}

static void handleCpuid(THREADID thread_id, PIN_REGISTER * gax, PIN_REGISTER * gbx, PIN_REGISTER * gcx, PIN_REGISTER * gdx)
{
   Core *core = localStore[thread_id].thread->getCore();
   assert (core);

   cpuid_result_t res;
   core->emulateCpuid(gax->dword[0], gcx->dword[0], res);

   gax->dword[0] = res.eax;
   gbx->dword[0] = res.ebx;
   gcx->dword[0] = res.ecx;
   gdx->dword[0] = res.edx;
}

static void handlePause()
{
   // Mostly used Inside spinlocks, use it here to increase the probability
   // that another processor/thread will get some functional execution time
   PIN_Yield();
}

static void fillOperandListMemOps(OperandList *list, INS ins)
{
   if (INS_IsMemoryRead (ins) || INS_IsMemoryWrite (ins))
   {
      // first all reads (dyninstrinfo pushed from redirectMemOp)
      for (unsigned int i = 0; i < INS_MemoryOperandCount(ins); i++)
      {
         if (INS_MemoryOperandIsRead(ins, i))
            list->push_back(Operand(Operand::MEMORY, 0, Operand::READ));
      }
      // then all writes (dyninstrinfo pushed from completeMemWrite)
      for (unsigned int i = 0; i < INS_MemoryOperandCount(ins); i++)
      {
         if (INS_MemoryOperandIsWritten(ins, i))
            list->push_back(Operand(Operand::MEMORY, 0, Operand::WRITE));
      }
   }
}

static void fillOperandList(OperandList *list, INS ins)
{
   // memory
   fillOperandListMemOps(list, ins);

   // for handling register operands
   unsigned int max_read_regs = INS_MaxNumRRegs(ins);
   unsigned int max_write_regs = INS_MaxNumWRegs(ins);

   for (unsigned int i = 0; i < max_read_regs; i++)
   {
      REG reg_i = INS_RegR(ins, i);
      if (REG_valid(reg_i))
         list->push_back(Operand(Operand::REG, reg_i, Operand::READ, REG_StringShort(reg_i).c_str(), INS_RegRContain(ins, reg_i)));
   }

   for (unsigned int i = 0; i < max_write_regs; i++)
   {
      REG reg_i = INS_RegW(ins, i);
      if (REG_valid(reg_i))
         list->push_back(Operand(Operand::REG, reg_i, Operand::WRITE, REG_StringShort(reg_i).c_str(), INS_RegWContain(ins, reg_i)));
   }

   // immediate
   for (unsigned int i = 0; i < INS_OperandCount(ins); i++)
   {
      if (INS_OperandIsImmediate(ins, i))
      {
         list->push_back(Operand(Operand::IMMEDIATE, INS_OperandImmediate(ins, i), Operand::READ));
      }
   }
}

std::unordered_map<ADDRINT, const std::vector<const MicroOp *> *> instruction_cache;

VOID InstructionModeling::addInstructionModeling(TRACE trace, INS ins, InstMode::inst_mode_t inst_mode)
{
   // Functional modeling

   // Simics-style magic instruction: xchg bx, bx
   if (INS_IsXchg(ins) && INS_OperandReg(ins, 0) == REG_BX && INS_OperandReg(ins, 1) == REG_BX)
   {
      if (Sim()->getConfig()->getEnableSyscallEmulation())
      {
         INS_InsertPredicatedCall(ins, IPOINT_BEFORE, (AFUNPTR)handleMagic, IARG_THREAD_ID, IARG_REG_VALUE, REG_GAX,
            #ifdef TARGET_IA32
               IARG_REG_VALUE, REG_GDX,
            #else
               IARG_REG_VALUE, REG_GBX,
            #endif
            IARG_REG_VALUE, REG_GCX, IARG_RETURN_REGS, REG_GAX, IARG_END);
         // Stop the trace after MAGIC (Redmine #118), which has potentially changed the instrumentation mode,
         // so execution can resume in the correct instrumentation version
         INS_InsertDirectJump(ins, IPOINT_AFTER, INS_Address(ins) + INS_Size(ins));
      }
      else
      {
         INS_InsertPredicatedCall(ins, IPOINT_BEFORE, (AFUNPTR)handleMagic, IARG_THREAD_ID, IARG_REG_VALUE, REG_GAX,
            #ifdef TARGET_IA32
               IARG_REG_VALUE, REG_GDX,
            #else
               IARG_REG_VALUE, REG_GBX,
            #endif
            IARG_REG_VALUE, REG_GCX, IARG_END);
      }
   }

   if (Sim()->getConfig()->getEnableSyscallEmulation())
   {
      if (INS_IsRDTSC(ins))
         INS_InsertPredicatedCall(ins, IPOINT_AFTER, (AFUNPTR)handleRdtsc, IARG_THREAD_ID, IARG_REG_REFERENCE, REG_GAX, IARG_REG_REFERENCE, REG_GDX, IARG_END);

      if (INS_Opcode(ins) == XED_ICLASS_CPUID)
      {
         INS_InsertPredicatedCall(ins, IPOINT_BEFORE, (AFUNPTR)handleCpuid, IARG_THREAD_ID, IARG_REG_REFERENCE, REG_GAX, IARG_REG_REFERENCE, REG_GBX, IARG_REG_REFERENCE, REG_GCX, IARG_REG_REFERENCE, REG_GDX, IARG_END);
         INS_Delete(ins);
      }
   }

   if (INS_Opcode(ins) == XED_ICLASS_PAUSE)
      INS_InsertPredicatedCall(ins, IPOINT_AFTER, (AFUNPTR)handlePause, IARG_END);

   if (INS_IsSyscall(ins) && Sim()->getConfig()->getEnableSyscallEmulation())
   {
      INS_InsertPredicatedCall(ins, IPOINT_BEFORE,
            AFUNPTR(lite::handleSyscall),
            IARG_THREAD_ID,
            IARG_CONTEXT,
            IARG_END);
   }

   // Set up localStore[thread_id].dynins
   if (INSTR_IF_DETAILED(inst_mode) && !INS_IsSyscall(ins))
   {
      Instruction *inst = InstructionModeling::decodeInstruction(ins);
      INSTRUMENT(INSTR_IF_DETAILED(inst_mode), trace, ins, IPOINT_BEFORE, AFUNPTR(InstructionModeling::handleInstruction), IARG_THREAD_ID, IARG_PTR, inst, IARG_END);
   }

   // Timing models, will add dynamic information to localStore[thread_id].dynins
   if (INS_IsBranch(ins) && INS_HasFallThrough(ins))
   {
      // In warming mode, warm up the branch predictors
      INSTRUMENT_PREDICATED(
         INSTR_IF_CACHEONLY(inst_mode),
         trace, ins, IPOINT_TAKEN_BRANCH, (AFUNPTR)handleBranchWarming,
         IARG_THREAD_ID,
         IARG_ADDRINT, INS_Address(ins),
         IARG_BOOL, TRUE,
         IARG_BRANCH_TARGET_ADDR,
         IARG_END);

      INSTRUMENT_PREDICATED(
         INSTR_IF_CACHEONLY(inst_mode),
         trace, ins, IPOINT_AFTER, (AFUNPTR)handleBranchWarming,
         IARG_THREAD_ID,
         IARG_ADDRINT, INS_Address(ins),
         IARG_BOOL, FALSE,
         IARG_BRANCH_TARGET_ADDR,
         IARG_END);

      // In detailed mode, push a DynamicInstructionInfo
      INSTRUMENT_PREDICATED(
         INSTR_IF_DETAILED(inst_mode),
         trace, ins, IPOINT_TAKEN_BRANCH, (AFUNPTR)handleBranch,
         IARG_THREAD_ID,
         IARG_ADDRINT, INS_Address(ins),
         IARG_BOOL, TRUE,
         IARG_BRANCH_TARGET_ADDR,
         IARG_END);

      INSTRUMENT_PREDICATED(
         INSTR_IF_DETAILED(inst_mode),
         trace, ins, IPOINT_AFTER, (AFUNPTR)handleBranch,
         IARG_THREAD_ID,
         IARG_ADDRINT, INS_Address(ins),
         IARG_BOOL, FALSE,
         IARG_BRANCH_TARGET_ADDR,
         IARG_END);
   }

   // If the instruction is xchg %edi, %edi, get the value on %edi
   if (INS_IsXchg(ins)) {
     assert(INS_OperandCount(ins) == 2);
     if (INS_OperandReg(ins, 0) == INS_OperandReg(ins, 1) && INS_OperandReg(ins, 0) == REG_EDI) {
       INSTRUMENT_PREDICATED(
         INSTR_IF_DETAILED(inst_mode),
         trace, ins, IPOINT_BEFORE, (AFUNPTR)handleXchg, 
	 IARG_CONST_CONTEXT, 
	 IARG_THREAD_ID, 
	 IARG_END);
     }
     
     if (INS_OperandReg(ins, 0) == INS_OperandReg(ins, 1) && INS_OperandReg(ins, 0) == REG_RDI) {
       cerr << "RDI \n";
       INSTRUMENT_PREDICATED(
         INSTR_IF_DETAILED(inst_mode),
         trace, ins, IPOINT_BEFORE, (AFUNPTR)handleXchgRDI, 
	 IARG_CONST_CONTEXT, 
	 IARG_THREAD_ID, 
	 IARG_END);
     }

     if (INS_OperandReg(ins, 0) == INS_OperandReg(ins, 1) && INS_OperandReg(ins, 0) == REG_RCX) {
       cerr << "RCX \n";
       INSTRUMENT_PREDICATED(
         INSTR_IF_DETAILED(inst_mode),
         trace, ins, IPOINT_BEFORE, (AFUNPTR)handleXchgRCX, 
	 IARG_CONST_CONTEXT, 
	 IARG_THREAD_ID, 
	 IARG_END);
     }

     
     if (INS_OperandReg(ins, 0) == INS_OperandReg(ins, 1) && INS_OperandReg(ins, 0) == REG_RBX) {
       cerr << "RBX \n";
       INSTRUMENT_PREDICATED(
         INSTR_IF_DETAILED(inst_mode),
         trace, ins, IPOINT_BEFORE, (AFUNPTR)handleXchgRBX, 
	 IARG_CONST_CONTEXT, 
	 IARG_THREAD_ID, 
	 IARG_END);
     }
     
     if (INS_OperandReg(ins, 0) == INS_OperandReg(ins, 1) && INS_OperandReg(ins, 0) == REG_R8){
       cerr << "R8 \n";
       INSTRUMENT_PREDICATED(
			     INSTR_IF_DETAILED(inst_mode),
			     trace, ins, IPOINT_BEFORE, (AFUNPTR)handleXchgDep0, 
			     IARG_CONST_CONTEXT, 
			     IARG_THREAD_ID, 
			     IARG_END);
     }

     if (INS_OperandReg(ins, 0) == INS_OperandReg(ins, 1) && INS_OperandReg(ins, 0) == REG_R9){
       cerr << "R9 \n";
       INSTRUMENT_PREDICATED(
			     INSTR_IF_DETAILED(inst_mode),
			     trace, ins, IPOINT_BEFORE, (AFUNPTR)handleXchgDep1, 
			     IARG_CONST_CONTEXT, 
			     IARG_THREAD_ID, 
			     IARG_END);
     }
     if (INS_OperandReg(ins, 0) == INS_OperandReg(ins, 1) && INS_OperandReg(ins, 0) == REG_R10){
       cerr << "R10 \n";
       INSTRUMENT_PREDICATED(
			     INSTR_IF_DETAILED(inst_mode),
			     trace, ins, IPOINT_BEFORE, (AFUNPTR)handleXchgDep2, 
			     IARG_CONST_CONTEXT, 
			     IARG_THREAD_ID, 
			     IARG_END);
     }
     if (INS_OperandReg(ins, 0) == INS_OperandReg(ins, 1) && INS_OperandReg(ins, 0) == REG_R11){
       cerr << "R11 \n";
       INSTRUMENT_PREDICATED(
			     INSTR_IF_DETAILED(inst_mode),
			     trace, ins, IPOINT_BEFORE, (AFUNPTR)handleXchgDep3, 
			     IARG_CONST_CONTEXT, 
			     IARG_THREAD_ID, 
			     IARG_END);
     }
     if (INS_OperandReg(ins, 0) == INS_OperandReg(ins, 1) && INS_OperandReg(ins, 0) == REG_R12){
       cerr << "R12 \n";
       INSTRUMENT_PREDICATED(
			     INSTR_IF_DETAILED(inst_mode),
			     trace, ins, IPOINT_BEFORE, (AFUNPTR)handleXchgDep4, 
			     IARG_CONST_CONTEXT, 
			     IARG_THREAD_ID, 
			     IARG_END);
     }
     if (INS_OperandReg(ins, 0) == INS_OperandReg(ins, 1) && INS_OperandReg(ins, 0) == REG_R13){
       cerr << "R13 \n";
       INSTRUMENT_PREDICATED(
			     INSTR_IF_DETAILED(inst_mode),
			     trace, ins, IPOINT_BEFORE, (AFUNPTR)handleXchgDep5, 
			     IARG_CONST_CONTEXT, 
			     IARG_THREAD_ID, 
			     IARG_END);
     }

     if (INS_OperandReg(ins, 0) == INS_OperandReg(ins, 1) && INS_OperandReg(ins, 0) == REG_R14){
       cerr << "R14 \n";
       INSTRUMENT_PREDICATED(
			     INSTR_IF_DETAILED(inst_mode),
			     trace, ins, IPOINT_BEFORE, (AFUNPTR)handleXchgDep6, 
			     IARG_CONST_CONTEXT, 
			     IARG_THREAD_ID, 
			     IARG_END);
     }
     if (INS_OperandReg(ins, 0) == INS_OperandReg(ins, 1) && INS_OperandReg(ins, 0) == REG_R15){
       cerr << "R15 \n";
       INSTRUMENT_PREDICATED(
			     INSTR_IF_DETAILED(inst_mode),
			     trace, ins, IPOINT_BEFORE, (AFUNPTR)handleXchgDep7, 
			     IARG_CONST_CONTEXT, 
			     IARG_THREAD_ID, 
			     IARG_END);
     }
     if (INS_OperandReg(ins, 0) == INS_OperandReg(ins, 1) && INS_OperandReg(ins, 0) == REG_RSI){
       cerr << "RSI \n";
       INSTRUMENT_PREDICATED(
			     INSTR_IF_DETAILED(inst_mode),
			     trace, ins, IPOINT_BEFORE, (AFUNPTR)handleXchgBeginLoop, 
			     IARG_CONST_CONTEXT, 
			     IARG_THREAD_ID, 
			     IARG_END);
     }
     if (INS_OperandReg(ins, 0) == INS_OperandReg(ins, 1) && INS_OperandReg(ins, 0) == REG_RDX){
       cerr << "RDX \n";
       INSTRUMENT_PREDICATED(
			     INSTR_IF_DETAILED(inst_mode),
			     trace, ins, IPOINT_BEFORE, (AFUNPTR)handleXchgEndLoop, 
			     IARG_CONST_CONTEXT, 
			     IARG_THREAD_ID, 
			     IARG_END);
     }
   }   

   if (!INS_IsSyscall(ins))
   {
      // Instrument Memory Operations
      lite::addMemoryModeling(trace, ins, inst_mode);
   }

   // Spin loop detection
   if (Sim()->getConfig()->getEnableSpinLoopDetection())
      addSpinLoopDetection(trace, ins, inst_mode);
}

Instruction* InstructionModeling::decodeInstruction(INS ins)
{
   // Timing modeling

   OperandList list;
   fillOperandList(&list, ins);

   Instruction *inst;

   // branches
   if (INS_IsBranch(ins) && INS_HasFallThrough(ins))
   {
      inst = new BranchInstruction(list);
   }
   // Now handle instructions which have a static cost
   else
   {
      switch(INS_Opcode(ins))
      {
      case XED_ICLASS_DIV:
         inst = new ArithInstruction(INST_DIV, list);
         break;
      case XED_ICLASS_MUL:
         inst = new ArithInstruction(INST_MUL, list);
         break;
      case XED_ICLASS_FDIV:
         inst = new ArithInstruction(INST_FDIV, list);
         break;
      case XED_ICLASS_FMUL:
         inst = new ArithInstruction(INST_FMUL, list);
         break;
      default:
         inst = new GenericInstruction(list);
      }
   }

   ADDRINT addr = INS_Address(ins);

   inst->setAddress(addr);
   inst->setSize(INS_Size(ins));
   inst->setAtomic(INS_IsAtomicUpdate(ins));
   inst->setDisassembly(INS_Disassemble(ins).c_str());


   const std::vector<const MicroOp *> * uops = InstructionDecoder::decode(INS_Address(ins), INS_XedDec(ins), inst);
   inst->setMicroOps(uops);

   return inst;
}

VOID InstructionModeling::countInstructions(THREADID thread_id, ADDRINT address, INT32 count)
{
   if (!Sim()->isRunning())
   {
      // Main thread has exited, but we still seem to be running.
      // Don't touch any more simulator structure as they're being deallocated right now.
      // Just wait here until the whole application terminates us.
      while(1)
         sched_yield();
   }

   Core* core = localStore[thread_id].thread->getCore();
   assert(core);
   bool check_rescheduled = core->countInstructions(address, count);

   if (check_rescheduled)
   {
      // If countInstructions returns true, we may have been rescheduled (using the fast-forward performance model)
      SubsecondTime time;
      if (localStore[thread_id].thread->reschedule(time, core))
      {
         core = localStore[thread_id].thread->getCore();
         core->getPerformanceModel()->queuePseudoInstruction(new SyncInstruction(time, SyncInstruction::UNSCHEDULED));
      }
   }
}

VOID InstructionModeling::accessInstructionCacheWarmup(THREADID threadid, ADDRINT address, UINT32 size)
{
   Core *core = localStore[threadid].thread->getCore();
   assert(core);
   core->accessMemoryFast(true, Core::READ, address);
}
