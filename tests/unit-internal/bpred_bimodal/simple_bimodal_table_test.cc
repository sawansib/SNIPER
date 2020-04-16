
#include "simple_bimodal_table.h"

#include <iostream>

using namespace std;

int main() {

	SimpleBimodalTable sbt(4096);

	IntPtr ip = 0x6789, tgt = 0x34344;

	bool actual = true;
	bool prediction =  sbt.predict(ip, tgt);
	cout << "Prediction = " << prediction << endl;;
	sbt.update(prediction, actual, ip, tgt);

	actual = true;
	prediction =  sbt.predict(ip, tgt);
	cout << "Prediction = " << prediction << endl;;
	sbt.update(prediction, actual, ip, tgt);

	actual = true;
	prediction =  sbt.predict(ip, tgt);
	cout << "Prediction = " << prediction << endl;;
	sbt.update(prediction, actual, ip, tgt);

	actual = true;
	prediction =  sbt.predict(ip, tgt);
	cout << "Prediction = " << prediction << endl;;
	sbt.update(prediction, actual, ip, tgt);

	actual = true;
	prediction =  sbt.predict(ip, tgt);
	cout << "Prediction = " << prediction << endl;;
	sbt.update(prediction, actual, ip, tgt);

	actual = false;
	prediction =  sbt.predict(ip, tgt);
	cout << "Prediction = " << prediction << endl;;
	sbt.update(prediction, actual, ip, tgt);

	actual = false;
	prediction =  sbt.predict(ip, tgt);
	cout << "Prediction = " << prediction << endl;;
	sbt.update(prediction, actual, ip, tgt);

	actual = false;
	prediction =  sbt.predict(ip, tgt);
	cout << "Prediction = " << prediction << endl;;
	sbt.update(prediction, actual, ip, tgt);

	actual = false;
	prediction =  sbt.predict(ip, tgt);
	cout << "Prediction = " << prediction << endl;;
	sbt.update(prediction, actual, ip, tgt);

	actual = false;
	prediction =  sbt.predict(ip, tgt);
	cout << "Prediction = " << prediction << endl;;
	sbt.update(prediction, actual, ip, tgt);

}
