
#include "fixed_types.h"
#include "pentium_m_loop_branch_predictor.h"

#define TEST_HIT(_hit) ({ if (ret_val.hit != (_hit)) { rc = 1; cout << "lpb failure: \n\t" << ret_val << endl; } })
#define TEST_HIT_PRED(_hit,_pred) ({ if (ret_val.hit != (_hit) || ret_val.prediction != (_pred)) { rc = 1; cout << "lpb failure: \n\t" << ret_val << endl; } })

int main() {

   int rc = 0;
   BranchPredictorReturnValue ret_val;
   PentiumMLoopBranchPredictor lpb;
   bool actual;

   IntPtr p = 0x5922;

   cout << " -- About to start a loop -- " << endl;

   // (predicted, actual, ip, target)
   ret_val = lpb.lookup(p, p);
   cout << ret_val << endl;
   // Unknown state this early 
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   cout << ret_val << endl; 
   // Unknown state this early 
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   cout << ret_val << endl; 
   // Unknown state this early 
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   cout << ret_val << endl; 
   // Unknown state this early 
   lpb.update(false, true, p, p);

   cout << " -- About to continue a loop -- " << endl;

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, true);
   lpb.update(false, true, p, p);

   cout << " -- About to continue a loop -- " << endl;

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, true);
   lpb.update(false, true, p, p);

   cout << " -- About to continue a loop -- " << endl;

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, true);
   lpb.update(false, true, p, p);

   cout << " -- About to continue a loop -- " << endl;

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, true);
   lpb.update(false, true, p, p);

   cout << " -- About to start a shorter loop -- " << endl;

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   // Here, we expect a misprediction, because we are moving to a shorter loop length
   TEST_HIT_PRED(true, false);
   lpb.update(false, true, p, p);

   cout << " -- About to continue the shorter loop -- " << endl;

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   // We have just been trained, so we expect a match here 
   TEST_HIT_PRED(true, true);
   lpb.update(false, true, p, p);

   cout << " -- About to continue the shorter loop -- " << endl;

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, true);
   lpb.update(false, true, p, p);

   cout << " -- About to start a very long loop ( ~10 ) -- " << endl;

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   // We expect this to fail because it thought that this was a shorter loop
   TEST_HIT_PRED(true, true);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   // Not trained yet, so report that we don't have a hit
   TEST_HIT(false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT(false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT(false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT(false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT(false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT(false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT(false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   // Here, expect it to not know how long we will be, but enable the loop here
   TEST_HIT(false);
   lpb.update(false, true, p, p);

   cout << " -- About to continue a very long loop ( ~10 ) -- " << endl;

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, true);
   // Here we enable a true signal, this should be our first match
   lpb.update(false, true, p, p);

   cout << " -- About to continue a very long loop ( ~10 ) -- " << endl;

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, true);
   // This should be our second long-loop match
   lpb.update(false, true, p, p);

   // Now, switch to the opposite direction, to test to see if that code overrides the state properly
   ret_val = lpb.lookup(p, p);
   // This will be our first miss, but it's okay, it doesn't know about our change in direction yet
   TEST_HIT_PRED(true, false);
   lpb.update(false, true, p, p);

   // Here it should have detected our change in direction and disabled the hit signal
   ret_val = lpb.lookup(p, p);
   TEST_HIT(false);
   lpb.update(false, true, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT(false);
   lpb.update(false, false, p, p);


   cout << " -- reverse dir short -- " << endl;

   // Training should be over by now
   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, true);
   lpb.update(false, true, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, true);
   lpb.update(false, true, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);

   cout << " -- reverse dir short -- " << endl;

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, true);
   lpb.update(false, true, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, true);
   lpb.update(false, true, p, p);

   ret_val = lpb.lookup(p, p);
   TEST_HIT_PRED(true, false);
   lpb.update(false, false, p, p);




   if (rc == 0) {
      cout << "lpb success" << endl;
   }

	exit (rc);
}
