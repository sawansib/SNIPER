#include "light_cache.h"
#include "core_manager.h"
#include "stats.h"
#include "hooks_manager.h"

#include <boost/lexical_cast.hpp>

LightCache::LightCache(core_id_t core_id, UInt32 cache_id)
   : m_core_id(core_id)
   , m_accesses(0)
   , m_misses(0)
   , m_state(NUM_LINES, std::pair<IntPtr, bool>(INVALID_ADDRESS, false))
{
   String cache_name = "light_cache";
   if (cache_id)
      cache_name += "_" + boost::lexical_cast<String>(cache_id);

   registerStatsMetric(cache_name, core_id, "accesses", &m_accesses);
   registerStatsMetric(cache_name, core_id, "misses", &m_misses);
}

void
LightCache::updateState(IntPtr address, bool write)
{
   if (!write)
      m_misses++;

   std::pair<IntPtr, bool> &state = m_state[getSet(address)];
   state.first = getTag(address);
   state.second = write;

   for(core_id_t core_id = 0; core_id < (core_id_t)Sim()->getConfig()->getApplicationCores(); core_id++)
      if (core_id != m_core_id)
         Sim()->getCoreManager()->getCoreFromID(core_id)->getLightCache()->invalidate(address, write);
}
