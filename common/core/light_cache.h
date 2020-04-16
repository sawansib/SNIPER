#ifndef __LIGHT_CACHE_H
#define __LIGHT_CACHE_H

#include "fixed_types.h"
#include "sim_api.h"

#include <vector>

class LightCache
{
   private:
      static const UInt32 LINE_BITS = 6;        // 1<<6 == 64 byte lines
      static const UInt32 LINES_BITS = 12;      // 1<<12 lines * 64 bytes/line = 256 KB
      static const UInt32 NUM_LINES = 1 << LINES_BITS;
      static const UInt32 LINES_MASK = NUM_LINES - 1;
      core_id_t m_core_id;
      UInt64 m_accesses;
      UInt64 m_accesses_saved;
      UInt64 m_misses;
      UInt64 m_misses_saved;
      std::vector<std::pair<IntPtr, bool> > m_state;
      IntPtr getTag(IntPtr address) { return address >> LINE_BITS; }
      IntPtr getSet(IntPtr address) { return (address >> LINE_BITS) & LINES_MASK; }
      void invalidate(IntPtr address, bool write) {
         std::pair<IntPtr, bool>& state = m_state[getSet(address)];
         if (state.first == getTag(address)) {
            if (write)
               state.first = INVALID_ADDRESS;
            else if (state.second)
               state.second = false;
         }
      }
      void reset()
      {
         std::pair<IntPtr, bool> empty(INVALID_ADDRESS, false);
         for (std::vector<std::pair<IntPtr, bool> >::iterator i = m_state.begin() ; i != m_state.end() ; ++i)
            *i = empty;
      }
   public:
      LightCache(core_id_t core_id, UInt32 cache_id);
      bool checkHit(IntPtr address, bool write) {
         m_accesses++;
         std::pair<IntPtr, bool>& state = m_state[getSet(address)];
         return (state.first == getTag(address)) && (state.second >= write);
      }
      void updateState(IntPtr address, bool write);
      void access(IntPtr address, bool write) {
         if (!checkHit(address, write))
            updateState(address, write);
      }
      UInt64 getAccesses() { return m_accesses; }
      UInt64 getMisses() { return m_misses; }
      UInt64 getRecentAccesses() { return m_accesses - m_accesses_saved; }
      UInt64 getRecentMisses() { return m_misses - m_misses_saved; }
      void save()
      {
         m_accesses_saved = m_accesses;
         m_misses_saved = m_misses;
      }
      UInt64 getDiff()
      {
         return (m_misses - m_misses_saved) * 100000 / (m_accesses - m_accesses_saved);
      }
};

#endif // __LIGHT_CACHE_H
