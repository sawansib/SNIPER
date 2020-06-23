#ifndef __DYNAMIC_INSTRUCTION_H
#define __DYNAMIC_INSTRUCTION_H

#include "operand.h"
#include "subsecond_time.h"
#include "hit_where.h"
#include "allocator.h"
#include <iostream>
#include <sstream>

class Core;
class Instruction;

class DynamicInstruction
{
   private:
      // Private constructor: alloc() should be used
      DynamicInstruction(Instruction *ins, IntPtr _eip)
      {
         instruction = ins;
         eip = _eip;
         branch_info.is_branch = false;
         num_memory = 0;
	 is_xchg = false;
	 is_marker = false; //tells that XCHG is mem dep marker
	 is_marker_end = false; // tells the end of marker
	 is_marker_begin = false; //tells the begin on marker
	 is_marker_dep = false; //tells if marker xchg is dep then save the value
	 marker_value = 0; //tells the marker value (only set for marker dep xchg's)
	 is_not_known = false;
	 is_marker_begin_loop = false;
	 is_marker_end_loop = false;
      }
   public:
      struct BranchInfo
      {
         bool is_branch;
         bool taken;
         IntPtr target;
      };
      struct MemoryInfo {
         bool executed; // For CMOV: true if executed
         Operand::Direction dir;
         IntPtr addr;
         UInt32 size;
         UInt32 num_misses;
         SubsecondTime latency;
         HitWhere::where_t hit_where;
      };
      static const UInt8 MAX_MEMORY = 2;

      Instruction* instruction;
      IntPtr eip; // Can be physical address, so different from instruction->getAddress() which is always virtual
      BranchInfo branch_info;
      UInt8 num_memory;
      MemoryInfo memory_info[MAX_MEMORY];
      bool is_xchg;
      int reg_value;
      bool is_marker; //tells that XCHG is mem dep marker
      //int final_marker_value;
      //int marker_value[264];
      //int marker_index ;
      bool is_marker_end; // tells the end of marker
      bool is_marker_begin; //tells the begin on marker
      bool is_marker_dep; //tells if marker xchg is dep then save the value
      int marker_value; //tells the marker value (only set for marker dep xchg's)
      bool is_not_known;
      bool is_marker_begin_loop;
      bool is_marker_end_loop;
      static Allocator* createAllocator();

      ~DynamicInstruction();

      static DynamicInstruction* alloc(Allocator *alloc, Instruction *ins, IntPtr eip)
      {
         void *ptr = alloc->alloc(sizeof(DynamicInstruction));
         DynamicInstruction *i = new(ptr) DynamicInstruction(ins, eip);
         return i;
      }
      static void operator delete(void* ptr) { Allocator::dealloc(ptr); }

      SubsecondTime getCost(Core *core);

      bool isBranch() const { return branch_info.is_branch; }
      bool isMemory() const { return num_memory > 0; }

      void addMemory(bool e, SubsecondTime l, IntPtr a, UInt32 s, Operand::Direction dir, UInt32 num_misses, HitWhere::where_t hit_where)
      {
         LOG_ASSERT_ERROR(num_memory < MAX_MEMORY, "Got more than MAX_MEMORY(%d) memory operands", MAX_MEMORY);
         memory_info[num_memory].dir = dir;
         memory_info[num_memory].executed = e;
         memory_info[num_memory].latency = l;
         memory_info[num_memory].addr = a;
         memory_info[num_memory].size = s;
         memory_info[num_memory].num_misses = num_misses;
         memory_info[num_memory].hit_where = hit_where;
         num_memory++;
      }

      void addBranch(bool taken, IntPtr target)
      {
         branch_info.is_branch = true;
         branch_info.taken = taken;
         branch_info.target = target;
      }

      void setXchgRegValue(int value) 
      {
	is_xchg = true;
	reg_value = value;
      }

       void setMarker(bool marker){is_marker = marker;} 
       bool getMarker() const { return is_marker;}
       
       void setStartMarker() {is_marker_begin = true;}
       void setEndMarker() {is_marker_end = true;}
       void SetMarkerValue(int value){marker_value = value;}
       void setMarkerDep(bool dep){is_marker_dep = dep;}
       void setNotKnown() {is_not_known = true;}
       void setMarkerBeginLoop() {is_marker_begin_loop = true;}
       void setMarkerEndLoop() {is_marker_end_loop = true;}
 

       bool getNotKnown() const {return is_not_known;}
       bool getStartMarker() const {return is_marker_begin;}
       bool getEndMarker() const {return is_marker_end;}
       int getMarkerValue() const {return marker_value;}
       bool getMarkerDep() const {return is_marker_dep;}
       bool getMarkerBeginLoop() const {return is_marker_begin_loop;}
       bool getMarkerEndLoop() const {return is_marker_end_loop;}
 
       SubsecondTime getBranchCost(Core *core, bool *p_is_mispredict = NULL);
      void accessMemory(Core *core);
};

#endif // __DYNAMIC_INSTRUCTION_H
