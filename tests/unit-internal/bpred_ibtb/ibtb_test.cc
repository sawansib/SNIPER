
#include "fixed_types.h"
#include "ibtb.h"

int main() {

   int rc = 0;

	IndirectBranchTargetBuffer ibtb(256,7);

   IntPtr p = 0x8056;
   bool hit = ibtb.predict(p, p);
   if (hit != false) {
      rc = 1;
      cout << "ibtb failure" << endl;
   }
   
   ibtb.update(true, true, p,p);
   hit = ibtb.predict(p, p);
   if (hit != true) {
      rc = 1;
      cout << "ibtb failure" << endl;
   }

   IntPtr missTagPtr = 0xc056;
   hit = ibtb.predict(missTagPtr, p);
   if (hit != false) {
      rc = 1;
      cout << "ibtb failure" << endl;
   }

   missTagPtr = 0x805a;
   hit = ibtb.predict(missTagPtr, p);
   if (hit != false) {
      rc = 1;
      cout << "ibtb failure" << endl;
   }

   IntPtr missIndexPtr = 0x8156;
   hit = ibtb.predict(missIndexPtr, p);
   if (hit != false) {
      rc = 1;
      cout << "ibtb failure" << endl;
   }

   if (rc == 0) {
      cout << "ibtb - all tests pass" << endl;
   }

   exit (rc);
}
