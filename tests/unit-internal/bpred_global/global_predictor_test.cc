
#include "pentium_m_global_predictor.h"

int main() {

   BranchPredictorReturnValue value;

   PentiumMGlobalPredictor gp;

   IntPtr ip = 0x7829;
   gp.update(false, true, ip, ip);
   value = gp.lookup(ip,ip);
   cout << value << endl;   

   ip = 0x7828; // Force a miss in the tag
   value = gp.lookup(ip,ip);
   cout << value << endl;
   gp.update(false, false, ip, ip);
   gp.update(false, false, ip, ip);
   gp.update(false, false, ip, ip);

   ip = 0x7828; // Hit
   value = gp.lookup(ip,ip);
   cout << value << endl;

	return 0;
}
